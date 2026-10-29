# Organism revision ledger — 2026-10-29

Scope: user requested revision of existing PR #3 after finding the first mask too
literal, helmet-like and sparse. The approved direction is six unequal recesses,
no nose/helmet, scalloped shells, internal channels and transverse anatomical ribs.
New design/plan: `docs/superpowers/{specs,plans}/2026-10-29-ambiguous-organism*`.
Repository instruction: inline implementation and one complete final review only.
The older v1 review is historical and does not approve this new implementation.

- Profile test RED: only two eye cavities. GREEN: six unequal hooked cavities,
  irregular central aperture, connected scalloped shells and open limb channels.
- Coarse real-profile front/oblique studies generated before rib joinery. First
  study was too much like holes punched into a plate. Added shell-edge channels,
  asymmetric hooked cavity contours and actual transverse-rib silhouettes.
- Joint tests RED: no blade inventory/registration. Implemented 24 unique ribs,
  actual cap slots, 28 mm feet, key windows, shoulders and retaining keys.
- Misplaced-key test RED→GREEN: zero solid overlap alone cannot prove engagement.
  Validator now sections the real key at the fin midplane and checks that it
  crosses a real tab window, plus inward shoulder/outward key bearing.
- Raised pose initially obstructed cavities; manufactured crown reliefs now clear
  both prescribed poses. No regeneration during existing-inventory placement.
- Minimum-scale jaw cap had insufficient slot bearing; moved terminal rib into
  broader material. Minimum 7 mm surrounding slot material is checked in CAD.
- Plain keys had no positive withdrawal stop. Added a wider head, 2.5 mm clip hole
  and 24 labelled clip-envelope proxies. Retainer-head/hole test RED→GREEN.
  Ruling: clip hardware is a required prototype selection, not certified hardware;
  the physical candidate must be redesigned if actual clips cannot fit and retain.
  Cost if wrong: new keys/caps, different fasteners or a revised joint after fit test.
- Curve-parameter spacing crowded adjacent retaining keys. Actual solid overlap
  located the offending pairs. Path-distance placement removes that crowding.
- Six focused joint/edge/reuse tests passed (82.19 s), including scale .9, curl .8
  and 1.2, measured stock 5.8 mm and raised modules. Additional view/export and full
  regressions are recorded below after final execution.
- Orbit viewer had a pre-existing creature-specific defect: Explode handled only
  legacy rib/closure roles. New real-pixel-coordinate assertion RED→GREEN; cap,
  blade, retainer and clip envelopes now move together, lower armour separately.
- Added more frontal three-quarter CAD view and actual local rib/key/cap section.
  Kept existing view filenames and pipeline. Webs/caps now omit inapplicable
  interface stations; plate station metadata uses its local XY coordinates.
- Final visual pass still found a broad quiet central bridge. Two curved through
  channels follow the inner cavity walls; nine-aperture profile assertion RED→GREEN.
  This is actual cut geometry, not surface engraving. Full checks rerun afterward.

Physical fits/strength, positive clip selection/security, tray handling, manual
access, continuous assembly/removal, actual browser rendering, Wire/Arena and
projector runtime remain NOT RUN. No merge is authorized by this task.

## Final verification and review

- Current-geometry full suite: **73 passed, 1 skipped in 411.90 s**, Python3.12.14.
  Skip: no Wire/Arena or configured offscreen ISF host; no runtime inference.
- Complete CLI harness PASS: all legacy/radial builds/reconfigurations/atlas modes,
  both current creature poses and visible-only atlases, localhost HTTP resources
  and preview UI logic. Creature-specific UI check also PASS, including actual
  changed pixel coordinates when Explode moves cap/rib/key groups.
- Both real CLI exports PASS. Evidence collector independently reloaded both saved
  inventories, confirmed identical IDs/revisions/fingerprints, matched recommended
  projection IDs to atlas tiles, and copied seven CAD images for each posture.
- Rest wood bounds: (−454.64,−381.26,10) to (454.64,418.61,178) mm.
  Raised: (−479.64,−381.26,10) to (479.64,468.61,178) mm. Hardware max Z190 mm.
  Each posture: 189 physical plywood instances, 56 definitions, 24 broad targets.
- Ruff, JavaScript syntax and whitespace checks PASS. The evidence script executed
  successfully. No geometry or implementation changes after the single review.
- Final review: independent whole-change reviewer, no Critical/Important findings.
  Report: `organism-revision-review.md`.
- Final: minor (deferred): cavity-area metadata names conservative clear-aperture
  probes as cavity areas; these are not full manufactured recess measurements.
- Final: Ruling: artistic acceptance — actual images support the revised direction,
  but the user decides whether ambiguity/intricacy succeeds — cost if wrong:
  another geometry iteration and new cuts; do not cut solely on test success.
- Final: Ruling: clip selection/retention — positive clips are required; supplied
  envelopes do not approve a specific pin — cost if wrong: joint/hardware redesign.
- Final: Ruling: physical fit/load/anchors/preload/wear/handling — digital candidate
  only, all physical checks NOT RUN — cost if wrong: failed fit, unsafe installation
  or damaged parts; prototype before fabrication/installation decisions.
- Final: Ruling: manual access/continuous paths — bench cap/rib sequence documented,
  only whole-module translation samples verified — cost if wrong: altered joints,
  clearances, cradle or assembly sequence after physical access trials.
- Final: Ruling: real browser/hosts/projector — static resources, HTTP and UI logic
  verified, actual rendering/compilation/calibration NOT RUN — cost if wrong:
  viewer, host-resource or projection-mapping corrections after runtime tests.
