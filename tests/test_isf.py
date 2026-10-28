import json
import math

import pytest


def test_isf_resources_match_image_inputs_and_controls(tmp_path):
    from parametric_deco.visuals.atlas import generate_atlas
    from parametric_deco.visuals.isf import export_isf_resources, shader_metadata, pulse_reference
    from test_atlas import fixture

    atlas = generate_atlas(fixture(), 256, 256)
    export_isf_resources(atlas, tmp_path / "visuals")
    manifest = json.loads((tmp_path / "visuals/atlas.json").read_text())
    for name in ("calibration.fs", "edge-pulse.fs"):
        metadata = shader_metadata((tmp_path / "visuals" / name).read_text())
        assert metadata["ISFVSN"] == "2"
        for item in metadata["INPUTS"]:
            if item["TYPE"] == "image":
                assert (tmp_path / "visuals" / manifest["inputs"][item["NAME"]]).exists()
    metadata = shader_metadata((tmp_path / "visuals/edge-pulse.fs").read_text())
    assert {"speed", "phase", "color", "width"} <= {i["NAME"] for i in metadata["INPUTS"]}
    for speed in (0, 1, -1):
        for width in (0, 0.01, 1):
            assert math.isfinite(pulse_reference(0.5, 0.1, 1, speed, 0, width))


def test_offscreen_host_rendering_not_available():
    pytest.skip(
        "No Wire/Arena or configured offscreen ISF host; static checks are not runtime validation"
    )
