"""Physical symmetry groups, exact lattice orbits and part correspondences."""
import math
import re
import numpy as np


def kind(config):
    if config.style == 'laminar':
        if config.parameters.symmetry == 'rotational':
            return 'C3'
        if config.parameters.symmetry == 'bilateral':
            return 'mirror-X'
    if config.style == 'layered-creature':
        return 'mirror-X'
    return 'none'


def matrices(config):
    mode = kind(config)
    if mode == 'C3':
        return (np.eye(2), np.array(((-.5, -math.sqrt(3)/2), (math.sqrt(3)/2, -.5))),
                np.array(((-.5, math.sqrt(3)/2), (-math.sqrt(3)/2, -.5))))
    if mode == 'mirror-X':
        return (np.eye(2), np.diag((-1., 1.)))
    return (np.eye(2),)


def mapped_id(identifier, config, index):
    if not index:
        return identifier
    if config.style == 'layered-creature':
        return identifier.replace('left', 'TEMP').replace('right', 'left').replace('TEMP', 'right')
    if config.style == 'laminar':
        match = re.match(r'^(.*-)(\d+)(-plate)?$', identifier)
        if not match:
            return identifier
        start, number, suffix = match.groups()
        n = int(number)
        n = (n + index * (config.parameters.focal_count // 3)) % config.parameters.focal_count if kind(config) == 'C3' else n + (1 if n % 2 == 0 else -1)
        return start + str(n) + (suffix or '')
    return identifier


def canonical_id(identifier, config):
    if config.style == 'layered-creature':
        return identifier.replace('right', 'left')
    if config.style == 'laminar' and kind(config) != 'none':
        match = re.match(r'^(.*-)(\d+)(-plate)?$', identifier)
        if match:
            start, number, suffix = match.groups()
            n = int(number)
            n = n % (config.parameters.focal_count // 3) if kind(config) == 'C3' else n - n % 2
            return start + str(n) + (suffix or '')
    return identifier


def verify_symmetry(assembly, config):
    """Compare actual extruded surfaces and clamp stacks under each group action.

    No recorded symmetry/purpose flags are accepted as evidence. Planar material,
    holes, local extrusion planes, thickness, placement and stack membership must
    all have real counterparts. The common octagonal board is deliberately not C3.
    """
    from shapely import affinity
    from ..model import Issue
    if kind(config) == 'none':
        return ()
    parts = [p for p in assembly.instances if p.role != 'backplate']
    issues = []
    for matrix in matrices(config)[1:]:
        group = np.eye(4)
        group[:2, :2] = matrix
        for part in parts:
            definition = assembly.definition_for(part)
            counterpart = False
            module = mapped_id(part.module_id, config, 1 if kind(config) == 'mirror-X' else
                               (1 if matrix[1, 0] > 0 else 2))
            for other in parts:
                if other.role != part.role or other.module_id != module:
                    continue
                target = assembly.definition_for(other)
                rel = np.linalg.inv(np.array(other.transform)) @ group @ np.array(part.transform)
                if max(abs(rel[2, 0]), abs(rel[2, 1]), abs(rel[0, 2]), abs(rel[1, 2])) > 1e-7:
                    continue
                ends = sorted((rel[2, 3], rel[2, 3] + rel[2, 2] * definition.thickness_mm))
                if not np.allclose(ends, (0, target.thickness_mm), atol=1e-7, rtol=0):
                    continue
                shape = affinity.affine_transform(definition.polygon,
                    [rel[0, 0], rel[0, 1], rel[1, 0], rel[1, 1], rel[0, 3], rel[1, 3]])
                if shape.symmetric_difference(target.polygon).area < 1e-6:
                    counterpart = True
                    break
            if not counterpart:
                issues.append(Issue('error', 'material_symmetry', 'actual extruded material has no symmetry counterpart', (part.instance_id,)))
        # Original root/clip fasteners retain their documented simplified
        # envelopes; those envelopes must obey the same reflection/orbit too.
        for record in assembly.hardware_bounds:
            label, x0, y0, z0, x1, y1, z1 = record
            corners = np.array(((x0, y0), (x0, y1), (x1, y0), (x1, y1))) @ matrix.T
            lo, hi = corners.min(axis=0), corners.max(axis=0)
            if not any(np.allclose((r[1], r[2], r[3], r[4], r[5], r[6]),
                                  (*lo, z0, *hi, z1), atol=1e-7, rtol=0)
                       for r in assembly.hardware_bounds):
                issues.append(Issue('error', 'hardware_symmetry', 'original hardware envelope has no counterpart', (str(label),)))
        stations = (assembly.composition or {}).get('end_supports', {}).get('stations', [])
        for station in stations:
            xy = matrix @ np.array(station['xy'])
            mapped = {mapped_id(p, config, 1 if kind(config) == 'mirror-X' else
                       (1 if matrix[1, 0] > 0 else 2)) for p in station['plate_ids']}
            if not any(np.linalg.norm(xy - np.array(s['xy'])) < 1e-7
                       and mapped == set(s['plate_ids']) for s in stations):
                issues.append(Issue('error', 'support_symmetry', 'clamped layers or axes have no complete symmetry orbit', (station['id'],)))
    return tuple(issues)
