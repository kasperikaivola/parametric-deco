"""Headless desktop request identity, worker and editing contracts."""
import json

import pytest

from parametric_deco.config import config_from_dict


def test_progress_estimate_reaches_the_ceiling_then_creeps():
    from parametric_deco.desktop import progress_fraction

    assert progress_fraction(0, 10) == 0
    assert progress_fraction(10, 10) == pytest.approx(0.9)
    assert progress_fraction(5, 10, floor=0.93) == pytest.approx(0.93)
    assert 0.9 < progress_fraction(15, 10) < 0.98
    assert progress_fraction(100, 10) == pytest.approx(0.98)


def test_parameter_edit_snaps_numbers_and_reports_ranges():
    from parametric_deco.parameter_edit import allowed_text, apply_parameter_edit

    laminar = config_from_dict({}).to_dict()
    assert allowed_text(laminar, ('parameters', 'focal_count')) == 'integer 3, 6 or 9'
    assert allowed_text(laminar, ('parameters', 'branching')) == 'integer 1–3'
    assert allowed_text(laminar, ('parameters', 'arrangement')) == 'whorl or bilateral'
    assert allowed_text(laminar, ('parameters', 'asymmetry')) == '0–0.2'
    assert allowed_text(laminar, ('parameters', 'secondary_lobes')) == 'null or integer 0–1'
    assert allowed_text(laminar, ('envelope', 'width_mm')) == '800–1400'
    assert allowed_text(laminar, ('envelope', 'depth_mm')) == '120–240'

    edited = apply_parameter_edit(laminar, ('parameters', 'focal_count'), '4')
    assert edited['parameters']['focal_count'] == 3
    edited = apply_parameter_edit(laminar, ('parameters', 'focal_count'), '100')
    assert edited['parameters']['focal_count'] == 9
    edited = apply_parameter_edit(laminar, ('parameters', 'branching'), '2.4')
    assert edited['parameters']['branching'] == 2
    edited = apply_parameter_edit(laminar, ('parameters', 'asymmetry'), '9')
    assert edited['parameters']['asymmetry'] == 0.2
    edited = apply_parameter_edit(laminar, ('parameters', 'phase_deg'), '-999')
    assert edited['parameters']['phase_deg'] == -180
    edited = apply_parameter_edit(laminar, ('envelope', 'width_mm'), '2000')
    assert edited['envelope']['width_mm'] == 1400
    edited = apply_parameter_edit(laminar, ('envelope', 'depth_mm'), '10')
    assert edited['envelope']['depth_mm'] == 120
    edited = apply_parameter_edit(laminar, ('parameters', 'arrangement'), 'bilateral')
    assert edited['parameters']['arrangement'] == 'bilateral'
    assert edited['parameters']['symmetry'] == 'bilateral'
    assert config_from_dict(edited)
    edited = apply_parameter_edit(laminar, ('parameters', 'secondary_lobes'), 'null')
    assert edited['parameters']['secondary_lobes'] is None
    edited = apply_parameter_edit(laminar, ('material', 'grade'), 'birch')
    assert edited['material']['grade'] == 'birch'
    edited = apply_parameter_edit(laminar, ('schema_version',), '9')
    assert edited['schema_version'] == 2
    low_pitch = apply_parameter_edit(laminar, ('grid', 'pitch_x_mm'), '1')
    assert low_pitch['grid']['pitch_x_mm'] >= 42
    assert config_from_dict(low_pitch)
    edited = apply_parameter_edit(laminar, ('grid', 'pitch_x_mm'), '80')
    assert edited['grid']['pitch_x_mm'] == 80
    assert edited['grid']['pitch_y_mm'] == pytest.approx(80 * (3 ** 0.5) / 2)
    assert edited['grid']['offset_mm'] == 40
    assert config_from_dict(edited)
    with pytest.raises(ValueError):
        apply_parameter_edit(laminar, ('parameters', 'arrangement'), 'sideways')

    creature = config_from_dict({'style': 'layered-creature'}).to_dict()
    assert allowed_text(creature, ('parameters', 'limb_count')) == 'integer 2, 4 or 6'
    edited = apply_parameter_edit(creature, ('parameters', 'limb_count'), '5')
    assert edited['parameters']['limb_count'] == 4
    edited = apply_parameter_edit(creature, ('parameters', 'limb_count'), '5.2')
    assert edited['parameters']['limb_count'] == 6
    edited = apply_parameter_edit(creature, ('parameters', 'scale'), '2')
    assert edited['parameters']['scale'] == 1
    edited = apply_parameter_edit(creature, ('envelope', 'depth_mm'), '10')
    assert edited['envelope']['depth_mm'] == 190
    assert config_from_dict(edited)
    shallow = apply_parameter_edit(creature, ('parameters', 'shell_layers'), '3')
    shallow = apply_parameter_edit(shallow, ('envelope', 'depth_mm'), '170')
    assert shallow['envelope']['depth_mm'] == 170
    edited = apply_parameter_edit(shallow, ('parameters', 'shell_layers'), '6')
    assert edited['parameters']['shell_layers'] == 4
    assert config_from_dict(edited)

    radial = config_from_dict({'style': 'radial-weave'}).to_dict()
    assert allowed_text(radial, ('parameters', 'opening_radius_mm')) == '> 0 and ≤ 183'
    assert allowed_text(radial, ('parameters', 'radius_mm')) == '297–340'
    assert allowed_text(radial, ('parameters', 'lobes')) == 'only 3'
    edited = apply_parameter_edit(radial, ('parameters', 'radius_mm'), '900')
    assert edited['parameters']['radius_mm'] == 340
    edited = apply_parameter_edit(radial, ('parameters', 'radius_mm'), '10')
    assert edited['parameters']['radius_mm'] == 297
    edited = apply_parameter_edit(radial, ('parameters', 'lobes'), '8')
    assert edited['parameters']['lobes'] == 3
    edited = apply_parameter_edit(radial, ('parameters', 'opening_radius_mm'), '1000')
    assert edited['parameters']['opening_radius_mm'] == 183
    assert config_from_dict(edited)

    rib = config_from_dict({'style': 'rib-study'}).to_dict()
    assert allowed_text(rib, ('parameters', 'recipe', 'stations_mm')).startswith('ascending')
    assert allowed_text(rib, ('parameters', 'placements', 0, 'x_mm')) == 'any finite number'
    edited = apply_parameter_edit(rib, ('parameters', 'recipe', 'rib_bottom_mm'), '500')
    assert edited['parameters']['recipe']['rib_bottom_mm'] == pytest.approx(44.99)
    assert config_from_dict(edited)
    edited = apply_parameter_edit(rib, ('backplate', 'sides'), '2.2')
    assert edited['backplate']['sides'] == 3
    edited = apply_parameter_edit(rib, ('parameters', 'recipe', 'stations_mm', 0), '1')
    assert edited['parameters']['recipe']['stations_mm'][0] == 55
    edited = apply_parameter_edit(rib, ('parameters', 'placements', 0, 'rib_order', 0), '3')
    assert edited['parameters']['placements'][0]['rib_order'] == [3, 1, 2, 0]
    edited = apply_parameter_edit(rib, ('parameters', 'placements', 0, 'rib_order'), '[3, 2, 1, 0]')
    assert edited['parameters']['placements'][0]['rib_order'] == [3, 2, 1, 0]
    edited = apply_parameter_edit(rib, ('mounting', 'washer_radius_mm'), '100')
    assert edited['mounting']['washer_radius_mm'] == pytest.approx(14.99)
    assert config_from_dict(edited)
    edited = apply_parameter_edit(rib, ('style',), 'laminar')
    assert edited['style'] == 'laminar'
    assert 'focal_count' in edited['parameters']
    assert config_from_dict(edited)


def _find_parameter(tree, name, parent=None):
    count = tree.topLevelItemCount() if parent is None else parent.childCount()
    for index in range(count):
        item = tree.topLevelItem(index) if parent is None else parent.child(index)
        if item.text(0) == name:
            return item
        found = _find_parameter(tree, name, item)
        if found is not None:
            return found
    return None


def test_parameter_table_edits_in_place_and_shows_the_range(monkeypatch):
    monkeypatch.setenv('QT_QPA_PLATFORM', 'offscreen')
    pytest.importorskip('PySide6.QtWidgets')
    from PySide6.QtWidgets import QApplication, QInputDialog
    from parametric_deco.desktop import create_window

    def forbid_dialog(*_args, **_kwargs):
        raise AssertionError('parameter edit opened a dialog')

    monkeypatch.setattr(QInputDialog, 'getMultiLineText', forbid_dialog)
    app = QApplication.instance() or QApplication([])
    window = create_window()
    window.timer.stop()
    window.stop_preview_process()
    try:
        assert window.tree.columnCount() == 3
        assert window.tree.headerItem().text(2) == 'Allowed'
        focal = _find_parameter(window.tree, 'focal_count')
        assert focal.text(2) == 'integer 3, 6 or 9'
        asymmetry = _find_parameter(window.tree, 'asymmetry')
        assert asymmetry.text(2) == '0–0.2'
        focal.setText(1, '100')
        app.processEvents()
        data = json.loads(window.editor.toPlainText())
        assert data['parameters']['focal_count'] == 9
        focal = _find_parameter(window.tree, 'focal_count')
        assert focal.text(1) == '9'
        assert focal.text(2) == 'integer 3, 6 or 9'
    finally:
        window.timer.stop()
        window.stop_preview_process()
        window.dirty = False
        window.close()
        app.processEvents()


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


def test_f3_editable_tree_keeps_lists_defaults_and_invalid_values():
    from parametric_deco.desktop_state import editable_config, replace_value
    raw = {'style':'rib-study','parameters':{'placements':[{'module_id':'old'}]}}
    data = editable_config(raw)
    assert isinstance(data['parameters']['placements'],list)
    assert data['parameters']['placements'][0]['x_mm'] == 25
    assert data['lighting']['enabled'] is False
    replace_value(data,('parameters','placements',0,'x_mm'),'75')
    replace_value(data,('parameters','recipe','stations_mm',0),'60')
    assert data['parameters']['placements'][0]['x_mm'] == 75
    assert data['parameters']['recipe']['stations_mm'][0] == 60
    replace_value(data,('lighting','strip_width_mm'),'0')
    invalid = editable_config(data)
    assert invalid['lighting']['strip_width_mm'] == 0
    replace_value(invalid,('lighting','strip_width_mm'),'12')
    assert config_from_dict(invalid).lighting.strip_width_mm == 12
    radial=editable_config({'style':'radial-weave','parameters':{'rib_permutation':[8,7,6,5,4,3,2,1,0]}})
    replace_value(radial,('parameters','rib_permutation',0),'0')
    assert radial['parameters']['rib_permutation'][0] == 0
    assert editable_config({'style':'invalid','lighting':{'strip_width_mm':0}})['style'] == 'invalid'


def test_choice_editors_have_typed_options_and_nullable_overrides():
    from parametric_deco.parameter_edit import choices_for, apply_parameter_edit
    from parametric_deco.desktop_state import editable_config
    data = editable_config({})
    assert choices_for(data,('parameters','arrangement')) == ('whorl','bilateral')
    assert choices_for(data,('parameters','focal_count')) == (3,6,9)
    assert choices_for(data,('parameters','channels')) == (None,0,1,2,3)
    assert choices_for(data,('lighting','enabled')) == (False,True)
    assert choices_for(data,('lighting','voltage_v')) == (5,12,24)
    assert apply_parameter_edit(data,('lighting','enabled'),'true')['lighting']['enabled'] is True
    assert choices_for(data,('parameters','curvature')) == ()


def test_choice_metadata_tolerates_invalid_dependent_json_values():
    from parametric_deco.desktop_state import editable_config
    from parametric_deco.parameter_edit import choices_for
    data = editable_config({'style':'radial-weave','parameters':{'radius_mm':'unfinished'}})
    assert choices_for(data,('parameters','opening_radius_mm')) == ()
