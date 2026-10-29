"""Sample broad faces against actual extruded planar parts from a frontal projector.

Ray/slab clipping includes contour edges and holes. Finite surface samples estimate
visibility; this is not a calibrated projection or continuous illumination proof.
"""

import numpy as np
from shapely import contains_xy, linestrings, intersects


def projection_visibility(assembly, projector_mm=(0, 0, 2000), samples=20):
    if type(samples) is not int or not 4 <= samples <= 100:
        raise ValueError("samples must be integer 4..100")
    source = np.asarray(projector_mm, dtype=float)
    if source.shape != (3,) or not np.isfinite(source).all():
        raise ValueError("projector must be a finite XYZ point")
    obstacles = []
    for i in assembly.instances:
        part = assembly.definition_for(i)
        pose = np.array(i.transform)
        obstacles.append((i.instance_id, part, pose))
    surfaces = []
    for i in assembly.instances:
        if i.role not in ("armour", "cap"):
            continue
        part = assembly.definition_for(i)
        p = part.polygon
        pose = np.array(i.transform)
        x0, y0, x1, y1 = p.bounds
        x, y = np.meshgrid(
            np.linspace(x0, x1, samples + 2)[1:-1], np.linspace(y0, y1, samples + 2)[1:-1]
        )
        keep = contains_xy(p, x, y)
        x = x[keep]
        y = y[keep]
        points = (
            np.column_stack((x, y, np.full(len(x), part.thickness_mm))) @ pose[:3, :3].T
            + pose[:3, 3]
        )
        visible = np.ones(len(points), dtype=bool)
        blockers = []
        if np.dot(pose[:3, 2], source - pose[:3, 3]) <= 0:
            visible[:] = False
        for oid, other, other_pose in obstacles:
            if oid == i.instance_id or not visible.any():
                continue
            # Local rigid inverse; intersect each ray with the complete extrusion slab.
            starts = (points - other_pose[:3, 3]) @ other_pose[:3, :3]
            endpoint = (source - other_pose[:3, 3]) @ other_pose[:3, :3]
            delta = endpoint - starts
            dz = delta[:, 2]
            parallel = np.abs(dz) < 1e-12
            safe = np.where(parallel, 1, dz)
            a = -starts[:, 2] / safe
            b = (other.thickness_mm - starts[:, 2]) / safe
            entry = np.maximum(np.minimum(a, b), 1e-7)
            leave = np.minimum(np.maximum(a, b), 1 - 1e-7)
            inside = (starts[:, 2] > 0) & (starts[:, 2] < other.thickness_mm)
            entry = np.where(parallel & inside, 1e-7, entry)
            leave = np.where(parallel & inside, 1 - 1e-7, leave)
            active = (leave >= entry) & visible & (~parallel | inside)
            indices = np.flatnonzero(active)
            if not len(indices):
                continue
            begin = starts[indices, :2] + delta[indices, :2] * entry[indices, None]
            end = starts[indices, :2] + delta[indices, :2] * leave[indices, None]
            hit = intersects(other.polygon, linestrings(np.stack((begin, end), axis=1)))
            if np.any(hit):
                visible[indices[hit]] = False
                blockers.append(oid)
        fraction = float(visible.mean()) if len(points) else 0.0
        surfaces.append(
            {
                "surface_id": i.instance_id + "--front",
                "sample_count": len(points),
                "visible_fraction": fraction,
                "blocker_ids": blockers,
            }
        )
    return {
        "projector_mm": source.tolist(),
        "scope": "sampled broad-face targets; ray intersection with all actual planar extrusions; no runtime calibration",
        "samples_per_bbox_axis": samples,
        "surfaces": surfaces,
        "recommended_surface_ids": sorted(
            s["surface_id"] for s in surfaces if s["visible_fraction"] > 0
        ),
    }
