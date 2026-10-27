"""The only build123d boundary. Planar finished contours remain authoritative."""

from functools import lru_cache

import numpy as np
import trimesh
from build123d import Face, Location, Wire, export_step, extrude
from shapely.geometry import Polygon


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
