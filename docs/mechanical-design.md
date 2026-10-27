# Mechanical concept

This is a design proposal, not a fabrication drawing or validated load rating.

## Whole composition and modular construction

Design the overall silhouette, curves, rhythm, and crossings first. Divide that artwork into manageable modules with unobtrusive visual boundaries. Module positions, rib profiles, and spacing should coordinate across boundaries.

Apparent intertwining does not require mechanically trapped assemblies. Check both final-state collisions and the swept volume during extraction. If independent removal is impossible, document the dependency order rather than implying arbitrary removal.

## Component hierarchy

1. Backplate or backing frame: carries the modules and defines mounting stations.
2. Root assembly: locates and clamps each module to the backing.
3. Paired spines: establish profile and rib stations.
4. Transverse ribs: form the visible contour and brace the spine pair.
5. Closing member: blocks the internal disassembly direction and is retained at the backing connection.

All plywood components use the same nominal 6 mm stock. Increase stiffness through section geometry, separation, bracing, or multiple pieces where appropriate; do not silently introduce a second stock thickness.

A solid backplate supplies a background surface. Rails/frame may reduce weight and improve rear access. This choice is open.

## Candidate joint system

Complementary cross-lap slots locate ribs on two parallel spines. Slot bottoms and shoulders determine position; two separated connections determine orientation. Use a controlled sliding fit, not hammer-tight friction as the sole retention.

Ordinary cross-laps retain an extraction direction. A closing member must positively obstruct that motion. Its connection to the backplate must also prevent the closing member itself from escaping.

Do not assume one rail captures every degree of freedom merely because the model looks interlocked. The detailed design must show insertion directions, bearing/contact surfaces, restraints, and the complete assembly sequence.

Target sequence:

1. Assemble root, spines, ribs, and end bracing in the validated order.
2. Insert the closing member.
3. Locate the whole module on the backing.
4. Secure the root and closing-member attachment using backplate bolts.
5. To reconfigure, support and detach the module, move it to a bench, release the closure, and exchange/reposition ribs.
6. Reattach and verify alignment.

A detached assembly may lose retention when its backplate bolts are removed. The prototype must establish a handling method that keeps the closure engaged during removal and transport to the bench. Do not assume it remains self-locking.

If the closure cannot meet restraint/access requirements, compare removable plywood keys or retained clips as explicit fallbacks before changing the accepted target.

## Root interface

Proposed root: broad mounting flange, gussets, and spaced attachments to resist cantilever bending. Through-bolts, washers, and captive nuts or a metal nut plate support repeated assembly.

Separate locating from clamping. A round locating feature plus a second elongated locating feature can establish repeatability without overconstraining two tight holes. A seating face establishes depth. Actual feature shape and manufacturing practicality remain open.

Alternative mounting stations or indexed root adapters allow rotations/repositioning with known transforms. Bolts should not locate the module through loose clearance holes alone.

Wall anchorage, plate thickness/stiffness, bolt diameter, edge distances, and capacities depend on mass, centre of gravity, support material, and installation conditions. No stage-scale load rating follows from the proposed 1 m prototype.

## Reusable interfaces

Provide connection regions with repeatable slot dimensions and optional stations. Candidate variations include multiple rib stations, alternative compatible spine spacing, mirrored orientations, and indexed root positions.

Use interface families; equal thickness alone does not imply compatibility. Slot width, depth, direction, spacing, neighbouring clearance, and assembly access must agree.

Standard perpendicular cross-laps are the first candidate. Arbitrary angles and spatial twists require separate joint geometry or adapters. A changed curve may require new spines while retaining ribs, root hardware, and backing.

Extra slots are visually acceptable but reduce section strength. Enforce provisional minimum ligaments, distances between slot ends, and clear material around fasteners. Validate limits physically.

Engrave unobtrusive part/revision IDs, orientation marks, and station labels. Keep marks available for inventory and assembly without disrupting the intended projection.

## Fabrication and finish

Use measured thickness t and intended total slot clearance c:

finished slot width = t + c.

Kerf compensation generates the toolpath needed to achieve the finished geometry. Apply compensation once, in either exporter or laser software. Keep cut and engraving layers distinct; export closed contours, explicit millimetre units, and a scale-check feature.

Laser cutting does not need router dogbones. Account for taper, char, fragile tips, narrow webs, sheet dimensions, and nesting spacing.

Thin spray paint/lacquer is expected. Test finished joints. Mask mating surfaces or adjust fit if necessary. Do not require a separate coating-thickness parameter initially.

Natural wood, coloured paint, and neon finishes are intentional options. Inspect both unprojected appearance and projection response. Do not assume fluorescent coatings behave identically under projector and UV lighting.
