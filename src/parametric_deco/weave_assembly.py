"""Saved radial inventory placement and evidence for the curved module family."""

from dataclasses import asdict, replace
from functools import lru_cache
import json
import math

import numpy as np
from shapely import affinity
from shapely.geometry import LineString, MultiPoint, Point

from .cad import overlap_volume
from .geometry.backplate import generate_backplate, match_root_pattern
from .geometry.weave import generate_weave, manufacturing_request
from .model import (
    Assembly,
    BuildResult,
    Connection,
    Inventory,
    Issue,
    PartInstance,
    ValidationReport,
    digest,
)
from .validation import validate_assembly


def _design_geometry(design):
    return {k: v for k, v in design.items() if k not in ("rotation_deg", "rib_permutation")}


def _projection(part, instance):
    t = np.array(instance.transform)
    if instance.role == "rib":
        vertices = np.array([(*v, z, 1) for v in part.outer for z in (0, part.thickness_mm)])
        return MultiPoint((vertices @ t.T)[:, :2]).convex_hull
    return affinity.affine_transform(
        part.polygon, [t[0, 0], t[0, 1], t[1, 0], t[1, 1], t[0, 3], t[1, 3]]
    )


def weave_evidence(assembly, report):
    metadata = json.loads(json.dumps(assembly.composition))
    central_ribs = {
        i.module_id: i for i in assembly.instances if i.role == "rib" and i.station_id == "s4"
    }
    issues = []
    opening = metadata["design"]["opening_radius_mm"]
    clearance = min(
        _projection(assembly.definition_for(i), i).distance(Point(0, 0)) - opening
        for i in assembly.instances
    )
    metadata["opening_clearance_mm"] = clearance
    if clearance < -1e-5:
        issues.append(
            Issue("error", "central_opening", "manufactured geometry intrudes into opening")
        )
    crossings = []
    for crossing in metadata["crossings"]:
        over = central_ribs[crossing["over_module"]]
        under = central_ribs[crossing["under_module"]]
        intervals = []
        for instance in (over, under):
            part = assembly.definition_for(instance)
            line = part.polygon.intersection(LineString(((10, -1), (10, 300))))
            pieces = getattr(line, "geoms", (line,))
            intervals.append(
                (
                    min(g.bounds[1] for g in pieces) + instance.transform[2][3],
                    max(g.bounds[3] for g in pieces) + instance.transform[2][3],
                )
            )
        gap = intervals[0][0] - intervals[1][1]
        crossings.append({**crossing, "clearance_mm": gap})
        if gap < 10:
            issues.append(
                Issue("error", "crossing_clearance", f"crossing clearance only {gap:g} mm")
            )
    metadata["crossings"] = crossings
    metadata["minimum_crossing_clearance_mm"] = min(x["clearance_mm"] for x in crossings)
    dependencies = {
        issue.part_ids[0]: list(issue.part_ids[1:])
        for issue in report.issues
        if issue.code == "extraction_dependency"
    }
    removed = set()
    for module in metadata["removal_order"]:
        blockers = set(dependencies.get(module, ())) - removed
        if blockers:
            issues.append(
                Issue("error", "removal_order", f"{module} blocked by {sorted(blockers)}")
            )
        removed.add(module)
    metadata["sampled_extraction_dependencies"] = dependencies
    metadata["motion_scope"] = "sampled straight +Z module extraction; radial bench rib paths"
    return metadata, tuple(issues)


def validate_weave(assembly):
    report = validate_assembly(assembly)
    _, issues = weave_evidence(assembly, report)
    return replace(report, issues=report.issues + issues)


@lru_cache(maxsize=8)
def _radial_joint_report(assembly_json):
    assembly = Assembly.from_dict(json.loads(assembly_json))
    issues = []
    for rib in (i for i in assembly.instances if i.role == "rib"):
        part = assembly.definition_for(rib)
        spines = [
            i for i in assembly.instances if i.module_id == rib.module_id and i.role == "spine"
        ]
        cover = next(
            i for i in assembly.instances if i.module_id == rib.module_id and i.role == "closure"
        )
        direction = -np.array(rib.transform)[:3, 0]
        for distance in (0, 10, 40, 80):
            pose = np.array(rib.transform)
            pose[:3, 3] += direction * distance
            if any(
                overlap_volume(part, pose, assembly.definition_for(spine), spine.transform) > 1e-5
                for spine in spines
            ):
                issues.append(
                    Issue(
                        "error",
                        "radial_insertion",
                        f"{rib.instance_id} collides on open-rail radial path",
                    )
                )
                break
        pose = np.array(rib.transform)
        pose[:3, 3] += direction
        if overlap_volume(part, pose, assembly.definition_for(cover), cover.transform) <= 1e-5:
            issues.append(Issue("error", "radial_capture", f"{rib.instance_id} is not captured"))
    return ValidationReport(tuple(issues))


def verify_radial_joints(assembly):
    return _radial_joint_report(json.dumps(assembly.to_dict(), sort_keys=True))


def assemble_weave(config, inventory=None):
    from .config import validate_config

    configuration = validate_config(config)
    if not configuration.digital_valid:
        raise ValueError("; ".join(i.message for i in configuration.issues))
    if inventory is None:
        bundle, layout = generate_weave(config)
        backing = generate_backplate(config).definitions[0]
        definitions = (backing, *bundle.definitions)
        backing_instance = PartInstance(
            "backplate",
            backing.definition_id,
            backing.revision,
            (
                (1, 0, 0, 0),
                (0, 1, 0, 0),
                (0, 0, 1, config.mounting.rear_clearance_mm),
                (0, 0, 0, 1),
            ),
            role="backplate",
        )
        templates = (backing_instance, *bundle.instances)
        layout = json.loads(json.dumps(layout))
        layout["templates"] = [asdict(i) for i in templates]
        layout["fingerprint"] = digest(layout)
    else:
        inventory = Inventory.from_dict(inventory.to_dict())
        layout = json.loads(json.dumps(inventory.layout))
        if not isinstance(layout, dict) or layout.get("family") != "radial-weave-v1":
            raise ValueError("inventory has no radial-weave placement template")
        fingerprint = layout.pop("fingerprint", None)
        if digest(layout) != fingerprint:
            raise ValueError("stale inventory layout fingerprint")
        layout["fingerprint"] = fingerprint
        if _design_geometry(layout["design"]) != _design_geometry(asdict(config.parameters)):
            raise ValueError(
                "requested geometry differs from manufactured inventory; generate new cuts"
            )
        if layout.get("manufacturing_request") != manufacturing_request(config):
            raise ValueError("requested stock/backing/mounting differs from manufactured inventory")
        templates = tuple(PartInstance(**i) for i in layout["templates"])
        physical = {i.instance_id: i for i in inventory.instances}
        if len(physical) != len(templates) or set(physical) != {i.instance_id for i in templates}:
            raise ValueError("missing or extra physical inventory instances for saved layout")
        for i in templates:
            actual = physical[i.instance_id]
            if (actual.definition_id, actual.revision, actual.role) != (
                i.definition_id,
                i.revision,
                i.role,
            ):
                raise ValueError(f"{i.instance_id}: stale inventory/template revision or role")
        definitions = inventory.definitions
    by_id = {i.instance_id: i for i in templates}
    relative_rotation = config.parameters.rotation_deg - layout.get("template_rotation_deg", 0)
    theta = math.radians(relative_rotation)
    co, si = math.cos(theta), math.sin(theta)
    rotation = np.array(((co, -si, 0, 0), (si, co, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
    permutation = config.parameters.rib_permutation
    assignment = {}
    for module in layout["modules"]:
        for station, index in enumerate(permutation):
            assignment[module["rib_ids"][index]] = (
                module["station_transforms"][station],
                f"s{station}",
            )
    instances = []
    for i in templates:
        if i.role == "backplate":
            instances.append(i)
            continue
        pose, station = assignment.get(i.instance_id, (i.transform, i.station_id))
        instances.append(replace(i, transform=rotation @ np.array(pose), station_id=station))
    connections = []
    path = []
    for module in layout["modules"]:
        for station, index in enumerate(permutation):
            name = module["rib_ids"][index]
            rib = by_id[name]
            part = next(
                d
                for d in definitions
                if (d.definition_id, d.revision) == (rib.definition_id, rib.revision)
            )
            for spine in module["spine_ids"]:
                connections.append(
                    Connection(name, spine, part.interfaces[0].family, f"s{station}")
                )
            connections.append(Connection(name, module["closure_id"], "radial-capture-v1", "rail"))
            path.append(name)
    mounts = []
    hardware = []
    for module, _, x, y in layout["mounting_grid"]:
        point = rotation @ np.array((x, y, 0, 1))
        hole = match_root_pattern(config, (point[:2],))[0]
        mounts.append((module, hole.point_id, float(point[0]), float(point[1])))
    for module, x0, y0, z0, x1, y1, z1 in layout["hardware_bounds"]:
        corners = (
            np.array([(x, y, z, 1) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])
            @ rotation.T
        )
        hardware.append((module, *corners[:, :3].min(axis=0), *corners[:, :3].max(axis=0)))
    metadata = {k: layout[k] for k in ("family", "design", "modules", "crossings", "removal_order")}
    metadata = json.loads(json.dumps(metadata))
    metadata["rotation_deg"] = config.parameters.rotation_deg
    for crossing in metadata["crossings"]:
        crossing["theta_deg"] = (crossing["theta_deg"] + relative_rotation) % 360
        angle = math.radians(crossing["theta_deg"])
        crossing["position_mm"] = [
            config.parameters.radius_mm * math.cos(angle),
            config.parameters.radius_mm * math.sin(angle),
        ]
    env = config.envelope
    assembly = Assembly(
        tuple(definitions),
        tuple(instances),
        tuple(connections),
        tuple(mounts),
        tuple(
            (name, index / len(path), (index + 1) / len(path)) for index, name in enumerate(path)
        ),
        (env.width_mm, env.height_mm, env.depth_mm),
        tuple(hardware),
        tuple(
            (m["module_id"], (0.0, 0.0, 1.0), tuple(range(0, 241, 10))) for m in layout["modules"]
        ),
        metadata,
    )
    report = validate_assembly(assembly)
    metadata, evidence_issues = weave_evidence(assembly, report)
    assembly = replace(assembly, composition=metadata)
    report = replace(report, issues=report.issues + evidence_issues)
    return BuildResult(
        assembly,
        tuple(definitions),
        (
            "Radial-slide joint family: physical fit/load/handling NOT RUN; support required.",
            "Remove high modules first, then low; radial rib reconfiguration only on a bench.",
            "Wire/Arena and actual browser rendering NOT RUN.",
        ),
        {
            "generator": "parametric-deco/0.1.0",
            "mode": "existing_inventory" if inventory else "generate_new",
            "config": config.to_dict(),
            "config_hash": digest(config.to_dict()),
            "units": "mm",
            "kerf_compensation": "laser_software_only",
        },
        report,
        Inventory(tuple(definitions), tuple(instances), layout),
    )
