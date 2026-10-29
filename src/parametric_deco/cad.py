"""The only build123d boundary. Planar finished contours remain authoritative."""

from functools import lru_cache

import numpy as np
import trimesh
from build123d import Face, Location, Wire, export_step, extrude
from shapely.geometry import Polygon, LineString, box
from shapely import affinity


def extrude_polygon(polygon: Polygon, thickness_mm: float):
    if not polygon.is_valid or polygon.is_empty or thickness_mm <= 0:
        raise ValueError("invalid contour or thickness_mm")
    outer = Wire.make_polygon([(x, y, 0) for x, y in polygon.exterior.coords])
    holes = [Wire.make_polygon([(x, y, 0) for x, y in ring.coords]) for ring in polygon.interiors]
    return extrude(Face(outer, holes), amount=thickness_mm, dir=(0, 0, 1))


@lru_cache(maxsize=128)
def solid_for(definition):
    return extrude_polygon(definition.polygon, definition.thickness_mm)


def placed_solid(definition, transform):
    from OCP.gp import gp_Trsf

    trsf = gp_Trsf()
    a = np.asarray(transform, dtype=float)
    trsf.SetValues(*a[:3, :].ravel().tolist())
    return solid_for(definition).moved(Location(trsf))


def mesh_for(definition):
    vertices, triangles = solid_for(definition).tessellate(0.15, 0.15)
    return trimesh.Trimesh(vertices=[tuple(v) for v in vertices], faces=triangles, process=True)


def overlap_volume(a, ta, b, tb):
    ta, tb = np.asarray(ta), np.asarray(tb)
    # Parallel XY plates are exact prisms. Compute the same intersection without
    # asking the solid kernel to repeatedly intersect hundreds of cut edges.
    if all(np.allclose(t[2, :3], (0, 0, 1), atol=1e-12) for t in (ta, tb)):
        height = min(ta[2, 3] + a.thickness_mm, tb[2, 3] + b.thickness_mm) - max(ta[2, 3], tb[2, 3])
        if height <= 0:
            return 0.0
        polygons = [
            affinity.affine_transform(
                p.polygon, [t[0, 0], t[0, 1], t[1, 0], t[1, 1], t[0, 3], t[1, 3]]
            )
            for p, t in ((a, ta), (b, tb))
        ]
        return polygons[0].intersection(polygons[1]).area * height
    for web, tw, plate, tp in ((a, ta, b, tb), (b, tb, a, ta)):
        exact = _trestle_overlap(web, tw, plate, tp)
        if exact is not None:
            return exact
    return _kernel_overlap(a, tuple(map(tuple, ta)), b, tuple(map(tuple, tb)))


def _trestle_overlap(web, tw, plate, tp):
    """Exact slice integration for rectilinear upright trestles against XY plates.

    Fall back to OCP for every other orientation/profile. No mesh approximation.
    """
    if not (
        web.definition_id.startswith("flow-")
        and web.kind == "register"
        and np.allclose(tw[2, :3], (0, 1, 0), atol=1e-12)
        and np.allclose(tp[2, :3], (0, 0, 1), atol=1e-12)
    ):
        return None
    poly = web.polygon
    rings = [poly.exterior, *poly.interiors]
    for ring in rings:
        for p, q in zip(ring.coords, list(ring.coords)[1:]):
            if abs(p[0] - q[0]) > 1e-9 and abs(p[1] - q[1]) > 1e-9:
                return None
    lo = max(poly.bounds[1], tp[2, 3] - tw[2, 3])
    hi = min(poly.bounds[3], tp[2, 3] + plate.thickness_mm - tw[2, 3])
    if hi <= lo:
        return 0.0
    levels = sorted({lo, hi, *(y for ring in rings for x, y in ring.coords if lo < y < hi)})
    target = affinity.affine_transform(
        plate.polygon, [tp[0, 0], tp[0, 1], tp[1, 0], tp[1, 1], tp[0, 3], tp[1, 3]]
    )
    total = 0.0
    for lower, upper in zip(levels, levels[1:]):
        mid = (lower + upper) / 2
        section = poly.intersection(
            LineString([(poly.bounds[0] - 1, mid), (poly.bounds[2] + 1, mid)])
        )
        for line in section.geoms if hasattr(section, "geoms") else [section]:
            if line.is_empty or line.geom_type != "LineString":
                continue
            lowx, _, highx, _ = line.bounds
            strip = affinity.affine_transform(
                box(lowx, 0, highx, web.thickness_mm),
                [tw[0, 0], tw[0, 2], tw[1, 0], tw[1, 2], tw[0, 3], tw[1, 3]],
            )
            total += strip.intersection(target).area * (upper - lower)
    return total


@lru_cache(maxsize=32768)
def _kernel_overlap(a, ta, b, tb):
    common = placed_solid(a, ta) & placed_solid(b, tb)
    return sum(s.volume for s in common.solids()) if common else 0.0


__all__ = [
    "extrude_polygon",
    "export_step",
    "solid_for",
    "placed_solid",
    "mesh_for",
    "overlap_volume",
]
