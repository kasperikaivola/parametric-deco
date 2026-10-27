# Backplate and lattice

The regular polygon is centred and uniformly scaled to fit width/height,
including rotated odd-sided polygons. It is not stretched to force all
four envelope edges to be touched. Grid coordinates are X=originX+column·pitchX
+(row mod 2)·offset; Y=originY+row·pitchY. Negative odd rows have parity 1.
Stable hole IDs carry signed row/column, independent of clipping order.

A full circular disk plus edge material margin must fit inside the polygon.
Hole-to-hole web is checked conservatively against row pitch and same-row
pitch. Root positions match actual grid coordinates within 1e-6 mm, with
washer-edge margins. Arbitrary rotations are not guaranteed to fit.

For manageable prototype CAD, backing holes have 32-sided nominal contours
(6.5 mm circumscribed diameter; radial sag <=0.0157 mm). Root holes use
64 segments (sag <=0.004 mm). Verify the resulting cut with the coupon.
These polygonal approximations are recorded rather than claiming exact
analytical circles in the laser contours.

The initial octagon top view was rendered with every hole visible. The
maximum envelope, rear clearance and hardware remain separate from this
plywood contour. No segmentation or wall-anchor scheme is implied.
