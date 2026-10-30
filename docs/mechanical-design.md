# Mechanical construction

All styles use connected planar plywood cuts at one measured stock thickness,
initially nominal 6 mm. Slot fit uses measured stock plus clearance, independent
of envelope sizing; laser kerf compensation is applied once in laser software.
Generated instructions identify parts, levels, fasteners and removal order.

| Style | Construction and handling |
| --- | --- |
| Laminar | Anatomical plates on paired slotted trestles; two root bolts per module. No spacer rings or individual rib clips. Support detached parts in a cradle. |
| Layered creature | Layered shells, spacer columns, alignment webs and transverse ribs. Headed retaining keys REQUIRE positive split-pin/clip stops. Service cap assemblies inverted in a padded cradle. |
| Radial weave | Curved paired spines, radial fins and upper capture rails. Remove rails before inward fin withdrawal; high modules precede low at crossings. |
| Rib study | Paired straight spines, transverse ribs and full upper closure clamped by two root bolts. Detached modules need tray support and compression. |

Root washers must bear on actual manufactured material; hardware clearance
boxes are simplified proxies. Rear access is required. Staggered mounting grids
serve the creature, radial and rib styles; laminar derives roots from anatomy.
See [design guide](design.md) for supported dimensions, assembly effort and style
parameters, and [rib-study joint detail](implementation/joint-mechanism.md).

Physical fit, wear, stiffness, bolt/clip selection, handling, backing stiffness,
wall anchorage and load capacity remain NOT RUN. Digital static collisions and
sampled translations are bounded checks, not strength or continuous-motion proof.
