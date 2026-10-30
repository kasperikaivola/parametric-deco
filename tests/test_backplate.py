from parametric_deco.config import RibStudy
from dataclasses import replace
import math

import pytest
from shapely.geometry import Point


def test_polygon_uniform_fit_and_grid_negative_parity():
    from parametric_deco.config import DesignConfig
    from parametric_deco.geometry.backplate import backplate_polygon, mounting_holes

    c = DesignConfig(style="rib-study", parameters=RibStudy())
    for n in (6, 8):
        shape = backplate_polygon(replace(c, backplate=replace(c.backplate, sides=n)))
        assert shape.bounds[0] >= -500 - 1e-8
        assert shape.bounds[2] <= 500 + 1e-8
        edges = [
            math.dist(a, b) for a, b in zip(shape.exterior.coords, list(shape.exterior.coords)[1:])
        ]
        assert max(edges) - min(edges) < 1e-8
    holes = {(h.row, h.column): h for h in mounting_holes(c)}
    assert holes[-1, 0].x_mm == 25
    assert holes[1, 0].x_mm == 25
    assert holes[-2, 0].x_mm == 0
    shape = backplate_polygon(c)
    for h in holes.values():
        assert shape.boundary.distance(Point(h.x_mm, h.y_mm)) >= 18.25 - 1e-8
    shifted = replace(c, grid=replace(c.grid, origin_x_mm=13, origin_y_mm=-7))
    hs = {(h.row, h.column): h for h in mounting_holes(shifted)}
    assert hs[-1, 0].x_mm == 38
    assert hs[-1, 0].y_mm == -57
    assert hs[0, 0].point_id == holes[0, 0].point_id


def test_root_requires_all_holes_and_washers():
    from parametric_deco.config import DesignConfig
    from parametric_deco.geometry.backplate import match_root_pattern

    c = DesignConfig(style="rib-study", parameters=RibStudy())
    assert len(match_root_pattern(c, ((25, -50), (25, 50)))) == 2
    with pytest.raises(ValueError, match="mount"):
        match_root_pattern(c, ((25, -50), (26, 50)))


@pytest.mark.parametrize("style", ["laminar", "layered-creature", "radial-weave", "rib-study"])
def test_all_styles_share_regular_polygon_outline_and_controls(style):
    from parametric_deco.config import config_from_dict
    from parametric_deco.geometry.backplate import backplate_polygon

    c = config_from_dict({"style": style})
    original = backplate_polygon(c)
    assert len(original.exterior.coords) == 9
    assert original.bounds == pytest.approx((-500, -500, 500, 500))
    for sides, rotation in ((6, 22.5), (8, 0)):
        changed = backplate_polygon(replace(c, backplate=replace(c.backplate,
                                            sides=sides, rotation_deg=rotation)))
        assert len(changed.exterior.coords) == sides + 1
        assert not changed.equals(original)
        edges = [math.dist(a, b) for a, b in zip(changed.exterior.coords,
                                                list(changed.exterior.coords)[1:])]
        assert max(edges) - min(edges) < 1e-8


@pytest.mark.parametrize("style,previous_request", [
    ("laminar", "f1f00a62081cf3c6c3748a71303f4566d5f14ef70c0bd04c87f150a94918b737"),
    ("layered-creature", "56409df9fac643f6fe6b0737e793f20dd1ce088991e08853471e500bc6c76614"),
])
def test_new_boards_saved_replay_and_previous_requests_require_cuts(tmp_path, style,
                                                                  previous_request):
    import json
    from parametric_deco.assembly import assemble
    from parametric_deco.config import config_from_dict
    from parametric_deco.geometry.backplate import backplate_polygon
    from parametric_deco.model import Inventory, digest

    c = config_from_dict({"style": style})
    build = assemble(c)
    assert build.report.digital_valid, build.report.to_dict()
    board = next(d for d in build.assembly.definitions if d.kind == 'backplate')
    assert len(board.outer) == c.backplate.sides
    assert board.polygon.exterior.equals(backplate_polygon(c).exterior)
    assert board.thickness_mm == 6
    # Real bores and closed seats/apertures remain in the manufactured cut.
    if style == 'laminar':
        from shapely.geometry import Polygon
        assert len(board.holes) == 4 * len(build.assembly.composition['modules'])
        for module in build.assembly.composition['modules']:
            for slot in module['slot_polygons']:
                assert board.polygon.intersection(Polygon(slot)).area < 1e-6
    else:
        from parametric_deco.geometry.backplate import mounting_holes
        assert len(board.holes) == len(mounting_holes(c)) + len(backplate_polygon(c).interiors)
        assert all(not board.polygon.covers(Point(h.x_mm, h.y_mm))
                   for h in mounting_holes(c))
    path = tmp_path / 'inventory.json'
    path.write_text(json.dumps(build.inventory.to_dict()))
    saved = Inventory.load(path)
    assert assemble(c, saved).inventory.to_dict() == saved.to_dict()
    assert config_from_dict(c.to_dict()) == c
    for changes in ({'sides': 6}, {'rotation_deg': 0}):
        changed = replace(c, backplate=replace(c.backplate, **changes))
        with pytest.raises(ValueError, match='new cuts'):
            assemble(changed, saved)

    # Baseline master requests predate common-polygon-v1. Even a valid signed
    # saved layout from that request must be rejected before any geometry replay.
    layout = saved.layout.copy()
    layout['manufacturing_request'] = previous_request
    layout.pop('fingerprint')
    layout['fingerprint'] = digest(layout)
    path.write_text(json.dumps(replace(saved, layout=layout).to_dict()))
    old_saved = Inventory.load(path)
    with pytest.raises(ValueError, match='new cuts'):
        assemble(c, old_saved)
    assert old_saved.to_dict() == Inventory.load(path).to_dict()


def test_creature_polygon_retains_through_eye_and_central_channels():
    from shapely import affinity
    from shapely.ops import unary_union
    from parametric_deco.config import config_from_dict
    from parametric_deco.geometry.backplate import backplate_polygon
    from parametric_deco.geometry.creature_profiles import cavity_voids, central_void, placement_offset

    c = config_from_dict({'style': 'layered-creature'})
    voids = unary_union([*cavity_voids(c.parameters, 1.06), affinity.scale(
        central_void(), xfact=c.parameters.scale, yfact=c.parameters.scale, origin=(0, 0))])
    dx, dy = placement_offset(c)
    placed_voids = affinity.translate(voids, xoff=dx, yoff=dy)
    assert backplate_polygon(c).intersection(placed_voids).area < 1e-6
