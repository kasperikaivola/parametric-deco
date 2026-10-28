# Radial weave digital artwork

Approved direction: pronounced central opening; dense radial, sweeping tapered
ribbed forms with several unmistakable over/under crossings. User requested
implementation directly. Existing 1,000 × 1,000 × 200 mm envelope, one measured
plywood thickness (default 6 mm), reusable identified parts, simple internal
slots, backplate bolts and bench reconfiguration remain requirements.

## Approach chosen by implementer

Keep the old mechanical study and introduce an opt-in radial-weave family.
Two sinusoidal annular paths R=300 ± 65 sin(3 theta) mm cross six times. Split
each path into six arc modules centred on crossings; alternate high/low modules
so each path visibly alternates over and under. Boundaries have small designed
seams between mechanically separate modules. The backplate receives an actual
180 mm-radius central aperture, and all sculpture must stay outside that radius.

Alternatives: moving old straight copies was already visually inadequate;
nonplanar twisted spines would complicate laser joinery. Instead use planar
curved XY spines and perpendicular radial vertical ribs. These are new candidate
joints, not presumed equivalent to the old +Z-sliding family.

Two horizontal spines per module sit at local Z=20/44 (low) or 102/126 (high).
A curved inner closing rail sits at Z=70 or 152. Its rib tongues project one
stock thickness through closed slots. Ribs slide radially inward for removal;
the installed rail obstructs that motion. Complementary slots open inward on
spines and outward on ribs. Common spine-slot datum is U=0; rib slots use
measured thickness + total fit clearance. No rib pins or individual rib bolts.

Nine fins per 60-degree arc, centred at -25..25 degrees. Two end fins extend to
the backing as support cheeks. Other high fins start at Z=92, while low fins
are <=76 near crossings, giving actual depth separation. Low outer crests rise
near the well-separated ends to coordinate the visible boundary height. The
inner capture tongue remains at its own fixed rail height. Root pads are clipped
to each arc sector; choose two actual backplate grid holes with washer/material
clearance and clear vertical bolt corridors. Long root bolts clamp the closing
rail; detailed load capacity and detached support remain physical tests.

Every part is a real connected planar contour extruded at measured thickness.
The innermost rail is 32 mm wide and the tongue 12 mm long, leaving approximately
10 mm radial material around capture slots. Three-degree-or-smaller seams keep
module boundaries deliberate; root geometry must not bridge into adjacent sectors.
The 200 mm wall-relative limit includes backing, rear gap and hardware.

## Shared model and evidence

Use existing PartDefinition/PartInstance, exporters, inventory, atlases and CLI.
Add optional composition configuration and serializable assembly composition
metadata. Save authoritative radial placement templates alongside inventory;
existing-inventory mode uses saved geometry and stations, never regenerated cuts.
A second arrangement rotates the complete placement 180 degrees and permutes
compatible central ribs on the bench, preserving every physical ID/fingerprint.

Report exact crossing locations and high/low roles, opening clearance, static
interferences, and a checked removal order (high modules before low). Validate
positive-Z module extraction under that order; validate radial rib insertion
without closure and obstruction with closure. Sampled paths are not an exhaustive
rigid-body proof. Generate front, oblique, side, exploded and joint views from CAD,
inspect them, and do not claim artistic completion from counts alone.

Physical fit, stiffness, root hardware, tray handling and Wire/Arena remain NOT RUN.
One fresh whole-branch review at the end, no task-by-task reviews.
