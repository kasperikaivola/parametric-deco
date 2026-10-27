# Parametric Deco Implementation Plan

> **For agentic workers:** Implement task-by-task using superpowers:executing-plans if that skill is available. This handoff is intended for GPT-6.1 Sol. Read the referenced design documents first. Use the checkboxes to track progress. Implement in the user's chosen execution environment; do not assume this planning session has installed or tested any software.

**Goal:** Build a Python CAD application that generates a reconfigurable intertwined plywood sculpture, laser-cut parts, an identified assembly preview, and ISF resources for Resolume Wire/Arena.

**Architecture:** One versioned part/assembly model drives manufacturing and visual outputs. A simple CLI generates artifacts and validation reports; an interactive preview displays the assembly. Mechanical modules remain separate in the data while visual paths and groups span the whole artwork.

**Tech stack:** Python CAD, SVG, JSON, GLB, ISF/GLSL, Resolume Wire/Arena. Proposed implementation defaults: Python 3.11, build123d, NumPy, Shapely, trimesh, Pillow, pytest, and Ruff. Check current primary documentation and install compatibility before pinning dependencies. Prefer standard-library argparse and JSON over adding a UI/configuration framework.

**Spec:** Read [requirements](../../requirements.md), [decisions](../../decisions.md), [mechanical design](../../mechanical-design.md), [software architecture](../../software-architecture.md), [prototype validation](../../prototype-validation.md), and [roadmap](../../roadmap.md). Their latest "Updated decisions" sections override historical alternatives farther down those files.

## Execution contract

This document authorizes no automatic laser operation or hardware installation. It plans software and prototype artifacts. The user will perform physical tests and may supply Arena/Wire access. Finish all independent software work even when physical or proprietary-host validation is unavailable; report those checks as NOT RUN, not passed.

Work on a new branch such as implement-parametric-deco-v1. Inspect the actual repository and AGENTS.md before editing; preserve unrelated work. At planning time the repository contained documentation only. Avoid building a backend framework, full VJ application, material database, or generalized physics solver.

This plan supplies reasonable defaults, not additional user-approved hardware specifications. Change an implementation default when evidence warrants it and record the reason. Ask only when a real requirement must change or necessary external information cannot be represented as an explicit unknown.

Resolve existing documentary contradictions during implementation: Python CAD is selected; the backplate is plywood; ISF through Wire is first; ordinary mounting bolts are the baseline; precision locating pins and other CAD platforms are historical alternatives. Grade and finish are optional.

## Global constraints

- Initial approximate envelope: 1,000 mm wide, 1,000 mm high, 200 mm deep.
- Laser-cut plywood; one nominal thickness parameter initially set to 6 mm.
- One integrated intertwined artwork, not several unrelated small decorations.
- Plywood polygon backplate with staggered rows of mounting holes.
- Simple robust root attachments; avoid fragile mounting tabs.
- Prefer internal slots and a backplate-retained closure, with no individual rib bolts/pins/clips.
- Detach a module, rearrange it on a bench, then reattach.
- Extra compatible slots/holes are allowed.
- Natural/coloured/neon finishes are optional. No white-paint requirement.
- Immutable manufactured parts; changing design parameters must not resize inventory.
- ISF shaders are hosted/packaged through Wire for Arena. Bare ISF is not assumed to load directly in Arena.
- Physical retention and structural adequacy are unvalidated.
- Keep calibration separate and apply geometric mapping once.

## Review focus

1. Resizing the artwork must not scale thickness, holes, or fit clearance: Task 2.
2. Grid origin/parity changes and edge holes must preserve valid positions and robust margins: Task 3.
3. A valid-looking assembly may be impossible to insert/remove or may shed parts when detached: Tasks 4 and 8.
4. Inventory duplicates and stale part revisions must be rejected, not silently regenerated: Task 5.
5. Coordinate textures may be flipped, colour-managed, interpolated across IDs, or mapped twice: Tasks 7 and 9.

## Defaults and coordinate contract

Use millimetres internally. World axes: X right, Y up, Z outward from the wall, right-handed. The wall mounting plane is Z=0; backing, optional rear clearance, root hardware allowance, and sculpture must fit within the configured total depth. Hardware allowance must be explicit; a mesh without bolts must not imply their extent is zero.

Use an octagonal backplate as a demo default; side count is configurable. Fit the rotated regular polygon to the available width/height with uniform scaling (do not silently distort a regular polygon). The envelope is a maximum, not a demand to touch every boundary.

Illustrative grid defaults: horizontal pitch 50 mm, row pitch 50 mm, alternate-row offset 25 mm, hole diameter 6.5 mm, edge material margin 15 mm. These are prototype choices, not a bolt/load specification. Use grid origin (0,0) and integer row/column IDs. Root placement must match real hole coordinates, including washer clearance.

Measured thickness may initially equal nominal thickness only with an explicit assumed/unmeasured status. Proposed digital fit clearance is 0.2 mm total; export a coupon spanning 0.0–0.4 mm in 0.1 mm steps. Do not call that fit validated.

Export nominal finished contours and delegate kerf compensation to the laser software for v1. Record this policy in every manufacturing manifest. Unknown laser bed size permits individual part exports but blocks claiming a valid nested sheet layout. Do not assume the 1 m backplate fits the machine or automatically invent a segmented structural joint.

## File structure

Create focused files under src/parametric_deco/:
- config.py: configuration loading and validation.
- model.py: immutable part definitions, instances, connections, surfaces, reports.
- cad.py: narrow build123d boundary; no alternate backend abstraction.
- geometry/backplate.py, geometry/module.py, geometry/joints.py: individual geometry responsibilities.
- assembly.py: transforms, inventory assignment, and global visual groups.
- validation.py: envelope, interfaces, interferences, and documented motion checks.
- export/svg.py, export/scene.py, export/manifest.py: consumer-specific output.
- visuals/atlas.py and visuals/isf.py: atlas geometry, textures, shaders.
- cli.py: user commands.

Other files:
- pyproject.toml and a reproducible dependency lock.
- examples/single-module.json, examples/intertwined.json, examples/inventory.json, examples/reconfigured.json.
- shaders/edge-pulse.fs and shaders/calibration.fs.
- preview/: lightweight local viewer, bundled dependencies with notices.
- tests/: matching test modules listed below.
- docs/implementation/: backend decision, joint mechanism, CLI, fabrication, Arena handoff, validation evidence.
- .github/workflows/test.yml.

Do not commit huge generated builds. Include compact representative fixtures and commands that reproduce outputs.

## Shared interfaces

Define these types in model.py; serialize with schema_version=1:
- PartDefinition: definition_id, revision, thickness_mm, local 2D outer contour/holes, interface stations, local projecting surface records, geometry fingerprint.
- PartInstance: instance_id, definition_id, revision, 4x4 local-to-world transform.
- Assembly: definitions, instances, explicit connections, mounting-grid references, global effect groups/paths.
- BuildResult: assembly, fabrication parts, warnings, provenance.
- ValidationReport: issues with severity/code/part IDs; separate digital validity from physical and host test status.
- GeometryBundle: planar contours and CAD solids/meshes associated with explicit part IDs.
- AtlasResult: atlas manifest, textures, and surface-to-tile mapping.
- ExportResult: paths, warnings, and content hashes.

Use finite numeric values, explicit units, stable IDs independent of iteration order, and canonical serialization for fingerprints. Hardware representations can be simplified envelope geometry but must be labelled.

## Task 1 — Verify the Python CAD path

**Files:** pyproject.toml; src/parametric_deco/cad.py; tests/test_cad_smoke.py; docs/implementation/backend.md.

- [ ] Install a compatible pinned build123d stack and development tools in an isolated environment.
- [ ] Write a failing smoke test that builds a 100 × 40 mm plate with a 6.5 mm hole at 6 mm thickness and checks its bounding box and hole preservation after export/reload.
- [ ] Implement the minimal CAD/extrusion/export path and run python -m pytest tests/test_cad_smoke.py -v.
- [ ] Document installed versions and observed export behaviour. Use CadQuery only if a concrete build123d blocker appears; record evidence and update this plan's filenames/contracts rather than maintaining both.
- [ ] Commit the working smoke path.

**Exit:** A real solid and its clean 2D contour export, not only mocked CAD calls. No broad package comparison required.

## Task 2 — Configuration and immutable model

**Files:** config.py, model.py, tests/test_config.py, tests/test_model.py, examples/single-module.json.

**Interfaces:** load_config(path: Path) -> DesignConfig; validate_config(config: DesignConfig) -> ValidationReport. DesignConfig includes envelope, material/measurement status, grid, module recipe, mounting, and optional cutting-bed size.

- [ ] Write tests rejecting NaN/infinity, nonpositive dimensions/pitches, polygon sides below 3, impossible depth, and overlapping hole specifications.
- [ ] Test an envelope resize leaves nominal/measured thickness, hole diameter, and clearance unchanged.
- [ ] Test serialization round-trip, stable geometry fingerprints, and revision changes on geometry changes but not arrangement changes.
- [ ] Implement configuration and records, with clear field-specific errors and optional grade/finish.
- [ ] Run python -m pytest tests/test_config.py tests/test_model.py -v and commit.

**Exit:** Demo configuration is valid without colour, grade, bed size, or projector details, while unknown values remain visible.

## Task 3 — Backplate and compatible root grid

**Files:** geometry/backplate.py, tests/test_backplate.py, docs/implementation/backplate.md.

**Interfaces:** generate_backplate(config: DesignConfig) -> GeometryBundle; mounting_holes(config: DesignConfig) -> list[MountPoint]. Define MountPoint with integer row/column, XY coordinates, diameter.

Grid rule: x = origin_x + column*pitch_x + (row mod 2)*offset; y = origin_y + row*pitch_y. Use the same parity convention for negative rows.

- [ ] Test hexagon/octagon bounds, alternate-row offsets on positive/negative rows, and stable IDs after clipping.
- [ ] Test full hole disks, not just centres, stay inside the polygon with the specified material margin. Check remaining webs and reject impossible hole sizes.
- [ ] Generate the 6 mm solid and nominal contours; retain IDs independent of output ordering.
- [ ] Test that root bolt patterns are accepted only when all required mounting positions match available holes within a stated numerical tolerance.
- [ ] Run python -m pytest tests/test_backplate.py -v; inspect a rendered top view; commit.

**Exit:** A parametrically generated polygon backplate and deterministic usable grid, with no unsupported arbitrary-rotation promise.

## Task 4 — Solve one module's actual joinery

**Files:** geometry/joints.py, geometry/module.py, tests/test_joints.py, tests/test_module.py, docs/implementation/joint-mechanism.md.

**Interfaces:** generate_module(config: DesignConfig) -> GeometryBundle. Define ModuleRecipe for two planar parallel spines, rib profiles, discrete stations, root, end bracing, and closure.

- [ ] Draw the actual cross-sections and assembly states before generalizing the joint. Include insertion vectors, bearing surfaces, blocked motions, closure retention, and nut/tool access.
- [ ] Start with a small demonstrator containing two spines and at least three ribs. Use a common slot datum so perpendicular planar joints remain manufacturable. Avoid modelling arbitrary normal-oriented ribs as simple perpendicular cross-laps.
- [ ] Model the closing member as real cut geometry, not a label or invisible constraint. Explain how it reaches all required retaining features.
- [ ] Establish the detached handling sequence: the assembly must be supported and closure kept engaged during removal. If a handhold or temporary support is needed, document it.
- [ ] Test slot finished width against measured thickness + clearance, mating station compatibility, and section thickness. Check selected intermediate assembly states for interference.
- [ ] Test representative attempted withdrawals: closure removed permits the documented path; closure installed obstructs it. State which motion paths were checked; sampled translations are not a proof of all rigid-body motions.
- [ ] Generate sectional/exploded views, coupon contours, and prototype assembly instructions.
- [ ] Run python -m pytest tests/test_joints.py tests/test_module.py -v and commit the candidate with physical_validation=not_run.

**Stop condition:** If the proposed closure is mechanically impossible, record the failing geometry and propose the smallest change. Do not quietly add rib pins/bolts or ship a decorative imitation of a lock. Continue unrelated backplate/export/visual work.

## Task 5 — Inventory and assembly

**Files:** assembly.py, validation.py, tests/test_inventory.py, tests/test_assembly.py, examples/inventory.json, examples/reconfigured.json.

**Interfaces:** assemble(config: DesignConfig, inventory: Inventory | None) -> BuildResult; validate_assembly(assembly: Assembly) -> ValidationReport. Define Inventory as identified physical instances referencing immutable definitions.

- [ ] Test duplicate instance assignment, unknown revision, mismatched interface family, unavailable station, and insufficient quantity.
- [ ] Implement separate generate-new and existing-inventory modes. Existing-inventory mode must load saved manufactured geometry; do not regenerate it from current design parameters.
- [ ] Test a valid rib rearrangement retains definition fingerprints but changes instance transforms and visual data.
- [ ] Check total envelope, including backing/clearance allowances, and actual solid interference at joints. Do not suppress all collisions between connected parts; intended contact is allowed, unintended volumetric overlap is not.
- [ ] Record extraction direction/sequence per module and detect known path collisions. Mark incomplete motion verification honestly.
- [ ] Run python -m pytest tests/test_inventory.py tests/test_assembly.py -v and commit.

**Exit:** An explicit missing-part/incompatibility report, never a silently stretched inventory.

## Task 6 — Fabrication, scene export, preview, and CLI

**Files:** export/*.py, cli.py, preview/, tests/test_exports.py, tests/test_cli.py, docs/implementation/cli.md, docs/implementation/fabrication.md.

**Interfaces:** export_build(build: BuildResult, out_dir: Path) -> ExportResult. The manifest records geometry fingerprints, transforms, warnings, units, versions, and compensation policy.

Required CLI:
- parametric-deco validate CONFIG
- parametric-deco build CONFIG --out DIR
- parametric-deco reconfigure CONFIG --inventory FILE --out DIR
- parametric-deco preview DIR
- parametric-deco visuals DIR --out VISUAL_DIR

- [ ] Test SVG mm units/viewBox, valid closed loops, holes, separation of cut/engrave layers, no duplicate outlines, and a known-size scale check.
- [ ] Keep nominal contours unoffset in v1; manifest explicitly assigns kerf compensation to laser software.
- [ ] Export individual parts when bed size is unknown. If supplied, implement simple deterministic placement with conservative spacing; reject oversized parts, never shrink them. Optimal nesting and automatic structural segmentation are out of scope.
- [ ] Export GLB with node identities and transforms; convert mm to metres at the format boundary and test a known 100 mm dimension.
- [ ] Build a small locally served viewer with orbit, part identification, assembled/exploded state, and visibility controls. Bundle dependencies for offline use, no CDN requirement.
- [ ] CLI errors return nonzero status and identify bad fields/parts. Prevent accidental output overwrite unless explicitly requested.
- [ ] Run python -m pytest tests/test_exports.py tests/test_cli.py -v; generate and inspect a demo; commit.

**Exit:** Artifacts correspond to the same assembly, with reproducible commands. A simple preview is sufficient; do not build a full editor.

## Task 7 — Geometry atlas and first ISF effects

**Files:** visuals/atlas.py, visuals/isf.py, shaders/*.fs, tests/test_atlas.py, tests/test_isf.py, docs/implementation/visual-data.md.

**Interfaces:** generate_atlas(assembly: Assembly, width: int, height: int) -> AtlasResult; export_isf_resources(atlas: AtlasResult, out_dir: Path) -> ExportResult.

Choose a surface atlas as the initial content space; Arena performs final mapping. Pack explicit projecting faces into tiles with gutters. Keep an explicit tile-to-part/surface mapping; backing faces can be optional. Never confuse a front-view silhouette with correct geometry for every side face.

- [ ] Define local face coordinates, normalized assembly XYZ, validity masks, semantic IDs, and a path/phase coordinate for a continuous cross-module effect.
- [ ] Prefer simple uncompressed PNG resources initially. Quantify 8-bit coordinate precision rather than claiming it supports sub-millimetre edges over a 1 m range. Use local coordinates for precise edge patterns; improve encoding if host tests require it.
- [ ] Test tile orientation with an asymmetric fixture, nonoverlap/gutters, background mask, stable IDs, and cross-module path continuity.
- [ ] Treat ID/coordinate textures as data, not colour imagery. Document filtering and colour-management assumptions; never interpolate categorical IDs.
- [ ] Implement calibration.fs with labelled/asymmetric orientation cues and edge-pulse.fs with controllable speed, phase, colour, and width. Expose ISF image/parameter inputs with valid metadata.
- [ ] Test metadata parsing, input/resource agreement, finite shader math at zero speed/width limits, and optional offscreen reference rendering if a GL context is available.
- [ ] Run python -m pytest tests/test_atlas.py tests/test_isf.py -v and commit.

**Exit:** Documented data contract, generated textures, and actual ISF sources. Static checks alone do not establish Wire/Arena compatibility.

## Task 8 — Integrated intertwined example

**Files:** examples/intertwined.json, tests/test_integration.py, docs/implementation/reconfiguration.md.

- [ ] Arrange repeated compatible modules to suggest one intertwined radial sculpture, within the default envelope. Coordinate contours/rib rhythm and visual paths across module boundaries.
- [ ] Use module instances, not duplicated anonymous mesh blobs. Preserve reusable rib definitions.
- [ ] Generate a second arrangement using the same inventory and emit the changed assembly/mapping manifest.
- [ ] Test envelope, identity preservation, static interference, root-grid compatibility, and defined extraction paths.
- [ ] Inspect front/side views and an exploded view; correct a visually disconnected collection of arms rather than declaring any radial array sufficient.
- [ ] Run python -m pytest tests/test_integration.py -v and commit.

**Exit:** Two reproducible arrangements of the same inventory and a documented removal order. Any unverified physical checks remain explicit.

## Task 9 — Wire/Arena handoff and physical validation packet

**Files:** integrations/resolume/, docs/implementation/arena.md, docs/implementation/validation-status.md.

- [ ] Read official target-version Wire/ISF documentation before authoring the wrapper. State exact versions used.
- [ ] When Wire is available, create a real patch loading generated ISF/resources, expose its controls, compile/package it, and load it in Arena.
- [ ] Check asymmetric orientation, texture values/filtering, resource relocation, masks, cross-module phase, and that geometric mapping is applied only in Arena.
- [ ] Document a practical mapping recipe for one physical module before extending it to every atlas tile. A face atlas may create many slices; record operator effort and limitations.
- [ ] Do not invent a Wire patch schema or Arena screen-preset exporter. If host access is unavailable, supply exact reproducible manual setup instructions and mark the patch/compile/runtime checks NOT RUN.
- [ ] Include the fit coupon, joint/root cut files, numbered assembly/removal instructions, closure-contact views, and a short feedback form for fit, wear, stiffness, and detachment handling.
- [ ] Finish test/report documentation with explicit PASS/FAIL/NOT RUN statuses and reproducible evidence.

**Exit:** Either tested host artifacts or an honest actionable host handoff. No false end-to-end success claims.

## Task 10 — Reproducibility and final delivery

**Files:** .github/workflows/test.yml, README.md, docs/decisions.md, docs/roadmap.md.

- [ ] Add CI for unit/integration tests and a generated-example smoke test. Isolate optional GPU/proprietary-host tests and expose their skipped status.
- [ ] Run python -m pytest -q and python -m ruff check . in a clean environment; run all documented CLI examples.
- [ ] Reconcile older documentation with implemented choices without erasing the decision rationale.
- [ ] Record unresolved mechanical and host checks, dependency versions, branch/commit, and artifact generation commands.
- [ ] Commit and provide a concise handoff with links to source, examples, and validation reports.

## Completion and scope boundary

A successful software milestone includes a working Python generator, polygon/grid backing, a real candidate slotted module, immutable inventory/reconfiguration, SVG/GLB/manifest outputs, preview, ISF resources, and documented Arena integration. Physical approval and proprietary-host validation are separately reported.

Do not implement a standalone VJ engine, multi-projector auto-calibration, FEA, generalized nesting optimizer, a colour/material database, or arbitrary 3D twist joints in this pass. Preserve the data interfaces needed to add those later.

## Self-review mapping

- Dimensions/material/laser/backplate: Tasks 2, 3, 6.
- Simple roots, internal slots, detachable reconfiguration: Tasks 4, 5, 9.
- Whole intertwined artwork and removable modules: Tasks 5, 8.
- Shared geometry, immutable reuse, projection regeneration: Tasks 2, 5–8.
- ISF/Wire/Arena and future renderer compatibility: Tasks 7, 9.
- Optional grade/finish and unknown hardware context: Tasks 2, 6, 9.
- Automated versus physical evidence: Tasks 4, 9, 10.

No implementation or test execution occurred while authoring this plan.
