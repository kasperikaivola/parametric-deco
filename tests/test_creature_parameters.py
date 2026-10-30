"""Controls must change manufactured composition, not just the preview."""

from dataclasses import replace
import pytest
from parametric_deco.config import CreatureMask, DesignConfig, config_from_dict, validate_config


def test_alien_default_controls_and_json_roundtrip():
    p = CreatureMask()
    assert p.limb_count == 4
    assert p.cavity_count == 6
    assert p.ribs_per_limb == 6
    assert p.limb_layers == 4
    assert p.shell_layers == 6
    c = DesignConfig(style="layered-creature", parameters=p)
    assert config_from_dict(c.to_dict()) == c


@pytest.mark.parametrize(
    "field", ["limb_count", "cavity_count", "ribs_per_limb", "shell_layers", "limb_layers"]
)
@pytest.mark.parametrize("value", [True, 3.5, 4.0, "4", -1, 100])
def test_counts_reject_nonintegers_and_out_of_range(field, value):
    c = DesignConfig(style="layered-creature", parameters=replace(CreatureMask(), **{field: value}))
    assert not validate_config(c).digital_valid
    with pytest.raises(ValueError):
        config_from_dict(c.to_dict())


@pytest.mark.parametrize("field", ["limb_reach", "limb_width", "rib_height_mm", "asymmetry"])
@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), -1, 1000])
def test_shape_controls_reject_invalid_numbers(field, value):
    c = DesignConfig(style="layered-creature", parameters=replace(CreatureMask(), **{field: value}))
    assert not validate_config(c).digital_valid


@pytest.mark.parametrize(
    "limbs,cavities,ribs,layers",
    [(2, 3, 3, 3), (3, 5, 4, 4), (4, 6, 6, 6), (5, 7, 4, 5), (6, 8, 3, 3)],
)
def test_profiles_follow_numeric_composition(limbs, cavities, ribs, layers):
    from parametric_deco.geometry.creature_profiles import (
        profiles,
        module_roots,
        cavity_voids,
        rib_stations,
    )

    p = CreatureMask(
        limb_count=limbs, cavity_count=cavities, ribs_per_limb=ribs, shell_layers=layers
    )
    shapes = profiles(settings=p)
    assert len(shapes) == limbs + 1
    assert set(shapes) == set(module_roots(p))
    assert len(shapes["head"]) == layers
    assert len(cavity_voids(p)) == cavities
    for name, parts in shapes.items():
        assert all(q.is_valid and q.geom_type == "Polygon" for q in parts)
        if name != "head":
            assert len(parts) == p.limb_layers
            assert len(rib_stations(name, settings=p)) == ribs


@pytest.mark.parametrize(
    "field,value",
    [
        ("limb_reach", 0.9),
        ("limb_width", 1.1),
        ("asymmetry", 0),
        ("rib_height_mm", 50),
        ("curl", 1.2),
    ],
)
def test_controls_change_real_shapes_or_rib_dimensions(field, value):
    from parametric_deco.geometry.creature_profiles import profiles, rib_stations

    a, b = CreatureMask(), replace(CreatureMask(), **{field: value})
    if field == "rib_height_mm":
        assert (
            rib_stations("crown-left", settings=a)[0][3]
            != rib_stations("crown-left", settings=b)[0][3]
        )
    else:
        before, after = profiles(settings=a), profiles(settings=b)
        assert any(
            not before[name][-1].equals(after[name][-1]) for name in before if name != "head"
        )


@pytest.mark.parametrize("limbs", [2, 3, 4, 5, 6])
def test_generated_inventory_counts_every_requested_limb_and_rib(limbs):
    from parametric_deco.geometry.creature import generate_creature

    p = CreatureMask(
        limb_count=limbs, ribs_per_limb=3, cavity_count=4, shell_layers=4, limb_layers=3
    )
    bundle, layout = generate_creature(DesignConfig(style="layered-creature", parameters=p))
    assert len(layout["modules"]) == limbs + 1
    assert len([i for i in bundle.instances if i.role == "blade"]) == limbs * 3
    assert len(layout["removal_order"]) == limbs + 1
    assert len(layout["modules"][0]["plate_ids"]) == 4
    assert layout["family"] == "creature-organism-v3"


@pytest.fixture(scope="module")
def default_manufacture():
    from parametric_deco.assembly import assemble

    result = assemble(DesignConfig(style="layered-creature", parameters=CreatureMask()))
    assert result.report.digital_valid, result.report.to_dict()
    return result


@pytest.mark.parametrize(
    "field,value",
    [
        ("limb_count", 2),
        ("cavity_count", 4),
        ("ribs_per_limb", 3),
        ("shell_layers", 4),
        ("limb_layers", 3),
        ("limb_reach", 0.9),
        ("limb_width", 0.9),
        ("rib_height_mm", 50),
        ("asymmetry", 0),
    ],
)
def test_changed_composition_or_shape_requires_new_cuts(default_manufacture, field, value):
    from parametric_deco.assembly import assemble

    changed = DesignConfig(style="layered-creature", parameters=replace(CreatureMask(), **{field: value}))
    with pytest.raises(ValueError, match="new cuts"):
        assemble(changed, default_manufacture.inventory)


@pytest.mark.parametrize("count,cavities", [(2, 3), (3, 5), (4, 6), (5, 7), (6, 8)])
def test_composition_variants_assemble_as_actual_parts(count, cavities):
    from parametric_deco.assembly import assemble

    p = CreatureMask(
        limb_count=count,
        cavity_count=cavities,
        ribs_per_limb=3,
        shell_layers=4,
        limb_layers=3,
        limb_reach=0.9,
        limb_width=0.95,
        rib_height_mm=55,
    )
    result = assemble(DesignConfig(style="layered-creature", parameters=p))
    assert result.report.digital_valid, result.report.to_dict()
    assert len(result.assembly.composition["modules"]) == count + 1
    assert len([i for i in result.assembly.instances if i.role == "blade"]) == count * 3
    assert len(result.assembly.composition["clear_aperture_probe_areas_mm2"]) == cavities
