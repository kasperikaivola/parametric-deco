"""Nominal perpendicular slots. No toolpath compensation."""

from shapely.geometry import box

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
