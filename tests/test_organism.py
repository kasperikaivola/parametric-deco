from dataclasses import replace
import pytest
from parametric_deco.config import config_from_dict


def test_new_family_and_size_validation():
    c = config_from_dict({"style": "laminar", "parameters": {}})
    assert c.parameters.complexity == 0
    for dimensions in [(800, 800, 120), (1000, 1000, 200), (1400, 1400, 240)]:
        config_from_dict(
            {
                "style": "laminar", "parameters": {},
                "envelope": dict(zip(("width_mm", "height_mm", "depth_mm"), dimensions)),
            }
        )
    for bad in [{"complexity": True}, {"focal_count": 2}, {"curvature": float("nan")}]:
        with pytest.raises(ValueError):
            config_from_dict({"style": "laminar", "parameters": bad})
    with pytest.raises(ValueError, match="800"):
        config_from_dict({"style": "laminar", "parameters": {}, "envelope": {"width_mm": 300}})


def test_complexity_preserves_primary_anatomy():
    from parametric_deco.geometry.organism import anatomy

    c = config_from_dict({"style": "laminar", "parameters": {}})
    low = anatomy(c)
    high = anatomy(replace(c, parameters=replace(c.parameters, complexity=2)))
    assert len(high) > len(low)
    for a, b in zip(low, high):
        assert (a.name, a.z) == (b.name, b.z)
        assert a.major_outline.equals(b.major_outline)
        assert (a.path == b.path).all()


def test_manufactured_module_depth_and_inventory():
    from parametric_deco.assembly import assemble

    c = config_from_dict({"style": "laminar", "parameters": {}})
    b = assemble(c)
    assert b.report.digital_valid, b.report.issues
    assert len(b.inventory.instances) == 7
    assert b.assembly.composition["construction"]["spacers"] == 0
    assert b.assembly.composition["construction"]["retainers"] == 0
    assert all(p.thickness_mm == 6 for p in b.fabrication_parts)
    assert assemble(c, b.inventory).inventory.to_dict() == b.inventory.to_dict()
    with pytest.raises(ValueError, match="new cuts"):
        assemble(replace(c, parameters=replace(c.parameters, curvature=1.1)), b.inventory)


def test_margins_and_necks_reject_real_thin_material():
    from shapely.geometry import box
    from parametric_deco.organism_assembly import guard_slots, neck_check

    with pytest.raises(ValueError, match="neighboring"):
        guard_slots(box(-100, -100, 100, 100), [box(0, 0, 5, 20), box(10, 0, 15, 20)])
    with pytest.raises(ValueError, match="neck"):
        neck_check(box(-30, -20, -10, 20).union(box(10, -20, 30, 20)).union(box(-10, -2, 10, 2)))


def test_legacy_dense_slots_rejected_before_keys():
    from parametric_deco.config import DesignConfig, CreatureMask
    from parametric_deco.geometry.creature import generate_creature

    c = DesignConfig(
        style="layered-creature", parameters=CreatureMask(
            limb_count=6,
            ribs_per_limb=7,
            limb_reach=0.85,
            limb_width=0.9,
            scale=0.9,
            asymmetry=0.15,
            shell_layers=4,
            limb_layers=3,
            rib_height_mm=45,
        )
    )
    with pytest.raises(ValueError, match="neighboring rib slots"):
        generate_creature(c)


def test_segmentation_changes_material_without_replacing_focal_layout():
    from parametric_deco.geometry.organism import anatomy

    c = config_from_dict({"style": "laminar", "parameters": {"segmentation": 2}})
    dense = replace(c, parameters=replace(c.parameters, segmentation=4))
    low, high = anatomy(c), anatomy(dense)
    assert [lobe.z for lobe in low] == [lobe.z for lobe in high]
    assert low[0].shape.area != high[0].shape.area


def test_secondary_relief_separates_overlapping_plates():
    from itertools import combinations
    from parametric_deco.geometry.organism import anatomy

    lobes = anatomy(config_from_dict({"style": "laminar", "parameters": {"complexity": 2}}))
    for a, b in combinations(lobes, 2):
        if abs(a.z - b.z) < 6:
            assert a.shape.intersection(b.shape).area < 1e-6, (a.name, b.name)


@pytest.mark.parametrize("angle", [0, 0.37, 1.1])
def test_trestle_prism_overlap_matches_solid_kernel(angle):
    import math
    import numpy as np
    from shapely.geometry import box
    from parametric_deco.model import PartDefinition
    from parametric_deco.cad import overlap_volume, _kernel_overlap, _trestle_overlap

    web = PartDefinition.from_polygon(
        "flow-web-check", box(-15, 0, 15, 60).union(box(-7, -6, 7, 66)), 6, kind="register"
    )
    plate = PartDefinition.from_polygon(
        "plate-check", box(-40, -40, 40, 40).difference(box(8, -7.1, 14.2, 7.1)), 6
    )
    co, si = math.cos(angle), math.sin(angle)
    rotation = np.array(((co, -si, 0, 0), (si, co, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)))
    pw = rotation @ np.array(((0, 0, 1, 8.1), (1, 0, 0, 0), (0, 1, 0, 10), (0, 0, 0, 1)))
    for z in (7, 10, 30, 68, 70):
        pp = rotation @ np.array(((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, z), (0, 0, 0, 1)))
        optimized = _trestle_overlap(web, pw, plate, pp)
        assert optimized is not None
        assert optimized == pytest.approx(
            _kernel_overlap(web, tuple(map(tuple, pw)), plate, tuple(map(tuple, pp))), abs=1e-6
        )
        assert overlap_volume(web, pw, plate, pp) == pytest.approx(optimized, abs=1e-6)


def test_loaded_assembly_bearing_and_support_checks():
    from parametric_deco.assembly import assemble
    from parametric_deco.organism_assembly import verify_organism
    from parametric_deco.model import PartDefinition
    from shapely.geometry import Point

    b = assemble(config_from_dict({"style": "laminar", "parameters": {}}))
    assert verify_organism(b.assembly).digital_valid
    a = b.assembly
    instance = next(i for i in a.instances if i.role == "armour")
    original = a.definition_for(instance)
    root = next(s["xy"] for s in a.composition["end_supports"]["stations"]
                if instance.instance_id in s["plate_ids"])
    damaged = PartDefinition.from_polygon(
        original.definition_id,
        original.polygon.difference(Point(root).buffer(12)),
        6,
        original.interfaces,
        kind="armour",
    )
    altered = replace(
        a,
        definitions=tuple(damaged if d == original else d for d in a.definitions),
        instances=tuple(
            replace(i, revision=damaged.revision) if i == instance else i for i in a.instances
        ),
    )
    assert not verify_organism(altered).digital_valid


@pytest.mark.parametrize(
    "field,value",
    [
        ("curvature", 1.15),
        ("taper", 1.2),
        ("swelling", 1.1),
        ("angularity", 0.3),
        ("asymmetry", 0.18),
        ("spread", 1.1),
        ("phase_deg", 31),
        ("symmetry", "none"),
        ("channels", 0),
        ("segmentation", 4),
        ("branching", 3),
        ("anatomy_phase_deg", 55),
    ],
)
def test_each_shape_control_changes_actual_contours(field, value):
    from parametric_deco.geometry.organism import anatomy

    c = config_from_dict({"style": "laminar", "parameters": {}})
    base = anatomy(c)
    changed = anatomy(replace(c, parameters=replace(c.parameters, **{field: value})))
    assert any(not a.shape.equals(b.shape) for a, b in zip(base, changed))


def test_size_changes_geometry_but_not_joint_dimensions():
    from pathlib import Path
    from parametric_deco.config import load_config
    from parametric_deco.organism_assembly import manufacture

    results = [
        manufacture(load_config(Path("examples/organism-" + size + ".json")))
        for size in ("small", "low", "large")
    ]
    for definitions, instances, layout in results:
        assert {p.thickness_mm for p in definitions} == {6}
        from shapely.geometry import Polygon

        for module in layout["modules"]:
            for slot in module["slot_polygons"]:
                assert Polygon(slot).area == pytest.approx(6.2 * 14.2)
        assert len(instances) == 7
        board = next(part for part in definitions if part.kind == "backplate")
        assert all(Polygon(hole).bounds[2] - Polygon(hole).bounds[0] == pytest.approx(6.5) for hole in board.holes)


def test_cut_ligaments_measure_actual_holes():
    from shapely.geometry import box
    from parametric_deco.organism_assembly import cut_ligaments

    with pytest.raises(ValueError, match="ligament"):
        cut_ligaments(box(-20, -20, 20, 20).difference(box(10, -10, 16, 10)), 7)


@pytest.mark.parametrize("name", ["medium", "high", "bilateral"])
def test_richer_compositions_have_valid_actual_assembly(name):
    from pathlib import Path
    from parametric_deco.config import load_config
    from parametric_deco.assembly import assemble

    result = assemble(load_config(Path("examples/organism-" + name + ".json")))
    assert result.report.digital_valid, result.report.to_dict()


def test_determinism_and_all_new_cut_requests():
    from parametric_deco.assembly import assemble
    from parametric_deco.organism_assembly import manufacture
    from parametric_deco.model import Inventory

    c = config_from_dict({"style": "laminar", "parameters": {}})
    first = manufacture(c)
    second = manufacture(c)
    assert [p.fingerprint for p in first[0]] == [p.fingerprint for p in second[0]]
    assert first[2] == second[2]
    inv = Inventory(tuple(first[0]), tuple(first[1]), first[2])
    changes = {
        "arrangement": "bilateral",
        "branching": 3,
        "anatomy_phase_deg": 55,
        "focal_count": 9,
        "phase_deg": 31,
        "spread": 1.1,
        "symmetry": "none",
        "complexity": 1,
        "secondary_lobes": 1,
        "channels": 2,
        "segmentation": 3,
        "curvature": 1.1,
        "taper": 1.1,
        "swelling": 1.1,
        "angularity": 0.2,
        "asymmetry": 0.15,
    }
    for field, value in changes.items():
        values = {field: value}
        if field == "arrangement":
            values["symmetry"] = "bilateral"
        changed = replace(c, parameters=replace(c.parameters, **values))
        with pytest.raises(ValueError, match="new cuts"):
            assemble(changed, inv)
    with pytest.raises(ValueError, match="new cuts"):
        assemble(replace(c, envelope=replace(c.envelope, width_mm=1200)), inv)
    with pytest.raises(ValueError, match="new cuts"):
        assemble(replace(c, material=replace(c.material, measured_mm=5.8)), inv)


def test_previous_anatomical_creature_request_requires_new_polygon_board_cuts():
    from pathlib import Path
    from parametric_deco.config import load_config
    from parametric_deco.geometry.creature import request_signature

    c = load_config(Path("examples/creature-alien-two.json"))
    assert (
        request_signature(c) != "2b11c951b049aef3a6d13459b0bf0250860fbbfeca05361c1f9a93e80c77ebf1"
    )


def test_primary_anatomy_varies_beyond_rotated_copies():
    import numpy as np
    from parametric_deco.geometry.organism import anatomy

    c = config_from_dict({"style": "laminar", "parameters": {"asymmetry": 0}})
    lobes = anatomy(c)
    ratios = [
        np.linalg.norm(lobe.path[-1] - lobe.path[0])
        / np.linalg.norm(np.diff(lobe.path, axis=0), axis=1).sum()
        for lobe in lobes
    ]
    assert np.ptp(ratios) > 0.02
    assert len({lobe.z for lobe in lobes}) == c.parameters.focal_count // 3


@pytest.mark.parametrize("before,after", [(0, 1), (1, 2)])
def test_complexity_retains_existing_internal_material(before, after):
    from parametric_deco.geometry.organism import anatomy

    c = config_from_dict({"style": "laminar", "parameters": {"complexity": before, "channels": 0, "secondary_lobes": 0}})
    previous = anatomy(c)
    enriched = anatomy(replace(c, parameters=replace(c.parameters, complexity=after)))
    assert len(previous) == len(enriched)
    for a, b in zip(previous, enriched):
        assert a.shape.difference(b.shape).area < 1e-6, (a.name, a.shape.difference(b.shape).area)


@pytest.mark.parametrize("count", range(5))
def test_explicit_segmentation_is_prefix_preserving(count):
    from parametric_deco.geometry.organism import anatomy

    c = config_from_dict({"style": "laminar", "parameters": {"segmentation": count, "channels": 0, "secondary_lobes": 0}})
    previous = anatomy(c)
    enriched = anatomy(replace(c, parameters=replace(c.parameters, segmentation=count + 1)))
    assert all(a.shape.difference(b.shape).area < 1e-6 for a, b in zip(previous, enriched))


def test_primary_medial_paths_do_not_return_as_scrolls():
    import numpy as np
    from parametric_deco.geometry.organism import anatomy

    for arrangement in ("whorl", "bilateral"):
        c = config_from_dict({"style": "laminar", "parameters": {"arrangement": arrangement, "symmetry": "bilateral" if arrangement == "bilateral" else "rotational"}})
        for lobe in anatomy(c):
            arc = np.linalg.norm(np.diff(lobe.path, axis=0), axis=1).sum()
            chord = np.linalg.norm(lobe.path[-1] - lobe.path[0])
            assert chord / arc > 0.65, (arrangement, lobe.name, chord / arc)


def test_thin_sweeps_are_continuous_between_samples():
    import numpy as np
    from parametric_deco.geometry.organism import ribbon

    shape = ribbon(
        np.array(((0.0, 0.0), (0.1, 0.02), (0.2, 0.01))), np.array((0.004, 0.005, 0.004))
    )
    assert shape.geom_type == "Polygon"
    assert shape.is_valid


def test_rejects_previous_scroll_inventory_family():
    from parametric_deco.organism_assembly import manufacture
    from parametric_deco.assembly import assemble
    from parametric_deco.model import Inventory, digest

    c = config_from_dict({"style": "laminar", "parameters": {}})
    definitions, instances, layout = manufacture(c)
    layout["family"] = "flow-organism-v1"
    layout.pop("fingerprint")
    layout["fingerprint"] = digest(layout)
    with pytest.raises(ValueError, match="new cuts"):
        assemble(c, Inventory(tuple(definitions), tuple(instances), layout))
