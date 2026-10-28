# Decision register

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

Recorded 2026-10-27. Accepted requirements are distinguished from recommendations.

## Accepted

| ID | Decision |
| --- | --- |
| D01 | Overall dimensions are parametric; initial target is approximately 1 × 1 × 0.2 m. |
| D02 | Use laser cutting and one nominal plywood thickness, initially 6 mm. |
| D03 | Reuse and reconfiguration are core requirements. Additional connection slots/holes are acceptable. |
| D04 | Detach a module before rearranging it, then reattach it to the backplate. |
| D05 | Prefer slotted internal assembly; bolts are acceptable at the backplate interface. |
| D06 | The finished sculpture should look like one intertwined artwork. |
| D07 | White is not the default finish. Natural, coloured, and neon surfaces remain candidates. |
| D08 | Support Resolume Arena and retain the possibility of our own renderer. |

## Proposed, not yet validated

| ID | Proposal | Evidence needed |
| --- | --- | --- |
| P01 | Two parallel profiled spines, transverse ribs, and braced root/end crosspieces | Stiffness, torsion, assembly access |
| P02 | A closing rail blocks extraction and is retained by the backplate attachment | Actual geometry, complete restraint, removal sequence |
| P03 | Standard root flange with locating features and clamping bolts | Mounting access and repeatability |
| P04 | Multiple standardized slot stations and compatible rib families | Fit, collision, remaining section strength |
| P05 | Python orchestration and application-independent assembly data | Small CAD/export comparison |
| P06 | Config files, CLI generation, and a 3D preview before a full GUI | User workflow review |
| P07 | Independent module removal for the initial intertwined arrangement | Swept extraction-path checks and physical trial |

## Open decisions

- Python CAD library: CadQuery or build123d.
- Exact cross-lap and closing-member geometry; fallback keys only if needed.
- Interface dimensions, spine separation, slot pitch, and allowable orientations.
- Polygon side count, mounting-grid dimensions, root pattern, and any required backplate segmentation.
- Laser bed and stock sheet dimensions, requiring segmentation where necessary.
- Measured thickness, fit clearance, and kerf for actual fabrication. Grade and coating remain optional.
- Root bolt pattern, hardware, backing stiffness, wall type, and installation loads.
- Initial curve/profile family, arm count, and arrangement.
- Scene interchange format and exact Arena mapping integration.
- Whether custom renderer output is a content atlas or a calibrated projector image.
- Projector model, resolution, throw, placement, and calibration workflow.
- Production runtime language/framework for a custom renderer.
- Licensing of the project and any reused assets or libraries.

## Options considered

Python CAD and initial ISF output through Wire/Arena are selected. A custom renderer remains optional. OpenSCAD is historical research, not the current backend candidate.

Blender is useful for artistic exploration, UV work, and preview. Rhino/Grasshopper offers interactive parametric design. MadMapper and TouchDesigner remain researched alternatives for mapping/calibration, but do not replace the accepted Arena compatibility requirement.

Earlier ideas using different plywood thicknesses for ribs and spines are superseded by D02. Earlier suggestions for white projection surfaces are superseded by D07. Individual keeper pins/clips are fallback concepts, not the preferred accepted assembly target.
