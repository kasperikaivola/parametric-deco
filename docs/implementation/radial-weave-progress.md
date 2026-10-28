# Execution ledger — radial weave

Plan: docs/superpowers/plans/2026-10-28-radial-weave-implementation.md
Spec: docs/superpowers/specs/2026-10-28-radial-weave-design.md

Baseline master bc798a0; clean isolated branch implement-radial-weave.
User selected pronounced opening and dense sweeping radial forms with crossings.
One final review only. Existing stock family and old study remain supported.

Preflight: geometry → assembly → validation → export all use mm/right-handed axes.
New radial family requires inward rib extraction, not legacy global +Z retention.
Inventory layout must store station transforms and not depend on mutable config.

Geometry: original fixed-end pads left only one clear grid hole for a5/b1.
Opposite-end root search now provides 24 clear mounts without relaxing clearances.
Search pads are trimmed to the selected washer regions and backbone bridges;
this also removed the former pad/fin clashes. Blueprint/config tests pass.
Root-pad trial renders inspected: pronounced aperture and two continuous annular paths;
trimmed roots replace oversized petals. Front/exploded inspected; final exports pending.
Validation acceleration uses exact XY-prism intersections and conservative XY rejection
before kernel booleans; moving geometry still uses real solid intersection.
Numerical test correction: allow 1e-6 mm aperture tolerance (observed -2.84e-14 mm).

Task 1: complete — finite/ranged composition validation, 12 connected curved
modules, 108 fins, circumscribed central aperture, alternating six crossings,
24 selected clear roots; front/side/oblique/exploded/section CAD views inspected.
Task 2: complete — real radial joint paths and rail obstruction pass; full solids
and sampled ordered +Z module removal pass. Saved geometry and physical identities
survive reconfiguration. Changed stock and stale layouts reject (regression RED→GREEN).
Task 3: complete — both CLI arrangements export SVG/GLB/JSON and 4096² atlas/ISF
resources. Radial assembly instructions replace the legacy instructions. Rotated
world crossing angles corrected (observed 0 instead of 180 RED→GREEN); crossing
sampling resolves central station rather than original physical fin number.
Task 4: initial verification — full suite 55 passed / 1 explicit host skip
(Python 3.12.14, 282.00 s). Ruff and JS syntax pass. Full CLI harness running.
Final single review pending. Physical/host/browser rendering NOT RUN.

Final review: one fresh read-only whole-branch review of bc798a0..01e9f09,
including source, plan/spec, saved evidence, inventory safeguards and all seven
CAD views. No Critical or Important findings; digital candidate ready after CLI.
Final: minor (deferred): float-valued rib_permutation indices pass configuration
equality checks and fail with TypeError during assembly; use integer indices.
No second review round. No material fix pass was required.
Final: Ruling: physical fit/load/handling and root/backing design remain uncertified
— digital candidate only, physical checks NOT RUN — a prototype may require redesign.
Final: Ruling: motion evidence remains bounded sampled translation, not continuous
motion or tool-access certification — matches reported scope — an unsampled clash
or access failure may require redesign.
Final: Ruling: browser/Wire/Arena/projector behavior remains NOT RUN — no available
host execution evidence — runtime compatibility or calibration may need fixes.
Final: Ruling: artistic acceptance remains the user's judgment — CAD shows opening
and recognizable interwoven paths — aesthetic iteration may still be wanted.
Final: Ruling: review deferred CLI judgment is now resolved by a completed passing
harness — both families, both radial arrangements/atlases and localhost preview/UI
logic passed — future environment-specific failures remain possible.

Final verification: 55 passed / 1 explicit Wire/Arena host skip on Python 3.12.14
(253.88 s), on the final source including world-space crossing metadata.
Complete CLI harness PASS: both legacy examples, both radial arrangements,
all atlas selection modes, both radial atlases, localhost preview HTTP and
preview UI logic. Real browser rendering still NOT RUN. Ruff, JS syntax,
whitespace and compatibility check of all 66 installed packages PASS.
Final CAD build/evidence refreshed; compact tracked evidence omits duplicate
station matrices, which remain authoritative in exported inventory/assembly files.
Delivery approved explicitly by the user: publish implement-radial-weave to
kasperikaivola/parametric-deco and create a draft PR. Publication uses the
connected GitHub app because the terminal has no GitHub credentials.
The earlier authorization block is resolved. Master is not merged.
