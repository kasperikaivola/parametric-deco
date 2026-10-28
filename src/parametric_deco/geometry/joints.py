"""Nominal perpendicular slots. No toolpath compensation."""

from shapely.geometry import box, LineString

from ..model import InterfaceStation, PartDefinition


def slot_width(config):
    return config.material.measured_mm + config.material.clearance_mm


def fit_coupon(config):
    t = config.material.measured_mm
    shape = box(0, 0, 120, 40)
    interfaces = []
    for i in range(5):
        width = t + i * 0.1
        x = 15 + i * 22
        shape = shape.difference(box(x - width / 2, 20, x + width / 2, 45))
        interfaces.append(InterfaceStation(f"clearance-{i}", x, width, 20, "fit-coupon"))
    return PartDefinition.from_polygon(
        "fit-coupon", shape, config.material.measured_mm, tuple(interfaces), kind="coupon"
    )


def rib_slot_centres(definition):
    """Read the paired open-slot positions from manufactured contours, not current recipe."""
    if not definition.interfaces:
        raise ValueError(f"{definition.definition_id}: missing rib interface")
    interface = definition.interfaces[0]
    minx, minz, maxx, _ = definition.polygon.bounds
    probe = (minz + interface.datum_mm) / 2
    section = definition.polygon.intersection(LineString(((minx - 1, probe), (maxx + 1, probe))))
    pieces = sorted(
        (g.bounds[0], g.bounds[2])
        for g in getattr(section, "geoms", (section,))
        if g.geom_type == "LineString"
    )
    gaps = [(a[1], b[0]) for a, b in zip(pieces, pieces[1:])]
    if len(gaps) != 2 or any(abs(b - a - interface.slot_width_mm) > 1e-6 for a, b in gaps):
        raise ValueError(f"{definition.definition_id}: incompatible paired-slot interface geometry")
    return tuple((a + b) / 2 for a, b in gaps)
