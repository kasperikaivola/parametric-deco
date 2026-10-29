"""Smooth planar anatomy shared by coarse studies and manufactured profiles (mm)."""

import numpy as np
from shapely import affinity
from shapely.geometry import Polygon, Point, MultiPoint
from shapely.ops import unary_union
from dataclasses import replace
from ..config import CreatureMask

ROOTS = {
    "head": ((-50, 100), (50, 100)),
    "crown-left": ((-200, 100), (-225, 150)),
    "crown-right": ((200, 100), (225, 150)),
    "jaw-left": ((-100, -100), (-150, -100)),
    "jaw-right": ((100, -100), (150, -100)),
    "feeler-left": ((-75, -250), (-125, -250)),
    "feeler-right": ((75, -250), (125, -250)),
}


def module_roots(settings=None):
    p = settings or CreatureMask()
    return dict(list(ROOTS.items())[: 1 + p.limb_count])


def cavity_voids(settings=None, factor=1):
    p = settings or CreatureMask()
    return tuple(
        affinity.scale(q, xfact=p.scale, yfact=p.scale, origin=(0, 0))
        for q in eye_voids(factor, p.cavity_count)
    )


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


def eye_voids(factor=1, count=6):
    """Six competing recesses, deliberately unequal rather than six eye sockets."""
    controls = [
        [(-165, 171), (-140, 202), (-91, 190), (-70, 152), (-104, 155), (-130, 177)],
        [(75, 156), (106, 195), (145, 179), (153, 155), (118, 170), (102, 151)],
        [(-197, 7), (-163, 45), (-123, 26), (-114, -10), (-148, 4), (-173, -30)],
        [(117, 8), (140, 37), (184, 23), (190, -8), (155, -47), (160, -8), (133, -22)],
        [(-109, -150), (-83, -119), (-49, -141), (-36, -177), (-72, -162), (-98, -180)],
        [(43, -147), (67, -128), (99, -148), (93, -183), (72, -166), (48, -180)],
    ]
    controls.extend(
        [
            [(-17, -105), (-6, -85), (15, -99), (12, -117), (-7, -121)],
            [(-14, 151), (-5, 139), (15, 149), (10, 169), (-9, 171)],
        ]
    )
    indices = np.rint(np.linspace(0, 5, count)).astype(int) if count <= 6 else np.arange(count)
    result = []
    for index in indices:
        points = controls[index]
        shape = organic(points)
        scaled = affinity.scale(shape, xfact=factor, yfact=factor, origin=shape.centroid)
        result.append(shape.union(scaled) if factor >= 1 else shape.intersection(scaled))
    return tuple(result)


def central_void():
    return organic([(-35, 8), (-7, 37), (34, 15), (27, -19), (-11, -31)])


def head_outline():
    # Scalloped overlapping lobes, without a helmet dome or pointed chin.
    return organic(
        [
            (0, 206),
            (-75, 250),
            (-153, 230),
            (-204, 172),
            (-199, 87),
            (-236, 24),
            (-225, -66),
            (-158, -111),
            (-130, -206),
            (-58, -237),
            (0, -202),
            (58, -237),
            (130, -206),
            (158, -111),
            (225, -66),
            (236, 24),
            (199, 87),
            (204, 172),
            (153, 230),
            (75, 250),
        ]
    )


def appendage_recipes(curl=1):
    """Lateral folds, lower graspers and optional sensory limbs; no upper C horns."""
    return {
        "crown-left": (
            [
                (-135, 80),
                (-285, 110),
                (-375, 65),
                (-400, -20),
                (-385, -75),
                (-330, -65 + 30 * (curl - 1)),
            ],
            [125, 150, 135, 110, 80, 48],
        ),
        "jaw-left": (
            [
                (-105, -80),
                (-245, -140),
                (-370, -230),
                (-360, -330),
                (-295, -350),
                (-255, -305 + 25 * (curl - 1)),
            ],
            [120, 125, 115, 100, 75, 42],
        ),
        "feeler-left": (
            [
                (-95, -240),
                (-160, -300),
                (-180, -370),
                (-155, -420),
                (-115, -430),
                (-80, -400 + 20 * (curl - 1)),
            ],
            [90, 95, 95, 90, 65, 38],
        ),
    }


def limb_recipe(name, settings):
    left = name.replace("right", "left")
    points, widths = appendage_recipes(settings.curl)[left]
    points = np.array(points, dtype=float)
    if "right" in name:
        points[:, 0] *= -1
    anchor = np.mean(ROOTS[name], axis=0)
    side = 0.5 if "right" in name else -0.5
    points = anchor + (points - anchor) * settings.limb_reach * (1 + side * settings.asymmetry)
    widths = np.array(widths) * settings.limb_width * (1 + 0.3 * side * settings.asymmetry)
    return points, widths


def rib_stations(name, scale=1, curl=1, *, settings=None):
    """Centre XY, transverse unit vector, physical blade width and height (mm)."""
    p = settings or CreatureMask(scale=scale, curl=curl)
    points, widths = limb_recipe(name, p)
    path = smooth(points)
    cumulative = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    start, end = round(0.23 * (len(path) - 1)), round(0.8 * (len(path) - 1))
    distances = np.linspace(cumulative[start], cumulative[end], p.ribs_per_limb)
    stations = []
    for j, distance in enumerate(distances):
        k = int(np.argmin(abs(cumulative - distance)))
        fraction = k / (len(path) - 1)
        tangent = path[k + 1] - path[k - 1]
        tangent /= np.linalg.norm(tangent)
        normal = np.array((-tangent[1], tangent[0]))
        width = float(np.interp(fraction * (len(widths) - 1), np.arange(len(widths)), widths))
        width = max(54, width * 0.78) * p.scale
        height = (
            p.rib_height_mm
            * (0.5 + 0.5 * np.sin(np.pi * (j + 0.7) / (p.ribs_per_limb + 0.7)))
            * p.scale
        )
        if name.startswith("feeler"):
            height *= 0.72
        stations.append((path[k] * p.scale, normal, width, height))
    return stations


def sweep(points, widths):
    path = smooth(points)
    tangent = np.gradient(path, axis=0)
    normal = np.column_stack((-tangent[:, 1], tangent[:, 0]))
    normal /= np.linalg.norm(normal, axis=1)[:, None]
    w = np.interp(np.linspace(0, len(widths) - 1, len(path)), np.arange(len(widths)), widths) / 2
    p = Polygon(np.vstack((path + normal * w[:, None], (path - normal * w[:, None])[::-1]))).buffer(
        0
    )
    # Rounded caps and a small roundover remove needle tips; no engraving/noise.
    return unary_union(
        [p, Point(path[0]).buffer(w[0], quad_segs=12), Point(path[-1]).buffer(w[-1], quad_segs=12)]
    ).buffer(2, quad_segs=6)


def profiles(scale=1, curl=1, *, settings=None):
    settings = settings or CreatureMask(scale=scale, curl=curl)
    scale = settings.scale
    nominal = replace(settings, scale=1)
    voids = unary_union((*cavity_voids(nominal, 1.06), central_void()))
    inner_channel = sweep(
        [(-70, 56), (-83, 18), (-73, -30), (-52, -65), (-46, -99)], [8, 10, 10, 9, 8]
    )
    inner_channels = unary_union(
        [inner_channel, affinity.scale(inner_channel, xfact=-1, yfact=1, origin=(0, 0))]
    )
    head = []
    shell_channels = [
        sweep([(-250, 85), (-205, 88), (-157, 96), (-105, 75)], [30, 20, 16, 12]),
        sweep([(-250, -94), (-195, -87), (-155, -82), (-100, -87)], [30, 20, 16, 12]),
        sweep([(0, 270), (0, 220), (0, 164)], [38, 26, 16]),
        sweep([(0, -260), (0, -205), (0, -125)], [40, 28, 16]),
    ]
    shell_channels += [
        affinity.scale(p, xfact=-1, yfact=1, origin=(0, 0)) for p in shell_channels[:2]
    ]
    for j in range(settings.shell_layers):
        # Alternate lobe exposure around the cavities; no solid rostrum cap.
        outer = affinity.scale(
            head_outline(), xfact=1 - 0.022 * j, yfact=1 - 0.018 * j, origin=(0, 0)
        )
        channels = unary_union([p.buffer(j * 1.2) for p in shell_channels])
        head.append(
            outer.difference(
                unary_union([voids.buffer(j * 1.5), channels, inner_channels.buffer(j * 0.6)])
            )
        )
    result = {"head": head}
    for name in list(module_roots(settings))[1:]:
        points, widths = limb_recipe(name, nominal)
        count = settings.limb_layers
        root = MultiPoint(ROOTS[name]).convex_hull.buffer(44, quad_segs=12)
        path = smooth(points)
        # Two long through channels, crossed only by deliberate rib-bearing bridges.
        from shapely.geometry import LineString

        channels = unary_union(
            [
                LineString(path[15:35]).buffer(13, quad_segs=8),
                LineString(path[39:51]).buffer(8, quad_segs=8),
            ]
        )
        bridges = []
        for center, normal, width, height in rib_stations(name, settings=nominal):
            tangent = np.array((-normal[1], normal[0]))
            corners = [
                center + u * normal + v * tangent
                for u, v in [(-width, -13), (width, -13), (width, 13), (-width, 13)]
            ]
            bridges.append(Polygon(corners))
        channels = channels.difference(unary_union(bridges))
        layers = []
        for j in range(count):
            widths_j = np.array(widths) * (1 - 0.07 * j)
            widths_j[-1] = max(18, widths_j[-1])
            shape = unary_union([sweep(points, widths_j), root])
            # Inset clipping keeps at least 10 mm rails around channel edges.
            holes = channels.intersection(shape.buffer(-10))
            shape = shape.difference(unary_union([holes, voids]))
            layers.append(shape)
        result[name] = layers
    return {
        name: [affinity.scale(p, xfact=scale, yfact=scale, origin=(0, 0)) for p in layers]
        for name, layers in result.items()
    }


def backing_outline(scale=1, *, settings=None):
    settings = settings or CreatureMask(scale=scale)
    scale = settings.scale
    root_regions = []
    for name, roots in module_roots(settings).items():
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
    eyes = [
        *cavity_voids(settings, 1.06),
        affinity.scale(central_void(), xfact=scale, yfact=scale, origin=(0, 0)),
    ]
    return shape.difference(unary_union(eyes))
