"""Wall hanging plan for the universal board, using its existing free grid bores.

The deco clamps put M6 heads behind the board, so decos are assembled onto the
board before it goes on the wall. The board is then hung with wall screws through
free grid bores that stay reachable from the front, each carrying a rigid standoff
tube that fills the rear clearance. Nothing is drilled or added to cut inventory.
"""

import math

from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from .validation import xy_footprint

PLYWOOD_DENSITY_KG_M3 = 700  # birch-ply upper bound; poplar/light ply is lighter
STANDOFF_OD_MM = 12
TOOL_CLEARANCE_MM = 10  # screw head/washer plus driver bit around the bore axis


def plan_wall_mount(assembly, config):
    board = next(i for i in assembly.instances if i.role == "backplate")
    board_part = assembly.definition_for(board)
    board_shape = xy_footprint(board_part, board.transform)
    bore_area = math.pi * (config.grid.hole_diameter_mm / 2) ** 2
    bores = [Polygon(ring).centroid for ring in board_shape.interiors
             if abs(Polygon(ring).area - bore_area) < 1]
    stations = [Point(s["xy"]) for s in
                (assembly.composition or {}).get("end_supports", {}).get("stations", [])]
    covering = unary_union([xy_footprint(assembly.definition_for(i), i.transform)
                            for i in assembly.instances if i.instance_id != board.instance_id])
    rear_keepout = config.mounting.washer_radius_mm + STANDOFF_OD_MM / 2 + 1
    free = []
    for point in bores:
        if any(point.distance(s) < rear_keepout for s in stations):
            continue
        clearance = covering.distance(point) if not covering.is_empty else math.inf
        if clearance >= TOOL_CLEARANCE_MM:
            free.append((point, clearance))
    _, ymin, _, ymax = board_shape.bounds
    xmin, _, xmax, _ = board_shape.bounds
    height, width = ymax - ymin, xmax - xmin

    def spread_pair(band, up):
        # One anchor each side of centre, as high (or low) as possible, mildly
        # preferring wider spacing; mirror-symmetric boards give mirrored anchors.
        def score(row):
            return (row[0].y if up else -row[0].y) + 0.25 * abs(row[0].x)
        left = [row for row in band if row[0].x < -0.125 * width]
        right = [row for row in band if row[0].x > 0.125 * width]
        if not left or not right:
            return []
        return [max(left, key=score), max(right, key=score)]

    upper = spread_pair([row for row in free if row[0].y >= ymax - 0.4 * height], True)
    lower = spread_pair([row for row in free if row[0].y <= ymin + 0.4 * height], False)
    mass = _mass_kg(assembly)
    anchors = [{"xy_mm": [round(p.x, 6), round(p.y, 6)], "role": role,
                "front_tool_clearance_mm": round(min(c, 999.0), 3)}
               for role, rows in (("primary", upper), ("anti-tilt", lower)) for p, c in rows]
    plan = {
        "method": "wall screws through free universal-grid bores; rigid standoff per screw",
        "status": "ok" if upper else "no_front_access",
        "standoff": {"length_mm": config.mounting.rear_clearance_mm,
                     "outer_diameter_mm": STANDOFF_OD_MM,
                     "inner_diameter_mm": config.grid.hole_diameter_mm},
        "screw": {"nominal_diameter_mm": 6,
                  "minimum_length_mm": math.ceil(config.mounting.rear_clearance_mm
                                                 + board_part.thickness_mm + 1.5 + 30),
                  "note": "length includes 30 mm wall embedment; select fixings for the wall type"},
        "anchors": anchors,
        "free_front_access_bores": len(free),
        "estimated_mass_kg": round(mass, 2),
        "sequence": ["assemble all decos and clamps on the board while it lies flat",
                     "mark the primary bores on the wall, fit fixings",
                     "offer the board up with standoffs, drive primary screws, then anti-tilt"],
    }
    return plan


def wall_mount_warnings(plan):
    if plan["status"] == "ok":
        if not any(a["role"] == "anti-tilt" for a in plan["anchors"]):
            return ("Wall mount: no front-accessible lower bores; fit a bumper of standoff "
                    "length at the bottom edge so the board does not lean on rear clamp heads.",)
        return ()
    return ("Wall mount: artwork covers every free upper grid bore, so the board cannot be "
            "screwed to the wall from the front after assembly. Use a rear cleat fixed through "
            "free bores before mounting decos, or leave a reachable bore near the top edge.",)


def _mass_kg(assembly):
    volume = 0.0
    for inst in assembly.instances:
        part = assembly.definition_for(inst)
        if inst.role in ("mounting-hardware",) or part.kind == "purchased-hardware":
            continue
        volume += part.polygon.area * part.thickness_mm
    plywood = volume * 1e-9 * PLYWOOD_DENSITY_KG_M3
    steel = 0.0
    for inst in assembly.instances:
        if inst.role == "mounting-hardware":
            part = assembly.definition_for(inst)
            steel += part.polygon.area * part.thickness_mm * 1e-9 * 7850
    return plywood + steel

