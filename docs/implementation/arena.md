# Wire / Arena handoff (host validation NOT RUN)

No Wire or Arena executable/licence is available in this environment. Exact
installed Wire version: **NOT RUN / unavailable**. Exact installed Arena
version: **NOT RUN / unavailable**. ISF 2 metadata and the official Wire ISF
page, whose version-specific note names 7.22, are the reference baseline.
Do not read that as a claim of testing 7.22 or the latest release. Record
both exact installed versions in host-feedback.md when running this packet.
No .wired/.cwired patch or screen-preset XML has been fabricated.

Primary references read 2026-10-27:

- https://resolume.com/support/en/isf — ISF resource/fragment node and inputs.
- https://resolume.com/support/en/wire-resolume-integration — Source category,
  texture resolution, Float/Color input nodes and Dashboard order.
- https://resolume.com/support/en/wire-saving-consolidating — Consolidate copies
  resources and rewrites paths; compiling packages resources into one file.
- https://resolume.com/support/en/advanced-output — input selection and output
  transformation are distinct; screen setups can be saved by the operator.

## One-module manual authoring recipe

1. Generate build/single and build/single-visuals with the documented CLI.
   Open atlas.json. Keep its dimensions exactly (default 2048 × 2048).
2. Start a new Wire patch. In Patch settings choose **Source** category and
   name it Parametric Deco Calibration. Create an ISF node. Select it, open
   the node panel, Attributes → Fragment Shader → browse to calibration.fs.
3. Import calibration.png and local.png as image resources. Feed their
   texture outputs to the ISF inlets named calibrationImage and localData.
   The atlas inputs table is authoritative; filenames are relative to the
   visual output directory. Match patch/output resolution to atlas size.
4. Route the ISF texture to Texture Out. Expose a Bool input named grid and
   connect it to grid. Verify tiles have labels, red +U and green +V arrows,
   transparent invalid pixels and black gutters; a mirrored result is a fail.
5. Save. Set Source category if it does not appear in Arena. In Arena select
   a composition with the same pixel dimensions, load the saved Wire Source,
   use neutral transforms and no colour-changing effects on the data path.
6. Use the **same method in a second patch** for edge-pulse.fs. Connect
   local.png → localData and edges.png → edgeData. Connect Float inputs
   speed [-2,2], phase [0,1], width [0,0.5] and a Color input color to their
   named shader inlets. Order/rename inputs on the Dashboard for Arena.
7. Explicitly test nearest/no-mipmap sampling and no sRGB conversion for
   numeric textures. Check known local pixel values against atlas.json
   before relying on edges/IDs. If Wire cannot preserve numeric PNG values
   on this host, report FAIL and revise encoding/loading; do not compensate
   by changing the sculpture or applying a second geometric warp.
8. Use Consolidate to copy the patch and resources together. Move/rename the
   original visual resource folder; reopen the consolidated patch and verify
   all images still load. Compile using Wire's interface. Official CLI form
   for a **real saved patch** is `Wire.exe compile <patch-file> --output <file>`;
   no nonexistent patch filename is supplied by this repository.
9. Load the compiled source in Arena, record exact versions/licensing and
   repeat zero-speed/zero-width, direction, mask, phase and relocation tests.

## Mapping one actual face, then one module

1. Begin with a large visible rib front face, not every cut-hole wall.
   Find its instance/surface tile in atlas.json. In Arena Advanced Output,
   add a slice with Input Selection exactly matching pixel_rect [x,y,w,h]
   in the atlas. Include the valid face and leave gutter pixels outside.
2. In Output Transformation map that slice to the corresponding physical
   face. Use the face contour/basis and asymmetric cues to check local U/V;
   adjust physical vertex/corner alignment. Mask apertures and occluded
   areas using the generated alpha and the actual projector viewpoint.
3. Map the visible spine and closure faces on this module using separate
   slices. A nonrectangular tile contains transparent pixels and may need
   additional control points for perspective/depth; a bounding rectangle
   alone is not a geometry-calibrated projection.
4. Save the Arena screen preset through Arena. This is the **only** geometric
   mapping stage. The ISF produces unmapped face-atlas content. Do not prewarp
   this source and then reuse the same Arena warp.
5. Check narrow edge patterns and opposite pulse direction on neighbouring
   parts. Detach/reattach the supported module, recheck alignment, and record
   residual error, occlusion and whether projection is usable on the finish.
6. Extend to the other modules only after this passes. Record slice count
   and setup minutes. Every edge/hole-wall tile is explicit, so mapping all
   tiles would be labour-intensive; v1 deliberately lets the operator map
   only useful visible faces. Automatic screen-preset export is out of scope.

The pipeline stops at actionable resources/manual setup here. Shader compile,
resource relocation, data-value preservation, actual mapping, projection and
runtime performance are all NOT RUN until a host operator records evidence.
