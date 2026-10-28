# Radial weave — candidate assembly and handling

PHYSICAL FIT, LOAD, STIFFNESS AND DETACHED HANDLING: NOT RUN.
The digital checks are sampled motions and nominal geometry. Prototype one joint
and one root before committing to a full cut. The legacy module coupon does not
validate the radial tongue/window mechanism; test actual radial fin/spine/rail cuts.

On a supported bench, arrange the two identical curved spines at their documented
heights (low 20/44 mm, high 102/126 mm above the backing front). Keep the module
supported. Slide each identified rib radially outward from the central opening
into both open spine slots. The inverse removal direction is radially inward.
Ribs and spines are separate manufactured parts; do not bend a curved spine.

With all fins seated, lower the curved capture rail axially over the twelve-mm
radial tongues. The closed rail windows obstruct inward rib withdrawal. Check
window seating on every fin; the rail is a separate loose part until clamped.
There are no individual rib screws. Two root bolts through the selected backing
grid holes and both spine/rail pads clamp the module. The manifest contains
conservative hardware bounds, not fastener sizes, strength or torque instructions.
The high roots require long bolts: obtain a prototype-derived bolt/spacer and
wall-anchor design before mounting. Backing stiffness around the opening is untested.

Install low modules before high modules, using the reverse of composition.removal_order
in assembly.json. Remove high modules before low modules, following that exact order.
Remove the root bolts first, maintain closure compression and use a support tray
while lifting the complete module straight outward (+Z). The sampled digital path
extends 240 mm; it does not prove all rigid-body motions or manual access.
Do not lift by a fin or allow a detached capture rail to lift off its tongues.

For the second arrangement, disassemble on a bench. Rotate placement 180 degrees
and move only the compatible central physical fins according to the supplied
reconfiguration JSON. Preserve physical IDs and revisions. Generate with
`reconfigure --inventory`, not `build`, to verify reuse of the same stock.
Regenerate atlases from that assembly. Wire/Arena and projector calibration: NOT RUN.
