import math

import pytest
from build123d import import_step
from shapely.geometry import Point, box


def test_real_plate_step_roundtrip_preserves_hole_and_dimensions(tmp_path):
    from parametric_deco.cad import extrude_polygon, export_step

    polygon = box(0, 0, 100, 40).difference(Point(50, 20).buffer(3.25, quad_segs=64))
    solid = extrude_polygon(polygon, 6)
    export_step(solid, tmp_path / "plate.step")
    loaded = import_step(tmp_path / "plate.step")
    assert tuple(loaded.bounding_box().size) == pytest.approx((100, 40, 6))
    assert loaded.volume == pytest.approx((4000 - math.pi * 3.25**2) * 6, rel=1e-5)
    probe = extrude_polygon(box(49, 19, 51, 21), 6)
    assert (loaded & probe) is None
