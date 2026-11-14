"""Config combinations that look valid must either build or fail fast with guidance."""
from dataclasses import replace

import numpy as np
import pytest
from shapely import affinity
from shapely.geometry import Point, box

from parametric_deco.config import config_from_dict


@pytest.mark.parametrize('data,match', [
    ({'mounting': {'rear_clearance_mm': 4}}, 'rear_clearance_mm'),
    ({'mounting': {'hardware_outward_mm': 4}}, 'hardware_outward_mm'),
    ({'mounting': {'washer_radius_mm': 6}}, 'washer_radius_mm'),
    ({'grid': {'hole_diameter_mm': 8}}, 'hole_diameter_mm'),
    ({'parameters': {'symmetry': 'bilateral'}}, 'bilateral arrangement'),
    ({'parameters': {'symmetry': 'bilateral', 'arrangement': 'bilateral', 'focal_count': 5}},
     'even focal_count'),
    ({'style': 'radial-weave', 'parameters': {'rotation_deg': 45}}, 'use 30 or 60'),
    ({'style': 'radial-weave', 'parameters': {'amplitude_mm': 40}}, 'amplitude 50..80'),
    ({'lighting': {'enabled': True, 'max_segments': 2}}, 'max_segments: must be >= 6'),
    ({'lighting': {'enabled': True, 'emission': 'sideways'}}, 'lighting.emission'),
    ({'lighting': {'enabled': True, 'segment_leds': 2, 'min_segment_leds': 3}},
     'min_segment_leds'),
    ({'lighting': {'enabled': True, 'segment_leds': 20, 'injection_limit_a': 1}},
     'injection_limit_a'),
    ({'style': 'layered-creature', 'parameters': {'limb_count': 6}},
     'ribs_per_limb <= 5'),
])
def test_invalid_combinations_fail_fast_with_guidance(data, match):
    with pytest.raises(ValueError, match=match):
        config_from_dict(data)


def test_rib_study_station_count_derives_widths_and_rib_order():
    c = config_from_dict({'style': 'rib-study', 'parameters': {
        'recipe': {'length_mm': 250, 'stations_mm': [60, 120, 180]}}})
    assert len(c.parameters.recipe.rib_widths_mm) == 3
    assert c.parameters.placements[0].rib_order == (0, 1, 2)
    c = config_from_dict({'style': 'rib-study', 'parameters': {
        'recipe': {'length_mm': 400, 'stations_mm': [70, 140, 210, 280, 350]},
        'placements': [{'module_id': 'a'}, {'module_id': 'b', 'x_mm': 250}]}})
    assert all(p.station_indices == (0, 1, 2, 3, 4) for p in c.parameters.placements)
    # Explicit values are never overridden.
    with pytest.raises(ValueError, match='rib_widths'):
        config_from_dict({'style': 'rib-study', 'parameters': {
            'recipe': {'stations_mm': [60, 120, 180], 'rib_widths_mm': [100, 100]}}})


@pytest.mark.parametrize('parameters', [
    {'curvature': 1.3},
    {'spread': 0.85},
    {'symmetry': 'bilateral', 'arrangement': 'bilateral', 'focal_count': 8, 'swelling': 0.85,
     'complexity': 2},
    {'symmetry': 'none', 'focal_count': 7, 'swelling': 0.8, 'channels': 3, 'segmentation': 5},
])
def test_laminar_anatomy_stays_manufacturable(parameters):
    from parametric_deco.geometry.organism import _cuttable, anatomy
    c = config_from_dict({'parameters': parameters})
    lobes = anatomy(c)
    for lobe in lobes:
        assert lobe.shape.geom_type == 'Polygon' and lobe.shape.is_valid
        assert _cuttable(lobe.shape), lobe.name
    # Copies at a shared layer height never overlap each other.
    for n, a in enumerate(lobes):
        for b in lobes[n + 1:]:
            if abs(a.z - b.z) < 1e-9:
                assert a.shape.intersection(b.shape).area < 1e-6


def test_laminar_default_artwork_is_not_adapted():
    from parametric_deco.geometry.organism import _anatomy, anatomy, anatomy_adjustments
    c = config_from_dict({})
    assert anatomy_adjustments(c) == ()
    assert all(a.shape.equals_exact(b.shape, 0) for a, b in zip(anatomy(c), _anatomy(c, {})[0]))


def test_creature_head_columns_clear_crowded_limbs():
    from parametric_deco.geometry.creature import generate_creature
    for parameters in ({'limb_count': 6, 'ribs_per_limb': 5}, {'cavity_count': 8}):
        c = config_from_dict({'style': 'layered-creature', 'parameters': parameters})
        bundle, layout = generate_creature(c)
        lookup = {(d.definition_id, d.revision): d for d in bundle.definitions}
        columns = [i for i in bundle.instances if i.instance_id.startswith('head-column')]
        limbs = [i for i in bundle.instances if i.role in ('armour', 'cap')
                 and i.module_id != 'head']
        assert columns and limbs
        for col in columns:
            ring = affinity.translate(lookup[(col.definition_id, col.revision)].polygon,
                                      col.transform[0][3], col.transform[1][3])
            z = col.transform[2][3]
            for plate in limbs:
                if abs(plate.transform[2][3] - z) > 1e-6:
                    continue
                shape = lookup[(plate.definition_id, plate.revision)].polygon
                assert ring.intersection(shape).area < 1e-6, (col.instance_id, plate.instance_id)


def _two_hosts(width=80):
    from parametric_deco.model import Assembly, BuildResult, Inventory, PartDefinition, PartInstance
    parts = [PartDefinition.from_polygon('back', box(-180, -180, 180, 180), 6, kind='backplate')]
    instances = [PartInstance('back', 'back', parts[0].revision,
                              ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 10), (0, 0, 0, 1)),
                              role='backplate')]
    for n, (x, y) in enumerate(((-70, -70), (70, 70))):
        p = PartDefinition.from_polygon(f'host-{n}', box(x-width/2, y-40, x+width/2, y+40), 6)
        parts.append(p)
        instances.append(PartInstance(p.definition_id, p.definition_id, p.revision,
                                      ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 60), (0, 0, 0, 1)),
                                      module_id=f'm{n}', role='armour'))
    a = Assembly(tuple(parts), tuple(instances), envelope_mm=(400, 400, 100))
    return BuildResult(a, tuple(parts), inventory=Inventory(tuple(parts), tuple(instances)))


def test_variable_segment_length_and_electrical_estimates():
    from parametric_deco.lighting import add_lighting
    base = _two_hosts()
    # A 10-LED (167 mm) strip cannot fit an 80 mm host edge; shorter strips can.
    fixed = config_from_dict({'style': 'rib-study', 'lighting': {
        'enabled': True, 'segment_leds': 10, 'max_segments': 2, 'injection_limit_a': 1}})
    with pytest.raises(ValueError, match='lighting'):
        add_lighting(fixed, base)
    flexible = replace(fixed, lighting=replace(fixed.lighting, min_segment_leds=2))
    light = add_lighting(flexible, base).assembly.lighting
    counts = [s['led_count'] for s in light['segments']]
    assert all(2 <= n < 10 for n in counts)
    assert light['bom'][-2]['led_count'] == sum(counts)
    assert all(f['estimated_voltage_drop_pct'] > 0 for f in light['power']['feeds'])
    assert light['power']['longest_data_jumper_mm'] > 0
    assert light['emission']['backwash_segments'] == len(counts)


def test_auto_emission_falls_back_to_underside_without_throw():
    from parametric_deco.lighting import add_lighting
    base = _two_hosts()
    # Hosts 18 mm above the board leave no backwash throw (2 stock + strip + 10 mm).
    a = base.assembly
    lowered = tuple(replace(i, transform=((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 34),
                                          (0, 0, 0, 1))) if i.role == 'armour' else i
                    for i in a.instances)
    base = replace(base, assembly=replace(a, instances=lowered))
    c = config_from_dict({'style': 'rib-study', 'lighting': {'enabled': True, 'max_segments': 2}})
    light = add_lighting(c, base).assembly.lighting
    assert {s['emission'] for s in light['segments']} == {'underside'}
    strict = replace(c, lighting=replace(c.lighting, emission='backwash'))
    with pytest.raises(ValueError, match='fewer than two.*emission "auto"'):
        add_lighting(strict, base)


def test_legacy_lighting_supplement_config_is_normalised():
    from parametric_deco.lighting import LEGACY_LIGHTING
    from dataclasses import asdict
    from parametric_deco.config import Lighting
    current = asdict(Lighting())
    legacy = {k: v for k, v in current.items() if k not in LEGACY_LIGHTING}
    assert {**LEGACY_LIGHTING, **legacy} == {**current, 'emission': 'underside'}


@pytest.fixture(scope='module')
def lit_rib_study():
    from parametric_deco.assembly import assemble
    return assemble(config_from_dict({'style': 'rib-study', 'lighting': {'enabled': True}}))


def test_wall_mount_uses_free_front_access_bores(lit_rib_study):
    from parametric_deco.validation import xy_footprint
    a = lit_rib_study.assembly
    plan = a.composition['wall_mount']
    assert plan['status'] == 'ok'
    primary = [x for x in plan['anchors'] if x['role'] == 'primary']
    assert len(primary) == 2
    assert primary[0]['xy_mm'][0] < 0 < primary[1]['xy_mm'][0]
    assert plan['standoff']['length_mm'] == 10
    assert plan['estimated_mass_kg'] > 0
    others = [xy_footprint(a.definition_for(i), i.transform) for i in a.instances
              if i.role != 'backplate']
    for anchor in plan['anchors']:
        point = Point(anchor['xy_mm'])
        assert all(shape.distance(point) >= 10 for shape in others)


def test_projection_targets_all_styles_and_skip_hardware(lit_rib_study):
    from parametric_deco.visuals.atlas import generate_atlas
    from parametric_deco.visuals.visibility import projection_visibility
    a = lit_rib_study.assembly
    vis = projection_visibility(a)
    assert 'm1-closure--front' in vis['recommended_surface_ids']
    atlas = generate_atlas(a, 512, 512)
    roles = {i.instance_id: i.role for i in a.instances}
    assert all(roles[t['instance_id']] != 'mounting-hardware'
               and not roles[t['instance_id']].startswith('led-') for t in atlas.manifest['tiles'])
    targets = atlas.manifest['lighting_targets']
    assert len(targets) == len(a.lighting['segments'])
    assert all(t['tile_id'] and 0 <= t['atlas_uv'][0] <= 1 for t in targets)
    world = np.asarray(atlas.textures['worldData']).astype(float)
    fine = np.asarray(atlas.textures['worldFineData']).astype(float)
    valid = world[..., 3] > 0
    coarse = world[..., :3] / 255
    precise = (world[..., :3] + fine[..., :3] / 255 - 0.5) / 255
    assert np.abs(precise - coarse)[valid].max() <= 0.5 / 255 + 1e-9
    assert 'world-fine.png' == atlas.manifest['inputs']['worldFineData']


@pytest.mark.parametrize('data', [
    {'parameters': {'curvature': 1.3}},
    {'parameters': {'spread': 0.85}},
    {'style': 'layered-creature', 'parameters': {'limb_reach': 0.85}},
    {'style': 'radial-weave', 'parameters': {'rotation_deg': 30}},
    {'style': 'rib-study', 'parameters': {'recipe': {'length_mm': 250,
                                                     'stations_mm': [60, 120, 180]}}},
])
def test_previously_failing_combinations_build(data):
    from parametric_deco.assembly import assemble
    build = assemble(config_from_dict(data))
    assert build.report.digital_valid, [i for i in build.report.issues if i.severity == 'error']


def test_module_without_feasible_edge_is_reported_not_fatal():
    from parametric_deco.lighting import add_lighting
    from parametric_deco.model import PartDefinition, PartInstance
    base = _two_hosts()
    tiny = PartDefinition.from_polygon('tiny', box(-6, 100, 6, 112), 6)
    a = base.assembly
    host = PartInstance('tiny', 'tiny', tiny.revision,
                        ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 60), (0, 0, 0, 1)),
                        module_id='m-tiny', role='armour')
    base = replace(base, assembly=replace(a, definitions=(*a.definitions, tiny),
                                          instances=(*a.instances, host)))
    c = config_from_dict({'style': 'rib-study', 'lighting': {'enabled': True, 'max_segments': 3}})
    build = add_lighting(c, base)
    light = build.assembly.lighting
    assert light['density']['uncovered_modules'] == ['m-tiny']
    assert {s['module_id'] for s in light['segments']} == {'m0', 'm1'}
    assert any('m-tiny' in w for w in build.warnings)
