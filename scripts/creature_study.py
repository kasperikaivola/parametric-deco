"""Coarse contour/depth study: real planar profiles, no fabricated joinery claims."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from parametric_deco.geometry.creature_profiles import profiles, backing_outline
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
