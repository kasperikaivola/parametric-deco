# Radial Weave Implementation Plan

> Execute inline with superpowers:executing-plans. One whole-branch review at the end; no per-task reviewers. User has approved the visual direction and requested implementation.

**Goal:** Real digital intertwined artwork with a pronounced central opening and alternating crossings, plus immutable reconfiguration and fabrication/projection outputs.
**Architecture:** Opt-in curved radial module family on existing shared CAD/model/export pipeline; authoritative inventory placement templates separate from manufactured geometry.
**Tech stack:** Existing pinned Python/build123d/Shapely/trimesh/Pillow stack.
**Spec:** ../specs/2026-10-28-radial-weave-design.md

## Global constraints

- 1,000 × 1,000 × 200 mm maximum; measured stock 6 mm default; no thickness scaling.
- Central aperture radius 180 mm default; actual CAD contours must preserve it.
- Two sinusoidal paths, six crossings with alternating over/under roles.
- Real closed capture geometry, no individual rib fasteners, explicit root bolts.
- Reconfiguration preserves saved definitions/physical IDs; physical/host NOT RUN.

## Review focus

1. Captured radial tongues must obstruct inward withdrawal while permitting assembly without the rail.
2. High supports/root hardware may cross low sculpture despite clear crossing crests.
3. Geometry must preserve the central opening, including actual root pads and ribs.
4. Saved inventory must reject stale templates or resized geometry, not regenerate it.
5. Acyclic sampled removal and visual continuity must hold in both arrangements.

## Task 1 — Composition configuration and curved planar geometry

Files: config.py, geometry/weave.py, tests/test_weave.py.
- [x] Write failing tests for finite/ranged composition settings, aperture, module/rib counts, alternating crossing heights and connected contours.
- [x] Add optional composition configuration; preserve old configuration behaviour.
- [x] Generate planar arc spines, radial ribs, closed capture rail and compatible root pads. Select actual grid holes and bolt corridors.
- [x] Run focused tests; render candidate views before marking geometry complete.

## Task 2 — Inventory, retention and removal

Files: model.py, weave_assembly.py, assembly.py, validation.py, tests/test_weave.py.
- [x] Test real radial withdrawal/insertion and rail obstruction, full static collision, total depth, root holes, ordered module extraction.
- [x] Add optional authoritative inventory layout and assembly composition metadata; old schema-1 files remain loadable.
- [x] Generate first build or reconfigure saved geometry with compatible rib permutation and 180-degree placement rotation.
- [x] Test identity/fingerprint preservation, stale/missing parts and incompatible design requests.

## Task 3 — Rendered artwork, exports and reproducible examples

Files: examples/radial-weave*.json, export/views.py, export/manifest.py, docs/implementation/radial-weave.md.
- [x] Export both arrangements via existing CLI, cuts, GLB, inventory, atlas and shaders.
- [x] Include composition, root, crossing and removal evidence; supply correct family-specific assembly instructions.
- [x] Inspect front/oblique/side/exploded/section views. Correct any disconnected or visually ambiguous crossing result.
- [x] Update Task 8 status only against actual evidence; preserve the earlier mechanical study.

## Task 4 — Verification and single final review

- [x] Run full pytest, Ruff and CLI examples; keep physical/host checks separate.
- [x] Commit then request one fresh whole-branch read-only review. Fix material findings in one tested pass without re-review.
- [x] Push a new branch/draft PR with visual evidence and explicit limitations; no automatic merge authorization for this new feature.
