# Creature mask — chosen design

User requests an ambiguous living/biomechanical plywood wall relief inspired by
the supplied festival photograph: anatomical hierarchy, real cavities and sweeping
appendages, without a literal skull/cartoon face. Existing radial examples remain.
User delegates reasonable artistic choices and authorizes implementation and a PR,
not automatic merge. No extra approval gates; execute inline, one final review.

## Composition and alternatives

Chosen by implementer: bilateral carapace with two oblique eye recesses and a
central rostrum; two dominant curled crown limbs and two shorter hooked mandibles.
The head overlaps broad limb roots so five mechanical modules read as one organism.
Rounded swelling contours, graded overlapping lamellae and deliberate channels
replace the repeated circle. First produce front/oblique coarse geometry studies.

Rejected: deforming the radial braid retains its circular framework; adding
engraving/noise/fins does not establish anatomy. Nonplanar shells require a new
fabrication method. Selected approach: layered planar swept armour with slotted
vertical alignment webs and ordinary two-bolt roots. This sacrifices individual
fin interchange for coherent silhouettes and useful frontal projection surfaces.

## Mechanical candidate

1000×1000×200 mm wall-relative envelope; one measured thickness, initially6 mm.
Broad horizontal lamella profiles occupy deliberately staggered depth planes.
Two root bolts clamp each module's plates and stacks of laser-cut plywood spacer
rings. Two vertical rectangular webs register closed slots in the plates; a solid
cap blocks outward web withdrawal. Webs register XY, spacer stacks carry clamp
compression; no claim of self-locking when unbolted. Detached modules need a tray
and maintained compression, as with earlier prototypes. No fin screws or hidden
clips. Bolt heads remain visible and have explicit tool corridors; secondary
armour must not cover them. Fastener sizes/spacers/loading remain prototype tests.

Head: actual nested eye apertures through front armour and backing; depth and
aperture progression produce a recess without added decorative eyes. No teeth,
nostril pair or human cranial outline. Curled limbs have root swelling and rounded
ends; no load-bearing neck under20 mm. Filament tips are excluded.
Backplate: connected central shield following the head/roots, simple staggered
mounting grid, true eye apertures. Limbs extend beyond it within the envelope.

## Parameters, identity and reuse

Separate opt-in CreatureMask configuration; old radial and legacy schemas remain
loadable. Shape scale and crown curl modify manufactured profiles and require new
cuts. Stock thickness, clearance and hardware dimensions never scale with XY.
A second 'raised_crown' posture translates complete upper modules by grid-compatible
(±25,+50) mm offsets; head/mandibles and all manufactured identities remain fixed.
No arbitrary mirroring or fin permutation. Only identical definitions/revisions
are interchangeable. Save authoritative templates and manufacturing request hashes;
existing-inventory mode must not invoke generation and must reject stale/missing
inventory or altered geometry requests.

## Evidence and projection

Reuse shared PartDefinition/Assembly, SVG/GLB, atlas and ISF/Wire workflow; no engine.
Broad front surfaces selected. Quantify visibility/occlusion from frontal projector
at(0,0,2000) mm with sampled rays, including cavity channels and backing; export
selected visible surface IDs. Report samples as estimates, not illumination proof.
Use actual CAD front, oblique, side, exploded and local section views. Coarse study
is labelled study, not fabricated or structurally validated. Inspect images and
revise major forms before detail if it still reads as a generic ring/framework.
Check contacts, static solid interference, washer bearing, slot/web registration,
cap obstruction, root tool corridors and sampled whole-module removal order.
Physical strength, long cantilever stiffness, fit/finish, handling, wall anchors,
real projector and Wire/Arena/browser runtime remain NOT RUN.
