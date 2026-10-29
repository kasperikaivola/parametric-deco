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
    """Six competing recesses, deliberately unequal rather than six eye sockets."""
    controls = [
        [(-165, 171), (-140, 202), (-91, 190), (-70, 152), (-104, 155), (-130, 177)],
        [(75, 156), (106, 195), (145, 179), (153, 155), (118, 170), (102, 151)],
        [(-197, 7), (-163, 45), (-123, 26), (-114, -10), (-148, 4), (-173, -30)],
        [(117, 8), (140, 37), (184, 23), (190, -8), (155, -47), (160, -8), (133, -22)],
        [(-109, -150), (-83, -119), (-49, -141), (-36, -177), (-72, -162), (-98, -180)],
        [(43, -147), (67, -128), (99, -148), (93, -183), (72, -166), (48, -180)],
    ]
    result = []
    for points in controls:
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
    return {
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


def rib_stations(name, scale=1, curl=1):
    """(centre XY, transverse unit vector, blade width, height) in physical mm.

    Stock and joinery sizes are added later, never scaled with these profiles.
    """
    left = name.replace("right", "left")
    points, widths, _ = appendage_recipes(curl)[left]
    path = smooth(points)
    stations = []
    count = 7 if left.startswith("crown") else 5
    cumulative = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    start = round(0.27 * (len(path) - 1))
    end = round((0.69 if left.startswith("crown") else 0.62) * (len(path) - 1))
    distances = np.linspace(cumulative[start], cumulative[end], count)
    for j, distance in enumerate(distances):
        k = int(np.argmin(abs(cumulative - distance)))
        fraction = k / (len(path) - 1)
        tangent = path[k + 1] - path[k - 1]
        tangent /= np.linalg.norm(tangent)
        normal = np.array((-tangent[1], tangent[0]))
        width = float(np.interp(fraction * (len(widths) - 1), np.arange(len(widths)), widths))
        width = max(54, width * 0.78) * scale
        height = (36 + 42 * np.sin(np.pi * (j + 0.7) / (count + 0.7))) * scale
        if left.startswith("jaw"):
            height *= 0.72
        center = path[k] * scale
        if "right" in name:
            center[0] *= -1
            normal[0] *= -1
        stations.append((center, normal, width, height))
    return stations


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
    voids = unary_union((*eye_voids(1.06), central_void()))
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
    for j in range(6):
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
    for name, (points, widths, count) in appendage_recipes(curl).items():
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
        for center, normal, width, height in rib_stations(name, 1, curl):
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
        result[name.replace("left", "right")] = [
            affinity.scale(p, xfact=-1, yfact=1, origin=(0, 0)).difference(voids) for p in layers
        ]
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
    eyes = [
        affinity.scale(p, xfact=scale, yfact=scale, origin=(0, 0))
        for p in (*eye_voids(1.06), central_void())
    ]
    return shape.difference(unary_union(eyes))
