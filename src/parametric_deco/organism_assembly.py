"""Slotted trestle-supported lobes and immutable manufactured inventory."""

from dataclasses import asdict
import json
import math
import numpy as np
from shapely import affinity
from shapely.geometry import Point, Polygon, box, LineString
from shapely.ops import unary_union
from .config import validate_config
from .cad import overlap_volume
from .geometry.organism import anatomy
from .model import (
    Assembly,
    BuildResult,
    Connection,
    InterfaceStation,
    Inventory,
    PartDefinition,
    PartInstance,
    ValidationReport,
    Issue,
    digest,
)
from .validation import validate_assembly, instance_bounds, xy_footprint

FAMILY = "laminar-organism-v2"


def signature(c):
    return digest(
        {
            "family": FAMILY,
            "organism": asdict(c.parameters),
            "size": asdict(c.envelope),
            "stock_mm": c.material.measured_mm,
            "clearance_mm": c.material.clearance_mm,
            "bore_mm": c.grid.hole_diameter_mm,
            "mounting": asdict(c.mounting),
        }
    )


def pose2(center, angle, z):
    co, si = math.cos(angle), math.sin(angle)
    return (
        (co, -si, 0, float(center[0])),
        (si, co, 0, float(center[1])),
        (0, 0, 1, float(z)),
        (0, 0, 0, 1),
    )


def map_shape(shape, pose):
    p = np.asarray(pose)
    return affinity.affine_transform(shape, [p[0, 0], p[0, 1], p[1, 0], p[1, 1], p[0, 3], p[1, 3]])


def guard_slots(shape, slots, holes=(), margin=7):
    """Actual outline, other holes and neighboring slot edge-to-edge margins."""
    for k, slot in enumerate(slots):
        if not shape.buffer(1e-7).covers(slot.buffer(margin)):
            raise ValueError(f"slot {k}: requires {margin} mm outline bearing")
        for other in (*slots[k + 1 :], *holes):
            if slot.distance(other) < margin - 1e-7:
                raise ValueError(f"slot {k}: neighboring slot/hole margin below {margin} mm")


def neck_check(shape, width=8):
    """Conservative morphological neck test, independent of CAD validity.

    Erosion must leave one core; opening loss is limited to rounded tips and corners.
    Closed slot/hole ligaments are checked separately with exact distances.
    """
    core = shape.buffer(-width / 2, quad_segs=8)
    if core.is_empty or core.geom_type != "Polygon":
        raise ValueError(f"material neck below {width} mm or disconnected eroded core")
    if shape.difference(core.buffer(width / 2 + 0.3)).area > max(20, shape.area * 0.015):
        raise ValueError(f"excess material in features below {width} mm")


def cut_ligaments(shape, minimum):
    """Exact hole-to-outline and hole-to-hole material distances in finished cuts."""
    holes = [Polygon(ring) for ring in shape.interiors]
    gaps = [hole.distance(shape.exterior) for hole in holes]
    gaps.extend(a.distance(b) for j, a in enumerate(holes) for b in holes[j + 1 :])
    value = min(gaps) if gaps else None
    if value is not None and value < minimum - 1e-6:
        raise ValueError(f"finished-cut ligament {value:.3f} mm below {minimum:g} mm")
    return value


def support_layout(lobe, lobes, c, used):
    t, fit = c.material.measured_mm, c.material.clearance_mm
    local_slots = [
        box(x - (t + fit) / 2, -7 - fit / 2, x + (t + fit) / 2, 7 + fit / 2) for x in (-12, 12)
    ]
    local_holes = [Point(0, y).buffer(c.grid.hole_diameter_mm / 2, quad_segs=16) for y in (-14, 14)]
    # Candidate positions derive from the actual material, not a coordinate palette.
    x0, y0, x1, y1 = lobe.shape.bounds
    points = [Point(x, y) for x in np.linspace(x0, x1, 32) for y in np.linspace(y0, y1, 32)]
    points.extend(Point(p) for p in lobe.path)
    points = sorted(
        (p for p in points if lobe.shape.contains(p)),
        key=lambda p: (-p.distance(lobe.shape.boundary), p.x, p.y),
    )
    for point in points:
        distances = np.linalg.norm(lobe.path - (point.x, point.y), axis=1)
        index = int(distances.argmin())
        direction = lobe.path[min(index + 1, len(lobe.path) - 1)] - lobe.path[max(index - 1, 0)]
        for angle in (math.atan2(direction[1], direction[0]), 0, math.pi / 2):
            pose = pose2((point.x, point.y), angle, lobe.z)
            slots = [map_shape(s, pose) for s in local_slots]
            holes = [map_shape(h, pose) for h in local_holes]
            try:
                guard_slots(lobe.shape, slots, holes)
            except ValueError:
                continue
            bearings = [
                map_shape(Point(0, y).buffer(c.mounting.washer_radius_mm), pose) for y in (-14, 14)
            ]
            if not all(lobe.shape.covers(b) for b in bearings):
                continue
            feet = [map_shape(box(x - t / 2, -15, x + t / 2, 15), pose) for x in (-12, 12)]
            corridor = unary_union([*feet, *bearings])
            if any(
                corridor.intersects(other.shape)
                for other in lobes
                if other.name != lobe.name
                and other.z < lobe.z + t + c.mounting.hardware_outward_mm + 2
            ):
                continue
            if any(corridor.buffer(2).intersects(region) for region in used):
                continue
            return pose, slots, holes, feet, bearings, corridor
    raise ValueError(
        f"{lobe.name}: no substantial unobstructed trestle mounting patch; "
        "increase size, reduce secondary lobes, or change composition/style"
    )


def manufacture(c):
    lobes = anatomy(c)
    t = c.material.measured_mm
    fit = c.material.clearance_mm
    base = c.mounting.rear_clearance_mm + t
    definitions, instances, modules, used = [], [], [], []
    backing_regions, backing_cuts = [], []

    def add(name, shape, pose, module, role, interfaces=()):
        part = PartDefinition.from_polygon("flow-" + name, shape, t, interfaces, kind=role)
        definitions.append(part)
        inst = PartInstance(name, part.definition_id, part.revision, pose, module, role)
        instances.append(inst)
        return part

    for lobe in lobes:
        pose, slots, holes, feet, bearings, corridor = support_layout(lobe, lobes, c, used)
        used.append(corridor)
        center = np.array(pose)[:2, 3]
        # Thin but continuous backing frame follows the anatomical material.
        rail_path = lobe.path if lobe.backing_path is None else lobe.backing_path
        rail = LineString(rail_path[10:-10]).buffer(14, quad_segs=8)
        backing_regions.append(rail)
        from shapely.ops import nearest_points

        nearest = nearest_points(Point(center), rail)[1]
        backing_regions.append(LineString([Point(center), nearest]).buffer(14, quad_segs=8))
        backing_regions.extend(b.buffer(10) for b in bearings)
        backing_regions.extend(f.buffer(12) for f in feet)
        backing_cuts.extend([*slots, *holes])
        cap = lobe.shape.difference(unary_union([*slots, *holes]))
        neck_check(lobe.shape, 10)
        ligament = cut_ligaments(cap, 7)
        name = lobe.name
        cap_id = name + "-plate"
        add(
            cap_id,
            cap,
            pose2((0, 0), 0, lobe.z),
            name,
            "armour",
            tuple(
                InterfaceStation(
                    f"seat-{j}",
                    float(s.centroid.x),
                    t + fit,
                    float(s.centroid.y),
                    "flow-trestle-v1",
                )
                for j, s in enumerate(slots)
            ),
        )
        height = lobe.z - base
        web = box(-15, 0, 15, height).union(box(-7, -t, 7, height + t))
        neck_check(web, 8)
        web_ids = []
        for j, x in enumerate((-12, 12)):
            # Web local X = cap local Y, local Y = world Z, normal = cap local X.
            p = np.array(pose)
            u, v = p[:3, 0], p[:3, 1]
            origin = np.array((center[0], center[1], base)) + (x - t / 2) * u
            transform = np.eye(4)
            transform[:3, :3] = np.column_stack((v, (0, 0, 1), u))
            transform[:3, 3] = origin
            wid = name + f"-trestle-{j}"
            add(wid, web, tuple(map(tuple, transform)), name, "register")
            web_ids.append(wid)
        roots = [tuple(h.centroid.coords[0]) for h in holes]
        modules.append(
            {
                "module_id": name,
                "plate_id": cap_id,
                "web_ids": web_ids,
                "roots": roots,
                "slot_polygons": [list(s.exterior.coords) for s in slots],
                "z_mm": lobe.z,
                "height_mm": height,
                "tier": lobe.tier,
                "minimum_cut_ligament_mm": ligament,
            }
        )
    # A narrow flowing framework, joined at nearest points, avoids a central slab.
    backing = unary_union(backing_regions)
    while backing.geom_type != "Polygon":
        from shapely.ops import nearest_points

        pieces = list(backing.geoms)
        a, b = min(
            ((a, b) for i, a in enumerate(pieces) for b in pieces[i + 1 :]),
            key=lambda pair: pair[0].distance(pair[1]),
        )
        p, q = nearest_points(a, b)
        backing = backing.union(LineString([p, q]).buffer(14, quad_segs=8))
    # Add a fixed 4 mm structural allowance to both rail edges, independent of size.
    backing = backing.buffer(4, quad_segs=8)
    guard_slots(
        backing,
        [Polygon(m["slot_polygons"][j]) for m in modules for j in (0, 1)],
        [
            Point(x, y).buffer(c.grid.hole_diameter_mm / 2, quad_segs=16)
            for m in modules
            for x, y in m["roots"]
        ],
    )
    backing = backing.difference(unary_union(backing_cuts))
    cut_ligaments(backing, 7)
    add(
        "backplate", backing, pose2((0, 0), 0, c.mounting.rear_clearance_mm), "backing", "backplate"
    )
    layout = {
        "family": FAMILY,
        "manufacturing_request": signature(c),
        "modules": modules,
        "removal_order": [lobe.name for lobe in sorted(lobes, key=lambda lobe: -lobe.z)],
        "templates": [asdict(i) for i in instances],
    }
    layout["fingerprint"] = digest(layout)
    return definitions, instances, json.loads(json.dumps(layout))


def verify_organism(a):
    """Recheck actual manufactured bearing/slots/supports, including loaded geometry."""
    issues = []
    try:
        metadata = a.composition
        if metadata.get("family") != FAMILY:
            raise ValueError("flow family metadata required")
        by_id = {i.instance_id: i for i in a.instances}
        backing = by_id["backplate"]
        washer = metadata["washer_radius_mm"]
        hole = metadata["hole_radius_mm"]
        for module in metadata["modules"]:
            cap = by_id[module["plate_id"]]
            for x, y in module["roots"]:
                ring = (
                    Point(x, y)
                    .buffer(washer, quad_segs=24)
                    .difference(Point(x, y).buffer(hole + 0.04, quad_segs=24))
                )
                bore = Point(x, y).buffer(hole - 0.02, quad_segs=24)
                for inst in (cap, backing):
                    footprint = xy_footprint(a.definition_for(inst), inst.transform)
                    if (
                        ring.difference(footprint).area > 1e-5
                        or bore.intersection(footprint).area > 1e-5
                    ):
                        issues.append(
                            Issue(
                                "error",
                                "root_bearing",
                                inst.instance_id + ": missing bolt bore/washer bearing",
                            )
                        )
                corridor = Point(x, y).buffer(washer, quad_segs=24)
                for other in a.instances:
                    if other.module_id in (module["module_id"], "backing"):
                        continue
                    bounds = instance_bounds(a.definition_for(other), other.transform)
                    if (
                        bounds[0, 2]
                        < module["z_mm"]
                        + a.definition_for(cap).thickness_mm
                        + metadata["hardware_outward_mm"]
                    ):
                        if (
                            corridor.intersection(
                                xy_footprint(a.definition_for(other), other.transform)
                            ).area
                            > 1e-5
                        ):
                            issues.append(
                                Issue(
                                    "error",
                                    "bolt_corridor",
                                    other.instance_id + ": hardware access blocked",
                                )
                            )
            slots = [Polygon(p) for p in module["slot_polygons"]]
            for inst in (cap, backing):
                cut_ligaments(a.definition_for(inst).polygon, 7)
                footprint = xy_footprint(a.definition_for(inst), inst.transform)
                guard_slots(unary_union([footprint, *slots]), slots)
                if any(footprint.intersection(slot).area > 1e-5 for slot in slots):
                    issues.append(
                        Issue(
                            "error",
                            "trestle_slot",
                            inst.instance_id + ": missing manufactured slot",
                        )
                    )
            for wid in module["web_ids"]:
                web = by_id[wid]
                for support, dz in ((cap, 1), (backing, -1)):
                    pose = np.array(web.transform)
                    pose[2, 3] += dz
                    if (
                        overlap_volume(
                            a.definition_for(web),
                            pose,
                            a.definition_for(support),
                            support.transform,
                        )
                        <= 1e-5
                    ):
                        issues.append(
                            Issue("error", "trestle_bearing", wid + ": missing shoulder bearing")
                        )
    except (KeyError, ValueError, AttributeError) as error:
        issues.append(Issue("error", "organism_geometry", str(error)))
    return ValidationReport(tuple(issues))


def assemble_organism(c, inventory=None):
    report = validate_config(c)
    if not report.digital_valid:
        raise ValueError("; ".join(i.message for i in report.issues))
    if inventory is None:
        definitions, instances, layout = manufacture(c)
    else:
        inventory = Inventory.from_dict(inventory.to_dict())
        layout = json.loads(json.dumps(inventory.layout))
        if not layout or layout.get("family") != FAMILY:
            raise ValueError(
                "laminar-organism-v2 inventory required; earlier scroll geometry requires new cuts"
            )
        saved = layout.pop("fingerprint", None)
        if digest(layout) != saved:
            raise ValueError("stale inventory layout fingerprint")
        layout["fingerprint"] = saved
        if layout["manufacturing_request"] != signature(c):
            raise ValueError("manufacturing request differs; requires new cuts")
        definitions = inventory.definitions
        instances = tuple(PartInstance(**i) for i in layout["templates"])
        expected = {
            (i.instance_id, i.definition_id, i.revision, i.role, i.module_id) for i in instances
        }
        actual = {
            (i.instance_id, i.definition_id, i.revision, i.role, i.module_id)
            for i in inventory.instances
        }
        if actual != expected:
            raise ValueError("missing, extra or changed physical inventory")
    hardware, mounts, connections = [], [], []
    for m in layout["modules"]:
        for j, (x, y) in enumerate(m["roots"]):
            r = c.mounting.washer_radius_mm
            hardware.append(
                (
                    m["module_id"],
                    x - r,
                    y - r,
                    0,
                    x + r,
                    y + r,
                    m["z_mm"] + c.material.measured_mm + c.mounting.hardware_outward_mm,
                )
            )
            mounts.append((m["module_id"], f"root-{j}", x, y))
        connections.append(
            Connection(m["plate_id"], "backplate", "creature-root-clamp-v1", "bolts")
        )
        connections.extend(
            Connection(w, m["plate_id"], "flow-trestle-v1", f"seat-{j}")
            for j, w in enumerate(m["web_ids"])
        )
    count = len(layout["modules"])
    metadata = {
        **layout,
        "washer_radius_mm": c.mounting.washer_radius_mm,
        "hole_radius_mm": c.grid.hole_diameter_mm / 2,
        "hardware_outward_mm": c.mounting.hardware_outward_mm,
        "construction": {
            "plywood_parts": len(instances),
            "spacers": 0,
            "retainers": 0,
            "bolts": 2 * count,
            "nuts": 2 * count,
            "washers": 4 * count,
            "assembly_operations_estimate": 7 * count,
            "operation_basis": "2 trestle insertions + plate placement + 2 bolt insertions + 2 nut tightenings/module",
        },
        "physical_validation": "NOT RUN",
        "host_validation": "NOT RUN",
    }
    a = Assembly(
        tuple(definitions),
        tuple(instances),
        tuple(connections),
        tuple(mounts),
        tuple((m["plate_id"], j / count, (j + 1) / count) for j, m in enumerate(layout["modules"])),
        (c.envelope.width_mm, c.envelope.height_mm, c.envelope.depth_mm),
        tuple(hardware),
        tuple(
            (m["module_id"], (0, 0, 1), tuple(range(0, math.ceil(c.envelope.depth_mm) + 25, 8)))
            for m in layout["modules"]
        ),
        metadata,
    )
    report = validate_assembly(a)
    dependencies = {
        i.part_ids[0]: set(i.part_ids[1:])
        for i in report.issues
        if i.code == "extraction_dependency"
    }
    removed, issues = set(), [*report.issues, *verify_organism(a).issues]
    for name in layout["removal_order"]:
        if dependencies.get(name, set()) - removed:
            issues.append(Issue("error", "removal_order", name + ": sampled removal order blocked"))
        removed.add(name)
    bounds = np.array([instance_bounds(a.definition_for(i), i.transform) for i in a.instances])
    metadata["actual_bounds_mm"] = [
        bounds[:, 0].min(axis=0).tolist(),
        bounds[:, 1].max(axis=0).tolist(),
    ]
    metadata["sampled_extraction_dependencies"] = {k: sorted(v) for k, v in dependencies.items()}
    return BuildResult(
        a,
        tuple(definitions),
        (
            "Physical strength, fit, bolt security and detached handling NOT RUN.",
            "Support modules in a cradle; remove upper overlapping modules before lower ones.",
            "Wire/Arena/projector runtime NOT RUN; sampled motions are not continuous certification.",
        ),
        {
            "generator": FAMILY,
            "mode": "existing_inventory" if inventory else "generate_new",
            "config": c.to_dict(),
            "config_hash": digest(c.to_dict()),
        },
        ValidationReport(tuple(issues)),
        Inventory(tuple(definitions), tuple(instances), layout),
    )
