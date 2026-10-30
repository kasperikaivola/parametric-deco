"""Rebuild, validate and export all demonstrations using the existing CAD pipeline."""

from collections import Counter
import json
from pathlib import Path
import shutil

from parametric_deco.assembly import assemble
from parametric_deco.config import load_config
from parametric_deco.export.manifest import export_build
from parametric_deco.model import Assembly, Inventory
from parametric_deco.organism_assembly import cut_ligaments
from parametric_deco.visuals.atlas import generate_atlas
from parametric_deco.visuals.isf import export_isf_resources
from parametric_deco.visuals.visibility import projection_visibility

root = Path(__file__).resolve().parents[1]
evidence = {}
for name in ("low", "medium", "high", "bilateral", "small", "large"):
    key = "organism-" + name
    c = load_config(root / "examples" / (key + ".json"))
    build = assemble(c)
    if not build.report.digital_valid:
        raise RuntimeError(key + ": " + str(build.report.to_dict()))
    out = root / "build" / key
    export_build(build, out, force=True)
    a = Assembly.from_dict(json.loads((out / "assembly.json").read_text()))
    inv = Inventory.load(out / "inventory.json")
    replay = assemble(c, inv)
    assert replay.inventory.to_dict() == inv.to_dict()
    visible = projection_visibility(a)["recommended_surface_ids"]
    atlas = generate_atlas(a, 2048, 2048, surface_ids=visible)
    assert set(atlas.surface_to_tile) == set(visible)
    export_isf_resources(atlas, root / "build" / (key + "-visuals"), force=True)
    images = root / "docs/implementation/images/flow-organism" / key
    images.mkdir(parents=True, exist_ok=True)
    for view in ("front", "three-quarter", "side", "oblique", "joint-section", "exploded"):
        shutil.copy2(out / "views" / (view + ".png"), images / (view + ".png"))
    evidence[key] = {
        "requested_envelope_mm": list(a.envelope_mm),
        "bounds_mm": a.composition["actual_bounds_mm"],
        "actual_total_depth_including_hardware_mm": max(h[6] for h in a.hardware_bounds),
        "minimum_plate_cut_ligament_mm": min(
            m["minimum_cut_ligament_mm"] for m in a.composition["modules"]
        ),
        "minimum_backing_cut_ligament_mm": cut_ligaments(
            a.definition_for(next(i for i in a.instances if i.role == "backplate")).polygon, 7
        ),
        "construction": a.composition["construction"],
        "roles": dict(Counter(i.role for i in a.instances)),
        "validation": build.report.to_dict(),
        "recommended_surface_ids": visible,
        "inventory_fingerprints": sorted(p.fingerprint for p in a.definitions),
        "inventory_replay": "identical",
        "removal_order": a.composition["removal_order"],
    }
    print(key, a.composition["construction"], "projection surfaces", len(visible), flush=True)
(root / "docs/implementation/flow-organism-evidence.json").write_text(
    json.dumps(evidence, indent=2) + "\n"
)
