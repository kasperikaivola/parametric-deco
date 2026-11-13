# Surface atlas contract

Each selected face has its own tile with two-pixel
black gutters, identity, local face basis/contour and mapping in atlas.json.
Reverse faces are excluded, and so are purchased clamp hardware, lighting
carriers/strips and concealed joinery (spacers, register webs, retainers) unless
named explicitly with --surface. `--visible-only` samples every remaining part in
all four styles, including the board between the artwork.

When lighting is enabled, `lighting_targets` lists each LED segment with its host
tile and the atlas UV / normalized world position of the lit edge, so projected
content can be timed or masked against the addressable segments. Projector visibility/occlusion is
not solved: map only faces which can actually receive the light.

PNG origin is top-left; local U points right and V up. Shader UV origin is
bottom-left. The manifest supplies both pixel_rect (top-left) and uv_rect
(bottom-left, minU/minV/maxU/maxV). Red +U and green +V cues and labels are
in calibration.png. Verify the actual host's PNG upload orientation before
mapping; a successful static test is not a guarantee of host conventions.

All data resources are RGBA8 PNG, stored without compression, ICC or gamma
profiles. Disable sRGB conversion, colour correction, resizing, mipmaps and
linear filtering for data. IDs use RGB24 big-endian with zero background;
use **nearest** sampling for IDs. No interpolated categorical identities.
Local RG are normalized face coordinates, B is global path phase, A valid.
World RGB are normalized assembly XYZ with bounds in the manifest. Edges R
is distance to the **actual polygon boundary** including holes, divided by
minimum face bounding-box extent; A is validity. Phase is continuous per
rib across its front and edge bases, with explicit ordered intervals across
mechanical modules. Different ribs' path intervals meet at endpoints; this
is content adjacency, not a claim of physical surface continuity everywhere.

An 8-bit 1,000 mm world span has 3.922 mm steps and up to 1.961 mm rounding
error. `world-fine.png` (`worldFineData`) stores the residual of each channel, so
`xyz = (255*world + fine - 0.5)/255` (both sampled 0..1) resolves ~0.015 mm per
1,000 mm. World bounds cover projectable plywood only, not hardware or lighting
carriers. Local per-face coordinates/edge distance remain best for fine patterns;
local and world steps are quantified in atlas.json. Tile raster resolution imposes another
limit independent of encoding. Faces are selected before packing. Broad sheet faces are the default; outer
perimeter edges are opt-in with --surfaces exterior and hole walls with --surfaces
all. Repeated --surface INSTANCE--FACE selects only named faces. The allocator
preserves face aspect ratios and uses a common physical pixels/mm scale, with
four-pixel minimum dimensions and deterministic shelf placement. Each tile records
physical area and texel_size_mm, so users can judge actual surface resolution.
Allocation uses physical size, not an unavailable projector model. The full
surface list remains in assembly.json; selection does not discard geometry.

edge-pulse.fs exposes speed (including negative/zero), phase, color and width.
A floor on width avoids division/smoothstep degeneracy at zero. calibration.fs
shows the generated labels and asymmetric cues, optionally overlaid with a
grid. Both are real ISF 2 fragment sources with explicit image inputs. CPU
reference/static metadata tests pass; offscreen/proprietary host checks are
explicitly skipped without a configured host. This atlas is **unmapped
content**: apply geometric mapping once, in Arena. Calibration is separate.
