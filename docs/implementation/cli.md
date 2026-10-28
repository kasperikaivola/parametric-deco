# CLI

Install (Python 3.11–3.13, tested here on 3.12):

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
parametric-deco validate examples/single-module.json
parametric-deco build examples/single-module.json --out build/single
parametric-deco preview build/single
parametric-deco visuals build/single --out build/single-visuals
parametric-deco build examples/intertwined.json --out build/intertwined
parametric-deco reconfigure examples/reconfigured.json --inventory build/intertwined/inventory.json --out build/reconfigured
parametric-deco visuals build/reconfigured --out build/reconfigured-visuals
```

The preview binds only to 127.0.0.1:8765. Open the printed URL; Ctrl+C stops
it. Drag or use Front/Side/Perspective, explode, toggle backing/hardware or
individual parts, and click a part for its instance and definition revision.
It is a lightweight orthographic painter-rendered inspection tool; use GLB
in a dedicated viewer for higher-quality rendering and dense occlusion.
No CDN or external JavaScript is used. Source lives in package resources;
the preview/ directory mirrors the three files for easy inspection.

Errors return nonzero and name the relevant field/part. Existing nonempty
outputs require explicit --force. Export stages files before copying them
into the target; --force overwrites generated names and preserves unrelated
notes. Obsolete generated files are removed only when the previous manifest
identifies them and their hashes still match. A modified obsolete file blocks
the rebuild so it can be moved or preserved explicitly. Unsafe manifest paths
and symlink redirects are rejected before changing outputs.


Atlas controls (selection happens before packing):

```sh
parametric-deco visuals build/single --out build/fronts --surfaces broad
parametric-deco visuals build/single --out build/edges --surfaces exterior
parametric-deco visuals build/single --out build/selected --surface m1-rib-0--front
```

The broad-face default omits edge and hole-wall tiles. `--surfaces all` includes
all explicit faces when needed. Tile texel sizes and selected/available counts
are recorded in atlas.json. Existing inventory configuration supports explicit
physical-ID assignments; see reconfiguration.md and examples/reconfigured.json.
