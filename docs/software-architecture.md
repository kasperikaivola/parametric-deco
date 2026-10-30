# Software architecture

`DesignConfig` is the schema-v2 public recipe: a style and one typed parameters
object plus shared envelope/manufacturing settings. `config_from_dict` rejects
unknown fields and old generation requests; `validate_config` checks ranges.
`assembly.assemble` dispatches to laminar, layered-creature, radial-weave or the
rib-study adapter. Each keeps its own topology, joinery and geometry checks.
See [design guide](design.md) for parameters, examples and limits.

Shared `PartDefinition` revisions are immutable manufactured contours; physical
`PartInstance` IDs place those definitions. `Inventory` persists these cuts and
style-specific placement templates. Existing-inventory mode places saved geometry
without generation; fingerprints, layouts and compatibility are revalidated.
Generation schema v2 does not change inventory schema or geometry identity.

build123d/OCP supplies solids, Shapely planar cuts, and trimesh mesh interchange.
All adapters return `BuildResult` with assembly, fabrication parts, inventory,
provenance and a validation report. `export.manifest.export_build` supplies the
shared SVG/JSON/GLB/inspection/preview pipeline. GLB uses metres; nominal geometry
and scene JSON use millimetres. Export staging and manifests protect unrelated
files, obsolete modified outputs and symlink/path boundaries.

The offline viewer reads the same identified assembly. The projection pipeline
selects faces before atlas packing, keeps physical surface IDs and exports ISF,
coordinate/ID textures and masks. Wire hosts/packages shaders; Arena maps once.
Calibration remains separate from artwork geometry. No fabricated host preset,
custom VJ runtime, structural solver or exhaustive motion proof is provided.

Run `python -m pytest -q -rs`, `python -m ruff check .` and
`python tests/run_examples.py`; CI repeats these on Python 3.11. Physical and
proprietary host checks remain [NOT RUN](implementation/validation-status.md).
