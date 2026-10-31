# Validation boundary and reproduction

Run the current software checks from the repository root:

```sh
python -m pytest -q -rs
python -m ruff check .
python tests/run_examples.py
node --check src/parametric_deco/resources/viewer.js
```

CI repeats the Python suite, lint and example harness on Python 3.11. The explicit
host/offscreen rendering skip is an unavailable runtime, never a pass. Current
suite results belong to the tested commit/CI run rather than a historical ledger.

| Check | Evidence / boundary |
| --- | --- |
| Config/style schema and inventory identities | Automated strict-field, round-trip, saved-definition, fingerprint and layout tests |
| Geometry and manufacturing | CAD solids, contours, slot/bearing/ligament checks, static collisions and envelope; style-specific checks in tests |
| Withdrawal and assembly order | Sampled translations and dependency checks only; no exhaustive motion proof |
| Exports, preview and projection data | SVG/GLB/JSON, overwrite/path checks, atlas/ISF references, localhost preview HTTP and JS logic harness |
| Actual browser rasterization / pointer interaction | NOT RUN in this environment |
| Physical fit, wear, stiffness, hardware/clip security, handling and wall anchors | NOT RUN; see physical-feedback.md |
| Wire/Arena compilation, packaging, relocation, resource values and mapping | NOT RUN; see arena.md and ../../integrations/resolume/host-feedback.md |
| Structural load rating and exhaustive rigid-body disassembly | NOT RUN |

Actual CAD imagery is in the [design guide](../design.md). Existing generated
[laminar](flow-organism-evidence.json), [creature](creature-mask-evidence.json) and
[radial](radial-weave-evidence.json) evidence describes the generated geometry at its recorded revision, not
physical/host approval. Rebuild outputs to inspect a current request.

The [current gallery evidence](gallery-evidence.json) records shared front/three-quarter
assembly provenance for the centered creature and 90° radial example. The older
radial family evidence records its original 0°/180° configurations; it is a
historical snapshot, not the current gallery's 90°/270° configurations.

The [complete current gallery](gallery.md) covers all 15 example configurations
and four generators. Its support evidence records opposite end regions on actual
panel spans, direct universal-grid bores, every compression-tube interval, added
pad solid clearances and all-part routes to the board. Nominal-size examples share
one physical board fingerprint. Older family evidence is historical; current
support construction and its explicit physical limitations are in [mounting](mounting.md).

The earlier `d360100` implementation ledger (43 + 13 + two focused checks)
validated hardware, board identity, static clearances and the radial service
corridors, but its rectangle-only end criterion did not establish actual curled
root/distal coverage. That end-region proof is superseded by `path-end-clamps-v2`.
The current audit reconstructs laminar/creature medial paths, actual poses, radial
arcs and manufactured straight spans, independently of saved support claims.
Existing useful intermediate axes remain, with true-end grid columns added.

The focused fix regressions include a curled jaw whose rectangle extrema remain
supported while its actual 228 mm distal path is unbraced, and rejection of that
older stock without mutation/remachining. They also check all-family paths,
common board/grid axes, tubes/webs, shared stacks and immutable inventory roles.
The [cached-model report](support-validation.json) records all 15 final path/grid/
load-path checks and quantitative endpoint/offset/remaining-path measurements.
Physical fit/strength and Wire/Arena remain **NOT RUN**. No second complete review,
full local suite, full CLI harness, or CI run is part of this focused fix.

The focused path-end correction passed **24 tests**, including independent path
reconstruction for all 15 example configurations, the curled-jaw negative case,
and rejection of deficient v1 stock without changes. The final cached audit
passed all 15 path/grid/support records, all 60 matched/mounting images and hashes,
configuration/assembly provenance, current links, and all three unchanged-inventory
replays. Eight variants required changed cuts/hardware; seven reused physically
identical geometry and their normal renders. No full-suite, full CLI, second
complete-review, or CI run was performed for this correction.
