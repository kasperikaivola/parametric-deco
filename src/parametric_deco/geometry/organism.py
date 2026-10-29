"""Field-arranged, variable-width flowing anatomy; no manufactured coordinates table."""

from dataclasses import dataclass
import math
import numpy as np
from shapely import affinity
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from .creature_profiles import smooth


@dataclass(frozen=True)
class Lobe:
    name: str
    shape: Polygon
    z: float
    path: np.ndarray
    tier: int


def ribbon(path, widths, angularity=0):
    """Swept rounded disks: swelling and taper affect the entire path length."""
    return unary_union(
        [
            Point(p).buffer(
                float(w)
                * (1 + angularity * 0.16 * math.cos(10 * math.pi * k / max(len(path) - 1, 1))),
                quad_segs=10,
            )
            for k, (p, w) in enumerate(zip(path, widths))
        ]
    ).simplify(0.00035, preserve_topology=True)


def anatomy(c):
    o = c.organism
    primary = []
    for i in range(o.focal_count):
        theta = 2 * math.pi * i / o.focal_count + math.radians(o.phase_deg)
        variation = o.asymmetry * math.sin(i * 2.399 + 0.6)
        if o.symmetry == "rotational":
            variation = o.asymmetry * math.cos(2 * theta)
        if o.arrangement == "whorl":
            center = np.array((0.34 * math.cos(theta), 0.34 * math.sin(theta))) * o.spread
            angle = theta
        else:
            row, side = divmod(i, 2)
            rows = (o.focal_count + 1) // 2
            center = (
                np.array(
                    (
                        (-1 if side == 0 else 1) * (0.31 + 0.08 * math.cos(row)),
                        0.65 - 1.3 * row / max(rows - 1, 1),
                    )
                )
                * o.spread
            )
            angle = (math.pi if side == 0 else 0) + 0.25 * math.sin(row * 1.8)
        # A continuous field changes the whole anatomy, not only endpoint positions.
        # Alternating long saddles and broad lobes flow across neighboring focal regions.
        morph = 0.5 + 0.32 * math.cos(3 * theta) + 0.18 * math.sin(2 * theta)
        # These common controls interpolate the family; there are no per-example paths.
        controls = np.array(
            [
                [-0.26, -0.12],
                [-0.10, -0.24],
                [0.18, -0.17],
                [0.26, 0.02],
                [0.12, 0.21],
                [-0.23 + 0.10 * morph, 0.20],
                [-0.38 + 0.20 * morph, -0.02 + 0.14 * morph],
            ]
        )
        controls[:, 0] *= 0.82 + 0.34 * morph
        controls[1:5, 1] += 0.05 * math.sin(2 * theta)
        controls[:, 1] *= o.curvature * (1 + variation)
        controls[:, 0] *= 1 - variation * 0.6
        if o.symmetry == "bilateral" and i % 2:
            controls[:, 1] *= -1
        if o.symmetry == "none":
            angle += variation * 2
        path = smooth(controls, samples=20)
        rotation = np.array(
            ((math.cos(angle), -math.sin(angle)), (math.sin(angle), math.cos(angle)))
        )
        path = path @ rotation.T + center
        u = np.linspace(0, 1, len(path))
        widths = (
            0.053 * o.swelling * (1 + 0.5 * np.sin(math.pi * u)) * (1 - 0.55 * u ** (2 / o.taper))
        )
        shape = ribbon(path, widths, o.angularity)
        # A continuous branching lamina carries the focal curl into a swept appendage.
        # Its long shoulder changes with curvature, not just the terminal point.
        branch_controls = np.array(
            [
                [0.23, -0.04],
                [0.40, -0.11],
                [0.57, 0.02],
                [0.61, 0.21],
                [0.47, 0.39],
                [0.17, 0.43],
                [-0.12, 0.36],
            ]
        )
        branch_controls[:, 1] *= o.curvature
        branch_controls[:, 0] *= (0.80 + 0.40 * (1 - morph)) * (1 + variation)
        if o.symmetry == "bilateral" and i % 2:
            branch_controls[:, 1] *= -1
        branch = smooth(branch_controls, samples=20) @ rotation.T + center
        bu = np.linspace(0, 1, len(branch))
        bw = (
            0.057
            * o.swelling
            * (1 - 0.65 * bu ** (1.5 / o.taper))
            * (1 + 0.16 * np.sin(10 * math.pi * bu) ** 2)
        )
        shape = shape.union(ribbon(branch, bw, o.angularity))
        segments = 2 + o.complexity if o.segmentation is None else o.segmentation
        for fraction in np.linspace(0.24, 0.74, segments):
            j = int(fraction * (len(branch) - 1))
            k = int((0.30 + fraction * 0.60) * (len(path) - 1))
            start, finish = branch[j], path[k]
            delta = finish - start
            normal = np.array((-delta[1], delta[0]))
            middle = (start + finish) / 2 + 0.18 * o.curvature * normal
            bridge = smooth([start, middle, finish], samples=20)
            radii = (0.017 + 0.014 * (2 * np.linspace(0, 1, len(bridge)) - 1) ** 4) * o.swelling
            shape = shape.union(ribbon(bridge, radii, o.angularity))
        channels = (1 + o.complexity) if o.channels is None else o.channels
        cuts = []
        for k in range(channels):
            start = 8 + 27 * k
            segment = branch[start : start + 16]
            radii = bw[start : start + 16] * 0.22
            cuts.append(ribbon(segment, radii))
        shape = shape.difference(unary_union(cuts))
        primary.append((path, widths, shape))
    # Fit primary silhouette to requested dimensions, keeping complexity-independent bounds.
    bounds = unary_union([s for _, _, s in primary]).bounds
    sx = (c.envelope.width_mm - 4) / (bounds[2] - bounds[0])
    sy = (c.envelope.height_mm - 4) / (bounds[3] - bounds[1])
    center = np.array(((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2))
    result = []
    base = c.mounting.rear_clearance_mm + c.material.measured_mm
    usable = c.envelope.depth_mm - base - c.material.measured_mm - 14
    for i, (path, widths, shape) in enumerate(primary):
        path_mm = (path - center) * (sx, sy)
        shape_mm = affinity.affine_transform(
            shape, [sx, 0, 0, sy, -center[0] * sx, -center[1] * sy]
        )
        z = base + usable * (0.40 + 0.55 * i / max(o.focal_count - 1, 1))
        result.append(Lobe(f"primary-{i}", shape_mm, z, path_mm, 0))
    secondary = min(o.complexity, 1) if o.secondary_lobes is None else o.secondary_lobes
    for tier in range(1, secondary + 1):
        for i, (path, widths, _) in enumerate(primary):
            # Nested fragments inside the same silhouette; no replacement focal cavities.
            middle = path[35:96]
            anchor = path.mean(axis=0)
            factor = 0.64
            sub = anchor + (middle - anchor) * factor
            sub_width = widths[35:96] * 0.85
            poly = ribbon(sub, sub_width, o.angularity)
            poly = affinity.affine_transform(poly, [sx, 0, 0, sy, -center[0] * sx, -center[1] * sy])
            z = base + usable * (0.08 + 0.23 * i / max(o.focal_count - 1, 1))
            result.append(Lobe(f"secondary-{tier}-{i}", poly, z, (sub - center) * (sx, sy), tier))
    return result
