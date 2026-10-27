# Surface atlas contract

Each explicit front/edge/hole-wall face has its own tile with two-pixel
black gutters, identity, local face basis/contour and mapping in atlas.json.
Backing and reverse faces are excluded. Projector visibility/occlusion is
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
error. This does not support submillimetre world edges. Use local per-face
coordinates/edge distance for fine patterns; local steps and actual world
steps are quantified in atlas.json. Tile raster resolution imposes another
limit independent of encoding. A tile too small for a face should be enlarged
or given a separate atlas before production; v1 uses equal rectangular cells.

edge-pulse.fs exposes speed (including negative/zero), phase, color and width.
A floor on width avoids division/smoothstep degeneracy at zero. calibration.fs
shows the generated labels and asymmetric cues, optionally overlaid with a
grid. Both are real ISF 2 fragment sources with explicit image inputs. CPU
reference/static metadata tests pass; offscreen/proprietary host checks are
explicitly skipped without a configured host. This atlas is **unmapped
content**: apply geometric mapping once, in Arena. Calibration is separate.
