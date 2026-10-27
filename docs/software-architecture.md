# Software architecture proposal

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

## Principle

The shared part and assembly model is authoritative. CAD files, cutting outlines, assembled meshes, visual coordinates, and mapping assets are derived outputs.

Keep geometry and physical inventory independent of CAD and VJ applications. Do not reconstruct identities and connections from a flattened STL.

## Data model

Proposed entities:

- Design parameters: envelope, curve family, layout, rib profiles, and station spacing.
- Manufacturing profile: nominal and measured thickness, fit, kerf policy, sheet/bed size, finish notes.
- Part definition/revision: local geometry, thickness, interfaces, station IDs, projection faces, and labels.
- Physical part instance: unique ID referencing an immutable manufactured revision.
- Module configuration: assigned part instances, occupied slots, orientation, closure, and root adapter.
- Assembly: module transforms, mounting stations, and dependencies for removal.
- Visual metadata: surface IDs, symmetry groups, global paths, adjacency, and coordinate systems.
- Calibration: projector settings, alignment correspondences/transforms, and residual manual corrections.

Use explicit units and coordinate conventions, including handedness, surface normals, and origin. Record generation version and parameter provenance. Regeneration must be deterministic for a given version and input.

A piece cannot occupy two assembly positions at once. A new parameter setting cannot mutate the definition of an already-manufactured part.

## Workflows

### Existing inventory

Select parts and compatible stations; compute the assembled model. Report missing pieces, incompatibilities, collisions, and removal dependencies. Produce an updated assembly list and visual assets without claiming that existing pieces were resized.

### New fabrication

Generate or select definitions, compare with inventory, and identify new cuts. Export individual parts and nested sheets while retaining their identity. Produce assembly instructions and nominal projection geometry from the same assembly.

## Geometry engine decision

Evaluate a representative arm and root with each shortlisted backend.

| Option | Benefit | Concern |
| --- | --- | --- |
| OpenSCAD | Scripted solids, 2D extrusion, parameter overrides, automated SVG/DXF export | Rich metadata and assembly orchestration may need an external layer |
| Python + CadQuery/build123d | Direct access to geometry, metadata, validation, and exporters in one language | Dependency setup and export semantics need validation |
| Blender Geometry Nodes/Python | Artistic exploration, procedural forms, UV work, preview | Exact manufacturing constraints need deliberate implementation |
| Rhino/Grasshopper | Interactive parametric form exploration and fabrication ecosystem | Proprietary dependency and deployment considerations |

Python CAD is selected; the library is not yet selected. Prefer a small comparison producing clean cut contours and a correctly identified assembly over an abstract feature comparison.

A drawing with hidden lines is not a manufacturing contour. Validate units, closed loops, holes, tessellation, and duplicate edges.

## Initial interface and outputs

Proposed initial UI: documented configuration files, CLI generation, and an orbitable 3D preview with part selection and labels. A full editor is a later choice.

Candidate outputs:
- SVG cutting/engraving sheets with explicit units and compensation policy.
- DXF if required by the chosen cutting workflow.
- Scene mesh such as glTF/GLB for preview/custom rendering or OBJ for a validated consumer.
- JSON metadata and assembly manifest.
- Part list, station assignments, and assembly/removal instructions.
- Masks, UV/layout references, coordinate textures, and calibration patterns.

Mesh format selection remains open. Ensure part/surface identity survives export, using a manifest where the format is insufficient.

## Resolume Arena

Arena compatibility is required. Initially use Arena for performance mixing, effects/layers, controls, and projector output.

Possible adapters:
1. Generated masks/layout references and manually established slices.
2. Custom Wire/ISF sources using generated coordinate data.
3. A separate renderer feeding live textures to Arena through Spout on Windows.

No automatic SVG-to-slice import or stable programmatic screen-preset schema has been established. Arena's XML presets exist, but an exporter must be tested against the target version before being promised. A generated mask is not automatically a complete mapping setup.

Validate one module end-to-end before designing a large exporter.

## Future custom renderer

Scope initially to geometry-aware visuals:
- Load assembly mesh, identity, coordinates, and connections.
- Render procedural shaders in local surface or global artwork coordinates.
- Composite layers with masks and blend modes.
- Support presets, audio/beat modulation, and MIDI/OSC.
- Send output to Arena; optionally provide standalone projector output later.

C++/openFrameworks is a researched candidate, not a selected runtime. A full VJ replacement adds clip decoding/seeking, browser/UI, output management, controllers, persistence, and failure handling, and is not the first milestone.

Define the output contract explicitly:
- Content atlas/unmapped imagery: Arena performs mapping.
- Calibrated projector image: the renderer performs geometric mapping; Arena must not apply it again.

The second path also constrains subsequent effects: arbitrary image transformations in Arena can break registration.

## Coordinates and whole-artwork effects

Store local coordinates for each projecting face plus assembly coordinates and semantic groups. Preserve cross-module paths and adjacency so a pulse can follow the whole sculpture rather than reset at each mechanical boundary.

Slotted plywood has thickness: model edges/back faces where they matter for visibility and projection. Account for occlusion from the projector viewpoint. A hidden surface cannot be illuminated by software correction.

Calibration is separate from artwork coordinates. Rearrangement regenerates the nominal assembly, but real installation requires alignment verification. For flat layouts use a validated 2D workflow; for appreciable depth investigate camera/projector-model calibration. Multiple projectors and overlap blending are later scope unless required.

## Validation boundaries

Automate geometric checks, inventory consistency, compatible interfaces, closed contours, and collision tests. Assembly-path checking is more demanding than static collision detection and may begin with documented/manual verification.

Geometric validity does not establish structural safety, fit after finishing, or long-term wear. Those require physical evidence.

## First ISF deliverable

Generate one ISF fragment shader, a Wire wrapper, any required masks/coordinate textures, and a documented Arena mapping setup. Bare ISF loading directly in Arena is not assumed. Verify target Wire/Arena versions and authoring licence requirements. ISF defines content/effects; it does not carry the complete mechanical assembly or automatically calibrate a projector.

Python supplies geometry metadata and resources; Wire hosts the shader and exposes controls; Arena mixes and maps the resulting content. Validate atlas layout, texture precision/filtering, ID encoding, and resource packaging in the first spike. Keep shader sources reusable for a future host, without promising identical host behaviour before testing.
