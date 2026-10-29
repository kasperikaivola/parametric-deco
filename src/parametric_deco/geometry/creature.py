"""Layered armour, root spacers and closed-slot alignment webs; all plywood is planar."""

from dataclasses import asdict
import numpy as np
from shapely.geometry import Point, MultiPoint, box, Polygon
from shapely.ops import unary_union
from ..model import PartDefinition, PartInstance, GeometryBundle, InterfaceStation, digest
from .creature_profiles import ROOTS, profiles, eye_voids, central_void, rib_stations, smooth
from .backplate import generate_backplate, match_root_pattern


def request_signature(c):
    values = c.to_dict()
    values["creature"].pop("posture")
    values.pop("cutting_bed")
    return digest(values)


def key_positions(roots):
    a, b = np.array(roots, dtype=float)
    vector = b - a
    normal = np.array((-vector[1], vector[0])) / np.linalg.norm(vector)
    return [tuple((a + b) / 2 + sign * 12 * normal) for sign in (-1, 1)]


def generate_creature(c):
    t = c.material.measured_mm
    fit = c.material.clearance_mm
    base = c.mounting.rear_clearance_mm + t
    definitions = []
    instances = []
    modules = []
    backing = generate_backplate(c).definitions[0]
    definitions.append(backing)

    def place(identifier, definition, z, module, role, transform=None):
        if transform is None:
            transform = ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, z), (0, 0, 0, 1))
        instances.append(
            PartInstance(
                identifier, definition.definition_id, definition.revision, transform, module, role
            )
        )

    place("backplate", backing, c.mounting.rear_clearance_mm, "backing", "backplate")
    ring = PartDefinition.from_polygon(
        "creature-root-spacer",
        Point(0, 0)
        .buffer(17, quad_segs=12)
        .difference(Point(0, 0).buffer(c.grid.hole_diameter_mm / 2, quad_segs=12)),
        t,
        kind="spacer",
    )
    definitions.append(ring)
    retainer = PartDefinition.from_polygon(
        "organism-blade-retainer",
        box(-5, -12, 5, 14)
        .union(box(-9, -16, 9, -8))
        .difference(Point(0, 10).buffer(1.25, quad_segs=12)),
        t,
        kind="retainer",
    )
    definitions.append(retainer)
    for name, layers in profiles(c.creature.scale, c.creature.curl).items():
        roots = ROOTS[name]
        match_root_pattern(c, roots)
        keys = key_positions(roots)
        levels = (
            [16 + 2 * j for j in range(len(layers))]
            if name == "head"
            else [3 * j if j < len(layers) - 1 else 3 * j + 1 for j in range(len(layers))]
        )
        cap_level = levels[-1]
        root_shape = MultiPoint(roots).convex_hull.buffer(40, quad_segs=12)
        slots = [
            box(x - 9 - fit / 2, y - (t + fit) / 2, x + 9 + fit / 2, y + (t + fit) / 2)
            for x, y in keys
        ]
        station = tuple(
            InterfaceStation(f"key-{j}", x, t + fit, y, "creature-register-v1")
            for j, (x, y) in enumerate(keys)
        )
        plate_ids = []
        for j, (shape, level) in enumerate(zip(layers, levels)):
            # Fixed-size, substantial roots are construction regions, hidden under the head.
            shape = unary_union([shape, root_shape])
            from shapely import affinity

            voids = [
                affinity.scale(p, xfact=c.creature.scale, yfact=c.creature.scale, origin=(0, 0))
                for p in (*eye_voids(1.06), central_void())
            ]
            if name.startswith("crown"):
                dx = -25 if "left" in name else 25
                voids += [affinity.translate(p, xoff=-dx, yoff=-50) for p in list(voids)]
            shape = shape.difference(unary_union(voids))
            for x, y in roots:
                shape = shape.difference(
                    Point(x, y).buffer(c.grid.hole_diameter_mm / 2, quad_segs=16)
                )
            if j < len(layers) - 1:
                shape = shape.difference(unary_union(slots))
            blade_joints = []
            blade_slots = []
            blade_parts = []
            if name != "head" and j == len(layers) - 1:
                for k, (center, normal, width, height) in enumerate(
                    rib_stations(name, c.creature.scale, c.creature.curl)
                ):
                    nx, ny = normal
                    tangent = np.array((ny, -nx))
                    # A substantial tab crosses a closed cap slot. A separate key bears below.
                    corners = [
                        center + u * normal + v * tangent
                        for u, v in [
                            (-14 - fit / 2, -(t + fit) / 2),
                            (14 + fit / 2, -(t + fit) / 2),
                            (14 + fit / 2, (t + fit) / 2),
                            (-14 - fit / 2, (t + fit) / 2),
                        ]
                    ]
                    slot = Polygon(corners)
                    blade_slots.append(slot)
                    if not shape.buffer(-7).covers(slot):
                        raise ValueError(f"{name} rib {k}: insufficient cap slot bearing")
                    curve = smooth(
                        [
                            (-width / 2, t),
                            (-width * 0.42, height * 0.6),
                            (-width * 0.12, height),
                            (width * 0.2, height * 0.8),
                            (width / 2, t),
                        ]
                    )
                    body = Polygon(curve).union(box(-14, -3 * t, 14, t))
                    body = body.difference(
                        box(-5 - fit / 2, -2 * t - fit / 2, 5 + fit / 2, -t + fit / 2)
                    )
                    blade = PartDefinition.from_polygon(
                        f"organism-{name}-blade-{k}",
                        body,
                        t,
                        (
                            InterfaceStation(
                                "retainer", 0, t + fit, -1.5 * t, "creature-blade-key-v2"
                            ),
                        ),
                        kind="blade",
                    )
                    zcap = base + level * t
                    pose = (
                        (nx, 0, tangent[0], center[0] - t / 2 * tangent[0]),
                        (ny, 0, tangent[1], center[1] - t / 2 * tangent[1]),
                        (0, 1, 0, zcap),
                        (0, 0, 0, 1),
                    )
                    bid, rid = f"{name}-blade-{k}", f"{name}-retainer-{k}"
                    key_pose = (
                        (nx, tangent[0], 0, center[0]),
                        (ny, tangent[1], 0, center[1]),
                        (0, 0, -1, zcap - t),
                        (0, 0, 0, 1),
                    )
                    # x,y,-z is right-handed here because tangent=(ny,-nx).
                    blade_parts.append((bid, blade, pose, rid, key_pose))
                    blade_joints.append(
                        {
                            "blade_id": bid,
                            "retainer_id": rid,
                            "slot_id": f"blade-{k}",
                            "center": center.tolist(),
                            "normal": normal.tolist(),
                            "clip_hole_diameter_mm": 2.5,
                        }
                    )
                shape = shape.difference(unary_union(blade_slots))
            interfaces = (
                station
                if j < len(layers) - 1
                else tuple(
                    InterfaceStation(
                        f"blade-{k}",
                        float(center[0]),
                        t + fit,
                        float(center[1]),
                        "creature-blade-seat-v2",
                    )
                    for k, (center, *_rest) in enumerate(
                        rib_stations(name, c.creature.scale, c.creature.curl)
                    )
                )
                if name != "head"
                else ()
            )
            d = PartDefinition.from_polygon(
                f"organism-{name}-armour-{j}", shape, t, interfaces, kind="armour"
            )
            definitions.append(d)
            pid = f"{name}-armour-{j}"
            plate_ids.append(pid)
            place(pid, d, base + level * t, name, "cap" if j == len(layers) - 1 else "armour")
        for bid, blade, pose, rid, key_pose in blade_parts:
            definitions.append(blade)
            place(bid, blade, 0, name, "blade", pose)
            place(rid, retainer, 0, name, "retainer", key_pose)
        # Compression columns fill only the gaps between manufactured plates.
        for column, (x, y) in enumerate(roots):
            for level in range(cap_level):
                if level in levels:
                    continue
                identifier = f"{name}-column-{column}-{level}"
                transform = ((1, 0, 0, x), (0, 1, 0, y), (0, 0, 1, base + level * t), (0, 0, 0, 1))
                place(identifier, ring, 0, name, "spacer", transform)
        key = PartDefinition.from_polygon(
            f"organism-{name}-register-web", box(-9, 0, 9, cap_level * t), t, kind="register"
        )
        definitions.append(key)
        key_ids = []
        for j, (x, y) in enumerate(keys):
            identifier = f"{name}-web-{j}"
            key_ids.append(identifier)
            transform = ((1, 0, 0, x), (0, 0, -1, y + t / 2), (0, 1, 0, base), (0, 0, 0, 1))
            place(identifier, key, 0, name, "register", transform)
        modules.append(
            {
                "module_id": name,
                "plate_ids": plate_ids,
                "cap_id": plate_ids[-1],
                "key_ids": key_ids,
                "roots": roots,
                "keys": keys,
                "levels": levels,
                "cap_z_mm": base + cap_level * t,
                "blade_joints": blade_joints,
            }
        )
    layout = {
        "family": "creature-organism-v2",
        "manufacturing_request": request_signature(c),
        "modules": modules,
        "templates": [asdict(i) for i in instances],
        "removal_order": ["head", "crown-left", "crown-right", "jaw-left", "jaw-right"],
    }
    layout["fingerprint"] = digest(layout)
    return GeometryBundle(tuple(definitions), tuple(instances)), layout
