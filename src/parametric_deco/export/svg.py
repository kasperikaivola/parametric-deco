"""Closed nominal manufacturing contours. Y is flipped only at this SVG boundary."""

from html import escape
from pathlib import Path

from ..model import PartDefinition


def number(value):
    return f"{value:.6f}".rstrip("0").rstrip(".") if value else "0"


def _path(ring, dx=0, dy=0):
    points = list(ring)
    return "M" + " L".join(f"{number(x + dx)} {number(-y - dy)}" for x, y in points) + " Z"


def svg_document(items, width, height, viewbox):
    cuts, marks = [], []
    for part, dx, dy, label in items:
        for ring in (part.outer, *part.holes):
            cuts.append(f'<path d="{_path(ring, dx, dy)}"/>')
        point = part.polygon.representative_point()
        marks.append(
            f'<text x="{number(point.x + dx)}" y="{number(-point.y - dy)}" '
            f'font-size="3">{escape(label)}</text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{number(width)}mm" '
        f'height="{number(height)}mm" viewBox="{viewbox}">'
        "<title>Nominal finished contours; kerf compensation in laser software only</title>"
        '<g id="cut" fill="none" stroke="#ff0000" stroke-width="0.1">'
        + "".join(cuts)
        + '</g><g id="engrave" fill="#0000ff">'
        + "".join(marks)
        + "</g></svg>"
    )


def write_part_svg(part: PartDefinition, path: Path):
    minx, miny, maxx, maxy = part.polygon.bounds
    vb = " ".join(number(n) for n in (minx, -maxy, maxx - minx, maxy - miny))
    Path(path).write_text(
        svg_document(
            [(part, 0, 0, f"{part.definition_id}@{part.revision}")], maxx - minx, maxy - miny, vb
        )
    )


def place_sheets(parts_with_quantities, bed):
    """Deterministic shelf placement using conservative bounding rectangles, no rotation."""
    sheets, current = [], []
    gap = bed.spacing_mm
    x, y, row_height = gap, gap, 0
    for part, quantity in sorted(
        parts_with_quantities, key=lambda row: (row[0].definition_id, row[0].revision)
    ):
        minx, miny, maxx, maxy = part.polygon.bounds
        w, h = maxx - minx, maxy - miny
        if w + 2 * gap > bed.width_mm + 1e-8 or h + 2 * gap > bed.height_mm + 1e-8:
            raise ValueError(f"{part.definition_id}: oversized for cutting_bed; never shrink parts")
        for copy in range(quantity):
            if x + w + gap > bed.width_mm:
                x = gap
                y += row_height + gap
                row_height = 0
            if y + h + gap > bed.height_mm:
                sheets.append(current)
                current = []
                x, y, row_height = gap, gap, 0
            current.append((part, x - minx, y - miny, f"{part.definition_id}-{copy + 1}"))
            x += w + gap
            row_height = max(row_height, h)
    if current:
        sheets.append(current)
    return sheets
