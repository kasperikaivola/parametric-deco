"""Comparison views use one camera convention across every style."""
import numpy as np

from parametric_deco.export.views import project_vertices


def test_crossing_triangles_use_pixel_depth_regardless_of_draw_order():
    from parametric_deco.export.views import rasterize_triangles

    xy = np.array([[2., 2.], [30., 2.], [2., 30.]])
    red = (xy, np.array([0., 28., 0.]), (255, 0, 0))
    green = (xy, np.array([14., 14., 14.]), (0, 255, 0))
    # Each triangle is in front in part of their shared screen footprint.
    forward = rasterize_triangles((32, 32), (red, green))
    reverse = rasterize_triangles((32, 32), (green, red))
    assert np.array_equal(forward, reverse)
    assert tuple(forward[5, 5]) == (0, 255, 0)
    assert tuple(forward[5, 23]) == (255, 0, 0)
    assert tuple(forward[31, 31]) == (18, 21, 27)


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


def test_front_raster_has_unskewed_board_and_foreground_independent_of_z(tmp_path):
    from dataclasses import replace
    from PIL import Image
    from shapely.geometry import box
    from parametric_deco.export.views import render_views
    from parametric_deco.model import Assembly, IDENTITY, PartDefinition, PartInstance

    board = PartDefinition.from_polygon('board', box(-100, -50, 100, 50), 6,
                                        kind='backplate')
    cap = PartDefinition.from_polygon('cap', box(20, 0, 40, 20), 6, kind='armour')

    def raised(z):
        pose = np.array(IDENTITY)
        pose[2, 3] = z
        return PartInstance('cap', cap.definition_id, cap.revision,
                            tuple(map(tuple, pose)), 'module', 'armour')

    # Intentionally put the board last: front-face order must follow +Z depth.
    a = Assembly((board, cap), (raised(30), PartInstance(
        'board', board.definition_id, board.revision, IDENTITY, 'backing', 'backplate')))
    render_views(a, tmp_path / 'near', views=('front', 'three-quarter'))
    render_views(replace(a, instances=(raised(130), a.instances[1])), tmp_path / 'far',
                 views=('front', 'three-quarter'))
    front = np.array(Image.open(tmp_path / 'near/front.png'))
    assert np.array_equal(front, np.array(Image.open(tmp_path / 'far/front.png')))
    assert not np.array_equal(np.array(Image.open(tmp_path / 'near/three-quarter.png')),
                              np.array(Image.open(tmp_path / 'far/three-quarter.png')))
    # 200 x 100 board fills 980 x 490 pixels, with straight parallel screen edges.
    background = (18, 21, 27)
    for x in (100, 550, 1000):
        assert tuple(front[218, x]) == background
        assert tuple(front[225, x]) != background
        assert tuple(front[705, x]) != background
        assert tuple(front[712, x]) == background
    for y in (250, 465, 680):
        assert tuple(front[y, 58]) == background
        assert tuple(front[y, 65]) != background
        assert tuple(front[y, 1035]) != background
        assert tuple(front[y, 1042]) == background
    # Cap center at world (30,10) remains at (697,416) and occludes the board.
    assert front[416, 697, 0] > front[416, 600, 0] * 2
