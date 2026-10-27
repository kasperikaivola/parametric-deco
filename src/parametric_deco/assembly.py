"""Generate new parts or place immutable saved inventory; never conflate the modes."""

import math

import numpy as np
from shapely.geometry import Polygon, Point

from .config import validate_config
from .geometry.backplate import generate_backplate, match_root_pattern
from .geometry.module import generate_module
from .model import Assembly, BuildResult, Connection, Inventory, PartInstance, digest


def placement_matrix(p, z):
    theta = math.radians(p.angle_deg)
    co, si = math.cos(theta), math.sin(theta)
    return np.array(((co, -si, 0, p.x_mm), (si, co, 0, p.y_mm), (0, 0, 1, z), (0, 0, 0, 1)))


def _tuple_matrix(matrix):
    return tuple(tuple(float(x) for x in row) for row in matrix)


def assemble(config, inventory=None):
    report = validate_config(config)
    if not report.digital_valid:
        raise ValueError("; ".join(i.message for i in report.issues))
    if inventory is None:
        backing = generate_backplate(config).definitions[0]
        bundle = generate_module(config)
        definitions = (backing, *bundle.definitions)
        source = {}
        for p in config.placements:
            source[p.module_id] = bundle.instances
        backing_instance = PartInstance(
            "backplate",
            backing.definition_id,
            backing.revision,
            (
                (1, 0, 0, 0),
                (0, 1, 0, 0),
                (0, 0, 1, config.mounting.rear_clearance_mm),
                (0, 0, 0, 1),
            ),
            role="backplate",
        )
    else:
        # Revalidate even directly constructed inventories; do not call either generator here.
        inventory = Inventory.from_dict(inventory.to_dict())
        definitions = inventory.definitions
        backings = [i for i in inventory.instances if i.role == "backplate"]
        if len(backings) != 1:
            raise ValueError("inventory requires exactly one backing instance")
        backing_instance = backings[0]
        backing = next(
            d
            for d in definitions
            if (d.definition_id, d.revision)
            == (backing_instance.definition_id, backing_instance.revision)
        )
        source = {
            p.module_id: tuple(i for i in inventory.instances if i.module_id == p.module_id)
            for p in config.placements
        }
    lookup = {(d.definition_id, d.revision): d for d in definitions}
    placed = [backing_instance]
    connections, mount_refs, hardware, extraction = [], [], [], []
    paths = []
    base_z = backing_instance.transform[2][3] + backing.thickness_mm
    for p in config.placements:
        template = source.get(p.module_id, ())
        ribs = {i.instance_id.rsplit("rib-", 1)[-1]: i for i in template if i.role == "rib"}
        spines = [i for i in template if i.role == "spine"]
        covers = [i for i in template if i.role == "closure"]
        if len(spines) != 2 or len(covers) != 1 or any(str(r) not in ribs for r in p.rib_order):
            raise ValueError(f"{p.module_id}: missing or insufficient spine/rib/closure inventory")
        cover = covers[0]
        spine_def = lookup[spines[0].definition_id, spines[0].revision]
        cover_def = lookup[cover.definition_id, cover.revision]
        if lookup[spines[1].definition_id, spines[1].revision].fingerprint != spine_def.fingerprint:
            raise ValueError(f"{p.module_id}: incompatible paired spine revisions")
        stations = spine_def.interfaces
        if any(s >= len(stations) for s in p.station_indices):
            raise ValueError(f"{p.module_id}: unavailable station in manufactured spine")
        cover_z = spine_def.polygon.bounds[3] - cover_def.thickness_mm
        old_base = np.array(cover.transform)
        old_base[:3, 3] -= old_base[:3, 2] * cover_z
        inverse = np.linalg.inv(old_base)
        new_base = placement_matrix(p, base_z)
        local_instances = []
        for inst in (*spines, cover):
            local = inverse @ np.array(inst.transform)
            local_instances.append((inst, local, inst.station_id))
        for rib_index, station_index in zip(p.rib_order, p.station_indices):
            inst = ribs[str(rib_index)]
            definition = lookup[inst.definition_id, inst.revision]
            station = stations[station_index]
            if (
                not definition.interfaces
                or definition.interfaces[0].family != station.family
                or abs(definition.interfaces[0].slot_width_mm - station.slot_width_mm) > 1e-6
                or abs(definition.interfaces[0].datum_mm - station.datum_mm) > 1e-6
            ):
                raise ValueError(f"{inst.instance_id}: mismatched interface family/fit/datum")
            # Saved unassigned stock may retain a pose from an older module layout.
            # The perpendicular-pair family defines this canonical local orientation.
            local = np.array(
                (
                    (0, 0, 1, station.x_mm - definition.thickness_mm / 2),
                    (1, 0, 0, 0),
                    (0, 1, 0, 0),
                    (0, 0, 0, 1),
                )
            )
            local_instances.append((inst, local, station.station_id))
        module_placed = []
        for inst, local, station_id in local_instances:
            instance_id = (
                f"{p.module_id}-{inst.instance_id}" if inventory is None else inst.instance_id
            )
            new = PartInstance(
                instance_id,
                inst.definition_id,
                inst.revision,
                _tuple_matrix(new_base @ local),
                p.module_id,
                inst.role,
                station_id,
            )
            module_placed.append(new)
        placed.extend(module_placed)
        for rib in (i for i in module_placed if i.role == "rib"):
            for spine in (i for i in module_placed if i.role == "spine"):
                connections.append(
                    Connection(
                        rib.instance_id, spine.instance_id, stations[0].family, rib.station_id
                    )
                )
            paths.append(rib.instance_id)
        closure_placed = next(i for i in module_placed if i.role == "closure")
        for inst in module_placed:
            if inst.role != "closure":
                connections.append(
                    Connection(
                        inst.instance_id, closure_placed.instance_id, "upper-closure-v1", "closure"
                    )
                )
        # Find real manufactured circular root holes, not assumed current dimensions.
        root_rings = [Polygon(r) for r in cover_def.holes if abs(Polygon(r).centroid.x) < 1e-6]
        root_holes = [ring.centroid for ring in root_rings]
        if len(root_holes) != 2:
            raise ValueError(f"{p.module_id}: missing manufactured root pattern")
        roots = [(new_base @ np.array((h.x, h.y, 0, 1)))[:2] for h in root_holes]
        matches = match_root_pattern(config, roots)
        for h, (x, y), root_ring in zip(matches, roots, root_rings):
            # Inventory backing holes are immutable too. Test full washer and hole centres.
            actual = next(
                (
                    Polygon(r)
                    for r in backing.holes
                    if Polygon(r).centroid.distance(Point(x, y)) < 1e-6
                ),
                None,
            )
            if (
                actual is None
                or actual.area < math.pi * (config.grid.hole_diameter_mm / 2) ** 2 * 0.99
            ):
                raise ValueError(f"{p.module_id}: root mount absent from manufactured backing")
            radius = config.mounting.washer_radius_mm
            for part, hole in ((backing, actual), (cover_def, root_ring)):
                centre = hole.centroid
                hole_radius = max(
                    math.hypot(px - centre.x, py - centre.y) for px, py in hole.exterior.coords
                )
                if (
                    radius <= hole_radius + 1e-6
                    or Polygon(part.outer).boundary.distance(centre) < radius - 1e-6
                ):
                    raise ValueError(
                        f"{p.module_id}: washer has insufficient bearing "
                        f"on manufactured {part.definition_id}"
                    )
            mount_refs.append((p.module_id, h.point_id, float(x), float(y)))
            top_z = base_z + cover_z + cover_def.thickness_mm + config.mounting.hardware_outward_mm
            hardware.append(
                (
                    p.module_id,
                    float(x - radius),
                    float(y - radius),
                    0.0,
                    float(x + radius),
                    float(y + radius),
                    float(top_z),
                )
            )
        extraction.append(
            (
                p.module_id,
                (0.0, 0.0, 1.0),
                tuple(range(0, math.ceil(config.envelope.depth_mm) + 51, 10)),
            )
        )
    ids = [i.instance_id for i in placed]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate physical instance assignment")
    count = len(paths)
    effect_paths = tuple(
        (name, index / count, (index + 1) / count) for index, name in enumerate(paths)
    )
    env = config.envelope
    assembly = Assembly(
        tuple(definitions),
        tuple(placed),
        tuple(connections),
        tuple(mount_refs),
        effect_paths,
        (env.width_mm, env.height_mm, env.depth_mm),
        tuple(hardware),
        tuple(extraction),
    )
    from .validation import validate_assembly

    result = validate_assembly(assembly)
    warnings = (
        "Physical fit, retention, stiffness and detached handling NOT RUN.",
        "Wire/Arena runtime validation NOT RUN.",
        "Motion checks cover sampled +Z translations only; support tray required.",
        "Stock thickness is " + config.material.measurement_status + ".",
        "No valid nested sheet layout: cutting bed unknown."
        if config.cutting_bed is None
        else "Sheet placement uses conservative rectangular bounds; verify laser setup.",
    )
    return BuildResult(
        assembly,
        tuple(definitions),
        warnings,
        {
            "generator": "parametric-deco/0.1.0",
            "mode": "existing_inventory" if inventory else "generate_new",
            "config": config.to_dict(),
            "config_hash": digest(config.to_dict()),
            "kerf_compensation": "laser_software_only",
            "units": "mm",
        },
        result,
        Inventory(
            tuple(definitions),
            tuple(
                {
                    **({i.instance_id: i for i in inventory.instances} if inventory else {}),
                    **{i.instance_id: i for i in placed},
                }.values()
            ),
        ),
    )
