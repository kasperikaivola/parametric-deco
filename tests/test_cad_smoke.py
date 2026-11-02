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


def test_exact_polygon_mesh_matches_independent_solid_with_closed_holes():
    from shapely.geometry import box, Point
    from parametric_deco.model import PartDefinition
    from parametric_deco.cad import mesh_for, solid_for

    profile = box(-40, -30, 40, 30).union(box(30, -10, 70, 10))
    profile = profile.difference(Point(-15, 0).buffer(8, quad_segs=16)).difference(box(5, -5, 15, 5))
    part = PartDefinition.from_polygon('mesh-kernel-check', profile, 5.8)
    mesh = mesh_for(part)
    assert mesh.is_watertight
    assert mesh.volume == pytest.approx(solid_for(part).volume, abs=1e-6)
    import numpy as np
    assert np.allclose(mesh.bounds, [[-40, -30, 0], [70, 30, 5.8]])
    # Every cap triangle stays inside actual material, including concave bays and
    # closed bores. Compare their union, not triangle centroids.
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    top = mesh.triangles[np.all(np.isclose(mesh.triangles[:, :, 2], 5.8), axis=1)]
    caps = [Polygon(t[:, :2]) for t in top]
    assert all(profile.buffer(1e-8).covers(face) for face in caps)
    assert unary_union(caps).symmetric_difference(profile).area < 1e-7
    assert sum(face.area for face in caps) == pytest.approx(profile.area, abs=1e-7)
    for center, normal in zip(mesh.triangles_center, mesh.face_normals):
        if abs(normal[2]) < 1e-8:
            assert not profile.contains(Point(*(center[:2] + normal[:2] * 1e-5)))
    assert mesh_for(part) is mesh
