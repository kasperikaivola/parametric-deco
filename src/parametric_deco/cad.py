"""The only build123d boundary. Planar finished contours remain authoritative."""

from functools import lru_cache

import numpy as np
import trimesh
from build123d import Face, Location, Wire, export_step, extrude
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon
from OCP.gp import gp_Pnt
from shapely.geometry import Polygon, LineString, box
from shapely import affinity


def _polygon_wire(coords):
    """Same closed wire as Wire.make_polygon, without a Python Vector per vertex."""
    builder = BRepBuilderAPI_MakePolygon()
    points = [(float(x), float(y)) for x, y in coords]
    if points and (points[0][0] - points[-1][0]) ** 2 + (points[0][1] - points[-1][1]) ** 2 > 1e-12:
        points.append(points[0])
    for x, y in points:
        builder.Add(gp_Pnt(x, y, 0.0))
    return Wire(builder.Wire())


def extrude_polygon(polygon: Polygon, thickness_mm: float):
    if not polygon.is_valid or polygon.is_empty or thickness_mm <= 0:
        raise ValueError("invalid contour or thickness_mm")
    outer = _polygon_wire(polygon.exterior.coords)
    holes = [_polygon_wire(ring.coords) for ring in polygon.interiors]
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


@lru_cache(maxsize=1024)
def mesh_for(definition):
    # All manufactured geometry is an exact planar polygon extrusion. Triangulate
    # those authoritative contours directly, once, rather than retessellating an
    # identical OCP extrusion for every view/export (especially hundreds of bores).
    # The solid kernel remains the independent collision/STEP boundary.
    return trimesh.creation.extrude_polygon(
        definition.polygon, definition.thickness_mm, engine="earcut"
    )


def _piece_polygons(geom):
    if geom.is_empty:
        return
    if geom.geom_type == "Polygon":
        yield geom
    elif hasattr(geom, "geoms"):
        for part in geom.geoms:
            yield from _piece_polygons(part)


def _ring_edges(geom):
    """Non-vertical ring edges as rows (x1, y1, x2, y2), plus every vertex x."""
    chunks = []
    xs = []
    for poly in _piece_polygons(geom):
        for ring in (poly.exterior, *poly.interiors):
            coords = np.asarray(ring.coords, dtype=float)
            if len(coords) < 2:
                continue
            xs.append(coords[:, 0])
            start, end = coords[:-1, :2], coords[1:, :2]
            chunks.append(np.concatenate((start, end), axis=1))
    if not chunks:
        return np.empty((0, 4)), np.empty(0)
    edges = np.vstack(chunks)
    return edges[edges[:, 0] != edges[:, 2]], np.concatenate(xs)


def _scan_chords(edges, xs):
    """Vertical chord length at x values that sit strictly between vertices.

    A half-open crossing counts each vertex once. Sampling on a vertex is not
    safe: a vertical edge makes that single x differ from both side limits, and
    the spike has no area. An odd crossing count is not a simple section.
    """
    xs = np.asarray(xs, dtype=float)
    if len(xs) == 0:
        return np.empty(0)
    if len(edges) == 0:
        return np.zeros(len(xs))
    x1, y1, x2, y2 = (edges[:, column] for column in range(4))
    span = (x2 - x1)[:, None]
    chords = np.empty(len(xs))
    # Chunk the sample axis so a dense spine does not build an edges-by-samples square.
    for start in range(0, len(xs), 256):
        sample = xs[start:start + 256]
        x = sample[None, :]
        crosses = ((x1[:, None] <= x) & (x < x2[:, None])) | ((x2[:, None] <= x) & (x < x1[:, None]))
        y = np.where(crosses, y1[:, None] + (y2 - y1)[:, None] * (x - x1[:, None]) / span, np.inf)
        y.sort(axis=0)
        counts = np.isfinite(y).sum(axis=0)
        if np.any(counts & 1):
            return None
        part = np.zeros(len(sample))
        highest = int(counts.max()) if len(counts) else 0
        for count in range(2, highest + 1, 2):
            cols = counts == count
            if not np.any(cols):
                continue
            block = y[:count, cols]
            part[cols] = np.sum(block[1::2, :] - block[0::2, :], axis=0)
        chords[start:start + 256] = part
    return chords


def _chord_product(band, strip):
    """Exact integral of the product of two vertical chord functions.

    Between vertex x-coordinates both chords are linear, holes included, so the
    product has a closed-form integral on each piece.
    """
    rib_edges, rib_x = _ring_edges(band)
    plate_edges, plate_x = _ring_edges(strip)
    if len(rib_edges) == 0 or len(plate_edges) == 0:
        return 0.0
    xs = np.unique(np.concatenate((rib_x, plate_x)))
    if len(xs) < 2:
        return 0.0
    left, right = xs[:-1], xs[1:]
    width = right - left
    keep = width > 1e-15
    left, width = left[keep], width[keep]
    if len(width) == 0:
        return 0.0
    samples = np.empty(len(width) * 2)
    samples[0::2] = left + width * 0.25
    samples[1::2] = left + width * 0.75
    rib = _scan_chords(rib_edges, samples)
    plate = _scan_chords(plate_edges, samples)
    if rib is None or plate is None:
        return None
    c0, c1 = rib[0::2], rib[1::2]
    p0, p1 = plate[0::2], plate[1::2]
    # The piece is linear, so the 25% and 75% samples determine its endpoints.
    ends = np.stack((
        1.5 * c0 - 0.5 * c1,
        -0.5 * c0 + 1.5 * c1,
        1.5 * p0 - 0.5 * p1,
        -0.5 * p0 + 1.5 * p1,
    ))
    if np.any(ends < -1e-6):
        return None
    rc0, rc1, pc0, pc1 = np.maximum(ends, 0.0)
    return float(np.sum(width * (2 * rc0 * pc0 + 2 * rc1 * pc1 + rc0 * pc1 + rc1 * pc0) / 6.0))


def _radial_rib_overlap(web, tw, plate, tp):
    """Exact volume of an upright rib through a horizontal plate.

    The rib profile is extruded along a horizontal normal. In that frame the
    plate cuts a fixed strip. Both vertical chords are piecewise linear, so
    their product integrates exactly. Any other orientation keeps the kernel.
    """
    tw, tp = np.asarray(tw, dtype=float), np.asarray(tp, dtype=float)
    if not np.allclose(tp[2, :3], (0.0, 0.0, 1.0), atol=1e-9):
        return None
    if abs(tw[2, 0]) > 1e-9 or abs(tw[2, 2]) > 1e-9 or abs(abs(tw[2, 1]) - 1.0) > 1e-9:
        return None
    if abs(tw[0, 1]) > 1e-9 or abs(tw[1, 1]) > 1e-9:
        return None
    radial, tangent = tw[:2, 0], tw[:2, 2]
    if abs(np.dot(radial, radial) - 1.0) > 1e-8 or abs(np.dot(tangent, tangent) - 1.0) > 1e-8:
        return None
    if abs(np.dot(radial, tangent)) > 1e-8:
        return None
    # gp_Trsf keeps this matrix only as a rigid motion. A reflection is left to the kernel.
    if abs(np.linalg.det(tw[:3, :3]) - 1.0) > 1e-8 or abs(np.linalg.det(tp[:3, :3]) - 1.0) > 1e-8:
        return None
    z0, z1 = float(tp[2, 3]), float(tp[2, 3] + plate.thickness_mm)
    if tw[2, 1] > 0:
        y0, y1 = z0 - tw[2, 3], z1 - tw[2, 3]
    else:
        y0, y1 = tw[2, 3] - z1, tw[2, 3] - z0
    profile = web.polygon
    if y1 <= y0 or profile.is_empty:
        return 0.0
    band = profile.intersection(box(profile.bounds[0] - 1.0, y0, profile.bounds[2] + 1.0, y1))
    if band.is_empty or band.area <= 0:
        return 0.0
    world = affinity.affine_transform(
        plate.polygon, [tp[0, 0], tp[0, 1], tp[1, 0], tp[1, 1], tp[0, 3], tp[1, 3]]
    )
    origin = tw[:2, 3]
    # u along the rib profile, v along its thickness extrusion.
    uv = affinity.affine_transform(world, [
        radial[0], radial[1], tangent[0], tangent[1],
        -float(np.dot(radial, origin)), -float(np.dot(tangent, origin)),
    ])
    strip = uv.intersection(box(uv.bounds[0] - 1.0, 0.0, uv.bounds[2] + 1.0, web.thickness_mm))
    if strip.is_empty or strip.area <= 0:
        return 0.0
    return _chord_product(band, strip)


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
        if exact is None:
            exact = _radial_rib_overlap(web, tw, plate, tp)
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
