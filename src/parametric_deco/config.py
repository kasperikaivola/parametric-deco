"""Strict JSON configuration. Manufacturing dimensions never scale with envelope."""

from dataclasses import asdict, dataclass, fields
import json
import math
from pathlib import Path

from .model import Issue, ValidationReport, canonical, safe_id


@dataclass(frozen=True)
class Envelope:
    width_mm: float = 1000
    height_mm: float = 1000
    depth_mm: float = 200


@dataclass(frozen=True)
class Material:
    nominal_mm: float = 6
    measured_mm: float = 6
    measurement_status: str = "assumed_unmeasured"
    clearance_mm: float = 0.2
    grade: str | None = None
    finish: str | None = None


@dataclass(frozen=True)
class Grid:
    pitch_x_mm: float = 50
    pitch_y_mm: float = 50
    offset_mm: float = 25
    origin_x_mm: float = 0
    origin_y_mm: float = 0
    hole_diameter_mm: float = 6.5
    edge_margin_mm: float = 15


@dataclass(frozen=True)
class Backplate:
    sides: int = 8
    rotation_deg: float = 22.5


@dataclass(frozen=True)
class ModuleRecipe:
    length_mm: float = 300
    spine_separation_mm: float = 60
    spine_height_mm: float = 80
    joint_datum_mm: float = 45
    rib_top_mm: float = 116
    rib_bottom_mm: float = 10
    stations_mm: tuple = (70, 130, 190, 250)
    rib_widths_mm: tuple = (130, 160, 190, 160)


@dataclass(frozen=True)
class Mounting:
    rear_clearance_mm: float = 10
    hardware_outward_mm: float = 12
    washer_radius_mm: float = 9
    root_half_span_mm: float = 50


@dataclass(frozen=True)
class ModulePlacement:
    module_id: str = "m1"
    x_mm: float = 25
    y_mm: float = 0
    angle_deg: float = 0
    rib_order: tuple = (0, 1, 2, 3)
    station_indices: tuple = (0, 1, 2, 3)
    spine_instance_ids: tuple[str, ...] = ()
    closure_instance_id: str | None = None
    rib_instance_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CuttingBed:
    width_mm: float
    height_mm: float
    spacing_mm: float = 5


@dataclass(frozen=True)
class RadialWeave:
    radius_mm: float = 300
    amplitude_mm: float = 65
    opening_radius_mm: float = 180
    lobes: int = 3
    ribs_per_module: int = 9
    rotation_deg: float = 0
    rib_permutation: tuple = (0, 1, 2, 3, 4, 5, 6, 7, 8)


@dataclass(frozen=True)
class CreatureMask:
    limb_count: int = 4
    cavity_count: int = 6
    ribs_per_limb: int = 6
    shell_layers: int = 6
    limb_layers: int = 4
    limb_reach: float = 1.0
    limb_width: float = 1.0
    rib_height_mm: float = 65.0
    asymmetry: float = 0.08
    scale: float = 1.0
    curl: float = 1.0
    posture: str = "rest"


@dataclass(frozen=True)
class DesignConfig:
    schema_version: int = 1
    units: str = "mm"
    envelope: Envelope = Envelope()
    material: Material = Material()
    grid: Grid = Grid()
    backplate: Backplate = Backplate()
    module: ModuleRecipe = ModuleRecipe()
    mounting: Mounting = Mounting()
    placements: tuple[ModulePlacement, ...] = (ModulePlacement(),)
    cutting_bed: CuttingBed | None = None
    composition: RadialWeave | None = None
    creature: CreatureMask | None = None

    def to_dict(self):
        return asdict(self)


def validate_config(c):
    issues = []

    def bad(field, message):
        issues.append(Issue("error", "config", f"{field}: {message}"))

    def numeric(path, value, positive=True):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or (positive and value <= 0)
        ):
            bad(path, "must be finite" + (" and positive" if positive else ""))
            return False
        return True

    if c.schema_version != 1:
        bad("schema_version", "must be 1")
    if c.units != "mm":
        bad("units", "must be mm")
    if c.creature is not None:
        creature = c.creature
        if c.composition is not None:
            bad("creature", "select only one composition family")
        count_ranges = {
            "limb_count": (2, 6),
            "cavity_count": (3, 8),
            "ribs_per_limb": (3, 7),
            "shell_layers": (3, 6),
            "limb_layers": (3, 5),
        }
        for field, (lo, hi) in count_ranges.items():
            value = getattr(creature, field)
            if type(value) is not int or not lo <= value <= hi:
                bad("creature." + field, f"integer {lo}..{hi} required")
        shape_ranges = {
            "scale": (0.9, 1),
            "curl": (0.8, 1.2),
            "limb_reach": (0.85, 1.05),
            "limb_width": (0.9, 1.1),
            "rib_height_mm": (45, 80),
            "asymmetry": (0, 0.15),
        }
        for field, (lo, hi) in shape_ranges.items():
            value = getattr(creature, field)
            if numeric("creature." + field, value, False) and not lo <= value <= hi:
                bad("creature." + field, f"range {lo}..{hi} required")
        if issues:
            return ValidationReport(tuple(issues))
        if not 0.9 <= creature.scale <= 1 or not 0.8 <= creature.curl <= 1.2:
            bad("creature", "candidate scale .9..1 and curl .8..1.2 required")
        if creature.posture not in ("rest", "raised_crown"):
            bad("creature.posture", "use rest or raised_crown")
        required = (
            c.mounting.rear_clearance_mm
            + (18 + 2 * (creature.shell_layers - 1)) * c.material.measured_mm
            + c.mounting.hardware_outward_mm
        )
        if c.envelope.depth_mm < required:
            bad("envelope.depth_mm", f"creature requires {required:g} mm including hardware")
    if c.composition is not None:
        w = c.composition
        for key in ("radius_mm", "amplitude_mm", "opening_radius_mm", "rotation_deg"):
            numeric("composition." + key, getattr(w, key), key != "rotation_deg")
        if issues:
            return ValidationReport(tuple(issues))
        if w.lobes != 3 or type(w.lobes) is not int:
            bad("composition.lobes", "this candidate family requires 3 lobes / 6 crossings")
        if w.ribs_per_module != 9 or type(w.ribs_per_module) is not int:
            bad("composition.ribs_per_module", "this candidate family requires 9 ribs per module")
        if not 40 <= w.amplitude_mm <= 80 or not 250 <= w.radius_mm <= 340:
            bad("composition.radius_mm", "candidate range is radius 250..340, amplitude 40..80 mm")
        if w.opening_radius_mm > w.radius_mm - w.amplitude_mm - 52:
            bad("composition.opening_radius_mm", "must clear manufactured inner fins and root pads")
        if (
            len(w.rib_permutation) != 9
            or any(type(index) is not int for index in w.rib_permutation)
            or sorted(w.rib_permutation) != list(range(9))
            or any(w.rib_permutation[k] != k for k in (0, 1, 7, 8))
        ):
            bad(
                "composition.rib_permutation",
                "use integer indices; permute compatible central stations 2..6 only",
            )
    for name in ("envelope", "material", "grid", "backplate", "module", "mounting", "cutting_bed"):
        obj = getattr(c, name)
        if obj is None:
            continue
        for f in fields(obj):
            v = getattr(obj, f.name)
            path = f"{name}.{f.name}"
            if f.name in ("grade", "finish", "measurement_status"):
                continue
            if isinstance(v, tuple):
                for i, item in enumerate(v):
                    numeric(f"{path}[{i}]", item)
            else:
                signed = f.name in (
                    "origin_x_mm",
                    "origin_y_mm",
                    "offset_mm",
                    "rotation_deg",
                    "clearance_mm",
                    "rear_clearance_mm",
                    "hardware_outward_mm",
                    "edge_margin_mm",
                    "spacing_mm",
                )
                if (
                    numeric(path, v, not signed)
                    and signed
                    and f.name not in ("origin_x_mm", "origin_y_mm", "offset_mm", "rotation_deg")
                    and v < 0
                ):
                    bad(path, "must be nonnegative")
    if issues:
        return ValidationReport(tuple(issues))
    if not isinstance(c.backplate.sides, int) or c.backplate.sides < 3:
        bad("backplate.sides", "must be an integer >= 3")
    if c.material.measurement_status not in ("assumed_unmeasured", "measured"):
        bad("material.measurement_status", "must be assumed_unmeasured or measured")
    t = c.material.measured_mm
    m = c.module
    if abs(c.material.nominal_mm - t) > 1:
        bad("material.measured_mm", "more than 1 mm from nominal; verify stock")
    g = c.grid
    if c.mounting.washer_radius_mm <= g.hole_diameter_mm / 2 + 1e-6:
        bad("mounting.washer_radius_mm", "washer needs positive bearing outside the mounting hole")
    nearest = min(
        g.pitch_x_mm,
        g.pitch_y_mm,
        math.hypot(g.pitch_y_mm, min(g.offset_mm % g.pitch_x_mm, (-g.offset_mm) % g.pitch_x_mm)),
    )
    if g.hole_diameter_mm + 2 * g.edge_margin_mm > nearest:
        bad("grid.hole_diameter_mm", "insufficient web between neighbouring hole disks")
    if g.edge_margin_mm < c.mounting.washer_radius_mm - g.hole_diameter_mm / 2:
        bad("grid.edge_margin_mm", "washer would cross backing edge")
    total = (
        c.mounting.rear_clearance_mm
        + c.material.measured_mm * 2
        + (152 if c.composition else m.rib_top_mm)
        + c.mounting.hardware_outward_mm
    )
    if c.envelope.depth_mm < total:
        bad("envelope.depth_mm", f"requires at least {total:g} including hardware")
    if not (0 < m.rib_bottom_mm < m.joint_datum_mm < m.spine_height_mm < m.rib_top_mm):
        bad("module.joint_datum_mm", "require bottom < datum < spine height < rib top")
    if m.spine_separation_mm < 4 * (t + c.material.clearance_mm):
        bad("module.spine_separation_mm", "insufficient paired-slot ligament")
    if (
        len(m.stations_mm) < 3
        or tuple(sorted(set(m.stations_mm))) != tuple(m.stations_mm)
        or any(x < 55 or x > m.length_mm - 15 for x in m.stations_mm)
        or any(
            b - a < t + c.material.clearance_mm + 10
            for a, b in zip(m.stations_mm, m.stations_mm[1:])
        )
    ):
        bad("module.length_mm", "stations need root/end margins, unique ascending order and webs")
    if (
        len(m.rib_widths_mm) != len(m.stations_mm)
        or min(m.rib_widths_mm, default=0) < m.spine_separation_mm + 30
    ):
        bad(
            "module.rib_widths_mm", "one compatible profile per station; preserve outside ligaments"
        )
    if not 40 <= c.mounting.root_half_span_mm <= 55:
        bad("mounting.root_half_span_mm", "candidate root wings support half-span 40..55 mm")
    if c.mounting.washer_radius_mm >= 15:
        bad("mounting.washer_radius_mm", "root wing/tool corridor requires radius <15 mm")
    seen = set()
    for p in c.placements:
        try:
            safe_id(p.module_id)
        except ValueError as e:
            bad("placements.module_id", str(e))
        if p.module_id in seen:
            bad("placements.module_id", "duplicate module ID")
        seen.add(p.module_id)
        for key in ("x_mm", "y_mm", "angle_deg"):
            numeric("placements." + key, getattr(p, key), False)
        chosen = p.rib_instance_ids or p.rib_order
        if (
            len(chosen) != len(p.station_indices)
            or len(chosen) < 3
            or len(set(chosen)) != len(chosen)
            or len(set(p.station_indices)) != len(p.station_indices)
            or any(type(x) is not int or not 0 <= x < len(m.stations_mm) for x in p.station_indices)
            or (
                not p.rib_instance_ids
                and any(type(x) is not int or not 0 <= x < len(m.stations_mm) for x in p.rib_order)
            )
        ):
            bad("placements.rib_order", "need >=3 unique available ribs and stations")
        if p.spine_instance_ids and (
            len(p.spine_instance_ids) != 2 or len(set(p.spine_instance_ids)) != 2
        ):
            bad("placements.spine_instance_ids", "need two unique physical spine IDs")
        for identifier in (
            *p.spine_instance_ids,
            *p.rib_instance_ids,
            *((p.closure_instance_id,) if p.closure_instance_id is not None else ()),
        ):
            try:
                safe_id(identifier)
            except ValueError as e:
                bad("placements.instance_ids", str(e))
    if not c.placements:
        bad("placements", "at least one module is required")
    return ValidationReport(tuple(issues))


def config_from_dict(data):
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    unknown = set(data) - {f.name for f in fields(DesignConfig)}
    if unknown:
        raise ValueError(f"unknown config fields: {sorted(unknown)}")
    kwargs = dict(data)
    classes = {
        "envelope": Envelope,
        "material": Material,
        "grid": Grid,
        "backplate": Backplate,
        "module": ModuleRecipe,
        "mounting": Mounting,
        "cutting_bed": CuttingBed,
        "composition": RadialWeave,
        "creature": CreatureMask,
    }
    try:
        for key, cls in classes.items():
            if key in kwargs and kwargs[key] is not None:
                values = dict(kwargs[key])
                for f in fields(cls):
                    if isinstance(f.default, tuple) and f.name in values:
                        values[f.name] = tuple(values[f.name])
                kwargs[key] = cls(**values)
        if "placements" in kwargs:
            kwargs["placements"] = tuple(
                ModulePlacement(
                    **{
                        k: tuple(v)
                        if k
                        in (
                            "rib_order",
                            "station_indices",
                            "spine_instance_ids",
                            "rib_instance_ids",
                        )
                        else v
                        for k, v in p.items()
                    }
                )
                for p in kwargs["placements"]
            )
        c = DesignConfig(**kwargs)
        report = validate_config(c)
    except (TypeError, KeyError) as e:
        raise ValueError(f"invalid config: {e}") from e
    if not report.digital_valid:
        raise ValueError("; ".join(i.message for i in report.issues))
    canonical(c.to_dict())
    return c


def load_config(path: Path):
    return config_from_dict(json.loads(Path(path).read_text()))
