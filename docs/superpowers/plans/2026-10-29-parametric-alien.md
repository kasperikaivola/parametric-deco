# Parametric alien implementation plan

> Execute inline with superpowers:executing-plans; AGENTS.md requires one final
> complete review, no per-task review dispatch.

**Goal:** Numerically configurable alien composition, four limbs by default.
**Architecture:** Strict CreatureMask config, settings-aware profiles/root recipes,
shared validated planar-part generator and v3 immutable inventory. Existing preview
and export pipeline consumes actual generated assembly for each configuration.
**Tech stack:** existing Python/Shapely/OCP/trimesh/Pillow stack.
**Spec:** ../specs/2026-10-29-parametric-alien-design.md

## Constraints / review focus

No hidden fixed limbs/ribs/cavities; no silently accepted unused controls.
Count endpoints/odd counts, bool/fraction/NaN rejection, actual inventory identities,
backing/root connectivity, minimum slot bearing and material-stock separation.
All changed manufacture needs new cuts. Limits are explicit, no universal fitter.

- [x] Config tests RED for numeric controls and strict types; implement dataclass,
  parsing/validation and documented defaults. Add count/shape-change rejection tests.
- [x] Profile/count tests RED; parameterise cavity selection, layer/rib count, scale,
  reach/width/height/asymmetry and root/module recipes. Produce coarse front/oblique
  study of four-limb default before full joins. Inspect silhouette and revise if horns.
- [x] Assembly tests RED for2/4/6 modules and variable counts, dynamic backing/roots,
  coherent removal and unchanged-inventory poses. Update geometry, assembly, views
  and evidence helpers for v3. Check invalid combinations fail honestly.
- [x] Build/export2-,4-,6-limb examples and both default poses; atlas/GLB/SVG IDs and
  inventory checks. Generate actual CAD views, update docs/config table/galleries.
- [x] Full pytest, CLI harness, Ruff/JS/HTTP checks. One final independent review;
  material fixes verified without re-review. Push to existing PR #3, do not merge.

Results and deferred limits: [execution record](../../implementation/parametric-alien-progress.md).
