"""Nested hollow shells for layered-creature modules.

A solid module stacks full silhouettes. A hollow module cuts the layers as
nested shells that tile the rear silhouette, so the whole module comes out of
one blank. The bolts stay: every shell is clamped at its own bores, which the
support planner places on the real grid.

A bolt needs a disk of material around it, and a contour ring is only about
8 mm wide. So each bolt gets a keyhole pad, and every silhouette inside that
shell is offset around the pad by one ring width per level, like contour lines
bending round an obstacle. Rings stay single, disjoint polygons, and the same
cut leaves the pad's shaft and nut clear of the layers above.
"""

from collections import Counter

import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import nearest_points, unary_union

from .backplate import backplate_polygon, mounting_holes
from .creature_profiles import (
    blade_slot,
    hollow_shells,
    module_levels,
    rib_stations,
    retainer_blank,
)

# Ring width kept around a pad, the spoke that joins a pad to its ring, and the
# spacer-column radius shells must clear.
STEP = 7.5
SPOKE = 8.0
COLUMN = 17.0
SCRAP = 3000.0
GOAL = {"root": 0.12, "distal": 0.88, "bend": 0.50}


def _pieces(shape, area=1.0):
    if shape.is_empty:
        return []
    if shape.geom_type == "Polygon":
        return [shape] if shape.area > area else []
    return [
        g for g in getattr(shape, "geoms", ())
        if g.geom_type == "Polygon" and g.area > area
    ]


def _one(shape, opening=0.0):
    """The only polygon of a shape, after dropping slivers. None if it split."""
    parts = _pieces(shape)
    if len(parts) == 1:
        return parts[0]
    if opening and parts:
        parts = _pieces(shape.buffer(-opening, quad_segs=4).buffer(opening, quad_segs=4))
        if len(parts) == 1:
            return parts[0]
    return None


def _filled(shape):
    return Polygon(max(_pieces(shape), key=lambda g: g.area).exterior)


def _mirror(shape):
    return affinity.scale(shape, xfact=-1, yfact=1, origin=(0, 0))


def _span(shape):
    from ..supports import span_axis

    return span_axis(shape)


def _fraction(span, x, y):
    axis, lo, hi = span
    return float(min(max((x * axis[0] + y * axis[1] - lo) / (hi - lo + 1e-9), 0.0), 1.0))


def _window(frac, requirement):
    # Tighter than the planner's own end and bend windows, so a bore is never marginal.
    if requirement == "root":
        return frac <= 0.27
    if requirement == "distal":
        return frac >= 0.73
    return 0.28 <= frac <= 0.72


def _requirements(name, span):
    _axis, lo, hi = span
    # The planner asks a limb longer than 350 mm for a bend support. Ask a little early.
    return ["root", "distal"] + (["bend"] if name != "head" and hi - lo > 340 else [])


def _keyhole(ring, point, radius):
    """Bearing disk plus the spoke that joins it to its ring."""
    disk = Point(point).buffer(radius, quad_segs=12)
    if ring.distance(Point(point)) < 1e-6:
        return disk
    start, _ = nearest_points(ring, Point(point))
    spoke = LineString([(start.x, start.y), point]).buffer(SPOKE / 2, quad_segs=6)
    return unary_union([disk, spoke])


def _terraces(silhouettes, shells, pads, thin):
    """Shells after every pad has pushed the silhouettes inside its ring away.

    A thin ring must bend round the pad, so the cut grows by one ring width
    across it. A wide shell simply takes the notch and stays in one piece. A
    scrap the notch cuts off a shell goes to the shell inside it, so every
    shell stays one polygon.
    """
    top = len(shells) - 1
    cuts = [[] for _ in range(top + 1)]
    for pad in pads:
        reach = 0.0
        for level in range(pad["ring"] + 1, top + 1):
            cuts[level].append(pad["hole"].buffer(reach, quad_segs=8) if reach else pad["hole"])
            reach += STEP if thin[level] else 0.0
    nested = []
    for level, silhouette in enumerate(silhouettes):
        shape = silhouette.difference(unary_union(cuts[level])) if cuts[level] else silhouette
        shape = _one(shape)
        if shape is None:
            return None
        nested.append(shape)
    result = []
    for level in range(top):
        parts = _pieces(nested[level].difference(nested[level + 1]), area=0.0)
        parts = [part for part in parts if part.area > 1]
        if not parts:
            return None
        main = max(parts, key=lambda part: part.area)
        scraps = [part for part in parts if part is not main]
        if scraps:
            grown = _one(unary_union([nested[level + 1], *scraps]).buffer(0))
            if grown is None or any(part.area > SCRAP for part in scraps):
                return None
            nested[level + 1] = grown
        shell = _one(main, opening=0.6)
        if shell is None:
            return None
        result.append(shell)
    cap = shells[-1]
    if cuts[top]:
        cap = cap.difference(unary_union(cuts[top]))
    # The innermost silhouette grew by the scraps handed to it.
    cap = _one(unary_union([cap, nested[top].difference(_filled(shells[-1]))]).buffer(0), opening=0.6)
    if cap is None:
        return None
    result.append(cap)
    return result


class _Seat:
    """Pad planner for one module, using the same rules as the support planner."""

    def __init__(self, c, name, shells, context):
        self.c, self.name = c, name
        self.shells = shells
        self.top = len(shells) - 1
        self.silhouettes = self._nest(shells)
        self.ctx = context
        self.mirrored = name == "head"
        self.edge = max(c.mounting.washer_radius_mm + 2, c.grid.hole_diameter_mm / 2 + 7)
        self.radius = self.edge + 2
        # A shell that cannot hold a bearing disk of its own must be wrapped, not notched.
        self.thin = [
            shapely.length(shapely.maximum_inscribed_circle(shell, tolerance=0.5)) < self.radius
            for shell in shells[:-1]
        ] + [False]
        self.pads = []
        self.why = Counter()

    @staticmethod
    def _nest(shells):
        nested = [None] * len(shells)
        nested[-1] = _filled(shells[-1])
        for level in range(len(shells) - 2, -1, -1):
            nested[level] = _filled(unary_union([shells[level], nested[level + 1]]))
        return nested

    def _points(self, point):
        return [point, (-point[0], point[1])] if self.mirrored else [point]

    def _blocked(self, point):
        """Why the support planner would refuse a bore here, apart from the shells."""
        ctx = self.ctx
        for p in self._points(point):
            spot = Point(p)
            if ctx["foreign"] is not None and ctx["foreign"].intersects(spot.buffer(self.edge + 0.3)):
                return "another module's plate is in the way"
            if ctx["obstacles"] is not None and ctx["obstacles"].intersects(
                    spot.buffer(self.edge + 0.3)):
                return "a rib blade or key is in the way"
            need = COLUMN + self.edge + 0.5
            if any(spot.distance(Point(root)) < need for root in ctx["all_roots"]):
                return "too close to a root spacer column"
            if not ctx["board"].buffer(0.5).covers(spot.buffer(self.radius)):
                return "pad leaves the backplate"
        return None

    def _reasons(self):
        reasons = [(why, n) for why, n in self.why.most_common() if why != "in window"]
        found = f"{self.why['in window']} bores in the end window"
        return found + "".join(f"; {n} {why}" for why, n in reasons)

    def _seated(self, shells, pad):
        for point in pad["points"]:
            spot = Point(point)
            if not shells[pad["ring"]].buffer(0.6).covers(spot.buffer(max(self.edge - 0.6, 1))):
                return False
            for level, shell in enumerate(shells):
                if level != pad["ring"] and shell.intersects(spot.buffer(self.edge + 0.2)):
                    return False
        return _window(_fraction(_span(shells[pad["ring"]]), *pad["points"][0]), pad["requirement"])

    def _ring_candidates(self, ring, requirement):
        span = _span(self.silhouettes[ring])
        used = {tuple(np.round(p, 5)) for pad in self.pads for p in pad["points"]}
        found = []
        reach = STEP * sum(self.thin[ring + 1:self.top])
        for x, y in self.ctx["nodes"]:
            if self.mirrored and x > -1e-6:
                continue
            if (round(-x, 5), round(y, 5)) not in self.ctx["node_set"]:
                continue
            if tuple(np.round((x, y), 5)) in used:
                continue
            frac = _fraction(span, x, y)
            if not _window(frac, requirement):
                continue
            self.why["in window"] += 1
            reason = self._blocked((x, y))
            if reason:
                self.why[reason] += 1
                continue
            outline = self.silhouettes[ring]
            if not outline.buffer(0.3).covers(Point(x, y).buffer(self.radius, quad_segs=12)):
                self.why["pad leaves the layer outline"] += 1
                continue
            hole = _one(_keyhole(self.shells[ring], (x, y), self.radius).intersection(outline))
            if hole is None:
                self.why["pad cannot reach its ring"] += 1
                continue
            points = self._points((x, y))
            if self.mirrored:
                hole = unary_union([hole, _mirror(hole)])
            wrap = hole.buffer(reach, quad_segs=8) if reach else hole
            if wrap.intersects(self.ctx["protect"]):
                self.why["wrap reaches a column, slot or rib bearing"] += 1
                continue
            damage = wrap.intersection(self.shells[-1]).area
            spoke = self.shells[ring].distance(Point(x, y))
            found.append((round(damage), round(spoke), abs(frac - GOAL[requirement]),
                          x, y, hole, points))
        found.sort(key=lambda row: row[:5])
        return found

    def _ring_pads(self):
        for ring in range(self.top):
            span = _span(self.silhouettes[ring])
            for requirement in _requirements(self.name, span):
                for *_key, x, y, hole, points in self._ring_candidates(ring, requirement):
                    pad = {"ring": ring, "hole": hole, "points": points,
                           "requirement": requirement}
                    trial = _terraces(self.silhouettes, self.shells, [*self.pads, pad], self.thin)
                    if trial is None:
                        self.why["rings cannot wrap the pad"] += 1
                        continue
                    if all(self._seated(trial, other) for other in [*self.pads, pad]):
                        self.pads.append(pad)
                        break
                    self.why["pad crowds an earlier bolt"] += 1
                else:
                    raise ValueError(
                        f"{self.name} layer {ring}: no grid bore can carry its {requirement} "
                        f"bolt ({self._reasons()})"
                    )
        shells = _terraces(self.silhouettes, self.shells, self.pads, self.thin)
        if shells is None:
            raise ValueError(f"{self.name}: hollow shells cannot wrap their bolt pads")
        return shells

    def _cap_pads(self, shells):
        ctx = self.ctx
        cap = shells[-1]
        holes = ctx["cap_holes"]
        cut = cap.difference(holes)
        span = _span(cap)
        placed = []
        for requirement in _requirements(self.name, span):
            options = []
            for x, y in ctx["nodes"]:
                if self.mirrored and x > -1e-6:
                    continue
                if (round(-x, 5), round(y, 5)) not in ctx["node_set"]:
                    continue
                points = self._points((x, y))
                if any(tuple(np.round(p, 5)) in placed for p in points):
                    continue
                frac = _fraction(span, x, y)
                if not _window(frac, requirement):
                    continue
                ok = self._blocked((x, y)) is None
                for p in points:
                    spot = Point(p)
                    if (not ok
                            or holes.intersects(spot.buffer(self.edge))
                            or not cut.buffer(0.6).covers(spot.buffer(max(self.edge - 0.6, 1)))
                            or any(s.intersects(spot.buffer(self.edge + 0.2)) for s in shells[:-1])):
                        ok = False
                        break
                if ok:
                    options.append((abs(frac - GOAL[requirement]), x, y, points))
            if not options:
                raise ValueError(f"{self.name} cap: no grid bore can carry its {requirement} bolt")
            placed.extend(tuple(np.round(p, 5)) for p in min(options)[3])

    def seat(self):
        shells = self._ring_pads()
        self._cap_pads(shells)
        return shells


def hollow_layouts(c, plate_profiles, roots_by_module, keys_by_module, voids_by_module, offset):
    """Nested uncut shells for every module, each ready for the ordinary cuts.

    Raises ValueError, naming the module and layer, when a layout cannot seat a
    bolt. A shell is never dropped and a bolt is never removed.
    """
    t, fit = c.material.measured_mm, c.material.clearance_mm
    ox, oy = offset
    names = list(plate_profiles)
    raw = {}
    for name in names:
        if "right" in name:
            continue
        raw[name] = hollow_shells(plate_profiles[name])
    for name in names:
        if "right" in name:
            raw[name] = [_mirror(s) for s in raw[name.replace("right", "left")]]
    levels = {name: module_levels(name, len(raw[name])) for name in names}
    outline = {name: _filled(raw[name][0]) for name in names}
    board = affinity.translate(backplate_polygon(c), xoff=-ox, yoff=-oy)
    nodes = [(h.x_mm - ox, h.y_mm - oy) for h in mounting_holes(c)]
    node_set = {(round(x, 5), round(y, 5)) for x, y in nodes}
    all_roots = [p for name in names for p in roots_by_module[name]]
    layouts = {}
    for name in names:
        if "right" in name:
            continue
        shells = raw[name]
        roots = roots_by_module[name]
        keys = keys_by_module[name]
        slots = [
            box(x - 9 - fit / 2, y - (t + fit) / 2, x + 9 + fit / 2, y + (t + fit) / 2)
            for x, y in keys
        ]
        blades, retainers, ribs = [], [], []
        if name != "head":
            for center, normal, width, _height in rib_stations(name, settings=c.parameters):
                blades.append(blade_slot(center, normal, t, fit))
                along = np.array((normal[1], -normal[0]))
                start, end = center - normal * (width / 2), center + normal * (width / 2)
                ribs.append(LineString([tuple(start), tuple(end)]).buffer(
                    t / 2 + 0.4, cap_style=2, quad_segs=4))
                retainers.append(affinity.affine_transform(
                    retainer_blank(),
                    [normal[0], along[0], normal[1], along[1], center[0], center[1]]))
        # Wraps may not reach a spacer column, a register slot or a rib slot's bearing.
        protect = unary_union([
            *(Point(p).buffer(COLUMN + 0.8) for p in roots),
            *(slot.buffer(4) for slot in slots),
            *(slot.buffer(8) for slot in blades),
        ])
        cap = Polygon(max(_pieces(shells[-1]), key=lambda g: g.area).exterior)
        for p in roots:
            if cap.exterior.distance(Point(p)) < COLUMN + 0.5 or not cap.contains(Point(p)):
                raise ValueError(f"{name}: a hollow ring cannot clear the root spacer column")
        bores = [Point(p).buffer(c.grid.hole_diameter_mm / 2, quad_segs=16) for p in roots]
        top_z = levels[name][-1] + 1
        foreign = [
            outline[other] for other in names
            if other != name and levels[other][0] * t < top_z * t + 12
        ]
        context = {
            "nodes": nodes,
            "node_set": node_set,
            "board": board,
            "all_roots": all_roots,
            "protect": protect,
            "foreign": unary_union(foreign).buffer(0.2) if foreign else None,
            "obstacles": unary_union([*ribs, *retainers]) if ribs else None,
            "cap_holes": unary_union([voids_by_module[name], *bores, *blades]),
        }
        layouts[name] = _Seat(c, name, shells, context).seat()
    for name in names:
        if "right" in name:
            layouts[name] = [_mirror(s) for s in layouts[name.replace("right", "left")]]
    return layouts

