# Final whole-change review — ambiguous organism revision

Single independent review of `5e187cb..ddf24f7`, after implementation, read-only.
The reviewer inspected actual front, three-quarter, oblique, rib-joint and raised
CAD views, source, tests and generated evidence. No task-level reviews were run.

## Findings

Critical: none. Important: none.

Minor (deferred): `creature_assembly.py` reports `cavity_areas_mm2` from conservative
`eye_voids(0.75)` obstruction probes, rather than the manufactured cavity cuts.
The first reported area is 1495.37 mm² while its initial `eye_voids(1.06)` cut is
3049.69 mm²; upper head layers enlarge the openings further. The probe correctly
checks a common clear passage, but the metadata name can be mistaken for the full
recess area. Future clarification should rename the probe metric or report both.
Geometry, inventory and reuse evidence are unaffected. No minor fix pass was run.

## Review evidence and assessment

The six varied recesses, central opening and scalloped perimeter materially replace
the two-socket helmet reading. Four coherent curls remain legible. Transverse ribs
supply real oblique anatomy. Broad central terraces and strong bilateral structure
remain visible artistic tradeoffs; tests alone do not establish artistic acceptance.

The rib/key geometry has real cap slots, shoulders, tab windows, headed keys and
clip holes. Loaded crown cap/preceding plate Z ranges are 94–100 / 70–76 mm, tab
bottom 76 mm, key 82–88 mm. Jaw values are 76–82 / 52–58 mm, tab bottom 58 mm, key
64–70 mm. These agree with the prescribed 4t cap separation and 3t tab/gap.
Both postures contain 189 instances / 56 definitions and matching physical IDs,
revisions and manufactured geometry. Old inventory rejection is explicit.

Documentation requires 24 positive clips, identifies their geometry as clearance
proxies, and leaves selection, security, handling and actual access unverified.
The final suite confirms 73 passed, 1 explicit missing-host skip in 411.90 s.

Verdict: ready for review as a digital physical-test candidate. No structural,
fabrication, host-runtime or automatic-merge approval is implied.

## Declined judgments

- Final artistic acceptance or equivalence to the reference installation.
- Clip selection and reliable positive retention.
- Physical fit, stiffness, load capacity, wall anchors, wear, preload and handling.
- Real tool/finger access or continuous assembly/removal feasibility.
- Actual browser rendering, Wire/Arena execution and projector performance.

Implementer rulings and costs are recorded in `organism-revision-progress.md`.
