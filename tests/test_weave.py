from dataclasses import replace

import numpy as np
import pytest
from shapely.geometry import Point


def config():
    from parametric_deco.config import DesignConfig, RadialWeave

    return DesignConfig(composition=RadialWeave())


def test_weave_blueprint_has_aperture_real_crossings_and_connected_parts():
    from parametric_deco.geometry.weave import generate_weave
    from parametric_deco.geometry.backplate import generate_backplate, mounting_holes

    c = config()
    bundle, layout = generate_weave(c)
    assert len(layout["modules"]) == 12
    assert len([i for i in bundle.instances if i.role == "rib"]) == 108
    assert len(layout["crossings"]) == 6
    assert [x["over_module"] for x in layout["crossings"]] == ["a0", "b1", "a2", "b3", "a4", "b5"]
    assert all(d.polygon.is_valid and d.polygon.geom_type == "Polygon" for d in bundle.definitions)
    for d in bundle.definitions:
        if d.kind in ("spine", "closure"):
            assert d.polygon.distance(Point(0, 0)) >= 180 - 1e-5
    backing = generate_backplate(c).definitions[0]
    assert not backing.polygon.covers(Point(0, 0))
    assert all(np.hypot(h.x_mm, h.y_mm) >= 198.25 - 1e-6 for h in mounting_holes(c))


def test_weave_configuration_rejects_impossible_opening_and_nonfinite_values():
    from parametric_deco.config import validate_config

    c = config()
    for field, value in (
        ("radius_mm", float("nan")),
        ("opening_radius_mm", 300),
        ("lobes", 1),
        ("ribs_per_module", 10),
    ):
        report = validate_config(replace(c, composition=replace(c.composition, **{field: value})))
        assert not report.digital_valid, field


def test_weave_candidate_retains_ribs_and_reports_ordered_removal():
    from parametric_deco.assembly import assemble
    from parametric_deco.weave_assembly import validate_weave, verify_radial_joints

    result = assemble(config())
    assert result.report.digital_valid, result.report.to_dict()
    assert validate_weave(result.assembly).digital_valid
    assert verify_radial_joints(result.assembly).digital_valid
    evidence = result.assembly.composition
    assert evidence["minimum_crossing_clearance_mm"] >= 10
    assert len(evidence["removal_order"]) == 12
    assert evidence["opening_clearance_mm"] >= -1e-6


def test_weave_inventory_reconfiguration_never_regenerates_parts():
    from parametric_deco.assembly import assemble
    from parametric_deco.model import Inventory

    c = config()
    first = assemble(c)
    inventory = Inventory.from_dict(first.inventory.to_dict())
    changed = replace(
        c,
        composition=replace(
            c.composition, rotation_deg=180, rib_permutation=(0, 1, 3, 4, 5, 6, 2, 7, 8)
        ),
    )
    second = assemble(changed, inventory)
    assert second.report.digital_valid, second.report.to_dict()
    assert {d.fingerprint for d in first.assembly.definitions} == {
        d.fingerprint for d in second.assembly.definitions
    }
    assert {i.instance_id for i in first.assembly.instances} == {
        i.instance_id for i in second.assembly.instances
    }
    assert first.assembly.to_dict() != second.assembly.to_dict()
    assert second.assembly.composition["crossings"][0]["theta_deg"] == 180
    with pytest.raises(ValueError, match="manufactured|inventory"):
        assemble(replace(c, composition=replace(c.composition, radius_mm=310)), inventory)
    with pytest.raises(ValueError, match="missing|inventory"):
        assemble(changed, replace(inventory, instances=inventory.instances[:-1]))


def test_weave_export_includes_artwork_evidence_and_radial_instructions(tmp_path):
    import json
    from parametric_deco.assembly import assemble
    from parametric_deco.export.manifest import export_build

    build = assemble(config())
    export_build(build, tmp_path)
    assert (tmp_path / "views/oblique.png").is_file()
    instructions = (tmp_path / "assembly-instructions.md").read_text()
    assert "radially inward" in instructions
    assert "high modules" in instructions
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["composition"]["family"] == "radial-weave-v1"
    assert len(manifest["composition"]["crossings"]) == 6


def test_saved_weave_rejects_changed_stock_and_stale_layout():
    from parametric_deco.assembly import assemble
    from parametric_deco.model import Inventory
    import json

    # Use the immutable blueprint directly: rejection must precede geometry validation.
    from parametric_deco.geometry.weave import generate_weave
    from parametric_deco.geometry.backplate import generate_backplate
    from parametric_deco.model import PartInstance, digest
    from dataclasses import asdict

    c = config()
    bundle, layout = generate_weave(c)
    backing = generate_backplate(c).definitions[0]
    root = PartInstance(
        "backplate",
        backing.definition_id,
        backing.revision,
        ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 10), (0, 0, 0, 1)),
        role="backplate",
    )
    layout = json.loads(json.dumps(layout))
    layout["templates"] = [asdict(i) for i in (root, *bundle.instances)]
    layout["fingerprint"] = digest(layout)
    inv = Inventory((backing, *bundle.definitions), (root, *bundle.instances), layout)
    with pytest.raises(ValueError, match="manufactured|inventory"):
        assemble(replace(c, material=replace(c.material, measured_mm=5.8)), inv)
    layout["modules"][0]["station_transforms"][0][0][3] += 1
    with pytest.raises(ValueError, match="stale"):
        assemble(c, inv)
