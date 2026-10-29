# Creature Mask Implementation Plan

> Execute inline with superpowers:executing-plans. One fresh final review only.

**Goal:** A new creature-like parametric CAD example, robust digital assembly and exports.
**Architecture:** Separate CreatureMask family on shared immutable records/exporters;
planar layered profiles, closed-slot alignment webs and root-clamped spacer stacks.
**Tech stack:** Existing pinned build123d/Shapely/trimesh/Pillow Python stack.
**Spec:** ../specs/2026-10-28-creature-mask-design.md

## Global constraints
- 1000×1000×200 mm maximum initially; measured stock6 mm; no stock scaling.
- Preserve radial/legacy examples and unrelated changes; branch from latest master.
- Real closed contours, two root bolts/module, accessible retaining parts.
- Inventory placement does not regenerate geometry; no automatic merge.

## Review focus
1. True eye apertures and hierarchy in front/oblique, rather than a disguised ring.
2. Spacer compression paths, cap/web capture and actual washer/tool clearance.
3. Raised-crown inventory reuse stays in envelope and leaves practical removal order.
4. Configuration/inventory failures reject stale geometry and incompatible placements.
5. Projection visibility IDs stay matched to physical geometry; no host claims.

## Task 1 — silhouette and coarse visual study
Files: geometry/creature_profiles.py, scripts/creature_study.py, tests/test_creature.py.
- [x] Write profile tests for connected contours, eye voids, symmetry, rounded ends.
- [x] Run tests RED; implement curves and low-detail layered profiles; run GREEN.
- [x] Generate front/oblique coarse study before detailed joints; inspect and revise.

## Task 2 — physical family and immutable assembly
Files: config.py, geometry/creature.py, creature_assembly.py, assembly.py, backplate.py.
- [x] Test validation, measured thickness, slots/webs/caps, two actual grid roots/module.
- [x] Implement five modules, spacer stacks, backplate and interfaces; test real solids.
- [x] Test static clearances, bearing/tool corridors and cap blocking; fix failures.
- [x] Test saved identity in raised_crown, missing/stale inventory and new-cut requests;
implement authoritative saved templates and bounded extraction dependencies.

## Task 3 — exports and visual acceptance
Files: export/views.py, export/manifest.py, visuals/visibility.py, examples/creature*.json.
- [x] Test family-specific instructions, broad surfaces/IDs and visibility estimates.
- [x] Export cuts/GLB/JSON/atlases/ISF for both poses; inspect CAD front/oblique/section.
- [x] Revise major form if generic; document hierarchy, reuse and physical limitations.

## Task 4 — verification and handoff
- [x] Full pytest, Ruff, CLI workflows, JS and dependency compatibility.
- [x] One whole-branch review; fix material findings with regressions, no re-review.
- [x] Commit, publish through connected GitHub app if terminal auth unavailable,
verify published tree equals local, open PR; leave master unmerged.
