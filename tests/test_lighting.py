"""Physical lighting supplement, configuration and immutable replay contracts."""
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from parametric_deco.assembly import assemble
from parametric_deco.config import config_from_dict, load_config
from parametric_deco.desktop_state import PreviewState
from parametric_deco.model import Inventory


@pytest.mark.parametrize('field,value', [('strip_width_mm', 0), ('strip_thickness_mm', -1),
    ('led_pitch_mm', float('nan')), ('enabled', 1), ('voltage_v', 7)])
def test_invalid_lighting(field, value):
    with pytest.raises(ValueError, match='lighting'):
        config_from_dict({'lighting': {field: value}})


def test_default_and_desktop_controls():
    c = config_from_dict({})
    assert c.lighting.enabled is False
    s = PreviewState()
    s.edit('{"lighting":{"enabled":true,"strip_width_mm":12}}')
    assert s.config['lighting']['strip_width_mm'] == 12
    assert s.config['lighting']['led_pitch_mm'] > 0


@pytest.fixture(scope='module', params=['organism-small', 'creature-mask',
                                      'radial-weave', 'single-module'])
def lit(request):
    if request.param == 'creature-mask':
        return load_config(Path('examples/layered-creature-led.json'))
    c = load_config(Path('examples') / (request.param + '.json'))
    return config_from_dict({**c.to_dict(), 'lighting': {'enabled': True}})


@pytest.fixture(scope='module')
def lit_build(lit):
    return assemble(lit)


def test_all_styles_physical_lighting(lit, lit_build):
    b = lit_build
    assert b.report.digital_valid, b.report.issues
    light = b.assembly.lighting
    assert len(light['segments']) >= 2
    assert light['input']['position_mm'][1] < 0
    assert light['input']['signals'] == ['V+', 'DATA', 'GND']
    instances = {i.instance_id: i for i in b.assembly.instances}
    for s in light['segments']:
        assert s['led_count'] >= 1
        assert s['shield_margin_mm'] > 0
        assert s['target_instance'] == s['host_instance']
        if s['emission'] == 'backwash':
            assert np.dot(s['emission_direction'], (0, 0, 1)) < -.99
            assert s['throw_mm'] >= lit.lighting.min_throw_mm
            assert not s['concealment']['direct_emitter_view_from_front']
        else:
            assert s['emission'] == 'underside'
            assert np.dot(s['emission_direction'], (0, 0, 1)) > .99
        for name in s['part_instances']:
            p = b.assembly.definition_for(instances[name])
            assert p.polygon.is_valid
            assert len(p.holes) >= 2
        host = instances[s['host_instance']]
        assert host.role != 'backplate'
    assert light['data_route'] == [s['segment_id'] for s in light['segments']]
    assert len(light['jumpers']) == len(light['segments'])
    assert b.inventory == Inventory.from_dict(b.inventory.to_dict())
    import json
    replay = assemble(lit, Inventory.from_dict(json.loads(json.dumps(b.inventory.to_dict()))))
    from parametric_deco.lighting import placement_fingerprint
    assert placement_fingerprint(replay.assembly) == placement_fingerprint(b.assembly)
    assert replay.assembly.lighting == b.assembly.lighting
    from parametric_deco.model import canonical
    # JSON lists and in-memory tuples encode identical immutable stock records.
    assert canonical(replay.inventory.to_dict()) == canonical(b.inventory.to_dict())


def test_no_silent_inventory_manufacture(lit):
    unlit = assemble(replace(lit, lighting=replace(lit.lighting, enabled=False)))
    original = unlit.inventory.to_dict()
    with pytest.raises(ValueError, match='lighting.*inventory|inventory.*lighting'):
        assemble(lit, unlit.inventory)
    assert unlit.inventory.to_dict() == original
    assert all(not i.role.startswith('led-') for i in unlit.assembly.instances)


def test_unsupported_strip_fails(lit):
    with pytest.raises(ValueError, match='lighting'):
        assemble(replace(lit, lighting=replace(lit.lighting, strip_width_mm=500)))


def test_export_and_preview_include_physical_lighting(lit, lit_build, tmp_path):
    import json
    from parametric_deco.export.manifest import export_build
    from parametric_deco.lighting import preview_assembly
    b = lit_build
    preview = preview_assembly(b.assembly)
    assert sum(i.role == 'led-strip' for i in preview.instances) == len(b.assembly.lighting['segments'])
    result = export_build(b, tmp_path / 'export')
    out = tmp_path / 'export'
    route = json.loads((out / 'lighting-routing.json').read_text())
    assert route == b.assembly.lighting
    assert (out / 'lighting-bom.json').exists()
    assert (out / 'views/lighting-section.png').exists()
    assert 'NOT RUN' in (out / 'lighting-instructions.md').read_text()
    manifest = json.loads((out / 'manifest.json').read_text())
    for name in ('lighting-routing.json', 'lighting-bom.json', 'views/lighting-section.png'):
        assert name in manifest['files']
    assert any('/cuts/led-' in str(p) for p in result.paths)


def test_saved_json_replay_and_disable_preserve_inventory(tmp_path):
    import json
    c = load_config(Path('examples/single-module.json'))
    c = replace(c, lighting=replace(c.lighting, enabled=True))
    b = assemble(c)
    saved = Inventory.from_dict(json.loads(json.dumps(b.inventory.to_dict())))
    replay = assemble(c, saved)
    from parametric_deco.lighting import placement_fingerprint
    assert placement_fingerprint(replay.assembly) == placement_fingerprint(b.assembly)
    off = assemble(replace(c, lighting=replace(c.lighting, enabled=False)), saved)
    assert off.inventory.to_dict() == saved.to_dict()
    assert not any(i.role.startswith('led-') for i in off.assembly.instances)
    with pytest.raises(ValueError, match='lighting inventory placement/config changed'):
        assemble(replace(c, lighting=replace(c.lighting, strip_width_mm=12)), saved)


@pytest.mark.parametrize('strip_width', [10, 40])
def test_emitter_corridor_and_power_groups(strip_width):
    from parametric_deco.model import Assembly, PartDefinition, PartInstance, BuildResult
    from parametric_deco.lighting import add_lighting
    from shapely.geometry import box
    parts = [PartDefinition.from_polygon('back', box(-180, -180, 180, 180), 6, kind='backplate')]
    instances = [PartInstance('back', parts[0].definition_id, parts[0].revision,
                             ((1,0,0,0),(0,1,0,0),(0,0,1,10),(0,0,0,1)), role='backplate')]
    for n, (x,y) in enumerate(((-70,-70),(70,70))):
        p = PartDefinition.from_polygon(f'host-{n}', box(x-40,y-40,x+40,y+40), 6)
        parts.append(p)
        instances.append(PartInstance(p.definition_id,p.definition_id,p.revision,
                                      ((1,0,0,0),(0,1,0,0),(0,0,1,60),(0,0,0,1)),
                                      module_id=f'm{n}',role='armour'))
    a = Assembly(tuple(parts),tuple(instances),envelope_mm=(400,400,100))
    c = config_from_dict({'style':'rib-study','lighting': {'enabled':True,'injection_limit_a':.07, 'max_segments':2, 'strip_width_mm':strip_width}})
    b = add_lighting(c, BuildResult(a, tuple(parts), inventory=Inventory(tuple(parts),tuple(instances))))
    light = b.assembly.lighting
    assert len(light['power']['injection_groups']) == 2
    for jumper in light['jumpers']:
        if jumper['to'] in {g[0] for g in light['power']['injection_groups']}:
            assert jumper['signals'] == ['DATA', 'GND']
    assert len(light['power']['feeds']) == 2
    tie = next(row for row in light['bom'] if row['item'].startswith('reusable ties'))
    assert tie['minimum_length_mm'] >= 2*(strip_width+6+6+2)+20
    for s in light['segments']:
        assert s['checks']['emitter_corridor_clear']
        assert len(s['bolt_envelopes']) == 2
        assert all(b['diameter_mm'] == 7 for b in s['bolt_envelopes'])


def test_short_segments_cannot_claim_reusable_tie_retention():
    with pytest.raises(ValueError, match='lighting.*12 mm'):
        config_from_dict({'lighting': {'enabled': True, 'led_pitch_mm': 1}})


def test_density_budget_adds_separated_carriers():
    from parametric_deco.model import Assembly, PartDefinition, PartInstance, BuildResult
    from parametric_deco.lighting import add_lighting
    from shapely.geometry import box
    parts = [PartDefinition.from_polygon('back', box(-180,-180,180,180),6,kind='backplate'),
             PartDefinition.from_polygon('host', box(-100,-80,100,80),6)]
    instances = [PartInstance('back','back',parts[0].revision,
                              ((1,0,0,0),(0,1,0,0),(0,0,1,10),(0,0,0,1)),role='backplate'),
                 PartInstance('host','host',parts[1].revision,
                              ((1,0,0,0),(0,1,0,0),(0,0,1,60),(0,0,0,1)),
                              module_id='m0',role='armour')]
    a = Assembly(tuple(parts),tuple(instances),envelope_mm=(400,400,100))
    base = BuildResult(a,tuple(parts),inventory=Inventory(tuple(parts),tuple(instances)))
    c = config_from_dict({'style':'rib-study','lighting':{'enabled':True,'max_segments':6}})
    light = add_lighting(c,base).assembly.lighting
    assert len(light['segments']) == 6
    points = [s['emitter_position_mm'] for s in light['segments']]
    assert min(np.linalg.norm(np.array(a)-b) for n,a in enumerate(points)
               for b in points[n+1:]) >= 30
    assert light['density']['requested_max_segments'] == 6
    assert light['density']['achieved_segments'] == 6


def test_density_preserves_actual_rotational_carrier_material():
    from shapely.geometry import box
    from parametric_deco.model import Assembly, PartDefinition, PartInstance, BuildResult
    from parametric_deco.geometry.symmetry import matrices, verify_symmetry
    from parametric_deco.lighting import add_lighting
    c = config_from_dict({'lighting': {'enabled':True,'max_segments':7}})
    board = PartDefinition.from_polygon('back',box(-180,-180,180,180),6,kind='backplate')
    host = PartDefinition.from_polygon('host',box(50,-40,130,40),6)
    instances = [PartInstance('back','back',board.revision,
                  ((1,0,0,0),(0,1,0,0),(0,0,1,10),(0,0,0,1)),role='backplate')]
    for n,matrix in enumerate(matrices(c)):
        pose = np.eye(4)
        pose[:2, :2] = matrix
        pose[2, 3] = 60
        instances.append(PartInstance(f'primary-{n*2}-plate','host',host.revision,
                           pose,module_id=f'primary-{n*2}',role='armour'))
    a=Assembly((board,host),tuple(instances),envelope_mm=(400,400,100))
    b=add_lighting(c,BuildResult(a,(board,host),inventory=Inventory(a.definitions,a.instances)))
    # The single bottom cable entry intentionally has no C3 counterparts.
    lamps=replace(b.assembly, instances=tuple(i for i in b.assembly.instances
                    if not i.instance_id.startswith('led-input')), hardware_bounds=())
    assert not verify_symmetry(lamps,c)
    assert len(b.assembly.lighting['segments']) == 6
    assert b.assembly.lighting['density']['capacity_limited']


def _retention_fixture(strip_thickness=2, emission='underside'):
    from shapely.geometry import box
    from parametric_deco.model import Assembly, PartDefinition, PartInstance
    from parametric_deco.lighting import _candidate
    part = PartDefinition.from_polygon('flat-host', box(-100,-80,100,80),6)
    host = PartInstance('host',part.definition_id,part.revision,
                       ((1,0,0,0),(0,1,0,0),(0,0,1,60),(0,0,0,1)),role='armour')
    a = Assembly((part,),(host,),envelope_mm=(400,400,100))
    c = config_from_dict({'style':'rib-study','lighting':{'enabled':True,
                          'strip_thickness_mm':strip_thickness,'max_segments':2,
                          'emission':emission}})
    from shapely.geometry import Point
    distance = part.polygon.exterior.project(Point(0,-80))
    return a,host,c,distance,_candidate


@pytest.mark.parametrize('board_z',[10,20])
def test_f1_input_slots_and_full_ties_clear_intact_board(board_z):
    from parametric_deco.validation import xy_footprint
    from parametric_deco.cad import overlap_volume
    from shapely.geometry import Polygon
    a,host,c,distance,candidate = _retention_fixture()
    pose=np.array(host.transform)
    pose[2,3]=board_z
    host=replace(host,transform=pose)
    a=replace(a,instances=(host,))
    ds,ins,s = candidate(a,host,c,distance,0,input_anchor=True)
    tray = ds[0]
    board = a.definition_for(host)
    # Both exits of every strain-relief slot must be exposed outside intact board.
    slot_parts = [type(tray).from_polygon('slot',Polygon(h),1)
                  for h in tray.holes if abs(Polygon(h).area-6) < 1e-6]
    assert len(slot_parts) == 4
    assert all(xy_footprint(p,ins[0].transform).intersection(
        xy_footprint(board,host.transform)).area < 1e-8 for p in slot_parts)
    from parametric_deco.lighting import retention_geometry
    envelopes = retention_geometry(s)
    assert any(p.kind == 'tie-head' for _,p in envelopes)
    assert any(p.kind == 'input-cable' for _,p in envelopes)
    assert all(overlap_volume(p,i.transform,board,host.transform) < 1e-8
               for i,p in envelopes)
    assert all(overlap_volume(p,i.transform,wood,inst.transform) < 1e-8
               for i,p in envelopes for inst,wood in zip(ins,ds))


def test_f2_strip_thickness_reserves_tie_and_clearance():
    with pytest.raises(ValueError,match='tie'):
        _retention_fixture(5.5)
    # Backwash strips hang below the tray, so the pad gap no longer limits thickness.
    a,host,c,distance,candidate = _retention_fixture(5.5, 'backwash')
    assert candidate(a,host,c,distance,0) is not None


def test_backwash_emitters_face_away_and_need_throw():
    from shapely.geometry import box
    from parametric_deco.lighting import _emission_clear, retention_geometry
    from parametric_deco.model import PartDefinition, PartInstance
    a,host,c,distance,candidate = _retention_fixture(2, 'backwash')
    ds,ins,s = candidate(a,host,c,distance,0)
    assert s['emission'] == 'backwash'
    assert np.dot(s['emission_direction'], (0,0,1)) < -.99
    assert s['concealment']['direct_emitter_view_from_front'] is False
    assert s['concealment']['strip_body_hidden_below_deg'] > 70
    # Emitting face hangs below the tray: host underside 60, tray 2 stock lower.
    assert s['emitter_position_mm'][2] == pytest.approx(60-12-2)
    heads = [p for i,p in retention_geometry(s) if p.kind == 'tie-head']
    assert heads and all(i.transform[2][3] >= 60-6-1e-9 for i,p in retention_geometry(s)
                         if p.kind == 'tie-head')
    assert _emission_clear(a,s,c,[(host,a.definition_for(host))])
    # A part just below the strip removes the required throw.
    blocker = PartDefinition.from_polygon('blocker',box(-30,-90,30,-50),6)
    pose = ((1,0,0,0),(0,1,0,0),(0,0,1,60-12-2-8-6),(0,0,0,1))
    other = PartInstance('blocker','blocker',blocker.revision,pose)
    assert not _emission_clear(a,s,c,[(other,blocker)])


@pytest.mark.parametrize('depth,y0,y1',[(12.5,5,21),(14.5,2.5,7.5)])
def test_f2_rear_return_and_head_are_collision_checked(depth,y0,y1):
    from parametric_deco.lighting import _hardware_clear, _clear
    from parametric_deco.model import PartDefinition,PartInstance
    from shapely.geometry import box
    a,host,c,distance,candidate = _retention_fixture(4.5)
    ds,ins,s = candidate(a,host,c,distance,0)
    # Half-mm obstacle immediately behind tray: wood clears, rear tie does not.
    obstacle = PartDefinition.from_polygon('obstacle',box(-1.25,y0,1.25,y1),.5)
    pose=np.array(s['carrier_frame'])
    pose[:3,3]-=pose[:3,2]*depth
    # Align with the first real tie rather than a schematic centre line.
    pose[:3,3]+=pose[:3,0]*(-s['strip_length_mm']/2+3)
    other = PartInstance('obstacle','obstacle',obstacle.revision,pose)
    assert _clear(a,{d.definition_id:d for d in ds},ins,[(other,obstacle)])
    assert not _hardware_clear(a,s,[(host,a.definition_for(host)),(other,obstacle)])


def test_placement_hash_normalizes_numpy_scalars_and_signed_zero_after_json():
    import json
    from parametric_deco.model import Assembly
    from parametric_deco.lighting import placement_fingerprint
    # Source blade-clip envelopes use NumPy bounds; JSON reload uses Python floats.
    a = Assembly((), (), hardware_bounds=(('clip',np.float64(-0.0),np.float64(.123456789),
                  np.float64(0),np.float64(1),np.float64(2),np.float64(3)),))
    loaded = Assembly.from_dict(json.loads(json.dumps(a.to_dict())))
    assert placement_fingerprint(a) == placement_fingerprint(loaded)
    moved = replace(loaded, hardware_bounds=(('clip',0.001,.123456789,0,1,2,3),))
    assert placement_fingerprint(a) != placement_fingerprint(moved)
