"""Separated end clamps, real compression tubes, and immutable machining records.

The source inventory in the layout is a digital pre-machining placement template,
never an alternative set of physical stock. Only the outer inventory is manufactured.
All mounting axes use existing common-board grid bores; only deco contours are machined.
"""
from dataclasses import asdict, replace
import copy
import math

import numpy as np
from shapely.geometry import Point, Polygon, box, MultiPoint, LineString
from shapely.ops import nearest_points, unary_union
from shapely import affinity
from .geometry.symmetry import kind as symmetry_kind, matrices as symmetry_matrices, canonical_id, mapped_id

from .model import Connection, Inventory, Issue, PartDefinition, PartInstance, digest
from .validation import instance_bounds, xy_footprint
from .cad import overlap_volume

REVISION = "triangular-symmetric-mounts-v3"
COMPATIBLE_REVISIONS = (REVISION,)
END_LIMIT = 0.30


def span_axis(shape):
    """Major axis of the minimum-area rectangle, independent of vertex sampling."""
    corners = np.array(shape.minimum_rotated_rectangle.exterior.coords)[:4]
    vectors = np.roll(corners, -1, axis=0) - corners
    vector = vectors[np.argmax(np.linalg.norm(vectors, axis=1))]
    axis = vector / np.linalg.norm(vector)
    if axis[0] < 0 or (abs(axis[0]) < 1e-8 and axis[1] < 0):
        axis = -axis
    values = np.asarray(shape.exterior.coords) @ axis
    return axis, float(values.min()), float(values.max())


def _horizontal(i):
    return abs(i.transform[2][2]) > 1 - 1e-8 and i.role != "backplate"


def _filled(shape):
    return Polygon(shape.exterior)


def _disk(x, y, r):
    return Point(float(x), float(y)).buffer(r, quad_segs=24)


def physical_paths(a, c):
    """Reconstruct structural paths from family geometry and actual part poses.

    No station/path claims from the saved mounting plan enter this calculation.
    Broad head shells retain a planar spread criterion, not a fictitious limb.
    """
    targets = [i for i in a.instances if _horizontal(i) and i.role in ("armour", "cap", "spine", "closure")]
    local = {}
    if c.style == "laminar":
        from .geometry.organism import anatomy
        lobes = {lobe.name + "-plate": lobe for lobe in anatomy(c)}
        local = {i.instance_id: (lobes[canonical_id(i.instance_id, c) if symmetry_kind(c) == "C3" else i.instance_id].path, "laminar-medial") for i in targets}
    elif c.style == "layered-creature":
        from .geometry.creature_profiles import limb_recipe, smooth
        local = {i.instance_id: (smooth(limb_recipe(i.module_id, c.parameters)[0]) * c.parameters.scale,
                                 "creature-limb") for i in targets if i.module_id != "head"}
    elif c.style == "radial-weave":
        from .geometry.weave import radius, xy
        from dataclasses import replace as changed
        for i in targets:
            pose = np.array(i.transform)
            yaw = math.degrees(math.atan2(pose[1, 0], pose[0, 0]))
            design = changed(c.parameters, rotation_deg=c.parameters.rotation_deg - yaw)
            center = math.radians(int(i.module_id[1:]) * 60 + design.rotation_deg)
            offset = -26 if i.role == "closure" else 0
            angles = np.linspace(center - math.radians(29.25), center + math.radians(29.25), 193)
            local[i.instance_id] = (np.array([xy(radius(design, i.module_id[0], angle) + offset, angle)
                                              for angle in angles]), "radial-arc")
    else:
        for i in targets:
            spine = next(p for p in a.instances if p.module_id == i.module_id and p.role == "spine")
            x0, _, x1, _ = a.definition_for(spine).polygon.bounds
            local[i.instance_id] = (np.array(((x0, 0), (x1, 0))), "straight-span")
    result = {}
    for i in targets:
        if i.instance_id in local:
            points, kind = local[i.instance_id]
            vertices = np.array([(*p, 0, 1) for p in points]) @ np.array(i.transform).T
            result[i.instance_id] = (LineString(vertices[:, :2]), kind)
        else:
            shape = xy_footprint(a.definition_for(i), i.transform)
            axis, lo, hi = span_axis(shape)
            origin = np.array(shape.centroid.coords[0])
            origin -= np.dot(origin, axis) * axis
            result[i.instance_id] = (LineString((origin + lo * axis, origin + hi * axis)), "broad-head-span")
    return result


def path_limit(kind):
    # A ~1–2 mm angular/grid rounding discrepancy is immaterial on the radial arcs.
    return .315 if kind == "radial-arc" else END_LIMIT


def path_fraction(path, kind, point):
    if kind == "radial-arc":
        angles = np.unwrap(np.arctan2(np.asarray(path.coords)[:, 1], np.asarray(path.coords)[:, 0]))
        middle = (angles[0] + angles[-1]) / 2
        angle = middle + (math.atan2(point.y, point.x) - middle + math.pi) % (2 * math.pi) - math.pi
        return float((angle - angles[0]) / (angles[-1] - angles[0]))
    return path.project(point, normalized=True)


def end_covered(path, kind, point, end):
    fraction = path_fraction(path, kind, point)
    close = kind not in ("laminar-medial", "creature-limb") or path.distance(point) <= 60
    return close and (fraction <= path_limit(kind) if end == 0 else fraction >= 1 - path_limit(kind))


def _plan(a, c):
    # Keep useful spread/intermediate supports from the original planar layout;
    # then ADD true root/distal supports rather than exchanging one cantilever
    # for another. The final path audit is independent of that initial layout.
    if symmetry_kind(c) != 'none':
        return _orbit_plan(a, c)
    spread = _select_stations(a, c)
    return _select_stations(a, c, spread["stations"], physical_paths(a, c))


def _orbit_plan(a, c):
    """Select complete physical symmetry orbits, with every member feasible."""
    from .geometry.backplate import mounting_holes
    board = next(i for i in a.instances if i.role == 'backplate')
    board_shape = xy_footprint(a.definition_for(board), board.transform)
    filled_board = Polygon(board_shape.exterior)
    base = instance_bounds(a.definition_for(board), board.transform)[1, 2]
    targets = [i for i in a.instances if _horizontal(i) and i.role in ('armour', 'cap', 'spine', 'closure')]
    by_id = {i.instance_id: i for i in a.instances}
    shapes = {i.instance_id: xy_footprint(a.definition_for(i), i.transform) for i in a.instances}
    bounds = {i.instance_id: instance_bounds(a.definition_for(i), i.transform) for i in a.instances}
    holes = {i.instance_id: [Polygon(r) for r in shapes[i.instance_id].interiors] for i in targets}
    paths = physical_paths(a, c)
    nodes = [(h.x_mm, h.y_mm) for h in mounting_holes(c)]
    matrices = symmetry_matrices(c)
    edge = max(c.mounting.washer_radius_mm + 2, c.grid.hole_diameter_mm / 2 + 7)
    selected = []
    def occupied(point):
        return next((s for s in selected if Point(s['xy']).distance(point) < 1e-6), None)
    def feasible(target, point):
        pid = target.instance_id
        disk = point.buffer(edge, quad_segs=24)
        if not filled_board.buffer(1e-7).covers(disk) or shapes[pid].distance(point) > 60:
            return None
        if any(disk.intersects(h) for h in holes[pid]
               if abs(h.area - math.pi * (c.grid.hole_diameter_mm / 2) ** 2) >= 1):
            return None
        top = max(bounds[i.instance_id][1, 2] for i in targets
                  if c.style == 'laminar' or i.module_id == target.module_id)
        plates = []
        for other in a.instances:
            oid = other.instance_id
            if other.role == 'backplate' or bounds[oid][0, 2] >= top + 12:
                continue
            shape = shapes[oid]
            if (other != target and not shape.intersects(disk.buffer(.2))
                    and not (other.module_id == target.module_id and other in targets and shape.distance(point) <= 60)):
                continue
            if other in targets and (other.module_id == target.module_id or c.style == 'laminar'):
                if shape.distance(point) > 60 or any(disk.intersects(h) for h in holes[oid]
                    if abs(h.area - math.pi * (c.grid.hole_diameter_mm / 2) ** 2) >= 1):
                    return None
                plates.append(oid)
            else:
                return None
        if pid not in plates:
            return None
        # Retained original root stacks have physical plywood spacers and their
        # own shaft; an independent support may not collide with those axes.
        if any(module != target.module_id and point.distance(Point(x, y)) < edge + c.mounting.washer_radius_mm + 1
               for module, _, x, y in a.mounting_grid):
            return None
        previous = occupied(point)
        if previous:
            plates = sorted(set(plates) | set(previous['plate_ids']))
        if any(min(bounds[p][1, 2], bounds[q][1, 2]) - max(bounds[p][0, 2], bounds[q][0, 2]) > 1e-6
               for k, p in enumerate(plates) for q in plates[k + 1:]):
            return None
        return plates
    def on_grid(raw):
        # Only accept an existing actual board bore. Rounding an incompatible
        # 120-degree coordinate onto a nearby hole is explicitly forbidden.
        return next((p for p in nodes if np.linalg.norm(np.array(p) - raw) <= 1e-7), None)
    canonical = [i for i in targets if canonical_id(i.instance_id, c) == i.instance_id]
    canonical.sort(key=lambda i: (-shapes[i.instance_id].area, i.instance_id))
    for target in canonical:
        path, pkind = paths[target.instance_id]
        requirements = ('root', 'distal', 'bend') if c.style == 'layered-creature' and target.module_id != 'head' and path.length > 350 else ('root', 'distal')
        for requirement in requirements:
            def meets(point):
                f = path_fraction(path, pkind, point)
                if requirement == 'bend':
                    return .38 <= f <= .62 and path.distance(point) <= 60
                return end_covered(path, pkind, point, int(requirement == 'distal'))
            if any(target.instance_id in s['plate_ids'] and meets(Point(s['xy'])) for s in selected):
                continue
            candidates = []
            for p in nodes:
                point = Point(p)
                if not meets(point):
                    continue
                if symmetry_kind(c) == 'mirror-X' and target.module_id == 'head' and p[0] > 1e-7:
                    continue
                members = {}
                valid = True
                for index, matrix in enumerate(matrices):
                    q = on_grid(matrix @ np.array(p))
                    partner_id = mapped_id(target.instance_id, c, index)
                    if q is None or partner_id not in by_id:
                        valid = False
                        break
                    plates = feasible(by_id[partner_id], Point(q))
                    if plates is None:
                        valid = False
                        break
                    key = tuple(round(v, 7) for v in q)
                    if key not in members:
                        members[key] = {'xy': q, 'plate_ids': set(), 'reference_id': partner_id}
                    members[key]['plate_ids'].update(plates)
                if not valid:
                    continue
                # Every clamped partner and source interference is evaluated,
                # not merely an assumed transform of a good canonical marker.
                if any(any(min(bounds[x][1, 2], bounds[y][1, 2]) - max(bounds[x][0, 2], bounds[y][0, 2]) > 1e-6
                           for k, x in enumerate(sorted(m['plate_ids'])) for y in sorted(m['plate_ids'])[k + 1:])
                       for m in members.values()):
                    continue
                goal = .10 if requirement == 'root' else .90 if requirement == 'distal' else .5
                cost = (abs(path_fraction(path, pkind, point) - goal), shapes[target.instance_id].distance(point), p)
                candidates.append((cost, members))
            if not candidates:
                raise ValueError(f'{target.instance_id}: no complete {symmetry_kind(c)} grid orbit for {requirement}')
            # Simulate ALL accepted cuts plus the complete candidate orbit. A
            # pair of individually safe pads/bores can otherwise sever a neck.
            from types import SimpleNamespace
            def material_ok(members):
                trial = copy.deepcopy(selected)
                for member in members.values():
                    prior = next((s for s in trial if np.linalg.norm(np.array(s['xy']) - member['xy']) < 1e-7), None)
                    if prior:
                        prior['plate_ids'] = sorted(set(prior['plate_ids']) | member['plate_ids'])
                    else:
                        trial.append({'xy': member['xy'], 'plate_ids': sorted(member['plate_ids'])})
                source = SimpleNamespace(assembly=a, inventory=Inventory(a.definitions, a.instances, {}))
                try:
                    stock = _machined_inventory(source, {'stations': trial}, c)
                except ValueError:
                    return False
                manufactured = replace(a, definitions=stock.definitions, instances=stock.instances)
                for station in trial:
                    point = Point(station['xy'])
                    for pid in station['plate_ids']:
                        part = next(i for i in manufactured.instances if i.instance_id == pid)
                        shape = xy_footprint(manufactured.definition_for(part), part.transform)
                        bores = [Polygon(r) for r in shape.interiors]
                        drilled = next((h for h in bores if h.centroid.distance(point) < 1e-5), None)
                        if drilled is None or min([drilled.distance(shape.exterior), *(drilled.distance(h) for h in bores if h != drilled)]) < 7 - 1e-5:
                            return False
                return True
            members = next((members for _, members in sorted(candidates, key=lambda item: item[0]) if material_ok(members)), None)
            if members is None:
                raise ValueError(f'{target.instance_id}: complete orbit severs material or washer web for {requirement}')
            orbit_id = f'orbit-{len(selected)}'
            for member in members.values():
                point = Point(member['xy'])
                previous = occupied(point)
                if previous:
                    previous['plate_ids'] = sorted(set(previous['plate_ids']) | member['plate_ids'])
                    continue
                ref = by_id[member['reference_id']]
                local = np.linalg.inv(np.array(ref.transform)) @ np.array((*member['xy'], 0, 1))
                selected.append({'id': f'end-clamp-{len(selected)}', 'module_id': ref.module_id,
                    'reference_id': ref.instance_id, 'reference_xy': local[:2].tolist(),
                    'xy': list(member['xy']), 'plate_ids': sorted(member['plate_ids']),
                    'board_top_mm': float(base), 'orbit_id': orbit_id, 'purpose': requirement})
    # No saved claims are used by the validator; these rows are inspection data.
    spans = []
    for target in targets:
        path, pkind = paths[target.instance_id]
        stations = [s['id'] for s in selected if target.instance_id in s['plate_ids']]
        spans.append({'part_id': target.instance_id, 'path_kind': pkind, 'station_ids': stations})
    return {'revision': REVISION, 'symmetry': symmetry_kind(c), 'stations': selected, 'spans': spans}


def _select_stations(a, c, retained=None, paths=None):
    board = next(i for i in a.instances if i.role == "backplate")
    board_shape = xy_footprint(a.definition_for(board), board.transform)
    base = instance_bounds(a.definition_for(board), board.transform)[1, 2]
    bores = [_disk(*Polygon(h).centroid.coords[0], c.grid.hole_diameter_mm / 2)
             for h in a.definition_for(board).holes
             if abs(Polygon(h).area - math.pi * (c.grid.hole_diameter_mm / 2) ** 2) < 1]
    filled_board = unary_union([board_shape, *bores])
    shapes = {i.instance_id: xy_footprint(a.definition_for(i), i.transform) for i in a.instances}
    cutouts = {i.instance_id: [Polygon(r) for r in shapes[i.instance_id].interiors]
               for i in a.instances if _horizontal(i)}
    bounds = {i.instance_id: instance_bounds(a.definition_for(i), i.transform) for i in a.instances}
    targets = [i for i in a.instances if _horizontal(i) and i.role in ("armour", "cap", "spine", "closure")]
    washer = c.mounting.washer_radius_mm
    edge = max(washer + 2, c.grid.hole_diameter_mm / 2 + 7)
    reach = 105 if c.style == "radial-weave" else 60
    service = {i.instance_id: _vertical_sections(a, i) for i in targets} if c.style == "radial-weave" else {}
    shared_modules = c.style == "radial-weave" or (c.style == "laminar" and paths is not None)
    selected = copy.deepcopy(retained) if retained else []
    spans = []
    order = sorted(targets, key=lambda i: ((i.role != "spine") if c.style == "radial-weave" else False, -shapes[i.instance_id].area))
    for target in order:
        shape = shapes[target.instance_id]
        axis, low, high = span_axis(shape)
        length = high - low
        stations = []
        path, kind = paths[target.instance_id] if paths else (None, "planar-spread")
        def fraction_at(point):
            return path_fraction(path, kind, point) if path is not None else (np.dot(point.coords[0], axis) - low) / length
        def covered(point, end):
            return end_covered(path, kind, point, end) if path is not None else (
                fraction_at(point) <= END_LIMIT if end == 0 else fraction_at(point) >= 1 - END_LIMIT)
        for end in (0, 1):
            existing = [p for p in selected if (p["module_id"] == target.module_id or shared_modules)
                        and target.instance_id in p["plate_ids"]
                        and covered(Point(p["xy"]), end)]
            if existing:
                chosen = existing[0]
                stations.append(chosen["id"])
                continue
            round_holes = [h for h in cutouts[target.instance_id]
                           if abs(h.area - math.pi * (c.grid.hole_diameter_mm / 2) ** 2) < 1]
            filled_target = unary_union([shape, *round_holes])
            inset = filled_target.buffer(reach)
            if inset.is_empty:
                raise ValueError(f"{target.instance_id}: no end-clamp edge bearing; change dimensions")
            points = []
            # Existing universal board bores are the only permitted axes.
            points.extend((p.centroid.x, p.centroid.y, 0) for p in bores)
            
            
            candidates = []
            for x, y, priority in points:
                point = Point(x, y)
                fraction = fraction_at(point)
                if path is not None:
                    if not covered(point, end):
                        continue
                elif not ((-0.15 <= fraction <= END_LIMIT) if end == 0 else
                          (1 - END_LIMIT <= fraction <= 1.15)):
                    continue
                if c.style == "radial-weave" and point.distance(Point(0, 0)) < c.parameters.opening_radius_mm + edge + 2:
                    continue
                if not inset.covers(point):
                    continue
                bearing = _disk(x, y, edge)
                # Existing circular bores may be reused; decorative channels may not.
                own_holes = round_holes
                filled_target = unary_union([shape, *own_holes])
                if not _filled(filled_target).buffer(reach).covers(point):
                    continue
                if any(bearing.intersects(h) for h in cutouts[target.instance_id]
                       if abs(h.area - math.pi * (c.grid.hole_diameter_mm / 2) ** 2) >= 1):
                    continue
                if not filled_board.buffer(1e-6).covers(bearing):
                    continue
                top = max(bounds[p.instance_id][1, 2] for p in targets
                          if shared_modules or p.module_id == target.module_id)
                plates = []
                clear = True
                for other in a.instances:
                    if other.role == "backplate" or bounds[other.instance_id][0, 2] >= top + 12:
                        continue
                    obstacle = shapes[other.instance_id]
                    if (other != target and not obstacle.intersects(_disk(x, y, edge + .2))
                            and not (other.module_id == target.module_id and _horizontal(other)
                                     and other in targets
                                     and (obstacle.equals(shape) if c.style == "radial-weave"
                                          else obstacle.distance(point) <= reach))):
                        continue
                    if (other.module_id == target.module_id or shared_modules) and _horizontal(other) and other in targets:
                        if not _filled(obstacle).buffer(reach).covers(point):
                            clear = False
                            break
                        # Neither a slot nor an artistic channel may be covered by a washer.
                        annulus = _disk(x, y, edge).difference(_disk(x, y, c.grid.hole_diameter_mm / 2 + .1))
                        if any(annulus.intersection(h).area > 1e-5
                               for h in cutouts[other.instance_id]
                               if abs(h.area - math.pi * (c.grid.hole_diameter_mm / 2) ** 2) >= 1):
                            clear = False
                            break
                        plates.append(other.instance_id)
                    else:
                        clear = False
                        break
                if not clear or target.instance_id not in plates:
                    continue
                if service and any(bearing.intersects(service[pid]) for pid in plates):
                    continue
                if c.style != "radial-weave" and any(module != target.module_id and point.distance(Point(hx, hy)) < edge + washer + 1
                       for module, _, hx, hy in a.mounting_grid):
                    continue
                occupied = [p for p in selected if Point(p["xy"]).distance(point) < 2 * edge + 3]
                shared = next((p for p in occupied if Point(p["xy"]).distance(point) < 1e-6), None)
                if occupied and not (shared and (shared_modules or shared["module_id"] == target.module_id)):
                    continue
                if shared:
                    plates = sorted(set(plates) | set(shared["plate_ids"]))
                if any(min(bounds[p][1, 2], bounds[q][1, 2]) - max(bounds[p][0, 2], bounds[q][0, 2]) > 1e-6
                       for index, p in enumerate(plates) for q in plates[index + 1:]):
                    continue
                # Avoid a new bore grazing any existing board bore.
                if any(point.distance(h.centroid) > .01 and point.distance(h) < edge for h in bores):
                    continue
                candidates.append((priority + (0 if filled_target.covers(bearing) else 2), abs(fraction - ((.10 if end == 0 else .90) if path is not None else (.21 if end == 0 else .79))), x, y, plates))
            if not candidates:
                raise ValueError(f"{target.instance_id}: no clear clamp near {'start' if end == 0 else 'end'}; change geometry")
            _, _, x, y, plates = min(candidates)
            previous = next((p for p in selected if Point(p["xy"]).distance(Point(x, y)) < 1e-6), None)
            chosen = {"id": f"end-clamp-{len(selected)}", "module_id": target.module_id,
                      "reference_id": target.instance_id, "xy": [float(x), float(y)],
                      "plate_ids": plates, "board_top_mm": float(base)}
            local = np.linalg.inv(np.array(target.transform)) @ np.array((x, y, 0, 1))
            chosen["reference_xy"] = local[:2].tolist()
            if previous is not None:
                previous["plate_ids"] = sorted(set(previous["plate_ids"]) | set(plates))
                previous["shared_modules"] = sorted({i.module_id for i in targets if i.instance_id in previous["plate_ids"]})
                chosen = previous
            else:
                selected.append(chosen)
            stations.append(chosen["id"])
        spans.append({"part_id": target.instance_id, "path_kind": kind,
                      "axis_xy": axis.tolist(), "extent_mm": [low, high], "station_ids": stations})
    return {"revision": REVISION, "stations": selected, "spans": spans}


def _vertical_sections(a, slab):
    """Exact XY projection of upright material within a horizontal stock slab."""
    result = []
    bottom = slab.transform[2][3]
    top = bottom + a.definition_for(slab).thickness_mm
    for part in a.instances:
        pose = np.array(part.transform)
        if part.role == "backplate" or abs(pose[2, 1] - 1) > 1e-8:
            continue
        profile = a.definition_for(part)
        cut = profile.polygon.intersection(box(-10000, bottom - pose[2, 3], 10000, top - pose[2, 3]))
        pieces = getattr(cut, "geoms", (cut,))
        for piece in pieces:
            if piece.is_empty or piece.area < 1e-6:
                continue
            x0, _, x1, _ = piece.bounds
            corners = [pose @ np.array((x, 0, z, 1)) for x in (x0, x1) for z in (0, profile.thickness_mm)]
            sweep = (0, 10, 40, 80) if ((a.composition or {}).get("family") == "radial-weave-v1"
                         and slab.role == "spine" and part.role == "rib"
                         and part.module_id == slab.module_id) else (0,)
            for distance in sweep:
                shifted = [p[:2] - pose[:2, 0] * distance for p in corners]
                world = MultiPoint(shifted).convex_hull
                inverse = np.linalg.inv(np.array(slab.transform))
                vertices = [inverse @ np.array((x, y, 0, 1)) for x, y in world.exterior.coords]
                result.append(Polygon([v[:2] for v in vertices]))
    return unary_union(result)


def _machined_inventory(source, plan, c):
    """Each physical cut gets its own new revision; source templates stay digital."""
    a = source.assembly
    definitions, instances, mapping = [], [], {}
    finished = {}
    radius = c.grid.hole_diameter_mm / 2
    for i in a.instances:
        d = a.definition_for(i)
        canonical = canonical_id(i.instance_id, c) if symmetry_kind(c) != 'none' and _horizontal(i) and i.role != 'backplate' else i.instance_id
        if canonical != i.instance_id and canonical in finished:
            source_part = finished[canonical]
            if symmetry_kind(c) == 'C3':
                final = source_part
            else:
                shape = affinity.scale(source_part.polygon, xfact=-1, yfact=1, origin=(0, 0))
                final = PartDefinition.from_polygon(i.instance_id + '-supported', shape, d.thickness_mm, d.interfaces, d.kind)
            mapping[i.instance_id] = [final.definition_id, final.revision]
            if final not in definitions:
                definitions.append(final)
            instances.append(replace(i, definition_id=final.definition_id, revision=final.revision))
            finished[i.instance_id] = final
            continue
        cuts = []
        for s in plan["stations"]:
            if i.instance_id in s["plate_ids"]:
                local = np.linalg.inv(np.array(i.transform)) @ np.array((*s["xy"], 0, 1))
                cuts.append(_disk(*local[:2], radius))
        shape = d.polygon
        obstacles = _vertical_sections(a, i) if cuts else Polygon()
        for s in plan["stations"]:
            if i.instance_id in s["plate_ids"]:
                local = np.linalg.inv(np.array(i.transform)) @ np.array((*s["xy"], 0, 1))
                point = Point(*local[:2])
                safe = shape.difference(obstacles.buffer(max(c.mounting.washer_radius_mm + 2, radius + 7) + .2))
                if c.style == 'layered-creature' and i.module_id == 'head':
                    safe = safe.intersection(box(-10000, -10000, 0, 10000))
                if safe.is_empty:
                    raise ValueError(i.instance_id + ": no material route for end-clamp pad")
                anchor = nearest_points(point, safe)[1]
                from shapely.geometry import LineString
                pad = LineString([point.coords[0], anchor.coords[0]]).buffer(
                    max(c.mounting.washer_radius_mm + 2, radius + 7), quad_segs=16)
                shape = shape.union(pad.difference(obstacles.buffer(.1))).difference(unary_union([Polygon(h) for h in d.holes]))
        shape = shape.difference(unary_union(cuts)) if cuts else shape
        if cuts and c.style == "radial-weave":
            shape = shape.difference(Point(0, 0).buffer(c.parameters.opening_radius_mm + 2, quad_segs=96))
        if c.style == 'layered-creature' and i.module_id == 'head' and _horizontal(i):
            half = shape.intersection(box(-10000, -10000, 0, 10000))
            shape = half.union(affinity.scale(half, xfact=-1, yfact=1, origin=(0, 0)))
        # Per-instance revisions are required where identical source profiles get
        # different drilled supports. Never overwrite source geometry in place.
        final = PartDefinition.from_polygon(i.instance_id + "-supported", shape, d.thickness_mm,
                                            d.interfaces, d.kind) if cuts else d
        finished[i.instance_id] = final
        mapping[i.instance_id] = [final.definition_id, final.revision]
        if (final.definition_id, final.revision) not in {(p.definition_id, p.revision) for p in definitions}:
            definitions.append(final)
        instances.append(replace(i, definition_id=final.definition_id, revision=final.revision))
    layout = {"support_revision": REVISION, "source_template": source.inventory.to_dict(),
              "plan": plan, "part_mapping": mapping,
              "support_settings": {"grid": asdict(c.grid), "mounting": asdict(c.mounting),
                                   "backplate": asdict(c.backplate), "material": asdict(c.material)}}
    layout["fingerprint"] = digest(layout)
    return Inventory(tuple(definitions), tuple(instances), layout)


def _placed_plan(plan, a):
    result = copy.deepcopy(plan)
    by_id = {i.instance_id: i for i in a.instances}
    for station in result["stations"]:
        ref = by_id[station["reference_id"]]
        point = np.array(ref.transform) @ np.array((*station["reference_xy"], 0, 1))
        station["xy"] = point[:2].tolist()
    return result


def _hardware(a, plan, c):
    """Model specified M6 shafts, washers and cut-to-length rigid metal tubes.

    Tube OD 12 / ID 6.5, washers OD18 / ID6.5, shaft nominal6.
    Threads, nut flats and preload are not modeled or physically validated.
    """
    definitions, instances, connections = list(a.definitions), list(a.instances), list(a.connections)
    by_id = {i.instance_id: i for i in a.instances}
    board = next(i for i in a.instances if i.role == "backplate")
    board_bounds = instance_bounds(a.definition_for(board), board.transform)
    for s in plan["stations"]:
        x, y = s["xy"]
        plates = sorted([by_id[p] for p in s["plate_ids"]], key=lambda p: p.transform[2][3])
        s["shared_modules"] = sorted({p.module_id for p in plates})
        z = board_bounds[1, 2]
        segments = []
        for p in plates:
            bottom = instance_bounds(a.definition_for(p), p.transform)[0, 2]
            if bottom > z + 1e-6:
                segments.append(("tube", z, bottom, 6, c.grid.hole_diameter_mm / 2))
            z = instance_bounds(a.definition_for(p), p.transform)[1, 2]
            connections.append(Connection(p.instance_id, board.instance_id, "end-clamp-v1", s["id"]))
        s["top_mm"] = float(z)
        segments.extend((("washer-front", z, z + 1.5, c.mounting.washer_radius_mm, 3.25),
                         ("washer-rear", board_bounds[0, 2] - 1.5, board_bounds[0, 2], c.mounting.washer_radius_mm, 3.25),
                         ("shaft", board_bounds[0, 2] - 1.5, z + 7, 3, 0),
                         ("head", board_bounds[0, 2] - 5.5, board_bounds[0, 2] - 1.5, 5, 0),
                         ("locking-nut", z + 1.5, z + 6.5, 5.7, 3.25)))
        hardware_ids = []
        for index, (kind, start, end, outer, inner) in enumerate(segments):
            shape = _disk(0, 0, outer)
            if inner:
                shape = shape.difference(_disk(0, 0, inner))
            name = s["id"] + f"-{kind}-{index}"
            candidate = PartDefinition.from_polygon("hardware-shape", shape, end - start, kind="purchased-hardware")
            d = PartDefinition.from_polygon("hardware-" + candidate.fingerprint[:14], shape, end - start, kind="purchased-hardware")
            if (d.definition_id, d.revision) not in {(p.definition_id, p.revision) for p in definitions}:
                definitions.append(d)
            pose = ((1, 0, 0, x), (0, 1, 0, y), (0, 0, 1, start), (0, 0, 0, 1))
            instances.append(PartInstance(name, d.definition_id, d.revision, pose, s["module_id"], "mounting-hardware"))
            connections.append(Connection(name, plates[-1].instance_id, "end-clamp-v1", s["id"]))
            hardware_ids.append(name)
        s["hardware_ids"] = hardware_ids
    # Complete the documented original load graph: caps capture webs; lower armour
    # is clamped on columns; closures are held by the original board bolts.
    for m in (a.composition or {}).get("modules", []):
        cap = m.get("cap_id", m.get("closure_id", m.get("plate_id")))
        if cap:
            for pid in (*m.get("plate_ids", []), *m.get("key_ids", []), *m.get("spine_ids", [])):
                if pid != cap:
                    connections.append(Connection(pid, cap, "end-clamp-v1", "captured-load-path"))
    metadata = {**(a.composition or {}), "end_supports": plan,
                "universal_backplate": {"standard": "universal-triangular-board-v3",
                    "definition_id": a.definition_for(board).definition_id,
                    "fingerprint": a.definition_for(board).fingerprint,
                    "grid": asdict(c.grid), "backplate": asdict(c.backplate),
                    "stock_mm": c.material.measured_mm,
                    "size_mm": [c.envelope.width_mm, c.envelope.height_mm],
                    "grid_hole_count": len(a.definition_for(board).holes)},
                "support_hardware": {"tube_od_mm": 12, "tube_id_mm": c.grid.hole_diameter_mm,
                                     "shaft_diameter_mm": 6, "washer_thickness_mm": 1.5,
                                     "material": "rigid metal tube; M6 through bolts with locking nuts",
                                     "nut_and_head": "select M6 locking nut/head within 12 mm allowance; physical selection NOT RUN",
                                     "physical_validation": "NOT RUN"}}
    bounds = a.hardware_bounds
    if c.style == "radial-weave":
        for station in plan["stations"]:
            station["replaces_root_references"] = [list(m) for m in a.mounting_grid
                if Point(station["xy"]).distance(Point(m[2], m[3])) < 1e-6]
        bounds = tuple(b for b in bounds if not any(
            Point(station["xy"]).distance(Point((b[1] + b[4]) / 2, (b[2] + b[5]) / 2)) < 1e-6
            for station in plan["stations"]))
    return replace(a, definitions=tuple(definitions), instances=tuple(instances),
                   connections=tuple(connections), hardware_bounds=bounds, composition=metadata)


def verify_supports(a, config=None):
    """Check manufactured bores, annular bearings, gap-free columns and graph reachability."""
    issues = []
    plan = (a.composition or {}).get("end_supports")
    if not plan:
        return (Issue("error", "end_support", "separated-end support record missing"),)
    by_id = {i.instance_id: i for i in a.instances}
    width, height, depth = a.envelope_mm
    for part in a.instances:
        bounds = instance_bounds(a.definition_for(part), part.transform)
        if np.any(bounds[0] < np.array((-width / 2, -height / 2, 0)) - 1e-6) or np.any(bounds[1] > np.array((width / 2, height / 2, depth)) + 1e-6):
            issues.append(Issue("error", "support_envelope", "finished part or clamp hardware exceeds envelope", (part.instance_id,)))
    board = next(i for i in a.instances if i.role == "backplate")
    standard = (a.composition or {}).get("universal_backplate", {})
    if a.definition_for(board).fingerprint != standard.get("fingerprint"):
        issues.append(Issue("error", "support_grid", "manufactured universal board revision differs"))
    if config is None:
        from .config import config_from_dict
        values = (a.composition or {}).get("support_config")
        config = config_from_dict(values) if values else None
    paths = physical_paths(a, config) if config is not None else {}
    if not paths:
        issues.append(Issue("error", "end_support_path", "configuration required for independent physical path audit"))
    for pid, (path, kind) in paths.items():
        matching = [s for s in plan["stations"] if pid in s["plate_ids"]]
        fractions = sorted(path_fraction(path, kind, Point(s["xy"])) for s in matching)
        if not (any(end_covered(path, kind, Point(s["xy"]), 0) for s in matching)
                and any(end_covered(path, kind, Point(s["xy"]), 1) for s in matching)):
            issues.append(Issue("error", "end_support_path", "supports miss the real root or distal path region", (pid,)))
        for span in plan["spans"]:
            if span["part_id"] == pid:
                span["path_kind"] = kind
                span["path_length_mm"] = path.length
                span["placed_station_fractions"] = [float(f) for f in fractions]
                span["path_endpoints_mm"] = [list(path.coords[0]), list(path.coords[-1])]
    for s in plan["stations"]:
        x, y = s["xy"]
        for pid in (board.instance_id, *s["plate_ids"]):
            p = by_id.get(pid)
            if p is None:
                issues.append(Issue("error", "support_bore", "missing clamped part", (pid,)))
                continue
            shape = xy_footprint(a.definition_for(p), p.transform)
            bore = _disk(x, y, 3.01)
            bearing = _disk(x, y, 9).difference(_disk(x, y, 3.35))
            if shape.intersection(bore).area > 1e-5 or bearing.difference(shape).area > 1e-4:
                issues.append(Issue("error", "support_bore", "unaligned bore or missing washer bearing", (pid,)))
            point = Point(x, y)
            holes = [Polygon(r) for r in shape.interiors]
            drilled = [h for h in holes if h.centroid.distance(point) < 1e-5]
            if drilled:
                h = drilled[0]
                gaps = [h.distance(shape.exterior), *(h.distance(other) for other in holes if other != h)]
                if min(gaps) < 7 - 1e-5:
                    issues.append(Issue("error", "support_web", "finished bore ligament below 7 mm", (pid,)))
        tubes = []
        for hid in s.get("hardware_ids", []):
            p = by_id.get(hid)
            if p is None:
                issues.append(Issue("error", "support_hardware", "missing support hardware", (hid,)))
                continue
            b = instance_bounds(a.definition_for(p), p.transform)
            if np.linalg.norm(np.array(p.transform)[:2, 3] - (x, y)) > 1e-6:
                issues.append(Issue("error", "support_hardware", "hardware axis misaligned", (hid,)))
            if "-tube-" in hid:
                tubes.append((b[0, 2], b[1, 2]))
            if "-shaft-" in hid:
                board_bottom = instance_bounds(a.definition_for(board), board.transform)[0, 2]
                if b[0, 2] > board_bottom - 1.5 + 1e-6 or b[1, 2] < s["top_mm"] + 6.5:
                    issues.append(Issue("error", "support_hardware", "shaft does not span complete clamp stack", (hid,)))
        plates = sorted([by_id[p] for p in s["plate_ids"] if p in by_id], key=lambda p: p.transform[2][3])
        end = instance_bounds(a.definition_for(board), board.transform)[1, 2]
        for p in plates:
            b = instance_bounds(a.definition_for(p), p.transform)
            if b[0, 2] > end + 1e-6 and not any(abs(lo - end) < 1e-6 and abs(hi - b[0, 2]) < 1e-6 for lo, hi in tubes):
                issues.append(Issue("error", "support_column", "unfilled compression gap", (p.instance_id,)))
            end = b[1, 2]
    wood = [i for i in a.instances if i.role != "mounting-hardware"]
    wood_shapes = {i.instance_id: xy_footprint(a.definition_for(i), i.transform) for i in wood}
    wood_bounds = {i.instance_id: instance_bounds(a.definition_for(i), i.transform) for i in wood}
    for h in (i for i in a.instances if i.role == "mounting-hardware"):
        hb = instance_bounds(a.definition_for(h), h.transform)
        hs = xy_footprint(a.definition_for(h), h.transform)
        for w in wood:
            wb = wood_bounds[w.instance_id]
            if min(hb[1, 2], wb[1, 2]) - max(hb[0, 2], wb[0, 2]) > 1e-6 and hs.intersection(wood_shapes[w.instance_id]).area > 1e-5:
                issues.append(Issue("error", "support_collision", "support hardware crosses manufactured material", (h.instance_id, w.instance_id)))
    # Original source root shafts also need actual universal bores; their
    # presence cannot be excused by correctly aligned added end clamps.
    board_shape = xy_footprint(a.definition_for(board), board.transform)
    for module, _, x, y in a.mounting_grid:
        holes = [Polygon(r) for r in board_shape.interiors]
        if not any(h.centroid.distance(Point(x, y)) < 1e-7 for h in holes):
            issues.append(Issue("error", "support_grid", "original root has no universal board bore", (module,)))
    # Every board station must coincide with the same pre-existing coarse grid.
    for s in plan["stations"]:
        g = standard.get("grid", {})
        if g:
            x, y = s["xy"]
            row = round((y - g["origin_y_mm"]) / g["pitch_y_mm"])
            shift = g["origin_x_mm"] + (row % 2) * g["offset_mm"]
            column = round((x - shift) / g["pitch_x_mm"])
            if abs(x - (shift + column * g["pitch_x_mm"])) > 1e-6 or abs(y - (g["origin_y_mm"] + row * g["pitch_y_mm"])) > 1e-6:
                issues.append(Issue("error", "support_grid", "support axis is off the universal hole grid", (s["id"],)))
        shape = xy_footprint(a.definition_for(board), board.transform)
        if shape.intersection(_disk(*s["xy"], 3.01)).area > 1e-5:
            issues.append(Issue("error", "support_grid", "support has no universal board bore", (s["id"],)))
    graph = {name: set() for name in by_id}
    for connection in a.connections:
        if connection.a in graph and connection.b in graph:
            graph[connection.a].add(connection.b)
            graph[connection.b].add(connection.a)
    reached, todo = set(), [board.instance_id]
    while todo:
        name = todo.pop()
        if name not in reached:
            reached.add(name)
            todo.extend(graph[name] - reached)
    for missing in set(by_id) - reached:
        issues.append(Issue("error", "floating_part", "no connection path to backplate", (missing,)))
    plan["all_parts_reach_backplate"] = not bool(set(by_id) - reached)
    if config is not None:
        from .geometry.symmetry import verify_symmetry
        issues.extend(verify_symmetry(a, config))
    return tuple(issues)


def _new_material_issues(before, after):
    """Only changed construction regions need new solid-kernel collision checks."""
    old = {i.instance_id: i for i in before.instances}
    wooden = [i for i in after.instances if i.role != "mounting-hardware"]
    shapes = {i.instance_id: xy_footprint(after.definition_for(i), i.transform) for i in wooden}
    bounds = {i.instance_id: instance_bounds(after.definition_for(i), i.transform) for i in wooden}
    checked, issues = set(), []
    for part in wooden:
        if not _horizontal(part):
            continue
        previous = old[part.instance_id]
        added = shapes[part.instance_id].difference(xy_footprint(before.definition_for(previous), previous.transform))
        if added.area < 1e-6:
            continue
        pb = bounds[part.instance_id]
        for other in wooden:
            pair = tuple(sorted((part.instance_id, other.instance_id)))
            ob = bounds[other.instance_id]
            if (other == part or pair in checked or
                    min(pb[1, 2], ob[1, 2]) - max(pb[0, 2], ob[0, 2]) <= 1e-6 or
                    added.intersection(shapes[other.instance_id]).area <= 1e-6):
                continue
            checked.add(pair)
            if overlap_volume(after.definition_for(part), part.transform,
                              after.definition_for(other), other.transform) > 1e-5:
                issues.append(Issue("error", "support_pad_collision", "new construction pad crosses another cut", pair))
    return tuple(issues)


def _prepare_source(source, c):
    """Universal stock board; laminar plates use grid clamps instead of unique seats."""
    from .geometry.backplate import generate_backplate
    board = generate_backplate(c).definitions[0]
    definitions = [d for d in source.assembly.definitions if d.kind != "backplate"]
    definitions.append(board)
    instances = [replace(i, definition_id=board.definition_id, revision=board.revision)
                 if i.role == "backplate" else i for i in source.assembly.instances]
    metadata = copy.deepcopy(source.assembly.composition)
    connections = list(source.assembly.connections)
    hardware, mounts = source.assembly.hardware_bounds, source.assembly.mounting_grid
    if c.style == "radial-weave":
        levels = {m["module_id"]: m["level"] for m in metadata["modules"]}
        for index, i in enumerate(instances):
            if i.role != "rib" or levels[i.module_id] != "low":
                continue
            old_part = source.assembly.definition_for(i)
            clipped = old_part.polygon.intersection(box(-1000, -1000, 1000, 70)).union(box(-32, 70, -20, 70 + old_part.thickness_mm))
            part = PartDefinition.from_polygon(i.instance_id + "-captured-profile", clipped,
                                               old_part.thickness_mm, old_part.interfaces, old_part.kind)
            definitions.append(part)
            instances[index] = replace(i, definition_id=part.definition_id, revision=part.revision)
        used = {(i.definition_id, i.revision) for i in instances}
        definitions = [d for d in definitions if (d.definition_id, d.revision) in used]
    if c.style == "laminar":
        from .geometry.organism import anatomy
        lobes = {lobe.name + "-plate": lobe for lobe in anatomy(c)}
        definitions = [board]
        instances = [i for i in instances if i.role != "register"]
        for index, i in enumerate(instances):
            if i.role == "backplate":
                continue
            canonical = canonical_id(i.instance_id, c) if symmetry_kind(c) == 'C3' else i.instance_id
            d = PartDefinition.from_polygon(canonical + "-grid-clamped", lobes[canonical].shape,
                                            c.material.measured_mm, kind="armour")
            if d not in definitions:
                definitions.append(d)
            pose = np.array(i.transform)
            if symmetry_kind(c) == 'C3':
                sector = int(i.module_id.rsplit('-', 1)[1]) // (c.parameters.focal_count // 3)
                pose[:2, :2] = symmetry_matrices(c)[sector]
            instances[index] = replace(i, definition_id=d.definition_id, revision=d.revision, transform=pose)
        connections, hardware, mounts = [], (), ()
        for m in metadata["modules"]:
            m["roots"], m["web_ids"], m["slot_polygons"] = [], [], []
        metadata["construction"] = {"plywood_parts": len(instances), "spacers": 0, "retainers": 0,
                                    "mounting": "two separated universal-grid tube clamps per plate"}
    a = replace(source.assembly, definitions=tuple(definitions), instances=tuple(instances),
                connections=tuple(connections), hardware_bounds=hardware, mounting_grid=mounts,
                composition=metadata)
    # Remove only source checks whose scope was intentionally the family-specific
    # through-board void, now replaced by universal stock. Deco apertures stay open.
    errors = tuple(i for i in source.report.issues if not (
        i.code in ("central_opening", "eye_channel") and "backplate" in i.message))
    return replace(source, assembly=a, report=replace(source.report, issues=errors))


def supported_build(c, inventory, assemble_source):
    if not 6.2 <= c.grid.hole_diameter_mm <= 7:
        raise ValueError("separated-end M6 clamps require board bores 6.2..7 mm; change hardware design/new cuts")
    if inventory is None:
        source = _prepare_source(assemble_source(c), c)
        plan = _plan(source.assembly, c)
        physical = _machined_inventory(source, plan, c)
    else:
        inventory = Inventory.from_dict(inventory.to_dict())
        layout = copy.deepcopy(inventory.layout)
        if not isinstance(layout, dict) or layout.get("support_revision") not in COMPATIBLE_REVISIONS:
            raise ValueError("inventory predates separated-end support machining; requires new cuts")
        fingerprint = layout.pop("fingerprint", None)
        if digest(layout) != fingerprint:
            raise ValueError("stale support inventory layout fingerprint")
        if layout["support_settings"] != {"grid": asdict(c.grid), "mounting": asdict(c.mounting),
                                           "backplate": asdict(c.backplate), "material": asdict(c.material)}:
            raise ValueError("manufactured support hardware/board settings differ; requires new cuts")
        expected = layout["part_mapping"]
        if {i.instance_id: [i.definition_id, i.revision] for i in inventory.instances} != expected:
            raise ValueError("missing or stale manufactured support inventory")
        source_roles = {i["instance_id"]: (i["role"], i["module_id"], i.get("station_id"))
                        for i in layout["source_template"]["instances"]}
        if any((i.role, i.module_id, i.station_id) != source_roles.get(i.instance_id)
               for i in inventory.instances):
            raise ValueError("stale manufactured inventory role or ownership")
        source = _prepare_source(assemble_source(c, Inventory.from_dict(layout["source_template"])), c)
        physical = inventory
        plan = _placed_plan(layout["plan"], source.assembly)
    mapping = physical.layout["part_mapping"]
    instances = tuple(replace(i, definition_id=mapping[i.instance_id][0], revision=mapping[i.instance_id][1])
                      for i in source.assembly.instances)
    a = replace(source.assembly, definitions=physical.definitions, instances=instances)
    a = _hardware(a, copy.deepcopy(plan), c)
    a = replace(a, composition={**a.composition, "support_config": c.to_dict()})
    evidence_issues = ()
    if c.style == "radial-weave":
        from .weave_assembly import weave_evidence
        metadata, evidence_issues = weave_evidence(a, source.report)
        a = replace(a, composition=metadata)
    support_issues = verify_supports(a)
    if inventory is not None and any(i.code == "end_support_path" for i in support_issues):
        raise ValueError("saved stock lacks real root/distal path supports; requires new cuts")
    issues = (*support_issues, *_new_material_issues(source.assembly, a), *evidence_issues)
    report = replace(source.report, issues=(*source.report.issues, *issues))
    return replace(source, assembly=a, fabrication_parts=physical.definitions, report=report,
                   inventory=physical,
                   warnings=(*source.warnings, "Separated-end M6 clamp tubes are specified geometry; physical stiffness/fit NOT RUN."))
