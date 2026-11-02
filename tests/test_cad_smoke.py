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


def test_upright_rib_overlap_matches_solid_kernel():
    import numpy as np
    from shapely.geometry import Polygon, box

    from parametric_deco.cad import _kernel_overlap, _radial_rib_overlap, overlap_volume
    from parametric_deco.model import PartDefinition

    def rows(*values):
        return np.array(values, dtype=float)

    # Weave frame: profile +Y is world +Z, thickness runs along world -Y.
    rib_pose = rows(
        (1, 0, 0, 0),
        (0, 0, -1, 0),
        (0, 1, 0, 0),
        (0, 0, 0, 1),
    )
    notch = Polygon([(0, 0), (10, 0), (10, 4), (6, 4), (6, 6), (10, 6), (10, 10), (0, 10)])
    cases = (
        (box(0, 0, 10, 10), 2, box(0, -2, 10, 0), 4, rows(
            (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 2), (0, 0, 0, 1),
        )),
        (notch, 2, box(-1, -3, 12, 1), 20, rows(
            (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1),
        )),
    )
    for index, (rib_poly, rib_t, plate_poly, plate_t, plate_pose) in enumerate(cases):
        rib = PartDefinition.from_polygon(
            f"rib-overlap-{index}", rib_poly, rib_t, include_surfaces=False
        )
        plate = PartDefinition.from_polygon(
            f"plate-overlap-{index}", plate_poly, plate_t, include_surfaces=False
        )
        kernel = _kernel_overlap(
            rib, tuple(map(tuple, rib_pose)), plate, tuple(map(tuple, plate_pose))
        )
        exact = _radial_rib_overlap(rib, rib_pose, plate, plate_pose)
        assert exact == pytest.approx(kernel, abs=1e-6)
        assert overlap_volume(rib, rib_pose, plate, plate_pose) == pytest.approx(kernel, abs=1e-6)
