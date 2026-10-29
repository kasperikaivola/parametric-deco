# Flow organism generator

This revision supersedes the mask family's artistic direction. `organism-low.json`
is the production **starting study**, not fabrication approval. It uses six separate
branching laminae around a rotating focal field, with curved internal divisions,
rounded appendages and unequal relief levels. There is no central mask plate.
The negative spaces support several possible eye/face readings without adding pupils,
a nose, a mouth or a helmet dome. The shape exists in the plywood, without paint,
engraving or projected animation.

The vocabulary is deliberately bounded: flowing branched ribbons and nested lobes,
with whorled or staggered bilateral fields. It is not a topology solver. The
whorled example retains a repeated ornamental rhythm; artistic success is a visual
judgment, independent of the validation report. This is a smaller and more open
sculpture than the festival reference, not a reproduction of its complexity.

## Geometry and controls

`geometry/organism.py` provides one variable-width rounded sweep primitive. Smooth
paths, swelling, taper, angularity modulation and curved branching divisions form
the anatomy. A field places and orients these primitives; it does not select from
a cavity coordinate palette or a separate hard-coded layout for each example.
`organism_assembly.py` finds substantial mounting patches in the actual material,
creates slotted plywood trestles and backing, and validates the resulting assembly.

Composition and style shape the central regions as well as appendages. Curvature
changes the full cross-path coordinates and connecting curves, not one endpoint.
Width/height fit the primary anatomical field before fixed-size joinery is added.
Relief depth determines the actual heights of trestles and overlapping plates.
The curve field varies complete primary proportions and inter-region flow, rather
than rotating one identical hook. Primary modules occupy distinct relief levels;
secondary saddles take shorter path sections. Complexity adds exposed inner lobes,
integral curved divisions and longitudinal
channels; major primary exteriors, primary paths and their relief relationships
remain unchanged. Channels accumulate in fixed path intervals; increasing their
count does not exchange an existing opening for one elsewhere.

| Group | JSON field | Default / range | Actual geometry effect |
| --- | --- | --- | --- |
| Composition | `organism.arrangement` | `whorl`, `bilateral` | Orbiting focal field or staggered paired rows |
| Composition | `focal_count` | 6 / integers 4–8 | Number of primary focal/appendage modules |
| Composition | `phase_deg` | 17 / −180–180 | Field orientation and its controlled variations |
| Composition | `spread` | 1 / 0.85–1.15 | Relative focal spacing before fitting the silhouette |
| Composition | `symmetry` | `rotational`, `bilateral`, `none` | Repeated orientation, reflected local paths, or individually tilted forms |
| Complexity | `complexity` | 0 / integers 0–2 | Coordinated secondary lobes, segmentation and channels |
| Override | `secondary_lobes` | null / integers 0–1 | Null follows complexity; 1 adds an inner lobe per primary region |
| Override | `segmentation` | null / integers 0–5 | Integral curved divisions in each appendage, 2/3/4 by complexity |
| Override | `channels` | null / integers 0–3 | Longitudinal cut channels, 1/2/3 by complexity |
| Size | `envelope.width_mm`, `height_mm` | 1000 / 800–1400 | Generated composition size, with a 2 mm XY boundary allowance |
| Size | `envelope.depth_mm` | 200 / 120–240 | Actual relief and support heights; retains rear/hardware allowance |
| Style | `curvature` | 1 / 0.7–1.3 | Curvature over main paths, branches and divisions |
| Style | `taper` | 1 / 0.7–1.3 | Width distribution along paths |
| Style | `swelling` | 1 / 0.8–1.2 | Broadening and anatomical weight |
| Style | `angularity` | 0 / 0–0.6 | Continuous modulation of sweep radius along the path |
| Style | `asymmetry` | 0.12 / 0–0.2 | Controlled differences in reach, orientation and curvature |

Ranges are exploration bounds, not a promise that every cross-product is feasible.
Aspect ratio must be 0.7–1.4. Counts are strict integers; booleans, fractional
counts, unknown fields, non-finite values and infeasible geometry are rejected.
A request with insufficient root patches, thin ligaments, colliding parts or
blocked removal fails with a reason. Requested lobes are never silently deleted,
contours clipped to the envelope, or joints scaled down to fit. The original
600 mm exploration failed mounting feasibility; it is outside the initial range.

`material.measured_mm` is the single manufactured stock thickness, initially 6 mm;
`clearance_mm` sets fit independently. Bore and washer dimensions retain physical
sizes. The legacy `module`, `backplate` polygon, staggered-grid placement and
`creature.scale` controls belong to the earlier families; this family derives
its own backing and roots. It has no hidden scale/rib-height coupling.

## Comparable actual CAD examples

All pictures below come from extruded manufactured contours, including the real
slots, bolt holes, support webs and backing. They are not illustrative renders.
Each column uses the same camera directions and renderer. Image framing fits the
individual model; the size comparison is specified in millimetres, not inferred
from equal image widths.

| Example | Front | Three-quarter | Side |
| --- | --- | --- | --- |
| Low, 1000×1000×200 | ![](images/flow-organism/organism-low/front.png) | ![](images/flow-organism/organism-low/three-quarter.png) | ![](images/flow-organism/organism-low/side.png) |
| Medium, same composition/size | ![](images/flow-organism/organism-medium/front.png) | ![](images/flow-organism/organism-medium/three-quarter.png) | ![](images/flow-organism/organism-medium/side.png) |
| High, same composition/size | ![](images/flow-organism/organism-high/front.png) | ![](images/flow-organism/organism-high/three-quarter.png) | ![](images/flow-organism/organism-high/side.png) |
| Bilateral composition, same focal count | ![](images/flow-organism/organism-bilateral/front.png) | ![](images/flow-organism/organism-bilateral/three-quarter.png) | ![](images/flow-organism/organism-bilateral/side.png) |
| Same low design, 800×800×140 | ![](images/flow-organism/organism-small/front.png) | ![](images/flow-organism/organism-small/three-quarter.png) | ![](images/flow-organism/organism-small/side.png) |
| Same low design, 1400×1400×240 | ![](images/flow-organism/organism-large/front.png) | ![](images/flow-organism/organism-large/three-quarter.png) | ![](images/flow-organism/organism-large/side.png) |

The medium/high distinction adds visible local detail without buying another set
of small plates and supports. This keeps artistic detail separate from assembly
piece count. The same six focal modules are used in the bilateral composition;
this is a layout/orientation change, not just a limb-count variant.

See [generated evidence](flow-organism-evidence.json) for exact actual bounds,
validation, per-example role counts, projection IDs and inventory fingerprints.
The legacy creature/radial/intertwined studies are preserved with their own configs.

## Construction effort

Each primary or secondary module consists of one planar anatomical plate and two
upright 6 mm plywood trestles. The 14 mm locating tongues enter closed 6.2×14.2 mm
slots. Web bodies are 30 mm wide; shoulders provide 8 mm on either side of each
tongue. Two through-bolts clamp the plate onto the trestles and backing. Root bores
are initially 6.5 mm, washers use 9 mm clearance radii. Actual hardware must be
selected and tested; these dimensions are clearance/fit candidates, not a load rating.

The backing follows substantial inner rails and root pads, connected by 28 mm
wide bridges plus a fixed 4 mm allowance per edge (36 mm nominal rails) where needed. It is not a full front silhouette plate. No loose
plywood spacer rings, fin keys or positive retaining clips are needed.

| Study | Plywood pieces | Hidden spacer rings | Plywood retainers | Required clips | Bolts / nuts / washers | Approx. operations |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Legacy default mask | 179 | 98 | 24 | 24 | 10 / 10 / 20 | 222 |
| Legacy two-limb | 91 | 58 | 8 | 8 | 6 / 6 / 12 | 110 |
| New low / bilateral / size variants | 19 | 0 | 0 | 0 | 12 / 12 / 24 | 42 |
| New medium | 37 | 0 | 0 | 0 | 24 / 24 / 48 | 84 |
| New high | 37 | 0 | 0 | 0 | 24 / 24 / 48 | 84 |

These are construction counts, not visible-complexity scores. Purchased hardware
is listed explicitly: the richer new examples need more root fasteners than the
old default, although they remove clips and many cut pieces. Operations estimate
one placement per wooden piece excluding backing, one clip placement where used,
one insertion per bolt and one nut tightening. Washers are grouped with their
bolt/nut operation; cradle placement, moving the backing, access and installation
anchors are excluded. This is not a measured assembly-time prediction.

Bench assembly: support the paired webs in a cradle, lower the plate onto their top
tongues, seat the bottom tongues in the backing, and secure the two bolts with
washers/nuts. Install low modules before overlapping high ones. Remove in the
exported `removal_order`, supporting the complete module before releasing clamps.
Detached parts need the cradle; they are not self-locking. Rear bolt access is
required. The full backing may need a large cutting bed; there is no unvalidated
segmented backing joint hidden in this design. The cutting-bed exporter rejects
oversized pieces. Hardware lengths follow actual support height plus two stock
thicknesses, washer/nut allowance and engagement; hardware security is NOT RUN.

## Identity, exports and verification

New family `flow-organism-v1` has a new part namespace and fingerprints. Changing
composition, complexity, size, style, stock, clearance or mounting is a **new design
requiring new cuts**, even when semantic IDs look similar. Saved-inventory replay
never calls the generator, preserves manufactured definitions and physical IDs,
and rejects missing/extra parts, changed revisions and incompatible requests.
This first flow family supports replay of its manufactured arrangement; it does
not claim arbitrary module rearrangement. The legacy rest/raised and radial
rearrangements remain available and continue to use immutable inventory.

Generation checks connected polygons, a 10 mm eroded body core and rounded-tip
loss screen, exact finished hole-to-outline and hole-to-hole ligaments of at least
7 mm, explicit neighbouring-slot margins, root bores/washer bearing, real shoulder
contacts, static solid interference, hardware corridors and actual envelope bounds.
The body-core screen is a geometric neck test, not a structural stress model.
Loaded inventory is rechecked for bearing/slots, and sampled +Z removals must follow
the recorded order. Sampling does not certify continuous motion or manual access.
The legacy neighbouring-rib-slot omission is fixed independently.

The OCP CAD backend is retained. Rectilinear upright-trestle/XY-plate intersections
use exact slice integration, checked against OCP; all other solid pairs retain the
existing kernel path. The existing CAD inspection renderer and orbit viewer remain.
SVGs, identified GLB in metres, assembly/inventory JSON and per-surface IDs feed the
same visible-face atlas and ISF resources for Wire-to-Resolume. No new renderer or
invented Wire/Arena patch schema is introduced.

```sh
parametric-deco build examples/organism-low.json --out build/organism-low
parametric-deco preview build/organism-low
parametric-deco visuals build/organism-low --out build/organism-low-visuals --visible-only
# Generate all six complete exports, projection resources, images and evidence:
python scripts/organism_examples.py
```

Open the preview URL printed by the CLI to rotate, identify, hide and explode the
actual assembly. Static triangle sorting can show overlap-edge artifacts; use the
identified GLB in an independent viewer as another inspection path.

See [execution and final whole-change review](flow-organism-review.md).
Physical strength, stock fit, bolt locking/security, handling, anchors, actual tools
and assembly/removal access are **NOT RUN**. Actual browser rendering, projector
calibration, Wire/Arena compilation and live behaviour are **NOT RUN**. Passing
geometry tests neither certifies fabrication readiness nor establishes artistic
success. Start with a complete trestle/plate/backing prototype before full cuts.

The regenerated coarse [front](images/organism-study/whorl/front.png) and
[oblique](images/organism-study/whorl/oblique.png) studies omit joinery and backing.
They show the anatomical proposal, not manufacturing-ready contours.
