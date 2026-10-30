"""Headless desktop request identity, worker and editing contracts."""
import json

import pytest

from parametric_deco.config import config_from_dict


def test_revision_state_rejects_out_of_order_results_and_invalid_edits():
    from parametric_deco.desktop_state import PreviewState

    state = PreviewState()
    first = state.edit('{}')
    assert not state.ready
    second = state.edit('{"style":"rib-study"}')
    assert not state.complete(first, True)
    assert not state.ready
    assert state.complete(second, True)
    assert state.ready
    third = state.edit('{')
    assert third > second and state.error and not state.ready
    assert state.good_revision == second
    assert not state.complete(second, True)
    fourth = state.edit('{}')
    assert state.complete(fourth, False, 'CAD collision')
    assert not state.ready and state.error == 'CAD collision'
    assert state.good_revision == second


def test_complete_parameter_tree_round_trip():
    from parametric_deco.desktop_state import replace_value

    data = config_from_dict({'style': 'rib-study'}).to_dict()
    data = json.loads(json.dumps(data))
    replace_value(data, ('parameters', 'placements', 0, 'closure_instance_id'), '"closure-2"')
    replace_value(data, ('parameters', 'placements', 0, 'rib_order'), '[3,2,1,0]')
    replace_value(data, ('cutting_bed',), '{"width_mm":1200,"height_mm":800}')
    assert data['parameters']['placements'][0]['closure_instance_id'] == 'closure-2'
    assert config_from_dict(data).cutting_bed.width_mm == 1200
    with pytest.raises(ValueError):
        replace_value(data, ('material', 'grade'), 'unquoted string')


def test_preview_worker_uses_real_assembly_and_viewer(tmp_path):
    from parametric_deco.desktop_worker import run_request

    request = {'config': config_from_dict({'style':'rib-study'}).to_dict(),
               'mode':'preview', 'out':str(tmp_path / 'preview-build')}
    result = run_request(request)
    assert result['digital_valid']
    out = tmp_path / 'preview-build'
    scene = json.loads((out / 'scene.json').read_text())
    assert scene['units'] == 'mm' and scene['instances']
    assert (out / 'preview/index.html').is_file()
    assert (out / 'preview/viewer.js').is_file()
    assert not (out / 'cuts').exists()


def test_fingerprint_includes_inventory_contents_and_normalized_defaults():
    from parametric_deco.desktop_state import fingerprint

    config = config_from_dict({}).to_dict()
    assert fingerprint(config) == fingerprint(json.loads(json.dumps(config)))
    assert fingerprint(config, {'instances': [1]}) != fingerprint(config, {'instances': [2]})
    assert fingerprint(config) != fingerprint(config, {})


def test_failed_new_request_keeps_last_good_revision():
    from parametric_deco.desktop_state import PreviewState

    state = PreviewState()
    first = state.edit('{}')
    state.complete(first, True)
    second = state.edit('{"style":"rib-study"}')
    state.complete(second, False, 'physical geometry invalid')
    assert state.good_revision == first and not state.ready
    assert state.config['style'] == 'rib-study'
