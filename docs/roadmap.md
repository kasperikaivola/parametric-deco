# Roadmap

## Implemented prototype — 2026-10-27

This section supersedes open software alternatives below; historical proposals
remain as design rationale. build123d 0.13.0 is the selected Python CAD backend;
GLB is the scene interchange format. The plywood backing uses a regular polygon
and staggered grid. A full-length slotted upper closure with two long root bolts
is the candidate retention mechanism; a lower flange with unretained tongues
was rejected because it would not prevent lifting off. Root bolt envelopes and
rear access allowances are explicit, but fastener/anchor/load selection remains
unvalidated. Detached handling requires a support tray and manual compression.

CLI, immutable inventory/reconfiguration, SVG/GLB/JSON, offline preview and per-face
ISF/PNG resources are implemented. See [validation status](implementation/validation-status.md)
for software evidence and NOT RUN physical/host checks. ISF is hosted/packaged in
Wire; no bare-Arena loading, fabricated patch schema or automatic screen-preset
export is claimed. Grade/finish are optional. Older CAD/location alternatives
and generalized custom-renderer plans below are not current implementation work.


## Updated decisions — 2026-10-27

These decisions supersede conflicting earlier alternatives in this document.

- Python CAD is selected. Only the choice of Python library (CadQuery or build123d) remains open.
- Use a plywood backplate with a configurable polygon outline; hexagon and octagon are examples. Use the same nominal 6 mm thickness parameter.
- Provide laser-cut mounting holes in staggered rows. Parameterize diameter, horizontal/row pitch, alternate-row offset, grid origin, and edge margin.
- Use simple robust mounting points: broad root flanges and ordinary spaced through-bolts with washers and nuts are the baseline proposal. Avoid fragile tabs and elaborate precision locating mechanisms.
- Plywood grade and colouring are optional choices, not prerequisites for progress.
- Target ISF shaders first through Resolume Wire hosting/packaging for Arena. A standalone custom renderer remains a later option.

This is a staged design roadmap, not a completed implementation or a frozen engineering specification.

## Stage 0 — Document and resolve interfaces

Capture accepted requirements, alternatives, and open decisions. Obtain laser bed size, initial mounting conditions, and projector constraints; grade and colouring are optional.

Exit: reviewable interface sketches and explicit assembly directions; confirmed definition of total depth.

## Stage 1 — Joint and root prototype

Compare the preferred backplate-retained closure with a fallback only if needed. Produce fit coupons and a small physical joint prototype.

Exit: tested fit and retention, access, handling during detachment, and repeated disassembly. Choose the interface family from evidence.

## Stage 2 — Geometry/export spike

Select between Python CAD libraries using a small export prototype of the same arm. Export clean laser contours, assembled geometry, IDs, and station metadata.

Exit: selected backend with demonstrated units/contours/identity preservation. Keep experimental code identified as such.

## Stage 3 — Single module generator

Implement the shared definitions and configuration workflow, a complete arm/root, inventory revisions, preview, and cutting exports.

Exit: fabricated module matches preview, assembles as documented, and can be rearranged using existing parts.

## Stage 4 — Arena integration

Implement an ISF shader and Wire wrapper as the first Arena integration, including geometry resources and packaging. Test generated masks/coordinates and alignment patterns on the physical module.

Exit: useful visuals in Arena with a documented calibration process. Select the custom-renderer output contract before implementing that adapter.

## Stage 5 — Full intertwined sculpture

**Digital candidate implemented:** the separate radial-weave family provides two
curved interwoven paths, a pronounced opening, six alternating crossings and
immutable reconfiguration. See [evidence and reproduction](implementation/radial-weave.md).
The older four-module fixture remains a mechanical study. Physical stiffness,
fit, handling and host projection gates remain **INCOMPLETE / NOT RUN**.

Generate an approximately 1,000 × 1,000 × 200 mm composition from reusable modules. Coordinate curves and visual groups globally. Verify extraction paths and backing stiffness.

Exit: coherent whole-artwork appearance, documented reconfiguration, and regenerated projection assets.

## Stage 6 — Optional custom rendering

Implement geometry-aware shader effects, layers, modulation, presets, and Arena texture output if this provides value beyond Wire.

Exit: effects use the shared model and run reliably on target hardware. A complete VJ replacement remains a separate scope decision.

## Working rules

Preserve accepted requirements while resolving implementation details through prototypes. Record decision changes and why they were made. Do not mistake digital fit, static collision tests, or generated imagery for physical assembly and structural verification.
