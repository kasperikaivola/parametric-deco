# Resolume integration packet

Read [manual setup](../../docs/implementation/arena.md), then generate the
per-assembly shader/PNG resources. There is no fabricated Wire patch schema
or unsupported Arena preset exporter here. Both must be authored/tested in
the real target hosts. Record results in [host-feedback.md](host-feedback.md).

### Configurable projection content

Full builds include configured `projection/projection.fs`, saved settings and the
four image inputs: `local.png`, `world.png`, `world-fine.png`, `edges.png`. Use
nearest sampling, no mipmaps and no color correction on data textures. The GUI
and ISF share their effect GLSL. Geometric mapping remains owned by Arena.

```sh
parametric-deco visuals build/my-design --out build/my-visuals --projection-config my-design.json
```

`--width`, `--height` and `--surfaces` override saved settings. Without an explicit
configuration, the command uses the build's `projection/projection.json` when it
exists. The exported settings record effective dimensions and surface mode.
`projection-selection.json` additionally records the selected tile IDs, including
explicit `--surface` or `--visible-only` selections. Calibration and legacy edge
pulse shaders remain included. Optional packing errors in full CAD exports are
recorded in `projection/error.json`; they do not prevent cutting exports.
