"""Planar laser-cut radial modules for a two-strand relief braid.

Ribs slide radially inward; closed tongue windows in the upper rail retain them.
All wood is real connected planar geometry. No twisted extrusion or hidden lock.
"""

from dataclasses import asdict
from functools import lru_cache
from itertools import combinations
import math

import numpy as np
from shapely.geometry import MultiPoint, Point, Polygon, box
from shapely.ops import nearest_points, unary_union

from ..model import GeometryBundle, InterfaceStation, PartDefinition, PartInstance
from .backplate import mounting_holes
from .joints import slot_width


def manufacturing_request(config):
    return {
        "material": asdict(config.material),
        "grid": asdict(config.grid),
        "backplate": asdict(config.backplate),
        "mounting": asdict(config.mounting),
        "backing_size_mm": [config.envelope.width_mm, config.envelope.height_mm],
    }


def radius(design, strand, theta):
    return design.radius_mm + (1 if strand == "a" else -1) * design.amplitude_mm * math.sin(
        3 * (theta - math.radians(design.rotation_deg))
    )


def xy(r, theta):
    return (r * math.cos(theta), r * math.sin(theta))


def radial_rectangle(r, theta, u0, u1, v0, v1):
    er = np.array((math.cos(theta), math.sin(theta)))
    et = np.array((-math.sin(theta), math.cos(theta)))
    return Polygon([r * er + u * er + v * et for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))])


def band(design, strand, start, end, inner, outer):
    angles = np.linspace(start, end, 97)
    return Polygon(
        [xy(radius(design, strand, a) + outer, a) for a in angles]
        + [xy(radius(design, strand, a) + inner, a) for a in reversed(angles)]
    )


def rib_definition(level, index, t, width, crest, outer):
    low, high = (20, 44) if level == "low" else (102, 126)
    lid = 70 if level == "low" else 152
    bottom = 0 if index in (0, 8) else (10 if level == "low" else 92)
    # Inner web carries the paired notches and top capture tongue. Outer fins taper.
    profile = unary_union(
        [
            box(-50, bottom, 0, lid),
            box(-32, lid, -20, lid + t),
            Polygon(
                (
                    (0, bottom + 10),
                    (outer, bottom + 20),
                    (outer, crest - 15),
                    (outer * 0.6, crest),
                    (0, lid),
                )
            ),
        ]
    )
    for z in (low, high):
        profile = profile.difference(
            box(0, z - (width - t) / 2, outer + 1, z + t + (width - t) / 2)
        )
    station = InterfaceStation("pair", 0, width, 0, "radial-slide-" + level + "-v1")
    part = PartDefinition.from_polygon("candidate", profile, t, (station,), kind="rib")
    return PartDefinition.from_polygon(
        "weave-" + level + "-fin-" + part.fingerprint[:10], profile, t, (station,), kind="rib"
    )


@lru_cache(maxsize=8)
def generate_weave(config, root_flips=()):
    design = config.parameters
    if design is None:
        raise ValueError("composition is required for radial weave")
    t, w = config.material.measured_mm, slot_width(config)
    zbase = config.mounting.rear_clearance_mm + t
    modules = []
    rib_defs = {}
    rib_footprints = []
    offsets = [
        math.radians(25 * math.copysign(abs(v) ** 1.5, v)) if v else 0.0
        for v in np.linspace(-1, 1, 9)
    ]
    for strand in ("a", "b"):
        for crossing in range(6):
            name = f"{strand}{crossing}"
            centre = crossing * math.pi / 3 + math.radians(design.rotation_deg)
            level = "high" if (crossing % 2 == 0) == (strand == "a") else "low"
            lid = 152 if level == "high" else 70
            zlevels = (102, 126) if level == "high" else (20, 44)
            start, end = centre - math.radians(29.25), centre + math.radians(29.25)
            sector = Polygon([(0, 0), *[xy(2000, a) for a in np.linspace(start, end, 40)]])
            end_sign = (1 if strand == "a" else -1) * (-1 if name in root_flips else 1)
            root_theta = centre + end_sign * math.radians(20)
            root_centre = Point(xy(radius(design, strand, root_theta), root_theta))
            pads = []
            for offset in (14, 18, 22, 25):
                theta = centre + end_sign * math.radians(offset)
                r = radius(design, strand, theta)
                pads.append(
                    Point(xy(r + (25 if r > design.radius_mm else 20), theta)).buffer(
                        55, quad_segs=24
                    )
                )
            pad = (
                unary_union(pads)
                .intersection(sector)
                .difference(Point(0, 0).buffer(design.opening_radius_mm + 2, quad_segs=96))
            )
            spine = unary_union([band(design, strand, start, end, -12, 12), pad])
            rail = unary_union([band(design, strand, start, end, -42, -10), pad])
            ribs = []
            stations = []
            for j, offset in enumerate(offsets):
                theta = centre + offset
                r = radius(design, strand, theta)
                # Placement-template profile. Final support machining trims any
                # low crest above its capture rail (supports._prepare_source).
                crest = (
                    152
                    if level == "high"
                    else round(70 + 82 * max(0.0, (abs(math.sin(3 * (theta - math.radians(design.rotation_deg)))) - 0.8) / 0.2), 6)
                )
                outer = round(36 + 16 * math.sin(math.pi * j / 8), 6)
                part = rib_definition(level, j, t, w, crest, outer)
                rib_defs[part.definition_id] = part
                co, si = math.cos(theta), math.sin(theta)
                transform = (
                    (co, 0, si, r * co - t * si / 2),
                    (si, 0, -co, r * si + t * co / 2),
                    (0, 1, 0, zbase),
                    (0, 0, 0, 1),
                )
                instance = PartInstance(
                    f"{name}-fin-{j}",
                    part.definition_id,
                    part.revision,
                    transform,
                    name,
                    "rib",
                    f"s{j}",
                )
                ribs.append(instance)
                rib_footprints.append((name, radial_rectangle(r, theta, -50, outer, -t / 2, t / 2)))
                stations.append(
                    InterfaceStation(
                        f"s{j}", math.degrees(theta), w, 0, "radial-slide-" + level + "-v1"
                    )
                )
                spine = spine.difference(radial_rectangle(r, theta, -100, 0, -w / 2, w / 2))
                rail = rail.difference(
                    radial_rectangle(r, theta, -32 - (w - t) / 2, -20 + (w - t) / 2, -w / 2, w / 2)
                )
                if crest > lid:
                    # Tall outer crests need an open clearance in the root pad, not
                    # a fictitious solid plate through the standing fin.
                    rail = rail.difference(radial_rectangle(r, theta, 0, 100, -w / 2, w / 2))
            # Slotting a broad root region can cut off pad offcuts. Retain only the
            # component joined to the continuous backbone; bolt selection below uses
            # this actual contour, never a discarded root island.
            for key, offset in (("spine", 8), ("rail", -38)):
                shape = spine if key == "spine" else rail
                if shape.geom_type != "Polygon":
                    anchor = Point(xy(radius(design, strand, centre) + offset, centre))
                    kept = [g for g in shape.geoms if g.covers(anchor)]
                    if len(kept) != 1:
                        raise ValueError(f"{name}: disconnected {key} backbone")
                    if key == "spine":
                        spine = kept[0]
                    else:
                        rail = kept[0]
            modules.append(
                {
                    "module_id": name,
                    "level": level,
                    "centre": centre,
                    "spine": spine,
                    "rail": rail,
                    "pad": pad,
                    "root_centre": root_centre,
                    "lid": lid,
                    "zlevels": zlevels,
                    "ribs": ribs,
                    "stations": stations,
                }
            )
    holes = mounting_holes(config)
    definitions = list(rib_defs.values())
    instances = []
    metadata = []
    mounts = []
    hardware = []
    for module in modules:
        name = module["module_id"]
        candidates = []
        for hole in holes:
            point = Point(hole.x_mm, hole.y_mm)
            disk = point.buffer(config.mounting.washer_radius_mm + 0.5, quad_segs=12)
            if not module["pad"].covers(disk):
                continue
            if not module["spine"].covers(disk) or not module["rail"].covers(disk):
                continue
            if any(
                poly.distance(point) < config.mounting.washer_radius_mm + 0.5
                for _, poly in rib_footprints
            ):
                continue
            if any(
                other["module_id"] != name
                and min(other["spine"].distance(point), other["rail"].distance(point))
                < config.mounting.washer_radius_mm + 0.5
                for other in modules
            ):
                continue
            candidates.append(hole)
        pairs = [
            (a, b)
            for a, b in combinations(candidates, 2)
            if 40 <= math.hypot(a.x_mm - b.x_mm, a.y_mm - b.y_mm) <= 95
        ]
        if not pairs:
            # Grid orientation can leave one arc end with only one clear hole.
            # Regenerate that root at the other end, retaining every clearance.
            if name not in root_flips:
                return generate_weave(config, (*root_flips, name))
            raise ValueError(
                f"{name}: no robust pair of grid holes in radial root pad "
                f"({len(candidates)} usable); change grid/design"
            )
        pair = min(
            pairs,
            key=lambda pair: (
                sum(module["root_centre"].distance(Point(h.x_mm, h.y_mm)) for h in pair),
                pair[0].point_id,
                pair[1].point_id,
            ),
        )
        # Keep only the selected root and a material bridge to each backbone.
        # The search pad is a feasibility region, not a manufactured broad petal.
        strand = name[0]
        start = module["centre"] - math.radians(29.25)
        end = module["centre"] + math.radians(29.25)
        trimmed = []
        for shape, inner, outer in ((module["spine"], -12, 12), (module["rail"], -42, -10)):
            backbone = band(design, strand, start, end, inner, outer)
            points = [Point(h.x_mm, h.y_mm) for h in pair]
            anchors = [nearest_points(p, backbone)[1] for p in points]
            root = MultiPoint([p.coords[0] for p in points + anchors]).convex_hull.buffer(
                config.mounting.washer_radius_mm + 4, quad_segs=16
            )
            contour = shape.intersection(unary_union([backbone, root]))
            if contour.geom_type != "Polygon":
                raise ValueError(f"{name}: disconnected trimmed root")
            trimmed.append(contour)
        spine, rail = trimmed
        for hole in pair:
            cut = Point(hole.x_mm, hole.y_mm).buffer(hole.diameter_mm / 2, quad_segs=16)
            spine = spine.difference(cut)
            rail = rail.difference(cut)
            mounts.append((name, hole.point_id, hole.x_mm, hole.y_mm))
            r = config.mounting.washer_radius_mm
            hardware.append(
                (
                    name,
                    hole.x_mm - r,
                    hole.y_mm - r,
                    0.0,
                    hole.x_mm + r,
                    hole.y_mm + r,
                    zbase + module["lid"] + t + config.mounting.hardware_outward_mm,
                )
            )
        sd = PartDefinition.from_polygon(
            name + "-curved-spine", spine, t, tuple(module["stations"]), kind="spine"
        )
        cd = PartDefinition.from_polygon(name + "-capture-rail", rail, t, kind="closure")
        definitions.extend((sd, cd))
        for j, z in enumerate(module["zlevels"]):
            instances.append(
                PartInstance(
                    f"{name}-spine-{j}",
                    sd.definition_id,
                    sd.revision,
                    ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, zbase + z), (0, 0, 0, 1)),
                    name,
                    "spine",
                )
            )
        instances.append(
            PartInstance(
                name + "-rail",
                cd.definition_id,
                cd.revision,
                ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, zbase + module["lid"]), (0, 0, 0, 1)),
                name,
                "closure",
            )
        )
        instances.extend(module["ribs"])
        metadata.append(
            {
                "module_id": name,
                "level": module["level"],
                "rib_ids": [i.instance_id for i in module["ribs"]],
                "station_transforms": [i.transform for i in module["ribs"]],
                "spine_ids": [name + "-spine-0", name + "-spine-1"],
                "closure_id": name + "-rail",
            }
        )
    crossings = [
        {
            "theta_deg": (j * 60 + design.rotation_deg) % 360,
            "over_module": ("a" if j % 2 == 0 else "b") + str(j),
            "under_module": ("b" if j % 2 == 0 else "a") + str(j),
        }
        for j in range(6)
    ]
    blueprint = {
        "family": "radial-weave-v1",
        "manufacturing_request": manufacturing_request(config),
        "design": asdict(design),
        "template_rotation_deg": design.rotation_deg,
        "modules": metadata,
        "mounting_grid": mounts,
        "hardware_bounds": hardware,
        "crossings": crossings,
        "removal_order": [
            m["module_id"] for level in ("high", "low") for m in metadata if m["level"] == level
        ],
    }
    return GeometryBundle(tuple(definitions), tuple(instances)), blueprint
