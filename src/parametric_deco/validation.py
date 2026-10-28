"""Solid interference and bounded, explicitly non-exhaustive motion checks."""

from itertools import combinations

import numpy as np

from .cad import overlap_volume
from .model import Issue, ValidationReport


def instance_bounds(definition, transform):
    coordinates = [(*p, z, 1) for z in (0, definition.thickness_mm) for p in definition.outer]
    vertices = (np.asarray(transform) @ np.asarray(coordinates).T).T[:, :3]
    return np.array((vertices.min(axis=0), vertices.max(axis=0)))


def boxes_overlap(a, b, tolerance=1e-7):
    return bool(np.all(np.minimum(a[1], b[1]) - np.maximum(a[0], b[0]) > tolerance))


def validate_assembly(assembly):
    issues = []
    ids = [i.instance_id for i in assembly.instances]
    if len(ids) != len(set(ids)):
        issues.append(
            Issue("error", "duplicate_instance", "duplicate physical instance assignment")
        )
    definitions, bounds = {}, {}
    for inst in assembly.instances:
        try:
            definition = assembly.definition_for(inst)
        except ValueError as e:
            issues.append(Issue("error", "unknown_revision", str(e), (inst.instance_id,)))
            continue
        definitions[inst.instance_id] = definition
        bounds[inst.instance_id] = instance_bounds(definition, inst.transform)
    w, h, d = assembly.envelope_mm
    for name, b in list(bounds.items()) + [
        (f"hardware-{index}", np.array((v[1:4], v[4:7])))
        for index, v in enumerate(assembly.hardware_bounds)
    ]:
        if np.any(b[0] < np.array((-w / 2, -h / 2, 0)) - 1e-6) or np.any(
            b[1] > np.array((w / 2, h / 2, d)) + 1e-6
        ):
            issues.append(Issue("error", "envelope", f"{name} exceeds total envelope", (name,)))
    for a, b in combinations(assembly.instances, 2):
        if a.instance_id not in bounds or b.instance_id not in bounds:
            continue
        if boxes_overlap(bounds[a.instance_id], bounds[b.instance_id]):
            volume = overlap_volume(
                definitions[a.instance_id], a.transform, definitions[b.instance_id], b.transform
            )
            if volume > 1e-5:
                issues.append(
                    Issue(
                        "error",
                        "interference",
                        f"{volume:.6g} mm³ unwanted overlap",
                        (a.instance_id, b.instance_id),
                    )
                )
    # Candidate family requires immediate +Z restraint by a real closure, including
    # loaded assemblies whose inventory compatibility checks may have been bypassed.
    for rib in (i for i in assembly.instances if i.role == "rib" and i.instance_id in definitions):
        covers = [
            i
            for i in assembly.instances
            if i.role == "closure" and i.module_id == rib.module_id and i.instance_id in definitions
        ]
        transform = np.array(rib.transform)
        transform[2, 3] += 1.0
        if (
            len(covers) != 1
            or overlap_volume(
                definitions[rib.instance_id],
                transform,
                definitions[covers[0].instance_id],
                covers[0].transform,
            )
            <= 1e-5
        ):
            issues.append(
                Issue(
                    "error",
                    "closure_retention",
                    "rib +1 mm withdrawal is not blocked by its manufactured closure",
                    (rib.instance_id,),
                )
            )
    # Roots need a known connection endpoint, station and family, even for loaded assemblies.
    by_id = {i.instance_id: i for i in assembly.instances}
    for connection in assembly.connections:
        if connection.a not in by_id or connection.b not in by_id:
            issues.append(Issue("error", "connection", "unknown connection endpoint"))
            continue
        if connection.family != "upper-closure-v1":
            station_ids = {s.station_id for s in definitions[connection.b].interfaces}
            if connection.station_id not in station_ids:
                issues.append(Issue("error", "station", "unavailable station", (connection.a,)))
    # Root bolts are removed before these checks. Backing is behind extraction direction.
    for module_id, direction, steps in assembly.extraction_paths:
        blocked = set()
        movers = [i for i in assembly.instances if i.module_id == module_id]
        obstacles = [i for i in assembly.instances if i.module_id not in (module_id, "backing")]
        for mover in movers:
            for obstacle in obstacles:
                for distance in steps:
                    transform = np.array(mover.transform)
                    transform[:3, 3] += np.array(direction) * distance
                    bb = bounds[mover.instance_id] + np.array(direction) * distance
                    if (
                        boxes_overlap(bb, bounds[obstacle.instance_id])
                        and overlap_volume(
                            definitions[mover.instance_id],
                            transform,
                            definitions[obstacle.instance_id],
                            obstacle.transform,
                        )
                        > 1e-5
                    ):
                        blocked.add(obstacle.module_id)
                        break
        if blocked:
            issues.append(
                Issue(
                    "warning",
                    "extraction_dependency",
                    f"{module_id}: remove {', '.join(sorted(blocked))} first (sampled +Z path)",
                    (module_id,),
                )
            )
    return ValidationReport(tuple(issues))
