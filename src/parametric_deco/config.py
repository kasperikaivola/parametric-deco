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
    pitch_y_mm: float = 25 * math.sqrt(3)
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
    root_half_span_mm: float = 25 * math.sqrt(3)


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
    rotation_deg: float = 90
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
class Organism:
    arrangement: str = "whorl"
    focal_count: int = 6
    branching: int = 2
    anatomy_phase_deg: float = 0.0
    phase_deg: float = 17.0
    spread: float = 1.0
    symmetry: str = "rotational"
    complexity: int = 0
    secondary_lobes: int | None = None
    channels: int | None = None
    segmentation: int | None = None
    curvature: float = 1.0
    taper: float = 1.0
    swelling: float = 1.0
    angularity: float = 0.0
    asymmetry: float = 0.12


@dataclass(frozen=True)
class RibStudy:
    recipe: ModuleRecipe = ModuleRecipe()
    placements: tuple[ModulePlacement, ...] = (ModulePlacement(),)


STYLE_PARAMETERS = {
    "laminar": Organism,
    "layered-creature": CreatureMask,
    "radial-weave": RadialWeave,
    "rib-study": RibStudy,
}


@dataclass(frozen=True)
class DesignConfig:
    schema_version: int = 2
    units: str = "mm"
    style: str = "laminar"
    parameters: Organism | CreatureMask | RadialWeave | RibStudy = Organism()
    envelope: Envelope = Envelope()
    material: Material = Material()
    grid: Grid = Grid()
    backplate: Backplate = Backplate()
    mounting: Mounting = Mounting()
    cutting_bed: CuttingBed | None = None

    @property
    def module(self):
        return self.parameters.recipe if isinstance(self.parameters, RibStudy) else ModuleRecipe()

    @property
    def placements(self):
        return self.parameters.placements if isinstance(self.parameters, RibStudy) else ()

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

    if type(c.schema_version) is not int or c.schema_version != 2:
        bad("schema_version", "must be 2; rewrite generation requests using schema-v2")
    if not isinstance(c.style, str) or c.style not in STYLE_PARAMETERS:
        bad("style", "use " + ", ".join(STYLE_PARAMETERS))
    elif type(c.parameters) is not STYLE_PARAMETERS[c.style]:
        bad("parameters", "must match selected style " + c.style)
    if issues:
        return ValidationReport(tuple(issues))
    if c.units != "mm":
        bad("units", "must be mm")
    if c.style == "laminar":
        o = c.parameters
        for key, lo, hi in (("focal_count", 3, 9), ("branching", 1, 3), ("complexity", 0, 2)):
            v = getattr(o, key)
            if type(v) is not int or not lo <= v <= hi:
                bad("parameters." + key, f"integer {lo}..{hi} required")
        for key, hi in (("secondary_lobes", 1), ("channels", 3), ("segmentation", 5)):
            v = getattr(o, key)
            if v is not None and (type(v) is not int or not 0 <= v <= hi):
                bad("parameters." + key, f"null or integer 0..{hi} required")
        for key, lo, hi in (
            ("phase_deg", -180, 180),
            ("anatomy_phase_deg", -180, 180),
            ("spread", 0.85, 1.15),
            ("curvature", 0.7, 1.3),
            ("taper", 0.7, 1.3),
            ("swelling", 0.8, 1.2),
            ("angularity", 0, 0.6),
            ("asymmetry", 0, 0.2),
        ):
            v = getattr(o, key)
            if numeric("parameters." + key, v, False) and not lo <= v <= hi:
                bad("parameters." + key, f"range {lo}..{hi} required")
        if o.arrangement not in ("whorl", "bilateral"):
            bad("parameters.arrangement", "use whorl or bilateral")
        if o.symmetry not in ("rotational", "bilateral", "none"):
            bad("parameters.symmetry", "use rotational, bilateral or none")
        for key in ("width_mm", "height_mm", "depth_mm"):
            numeric("envelope." + key, getattr(c.envelope, key))
        if issues:
            return ValidationReport(tuple(issues))
        if not (800 <= c.envelope.width_mm <= 1400 and 800 <= c.envelope.height_mm <= 1400):
            bad("envelope", "organism width and height require 800..1400 mm")
        if not 0.7 <= c.envelope.width_mm / c.envelope.height_mm <= 1.4:
            bad("envelope", "organism aspect ratio requires 0.7..1.4")
        if not 120 <= c.envelope.depth_mm <= 240:
            bad("envelope.depth_mm", "organism relief requires 120..240 mm")
    if c.style == "laminar" and c.parameters.symmetry == "rotational" and all(isinstance(v, (int, float)) and math.isfinite(v) for v in (c.grid.pitch_x_mm, c.grid.pitch_y_mm, c.grid.offset_mm, c.grid.origin_x_mm, c.grid.origin_y_mm)):
        if c.parameters.arrangement != "whorl" or c.parameters.focal_count % 3:
            bad("parameters.symmetry", "exact C3 requires whorl and focal_count divisible by3")
        if (abs(c.grid.pitch_y_mm - c.grid.pitch_x_mm * math.sqrt(3) / 2) > 1e-8
                or abs(c.grid.offset_mm - c.grid.pitch_x_mm / 2) > 1e-8
                or abs(c.grid.origin_x_mm) > 1e-8 or abs(c.grid.origin_y_mm) > 1e-8):
            bad("grid", "exact C3 mounts require origin0 equilateral lattice: pitchY=pitchX*sqrt(3)/2, offset=pitchX/2")
    if c.style == "layered-creature" and type(c.parameters.limb_count) is int and c.parameters.limb_count % 2:
        bad("parameters.limb_count", "mirrored creature requires paired limb counts2,4,6")
    if c.style == "layered-creature" and all(isinstance(v, (int, float)) and math.isfinite(v) for v in (c.grid.origin_x_mm, c.grid.offset_mm, c.grid.pitch_x_mm)) and c.grid.pitch_x_mm > 0 and (abs(c.grid.origin_x_mm) > 1e-8 or min(abs(c.grid.offset_mm % c.grid.pitch_x_mm), abs(c.grid.offset_mm % c.grid.pitch_x_mm - c.grid.pitch_x_mm / 2)) > 1e-8):
        bad("grid", "mirrored mounts require originX0 and offset0 or pitchX/2")
    if c.style == "layered-creature":
        creature = c.parameters
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
                bad("parameters." + field, f"integer {lo}..{hi} required")
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
            if numeric("parameters." + field, value, False) and not lo <= value <= hi:
                bad("parameters." + field, f"range {lo}..{hi} required")
        if issues:
            return ValidationReport(tuple(issues))
        if not 0.9 <= creature.scale <= 1 or not 0.8 <= creature.curl <= 1.2:
            bad("creature", "candidate scale .9..1 and curl .8..1.2 required")
        if creature.posture not in ("rest", "raised_crown"):
            bad("parameters.posture", "use rest or raised_crown")
        required = (
            c.mounting.rear_clearance_mm
            + (18 + 2 * (creature.shell_layers - 1)) * c.material.measured_mm
            + c.mounting.hardware_outward_mm
        )
        if c.envelope.depth_mm < required:
            bad("envelope.depth_mm", f"creature requires {required:g} mm including hardware")
    if c.style == "radial-weave":
        w = c.parameters
        for key in ("radius_mm", "amplitude_mm", "opening_radius_mm", "rotation_deg"):
            numeric("parameters." + key, getattr(w, key), key != "rotation_deg")
        if issues:
            return ValidationReport(tuple(issues))
        if w.lobes != 3 or type(w.lobes) is not int:
            bad("parameters.lobes", "this candidate family requires 3 lobes / 6 crossings")
        if w.ribs_per_module != 9 or type(w.ribs_per_module) is not int:
            bad("parameters.ribs_per_module", "this candidate family requires 9 ribs per module")
        if not 40 <= w.amplitude_mm <= 80 or not 250 <= w.radius_mm <= 340:
            bad("parameters.radius_mm", "candidate range is radius 250..340, amplitude 40..80 mm")
        if w.opening_radius_mm > w.radius_mm - w.amplitude_mm - 52:
            bad("parameters.opening_radius_mm", "must clear manufactured inner fins and root pads")
        if (
            len(w.rib_permutation) != 9
            or any(type(index) is not int for index in w.rib_permutation)
            or sorted(w.rib_permutation) != list(range(9))
            or any(w.rib_permutation[k] != k for k in (0, 1, 7, 8))
        ):
            bad(
                "parameters.rib_permutation",
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
        + (152 if c.style == "radial-weave" else m.rib_top_mm)
        + c.mounting.hardware_outward_mm
    )
    if c.style in ("rib-study", "radial-weave") and c.envelope.depth_mm < total:
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
    if c.style == "rib-study" and not c.placements:
        bad("placements", "at least one module is required")
    return ValidationReport(tuple(issues))


def _construct(cls, values):
    if not isinstance(values, dict):
        raise ValueError(f"{cls.__name__} must be a JSON object")
    values = dict(values)
    for f in fields(cls):
        if isinstance(f.default, tuple) and f.name in values:
            values[f.name] = tuple(values[f.name])
    return cls(**values)


def config_from_dict(data):
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    if ({"organism", "creature", "composition", "module", "placements"} & data.keys()
            or data.get("schema_version", 2) != 2):
        raise ValueError("unsupported old generation request; rewrite using schema-v2 style and "
                         "parameters (see docs/design.md). Saved inventory is not migrated.")
    unknown = set(data) - {f.name for f in fields(DesignConfig)}
    if unknown:
        raise ValueError(f"unknown config fields: {sorted(unknown)}")
    kwargs = dict(data)
    style = kwargs.get("style", "laminar")
    if not isinstance(style, str) or style not in STYLE_PARAMETERS:
        raise ValueError("unknown style; use " + ", ".join(STYLE_PARAMETERS))
    try:
        values = kwargs.get("parameters", {})
        if style == "rib-study":
            if not isinstance(values, dict):
                raise ValueError("parameters must be a JSON object")
            values = dict(values)
            if "recipe" in values:
                values["recipe"] = _construct(ModuleRecipe, values["recipe"])
            if "placements" in values:
                values["placements"] = tuple(_construct(ModulePlacement, p)
                                              for p in values["placements"])
        kwargs["parameters"] = _construct(STYLE_PARAMETERS[style], values)
        for key, cls in {"envelope": Envelope, "material": Material, "grid": Grid,
                         "backplate": Backplate, "mounting": Mounting,
                         "cutting_bed": CuttingBed}.items():
            if key in kwargs and not (key == "cutting_bed" and kwargs[key] is None):
                kwargs[key] = _construct(cls, kwargs[key])
        c = DesignConfig(**kwargs)
        report = validate_config(c)
    except (TypeError, KeyError) as e:
        raise ValueError(f"invalid {style} config: {e}") from e
    if not report.digital_valid:
        raise ValueError("; ".join(i.message for i in report.issues))
    canonical(c.to_dict())
    return c


def load_config(path: Path):
    return config_from_dict(json.loads(Path(path).read_text()))
