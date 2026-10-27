# Roadmap

This is a staged design roadmap, not a completed implementation or a frozen engineering specification.

## Stage 0 — Document and resolve interfaces

Capture accepted requirements, alternatives, and open decisions. Obtain laser bed size, material grade, initial mounting conditions, and projector constraints.

Exit: reviewable interface sketches and explicit assembly directions; confirmed definition of total depth.

## Stage 1 — Joint and root prototype

Compare the preferred backplate-retained closure with a fallback only if needed. Produce fit coupons and a small physical joint prototype.

Exit: tested fit and retention, access, handling during detachment, and repeated disassembly. Choose the interface family from evidence.

## Stage 2 — Geometry/export spike

Compare shortlisted CAD approaches on the same arm. Export clean laser contours, assembled geometry, IDs, and station metadata.

Exit: selected backend with demonstrated units/contours/identity preservation. Keep experimental code identified as such.

## Stage 3 — Single module generator

Implement the shared definitions and configuration workflow, a complete arm/root, inventory revisions, preview, and cutting exports.

Exit: fabricated module matches preview, assembles as documented, and can be rearranged using existing parts.

## Stage 4 — Arena integration

Implement the simplest validated mapping-asset workflow. Test generated masks/coordinates and alignment patterns on the physical module.

Exit: useful visuals in Arena with a documented calibration process. Select the custom-renderer output contract before implementing that adapter.

## Stage 5 — Full intertwined sculpture

Generate an approximately 1,000 × 1,000 × 200 mm composition from reusable modules. Coordinate curves and visual groups globally. Verify extraction paths and backing stiffness.

Exit: coherent whole-artwork appearance, documented reconfiguration, and regenerated projection assets.

## Stage 6 — Optional custom rendering

Implement geometry-aware shader effects, layers, modulation, presets, and Arena texture output if this provides value beyond Wire.

Exit: effects use the shared model and run reliably on target hardware. A complete VJ replacement remains a separate scope decision.

## Working rules

Preserve accepted requirements while resolving implementation details through prototypes. Record decision changes and why they were made. Do not mistake digital fit, static collision tests, or generated imagery for physical assembly and structural verification.
