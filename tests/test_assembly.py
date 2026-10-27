from dataclasses import replace

import pytest


def test_default_assembly_valid_and_envelope_includes_hardware():
    from parametric_deco.config import DesignConfig
    from parametric_deco.assembly import assemble
    from parametric_deco.validation import validate_assembly

    a = assemble(DesignConfig()).assembly
    assert validate_assembly(a).digital_valid
    assert a.hardware_bounds
    small = replace(a, envelope_mm=(1000, 1000, 140))
    assert not validate_assembly(small).digital_valid


def test_connected_parts_do_not_suppress_solid_collisions():
    from parametric_deco.config import DesignConfig
    from parametric_deco.assembly import assemble
    from parametric_deco.validation import validate_assembly

    a = assemble(DesignConfig()).assembly
    rib = next(i for i in a.instances if i.role == "rib")
    matrix = [list(r) for r in rib.transform]
    matrix[2][3] -= 15
    broken = replace(
        a, instances=tuple(replace(i, transform=matrix) if i == rib else i for i in a.instances)
    )
    report = validate_assembly(broken)
    assert any(i.code == "interference" for i in report.issues)


def test_interface_family_and_unavailable_station_rejected():
    from parametric_deco.config import DesignConfig
    from parametric_deco.assembly import assemble
    from parametric_deco.model import Inventory, PartDefinition

    a = assemble(DesignConfig()).assembly
    rib = next(d for d in a.definitions if d.kind == "rib")
    bad = PartDefinition.from_polygon(
        rib.definition_id,
        rib.polygon,
        rib.thickness_mm,
        (replace(rib.interfaces[0], family="other"),),
        kind="rib",
    )
    defs = tuple(bad if d == rib else d for d in a.definitions)
    instances = tuple(
        replace(i, revision=bad.revision) if i.definition_id == rib.definition_id else i
        for i in a.instances
    )
    with pytest.raises(ValueError, match="interface"):
        assemble(DesignConfig(), Inventory(defs, instances))
