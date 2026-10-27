import json
from dataclasses import replace

import pytest


def test_resize_keeps_manufacturing_dimensions():
    from parametric_deco.config import DesignConfig

    c = DesignConfig()
    large = replace(c, envelope=replace(c.envelope, width_mm=1500))
    assert large.material.nominal_mm == 6
    assert large.material.measured_mm == 6
    assert large.grid.hole_diameter_mm == 6.5
    assert large.material.clearance_mm == 0.2


@pytest.mark.parametrize(
    "section,field,value",
    [
        ("envelope", "width_mm", float("nan")),
        ("grid", "pitch_x_mm", 0),
        ("grid", "pitch_y_mm", -1),
        ("grid", "hole_diameter_mm", 55),
        ("backplate", "sides", 2),
        ("envelope", "depth_mm", 20),
        ("material", "measured_mm", float("inf")),
        ("material", "clearance_mm", -1),
        ("mounting", "rear_clearance_mm", -1),
        ("module", "length_mm", 30),
    ],
)
def test_invalid_fields_rejected(section, field, value):
    from parametric_deco.config import DesignConfig, validate_config

    c = DesignConfig()
    c = replace(c, **{section: replace(getattr(c, section), **{field: value})})
    report = validate_config(c)
    assert not report.digital_valid
    assert any(f"{section}.{field}" in i.message for i in report.issues)


def test_load_roundtrip_and_unknown_fields(tmp_path):
    from parametric_deco.config import DesignConfig, load_config

    p = tmp_path / "config.json"
    p.write_text(json.dumps(DesignConfig().to_dict()))
    assert load_config(p) == DesignConfig()
    p.write_text('{"moduel": {}}')
    with pytest.raises(ValueError, match="moduel"):
        load_config(p)


@pytest.mark.parametrize("diameter,radius", [(6.5, 1), (20, 9)])
def test_root_washer_requires_positive_bearing_around_hole(diameter, radius):
    from parametric_deco.config import DesignConfig, validate_config

    c = DesignConfig()
    c = replace(
        c,
        grid=replace(c.grid, hole_diameter_mm=diameter),
        mounting=replace(c.mounting, washer_radius_mm=radius),
    )
    report = validate_config(c)
    assert not report.digital_valid
    assert any("washer" in i.message and "bearing" in i.message for i in report.issues)
