"""Comparison views use one camera convention across every style."""
import numpy as np

from parametric_deco.export.views import project_vertices


def test_shared_camera_axes_preserve_depth_and_front_orientation():
    vertices = np.array([[0., 0, 0], [100, 0, 0], [0, 100, 0], [0, 0, 100]])
    assert np.array_equal(project_vertices(vertices, 'front'), vertices)
    projected = project_vertices(vertices, 'three-quarter')
    assert np.allclose(projected[1:], [[88.69949228, -13.64650774, 44.11544963],
                                        [0, 95.53364891, 29.55202067],
                                        [-46.17791755, -26.21249229, 84.73786154]])
    assert projected[1, 0] > 0 and projected[2, 1] > 0
    assert projected[3, 0] < 0 and projected[3, 1] < 0
    assert np.allclose(np.linalg.norm(projected, axis=1), np.linalg.norm(vertices, axis=1))


def test_radial_gets_shared_three_quarter_view(tmp_path):
    from parametric_deco.assembly import assemble
    from parametric_deco.config import config_from_dict
    from parametric_deco.export.views import render_views

    assembly = assemble(config_from_dict({'style':'radial-weave'})).assembly
    render_views(assembly, tmp_path, views=('front', 'three-quarter'))
    assert {p.name for p in tmp_path.iterdir()} == {'front.png', 'three-quarter.png'}
