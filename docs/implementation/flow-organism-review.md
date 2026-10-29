# Flow organism execution and one final whole-change review

Repository branch: `creature-mask-example`, PR #3. Starting head:
`78c6c33e5a4f71db6bed90e2fd645cf58cbad0da`. Keep PR open; do not merge.

## Architecture and visual inspection

Read repository instructions, requirements, mechanical/software decisions, current
creature profiles/assembly/export infrastructure, design documents and prior review.
PR discussion retrieval returned no comments. The user's latest brief supersedes
prior artistic decisions and authorizes inline implementation without approval gates.

Generated front and oblique coarse CAD studies before joints. The first field of
simple curls was too repetitive and isolated. Added continuous branching appendages,
curved integral divisions, swelling/taper and physical longitudinal channels.
The second-tier small-plate proposal crowded support patches and contributed too
little visible anatomy; discarded it. Medium complexity adds exposed inner lobes;
high adds local detail without more cut pieces. Actual final views are inspected
separately from these coarse studies; coarse studies are not fabrication results.

Trestles replace spacer columns and individual fin retainers. Exact cut-ligament
checks exposed 3–5 mm backing ligaments, and later a 1.158 mm web between merged
rails. Replaced eroded silhouette copies with inner rails, then added a fixed
4 mm structural allowance per edge. Exact final hole/outline distances still gate
acceptance; the allowance is not substituted for measurement.

## Decisions under delegated design authority

- Initial supported XY range is 800–1400 mm, rather than 600 mm: the smaller
  exploration lacked credible mounting patches. Some range-valid combinations may
  still fail actual geometry checks. Cost if wrong: a later size/stock/joint design
  revision and new cuts; no tiny joints are silently substituted.
- Trestle-supported plates need a cradle while unclamped. No locking gadget was
  introduced. Richer examples use more ordinary root bolts than the legacy default.
  Cost if wrong: physical handling/strength/access tests may require new parts.
- New family replay preserves inventory, but arbitrary flow-module rearrangement
  is not implemented. Legacy radial and creature rest/raised rearrangements remain.
  Cost if wrong: a future arrangement-specific mounting and clearance revision.
- The field/ribbon vocabulary is bounded. The default keeps a rotational ornamental
  rhythm; final alien/mystic appeal remains aesthetic judgment. There is no numeric
  claim that passing geometry checks proves artistic success.

## Verification record

Focused development checks exercise strict config, parameter effects, stable major
silhouettes, real dimensions/stock/joints, static solids, loaded bearing/slot damage,
finished-cut ligaments, dense legacy slot regression, immutable inventory and exact
trestle-prism integration versus OCP. Intermediate failures were used to correct
geometry; they are not reported as accepted builds.

Before the review, the full suite passed 177 tests with one explicit missing-host
skip, the six CAD/projection exports and legacy CLI harness passed. The expanded
focused suite after the fix pass passed 29 tests. Final post-review full-suite and
export results are recorded below when the frozen-source runs complete.

## One final whole-change review and fix pass

One independent read-only reviewer inspected source, inventory/export integration,
all six final-export success records and final actual CAD views. No Critical
finding was reported. Three Important findings were accepted:

1. Adding `organism: null` changed old creature-v3 request hashes. Fixed by
   preserving the legacy signature field set. A regression pins the exact old
   `creature-alien-two` hash; it failed before the fix and passes afterward.
2. The prism test used a non-qualifying part and exercised the OCP fallback on
   both sides. Fixed the test to use the actual `flow-*` register web/tongue
   profile, explicitly require a non-null optimized result and compare it with
   OCP at three rotations and five elevations. Its path assertion failed before
   correction and passes afterward.
3. The first final anatomy still repeated six inward hooks and outer loops.
   Revised the common curve field to vary complete main/branch proportions and
   end-to-end flow between focal regions, spread primary modules across distinct
   relief levels, and use shorter secondary saddles rather than scaled curl copies.
   Flared divisions and spaced longitudinal channels preserve real material webs.
   New structural-diversity tests failed on the repeated predecessor and pass on
   the revision. These tests do **not** measure artistic success. The author
   inspected regenerated coarse/final CAD after the fix; no second independent
   review was requested or claimed.

The plan's minimum-size target/completion bookkeeping was brought into line with
implemented demonstrations. The remaining Minor observation is retained as a
limitation: side views show mostly parallel plywood plates on upright supports.
Actual depth/overlap is present, but this bounded family has less sculptural depth
and anatomical integration than the festival reference. Its ornamental rhythm is
still visible. Several facial readings and final alien character remain aesthetic
acceptance questions, not certified outcomes.

### Reviewer limits ruled on

Same-arrangement flow inventory replay is an intentional initial restriction;
arbitrary new flow arrangements require new cuts and are not advertised. Legacy
rearrangements remain supported. Physical strength, stock fit, manual tool access,
continuous removal, anchoring and real host/projector behaviour require physical
and runtime tests and remain NOT RUN. No load/security or host-success claim is
inferred from digital geometry. No additional reproducible hardware/atlas defect
was found by the reviewer; generation/export checks remain required for every build.

 Physical fit/load/strength/hardware,
anchors, manual assembly/removal access and handling remain NOT RUN. Actual browser
rendering, Wire/Arena compilation, projector calibration and illumination remain
NOT RUN. The JS/HTTP checks exercise logic/resources, not visual browser behaviour.

## Frozen-source post-review verification

- Full suite: `python -m pytest -q -rs` — **182 passed, 1 skipped**, 537.27 s.
  The skip explicitly requires an unavailable Wire/Arena/offscreen runtime.
- Focused suite: **29 passed**, including RED→GREEN compatibility, optimized-path
  coverage and primary anatomy/depth-diversity regressions.
- `scripts/organism_examples.py`: all six full builds, SVG/GLB/JSON/PNG exports,
  saved-inventory replays and visible atlas/ISF exports succeeded. Projection tile
  IDs match selected IDs; 36 final view copies match generated CAD PNGs exactly.
- Actual total depths: 132.8 / 189.8 / 227.8 mm at 800 / 1000 / 1400 mm sizes.
  Minimum measured finished plate and backing cut ligaments: 8.013195 mm.
- Ruff, JS syntax, high-example orbit/explode/visibility logic and local Markdown
  links passed. The JS test is not an actual visual browser inspection.
- Legacy `tests/run_examples.py` completed with exit 0: all single/intertwined,
  radial/reconfigured and legacy creature/two/six build, reconfiguration and
  projection commands passed, as did localhost HTTP resources and preview UI logic.

Physical/runtime limitations above remain NOT RUN; no approval to fabricate,
install or merge follows from these results.

Author CAD verification after the fix inspected final low/high fronts, high
three-quarter, bilateral front and low side, alongside the regenerated coarse
studies. Inter-region flow and relief diversity improved; the bounded loop/ribbon
vocabulary and mostly parallel faces remain visible limitations. This is not a
second independent review or an artistic-success certificate.
