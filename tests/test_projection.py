"""Projection settings, atlas parity and immutable manufacturing regressions."""
import json
from dataclasses import replace

import pytest

from parametric_deco.config import config_from_dict


def test_projection_roundtrip_and_strict_validation():
    config = config_from_dict({'projection': {'effect':'rings', 'speed':-0.4,
                                             'color':[1,0.2,0,1]}})
    assert config.projection.effect == 'rings'
    assert config_from_dict(config.to_dict()) == config
    for values in ({'effect':'typo'}, {'speed':True}, {'speed':float('nan')},
                   {'color':[1,0,0]}, {'color':[1,0,2,1]}, {'repeats':0},
                   {'enabled':'yes'}, {'atlas_width':15}, {'surfaces':'typo'}):
        with pytest.raises(ValueError, match='projection'):
            config_from_dict({'projection':values})


def test_projection_only_edits_preserve_cad_state_and_inventory_identity():
    from parametric_deco.desktop_state import PreviewState, cad_fingerprint
    from parametric_deco.geometry.creature import request_signature
    from parametric_deco.organism_assembly import signature
    state = PreviewState()
    config = config_from_dict({}).to_dict()
    revision = state.edit(json.dumps(config))
    state.complete(revision, True)
    config['projection']['speed'] = -0.5
    state.edit(json.dumps(config))
    assert state.ready and state.revision == revision
    assert state.config['projection']['speed'] == -0.5
    assert cad_fingerprint(config) == cad_fingerprint(config_from_dict({}).to_dict())
    for style, identify in [('layered-creature', request_signature), ('laminar', signature)]:
        original = config_from_dict({'style':style})
        updated = replace(original, projection=config_from_dict(config).projection)
        assert identify(original) == identify(updated)


def test_configured_projection_export_uses_shared_shader_and_settings(tmp_path):
    from parametric_deco.visuals.atlas import generate_atlas
    from parametric_deco.visuals.isf import export_isf_resources, shader_metadata
    from test_atlas import fixture
    settings = config_from_dict({'projection':{'effect':'rings','speed':-0.4,
                                               'brightness':0.7}}).projection
    atlas = generate_atlas(fixture(), 128, 128)
    out = tmp_path / 'projection'
    export_isf_resources(atlas, out, projection=settings)
    saved = json.loads((out / 'projection.json').read_text())
    assert saved['speed'] == -0.4
    source = (out / 'projection.fs').read_text()
    inputs = {entry['NAME']:entry for entry in shader_metadata(source)['INPUTS']}
    assert inputs['speed']['DEFAULT'] == -0.4
    assert inputs['brightness']['DEFAULT'] == 0.7
    assert 'decoEffect' in source


def test_projection_mesh_respects_faces_and_holes(tmp_path):
    import numpy as np
    from shapely.geometry import box
    from parametric_deco.model import Assembly, PartDefinition, PartInstance
    from parametric_deco.visuals.preview import write_projection
    part = PartDefinition.from_polygon('holed',box(0,0,100,100).difference(box(30,30,70,70)),6)
    assembly = Assembly((part,),(PartInstance('a',part.definition_id,part.revision),))
    settings = config_from_dict({'projection':{'atlas_width':128,'atlas_height':128}}).projection
    result = write_projection(assembly,tmp_path,settings)
    assert result['faces'] and 'decoEffect' in result['shader']
    area = 0
    for face in result['faces']:
        positions = np.array(face['positions'])
        assert len(positions) == len(face['uv']) and np.isfinite(positions).all()
        uv = np.array(face['uv'])
        assert np.min(uv) >= 0 and np.max(uv) <= 1
        for triangle in positions.reshape(-1,3,3):
            area += np.linalg.norm(np.cross(triangle[1]-triangle[0],triangle[2]-triangle[0]))/2
    assert area == pytest.approx(part.polygon.area)
    assert (tmp_path/'projection/edges.png').exists()


@pytest.mark.parametrize('style',['rib-study','laminar','layered-creature','radial-weave'])
def test_projection_edits_reuse_exact_saved_inventory(style):
    from parametric_deco.assembly import assemble
    original = config_from_dict({'style':style})
    first = assemble(original)
    frozen = json.dumps(first.inventory.to_dict(),sort_keys=True)
    changed = replace(original,projection=replace(original.projection,effect='checker',repeats=8))
    replay = assemble(changed,first.inventory)
    assert replay.report.digital_valid, replay.report.to_dict()
    assert json.dumps(replay.inventory.to_dict(),sort_keys=True) == frozen
    assert json.dumps(first.inventory.to_dict(),sort_keys=True) == frozen


def test_projection_refresh_reuses_assembly(tmp_path,monkeypatch):
    from parametric_deco import assembly
    from parametric_deco.desktop_worker import run_request
    config = config_from_dict({'style':'rib-study'}).to_dict()
    first = tmp_path/'first'
    run_request({'mode':'preview','config':config,'out':str(first)})
    def forbid(*args,**kwargs):
        raise AssertionError('projection refresh rebuilt physical CAD')
    monkeypatch.setattr(assembly,'assemble',forbid)
    config['projection'].update(surfaces='all',atlas_width=512,atlas_height=512)
    out = tmp_path/'refresh'
    result = run_request({'mode':'projection','config':config,'source':str(first),'out':str(out)})
    assert result['digital_valid']
    assert json.loads((out/'projection/atlas.json').read_text())['dimensions'] == [512,512]
    assert (out/'assembly.json').read_bytes() == (first/'assembly.json').read_bytes()


def test_small_projection_atlas_does_not_block_cad_or_cutting_exports(tmp_path):
    from parametric_deco.desktop_worker import run_request
    config = config_from_dict({'style':'rib-study','projection':{
        'atlas_width':128,'atlas_height':128,'surfaces':'all'}}).to_dict()
    out = tmp_path/'preview'
    result = run_request({'mode':'preview','config':config,'out':str(out)})
    assert result['digital_valid']
    scene = json.loads((out/'scene.json').read_text())
    assert 'atlas too small' in scene['projection']['error']
    assert scene['projection']['faces'] == []
    exported = tmp_path/'export'
    result = run_request({'mode':'export','config':config,'out':str(exported)})
    assert result['digital_valid'] and list((exported/'cuts').glob('*.svg'))
    assert (exported/'projection/projection.json').exists()
    assert (exported/'projection/error.json').exists()


def test_cli_saves_effective_projection_settings_and_selection(tmp_path,capsys):
    from parametric_deco.cli import main
    from test_atlas import fixture
    source = tmp_path/'source'
    source.mkdir()
    (source/'assembly.json').write_text(json.dumps(fixture().to_dict()))
    out = tmp_path/'visuals'
    assert main(['visuals',str(source),'--out',str(out),'--width','256','--height','128',
                 '--surfaces','all']) == 0, capsys.readouterr()
    atlas = json.loads((out/'atlas.json').read_text())
    settings = json.loads((out/'projection.json').read_text())
    assert [settings['atlas_width'],settings['atlas_height']] == atlas['dimensions']
    assert settings['surfaces'] == atlas['surface_selection']['mode']
    explicit = tmp_path/'explicit'
    assert main(['visuals',str(source),'--out',str(explicit),'--width','128','--height','128',
                 '--surface','a--front']) == 0
    saved = json.loads((explicit/'projection-selection.json').read_text())
    assert saved['surface_ids'] == ['a--front'] and saved['mode'] == 'explicit'
