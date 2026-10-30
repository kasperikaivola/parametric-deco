# PR #3 review corrections — laminar family v2

Review addressed: [comment 6510722024 on e7f2343](https://github.com/kasperikaivola/parametric-deco/pull/3#issuecomment-6510722024).
The PR stays open; no merge is authorized for this correction task.

## Division retention

The review's loss reproduction was confirmed. With channels and secondary lobes
disabled, redistributed `linspace` divisions removed medium material when high
complexity was requested. Three initial tests failed: medium→high and explicit
segmentation 3→4 and 4→5. The endpoint-first dyadic sequence now has nested prefixes.
All seven retention regressions pass on actual generated polygons, not only path,
exterior or helper-position equality. Size fitting is independent of internal detail.

## Replacement anatomy

The inner-curl/outer-loop construction was replaced, not proportionally deformed
again. Shared curved spindles carry eccentric focal lenses and divergent daughter
laminae. Field phase changes which regions have open clefts, closed cavities and
one/two/three branches. The two arrangements retain the same focal count but change
composition, orientation and anatomical overlap.

The initial v2 coarse study was inspected before detailed export. Narrow slit-like
lenses were widened/shortened to form focal chambers. Actual material checks then
required broader banks around the chambers. Coarse and final CAD both retain rounded
or truncated outer ends; requested thin/infeasible variants still fail validation.
The low study has regional topology differences without relying on complexity. Medium
adds physical inner recess walls; high adds their daughter anatomy. The first solid
inner walls obscured too much cavity, so they were opened around a substantial middle
mounting node. Closed little windows were changed into side-open recesses to avoid
floating pupil-like forms inside the larger cavities. Numerical tests constrain geometry; they do not establish visual appeal.

Inspection includes combined fronts, oblique/three-quarter and side views with visible
backing/supports. The backing follows the banks beside cavities, rather than crossing
every lens through its middle. Hardware is omitted in the labelled inspection PNGs
and represented by clearance proxies in GLB/JSON. No renderer was replaced.

## Construction and identity

Retained 6 mm stock, fixed physical clearances, trestles, substantial plywood backing,
module bolts, SVG/GLB/JSON, surface IDs, atlas/ISF and the rotatable viewer. Counts remain
19 wood pieces at low and 37 at medium/high, with no spacer rings or individual clips.
Purchased hardware and approximate assembly operations remain separately reported.

The geometry family is now `laminar-organism-v2`. Previous scroll inventories require
their original cuts/generator; v1 is explicitly rejected rather than regenerated.
Representative v1 images and the original commit are linked in the design guide.
Legacy creature/radial generation and immutable inventory behavior are preserved.
Only the new family's generated profiles remove exact duplicate Boolean vertices;
no legacy fingerprint/canonicalization change was made.

## Verification

Focused suite: 41 tests passed after the anatomy and side-open recess changes. This
includes the seven nested-material regressions, non-returning axes, connected thin
sweeps, new control effects, version rejection, stock/joint dimensions, real mounting,
bearing, static interference and ordered sampled removal. Existing shape/material
checks were retained; a shared major-body outline replaces exterior-only comparison
where new internal septa intentionally close a portion of an open cleft.

Frozen-source results:

- Full suite: **194 passed, 1 skipped** in 501.82 s (`python -m pytest -q -rs`).
  The skip explicitly requires an unavailable Wire/Arena/offscreen runtime.
- All six full CAD builds, fabrication SVGs, identified GLB/JSON, saved-inventory
  replays and visible-face atlas/ISF exports passed. Selected surface IDs match
  atlas tile IDs; all 36 final view copies match generated CAD PNGs byte-for-byte.
- Actual total depths including hardware allowances: 132.8 / 189.8 / 227.8 mm for
  the 800 / 1000 / 1400 mm versions. Minimum measured plate and backing cut
  ligament in these builds: **8.013195 mm**.
- The incoming medium→high material comparison (channels=0, secondary_lobes=0)
  loses at most **1.783e-13 mm²** per primary plate, numerical noise, versus the
  reported hundreds/thousands of mm². All explicit division increments retain
  existing internal material within the 1e-6 mm² regression tolerance.
- The complete legacy CLI harness passed generation/reconfiguration/projection for
  single, intertwined, radial and all creature studies; localhost preview HTTP,
  resources and UI logic passed. High-v2 orbit/explode/visibility logic, JS syntax,
  Ruff and Markdown links also passed. These are not real browser-render tests.

Author verification inspected low/medium/high fronts, oblique/three-quarter views,
the alternate composition and sides, including backing/supports. The v2 hierarchy
has large primary chambers, branching/cavity variation and forked, side-open inner
walls. The blade/lamina rhythm remains visible; aesthetic acceptance is still a
visual review decision, not a consequence of the numerical test count.
The incoming review was addressed as a fix pass;
no task-by-task reviewers or additional independent re-review were dispatched.

Physical strength, fit, fastener security, anchoring, handling, actual tool access and
continuous assembly/removal remain NOT RUN. Actual browser rendering, Wire/Arena
compilation and projector behaviour remain NOT RUN. Passing geometry/tests is not
fabrication approval or a claim that artistic acceptance has been independently met.
