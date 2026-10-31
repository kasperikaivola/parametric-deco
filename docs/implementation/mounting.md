# Universal board and separated end supports

The current manufacturing revision is `triangular-symmetric-mounts-v3` on
`universal-triangular-board-v3`. Every compatible deco uses **the exact same physical
board**, not a family-specific outline, aperture or seat pattern. Default stock
is a 1000 × 1000 mm envelope-fitted octagon, rotated 22.5°, 6 mm thick. Its bores
are 6.5 mm on a 50 × 25√3 mm equilateral triangular grid (row pitch ≈43.301270 mm), alternate rows shifted 25 mm, origin (0,0),
including negative-row parity and the same 18.25 mm bore-centre edge exclusion.
Changing board size, stock thickness, polygon controls or grid controls selects
a different physical board; the 800 and 1400 mm laminar presets are explicitly
separate stock sizes. All nominal-size presets share one board fingerprint.

No extra board drilling, family-specific eye/aperture/trestle cuts, or offset
adapters are required. Each mounting bore in a deco is directly coaxial with an
existing board grid hole. Connected construction material is added locally to
some deco outlines where necessary to carry a grid bore; these pads are part of
the laser-cut deco itself. They retain the decorative channels and actual rib
clearances. The universal board stays dark behind the artwork openings. Its
full unused hole grid is visible in the actual CAD gallery and mounting views with transparent deco contours and station/module IDs.


The C3 laminar presets repeat one canonical 120° motif, including all contours,
channels, layer heights, integral pads, bores and hardware. Uniform fitting stays
about the common grid origin. The explicitly named bilateral preset instead uses
exact reflected pairs. Creature paired limbs, head layers and complete clamp
stacks are exact X→−X reflections. Candidate support orbits are accepted together,
then combined trial machining checks connectivity and7 mm bore ligaments. Finished
extruded material and layer-specific support/hardware counterparts are audited
independently; a symmetric silhouette alone does not pass. Long creature limbs
also receive an intermediate bend support where their path exceeds 350 mm.

Earlier square-row grid inventories remain immutable and are rejected for this
revision with a new-cuts requirement. New repeated laminar sectors share one
physical cut definition; their supported placement is a rigid 120° copy. New
rib-study cuts omit obsolete original root mounting bores and root bolts: closed
key/retainer apertures remain functional, and separated direct end clamps carry
the captured spine/rib assembly. No replacement adapters are introduced.

## Long panels and real compression paths

A pair of screws in one root patch is not a separated support system. For
laminar plates, end regions follow each generated `Lobe.path`; for creature limbs,
they follow the actual curled `limb_recipe`/`smooth` path including scale, centering
and the assembly's real placement transform. A support must reach each outer 30%
region along that path and lie within 60 mm of it, so a distant neighboring branch
cannot supply a misleading projection. Existing intermediate supports are retained
and actual root/distal columns are added where needed. Their connected integral
material, 7 mm webs, washers, tubes and global clearances are checked normally.

Radial modules are audited along their angular arc, with a 0.315 end-region
fraction accommodating the existing 1–2 mm grid/arc boundary discrepancy. Straight
rib-study spans derive from actual manufactured spine length, not a changed recipe.
Broad head shells use a planar spread criterion, rather than a fictitious limb
path. For nonsymmetric legacy layouts rectangle extrema may seed intermediate supports;
they are **not** evidence that a curved root or distal tail is supported.

The validator reconstructs these paths from family geometry and current poses,
independently of saved station/span claims. The evidence records path lengths,
actual endpoints, every station's fraction and transverse offset, qualifying
root/distal support IDs, and residual path lengths. Cyan R/T traces in mounting
views identify the actual medial paths. These dimensions describe nominal
attachment geometry, not a tested bending stiffness or load rating.

One axis can support multiple stacked layers when it passes through their real
material. Some radial and laminar axes deliberately clamp overlapping modules on one
physical M6 shaft: each involved rail/spine has its own coaxial bore, and rigid
tube segments fill every gap through the complete combined stack. This couples
those modules until their common clamp is removed; it is one hardware schedule,
not two coincident fasteners. Where this axis reuses an original radial root bore,
the combined stack replaces that root bolt; no second coincident bolt/envelope is
retained. The evidence names these replaced root references. Both supported radial poses rotate the coupled
modules together without changing cuts; laminar modules support identical replay.
Support all coupled layers and remove their common clamp before extraction. Long rails can require additional axes because their end regions differ.

The mechanical stack at each station is rear M6 bolt head, rear 1.5 mm washer,
board, **rigid metal compression tube in every gap**, drilled panel(s), front
1.5 mm washer and M6 locking nut. Tube OD is 12 mm and ID matches the grid bore;
nominal shaft diameter is 6 mm, washer OD is 18 mm. Tube cut lengths and poses are
modeled individually, including the board-to-first-layer gap and every gap between
layers. Head/nut envelopes are modeled; threads and commercial locking features
are not. Metal pieces are identified purchased hardware, excluded from plywood
laser cuts and projection surfaces. `mounting-hardware.json` is the purchase/cut
schedule in a build export.

Laminar's former central trestles and unique board slots are replaced by these
direct end clamps. Creature armour layers and radial rails/spines use the same
system. Rib-study closures now have a real distal clamp in addition to their
near-root end clamp. Existing captured ribs, webs, small spacers and retainers
have explicit connection paths through these board-clamped structural parts;
they do not each need independent board bolts.

## Upright parts and contour changes

Radial low fins are trimmed at their 70 mm capture rail, retaining their captured
12 mm tongue. This removes the earlier decorative crests up to 82 mm above every
bearing. High fins retain 102/126/152 mm notch/capture planes; high end fins also
bear directly on the board at their bottom feet. Rib-study spines are captured by
closure tongues near their longitudinal ends; transverse ribs retain their paired
spine notches and top capture. Creature's smaller decorative upright fins retain
the 28 mm cap seat, shoulder, transverse key and specified positive clip. Those
fins have intentional decorative projection beyond their seat; the gallery's
upright-joinery records identify their actual dimensions and contact scheme.
Physical bending stiffness is not inferred from connection counts.

Added radial construction pads are routed against actual upright material
cross-sections at the corresponding slab depth, and spine pads preserve the
complete 0..80 mm inward fin service corridor. Capture rails keep their closed
tongue windows and are removed for fin servicing. New material is checked with
solid intersection tests, not just bore-axis distances, so a bridge cannot fill an
open rib notch. Bores/washer bearings, finished edge web, every tube interval,
shaft/washer/part clearances, rigid transforms, exact grid alignment and all-parts
connection reachability are separately checked. See the [full gallery](gallery.md)
and [machine-readable evidence](gallery-evidence.json) for every example.

## Inventory and validation scope

Old manufactured parts are never resized, drilled or silently assigned new
revisions. Earlier rectangle-only stock that misses actual root/distal regions
requires **new cuts**; it is rejected rather than silently drilled. Safe v1 stock
may replay unchanged only after the independent path audit passes.
A new inventory stores its final physical part revisions and a signed digital
pre-machining placement template separately. The template is historical design
input, not another set of physical stock. Reconfiguration places the saved final
cuts and checks their bores against the unchanged board. The raised creature,
180° radial permutation and rib-study example reconfiguration reuse their
source inventory. Unsupported off-grid, obstructed or unmachined placements fail
validation. Changing mounting/grid/material/board settings requires new cuts.

The software checks nominal geometry and sampled extraction only. Bolt preload,
commercial fit, material stiffness, locking, load capacity, wear, handling and
installation anchorage remain **physical NOT RUN**. Wire/Arena/projector checks
remain **NOT RUN**. Support all affected layers in a cradle before releasing any
root or end clamp. This is a prototype design, not a load-rated installation.

The [v3 cached geometry/view audit](symmetry-grid-validation.json) binds all 15
records and60 view images to their actual assembly hashes, including artwork-only
centering and unchanged-inventory replays. [Fresh radial joint evidence](radial-v3-joint-evidence.json)
checks all90 ribs on both new24-axis poses: inward 0/10/40/80 mm spine clearance
with rails removed, then 1 mm capture against installed rails. This remains sampled
nominal geometry evidence, not an exhaustive motion or physical fit proof.
