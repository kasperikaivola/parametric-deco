from shapely.geometry import Point


def test_creature_profiles_have_face_cavities_and_connected_sweeps():
    from parametric_deco.geometry.creature_profiles import profiles, eye_voids

    shapes = profiles()
    assert set(shapes) == {"head", "crown-left", "crown-right", "jaw-left", "jaw-right"}
    assert all(
        p.is_valid and p.geom_type == "Polygon" for layers in shapes.values() for p in layers
    )
    assert len(shapes["head"][0].interiors) >= 2
    assert not shapes["head"][-1].covers(Point(125, -70))
    assert all(
        p.intersection(eye_voids()[0]).area < 1e-6
        for name, layers in shapes.items()
        if name != "head"
        for p in layers
    )
    assert all(not p.covers(Point(-100, 45)) for p in shapes["head"])
    assert all(not p.covers(Point(100, 45)) for p in shapes["head"])
    assert shapes["crown-left"][0].bounds[0] < -400
    assert shapes["jaw-left"][0].bounds[1] < -300
    assert len(eye_voids()) == 2


def creature_config(**kwargs):
    from parametric_deco.config import DesignConfig, CreatureMask

    return DesignConfig(creature=CreatureMask(**kwargs))


def test_creature_configuration_rejects_invalid_requests():
    import pytest
    from dataclasses import replace
    from parametric_deco.config import config_from_dict, validate_config, RadialWeave

    c = creature_config()
    assert config_from_dict(c.to_dict()) == c
    for values in ({"scale": float("nan")}, {"scale": 1.4}, {"posture": "anything"}, {"curl": 0}):
        assert not validate_config(replace(c, creature=replace(c.creature, **values))).digital_valid
    with pytest.raises(ValueError, match="family|creature|composition"):
        config_from_dict(replace(c, composition=RadialWeave()).to_dict())


def test_creature_assembly_checks_real_parts_and_root_hardware():
    from parametric_deco.assembly import assemble
    from parametric_deco.creature_assembly import verify_creature

    result = assemble(creature_config())
    assert result.report.digital_valid, result.report.to_dict()
    assert verify_creature(result.assembly).digital_valid
    assert len(result.assembly.mounting_grid) == 10
    assert len(result.assembly.composition["modules"]) == 5
    assert result.assembly.composition["family"] == "creature-mask-v1"
    assert len(result.assembly.composition["removal_order"]) == 5
    assert result.assembly.composition["eye_aperture_area_mm2"] > 5000
    assert {d.thickness_mm for d in result.assembly.definitions} == {6}


def test_creature_inventory_reuses_complete_modules_without_new_cuts(monkeypatch):
    import pytest
    from dataclasses import replace
    from parametric_deco.assembly import assemble
    from parametric_deco.model import Inventory
    import parametric_deco.creature_assembly as family

    first = assemble(creature_config())
    inventory = Inventory.from_dict(first.inventory.to_dict())

    def no_generation(*args, **kwargs):
        raise AssertionError("must not regenerate stock")

    monkeypatch.setattr(family, "generate_creature", no_generation)
    second = assemble(creature_config(posture="raised_crown"), inventory)
    assert second.report.digital_valid, second.report.to_dict()
    assert {(i.instance_id, i.definition_id, i.revision) for i in first.assembly.instances} == {
        (i.instance_id, i.definition_id, i.revision) for i in second.assembly.instances
    }
    assert {d.fingerprint for d in first.assembly.definitions} == {
        d.fingerprint for d in second.assembly.definitions
    }
    assert first.assembly.instances != second.assembly.instances
    with pytest.raises(ValueError, match="new cuts|manufactured"):
        assemble(creature_config(curl=1.1), inventory)
    with pytest.raises(ValueError, match="missing|inventory"):
        assemble(creature_config(), replace(inventory, instances=inventory.instances[:-1]))
    inventory.layout["templates"][1]["transform"][0][3] += 1
    with pytest.raises(ValueError, match="stale"):
        assemble(creature_config(), inventory)


def test_creature_measured_stock_and_real_cap_capture():
    from dataclasses import replace
    from parametric_deco.assembly import assemble
    from parametric_deco.creature_assembly import verify_creature

    c = creature_config(scale=0.9, curl=1.2)
    result = assemble(
        replace(c, material=replace(c.material, measured_mm=5.8, measurement_status="measured"))
    )
    assert result.report.digital_valid, result.report.to_dict()
    assert {d.thickness_mm for d in result.assembly.definitions} == {5.8}
    missing = replace(
        result.assembly,
        instances=tuple(i for i in result.assembly.instances if i.instance_id != "head-armour-5"),
    )
    assert not verify_creature(missing).digital_valid


def test_projection_visibility_uses_real_holes_and_stable_surface_ids():
    from parametric_deco.model import Assembly, PartDefinition, PartInstance
    from parametric_deco.visuals.visibility import projection_visibility
    from shapely.geometry import box

    rear = PartDefinition.from_polygon("rear", box(-10, -10, 10, 10), 6)
    front = PartDefinition.from_polygon("front", box(-20, -20, 20, 20), 6)
    a = Assembly(
        (rear, front),
        (
            PartInstance("rear", rear.definition_id, rear.revision, role="armour"),
            PartInstance(
                "front",
                front.definition_id,
                front.revision,
                ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 20), (0, 0, 0, 1)),
                role="cap",
            ),
        ),
    )
    visibility = projection_visibility(a)
    by_id = {v["surface_id"]: v for v in visibility["surfaces"]}
    assert by_id["front--front"]["visible_fraction"] == 1
    assert by_id["rear--front"]["visible_fraction"] == 0
    assert visibility["recommended_surface_ids"] == ["front--front"]
    window = PartDefinition.from_polygon(
        "window", box(-20, -20, 20, 20).difference(box(-12, -12, 12, 12)), 6
    )
    opened = Assembly(
        (rear, window),
        (
            a.instances[0],
            PartInstance(
                "window",
                window.definition_id,
                window.revision,
                a.instances[1].transform,
                role="cap",
            ),
        ),
    )
    opened_report = projection_visibility(opened)
    assert (
        next(s for s in opened_report["surfaces"] if s["surface_id"] == "rear--front")[
            "visible_fraction"
        ]
        == 1
    )


def test_creature_exports_use_family_instructions_and_visibility(tmp_path):
    import json
    from parametric_deco.assembly import assemble
    from parametric_deco.export.manifest import export_build
    from parametric_deco.visuals.atlas import generate_atlas

    result = assemble(creature_config())
    export_build(result, tmp_path)
    assert "spacer" in (tmp_path / "assembly-instructions.md").read_text()
    assert "root bolts" in (tmp_path / "assembly-instructions.md").read_text()
    assert (tmp_path / "views/oblique.png").is_file()
    assert (tmp_path / "views/joint-section.png").is_file()
    v = json.loads((tmp_path / "projection-visibility.json").read_text())
    assert v["recommended_surface_ids"]
    atlas = generate_atlas(result.assembly, 256, 256, surface_ids=v["recommended_surface_ids"])
    assert set(atlas.surface_to_tile) == set(v["recommended_surface_ids"])
