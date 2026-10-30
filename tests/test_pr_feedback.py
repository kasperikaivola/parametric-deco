"""Regressions for the owner's PR #1 review, not an additional review round."""

from dataclasses import replace
from pathlib import Path

import pytest
from shapely.geometry import box

from parametric_deco.assembly import assemble
from parametric_deco.config import DesignConfig, RibStudy, load_config
from parametric_deco.model import Assembly, Inventory, PartDefinition, PartInstance


def test_short_ribs_rejected_by_closure_contact_interface_and_loaded_validation():
    from parametric_deco.geometry.module import generate_module
    from parametric_deco.validation import validate_assembly

    c = DesignConfig(style="rib-study", parameters=RibStudy())
    original = assemble(c)
    short = generate_module(replace(c, parameters=replace(c.parameters, recipe=replace(c.module, rib_top_mm=81))))
    replacements = {d.definition_id: d for d in short.definitions if d.kind == "rib"}
    definitions = tuple(replacements.get(d.definition_id, d) for d in original.assembly.definitions)
    instances = tuple(
        replace(i, revision=replacements[i.definition_id].revision) if i.role == "rib" else i
        for i in original.assembly.instances
    )
    inventory = Inventory(definitions, instances)
    with pytest.raises(ValueError, match="closure"):
        assemble(c, inventory)
    report = validate_assembly(
        replace(original.assembly, definitions=definitions, instances=instances)
    )
    assert not report.digital_valid
    assert any(issue.code == "closure_retention" for issue in report.issues)


def test_inventory_ids_are_not_parsed_as_rib_names():
    c = DesignConfig(style="rib-study", parameters=RibStudy())
    first = assemble(c)
    inventory = Inventory(
        first.assembly.definitions,
        tuple(
            replace(i, instance_id=f"stock-{index}")
            for index, i in enumerate(first.assembly.instances)
        ),
    )
    result = assemble(c, inventory)
    assert result.report.digital_valid, result.report.to_dict()
    assert {i.instance_id for i in result.assembly.instances} == {
        i.instance_id for i in inventory.instances
    }


def test_explicit_assignments_transfer_ribs_across_modules_with_arbitrary_ids():
    c = load_config(Path("examples/intertwined.json"))
    first = assemble(c)
    renamed = {i.instance_id: f"stock-{n}" for n, i in enumerate(first.assembly.instances)}
    stock = Inventory(
        first.assembly.definitions,
        tuple(replace(i, instance_id=renamed[i.instance_id]) for i in first.assembly.instances),
    )
    placements = []
    for p in c.placements:
        ids = [renamed[f"{p.module_id}-rib-{n}"] for n in p.rib_order]
        if p.module_id == "m1":
            ids[0] = renamed["m2-rib-0"]
        if p.module_id == "m2":
            ids[0] = renamed["m1-rib-0"]
        placements.append(
            replace(
                p,
                module_id="new-" + p.module_id,
                spine_instance_ids=tuple(renamed[f"{p.module_id}-spine-{n}"] for n in (0, 1)),
                closure_instance_id=renamed[f"{p.module_id}-closure"],
                rib_instance_ids=tuple(ids),
            )
        )
    configured = replace(c, parameters=replace(c.parameters, placements=tuple(placements)))
    result = assemble(configured, stock)
    assert result.report.digital_valid, result.report.to_dict()
    moved = next(i for i in result.assembly.instances if i.instance_id == renamed["m2-rib-0"])
    assert moved.module_id == "new-m1"
    assert len(result.assembly.instances) == len(stock.instances)
    duplicated = replace(
        configured,
        parameters=replace(configured.parameters, placements=(
            placements[0],
            replace(placements[1], rib_instance_ids=placements[0].rib_instance_ids),
            *placements[2:],
        )),
    )
    with pytest.raises(ValueError, match="duplicate"):
        assemble(duplicated, stock)


def test_default_example_atlas_preserves_useful_broad_face_resolution():
    from parametric_deco.visuals.atlas import generate_atlas

    a = assemble(load_config(Path("examples/intertwined.json"))).assembly
    atlas = generate_atlas(a, 2048, 2048)
    tiles = atlas.manifest["tiles"]
    assert len(tiles) == 28
    assert all(t["surface_id"] == "front" for t in tiles)
    ribs = [t for t in tiles if t["definition_id"].startswith("rib-")]
    assert min(min(t["pixel_rect"][2:]) for t in ribs) >= 160
    assert all(max(t["texel_size_mm"]) <= 0.8 for t in ribs)


def test_atlas_uses_physical_size_and_explicit_surface_selection():
    from parametric_deco.visuals.atlas import generate_atlas

    big = PartDefinition.from_polygon("large", box(0, 0, 100, 40), 6)
    small = PartDefinition.from_polygon("small", box(0, 0, 25, 10), 6)
    a = Assembly(
        (big, small),
        (
            PartInstance("large", big.definition_id, big.revision),
            PartInstance("small", small.definition_id, small.revision),
        ),
    )
    result = generate_atlas(a, 512, 512)
    sizes = {
        t["instance_id"]: t["pixel_rect"][2] * t["pixel_rect"][3] for t in result.manifest["tiles"]
    }
    assert sizes["large"] / sizes["small"] == pytest.approx(16, rel=0.1)
    selected = generate_atlas(a, 512, 512, surface_ids=("large--front",))
    assert [t["tile_id"] for t in selected.manifest["tiles"]] == ["large--front"]
    assert selected.manifest["tiles"][0]["pixel_rect"][2] >= 500
    with pytest.raises(ValueError, match="surface"):
        generate_atlas(a, 512, 512, surface_ids=("unknown--front",))
