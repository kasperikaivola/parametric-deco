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
