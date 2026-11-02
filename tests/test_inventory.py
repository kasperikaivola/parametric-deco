from parametric_deco.config import RibStudy
from dataclasses import replace

import pytest


def test_reconfigure_uses_saved_geometry_not_current_recipe():
    from parametric_deco.config import DesignConfig
    from parametric_deco.assembly import assemble
    from parametric_deco.model import Inventory

    c = DesignConfig(style="rib-study", parameters=RibStudy())
    first = assemble(c)
    inventory = first.inventory
    changed = replace(
        c,
        parameters=replace(c.parameters, recipe=replace(c.module, length_mm=400),
            placements=(replace(c.placements[0], rib_order=(3, 2, 1, 0)),)),
    )
    second = assemble(changed, Inventory.from_dict(inventory.to_dict()))
    assert {d.fingerprint for d in first.assembly.definitions} == {
        d.fingerprint for d in second.assembly.definitions
    }
    a = next(i for i in first.assembly.instances if i.instance_id == "m1-rib-0")
    b = next(i for i in second.assembly.instances if i.instance_id == "m1-rib-0")
    assert a.transform[0][3] == 92
    assert b.transform[0][3] == 272


def test_inventory_shortage_and_stale_revision_rejected():
    from parametric_deco.config import DesignConfig
    from parametric_deco.assembly import assemble
    from parametric_deco.model import Inventory

    build = assemble(DesignConfig(style="rib-study", parameters=RibStudy()))
    inv = build.inventory
    with pytest.raises(ValueError, match="missing|insufficient"):
        assemble(DesignConfig(style="rib-study", parameters=RibStudy()), replace(inv, instances=inv.instances[:-1]))
    data = inv.to_dict()
    data["instances"][0]["revision"] = "unknown"
    with pytest.raises(ValueError, match="revision"):
        Inventory.from_dict(data)
    data = inv.to_dict()
    data["instances"].append(data["instances"][0])
    with pytest.raises(ValueError, match="duplicate"):
        Inventory.from_dict(data)


def test_partial_reconfiguration_export_preserves_all_stock_and_can_restore(tmp_path):
    from parametric_deco.config import DesignConfig, ModulePlacement
    from parametric_deco.assembly import assemble
    from parametric_deco.model import Inventory
    from parametric_deco.export.manifest import export_build

    config = DesignConfig(style="rib-study", parameters=RibStudy())
    first = assemble(config)
    inventory = first.inventory
    # Translate by a parity-preserving grid offset, leaving its fourth rib in stock.
    partial_config = replace(
        config, parameters=replace(config.parameters,
            placements=(ModulePlacement("m1", 75, -2 * config.grid.pitch_y_mm, 0, (0, 1, 2), (0, 1, 2)),))
    )
    partial = assemble(partial_config, inventory)
    assert partial.report.digital_valid, partial.report.to_dict()
    export_build(partial, tmp_path / "partial")
    saved = Inventory.load(tmp_path / "partial/inventory.json")
    assert {i.instance_id for i in saved.instances} == {i.instance_id for i in inventory.instances}
    restored = assemble(config, saved)
    assert restored.report.digital_valid, restored.report.to_dict()
    original = {i.instance_id: i.transform for i in first.assembly.instances}
    for instance in restored.assembly.instances:
        import numpy as np

        assert np.allclose(instance.transform, original[instance.instance_id])


def test_saved_holes_require_real_washer_bearing_during_reconfiguration():
    from parametric_deco.config import DesignConfig
    from parametric_deco.assembly import assemble

    c = DesignConfig(style="rib-study", parameters=RibStudy())
    large_holes = replace(c, grid=replace(c.grid, hole_diameter_mm=20),
                          mounting=replace(c.mounting, washer_radius_mm=12))
    with pytest.raises(ValueError, match="M6.*bores"):
        assemble(large_holes)
