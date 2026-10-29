"""Coarse contour/depth study: real planar profiles, no fabricated joinery claims."""

from pathlib import Path
import numpy as np
from shapely.geometry import MultiPoint
from PIL import Image, ImageDraw, ImageFont
from parametric_deco.geometry.creature_profiles import (
    profiles,
    backing_outline,
    rib_stations,
    organic,
)
from parametric_deco.model import Assembly, PartDefinition, PartInstance
from parametric_deco.export.views import render_views

out = Path("docs/implementation/images/creature-study")
out.mkdir(parents=True, exist_ok=True)
defs = []
instances = []
shapes = []
for name, layers in {"backplate": [backing_outline()], **profiles()}.items():
    for j, p in enumerate(layers):
        z = 10 if name == "backplate" else 100 + 12 * j if name == "head" else 16 + 18 * j
        d = PartDefinition.from_polygon(
            f"{name}-{j}", p, 6, kind="backplate" if name == "backplate" else "armour"
        )
        defs.append(d)
        instances.append(
            PartInstance(
                d.definition_id,
                d.definition_id,
                d.revision,
                ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, z), (0, 0, 0, 1)),
                name,
                "backplate" if name == "backplate" else "armour",
            )
        )
        shapes.append((z, p, name, j))
for name in ("crown-left", "crown-right", "jaw-left", "jaw-right"):
    cap_z = 94 if name.startswith("crown") else 76
    for j, (center, normal, width, height) in enumerate(rib_stations(name)):
        poly = organic(
            [
                (-width / 2, 6),
                (-width * 0.42, height * 0.6),
                (-width * 0.12, height),
                (width * 0.2, height * 0.8),
                (width / 2, 6),
            ]
        )
        d = PartDefinition.from_polygon(f"{name}-rib-{j}", poly, 6, kind="armour")
        # Columns: transverse direction, outward Z, right-handed thickness direction.
        nx, ny = normal
        tangent = (ny, -nx)
        pose = (
            (nx, 0, tangent[0], center[0] - 3 * tangent[0]),
            (ny, 0, tangent[1], center[1] - 3 * tangent[1]),
            (0, 1, 0, cap_z),
            (0, 0, 0, 1),
        )
        defs.append(d)
        instances.append(
            PartInstance(d.definition_id, d.definition_id, d.revision, pose, name, "armour")
        )
        xy_world = (
            np.array([(*point, depth, 1) for point in d.outer for depth in (0, 6)])
            @ np.array(pose).T
        )
        shapes.append((cap_z + height, MultiPoint(xy_world[:, :2]).convex_hull, name, 0))
a = Assembly(tuple(defs), tuple(instances))
render_views(a, out)
# Explicit CAD-edge study for front readability; geometry is unchanged.
im = Image.new("RGB", (1100, 1000), (18, 21, 27))
dr = ImageDraw.Draw(im)
for z, p, name, j in sorted(shapes, key=lambda x: x[0]):
    mask = Image.new("L", im.size, 0)
    md = ImageDraw.Draw(mask)

    def xy(r):
        return [(550 + x * 0.95, 525 - y * 0.95) for x, y in r.coords]

    md.polygon(xy(p.exterior), fill=255)
    for r in p.interiors:
        md.polygon(xy(r), fill=0)
    color = (66, 55, 42) if name == "backplate" else (184 + 7 * j, 139 + 6 * j, 87 + 5 * j)
    layer = Image.new("RGB", im.size, color)
    im.paste(layer, (0, 0), mask)
    dr = ImageDraw.Draw(im)
    dr.line(xy(p.exterior), fill=(83, 57, 32), width=2)
    for r in p.interiors:
        dr.line(xy(r), fill=(83, 57, 32), width=2)
dr.text(
    (30, 25),
    "COARSE CREATURE STUDY / FRONT / CAD CONTOURS",
    font=ImageFont.load_default(size=23),
    fill="white",
)
dr.text(
    (30, 62),
    "Silhouette, cavities and depth only; joinery and physical behaviour not validated",
    fill="#b0b0b0",
)
im.save(out / "front-contours.png")
# Keep only explicitly labelled pre-joinery studies; final assembly views live elsewhere.
for filename in ("front.png", "side.png", "exploded.png", "joint-section.png"):
    (out / filename).unlink(missing_ok=True)
oblique = Image.open(out / "oblique.png")
label = ImageDraw.Draw(oblique)
label.rectangle((0, 0, 1100, 92), fill=(18, 21, 27))
label.text(
    (30, 25),
    "COARSE CREATURE STUDY / OBLIQUE / NO JOINERY",
    font=ImageFont.load_default(size=23),
    fill="white",
)
oblique.save(out / "oblique.png")
