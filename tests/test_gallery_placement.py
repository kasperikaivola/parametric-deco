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
        assert board.intersection(affinity.translate(eye, yoff=100)).area < 1e-8
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
    layout = saved['layout']
    layout.pop('template_rotation_deg')
    layout.pop('fingerprint')
    layout['fingerprint'] = digest(layout)
    legacy = Inventory.from_dict(json.loads(json.dumps(saved)))
    before = legacy.to_dict()
    replay = assemble(c, legacy)
    assert replay.report.digital_valid, replay.report.to_dict()
    assert legacy.to_dict() == before
    assert replay.assembly.to_dict() == build.assembly.to_dict()
    for _, _, x, y in replay.assembly.mounting_grid:
        assert match_root_pattern(c, [(x, y)])
