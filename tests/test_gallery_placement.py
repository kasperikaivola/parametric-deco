"""Gallery layout changes must be real CAD placement, with reusable cuts."""
import numpy as np
from parametric_deco.config import load_config
from parametric_deco.geometry.creature import generate_creature
from parametric_deco.geometry.backplate import backplate_polygon


def test_six_limb_centering_preserves_grid_and_clear_board_channels():
    c = load_config('examples/creature-alien-six.json')
    bundle, layout = generate_creature(c)
    assert layout.get('placement_offset_mm', [0, 0]) == [0, 100]
    from parametric_deco.geometry.creature_profiles import cavity_voids
    from shapely import affinity
    board = backplate_polygon(c)
    for eye in cavity_voids(c.parameters, .75):
        # Artwork cavities now retain the same dark universal stock behind them.
        assert board.covers(affinity.translate(eye, yoff=100))
    assert all(np.isfinite(np.array(i.transform)).all() for i in bundle.instances)


def test_representative_radial_uses_real_quarter_turn():
    from parametric_deco.config import RadialWeave
    from parametric_deco.geometry.weave import generate_weave
    assert RadialWeave().rotation_deg == 90
    c = load_config('examples/radial-weave.json')
    assert c.parameters.rotation_deg == 90
    _, layout = generate_weave(c)
    assert layout.get('template_rotation_deg', 0) == 90
    assert layout['crossings'][0]['theta_deg'] == 90


def test_centered_six_limb_actual_assembly_and_saved_inventory():
    from dataclasses import replace
    from parametric_deco.assembly import assemble
    from parametric_deco.validation import instance_bounds
    c = load_config('examples/creature-alien-six.json')
    build = assemble(c)
    assert build.report.digital_valid, build.report.to_dict()
    a = build.assembly
    bounds = np.array([instance_bounds(a.definition_for(i), i.transform)
                       for i in a.instances if i.role != 'backplate'])
    center_y = (bounds[:, 0, 1].min() + bounds[:, 1, 1].max()) / 2
    assert abs(center_y) < 2, center_y
    before = build.inventory.to_dict()
    raised = assemble(replace(c, parameters=replace(c.parameters, posture='raised_crown')),
                      build.inventory)
    assert raised.report.digital_valid, raised.report.to_dict()
    assert build.inventory.to_dict() == before
    assert raised.inventory.definitions == build.inventory.definitions
    assert raised.assembly.composition['placement_offset_mm'] == [0, 100]


def test_explicit_zero_rotation_and_legacy_radial_inventory_replay():
    from dataclasses import replace
    import json
    from parametric_deco.assembly import assemble
    from parametric_deco.model import Inventory, digest
    from parametric_deco.geometry.backplate import match_root_pattern
    c = load_config('examples/radial-weave.json')
    c = replace(c, parameters=replace(c.parameters, rotation_deg=0))
    build = assemble(c)
    assert build.report.digital_valid, build.report.to_dict()
    saved = build.inventory.to_dict()
    layout = saved['layout']['source_template']['layout']
    layout.pop('template_rotation_deg')
    layout.pop('fingerprint')
    layout['fingerprint'] = digest(layout)
    outer = saved['layout']
    outer.pop('fingerprint')
    outer['fingerprint'] = digest(outer)
    legacy = Inventory.from_dict(json.loads(json.dumps(saved)))
    before = legacy.to_dict()
    replay = assemble(c, legacy)
    assert replay.report.digital_valid, replay.report.to_dict()
    assert legacy.to_dict() == before
    assert replay.assembly.to_dict() == build.assembly.to_dict()
    for _, _, x, y in replay.assembly.mounting_grid:
        assert match_root_pattern(c, [(x, y)])


def test_legacy_creature_matches_saved_board_and_keeps_original_placement(monkeypatch):
    import parametric_deco.geometry.creature as geometry
    import parametric_deco.geometry.creature_profiles as profiles
    from parametric_deco.assembly import assemble
    from parametric_deco.model import Inventory, digest
    c = load_config('examples/creature-alien-six.json')
    from parametric_deco.geometry.backplate import generate_backplate, mounting_holes
    generate_backplate.cache_clear()
    mounting_holes.cache_clear()
    with monkeypatch.context() as legacy:
        legacy.setattr(geometry, 'placement_offset', lambda c: (0, 0))
        legacy.setattr(profiles, 'placement_offset', lambda c: (0, 0))
        bundle, layout = generate_creature(c)
    generate_backplate.cache_clear()
    mounting_holes.cache_clear()
    layout.pop('placement_offset_mm')
    layout.pop('fingerprint')
    layout['fingerprint'] = digest(layout)
    inventory = Inventory(bundle.definitions, bundle.instances, layout)
    before = inventory.to_dict()
    import pytest
    with pytest.raises(ValueError, match='requires new cuts'):
        assemble(c, inventory)
    assert inventory.to_dict() == before


def test_saved_mount_matching_requires_real_grid_bore_and_bearing():
    import pytest
    from shapely.geometry import Point, box
    from parametric_deco.geometry.backplate import match_root_pattern
    from parametric_deco.model import PartDefinition
    c = load_config('examples/creature-alien-six.json')
    def board(outer, radius):
        return PartDefinition.from_polygon('board', outer.difference(
            Point(0, 0).buffer(radius, quad_segs=8)), 6, kind='backplate')
    valid = board(box(-60, -60, 60, 60), c.grid.hole_diameter_mm / 2)
    assert match_root_pattern(c, [(0, 0)], backing=valid)[0].point_id == 'grid-r0-c0'
    aperture = board(box(-60, -60, 60, 60), 30)
    no_bearing = board(box(-12, -12, 12, 12), c.grid.hole_diameter_mm / 2)
    for invalid in (aperture, no_bearing):
        with pytest.raises(ValueError, match='saved grid bore/washer'):
            match_root_pattern(c, [(0, 0)], backing=invalid)
