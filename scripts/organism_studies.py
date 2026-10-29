"""Coarse anatomical studies, explicitly before joinery; existing CAD renderer."""

from pathlib import Path
from parametric_deco.config import config_from_dict
from parametric_deco.geometry.organism import anatomy
from parametric_deco.model import Assembly, PartDefinition, PartInstance
from parametric_deco.export.views import render_views

for arrangement in ("whorl", "bilateral"):
    c = config_from_dict({"organism": {"arrangement": arrangement}})
    definitions, instances = [], []
    for lobe in anatomy(c):
        p = PartDefinition.from_polygon(lobe.name, lobe.shape, 6)
        definitions.append(p)
        instances.append(
            PartInstance(
                lobe.name,
                p.definition_id,
                p.revision,
                ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, lobe.z), (0, 0, 0, 1)),
                lobe.name,
                "armour",
            )
        )
    render_views(
        Assembly(tuple(definitions), tuple(instances)),
        Path("docs/implementation/images/organism-study") / arrangement,
    )
