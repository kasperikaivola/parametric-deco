from shapely.geometry import Point


def test_creature_profiles_have_ambiguous_cavity_cluster_and_open_sweeps():
    from parametric_deco.geometry.creature_profiles import profiles, eye_voids
    from shapely.ops import unary_union

    shapes = profiles()
    cavities = eye_voids()
    assert len(cavities) == 6
    assert max(p.area for p in cavities) / min(p.area for p in cavities) > 1.4
    assert all(
        p.is_valid and p.geom_type == "Polygon" for layers in shapes.values() for p in layers
    )
    assert len(shapes["head"][0].interiors) >= 9
    # An actual central opening replaces the old solid rostrum.
    assert all(not p.covers(Point(0, 0)) for p in shapes["head"])
    assert all(
        p.intersection(unary_union(cavities)).area < 1e-6
        for layers in shapes.values()
        for p in layers
    )
    # Longitudinal internal channels survive in the large appendages.
    assert all(len(p.interiors) >= 2 for p in shapes["crown-left"])
    assert shapes["crown-left"][0].bounds[0] < -400
    assert shapes["jaw-left"][0].bounds[1] < -300


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
    assert result.assembly.composition["family"] == "creature-organism-v3"
    assert len(result.assembly.composition["removal_order"]) == 5
    assert result.assembly.composition["eye_aperture_area_mm2"] > 3000
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
    assert (tmp_path / "views/three-quarter.png").is_file()
    assert (tmp_path / "views/rib-joint.png").is_file()
    assert (tmp_path / "views/joint-section.png").is_file()
    v = json.loads((tmp_path / "projection-visibility.json").read_text())
    assert v["recommended_surface_ids"]
    atlas = generate_atlas(result.assembly, 256, 256, surface_ids=v["recommended_surface_ids"])
    assert set(atlas.surface_to_tile) == set(v["recommended_surface_ids"])


def test_organism_transverse_ribs_have_real_slots_keys_and_bearing():
    import numpy as np
    from dataclasses import replace
    from parametric_deco.assembly import assemble
    from parametric_deco.creature_assembly import verify_creature
    from parametric_deco.cad import overlap_volume

    result = assemble(creature_config())
    assert result.report.digital_valid, result.report.to_dict()
    a = result.assembly
    blades = [i for i in a.instances if i.role == "blade"]
    assert len(blades) == 24
    assert a.composition["family"] == "creature-organism-v3"
    assert len(a.composition["clear_aperture_probe_areas_mm2"]) == 6
    by_id = {i.instance_id: i for i in a.instances}
    for m in a.composition["modules"]:
        cap = by_id[m["cap_id"]]
        for joint in m.get("blade_joints", []):
            blade, key = by_id[joint["blade_id"]], by_id[joint["retainer_id"]]
            assert (
                overlap_volume(
                    a.definition_for(blade), blade.transform, a.definition_for(key), key.transform
                )
                < 1e-5
            )
            # Real key stops upward removal by bearing under cap.
            lift = np.array(key.transform)
            lift[2, 3] += 13
            assert (
                overlap_volume(a.definition_for(key), lift, a.definition_for(cap), cap.transform)
                > 1
            )
            # Blade shoulders stop inward motion through the cap slot.
            inward = np.array(blade.transform)
            inward[2, 3] -= 1
            assert (
                overlap_volume(
                    a.definition_for(blade), inward, a.definition_for(cap), cap.transform
                )
                > 1
            )
    missing = replace(
        a, instances=tuple(i for i in a.instances if i.instance_id != blades[0].instance_id)
    )
    assert not verify_creature(missing).digital_valid


def test_organism_rejects_previous_mask_inventory():
    from dataclasses import replace
    import pytest
    from parametric_deco.assembly import assemble

    result = assemble(creature_config())
    layout = dict(result.inventory.layout, family="creature-mask-v1")
    with pytest.raises(ValueError, match="family|new cuts"):
        assemble(creature_config(), replace(result.inventory, layout=layout))


def test_organism_rejects_retainer_that_misses_its_tab():
    from dataclasses import replace
    import numpy as np
    from parametric_deco.assembly import assemble
    from parametric_deco.creature_assembly import verify_creature

    a = assemble(creature_config()).assembly
    key = next(i for i in a.instances if i.role == "retainer")
    pose = np.array(key.transform)
    pose[:3, 3] += pose[:3, 0] * 20
    altered = replace(
        a,
        instances=tuple(
            replace(i, transform=pose) if i.instance_id == key.instance_id else i
            for i in a.instances
        ),
    )
    report = verify_creature(altered)
    assert any(i.code == "blade_key_engagement" for i in report.issues)


def test_organism_retainer_has_head_and_clip_hole():
    from parametric_deco.geometry.creature import generate_creature
    from shapely.geometry import box
    from shapely.geometry import Polygon

    bundle, layout = generate_creature(creature_config())
    key = next(d for d in bundle.definitions if d.definition_id == "organism-blade-retainer")
    assert len(key.holes) == 1
    assert Polygon(key.holes[0]).area > 4
    # Head is wider than the tab window; shank is narrower.
    assert key.polygon.intersection(box(-30, -16, 30, -8)).bounds[2] > 8
    assert key.polygon.intersection(box(-30, 0, 30, 5)).bounds[2] <= 5
    assert all(
        j["clip_hole_diameter_mm"] == 2.5 for m in layout["modules"] for j in m["blade_joints"]
    )


def test_organism_parameter_corners_preserve_connections_and_clear_channels():
    from parametric_deco.assembly import assemble

    for scale, curl, posture in (
        (0.9, 0.8, "raised_crown"),
        (1, 0.8, "rest"),
        (1, 1.2, "raised_crown"),
    ):
        result = assemble(creature_config(scale=scale, curl=curl, posture=posture))
        assert result.report.digital_valid, (scale, curl, posture, result.report.to_dict())
        assert sum(len(m["blade_joints"]) for m in result.assembly.composition["modules"]) == 24
