# Requirements

## Updated decisions — 2026-10-27

These decisions supersede conflicting earlier alternatives in this document.

- Python CAD is selected. build123d is the selected backend.
- Use a plywood backplate with a configurable polygon outline; hexagon and octagon are examples. Use the same nominal 6 mm thickness parameter.
- Provide laser-cut mounting holes in staggered rows. Parameterize diameter, horizontal/row pitch, alternate-row offset, grid origin, and edge margin.
- Use simple robust mounting points: broad root flanges and ordinary spaced through-bolts with washers and nuts are the baseline proposal. Avoid fragile tabs and elaborate precision locating mechanisms.
- Plywood grade and colouring are optional choices, not prerequisites for progress.
- Target ISF shaders first through Resolume Wire hosting/packaging for Arena. A standalone custom renderer remains a later option.

Status: confirmed requirements and explicitly identified proposals, 2026-10-27.

## Intent

Generate physical plywood artwork and a corresponding projection mapping representation. Reconfigure manufactured parts into new arrangements and regenerate the visual geometry without redrawing everything manually.

The default visual goal is a single integrated organic composition; alternate styles may explore layered masks, horns or radial braids. Modules are construction and transport units, not separate small decorations. Reference images supplied in the discussion show curved ribbed horns, stacked jagged profiles, and a radial stage composition. They establish visual intent, not evidence of their original joinery. Reference images are not reproduced in this repository.

## Confirmed physical requirements

- Independent overall width, height, and depth parameters.
- Initial approximate envelope: 1,000 mm wide, 1,000 mm high, 200 mm deep.
- Laser-cut plywood; one nominal thickness parameter initially set to 6 mm.
- Easy assembly, repeated disassembly, and reuse of parts.
- Prefer pieces connected internally through slots alone.
- Extra holes and slots are visually acceptable and may provide alternative connections.
- Mounting bolts between the structure and backplate are acceptable.
- Remove a module from the backplate, rearrange it on a bench, and reattach it.
- Avoid requiring clips, pins, or threaded fasteners at individual ribs in the preferred design.
- Natural wood and coloured or neon finishes are options. Do not default to white paint.
- Spray paint or lacquer is expected to produce a thin finish; verify fit after finishing.

## Confirmed software direction

- Compatibility with Resolume Arena.
- Preserve the option of a custom visual rendering engine.
- Fabrication geometry and projection geometry share the same underlying design.
- Reorganized assemblies produce updated projection assets.
- Keep manufactured part geometry distinct from configurable arrangement.

## Parameter semantics

Envelope convention: total assembly including backing and hardware, measured from the mounting surface. This includes hardware and rear clearance.

Manufacturing parameters must not scale with the overall artwork. Bolt holes, material thickness, slot clearances, and cutting compensation retain physical dimensions.

Separate nominal stock thickness from measured stock thickness. Slots use the measured value. Separate finished fit clearance from kerf compensation; apply toolpath compensation once.

Two explicit workflows:

1. **Reconfigure existing inventory:** use immutable manufactured parts at compatible positions. Report impossible arrangements and missing parts.
2. **Generate new cuts:** allow changes to part geometry and report which additional parts are needed.

A previously cut spine has fixed stations. Changing the station pitch in the generator creates a new part revision; it does not change inventory.

## Visual and projection requirements

- Coordinate contours, rib spacing, and curve directions across module boundaries.
- Allow apparent interweaving and depth overlap.
- Effects can cross mechanical module boundaries.
- Surface colour is intentional. Projection cannot fully undo absorption by dark or saturated paint.
- Reassembly requires an alignment check; repeatable mechanical location does not guarantee pixel-perfect registration.

## Proposed initial limits

- Start with shallow relief rather than arbitrary spatially twisting structures.
- Prefer apparent intertwining with independent module extraction.
- Allow a documented removal order later where interleaving traps adjacent modules.
- First prove a single complete module, not a full VJ application.
- Structural load capacity and installation details are not yet specified.
