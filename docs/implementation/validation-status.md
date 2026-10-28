# Validation evidence

Implementation branch: implement-parametric-deco-v1.

Initial delivery verification (before owner PR feedback, 2026-10-28): **44 passed, 1 explicit host skip**
on clean Python 3.11.17 in 108.10 seconds. Full documented CLI/localhost preview
harness PASS, Ruff PASS, whitespace checks PASS, all 66 locked dependencies
compatible. The single review and five fixes are in [final-review.md](final-review.md). The final commit and any
whole-branch review findings are recorded in progress.md and Git history.
This document separates reproducible software evidence from unperformed tests.

| Check | Status | Evidence |
| --- | --- | --- |
| Isolated dependency installation | PASS | Python 3.11.17 clean final environment; requirements.lock; 66 compatible packages |
| CAD solid / STEP hole roundtrip | PASS | test_cad_smoke.py, 100 × 40 × 6 mm plate, 6.5 mm hole |
| Config, immutable inventory and revision checks | PASS | test_config.py, test_model.py, test_inventory.py |
| Polygon/grid/root containment | PASS | test_backplate.py and inspected top view |
| Candidate joint translations and closure obstruction | PASS (sampled only) | test_module.py: 0/5/20/50/100 mm open path, +1 mm blocked by real closure |
| Static solid collision/envelope/root-grid checks | PASS | test_assembly.py, test_integration.py, both arrangements |
| SVG, GLB, quantity/sheet/overwrite checks | PASS | test_exports.py, test_cli.py |
| Asymmetric atlas, phase, IDs and ISF metadata/reference | PASS | test_atlas.py, test_isf.py |
| Preview JS syntax and UI logic | PASS | node --check; tests/test_preview.js against generated scene |
| Browser rasterization / pointer interaction | NOT RUN | Chromium archive downloads failed; no installed browser executable |
| Physical fit/wear/stiffness/root/tool/tray handling | NOT RUN | physical-feedback.md |
| Wire/Arena installed versions / shader compilation | NOT RUN | No proprietary host available; integrations/resolume/host-feedback.md |
| Resource relocation, host data values, mapping/projection | NOT RUN | arena.md gives reproducible manual host setup |
| Exhaustive rigid-body disassembly / structural load rating | NOT RUN | Outside sampled translation/geometry checks |

Software commands and final full-suite results are recorded in progress.md.
Host/offscreen shader rendering is one explicit pytest skip, not a pass.

## Owner-feedback verification

**49 passed / 1 explicit host-rendering skip**, Python 3.12.14, 124.08 seconds.
All CLI examples, explicit cross-module assignments and broad/exterior/selected
atlas generation pass, along with Ruff/format/whitespace checks. See
[PR feedback resolutions](pr-feedback.md). Hosted Python 3.11 CI is checked before
merging. **Task 8 / integrated artwork remains INCOMPLETE**, independently of the
mechanical and software test results.

## Reproduce

Use the setup and commands in cli.md; CI runs tests, Ruff and generated-example
smoke commands on Python 3.11. The initial installation used Python 3.12.14;
final post-review verification used an actual clean Python 3.11.17 environment. Remote CI status must be checked on GitHub.

Front, exploded and actual XZ mesh-section images below were generated from the
same assembly records, inspected and kept as compact representative evidence:

- [Front](images/front.png)
- [Exploded](images/exploded.png)
- [Joint section](images/joint-section.png)

The mechanical study coordinates are in examples/intertwined.json. The first
layout's collision evidence is retained in progress/reconfiguration documentation;
those collisions were corrected, not ignored. Curved profiles are faceted nominal
contours and can be refined later without mutating existing inventory revisions.

The coupon covers total fit clearances 0.0–0.4 mm in 0.1 mm steps. Generated
cuts/ contains the root/closure and spine/rib SVGs, coupon and 100 mm scale marks.
Generated views/ contains closure contact sections and exploded instructions.
No laser bed or physical measurements were supplied; nested sheets and physical
approval therefore remain separate decisions.


**Integrated artwork / Task 8: INCOMPLETE.** Existing images and module-count tests
only demonstrate mechanical layout and reconfiguration. They do not establish
continuous contours or apparent intertwining. Owner PR feedback corrections and
updated software results are recorded in progress.md.
