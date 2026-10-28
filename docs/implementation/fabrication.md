# Fabrication outputs — prototype candidate

cuts/ contains one closed SVG per definition/revision, the fit coupon, and
100 mm scale marks. manifest.json lists quantities, fingerprint, nominal
thickness, transforms (assembly.json), dependency versions and warnings.
Use counts from the manifest: one definition file is **not** one physical
copy. Inventory carries individually identified instances, including unassigned stock
retained from previous arrangements. assembly.json lists only placed instances.
Nominal thickness describes the purchased stock; solids, physical thickness,
slot widths, backing offsets and depth checks use measured thickness. When no
measurement exists, the explicit assumed/unmeasured default is 6 mm.

SVG units and viewBox are millimetres. Cut contours are red, closed and
unoffset; engravings are blue on a separate group. Convert text to outlines
in laser software if its SVG text handling is unreliable. Remove no hole
or slot loops. Apply kerf compensation **only in laser software**, once.
No driver/toolpath/laser execution is included. Verify the scale-check and
fit coupon before any full-size cut; measured stock and intended finish
can change fit even with the nominal 0.2 mm clearance.

Unknown bed size produces individual parts and explicitly no validated
nested sheet. If cutting_bed is supplied, a deterministic shelf placement
uses conservative bounds, configured gaps and no rotations or shrinking.
Oversized parts (including the 1 m backing) fail. No structural segmentation
joint is invented to make a sheet fit. Sheet placement validity establishes
geometric fit only, not material grain, machine margins or a safe toolpath.

GLB converts mm to metres at the export boundary and keeps identified nodes.
scene.json remains millimetres and feeds the offline canvas viewer. Hardware
is shown as labelled conservative cylindrical envelopes (washer radius for
the full bolt length), not an engineering fastener model. It is not included
as a wooden cutting part.

Use assembly-instructions.md plus joint-mechanism.md for numbered assembly
and supported removal. Inspect front, side and exploded views. Physical
fit, closure contact, torsion, wear, detachment and mounting tests NOT RUN.
