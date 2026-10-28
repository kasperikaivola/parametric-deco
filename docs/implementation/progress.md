# Implementation ledger

Plan: docs/superpowers/plans/2026-10-27-parametric-deco-implementation.md

Execution: inline, one whole-branch review at the end, no per-task reviews.

Preflight: model → geometry → assembly → export → atlas share millimetre coordinates, canonical immutable definitions, right-handed rigid transforms and stable IDs. Root/grid coordinates must agree; SVG flips Y only at export; GLB converts mm to metres only at export. Atlas content is not projector-calibrated imagery.

Environment: fresh clone on implementation branch, no pre-existing software/tests.

Ruling: use a full-length upper closure with two long root bolts rather than an unretained lower root flange — a closed slot alone does not stop a module lifting from a lower flange. Root wings clamp the upper closure to backing and close the rib +Z path. Cost if wrong: physical prototype may require redesign; no load/handling approval is claimed.
Ruling: execute in the fresh cloned checkout on a new branch — it is already isolated from user working files; a second worktree would add no protection here.

Task 1: complete — real CAD test RED (missing CAD module), GREEN; STEP reimport, dimensions, hole volume and probe. Dependency installation uses a fresh consistent build123d 0.13.0 stack; old mixed install discarded. CAD reference path implemented, smoke test passed.

Task 2: complete — 14 focused tests RED→GREEN; strict field validation, independent manufacturing dimensions, canonical immutable part geometry/revisions, checked rigid transforms and deserialization fingerprints. Default material measurement remains assumed/unmeasured.

Task 3: complete — grid and root tests RED→GREEN (2 tests); uniform regular polygons, negative-row parity, disk/margin containment, shifted origins and all-hole root matching. Top view rendered for inspection. Backing projection faces excluded explicitly; backing holes tessellated to 32 segments with bounded 0.0157 mm sag to keep prototype artifacts manageable.

Task 4: complete — 3 focused tests RED→GREEN; actual CAD slots, paired spines, four ribs and full-length slotted closure. Real solid intersection tests cover rib translations 0/5/20/50/100 mm and show +1 mm withdrawal blocked at every rib. Location API mismatch traced to unsupported Matrix constructor, fixed at CAD boundary using rigid gp_Trsf. Section/exploded exports accompany Task 6. Physical validation NOT RUN.

Task 5: complete — 5 tests RED→GREEN, 27.99 s. Saved inventory is reconstructed from verified manufactured contours, not regenerated from current module recipe. Revision/duplicate/quantity/family checks and real solid collision checks pass; connected parts are not exempt. Hardware is included in total bounds. Extraction sampling reports dependencies and remains non-exhaustive.

Task 6: complete — 5 export/CLI tests RED→GREEN (58.79 s); SVG/holes/scale/layers, GLB named nodes/metres, shelf packing quantities/oversize rejection, staging and overwrite guards, preview resources, runtime CLI. Viewer and demo inspection follow in integrated example.
Task 7: complete — 3 tests RED→GREEN and 1 explicit host skip; asymmetric face/mask orientation, tile gutters, stable IDs, path intervals, resource agreement and finite zero-limit CPU reference. Numeric/data contracts documented; static checks are not host validation.

Task 8: INCOMPLETE (corrected after owner review) — mechanical fixture RED→GREEN; both configurations preserve every inventory instance/revision while changing rib transforms. Initial corner collisions were detected and corrected using valid lattice positions. Curved spine/closure profiles coordinate the whorl; updated joint/integration tests pass (4 tests, 21.84 s). Front/side/exploded inspection caught a reversed exploded-view depth convention, corrected with a failing positive-Z projection test. Rendered section uses an actual mesh plane cut.
Task 9: complete software handoff — official Wire ISF/integration/consolidation and Arena mapping docs read. Manual source/texture/control/compile/mapping recipe and feedback forms supplied. Exact installed host versions unavailable; all compile, relocation, physical and runtime tests NOT RUN. No proprietary patch or preset schema invented.
Ruling: browser screenshot validation is NOT RUN because Chromium downloads were corrupt/unavailable in this environment — supply deterministic CAD inspection images, JS syntax and UI-logic smoke checks instead. Cost if wrong: browser-specific rendering/UI defects may remain; no browser-render pass is claimed.

Task 10: implementation complete — CI, README, decision reconciliation, compact saved inventory, representative inspected images, reproducible CLI/localhost smoke harness and status report added. Ruff passes; clean locked installation and pip compatibility check pass. Python 3.11 dependency resolution and every installed Requires-Python marker checked. scipy/Deprecated were constrained to compatible locked releases rather than claiming a 3.12-only lock supports 3.11. Final full suite and documented CLI harness are running before delivery.

Single whole-branch review starts after all implementation tasks; no per-task reviewer was dispatched. Final findings will be recorded below and fixed in one pass with regression tests, without re-review.

Pre-review full-suite evidence: clean Python 3.12.14 installation, 36 passed / 1 explicit host skip, 223.45 s. Full CLI harness PASS for validate, single/integrated builds, both visual resource outputs, saved-inventory reconfigure and localhost HTTP preview. JS UI-logic smoke PASS; actual browser NOT RUN. Ruff and git diff whitespace checks PASS. Python 3.11 pinned dependency resolution PASS; an actual 3.11 environment is also being installed for final verification.

Final review: one read-only whole-branch review, resumed after a usage-limit interruption in the same context; no additional review round. No Critical findings. Five Important findings verified and fixed in ONE pass, each with regression RED→GREEN:
- Retain all unassigned inventory across partial reconfiguration/export; restore after changing module pose.
- Select the real module ID for a section, with a deliberate empty-section placeholder.
- Use measured physical thickness consistently; retain nominal stock designation.
- Require geometric washer bearing for configured and saved manufactured root/backing holes.
- Remove obsolete owned cuts/sheets on forced rebuild, validating ownership hashes and rejecting unsafe paths before mutation.
Focused fix evidence: six measured-stock/inventory/module/washer tests PASS (23.80 s); two forced-rebuild/unsafe-path tests PASS (2.37 s). Ruff PASS. Full clean Python 3.11.17 suite and CLI harness running for final verification.
Final: minor (deferred): coupon lacks individual clearance engravings; ordered slot widths remain in interface metadata.
Final: Ruling: retain NOT RUN for physical retention/load, finished fit, tool/tray handling, Wire/Arena runtime, browser rasterization and exhaustive disassembly — unavailable evidence cannot be replaced by static tests; cost if wrong: physical/host problems can require prototype or integration changes before use.

Final: fixed all five Important findings — their eight regression cases RED→GREEN, then full clean Python 3.11.17 suite 44 PASS / 1 explicit host/offscreen skip (108.10 s). Full documented CLI harness PASS for validate, single/intertwined builds, inventory reconfiguration, both visual bundles and localhost HTTP preview. UI-logic smoke PASS. All 66 locked dependencies compatible. Ruff and whitespace checks PASS. No re-review requested; coupon engraving polish remains deferred. Remote CI is separate and not claimed to have run locally.


Owner PR #1 feedback — 2026-10-28:
- P1: reject ribs incompatible with the actual closure contact height; loaded assemblies verify +1 mm obstruction using solids.
- P2: select surfaces before packing; broad faces by default, physical-size allocation, exterior/all or explicit face options. Hole walls are opt-in.
- P2: explicit physical spine/closure/rib assignments independent of old ownership and physical ID spelling; reference poses are not used as assignment keys.
- P2: full intertwined composition is INCOMPLETE. The legacy example and images are mechanical study fixtures, not proof of artistic integration. This follows the owner's explicitly offered alternative.
No additional review round is commissioned; owner findings are addressed by regression tests and CI before the authorized merge.

Owner-feedback verification: five new regression tests RED→GREEN. Full suite 49 PASS / 1 explicit host skip (Python 3.12.14, 124.08 s). Full CLI harness PASS including explicit cross-module physical assignments and all documented atlas selection commands. Ruff/format/whitespace checks PASS. Task 8 remains INCOMPLETE under the owner's offered scope alternative; merging the software foundation does not complete the artwork. Hosted Python 3.11 CI is the remaining merge gate.
