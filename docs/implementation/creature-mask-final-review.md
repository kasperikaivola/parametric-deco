# Creature mask — single final whole-branch review

Reviewed base `430102f3a1b20c209ff7251a5adcd671baaaed56` through head
`e0db52dedeec3655a30d141b64d042fc521dfced`, on 2026-10-29.
This is the one final review required by AGENTS.md. Source, index and HEAD were
not changed; this report is the only reviewer-authored repository file.

## Readiness

**Ready for a PR as a digital sculpture candidate. No Critical or Important
finding was established.** This does not approve manufacture, loading, installation,
or host/projector operation. The remaining findings below are Minor. No automatic
merge is authorized, and no second review round is requested.

The front view has a recognisable nonhuman face, true oblique eye apertures,
dominant swelling crown curls and smaller lower hooks. It is no longer a circular
rib framework. The raised forehead/rostrum improves hierarchy over the coarse
study. The reference's much richer flowing anatomy is simplified substantially:
the broad face and repeated parallel terraces still read as a restrained alien
mask/emblem, and the low oblique exposes its stacked construction. This is an
artistic limitation for the user's judgment, not evidence of a missing cavity or
invalid physical profile. The resting pose is more cohesive than raised_crown;
the latter visibly exposes shoulder/root cutouts, as the documentation acknowledges.

## Findings

### Critical

None established.

### Important

None established.

### Minor 1 — register-web interface coordinates describe the plate, not the web

Location: `src/parametric_deco/geometry/creature.py:70-73,91,104-105`.

Every register-web definition receives the same station tuple as its armour
plates. For example, the exported crown-left web has local bounds
`(-9, 0, 9, 72)` but station X coordinates approximately `-201.77` and `-223.23`.
Those coordinates cannot locate interfaces on that local web. Solid caps also
receive the slot station tuple despite intentionally having no registration slots.

Trigger/impact: a consumer inspecting interface metadata, rather than the cut
polygon, gets misleading local joinery locations. Current assembly and exports
place the correct polygons: the creature checker uses actual footprints and the
generic connection checker only consults station IDs on the target plate. Thus
this is not an established miscut or interference defect. Give web/cap definitions
truthful family-local interface metadata, or omit inapplicable stations; do not
change an already manufactured inventory in place merely to normalize metadata.

### Minor 2 — the section is useful for web capture but not an axial bolt section

Location: `src/parametric_deco/export/views.py:48-51,115-117,157` and both committed
`creature-mask*-joint-section.png` images.

The section plane follows a head web at Y=88 mm, whereas head bolt centres are at
Y=100 mm. It cuts the spacer rings off-axis and consequently shows solid-looking
column slices without their bores. It also omits the backing. The caption's
“through head roots” is imprecise for someone checking the complete clamp path.

Trigger/impact: using this drawing to inspect bolt bores, backing contact or washer
bearing would overinterpret its evidence. Label it as an offset web section and,
when preparing fabrication drawings, add an axial root/backing section with the
actual selected hardware. The current model's ring/plate compression paths are
continuous; this finding concerns the explanatory drawing, not a demonstrated gap.

### Minor 3 — low-oblique images are weak evidence of face cavities

Location: `src/parametric_deco/export/views.py:17-20,83-94,136-140` and both committed
`creature-mask*-oblique.png` images.

At the current low viewing elevation, the eyes collapse into narrow layered slits
and some root/terrace overlaps show jagged painter-order artifacts. The broad,
uniform shading further suppresses the rostrum. These images show depth but are
less useful than the front view for inspecting the intended face hierarchy.

Trigger/impact: judging cavity continuity or anatomical presence from the oblique
alone is unreliable. A somewhat more frontal oblique using the existing view
pipeline would improve the handoff; no new renderer is required or recommended.
The front images and geometric channel checks establish that these are real holes.

## Evidence inspected

- Read AGENTS.md, the chosen design, implementation plan, progress ledger, example
  documentation, evidence JSON, changed source and tests, and shared inventory,
  validation, atlas and export code relevant to the changes.
- Inspected the private reference without copying it into the repository; coarse
  front/oblique studies; resting and raised front/oblique/section CAD images; and
  the resting exploded image. The coarse study is clearly distinguished from
  fabrication evidence.
- Loaded both existing exported assemblies/inventories through the normal schema
  readers. Confirmed 133 physical instances in each, identical instance-ID /
  definition-ID / revision assignments, and identical manufactured fingerprints.
- Independently probed plywood 8 mm off each root axis in both poses. Every module's
  two columns were contiguous from backing front Z=16 mm to its cap: head178 mm,
  crowns94 mm, mandibles76 mm. This corroborates generated compression paths, not
  their strength. Root holes, slots and caps are actual planar cut geometry.
- Confirmed each pose's recommended visibility surface IDs exactly match the
  exported atlas tile IDs. Visibility uses the physical part transforms and actual
  contour/hole intersections, including extrusion thickness; no separate renderer
  or fictitious host validation was introduced.
- Checked the source failure paths: family and layout fingerprint, manufacturing
  request signature, missing/extra instance IDs, stale role/revision, definition
  fingerprints, envelope, static interference, eye channels and sampled extraction
  order. Inventory reconfiguration uses saved templates, not generation. Its
  manufacturing request comparison is deliberately conservative.
- The raised pose's committed evidence bounds are approximately X±479.64 mm,
  Y−381.26..468.61 mm, and hardware Z≤190 mm, within the specified envelope. The
  removal dependencies require the head first, then the other complete modules.
- Existing radial/legacy dispatch remains intact. The supplied prior verification
  records 68 passed / 1 explicit host skip. Fresh full-suite and expanded CLI runs
  were still in progress during this review; their final result must be recorded
  by the implementer. I did not claim a separate full-suite run.

## Explicitly not judged or certified

- Plywood grade, kerf, slot fit, tolerances, edge finish and wear: no manufactured
  coupon or representative root/web prototype was available.
- Cantilever stiffness, spacer-column stability, clamp preload, bolt length/grade,
  washers, torque, wall anchors and load capacity: no selected hardware, load
  calculation or physical test was provided. The digital washer-radius corridor
  is not a measurement of a particular socket, wrench or human hand.
- Safe detached handling or a practical compression tray: the mechanism is
  explicitly not self-locking after unbolting; no tray/handling trial was performed.
- Continuous collision-free removal or every assembly sequence: the implementation
  checks sampled +Z translations and one dependency order, not exhaustive motion.
  Rear fastener access and manual tool access remain physical checks.
- Actual browser rendering, Wire/Arena compilation, projector calibration,
  illumination, ambient shadow and colour: these hosts/hardware were not run.
  Finite ray samples and selected IDs establish digital correspondence only.
- Final artistic acceptance or equivalence to the reference's sculptural richness:
  the reviewer can assess hierarchy and actual geometry, but the user decides
  whether this simplified mask has the desired presence.

Any follow-up is a targeted fix/verification pass, not another whole-branch review.
