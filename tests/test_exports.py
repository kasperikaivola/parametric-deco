import json
import xml.etree.ElementTree as ET

import numpy as np
import pytest
import trimesh
from shapely.geometry import Point, box


def test_svg_scale_closed_holes_and_distinct_layers(tmp_path):
    from parametric_deco.model import PartDefinition
    from parametric_deco.export.svg import write_part_svg

    d = PartDefinition.from_polygon(
        "plate", box(0, 0, 100, 40).difference(Point(50, 20).buffer(3.25)), 6
    )
    p = tmp_path / "plate.svg"
    write_part_svg(d, p)
    root = ET.parse(p).getroot()
    assert root.attrib["width"] == "100mm"
    assert root.attrib["height"] == "40mm"
    assert root.attrib["viewBox"] == "0 -40 100 40"
    groups = {g.attrib["id"]: g for g in root.findall("{*}g")}
    paths = groups["cut"].findall("{*}path")
    assert len(paths) == 2
    assert all(p.attrib["d"].endswith("Z") for p in paths)
    assert len({p.attrib["d"] for p in paths}) == 2
    assert groups["engrave"].find("{*}text") is not None


def test_glb_boundary_converts_only_translation_and_vertices(tmp_path):
    from parametric_deco.model import Assembly, PartDefinition, PartInstance
    from parametric_deco.export.scene import write_scene

    part = PartDefinition.from_polygon("plate", box(0, 0, 100, 40), 6)
    t = ((1, 0, 0, 200), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))
    a = Assembly((part,), (PartInstance("identified", part.definition_id, part.revision, t),))
    write_scene(a, tmp_path)
    loaded = trimesh.load(tmp_path / "assembly.glb", force="scene")
    assert "identified" in loaded.graph.nodes_geometry
    assert loaded.bounds[:, 0] == pytest.approx([0.2, 0.3])
    assert np.diff(loaded.bounds, axis=0)[0] == pytest.approx([0.1, 0.04, 0.006])


def test_bed_nesting_rejects_oversize_and_preserves_quantities():
    from parametric_deco.model import PartDefinition
    from parametric_deco.export.svg import place_sheets
    from parametric_deco.config import CuttingBed

    d = PartDefinition.from_polygon("plate", box(0, 0, 100, 40), 6)
    sheets = place_sheets([(d, 3)], CuttingBed(210, 100, 5))
    assert sum(len(s) for s in sheets) == 3
    with pytest.raises(ValueError, match="oversize"):
        place_sheets([(d, 1)], CuttingBed(90, 100, 5))


def test_export_manifest_inventory_and_overwrite_guard(tmp_path):
    from parametric_deco.config import DesignConfig
    from parametric_deco.assembly import assemble
    from parametric_deco.export.manifest import export_build
    from parametric_deco.model import Inventory

    build = assemble(DesignConfig())
    out = tmp_path / "build"
    export_build(build, out)
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["kerf_compensation"] == "laser_software_only"
    assert manifest["nested_layout_valid"] is False
    assert manifest["validation"]["physical_validation"] == "not_run"
    inv = Inventory.load(out / "inventory.json")
    assert len(inv.instances) == len(build.assembly.instances)
    assert (out / "preview/index.html").exists()
    with pytest.raises(FileExistsError):
        export_build(build, out)
    (out / "my-notes.txt").write_text("keep")
    export_build(build, out, force=True)
    assert (out / "my-notes.txt").read_text() == "keep"


def test_render_views_produces_nonempty_identified_images(tmp_path):
    from PIL import Image
    from parametric_deco.model import Assembly, PartDefinition, PartInstance
    from parametric_deco.export.views import render_views

    part = PartDefinition.from_polygon("plate", box(0, 0, 100, 40), 6)
    a = Assembly((part,), (PartInstance("plate-1", part.definition_id, part.revision),))
    render_views(a, tmp_path)
    for name in ("front", "side", "exploded", "joint-section"):
        im = np.array(Image.open(tmp_path / f"{name}.png"))
        assert im.shape == (900, 1100, 3)
        assert len(np.unique(im.reshape(-1, 3), axis=0)) > 4


def test_exploded_projection_depth_faces_toward_positive_z():
    from parametric_deco.export.views import project_vertices

    # Camera is above the backing. A point 100 mm outward is 35 mm closer.
    point = project_vertices(np.array([[0.0, 0.0, 100.0]]), "exploded")[0]
    assert point == pytest.approx([0, 94, 35])


def test_joint_section_supports_arbitrary_module_id(tmp_path):
    from parametric_deco.model import Assembly, PartDefinition, PartInstance
    from parametric_deco.export.views import render_views

    part = PartDefinition.from_polygon("plate", box(0, 0, 100, 40), 6)
    instance = PartInstance(
        "arm-rib", part.definition_id, part.revision, module_id="arm", role="rib"
    )
    render_views(Assembly((part,), (instance,)), tmp_path)
    assert (tmp_path / "joint-section.png").stat().st_size > 1000


def _small_export_build(width, bed):
    from parametric_deco.config import DesignConfig
    from parametric_deco.model import Assembly, BuildResult, PartDefinition, PartInstance

    part = PartDefinition.from_polygon("spine", box(0, 0, width, 40), 6)
    instance = PartInstance(
        "arm-spine", part.definition_id, part.revision, module_id="arm", role="spine"
    )
    config = DesignConfig(cutting_bed=bed)
    return BuildResult(
        Assembly((part,), (instance,)), (part,), provenance={"config": config.to_dict()}
    )


def test_force_rebuild_removes_obsolete_owned_cuts_and_sheets_only(tmp_path):
    from parametric_deco.config import CuttingBed
    from parametric_deco.export.manifest import export_build

    first = _small_export_build(100, CuttingBed(300, 100))
    out = tmp_path / "build"
    export_build(first, out)
    old_cut = next(p for p in (out / "cuts").glob("spine-*.svg"))
    old_sheet = out / "sheets/sheet-1.svg"
    assert old_cut.exists() and old_sheet.exists()
    (out / "notes.txt").write_text("keep my notes")
    second = _small_export_build(101, None)
    export_build(second, out, force=True)
    assert not old_cut.exists()
    assert not old_sheet.exists()
    assert len(list((out / "cuts").glob("spine-*.svg"))) == 1
    assert (out / "notes.txt").read_text() == "keep my notes"


def test_force_rebuild_rejects_unsafe_prior_manifest_paths(tmp_path):
    from hashlib import sha256
    from parametric_deco.export.manifest import export_build

    build = _small_export_build(100, None)
    out = tmp_path / "build"
    export_build(build, out)
    victim = tmp_path / "notes.txt"
    victim.write_text("outside the build")
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["../notes.txt"] = sha256(victim.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="manifest.*path"):
        export_build(build, out, force=True)
    assert victim.read_text() == "outside the build"
