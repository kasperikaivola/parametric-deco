# Parametric alien execution ledger — 2026-10-29

Plan: docs/superpowers/plans/2026-10-29-parametric-alien.md.
Spec: docs/superpowers/specs/2026-10-29-parametric-alien-design.md.
User explicitly requests numeric composition controls and implementation, default
limb count4, continuing PR #3. Work is inline on its existing isolated feature branch.
One whole-change final review only, no task reviewers.

- Config test RED→GREEN: CreatureMask initially lacked numeric controls. Defaults,
  strict integer count types, finite/ranged shapes and JSON roundtrip implemented.
- Profile test RED→GREEN: module_roots/cavity_voids and settings-aware profiles
  added. Selected counts drive limbs, primary cavities, head/limb layers and ribs.
  Reach/width/curl/asymmetry change actual paths/contours; height changes real fins.
- 66 config/profile/generated-count tests passed11.49s before final contour tuning.
- Old generator ignored requested count2 (still5 modules): test RED→GREEN after
  dynamic root/recipe, backing, part generation, metadata and removal integration.
- New family creature-organism-v3 rejects v1/v2 inventory. Manufacturing signature
  includes every new control. Rest/raised alone changes poses without new contours.
- Four-limb coarse CAD study inspected: limbs sweep laterally/downward, no pair of
  upward C horns. Root hardware, stock and slot sizes remain physical dimensions.
- Actual geometry checks caught raised-pose envelope overflow and interference
  between one lateral return and lower grasper. Peak reach shortened while keeping
  terminal clearance; tests exposed why moving the whole terminal inward was wrong.
- Six-limb .95-width case exposed jaw/feeler contact. Moved the sensory path into
  its own inner lane. No requested module/rib was dropped to make checks pass.
- Ruling: limb_count is TOTAL appendages, not4 main limbs plus fixed extras — this
  avoids hidden numeric composition and matches the parameter name — cost if wrong:
  caller must choose count5/6 for sensory extras, or request a different recipe family.
- Ruling: bounded anatomical cavity palette and six coherent module slots — keeps
  root/joinery constraints explicit, supports documented3–8/2–6 counts rather than
  pretending to solve arbitrary topology — cost if wrong: extend recipes/ranges for
  more cavities/limbs; some range-valid combinations still fail actual CAD guards.
- Previous cavity-area field renamed clear_aperture_probe_areas_mm2 when making
  count-dependent metadata truthful; it measures conservative passage probes.
- CLI harness expanded to build/atlas both2- and6-limb examples in addition to
  default/raised and all legacy/radial cases. Coarse/evidence helpers now consume
  actual config and collect variant images without regenerating inventory.

Physical fit/strength/fasteners/clips/handling/tool access, continuous assembly and
actual browser/Wire/Arena/projector checks remain NOT RUN.

## Verification before final review

- Focused current-geometry creature/config suite:92 passed in351.17s.
- All four actual builds/reconfigure PASS; all four visible-only atlas/ISF exports PASS.
- Evidence collector reloaded all four assemblies, validated atlas IDs, confirmed
  unchanged rest/raised inventory and copied actual CAD images into documentation.
- Two-limb example:91 instances/24 definitions/8 transverse ribs/10 broad targets.
  Default4 limbs:179 instances/54 definitions/24 ribs/22 broad targets.
  Six-limb example:204 instances/57 definitions/18 ribs/29 broad targets.
- Default/raised hardware maxZ190mm, two-limb166mm, six-limb178mm.
- Real default preview HTTP HTML/JS/scene/GLB resources PASS. UI orbit/explode/visibility
  logic PASS. Real browser rendering remains NOT RUN.
- Ruff, JS syntax, whitespace and README/detail image-link checks PASS.
- Complete pre-interruption suite:153 passed,1 missing-host skip in678.25s,
  Python3.12.14. Production source was unchanged afterward. Ephemeral logs were
  cleared at session restart; this result was observed in terminal output and
  independently by the reviewer before interruption.
- Expanded CLI harness process was lost during restart. Re-running all commands,
  with its successful final result appended below.
- Final review: one independent review of the entire change, not per-task reviews.


## Final review and rulings

- The original independent review resumed after interruption; no second review.
  No Critical/Important issue demonstrated; report: `parametric-alien-review.md`.
- Final: minor (deferred):7 mm margin guard does not include neighboring rib slots.
  Exact dense recipe was independently assembled after review: rejected by existing
  solid interference, not a demonstrated accepted invalid export. Keep this limited
  conclusion; it is not a general guarantee of minimum inter-slot ligaments.
- Final: minor (deferred): parameter table calls scale XY-only though rib heights
  also scale. Scale.9 reduces heights10%; stock/roots/joinery remain physical sizes.
- Final: Ruling: bounded palette/module vocabulary — documented current scope,
  with odd counts intentional — cost if wrong: extend recipes/checks for more topology.
- Final: Ruling: final artistic acceptance — images show the new compositions but
  broad shell and backing pads remain visible — cost if wrong: further geometry/new cuts.
- Final: Ruling: physical fit/strength/clips/handling/access/continuous motions — all
  NOT RUN, digital candidate only — cost if wrong: prototype-driven hardware, contour,
  clearance or assembly-aid changes before fabrication/installation decisions.
- Final: Ruling: browser/Wire/Arena/projector runtime — resources and UI logic checked,
  real runtime/calibration NOT RUN — cost if wrong: viewer/resource/mapping corrections.

## Final integration verification

- Fresh expanded CLI harness completed successfully after session restart: ALL
  legacy/radial/default/raised/two-limb/six-limb builds, reconfigurations and atlas
  exports PASS. Localhost preview HTTP HTML/JS/mm scene and preview orbit/explode/
  visibility logic PASS. Actual browser rendering remains NOT RUN.
- Exact dense review recipe was independently assembled: digital_valid=False with
  retaining-key solid interference. Fabrication export refuses such an assembly.
  The incomplete inter-slot margin check remains a deferred Minor, not an accepted
  invalid-build claim. No production fix pass or re-review was needed.
- Re-executed evidence collector after restart: all four saved inventories/atlas
  selections match their evidence; rest/raised identity and manufactured geometry
  remain identical. Committed gallery files unchanged; README/detail links PASS.
- Final Ruff, JS syntax and whitespace checks PASS. Production source remains
  identical to the153-passing/1-skipped full-suite run and reviewed implementation.
- Publication target is the existing creature-mask-example branch and PR #3.
  Master is not merged. The complete published tree is checked against the local
  tree; local implementation history is preserved separately when syncing refs.
