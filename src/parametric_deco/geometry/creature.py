"""Layered armour, root spacers and closed-slot alignment webs; all plywood is planar."""

from dataclasses import asdict
import numpy as np
from shapely.geometry import Point, MultiPoint, box
from shapely.ops import unary_union
from ..model import PartDefinition, PartInstance, GeometryBundle, InterfaceStation, digest
from .creature_profiles import ROOTS, profiles, eye_voids
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
    for name, layers in profiles(c.creature.scale, c.creature.curl).items():
        roots = ROOTS[name]
        match_root_pattern(c, roots)
        keys = key_positions(roots)
        levels = (
            [16 + 2 * j for j in range(len(layers))]
            if name == "head"
            else [3 * j for j in range(len(layers))]
        )
        cap_level = levels[-1]
        root_shape = MultiPoint(roots).convex_hull.buffer(40, quad_segs=12)
        slots = [
            box(x - 9 - fit / 2, y - (t + fit) / 2, x + 9 + fit / 2, y + (t + fit) / 2)
            for x, y in keys
        ]
        station = tuple(
            InterfaceStation(f"key-{j}", x, t + fit, 0, "creature-register-v1")
            for j, (x, y) in enumerate(keys)
        )
        plate_ids = []
        for j, (shape, level) in enumerate(zip(layers, levels)):
            # Fixed-size, substantial roots are construction regions, hidden under the head.
            shape = unary_union([shape, root_shape])
            from shapely import affinity

            voids = [
                affinity.scale(p, xfact=c.creature.scale, yfact=c.creature.scale, origin=(0, 0))
                for p in eye_voids(1 + 0.075 * j if name == "head" else 1.45)
            ]
            shape = shape.difference(unary_union(voids))
            for x, y in roots:
                shape = shape.difference(
                    Point(x, y).buffer(c.grid.hole_diameter_mm / 2, quad_segs=16)
                )
            if j < len(layers) - 1:
                shape = shape.difference(unary_union(slots))
            d = PartDefinition.from_polygon(f"{name}-armour-{j}", shape, t, station, kind="armour")
            definitions.append(d)
            pid = f"{name}-armour-{j}"
            plate_ids.append(pid)
            place(pid, d, base + level * t, name, "cap" if j == len(layers) - 1 else "armour")
        # Compression columns fill only the gaps between manufactured plates.
        for column, (x, y) in enumerate(roots):
            for level in range(cap_level):
                if level in levels:
                    continue
                identifier = f"{name}-column-{column}-{level}"
                transform = ((1, 0, 0, x), (0, 1, 0, y), (0, 0, 1, base + level * t), (0, 0, 0, 1))
                place(identifier, ring, 0, name, "spacer", transform)
        key = PartDefinition.from_polygon(
            f"{name}-register-web", box(-9, 0, 9, cap_level * t), t, station, kind="register"
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
            }
        )
    layout = {
        "family": "creature-mask-v1",
        "manufacturing_request": request_signature(c),
        "modules": modules,
        "templates": [asdict(i) for i in instances],
        "removal_order": ["head", "crown-left", "crown-right", "jaw-left", "jaw-right"],
    }
    layout["fingerprint"] = digest(layout)
    return GeometryBundle(tuple(definitions), tuple(instances)), layout
