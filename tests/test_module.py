import numpy as np
import pytest


def test_crosslap_final_and_insertion_states_have_no_overlap():
    from parametric_deco.config import DesignConfig
    from parametric_deco.geometry.module import generate_module
    from parametric_deco.cad import overlap_volume

    b = generate_module(DesignConfig())
    defs = {d.definition_id: d for d in b.definitions}
    ribs = [i for i in b.instances if i.role == "rib"]
    spines = [i for i in b.instances if i.role == "spine"]
    assert len(ribs) >= 3 and len(spines) == 2
    for rib in ribs:
        for dz in (0, 5, 20, 50, 100):
            t = np.array(rib.transform)
            t[2, 3] += dz
            for spine in spines:
                assert (
                    overlap_volume(
                        defs[rib.definition_id], t, defs[spine.definition_id], spine.transform
                    )
                    < 1e-6
                )


def test_real_closure_blocks_each_rib_withdrawal():
    from parametric_deco.config import DesignConfig
    from parametric_deco.geometry.module import generate_module
    from parametric_deco.cad import overlap_volume

    b = generate_module(DesignConfig())
    defs = {d.definition_id: d for d in b.definitions}
    closure = next(i for i in b.instances if i.role == "closure")
    for rib in (i for i in b.instances if i.role == "rib"):
        d = defs[rib.definition_id]
        assert (
            overlap_volume(d, rib.transform, defs[closure.definition_id], closure.transform) < 1e-6
        )
        t = np.array(rib.transform)
        t[2, 3] += 1
        assert overlap_volume(d, t, defs[closure.definition_id], closure.transform) > 20
        assert d.thickness_mm == pytest.approx(6)


def test_measured_stock_thickness_drives_geometry_and_finished_fit():
    from dataclasses import replace
    from parametric_deco.config import DesignConfig, validate_config
    from parametric_deco.geometry.module import generate_module
    from parametric_deco.assembly import assemble

    c = DesignConfig()
    c = replace(c, material=replace(c.material, measured_mm=5.7, measurement_status="measured"))
    assert validate_config(c).digital_valid
    module = generate_module(c)
    assert all(d.thickness_mm == pytest.approx(5.7) for d in module.definitions)
    spine = next(d for d in module.definitions if d.kind == "spine")
    assert spine.interfaces[0].slot_width_mm == pytest.approx(5.9)
    build = assemble(c)
    assert all(d.thickness_mm == pytest.approx(5.7) for d in build.assembly.definitions)
    assert build.report.digital_valid, build.report.to_dict()
