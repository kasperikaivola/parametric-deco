import json

import pytest

from parametric_deco.config import config_from_dict


@pytest.mark.parametrize('style', ['laminar', 'layered-creature', 'radial-weave', 'rib-study'])
def test_style_roundtrip(style):
    config = config_from_dict({'schema_version': 2, 'style': style, 'parameters': {}})
    public = config.to_dict()
    assert public['style'] == style
    assert public['schema_version'] == 2
    assert not {'organism', 'creature', 'composition', 'module', 'placements'} & public.keys()
    assert config_from_dict(public) == config


@pytest.mark.parametrize('data', [
    {'schema_version': 1}, {'organism': {}}, {'creature': {}}, {'composition': {}},
])
def test_old_requests_are_explicitly_rejected(data):
    with pytest.raises(ValueError, match='schema-v2'):
        config_from_dict(data)


@pytest.mark.parametrize('data', [
    {'style': 'unknown'}, {'style': 'laminar', 'parameters': {'limb_count': 4}},
    {'style': 'radial-weave', 'parameters': {'curvature': 1}},
    {'schema_version': True}, {'parameters': []},
])
def test_invalid_style_schema_and_parameters(data):
    with pytest.raises(ValueError):
        config_from_dict(data)


def test_cli_styles_and_init(tmp_path, capsys):
    from parametric_deco.cli import main
    assert main(['styles']) == 0
    styles = json.loads(capsys.readouterr().out)
    assert {s['style'] for s in styles} == {'laminar', 'layered-creature', 'radial-weave', 'rib-study'}
    for style in styles:
        path = tmp_path / (style['style'] + '.json')
        assert main(['init', '--style', style['style'], '--out', str(path)]) == 0
        assert config_from_dict(json.loads(path.read_text())).style == style['style']
        capsys.readouterr()
    assert main(['init', '--out', str(path)]) == 2
    assert 'exists' in capsys.readouterr().err


def test_default_is_laminar():
    from parametric_deco.config import DesignConfig
    assert config_from_dict({}) == DesignConfig()
    assert DesignConfig().style == 'laminar'


def test_common_polygon_board_changes_previous_creature_manufacturing_identity():
    from pathlib import Path
    from parametric_deco.geometry.creature import request_signature
    # The earlier anatomical board cannot satisfy the new physical polygon cuts.
    # Captured from the pre-v2 public example; no Git checkout/history needed.
    config = config_from_dict(json.loads(Path('examples/creature-mask.json').read_text()))
    assert request_signature(config) != (
        '9926851e9b6fca328ed53126efe5a6f0a940d5c72d44a6e8f3b1f80619c59841'
    )
    assert request_signature(config_from_dict(config.to_dict())) == request_signature(config)


def test_cross_style_inventory_requires_new_cuts():
    from parametric_deco.assembly import assemble
    from parametric_deco.config import STYLE_PARAMETERS
    for source in STYLE_PARAMETERS:
        config = config_from_dict({'style': source})
        build = assemble(config)
        saved = json.loads(json.dumps(build.inventory.to_dict()))
        replay = assemble(config_from_dict(config.to_dict()), build.inventory)
        assert json.loads(json.dumps(replay.inventory.to_dict())) == saved
        for target in STYLE_PARAMETERS.keys() - {source}:
            with pytest.raises(ValueError, match='style.*new cuts'):
                assemble(config_from_dict({'style': target}), build.inventory)
        assert json.loads(json.dumps(build.inventory.to_dict())) == saved
