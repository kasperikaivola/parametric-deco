"""Collect evidence from the two CLI builds, without generating manufactured parts.

Run after build/reconfigure and both --visible-only visuals commands in the docs.
"""

from collections import Counter
import json
from pathlib import Path
import shutil

import numpy as np

from parametric_deco.model import Assembly, Inventory
from parametric_deco.validation import instance_bounds


records = {}
inventories = []
for name in ("creature-mask", "creature-mask-raised", "creature-alien-two", "creature-alien-six"):
    directory = Path("build") / name

    def read(filename):
        return json.loads((directory / filename).read_text())

    assembly = Assembly.from_dict(read("assembly.json"))
    inventory = Inventory.from_dict(read("inventory.json"))
    assert assembly.composition["family"] == "creature-organism-v3"
    assert read("validation.json")["digital_valid"]
    if name in ("creature-mask", "creature-mask-raised"):
        inventories.append(inventory)
    bounds = np.array(
        [instance_bounds(assembly.definition_for(i), i.transform) for i in assembly.instances]
    )
    visibility = read("projection-visibility.json")
    atlas = json.loads((Path("build") / (name + "-visuals") / "atlas.json").read_text())
    recommended = visibility["recommended_surface_ids"]
    assert {tile["tile_id"] for tile in atlas["tiles"]} == set(recommended)
    records[name] = {
        "family": assembly.composition["family"],
        "physical_instances": len(assembly.instances),
        "manufactured_definitions": len(assembly.definitions),
        "roles": dict(Counter(i.role for i in assembly.instances)),
        "wood_bounds_mm": [
            bounds[:, 0, :].min(axis=0).tolist(),
            bounds[:, 1, :].max(axis=0).tolist(),
        ],
        "hardware_max_z_mm": max(h[6] for h in assembly.hardware_bounds),
        "composition": {k: v for k, v in assembly.composition.items() if k != "modules"},
        "recommended_projecting_surfaces": recommended,
        "visibility_fractions": {
            s["surface_id"]: s["visible_fraction"] for s in visibility["surfaces"]
        },
        "validation": read("validation.json"),
    }
    for image in (directory / "views").glob("*.png"):
        if name.startswith("creature-alien") and image.stem not in ("front", "three-quarter"):
            continue
        shutil.copy2(
            image, Path("docs/implementation/images/creature-mask") / (name + "-" + image.name)
        )
first, second = inventories


def identity(inv):
    return sorted((i.instance_id, i.definition_id, i.revision, i.role) for i in inv.instances)


assert identity(first) == identity(second)
assert sorted(d.fingerprint for d in first.definitions) == sorted(
    d.fingerprint for d in second.definitions
)
records["reuse"] = {
    "identical_physical_assignments": True,
    "identical_manufactured_geometry": True,
    "previous_v1_v2_inventory_compatible": False,
}
Path("docs/implementation/creature-mask-evidence.json").write_text(
    json.dumps(records, indent=2) + "\n"
)
print("Verified matching inventory, atlas IDs and copied actual CAD views for both poses.")
