"""Authoritative creature inventory placement, mechanical checks and removal evidence."""

from dataclasses import replace
import json
import numpy as np
from shapely.geometry import Point
from shapely import affinity
from .cad import overlap_volume
from .config import validate_config
from .geometry.creature import generate_creature, request_signature
from .geometry.backplate import match_root_pattern
from .model import (
    Assembly,
    Inventory,
    BuildResult,
    PartInstance,
    Connection,
    Issue,
    ValidationReport,
    digest,
)
from .validation import validate_assembly, xy_footprint, instance_bounds


def verify_creature(a):
    issues = []
    by_id = {i.instance_id: i for i in a.instances}
    if not a.composition or a.composition.get("family") != "creature-mask-v1":
        return ValidationReport((Issue("error", "family", "creature metadata required"),))
    for m in a.composition["modules"]:
        try:
            cap = by_id[m["cap_id"]]
            for kid in m["key_ids"]:
                key = by_id[kid]
                part = a.definition_for(key)
                lifted = np.array(key.transform)
                lifted[2, 3] += 1
                if overlap_volume(part, lifted, a.definition_for(cap), cap.transform) <= 1e-5:
                    issues.append(
                        Issue(
                            "error", "web_capture", f"{kid}: cap does not block outward withdrawal"
                        )
                    )
                for pid in m["plate_ids"][:-1]:
                    plate = by_id[pid]
                    shape = xy_footprint(a.definition_for(plate), plate.transform)
                    key_shape = xy_footprint(part, key.transform)
                    if shape.intersection(key_shape).area > 1e-7:
                        issues.append(
                            Issue(
                                "error", "register_slot", f"{kid}: slot registration interference"
                            )
                        )
            for x, y in m["placed_roots"]:
                radius = a.composition["washer_radius_mm"]
                hole_radius = a.composition["hole_radius_mm"]
                bearing = (
                    Point(x, y)
                    .buffer(radius, quad_segs=24)
                    .difference(Point(x, y).buffer(hole_radius + 0.05, quad_segs=24))
                )
                for pid in m["plate_ids"]:
                    plate = by_id[pid]
                    shape = xy_footprint(a.definition_for(plate), plate.transform)
                    if bearing.difference(shape).area > 1e-4:
                        issues.append(
                            Issue("error", "root_bearing", f"{pid}: insufficient washer bearing")
                        )
                # Conservative entire shaft/washer corridor; own compression column is intentional.
                cap_top = instance_bounds(a.definition_for(cap), cap.transform)[1, 2]
                for obstacle in a.instances:
                    if obstacle.module_id in (m["module_id"], "backing"):
                        continue
                    bounds = instance_bounds(a.definition_for(obstacle), obstacle.transform)
                    footprint = xy_footprint(a.definition_for(obstacle), obstacle.transform)
                    if bounds[0, 2] < cap_top + a.composition[
                        "hardware_outward_mm"
                    ] and footprint.intersects(Point(x, y).buffer(radius)):
                        issues.append(
                            Issue(
                                "error",
                                "bolt_corridor",
                                f"{m['module_id']}: root hardware crosses {obstacle.instance_id}",
                            )
                        )
        except (KeyError, ValueError) as exc:
            issues.append(Issue("error", "creature_inventory", f"incomplete assembly: {exc}"))
    return ValidationReport(tuple(issues))


def assemble_creature(c, inventory=None):
    checked = validate_config(c)
    if not checked.digital_valid:
        raise ValueError("; ".join(i.message for i in checked.issues))
    if inventory is None:
        bundle, layout = generate_creature(c)
        definitions = bundle.definitions
        templates = bundle.instances
        layout = json.loads(json.dumps(layout))
    else:
        inventory = Inventory.from_dict(inventory.to_dict())
        definitions = inventory.definitions
        layout = json.loads(json.dumps(inventory.layout))
        if not isinstance(layout, dict) or layout.get("family") != "creature-mask-v1":
            raise ValueError("inventory requires creature family")
        saved = layout.pop("fingerprint", None)
        if digest(layout) != saved:
            raise ValueError("stale inventory layout fingerprint")
        layout["fingerprint"] = saved
        if layout["manufacturing_request"] != request_signature(c):
            raise ValueError("manufactured geometry request differs; requires new cuts")
        templates = tuple(PartInstance(**i) for i in layout["templates"])
        physical = {i.instance_id: i for i in inventory.instances}
        if set(physical) != {i.instance_id for i in templates}:
            raise ValueError("missing or extra inventory parts")
        for i in templates:
            actual = physical[i.instance_id]
            if (actual.definition_id, actual.revision, actual.role) != (
                i.definition_id,
                i.revision,
                i.role,
            ):
                raise ValueError("stale inventory revision or role")
    moves = {}
    for m in layout["modules"]:
        name = m["module_id"]
        moves[name] = (
            ((-25 if "left" in name else 25), 50)
            if c.creature.posture == "raised_crown" and name.startswith("crown")
            else (0, 0)
        )
    instances = []
    for i in templates:
        pose = np.array(i.transform)
        dx, dy = moves.get(i.module_id, (0, 0))
        pose[:2, 3] += (dx, dy)
        instances.append(replace(i, transform=pose))
    metadata = {
        "family": "creature-mask-v1",
        "posture": c.creature.posture,
        "modules": json.loads(json.dumps(layout["modules"])),
        "removal_order": layout["removal_order"],
        "washer_radius_mm": c.mounting.washer_radius_mm,
        "hole_radius_mm": c.grid.hole_diameter_mm / 2,
        "hardware_outward_mm": c.mounting.hardware_outward_mm,
        "interchangeability": "complete crown modules move by prescribed grid offset; unique armour plates do not interchange",
    }
    connections = []
    mounts = []
    hardware = []
    for m in metadata["modules"]:
        dx, dy = moves[m["module_id"]]
        roots = [(x + dx, y + dy) for x, y in m["roots"]]
        m["placed_roots"] = roots
        holes = match_root_pattern(c, roots)
        for h in holes:
            mounts.append((m["module_id"], h.point_id, h.x_mm, h.y_mm))
            r = c.mounting.washer_radius_mm
            hardware.append(
                (
                    m["module_id"],
                    h.x_mm - r,
                    h.y_mm - r,
                    0,
                    h.x_mm + r,
                    h.y_mm + r,
                    m["cap_z_mm"] + c.material.measured_mm + c.mounting.hardware_outward_mm,
                )
            )
            connections.append(
                Connection(m["cap_id"], "backplate", "creature-root-clamp-v1", h.point_id)
            )
        for j, kid in enumerate(m["key_ids"]):
            for pid in m["plate_ids"][:-1]:
                connections.append(Connection(kid, pid, "creature-register-v1", f"key-{j}"))
        for i in instances:
            if i.module_id == m["module_id"] and i.role == "spacer":
                connections.append(
                    Connection(i.instance_id, m["cap_id"], "creature-root-clamp-v1", "root-pair")
                )
    paths = tuple(
        (m["module_id"], (0, 0, 1), tuple(range(0, 241, 12))) for m in metadata["modules"]
    )
    visible_parts = [i for i in instances if i.role in ("armour", "cap")]
    a = Assembly(
        tuple(definitions),
        tuple(instances),
        tuple(connections),
        tuple(mounts),
        tuple(
            (i.instance_id, j / len(visible_parts), (j + 1) / len(visible_parts))
            for j, i in enumerate(visible_parts)
        ),
        (c.envelope.width_mm, c.envelope.height_mm, c.envelope.depth_mm),
        tuple(hardware),
        paths,
        metadata,
    )
    report = validate_assembly(a)
    own = verify_creature(a)
    issues = list(report.issues) + list(own.issues)
    dependencies = {
        i.part_ids[0]: list(i.part_ids[1:])
        for i in report.issues
        if i.code == "extraction_dependency"
    }
    removed = set()
    for name in metadata["removal_order"]:
        if set(dependencies.get(name, ())) - removed:
            issues.append(Issue("error", "removal_order", f"{name}: invalid removal order"))
        removed.add(name)
    metadata["sampled_extraction_dependencies"] = dependencies
    # Common clear eye aperture through every depth layer, including roots/backing.
    from .geometry.creature_profiles import eye_voids

    eyes = [
        affinity.scale(p, xfact=c.creature.scale, yfact=c.creature.scale, origin=(0, 0))
        for p in eye_voids(0.75)
    ]
    for eye in eyes:
        for i in instances:
            if eye.intersection(xy_footprint(a.definition_for(i), i.transform)).area > 1e-5:
                issues.append(
                    Issue("error", "eye_channel", f"{i.instance_id}: eye channel obstruction")
                )
    metadata["eye_aperture_area_mm2"] = sum(p.area for p in eyes)
    a = replace(a, composition=metadata)
    report = replace(report, issues=tuple(issues))
    return BuildResult(
        a,
        tuple(definitions),
        (
            "Creature clamp/slot family: physical fit, stiffness, bolts and handling NOT RUN.",
            "Support the complete module in a tray before releasing root clamps.",
            "Browser/Wire/Arena/projector runtime NOT RUN.",
        ),
        {
            "generator": "parametric-deco/0.1.0",
            "mode": "existing_inventory" if inventory else "generate_new",
            "config": c.to_dict(),
            "config_hash": digest(c.to_dict()),
            "units": "mm",
            "kerf_compensation": "laser_software_only",
        },
        report,
        Inventory(tuple(definitions), tuple(instances), layout),
    )
