# Creature layer relief

Historical contour/material study at the pre-symmetry revision. Its area metrics
and family-specific images/evidence are not measurements of current v3 cuts.
The [current gallery](gallery.md) and [mounting revision](mounting.md) supersede
its geometry, root positions, bores, symmetry and board assumptions.

New cuts use depth-normalized contour retreats rather than almost identical
plates. Head lobes retreat by unequal amounts around the silhouette; widened
curving channels and cavity rims expose lower terraces. Limb rails taper more
strongly toward folded tips, with rounded local pads retaining closed rib-slot
bearing. The base silhouette, ambiguous unequal apertures, root compression
regions, register webs, board geometry, placement and camera transforms stay
shared with the previous design.

This is a deliberate manufacturing geometry change for newly generated parts.
Saved inventory replay uses its original immutable definitions, never regenerated
profiles. The request adapter continues to permit compatible saved cuts and crown
posture changes. New and saved cuts are not silently mixed.

Regression checks measure each head depth's area visible through all plates above
it, cap/base net area ratios, connected single polygons at layer-count and shape
boundaries, a conservative 3 mm contour erosion to detect head necks below
6 mm, and the existing physical slot/key/root and through-aperture checks.
Material evidence compares **net plywood polygon area summed by physical instance**
against master `2f88791`; it includes holes and repeated spacers. It does not claim
stock-sheet or nesting savings. Actual sheet consumption depends on cutting layout.

The committed creature images and gallery front/three-quarter views are rendered
from actual exported geometry, using the existing matched cameras. Updated
`creature-mask-evidence.json` and `gallery-evidence.json` record assembly validation
and provenance. Physical fit, stiffness, hardware/clip security, handling, wall
anchors, and Wire/Arena/projector runtime remain **NOT RUN**.
