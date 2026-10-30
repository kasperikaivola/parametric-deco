"""Upper plates must reveal meaningful lower contour area, without loose islands."""
from dataclasses import replace

import pytest
from shapely.ops import unary_union

from parametric_deco.config import CreatureMask
from parametric_deco.geometry.creature_profiles import profiles


@pytest.mark.parametrize('layers', [3, 5, 6])
def test_head_cutbacks_reveal_each_depth_and_reduce_cap_area(layers):
    shapes = profiles(settings=replace(CreatureMask(), shell_layers=layers))['head']
    assert shapes[-1].area < shapes[0].area * .66
    for index, shape in enumerate(shapes[:-1]):
        visible = shape.difference(unary_union(shapes[index + 1:]))
        assert visible.area > shapes[0].area * .025
    assert all(q.is_valid and q.geom_type == 'Polygon' for q in shapes)


@pytest.mark.parametrize('layers', [3, 4, 5])
def test_limb_cutbacks_reveal_rails_without_disconnected_tips(layers):
    shapes = profiles(settings=replace(CreatureMask(), limb_layers=layers))
    for name, parts in shapes.items():
        if name == 'head':
            continue
        assert parts[-1].area < parts[0].area * .78
        assert all(q.is_valid and q.geom_type == 'Polygon' for q in parts)


@pytest.mark.parametrize('cavities,scale,curl,width,reach', [
    (3, .9, .8, .9, .85), (8, 1, 1.2, 1.1, 1.05),
    (8, .9, 1.2, .9, 1.05), (3, 1, .8, 1.1, .85),
])
def test_layer_cutbacks_stay_connected_at_shape_boundaries(cavities, scale, curl, width, reach):
    p = CreatureMask(cavity_count=cavities, scale=scale, curl=curl,
                     limb_width=width, limb_reach=reach, limb_count=6,
                     shell_layers=6, limb_layers=5)
    assert all(q.is_valid and q.geom_type == 'Polygon'
               for parts in profiles(settings=p).values() for q in parts)


@pytest.mark.parametrize('cavities', [3, 6, 8])
@pytest.mark.parametrize('scale', [.9, 1])
def test_head_terraces_keep_six_mm_contour_necks(cavities, scale):
    # A 3 mm erosion on each side must not detach a lobe: catches a thin
    # plywood neck even when the un-eroded polygon is technically connected.
    for plate in profiles(settings=CreatureMask(cavity_count=cavities, scale=scale))['head']:
        assert plate.buffer(-3).geom_type == 'Polygon'


@pytest.mark.parametrize('scale', [.9, 1])
def test_narrow_rails_preserve_physical_rib_slot_bearing_when_scaled(scale):
    import numpy as np
    from shapely.geometry import Polygon
    from parametric_deco.geometry.creature_profiles import rib_stations

    p = CreatureMask(limb_count=6, ribs_per_limb=3, scale=scale,
                     limb_width=.9, limb_reach=.9)
    for name, plates in profiles(settings=p).items():
        if name == 'head':
            continue
        for center, normal, *_ in rib_stations(name, settings=p):
            tangent = np.array((normal[1], -normal[0]))
            slot = Polygon([center + u * normal + v * tangent
                            for u, v in [(-14.1, -3.1), (14.1, -3.1),
                                         (14.1, 3.1), (-14.1, 3.1)]])
            assert plates[-1].buffer(-7).covers(slot), name
