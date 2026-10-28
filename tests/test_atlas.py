import numpy as np
import pytest
from shapely.geometry import Polygon


def fixture():
    from parametric_deco.model import Assembly, PartDefinition, PartInstance

    part = PartDefinition.from_polygon("asymmetric", Polygon([(0, 0), (100, 0), (0, 40)]), 6)
    instance = PartInstance("a", part.definition_id, part.revision)
    return Assembly((part,), (instance,), effect_paths=(("a", 0.0, 1.0),))


def test_asymmetric_mask_orientation_data_and_background():
    from parametric_deco.visuals.atlas import generate_atlas

    result = generate_atlas(fixture(), 256, 256)
    tile = next(t for t in result.manifest["tiles"] if t["surface_id"] == "front")
    x, y, w, h = tile["pixel_rect"]
    mask = np.array(result.textures["localData"])[:, :, 3]
    # Top-left PNG corresponds to face-local +V, so triangle upper-right is empty.
    assert mask[y + int(h * 0.1), x + int(w * 0.9)] == 0
    assert mask[y + int(h * 0.9), x + int(w * 0.1)] == 255
    assert mask[0, 0] == 0
    assert tile["uv_rect"][1] < tile["uv_rect"][3]
    assert result.manifest["world_quantization_mm"]["step"][0] == pytest.approx(100 / 255)
    assert result.manifest["sampling"]["categorical_ids"] == "nearest, no mipmaps, no sRGB"
    rects = [t["pixel_rect"] for t in result.manifest["tiles"]]
    for i, (a, b, c, d) in enumerate(rects):
        for x, y, w, h in rects[i + 1 :]:
            assert a + c <= x or x + w <= a or b + d <= y or y + h <= b


def test_stable_id_order_and_path_continuity():
    from dataclasses import replace
    from parametric_deco.model import PartInstance
    from parametric_deco.visuals.atlas import generate_atlas

    a = fixture()
    d = a.definitions[0]
    b = PartInstance(
        "b", d.definition_id, d.revision, ((1, 0, 0, 120), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))
    )
    a = replace(a, instances=(b, *a.instances), effect_paths=(("a", 0.0, 0.5), ("b", 0.5, 1.0)))
    first = generate_atlas(a, 256, 256)
    second = generate_atlas(replace(a, instances=tuple(reversed(a.instances))), 256, 256)
    assert first.manifest == second.manifest
    assert first.manifest["paths"][0][2] == first.manifest["paths"][1][1]
    with pytest.raises(ValueError, match="atlas"):
        generate_atlas(a, 8, 8)
