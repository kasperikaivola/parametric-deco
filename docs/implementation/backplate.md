# Backplate and lattice

Every style uses the identical configurable regular polygon and full predefined hole grid at matching stock size, material and settings. There are no family-specific apertures, trestle seats or extra board bores. Deco mounting bores align directly to existing board bores; no offset adapters are needed. The dark board remains behind artwork openings. See [mounting](mounting.md) and the [complete gallery](gallery.md).

The regular polygon is centred and uniformly scaled to fit width/height,
including rotated odd-sided polygons. It is not stretched to force all
four envelope edges to be touched. Grid coordinates are X=originX+column·pitchX
+(row mod 2)·offset; Y=originY+row·pitchY. Negative odd rows have parity 1.
The default shared standard is equilateral: pitch X 50 mm, pitch Y 25√3 mm, offset 25 mm, origin (0,0). Exact120° orbits lie on this lattice, whereas the former50×50 staggered grid cannot contain them.
Stable hole IDs carry signed row/column, independent of clipping order.

For the universal board, a full circular disk plus edge material margin must fit inside the polygon.
Hole-to-hole web is checked conservatively against row pitch and same-row
pitch. Root positions match actual grid coordinates within 1e-6 mm, with
washer-edge margins. Arbitrary rotations are not guaranteed to fit.

For manageable prototype CAD, backing holes have 32-sided nominal contours
(6.5 mm circumscribed diameter; radial sag <=0.0157 mm). Original root holes use
64 segments; new end-clamp bores/hardware use96 segments (sag <=0.004 mm). Verify the resulting cut with the coupon.
These polygonal approximations are recorded rather than claiming exact
analytical circles in the laser contours.

Laminar now uses direct grid-aligned end clamps with rigid tube standoffs instead of unique board seats. Changing grid, polygon or stock settings can make a mounting pattern unsupported; this is rejected. The triangular-symmetric-mounts-v3 revision requires new cuts relative to previous family-specific boards and root-only deco parts. Saved old inventories remain immutable and are never silently migrated. The 1000 mm gallery examples share one actual board fingerprint; 800 and 1400 mm presets use separate stock sizes.

The maximum envelope, rear clearance and hardware remain separate from this
plywood contour. No segmentation or wall-anchor scheme is implied.
