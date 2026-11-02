"""Versioned immutable manufacturing and arrangement records (millimetres)."""

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from pathlib import Path
import re

import numpy as np
from shapely.geometry import Polygon
from shapely import normalize

SCHEMA_VERSION = 1
IDENTITY = ((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def safe_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise ValueError(f"invalid ID: {value!r}")
    return value


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    message: str
    part_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValidationReport:
    issues: tuple[Issue, ...] = ()
    physical_validation: str = "not_run"
    host_validation: str = "not_run"
    motion_validation: str = "sampled_translations_only"

    @property
    def digital_valid(self):
        return not any(i.severity == "error" for i in self.issues)

    def to_dict(self):
        return {"schema_version": 1, "digital_valid": self.digital_valid, **asdict(self)}


@dataclass(frozen=True)
class InterfaceStation:
    station_id: str
    x_mm: float
    slot_width_mm: float
    datum_mm: float
    family: str = "perpendicular-pair-v1"


@dataclass(frozen=True)
class Surface:
    surface_id: str
    origin: tuple
    u_axis: tuple
    v_axis: tuple
    outer: tuple
    holes: tuple = ()

    @property
    def polygon(self):
        return Polygon(self.outer, self.holes)


@dataclass(frozen=True)
class PartDefinition:
    definition_id: str
    revision: str
    thickness_mm: float
    outer: tuple
    holes: tuple
    interfaces: tuple[InterfaceStation, ...]
    surfaces: tuple[Surface, ...]
    fingerprint: str
    kind: str = "part"

    @property
    def polygon(self):
        return Polygon(self.outer, self.holes)

    @classmethod
    def from_polygon(cls, definition_id, polygon, thickness_mm, interfaces=(), kind="part"):
        safe_id(definition_id)
        polygon = normalize(polygon)
        if (
            polygon.geom_type != "Polygon"
            or not polygon.is_valid
            or polygon.is_empty
            or not np.isfinite(thickness_mm)
            or thickness_mm <= 0
        ):
            raise ValueError(f"{definition_id}: invalid connected planar part or thickness")
        outer = tuple(tuple(float(v) for v in xy) for xy in polygon.exterior.coords[:-1])
        holes = tuple(
            tuple(tuple(float(v) for v in xy) for xy in r.coords[:-1]) for r in polygon.interiors
        )
        surfaces = [
            Surface(
                "front",
                (0.0, 0.0, float(thickness_mm)),
                (1.0, 0.0, 0.0),
                (0.0, 1.0, 0.0),
                outer,
                holes,
            )
        ]
        # Explicit edge faces, including cut-hole walls. Back face is optional/excluded.
        for ri, ring in enumerate(() if kind in ("backplate", "purchased-hardware") else (outer, *holes)):
            for ei, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1])):
                dx, dy = b[0] - a[0], b[1] - a[1]
                length = float(np.hypot(dx, dy))
                surfaces.append(
                    Surface(
                        f"edge-{ri}-{ei}",
                        (*a, 0.0),
                        (dx / length, dy / length, 0.0),
                        (0.0, 0.0, 1.0),
                        (
                            (0.0, 0.0),
                            (length, 0.0),
                            (length, float(thickness_mm)),
                            (0.0, float(thickness_mm)),
                        ),
                    )
                )
        if kind in ("backplate", "purchased-hardware"):
            surfaces = []
        payload = {
            "thickness_mm": float(thickness_mm),
            "outer": outer,
            "holes": holes,
            "interfaces": [asdict(s) for s in interfaces],
            "kind": kind,
        }
        fingerprint = digest(payload)
        return cls(
            definition_id,
            fingerprint[:12],
            float(thickness_mm),
            outer,
            holes,
            tuple(interfaces),
            tuple(surfaces),
            fingerprint,
            kind,
        )

    def to_dict(self):
        return {"schema_version": 1, **asdict(self)}

    @classmethod
    def from_dict(cls, data):
        if data.get("schema_version") != 1:
            raise ValueError("part schema_version must be 1")
        interfaces = tuple(InterfaceStation(**s) for s in data["interfaces"])
        part = cls.from_polygon(
            data["definition_id"],
            Polygon(data["outer"], data["holes"]),
            data["thickness_mm"],
            interfaces,
            data["kind"],
        )
        if part.fingerprint != data["fingerprint"] or part.revision != data["revision"]:
            raise ValueError(f"{data['definition_id']}: stale geometry fingerprint/revision")
        if canonical([asdict(s) for s in part.surfaces]) != canonical(data["surfaces"]):
            raise ValueError(f"{data['definition_id']}: surface geometry mismatch")
        return part


@dataclass(frozen=True)
class PartInstance:
    instance_id: str
    definition_id: str
    revision: str
    transform: tuple = IDENTITY
    module_id: str = "backing"
    role: str = "part"
    station_id: str | None = None

    def __post_init__(self):
        for identifier in (self.instance_id, self.definition_id, self.module_id):
            safe_id(identifier)
        a = np.asarray(self.transform, dtype=float)
        if (
            a.shape != (4, 4)
            or not np.isfinite(a).all()
            or not np.allclose(a[3], [0, 0, 0, 1], atol=1e-9)
            or not np.allclose(a[:3, :3].T @ a[:3, :3], np.eye(3), atol=1e-9)
            or not np.isclose(np.linalg.det(a[:3, :3]), 1, atol=1e-9)
        ):
            raise ValueError(f"{self.instance_id}: transform must be finite right-handed rigid 4x4")
        object.__setattr__(self, "transform", tuple(tuple(float(x) for x in r) for r in a))


@dataclass(frozen=True)
class Connection:
    a: str
    b: str
    family: str
    station_id: str


@dataclass(frozen=True)
class MountPoint:
    row: int
    column: int
    x_mm: float
    y_mm: float
    diameter_mm: float

    @property
    def point_id(self):
        return f"grid-r{self.row}-c{self.column}"


@dataclass(frozen=True)
class Assembly:
    definitions: tuple[PartDefinition, ...]
    instances: tuple[PartInstance, ...]
    connections: tuple[Connection, ...] = ()
    mounting_grid: tuple = ()
    effect_paths: tuple = ()
    envelope_mm: tuple = (1000.0, 1000.0, 200.0)
    hardware_bounds: tuple = ()
    extraction_paths: tuple = ()
    composition: dict | None = None

    def definition_for(self, instance):
        for d in self.definitions:
            if (d.definition_id, d.revision) == (instance.definition_id, instance.revision):
                return d
        raise ValueError(f"{instance.instance_id}: unknown definition/revision")

    def to_dict(self):
        return {
            "schema_version": 1,
            "units": "mm",
            "definitions": [d.to_dict() for d in self.definitions],
            **{k: v for k, v in asdict(self).items() if k != "definitions"},
        }

    @classmethod
    def from_dict(cls, data):
        if data.get("schema_version") != 1 or data.get("units") != "mm":
            raise ValueError("assembly requires schema_version=1 and units=mm")
        return cls(
            tuple(PartDefinition.from_dict(d) for d in data["definitions"]),
            tuple(PartInstance(**i) for i in data["instances"]),
            tuple(Connection(**c) for c in data["connections"]),
            tuple(data["mounting_grid"]),
            tuple(data["effect_paths"]),
            tuple(data["envelope_mm"]),
            tuple(data["hardware_bounds"]),
            tuple(data["extraction_paths"]),
            data.get("composition"),
        )


@dataclass(frozen=True)
class Inventory:
    definitions: tuple[PartDefinition, ...]
    instances: tuple[PartInstance, ...]
    layout: dict | None = None

    def to_dict(self):
        return {
            "schema_version": 1,
            "units": "mm",
            "definitions": [d.to_dict() for d in self.definitions],
            "instances": [asdict(i) for i in self.instances],
            **({"layout": self.layout} if self.layout is not None else {}),
        }

    @classmethod
    def from_dict(cls, data):
        if data.get("schema_version") != 1 or data.get("units") != "mm":
            raise ValueError("inventory requires schema_version=1 and units=mm")
        result = cls(
            tuple(PartDefinition.from_dict(d) for d in data["definitions"]),
            tuple(PartInstance(**i) for i in data["instances"]),
            data.get("layout"),
        )
        ids = [i.instance_id for i in result.instances]
        if len(ids) != len(set(ids)):
            raise ValueError("inventory contains duplicate instance IDs")
        keys = [(d.definition_id, d.revision) for d in result.definitions]
        if len(keys) != len(set(keys)):
            raise ValueError("inventory contains duplicate definitions")
        for i in result.instances:
            if (i.definition_id, i.revision) not in keys:
                raise ValueError(f"{i.instance_id}: unknown revision")
        return result

    @classmethod
    def load(cls, path):
        return cls.from_dict(json.loads(Path(path).read_text()))


@dataclass(frozen=True)
class GeometryBundle:
    definitions: tuple[PartDefinition, ...]
    instances: tuple[PartInstance, ...] = ()
    solids: dict = field(default_factory=dict, compare=False)


@dataclass(frozen=True)
class BuildResult:
    assembly: Assembly
    fabrication_parts: tuple[PartDefinition, ...]
    warnings: tuple[str, ...] = ()
    provenance: dict = field(default_factory=dict)
    report: ValidationReport = ValidationReport()
    inventory: Inventory | None = None


@dataclass(frozen=True)
class AtlasResult:
    manifest: dict
    textures: dict
    surface_to_tile: dict


@dataclass(frozen=True)
class ExportResult:
    paths: tuple[Path, ...]
    warnings: tuple[str, ...] = ()
    content_hashes: dict = field(default_factory=dict)
