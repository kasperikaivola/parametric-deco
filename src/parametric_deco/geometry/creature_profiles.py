"""Smooth planar anatomy shared by coarse studies and manufactured profiles (mm)."""

import numpy as np
from shapely import affinity
from shapely.geometry import Polygon, Point, MultiPoint
from shapely.ops import unary_union

ROOTS = {
    "head": ((-50, 100), (50, 100)),
    "crown-left": ((-200, 100), (-225, 150)),
    "crown-right": ((200, 100), (225, 150)),
    "jaw-left": ((-100, -100), (-150, -100)),
    "jaw-right": ((100, -100), (150, -100)),
}


def smooth(points, closed=False, samples=12):
    p = np.array(points, dtype=float)
    p = np.vstack((p[-1], p, p[:2])) if closed else np.vstack((p[0], p, p[-1]))
    out = []
    for i in range(1, len(p) - 2):
        a, b, c, d = p[i - 1 : i + 3]
        for t in np.linspace(0, 1, samples, endpoint=False):
            out.append(
                0.5
                * (
                    (2 * b)
                    + (-a + c) * t
                    + (2 * a - 5 * b + 4 * c - d) * t * t
                    + (-a + 3 * b - 3 * c + d) * t * t * t
                )
            )
    if not closed:
        out.append(p[-2])
    return np.array(out)


def organic(points):
    return Polygon(smooth(points, True)).buffer(0)


def eye_voids(factor=1):
    left = organic([(-168, 64), (-128, 82), (-80, 66), (-44, 24), (-74, 8), (-124, 22)])
    left = affinity.scale(left, xfact=factor, yfact=factor, origin=(-105, 45))
    return left, affinity.scale(left, xfact=-1, yfact=1, origin=(0, 0))


def head_outline():
    return organic(
        [
            (0, 258),
            (-68, 215),
            (-150, 190),
            (-210, 115),
            (-198, 20),
            (-167, -85),
            (-112, -177),
            (-42, -210),
            (0, -250),
            (42, -210),
            (112, -177),
            (167, -85),
            (198, 20),
            (210, 115),
            (150, 190),
            (68, 215),
        ]
    )


def sweep(points, widths):
    path = smooth(points)
    tangent = np.gradient(path, axis=0)
    normal = np.column_stack((-tangent[:, 1], tangent[:, 0]))
    normal /= np.linalg.norm(normal, axis=1)[:, None]
    w = np.interp(np.linspace(0, len(widths) - 1, len(path)), np.arange(len(widths)), widths) / 2
    p = Polygon(np.vstack((path + normal * w[:, None], (path - normal * w[:, None])[::-1])))
    # Rounded caps and a small roundover remove needle tips; no engraving/noise.
    return unary_union(
        [p, Point(path[0]).buffer(w[0], quad_segs=12), Point(path[-1]).buffer(w[-1], quad_segs=12)]
    ).buffer(2, quad_segs=6)


def profiles(scale=1, curl=1):
    head = []
    cheek = organic([(123, -40), (134, -58), (127, -101), (116, -83)])
    cheeks = [cheek, affinity.scale(cheek, xfact=-1, yfact=1, origin=(0, 0))]
    for j in range(5):
        outer = affinity.scale(
            head_outline(), xfact=1 - 0.035 * j, yfact=1 - 0.035 * j, origin=(0, 0)
        )
        head.append(outer.difference(unary_union((*eye_voids(1 + 0.075 * j), *cheeks))))
    ridge = organic(
        [
            (0, 238),
            (-64, 183),
            (-110, 132),
            (-91, 94),
            (-35, 72),
            (-20, -75),
            (0, -151),
            (20, -75),
            (35, 72),
            (91, 94),
            (110, 132),
            (64, 183),
        ]
    )
    head.append(ridge.difference(unary_union(eye_voids(1.375))))
    result = {"head": head}
    recipes = {
        "crown-left": (
            [
                (-135, 80),
                (-260, 150),
                (-385, 265),
                (-375, 365),
                (-290, 385),
                (-265, 330 + 25 * (curl - 1)),
            ],
            [125, 160, 130, 85, 45, 22],
            5,
        ),
        "jaw-left": (
            [(-105, -80), (-225, -150), (-300, -245), (-260, -340), (-170, -350), (-130, -300)],
            [120, 110, 95, 65, 35, 22],
            4,
        ),
    }
    for name, (points, widths, count) in recipes.items():
        root = MultiPoint(ROOTS[name]).convex_hull.buffer(44, quad_segs=12)
        layers = []
        for j in range(count):
            widths_j = np.array(widths) * (1 - 0.115 * j)
            widths_j[-1] = max(18, widths_j[-1])
            p = unary_union([sweep(points, widths_j), root]).difference(
                unary_union(eye_voids(1.45))
            )
            if p.geom_type != "Polygon":
                p = max(p.geoms, key=lambda g: g.area)
            layers.append(p)
        result[name] = layers
        result[name.replace("left", "right")] = [
            affinity.scale(p, xfact=-1, yfact=1, origin=(0, 0)) for p in layers
        ]
    # Profile dimensions scale; root drilling and keying are added later at physical sizes.
    return {
        name: [affinity.scale(p, xfact=scale, yfact=scale, origin=(0, 0)) for p in layers]
        for name, layers in result.items()
    }


def backing_outline(scale=1):
    root_regions = []
    for name, roots in ROOTS.items():
        poses = [(0, 0)]
        if name.startswith("crown"):
            poses.append((-25 if "left" in name else 25, 50))
        for dx, dy in poses:
            root_regions.append(
                MultiPoint([(x + dx, y + dy) for x, y in roots]).convex_hull.buffer(
                    52, quad_segs=12
                )
            )
    head = affinity.scale(
        head_outline().buffer(12, quad_segs=8), xfact=scale, yfact=scale, origin=(0, 0)
    )
    shape = unary_union([head, *root_regions])
    eyes = [affinity.scale(p, xfact=scale, yfact=scale, origin=(0, 0)) for p in eye_voids(0.8)]
    return shape.difference(unary_union(eyes))
