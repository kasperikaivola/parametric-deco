# Ambiguous organism — candidate assembly, family v2

Physical fit, strength, cantilever stiffness, hardware, finishing and handling:
NOT RUN. Prototype one complete rib/tab/key/clip joint and one root stack first.
The generic fit coupon checks stock slot width only, not these whole joints.

All wood uses one measured thickness t (6 mm initially). Five modules use armour
plates, two alignment webs, cut-plywood root spacer rings and two root bolts each.
Levels in assembly.json are multiples of t above the backing front. Root spacers
fill every unoccupied level, making continuous compression columns to the cap.
The cap has no root-web slots and blocks outward web withdrawal. Webs register
alignment; they are not structural ratings. Bolts/hardware proxies are not final
fastener, washer or torque specifications.

## Transverse ribs and retaining keys

There are 24 unique shaped transverse ribs: seven on each crown and five on each
lower hook. Each has a 28 mm wide foot through a closed cap slot (clearance added
only to the slot). Its shoulders bear on the cap front. An individual horizontal
plywood key passes through the foot's 10 mm by t window. Key width is 10 mm; a
wider 18 mm head stops passage through the window. The far end has a 2.5 mm hole
for a REQUIRED positive split-pin/clip stop. Do not rely on key friction alone.

Select and prototype 24 suitable clips/pins. Their supplied bounding envelopes
are clearance proxies, NOT selected or fully modelled fasteners. Clip length,
head/tail shape, installation, security and tool access are NOT RUN. Nominal
proxy length is 2t with the clip positioned below the cap; confirm the real clip
can be installed and removed in that gap and cannot pass through the tab window.
The joint needs redesign if suitable hardware cannot meet that envelope.

The cap is four t above the preceding plate, leaving a three-t clear gap. The
rib tab reaches three t behind the cap. Its key occupies the middle t of that gap.
At the two root columns, extra spacer rings fill the increased cap separation.

Build the cap/rib subassembly upside down on a padded support. Insert each foot
through its labelled cap slot. Insert its headed key from the accessible underside,
then install the positive clip through its hole. Inspect shoulder seating and
key/clip engagement. Do this BEFORE placing the cap on the lower module stack.
Fins and keys are not intended to be serviced blindly between mounted layers.

## Complete modules and removal

Build the lower plate/spacer stack in a flat supported tray using actual IDs and
levels. Insert alignment webs through their closed slots. Put the supported cap,
ribs, keys and clips on top. Use two temporary root alignment rods while stacking;
maintain compression during transfer. Install lower hooks and crowns before the
central shell, whose layers overlap their roots. Secure two root bolts per module
through all plate/spacer bores and the specified backing-grid holes.

For removal, support the central shell, release its two bolts and lift outward
first. Follow composition.removal_order for complete appendages. Maintain tray
support and compression: these stacks are NOT self-locking after unbolting. To
service ribs, take the complete module to the workbench, support the lower stack
and lift off the entire cap/rib subassembly. Turn it over in a cradle to access
keys and clips. Do not suspend or carry a module by its ribs, hooks or keys.

Digital checks cover static solids, window engagement, shoulder/key bearing and
sampled whole-module +Z extraction every 12 mm through 240 mm. They do not certify
continuous assembly paths, real tool/finger access or safe detached handling.
The rib-joint image is an actual local mesh section; exploded offsets are only
identification aids. No physical load, wear or handling tests have been performed.

## Inventory and projection

Family creature-organism-v2 requires NEW CUTS compared with creature-mask-v1.
Do not reuse the old inventory merely because filenames or module IDs match.
Within v2, rest and raised_crown use the SAME manufactured inventory: move each
complete crown by its prescribed grid offset. All ribs, keys and clips move with
that module. Unique plates and ribs do not interchange across stations or sides.
Only identical definitions/revisions, including retaining keys/spacer rings and
matching webs, interchange. Changed scale, curl, thickness or clearances needs
NEW CUTS. Use existing-inventory reconfigure to verify a proposed arrangement.

Projection-visibility.json samples broad shell faces from (0,0,2000) mm using
actual extruded contours/holes. Thin rib edges can self-shadow and are not treated
as broad frontal projection targets. Use --visible-only for recommended atlas IDs.
Wire/Arena compilation, projector calibration and real illumination: NOT RUN.
