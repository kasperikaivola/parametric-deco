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
