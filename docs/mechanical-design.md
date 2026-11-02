# Mechanical construction

All styles use connected planar plywood cuts at one measured stock thickness,
initially nominal 6 mm. Slot fit uses measured stock plus clearance, independent
of envelope sizing; laser kerf compensation is applied once in laser software.
Generated instructions identify parts, levels, fasteners and removal order.

| Style | Construction and handling |
| --- | --- |
| Laminar | Anatomical plates on separated direct grid-aligned end clamps with rigid metal tube standoffs; no unique board seats or offset adapters. Support detached parts in a cradle. |
| Layered creature | Layered shells, original root spacer columns, alignment webs and transverse ribs, plus separated end clamps and gap-filling tube columns for every broad layer. Headed retaining keys REQUIRE positive split-pin/clip stops. Service cap assemblies inverted in a padded cradle. |
| Radial weave | Curved paired spines, radial fins and upper capture rails on separated end clamps; some axes share one segmented compression stack between neighboring modules. Low fins stop at the capture rail. Remove rails before inward fin withdrawal; high modules precede low at crossings. |
| Rib study | Paired straight spines, transverse ribs and full upper closure with separated near-root/distal tube clamps. Detached modules need tray support and compression. |

Every deco mounting axis is directly coaxial with the same physical board grid at matching stock size/settings. Washers bear on real material and rigid tubes fill every actual gap. End-clamp geometry is modeled; original root/clip envelopes remain simplified. Rear access is required. See [current mounting evidence](implementation/mounting.md) and the [all-example gallery](implementation/gallery.md).
See [design guide](design.md) for supported dimensions, assembly effort and style
parameters, and [rib-study joint detail](implementation/joint-mechanism.md).

Physical fit, wear, stiffness, bolt/clip selection, handling, backing stiffness,
wall anchorage and load capacity remain NOT RUN. Digital static collisions and
sampled translations are bounded checks, not strength or continuous-motion proof.
