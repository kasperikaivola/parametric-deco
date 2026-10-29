# Flow organism assembly — physical checks NOT RUN

Use `assembly.json` composition.modules for exact plate/web IDs, root coordinates,
height and removal_order. Stock, fit and hardware have not been physically tested.

Each module is one anatomical plate on two upright plywood trestles. The 14 mm
wide top and bottom locating tongues enter closed stock-plus-clearance slots.
Trestle shoulders seat on the backing and support the plate underside. Two ordinary
through bolts clamp the plate, trestles and backing together. There are no spacer
rings or loose retaining clips. Select bolt length for backing + trestle height +
plate + washers/nut engagement, and select actual hardware/locking after a prototype.
Hardware in the GLB is a conservative clearance proxy, not a commercial fastener.

On a bench, use a cradle to hold two trestles upright, lower the plate over their
top tongues, place the supported assembly on its backing slots, insert the two
bolts and tighten with washers and nuts. Keep the assembly supported throughout.
Install lower modules before overlapping higher modules (reverse removal_order).
Rear bolt access is required; detach the backing from its installation first.

For removal, support the module, release its root bolts, and lift in +Z until bottom
tongues clear the backing. Take it to a cradle on the workbench. The trestles remain
loose when unclamped: do not carry by tips or plates without the cradle. Bench
assembly/handling and continuous paths remain NOT RUN. Numerical motion checks
sample rigid +Z translations and report dependencies; they do not test fingers,
tools, deformations or falling parts. Do not treat passing CAD checks as approval
for public installation, overhead mounting or laser fabrication.

Retain natural wood surfaces if desired; the shape does not depend on paint or
engraving. Projection atlas and ISF resources still need real Wire/Arena/projector
validation and calibration after any arrangement or size change.
