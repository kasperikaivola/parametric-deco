"""Candidate paired-spine module with a full-length backplate-clamped top closure."""

from functools import lru_cache
import math

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from ..cad import solid_for
from ..model import GeometryBundle, InterfaceStation, PartDefinition, PartInstance
from .joints import slot_width


@lru_cache(maxsize=16)
def generate_module(config):
    m, t = config.module, config.material.measured_mm
    w, half = slot_width(config), m.spine_separation_mm / 2
    stations = tuple(
        InterfaceStation(f"s{i}", float(x), w, m.joint_datum_mm)
        for i, x in enumerate(m.stations_mm)
    )
    # XZ spines; top tongues locate the upper closure at both ends.
    tongues = ((15, 40), (m.length_mm - 40, m.length_mm - 15))
    upper = [
        (
            m.length_mm * i / 48,
            m.spine_height_mm
            - 0.3 * (m.spine_height_mm - m.joint_datum_mm) * (1 - math.sin(math.pi * i / 48)),
        )
        for i in range(49)
    ]
    spine_shape = unary_union(
        [Polygon([(0, 0), (m.length_mm, 0), *reversed(upper)])]
        + [box(a, 0, b, m.rib_top_mm + t) for a, b in tongues]
    )
    for s in stations:
        spine_shape = spine_shape.difference(
            box(s.x_mm - w / 2, m.joint_datum_mm, s.x_mm + w / 2, m.rib_top_mm + t + 1)
        )
    spine = PartDefinition.from_polygon("spine", spine_shape, t, stations, kind="spine")
    ribs = []
    for ri, width in enumerate(m.rib_widths_mm):
        h = width / 2
        bend = 0.18 * math.sin(ri * math.pi / 2)
        left, right = h * (1 + bend), h * (1 - bend)
        # Common bearing region; larger wings form a rhythm across the assembly.
        profile = Polygon(
            [
                (-left, 40),
                (-left * 0.85, 80),
                (-max(half + 8, h * 0.55), m.rib_top_mm),
                (max(half + 8, h * 0.55), m.rib_top_mm),
                (right, 80),
                (right * 0.8, 35),
                (half + 15, m.rib_bottom_mm),
                (-half - 15, m.rib_bottom_mm),
            ]
        )
        for y in (-half, half):
            profile = profile.difference(
                box(y - w / 2, m.rib_bottom_mm - 1, y + w / 2, m.joint_datum_mm)
            )
        ribs.append(
            PartDefinition.from_polygon(
                f"rib-{ri}",
                profile,
                t,
                (InterfaceStation("pair", 0, w, m.joint_datum_mm),),
                kind="rib",
            )
        )
    # XY closure: two longitudinal rails, rib capture bridges, root and end braces.
    rails = []
    for side in (-half, half):
        centre = [
            (
                10 + (m.length_mm - 10) * i / 96,
                side
                + 18 * math.sin(2 * math.pi * (10 + (m.length_mm - 10) * i / 96) / m.length_mm),
            )
            for i in range(97)
        ]
        rails.append(
            Polygon([(x, y - 8) for x, y in centre] + [(x, y + 8) for x, y in reversed(centre)])
        )
    closure_shape = unary_union(
        [
            box(-25, -config.mounting.root_half_span_mm - 20, 55, config.mounting.root_half_span_mm + 20),
            *rails,
            box(m.length_mm - 45, -half - 10, m.length_mm, half + 10),
        ]
        + [box(x - 10, -half - 10, x + 10, half + 10) for x in m.stations_mm]
    )
    for a, b in tongues:
        for y in (-half, half):
            closure_shape = closure_shape.difference(
                box(
                    a - config.material.clearance_mm / 2,
                    y - w / 2,
                    b + config.material.clearance_mm / 2,
                    y + w / 2,
                )
            )
    # All installed mounting bores are chosen directly on the common board grid
    # by the end-clamp stage. No obsolete off-grid root bores remain in new cuts.
    closure = PartDefinition.from_polygon("closure", closure_shape, t, kind="closure")
    instances = []
    for index, y in enumerate((-half, half)):
        transform = ((1, 0, 0, 0), (0, 0, -1, y + t / 2), (0, 1, 0, 0), (0, 0, 0, 1))
        instances.append(
            PartInstance(
                f"spine-{index}", spine.definition_id, spine.revision, transform, role="spine"
            )
        )
    for ri, x in enumerate(m.stations_mm):
        rib = ribs[ri]
        transform = ((0, 0, 1, x - t / 2), (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1))
        instances.append(
            PartInstance(
                f"rib-{ri}",
                rib.definition_id,
                rib.revision,
                transform,
                role="rib",
                station_id=f"s{ri}",
            )
        )
    instances.append(
        PartInstance(
            "closure",
            closure.definition_id,
            closure.revision,
            ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, m.rib_top_mm), (0, 0, 0, 1)),
            role="closure",
        )
    )
    definitions = (spine, *ribs, closure)
    return GeometryBundle(
        definitions, tuple(instances), {d.definition_id: solid_for(d) for d in definitions}
    )
