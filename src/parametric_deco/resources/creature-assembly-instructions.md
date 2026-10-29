# Creature armour — candidate assembly

Physical fit, strength, cantilever stiffness, mounting hardware, finishing and
handling: NOT RUN. Prototype a root column and slot/web interface before full cuts.
The generic fit coupon checks stock slot width only; test the actual 18 mm web
windows and root stack separately. This family uses two root bolts per module, slotted alignment webs and cut-plywood
spacer rings. It is a root-clamped stack, not a self-locking slotted skeleton.

Use assembly.json IDs and the documented layer levels; each level is one measured
plywood thickness above the backing front. Never substitute nominal thickness for
measured thickness. Spacer rings fill every root-column level not occupied by a
plate. Both columns must bear continuously from backing to cap. Two rectangular
webs register the armour's closed slots; the cap has no web slots and blocks
outward withdrawal. Webs are alignment parts, not height spacers or load ratings.

Build each module in a flat, supported tray: spacer/plate levels in order, webs
through matching closed slots, then the solid cap. Use the two root bolts as temporary alignment rods
through the root holes to preserve stack alignment. Maintain compression while
transferring to the backing. Install mandibles and crowns before the head; the head
overlaps their roots. Seat the two root bolts through the actual grid holes and
all plate/spacer holes. The exported hardware envelopes are conservative proxies,
not a bolt/washer/spacer specification or torque recommendation.

For removal, support the head in its tray and release its root bolts first. Lift
it straight outward. The exposed crown and jaw retaining bolts are then accessible;
follow composition.removal_order. Keep stacks compressed while detached: removing
the root bolts releases the clamp and parts can separate. No additional armour
covers retaining caps or the exposed head bolt heads. Digital removal paths are
sampled straight +Z translations, not a complete manual-access proof.

Rest and raised_crown reuse the SAME parts: move only each complete crown module by
its prescribed staggered-grid offset. Unique shaped plates are not interchangeable
across levels, modules or sides. Identical spacer definitions and identical webs
may interchange. Do not mirror manufactured parts. Changed scale, curl, stock,
clearance or backing requires NEW CUTS; use existing-inventory reconfigure to check.

Projection-visibility.json estimates visible broad faces for a projector at
(0,0,2000) mm using finite surface samples and actual extruded contours. It does not
certify illumination, ambient shadows or calibration. Use --visible-only for an
atlas excluding sampled hidden faces. Recalibrate after movement. Actual browser,
Wire/Arena shader compilation and projector runtime: NOT RUN.
