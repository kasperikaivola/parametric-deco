# Laminar organism generator — v2

This revision addresses [the review of e7f2343](https://github.com/kasperikaivola/parametric-deco/pull/3#issuecomment-6510722024).
The previous shared inner-curl/outer-returning-loop primitive has been removed.
`organism-low.json` is the production starting study, not fabrication approval.

The shared primitives now form **open curved spindles, divergent daughter laminae,
eccentric lens cavities and clefts**. A region can have a closed chamber, a chamber
opening into a branch cleft, or a different number of divergent blades. These are
field-driven relationships, rather than per-example coordinate sets. Primary medial
paths continue along their lobe instead of turning back into a scroll.

Low complexity already includes regional branching differences, closed and open
negative spaces, asymmetric focal proportions and overlapping relief. Medium adds
separate forked recess walls. High retains these and adds daughter anatomy to those
walls. Side-open inner walls leave visible recesses around substantial mounting nodes
instead of filling the focal cavities with solid plates or isolated pupil-like windows. No pupils, face
features, painted anatomy or engraved detail are required.

This remains a bounded family of planar plywood anatomy. Its flowing blade/lamina
rhythm can also suggest botanical forms; whether the combined result has the
intended mystic/alien presence is a visual judgment. The comparisons below show the
actual combined CAD, including the backing and supports, rather than certifying
artistic success from a path-diversity or contour-validity test.

## Geometry, retention and controls

`geometry/organism.py` supplies curved medial axes, continuously connected variable-
width sweeps, swelling/tapered spindles, cavities and daughter branches. Curvature
shapes the interior span of an axis. Both the low/medium/high series and the alternate
layout use the same primitives and field rules. `organism_assembly.py` retains the
existing slotted trestles, fixed physical joinery, bolt mounts and CAD validation.

Size fitting uses the **complexity-independent primary body outline**. Additional
septa lie within that outline; existing primary paths, body outlines and relief
relationships stay fixed. Subdividing an open cavity can change its local cut boundary,
but does not redistribute or remove an earlier division. Division positions use the
nested sequence **0.24, 0.74, 0.49, 0.365, 0.615**. Each count takes a prefix. Default
low/medium/high use 1/2/3 divisions. Optional grooves also accumulate at fixed stations.

The regression tests compare actual polygon differences with channels and secondary
lobes disabled: low→medium, medium→high, and every explicit segmentation increment
0→1 through 4→5. Existing internal material must remain, within numerical tolerance.
This replaces the previous test coverage that checked only outer boundaries/paths.
Optional new grooves intentionally remove their own material and are tested separately.

The sweep connects its samples with material strips; a thin sweep cannot degrade into
disconnected disks. Exact repeated Boolean vertices are removed in the new family
without a tolerance or contour smoothing. Legacy inventory canonicalization is unchanged.

| Group | JSON field | Default / range | Actual geometry effect |
| --- | --- | --- | --- |
| Composition | `organism.arrangement` | `whorl`, `bilateral` | Orbiting focal field or staggered paired rows |
| Composition | `focal_count` | 6 / integers 4–8 | Number of primary focal/appendage modules |
| Composition | `branching` | 2 / integers 1–3 | Maximum daughter branches per region; the field varies actual counts |
| Composition | `anatomy_phase_deg` | 0 / −180–180 | Shifts regional open/closed cavity and branch relationships |
| Composition | `phase_deg` | 17 / −180–180 | Whorl orientation and relative phase of regional anatomy |
| Composition | `spread` | 1 / 0.85–1.15 | Relative focal spacing before fitting the silhouette |
| Composition | `symmetry` | `rotational`, `bilateral`, `none` | Repeated orientation, reflected local paths, or individually tilted forms |
| Complexity | `complexity` | 0 / integers 0–2 | Coordinated secondary lobes, segmentation and channels |
| Override | `secondary_lobes` | null / integers 0–1 | Null follows complexity; 1 adds an inner lobe per primary region |
| Override | `segmentation` | null / integers 0–5 | Integral curved divisions in each appendage, 1/2/3 by complexity |
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

| Comparable actual oblique CAD | View |
| --- | --- |
| Low | ![](images/flow-organism/organism-low/oblique.png) |
| Medium | ![](images/flow-organism/organism-medium/oblique.png) |
| High | ![](images/flow-organism/organism-high/oblique.png) |
| Alternate bilateral | ![](images/flow-organism/organism-bilateral/oblique.png) |

The medium/high distinction adds daughter branches to pierced inner recess walls,
as well as retained internal divisions, without buying another set of supports. This keeps artistic detail separate from assembly
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

The backing follows the material banks beside the cavities and substantial root pads, connected by 28 mm
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

New family `laminar-organism-v2` requires new cuts compared with the previous
`flow-organism-v1` scroll study. Stable semantic part names do not make different
revisions interchangeable; fingerprints identify manufactured contours. Changing
composition, complexity, size, style, stock, clearance or mounting is a **new design
requiring new cuts**, even when semantic IDs look similar. Saved-inventory replay
never calls the generator, preserves manufactured definitions and physical IDs,
and rejects missing/extra parts, changed revisions and incompatible requests.
This laminar family supports replay of its manufactured arrangement; it does
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

See [review corrections and verification](laminar-organism-corrections.md).
The earlier [flow review record](flow-organism-review.md) is historical.
Physical strength, stock fit, bolt locking/security, handling, anchors, actual tools
and assembly/removal access are **NOT RUN**. Actual browser rendering, projector
calibration, Wire/Arena compilation and live behaviour are **NOT RUN**. Passing
geometry tests neither certifies fabrication readiness nor establishes artistic
success. Start with a complete trestle/plate/backing prototype before full cuts.

The regenerated coarse [front](images/organism-study/whorl/front.png) and
[oblique](images/organism-study/whorl/oblique.png) studies omit joinery and backing.
They show the anatomical proposal, not manufacturing-ready contours.

## Preserved rejected scroll study

The previous v1 [low front](images/flow-organism-v1-legacy/low-front.png),
[high three-quarter](images/flow-organism-v1-legacy/high-three-quarter.png) and
[bilateral front](images/flow-organism-v1-legacy/bilateral-front.png) are retained
for comparison, not presented as the current design. Their complete cuts/generator
remain at [e7f2343](https://github.com/kasperikaivola/parametric-deco/tree/e7f2343105e2da93aa11d130b68129cafbd815be).
A v1 inventory is rejected by the new generator with a new-cuts explanation; it is
never silently regenerated or treated as v2 parts. Legacy creature/radial examples
and their unchanged-inventory rearrangements remain supported separately.
