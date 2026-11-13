"""Branched laminae, lens chambers and clefts in a configurable anatomical field."""

from dataclasses import dataclass
import math
import numpy as np
from shapely import affinity, remove_repeated_points
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union


@dataclass(frozen=True)
class Lobe:
    name: str
    shape: Polygon
    z: float
    path: np.ndarray
    tier: int
    backing_path: np.ndarray | None = None
    major_outline: Polygon | None = None


def ribbon(path, widths, angularity=0):
    """Rounded sweep with substantial truncated ends; all widths are real material."""
    path = np.asarray(path, dtype=float)
    radii = np.asarray(widths, dtype=float) * (
        1 + angularity * 0.12 * np.cos(10 * math.pi * np.linspace(0, 1, len(path)))
    )
    if angularity == 0 and np.ptp(radii) < 1e-12:
        return LineString(path).buffer(float(radii[0]), quad_segs=10)
    pieces = [Point(p).buffer(float(r), quad_segs=10) for p, r in zip(path, radii)]
    for a, b, ra, rb in zip(path, path[1:], radii, radii[1:]):
        direction = b - a
        length = np.linalg.norm(direction)
        if length == 0:
            continue
        n = np.array((-direction[1], direction[0])) / length
        pieces.append(Polygon([a + ra * n, b + rb * n, b - rb * n, a - ra * n]))
    return unary_union(pieces).simplify(0.00035, preserve_topology=True)


def division_positions(count):
    """Nested endpoint-first dyadic sequence, independent of requested final count."""
    if type(count) is not int or not 0 <= count <= 5:
        raise ValueError("division count requires integer 0..5")
    positions = [0.24, 0.74]
    intervals = [(0.24, 0.74)]
    while len(positions) < count:
        a, b = intervals.pop(0)
        middle = (a + b) / 2
        positions.append(middle)
        intervals.extend(((a, middle), (middle, b)))
    return tuple(positions[:count])


def curve(start, end, bend, samples=97):
    """An open curved medial axis; bend acts over the complete interior span."""
    a, b = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
    u = np.linspace(0, 1, samples)
    direction = b - a
    normal = np.array((-direction[1], direction[0])) / np.linalg.norm(direction)
    return a + (b - a) * u[:, None] + normal * (4 * u * (1 - u) * bend)[:, None]


def spindle(path, width, style, tip=0.018):
    u = np.linspace(0, 1, len(path))
    widths = tip + width * np.sin(math.pi * u) ** (0.7 * style.taper)
    return ribbon(path, widths, style.angularity)


def field(o, i):
    theta = 2 * math.pi * i / o.focal_count + math.radians(o.phase_deg)
    phase = theta + math.radians(o.anatomy_phase_deg)
    morph = 0.5 + 0.30 * math.cos(3 * phase) + 0.20 * math.sin(2 * phase)
    if o.arrangement == "whorl":
        center = np.array((0.34 * math.cos(theta), 0.34 * math.sin(theta))) * o.spread
        angle = theta + 0.35 * math.sin(2 * phase)
    else:
        row, side = divmod(i, 2)
        rows = (o.focal_count + 1) // 2
        center = (
            np.array(
                (
                    (-1 if side == 0 else 1) * (0.27 + 0.07 * math.cos(row)),
                    0.43 - 0.86 * row / max(rows - 1, 1),
                )
            )
            * o.spread
        )
        angle = (math.pi if side == 0 else 0) + (0.35 - 0.14 * row) * (-1 if side == 0 else 1)
    variation = o.asymmetry * math.sin(i * 2.399 + 0.6)
    if o.symmetry == "rotational":
        variation = o.asymmetry * math.cos(2 * theta)
    if o.symmetry == "none":
        angle += variation * 2
    reflection = -1 if o.symmetry == "bilateral" and i % 2 else 1
    co, si = math.cos(angle), math.sin(angle)
    rotation = np.array(((co, -si), (si, co))) @ np.diag((1, reflection))
    return center, rotation, morph, variation, phase


def primary_anatomy(o, i, max_cleft=1.0, septum_radius=0.0, channel_cap=None):
    center, rotation, morph, variation, phase = field(o, i)
    main = curve(
        (-0.28, -0.06 * math.sin(phase)),
        (0.49 + 0.12 * morph, 0.14 * math.sin(2 * phase)),
        (0.045 + 0.12 * morph) * o.curvature * (1 + variation),
    )
    u = np.linspace(0, 1, len(main))
    widths = 0.024 + 0.105 * o.swelling * np.sin(math.pi * u) ** (0.7 * o.taper) * (
        1 + 0.15 * np.cos(2 * math.pi * u + phase)
    )
    body = ribbon(main, widths, o.angularity)
    # Daughter laminae diverge from different axial nodes; they never return as loops.
    branch_count = 1 + min(o.branching - 1, int(morph * o.branching))
    for j in range(branch_count):
        t = 0.28 + 0.19 * j
        anchor = main[int(t * (len(main) - 1))]
        side = 1 if j % 2 == 0 else -1
        target = np.array(
            (
                0.30 + 0.19 * (1 - morph) + 0.08 * j,
                side * (0.23 + 0.10 * morph + 0.035 * j) * o.curvature,
            )
        )
        branch = curve(anchor, target, side * (0.07 + 0.04 * math.sin(phase)) * o.curvature)
        body = body.union(spindle(branch, 0.038 * o.swelling, o, tip=0.018))
    outline = Polygon(body.exterior)
    # The focal lens is longitudinal, oblique and eccentric, never a pupil disk.
    lens_path = main[26:74]
    # The lens follows lamina slimming so a low swelling keeps a proportional rim
    # instead of eating the material between cavity and outline (>=1 unchanged).
    lens_width = 0.047 * (0.85 + 0.3 * morph) * min(1.0, o.swelling)
    lens = spindle(lens_path, lens_width, o, tip=0.012)
    shape = body.difference(lens)
    if math.sin(2 * phase + 0.6) > 0.25:
        # An open cleft relates the cavity to the daughter branch, rather than
        # imposing the same closed-rim relationship on every region. Strong
        # curvature can carry the cleft through a daughter branch; shorten it until
        # the lamina stays one connected cut instead of shedding a loose fragment.
        anchor = lens_path[int(0.63 * (len(lens_path) - 1))]
        for reach in (r for r in (1.0, 0.85, 0.7, 0.55, 0.4) if r <= max_cleft):
            notch = curve(anchor, anchor + np.array((0.04, 0.19 * o.curvature * reach)), 0.015)
            cleft = body.difference(lens.union(ribbon(notch, np.linspace(0.018, 0.032,
                                                                         len(notch)))))
            if cleft.geom_type == "Polygon":
                shape = cleft
                break
    segments = 1 + o.complexity if o.segmentation is None else o.segmentation
    for fraction in division_positions(segments):
        k = int(fraction * (len(lens_path) - 1))
        p = lens_path[k]
        tangent = lens_path[min(k + 1, len(lens_path) - 1)] - lens_path[max(0, k - 1)]
        normal = np.array((-tangent[1], tangent[0])) / np.linalg.norm(tangent)
        septum = curve(
            p - 0.085 * normal, p + 0.085 * normal, 0.025 * math.sin(phase + fraction * 3)
        )
        material = ribbon(septum, np.full(len(septum), max(0.012 * o.swelling, septum_radius)))
        # Septa are internal to a fixed lamina outline: growing this nested set
        # cannot move/rescale the silhouette or remove an earlier division.
        shape = shape.union(material.intersection(outline))
    channels = 1 + o.complexity if o.channels is None else o.channels
    if channel_cap is not None:
        channels = min(channels, channel_cap)
    tangent = np.gradient(main, axis=0)
    normals = np.column_stack((-tangent[:, 1], tangent[:, 0]))
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    lens_radii = np.zeros(len(main))
    lu = np.linspace(0, 1, len(lens_path))
    lens_radii[26:74] = 0.012 + lens_width * np.sin(math.pi * lu) ** (
        0.7 * o.taper
    )
    bank_offset = (widths + lens_radii) / 2
    for k in range(channels):
        # The bank follows the actual material between the focal lens and outer
        # edge. It cannot drift outside a narrow root as a fixed Y offset could.
        start = 25 + 16 * k
        segment = (
            main[start : start + 10]
            - normals[start : start + 10] * bank_offset[start : start + 10, None]
        )
        groove = ribbon(segment, np.full(len(segment), 0.004))
        grooved = shape.difference(groove)
        # A channel decorates the lamina; it may never sever it into loose pieces.
        if grooved.geom_type == "Polygon" or shape.geom_type != "Polygon":
            shape = grooved
    transform = [rotation[0, 0], rotation[0, 1], rotation[1, 0], rotation[1, 1], *center]
    shape = affinity.affine_transform(shape, transform)
    outline = affinity.affine_transform(outline, transform)
    path = main @ rotation.T + center
    bank = (main - normals * bank_offset[:, None]) @ rotation.T + center
    return shape, outline, path, bank, (center, rotation, morph, phase)


def finished_profile(polygon, affine):
    # Boolean unions can repeat a vertex exactly. Remove zero-length edges only;
    # no tolerance, smoothing, feature deletion or legacy inventory change.
    return remove_repeated_points(affinity.affine_transform(polygon, affine), tolerance=0)


def _unreplicated_anatomy(c, normalized=False, details=None):
    o = c.parameters
    details = details or {}
    primaries = [primary_anatomy(o, i, *details.get(i, DETAIL_LEVELS[0]))
                 for i in range(o.focal_count)]
    # Size is fitted once from complexity-independent outer anatomy.
    bounds = unary_union([p[1] for p in primaries]).bounds
    sx = (c.envelope.width_mm - 4) / (bounds[2] - bounds[0])
    sy = (c.envelope.height_mm - 4) / (bounds[3] - bounds[1])
    center = np.array(((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2))
    if normalized:
        sx, sy, center = 1.0, 1.0, np.zeros(2)
    affine = [sx, 0, 0, sy, -center[0] * sx, -center[1] * sy]
    base = c.mounting.rear_clearance_mm + c.material.measured_mm
    usable = c.envelope.depth_mm - base - c.material.measured_mm - 14
    result = []
    for i, (shape, outline, path, bank, _) in enumerate(primaries):
        result.append(
            Lobe(
                f"primary-{i}",
                finished_profile(shape, affine),
                base + usable * (0.40 + 0.55 * i / max(o.focal_count - 1, 1)),
                (path - center) * (sx, sy),
                0,
                (bank - center) * (sx, sy),
                finished_profile(outline, affine),
            )
        )
    secondary = min(o.complexity, 1) if o.secondary_lobes is None else o.secondary_lobes
    if secondary:
        for i, (_, outline, path, bank, info) in enumerate(primaries):
            focal, rotation, morph, phase = info
            sub = curve(
                (-0.24, -0.025), (0.23, 0.10 * math.sin(phase)), (0.05 + 0.08 * morph) * o.curvature
            )
            poly = spindle(sub, 0.045 * o.swelling, o, tip=0.017)
            # This is a separate forked recess wall, not a scaled primary curl.
            for j in range(o.complexity):
                anchor = sub[int((0.30 + 0.20 * j) * (len(sub) - 1))]
                end = np.array((0.04 + 0.12 * j, (-1 if j % 2 else 1) * (0.12 + 0.035 * morph)))
                finger = curve(anchor, end, 0.035 * math.cos(phase))
                poly = poly.union(spindle(finger, 0.025 * o.swelling, o, tip=0.016))
            # Side-open recesses leave a substantial middle mounting node.
            # No small closed window floats as a pupil inside the primary lens.
            clefts = []
            for a, b, side in ((17, 32, -1), (66, 81, 1)):
                window = spindle(sub[a:b], 0.012, o, tip=0.008)
                anchor = sub[(a + b) // 2]
                outlet = curve(anchor, anchor + np.array((0, side * 0.14)), 0)
                clefts.append(window.union(ribbon(outlet, np.full(len(outlet), 0.012))))
            opened = poly.difference(unary_union(clefts))
            if opened.geom_type != "Polygon":
                # Keep each side-open recess only where it leaves one connected wall.
                for cleft in clefts:
                    trial = poly.difference(cleft)
                    if trial.geom_type == "Polygon":
                        poly = trial
                opened = poly
            poly = opened
            poly = affinity.affine_transform(
                poly, [rotation[0, 0], rotation[0, 1], rotation[1, 0], rotation[1, 1], *focal]
            )
            world_path = sub @ rotation.T + focal
            result.append(
                Lobe(
                    f"secondary-1-{i}",
                    finished_profile(poly, affine),
                    base + usable * (0.08 + 0.23 * i / max(o.focal_count - 1, 1)),
                    (world_path - center) * (sx, sy),
                    1,
                )
            )
    _unreplicated_anatomy.last_scale = min(sx, sy)
    return result


def _separate_sectors(canonical, step=0.01, limit=40):
    """Move a C3 motif radially until its rotated copies stop overlapping.

    Rotated copies of one lobe share a layer height, so a compact motif (small
    spread, strong curvature) can cross into its neighbouring 120° sector and
    collide with itself. Unaffected motifs are returned unchanged.
    """
    from dataclasses import replace

    def collides(lobes):
        for lobe in lobes:
            for sector in (1, 2):
                rotated = affinity.rotate(lobe.shape, sector * 120, origin=(0, 0))
                # Only copies of the same lobe share a layer height.
                if rotated.intersection(lobe.shape).area > 1e-9:
                    return True
        return False

    if not collides(canonical):
        return canonical
    for n in range(1, limit + 1):
        moved = []
        for lobe in canonical:
            c = np.asarray(lobe.shape.centroid.coords[0])
            offset = c / max(np.linalg.norm(c), 1e-9) * step * n
            moved.append(replace(
                lobe, shape=affinity.translate(lobe.shape, *offset),
                major_outline=(affinity.translate(lobe.major_outline, *offset)
                               if lobe.major_outline is not None else None),
                path=lobe.path + offset,
                backing_path=(lobe.backing_path + offset
                              if lobe.backing_path is not None else None)))
        if not collides(moved):
            return moved
    raise ValueError("laminar C3 motif overlaps its rotated copies; increase spread or "
                     "reduce curvature/swelling")


# Per-lamina detail levels: (max cleft reach, septum radius in mm, channel cap).
# Level 0 is the requested artwork; later levels keep the silhouette and layout but
# grow fragile details to the 10 mm neck / 7 mm ligament manufacturing minimums.
DETAIL_LEVELS = ((1.0, 0.0, None), (0.7, 0.0, None), (0.55, 6.0, None),
                 (0.4, 6.0, 1), (0.0, 6.0, 0))
MIN_NECK_MM, MIN_LIGAMENT_MM = 10, 7


def _cuttable(shape):
    from ..organism_assembly import cut_ligaments, neck_check
    try:
        neck_check(shape, MIN_NECK_MM)
        cut_ligaments(shape, MIN_LIGAMENT_MM)
    except ValueError:
        return False
    return True


def _canonical_index(name, o):
    k = int(name.rsplit("-", 1)[1])
    if o.symmetry == "rotational":
        return k % (o.focal_count // 3)
    if o.symmetry == "bilateral":
        return k - k % 2
    return k


def _fit_details(c):
    """Raise the detail level of each failing lamina until its finished cut passes."""
    o = c.parameters
    levels = {}
    for _ in range(len(DETAIL_LEVELS) * 2):
        lobes, scale = _anatomy(c, levels)
        failing = {_canonical_index(lobe.name, o) for lobe in lobes
                   if not _cuttable(lobe.shape)}
        if not failing:
            break
        raised = False
        for index in failing:
            if levels.get(index, 0) < len(DETAIL_LEVELS) - 1:
                levels[index] = levels.get(index, 0) + 1
                raised = True
        if not raised:
            # Nothing left to adapt; manufacturing reports the actual deficiency.
            return _anatomy(c, {})[0], ()
    else:
        return _anatomy(c, {})[0], ()
    notes = []
    for index, level in sorted(levels.items()):
        cleft, septum, cap = DETAIL_LEVELS[level]
        change = [f"cleft {cleft:.0%}" if cleft < 1 else None,
                  f"septa {2 * septum:g} mm" if septum else None,
                  f"channels <= {cap}" if cap is not None else None]
        notes.append(f"primary-{index}: " + ", ".join(x for x in change if x))
    return lobes, tuple(notes)


_FIT_CACHE = {}


def anatomy_adjustments(c):
    """Human-readable record of manufacturability adaptations made by anatomy(c)."""
    return _fitted(c)[1]


def _fitted(c):
    key = repr(c)
    if key not in _FIT_CACHE:
        if len(_FIT_CACHE) > 16:
            _FIT_CACHE.clear()
        _FIT_CACHE[key] = _fit_details(c)
    return _FIT_CACHE[key]


def anatomy(c):
    """Fitted anatomy. Thin necks from strong curvature, low swelling or a small
    fitted scale adapt clefts/septa/channels per lamina (silhouette unchanged)."""
    return list(_fitted(c)[0])


def _anatomy(c, levels):
    """Author one motif, then copy it exactly; fit uniformly about the grid origin."""
    o = c.parameters

    def details(scale):
        return {i: (cleft, septum / scale if septum else 0.0, cap)
                for i, (cleft, septum, cap) in
                ((i, DETAIL_LEVELS[level]) for i, level in levels.items())}

    if o.symmetry not in ("rotational", "bilateral"):
        # Scale is independent of details: it is fitted to unmodified outlines.
        lobes = _unreplicated_anatomy(c)
        scale = _unreplicated_anatomy.last_scale
        if levels:
            lobes = _unreplicated_anatomy(c, details=details(scale))
        return lobes, scale
    lobes, scale = _symmetric_anatomy(c, {})
    if levels:
        lobes, scale = _symmetric_anatomy(c, details(scale))
    return lobes, scale


def _symmetric_anatomy(c, details):
    from dataclasses import replace
    from .backplate import backplate_polygon
    o = c.parameters
    source = _unreplicated_anatomy(c, normalized=True, details=details)
    count = o.focal_count
    if o.symmetry == "rotational":
        if o.arrangement != "whorl" or count % 3:
            raise ValueError("exact C3 laminar requires whorl and focal_count divisible by3")
        motif = count // 3
        canonical = _separate_sectors(
            [lobe for lobe in source if int(lobe.name.rsplit('-', 1)[1]) < motif])
        copies = []
        for sector in range(3):
            angle = sector * 2 * math.pi / 3
            co, si = math.cos(angle), math.sin(angle)
            rotation = np.array(((co, -si), (si, co)))
            for lobe in canonical:
                j = int(lobe.name.rsplit('-', 1)[1])
                name = lobe.name.rsplit('-', 1)[0] + '-' + str(j + sector * motif)
                copies.append(replace(lobe, name=name,
                    shape=affinity.rotate(lobe.shape, sector * 120, origin=(0, 0)),
                    major_outline=affinity.rotate(lobe.major_outline, sector * 120, origin=(0, 0)) if lobe.major_outline is not None else None,
                    path=lobe.path @ rotation.T,
                    backing_path=lobe.backing_path @ rotation.T if lobe.backing_path is not None else None))
    else:
        if o.arrangement != "bilateral" or count % 2:
            raise ValueError("bilateral laminar requires paired focal_count and bilateral arrangement")
        motif = count // 2
        canonical = [lobe for lobe in source if int(lobe.name.rsplit('-', 1)[1]) % 2 == 0]
        shift = max(lobe.shape.bounds[2] for lobe in canonical) + .035
        copies = []
        for lobe in canonical:
            left = replace(lobe, shape=affinity.translate(lobe.shape, xoff=-shift),
                           major_outline=affinity.translate(lobe.major_outline, xoff=-shift) if lobe.major_outline is not None else None,
                           path=lobe.path - (shift, 0),
                           backing_path=lobe.backing_path - (shift, 0) if lobe.backing_path is not None else None)
            right = replace(left, name=left.name.rsplit('-', 1)[0] + '-' + str(int(left.name.rsplit('-', 1)[1]) + 1),
                            shape=affinity.scale(left.shape, xfact=-1, yfact=1, origin=(0, 0)),
                            major_outline=affinity.scale(left.major_outline, xfact=-1, yfact=1, origin=(0, 0)) if left.major_outline is not None else None,
                            path=left.path * (-1, 1),
                            backing_path=left.backing_path * (-1, 1) if left.backing_path is not None else None)
            copies.extend((left, right))
    # A bounding-box translation after replication would move the rotation center.
    # Inscribed-circle fitting keeps the entire repeated motif on the common board.
    radius = max(np.linalg.norm(np.asarray(lobe.shape.exterior.coords), axis=1).max() for lobe in copies)
    board_radius = backplate_polygon(c).boundary.distance(Point(0, 0))
    scale = min((c.envelope.width_mm - 4) / 2, (c.envelope.height_mm - 4) / 2, board_radius - 2) / radius
    base = c.mounting.rear_clearance_mm + c.material.measured_mm
    usable = c.envelope.depth_mm - base - c.material.measured_mm - 14
    result = []
    for lobe in copies:
        index = int(lobe.name.rsplit('-', 1)[1])
        j = index % motif if o.symmetry == "rotational" else index // 2
        level = (.40 + .55 * j / max(motif - 1, 1)) if lobe.tier == 0 else (.08 + .23 * j / max(motif - 1, 1))
        result.append(replace(lobe, shape=affinity.scale(lobe.shape, xfact=scale, yfact=scale, origin=(0, 0)),
                      major_outline=affinity.scale(lobe.major_outline, xfact=scale, yfact=scale, origin=(0, 0)) if lobe.major_outline is not None else None,
                      path=lobe.path * scale, backing_path=lobe.backing_path * scale if lobe.backing_path is not None else None,
                      z=base + usable * level))
    return sorted(result, key=lambda lobe: (lobe.tier, int(lobe.name.rsplit('-', 1)[1]))), scale
