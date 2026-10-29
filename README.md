# Parametric Deco

A Python CAD prototype for one reconfigurable plywood sculpture, with immutable
part inventory, laser contours, identified assembly geometry and face-atlas ISF
resources for Resolume Wire/Arena.

The default envelope is 1,000 × 1,000 × 200 mm including backing, rear clearance
and hardware. Nominal plywood is 6 mm. Grade/finish are optional; white paint is
not required. Dimensions do not scale stock thickness, holes or slot clearance.

## Run

Python 3.11–3.13 is supported; validation used Python 3.12.14 and a clean Python 3.11.17 environment.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
parametric-deco validate examples/single-module.json
parametric-deco build examples/intertwined.json --out build/intertwined
parametric-deco preview build/intertwined
parametric-deco visuals build/intertwined --out build/visuals
parametric-deco reconfigure examples/reconfigured.json --inventory build/intertwined/inventory.json --out build/reconfigured
python -m pytest -q -rs
python -m ruff check .
```

On Windows, activate with `.venv\Scripts\activate`. See [all CLI examples](docs/implementation/cli.md).

Outputs: individual nominal SVGs and quantity manifest, fit coupon, scale check,
assembly/inventory JSON, named GLB (metres), offline orbit/identify/explode viewer,
front/oblique/side/section/exploded PNGs, validation report, and numbered assembly/removal
instructions. An optional cutting bed enables conservative shelf placement;
oversized parts fail rather than shrink. Unknown bed size gives individual cuts.

The new [radial weave](docs/implementation/radial-weave.md) is the digital artwork
candidate: two curved paths, a 360 mm central opening, twelve removable modules
and six alternating over/under crossings. Build `examples/radial-weave.json`;
use `examples/radial-weave-reconfigured.json` with its saved inventory for the
second arrangement. The earlier `examples/intertwined.json` remains a mechanical
study. Physical and host validation gates remain open.

Reconfiguration uses immutable manufactured definitions and explicit physical
instance assignments; the example exchanges compatible ribs between modules.
Default atlases select broad faces before packing and allocate pixels according
to physical size. Optional exterior/all-face or explicit selections are available.

![Radial weave CAD oblique view](docs/implementation/images/radial-weave-oblique.png)

## Ambiguous organism example

The [organism example](docs/implementation/creature-mask.md) combines six unequal,
hooked recesses around an irregular central opening with a scalloped shell and
four sweeping appendages. There is no solid nose ridge or helmet dome. Open channels
and 24 shaped transverse ribs supply internal anatomy, alongside selective broad
projection surfaces. The planar ribs use cap slots, headed keys and required
retaining clips; five coherent modules bolt to the backing. Detached stacks need
a support tray and compression. The radial weave remains a separate example.

This revision requires **new cuts**: inventory family `creature-organism-v2` rejects
the earlier literal mask's inventory. The `creature-mask` example filenames remain
stable. Rest/raised poses within v2 reuse the same manufactured parts.

```sh
parametric-deco build examples/creature-mask.json --out build/creature-mask
parametric-deco reconfigure examples/creature-mask-raised.json --inventory build/creature-mask/inventory.json --out build/creature-mask-raised
parametric-deco visuals build/creature-mask --out build/creature-mask-visuals --visible-only
```

### Inspect the 3D structure

These images come from the actual CAD. The three-quarter view shows transverse ribs
and stand-off from the backing; the exploded view separates lower plates from cap/rib subassemblies
for inspection (the offsets are illustrative, not assembly motion).

| Front silhouette | Three-quarter: depth and anatomy |
| --- | --- |
| ![Creature mask CAD front](docs/implementation/images/creature-mask/creature-mask-front.png) | ![Organism actual CAD three-quarter](docs/implementation/images/creature-mask/creature-mask-three-quarter.png) |

| Side: plate spacing | Exploded: internal structure |
| --- | --- |
| ![Creature mask CAD side](docs/implementation/images/creature-mask/creature-mask-side.png) | ![Creature mask CAD exploded](docs/implementation/images/creature-mask/creature-mask-exploded.png) |

For a **live rotatable view**, build the example using the command above, then run:

```sh
parametric-deco preview build/creature-mask
```

Open **http://127.0.0.1:8765/preview/** in your browser. Drag to rotate, scroll to
zoom, and click a part to identify it. Use **Explode** to separate the layers,
uncheck **Backplate** to inspect the webs and spacers, or expand **Part visibility**
to hide individual parts. **Front**, **Side** and **Perspective** reset the angle.
Stop the local server with Ctrl+C. The viewer is bundled with each build and needs
no external JavaScript service; GitHub's README itself cannot run it.

You can also open the generated `build/creature-mask/assembly.glb` in a GLB-capable
3D viewer. Hardware in the browser preview is a simplified clearance envelope.

## Validation boundary

This is a **software prototype and physical-test candidate**, not a load-rated
installation. A real full-length top closure blocks sampled rib withdrawals and
is clamped to the backing by two long root bolts per module. Detached modules
require a support tray and hand compression. Read the [joint sequence](docs/implementation/joint-mechanism.md)
before cutting or handling anything.

Physical fit, wear, stiffness, root hardware selection, wall anchorage and
projection trials are **NOT RUN**. Wire/Arena are unavailable here: actual shader
compilation, patch packaging, resource relocation and mapping are **NOT RUN**.
The repository supplies ISF/PNG resources and [manual host setup](docs/implementation/arena.md),
not an invented Wire patch or Arena preset. Geometric mapping belongs in Arena
and is applied once. [Validation evidence and outstanding checks](docs/implementation/validation-status.md).

## Documentation

- [Requirements](docs/requirements.md), [decisions](docs/decisions.md), [mechanical concept](docs/mechanical-design.md).
- [Architecture](docs/software-architecture.md), [prototype tests](docs/prototype-validation.md), [roadmap](docs/roadmap.md).
- [Implementation plan](docs/superpowers/plans/2026-10-27-parametric-deco-implementation.md) and [execution ledger](docs/implementation/progress.md).
- [CAD backend](docs/implementation/backend.md), [backplate](docs/implementation/backplate.md), [fabrication](docs/implementation/fabrication.md).
- [Reconfiguration](docs/implementation/reconfiguration.md), [visual data](docs/implementation/visual-data.md), [host feedback](integrations/resolume/host-feedback.md), [physical feedback](docs/implementation/physical-feedback.md).

AGENTS.md requires one whole-implementation review at the end, without task-by-task
review rounds. No standalone VJ engine, structural solver, automatic calibration
or generalized nesting optimizer is included. The owner has not selected a
project-wide licence; runtime dependencies retain their upstream licences.
