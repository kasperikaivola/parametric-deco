"""Regular polygon and deterministic staggered hole lattice."""

from functools import lru_cache
import math

from shapely.geometry import Point, Polygon

from ..cad import solid_for
from ..model import GeometryBundle, MountPoint, PartDefinition


def backplate_polygon(config):
    n = config.backplate.sides
    theta = math.radians(config.backplate.rotation_deg)
    points = [
        (math.cos(theta + 2 * math.pi * i / n), math.sin(theta + 2 * math.pi * i / n))
        for i in range(n)
    ]
    # Uniformly fit a regular polygon; centred by its bounding box for odd polygons too.
    xs, ys = zip(*points)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    scale = min(
        config.envelope.width_mm / (max(xs) - min(xs)),
        config.envelope.height_mm / (max(ys) - min(ys)),
    )
    polygon = Polygon([((x - cx) * scale, (y - cy) * scale) for x, y in points])
    if config.composition is not None:
        radius = config.composition.opening_radius_mm / math.cos(math.pi / 384)
        polygon = polygon.difference(Point(0, 0).buffer(radius, quad_segs=96))
    return polygon


@lru_cache(maxsize=16)
def mounting_holes(config):
    g = config.grid
    p = backplate_polygon(config)
    minx, miny, maxx, maxy = p.bounds
    # Bounds include origin and offset even when offset > pitch.
    result = []
    for row in range(
        math.floor((miny - g.origin_y_mm) / g.pitch_y_mm) - 1,
        math.ceil((maxy - g.origin_y_mm) / g.pitch_y_mm) + 2,
    ):
        shift = g.origin_x_mm + (row % 2) * g.offset_mm
        for col in range(
            math.floor((minx - shift) / g.pitch_x_mm) - 1,
            math.ceil((maxx - shift) / g.pitch_x_mm) + 2,
        ):
            x, y = shift + col * g.pitch_x_mm, g.origin_y_mm + row * g.pitch_y_mm
            point = Point(x, y)
            if (
                p.covers(point)
                and p.boundary.distance(point) >= g.edge_margin_mm + g.hole_diameter_mm / 2 - 1e-9
            ):
                result.append(MountPoint(row, col, x, y, g.hole_diameter_mm))
    return tuple(result)


def match_root_pattern(config, positions, tolerance_mm=1e-6):
    holes = mounting_holes(config)
    polygon = backplate_polygon(config)
    matched = []
    for x, y in positions:
        h = next((h for h in holes if math.hypot(h.x_mm - x, h.y_mm - y) <= tolerance_mm), None)
        if h is None or polygon.boundary.distance(Point(x, y)) < config.mounting.washer_radius_mm:
            raise ValueError(f"root mount ({x:g}, {y:g}) has no available grid hole/washer margin")
        matched.append(h)
    if len({h.point_id for h in matched}) != len(matched):
        raise ValueError("root mount pattern assigns a hole twice")
    return tuple(matched)


@lru_cache(maxsize=16)
def generate_backplate(config):
    polygon = backplate_polygon(config)
    holes = [
        Point(h.x_mm, h.y_mm).buffer(h.diameter_mm / 2, quad_segs=8) for h in mounting_holes(config)
    ]
    from shapely.ops import unary_union

    part = PartDefinition.from_polygon(
        "backplate",
        polygon.difference(unary_union(holes)),
        config.material.measured_mm,
        kind="backplate",
    )
    return GeometryBundle((part,), solids={part.definition_id: solid_for(part)})
