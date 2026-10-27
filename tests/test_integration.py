from pathlib import Path

from parametric_deco.config import load_config
from parametric_deco.assembly import assemble
from parametric_deco.model import Inventory


def test_intertwined_and_reconfigured_reuse_same_inventory():
    first = assemble(load_config(Path("examples/intertwined.json")))
    assert first.report.digital_valid, first.report.to_dict()
    assert len({i.module_id for i in first.assembly.instances if i.role == "rib"}) == 4
    assert not any(i.code == "extraction_dependency" for i in first.report.issues)
    second = assemble(
        load_config(Path("examples/reconfigured.json")),
        Inventory(first.assembly.definitions, first.assembly.instances),
    )
    assert second.report.digital_valid, second.report.to_dict()
    assert {i.instance_id for i in first.assembly.instances} == {
        i.instance_id for i in second.assembly.instances
    }
    assert {d.fingerprint for d in first.assembly.definitions} == {
        d.fingerprint for d in second.assembly.definitions
    }
    assert first.assembly.to_dict() != second.assembly.to_dict()
    assert len(first.assembly.mounting_grid) == 8
    assert len(first.assembly.extraction_paths) == 4
