"""Regenerate only the three comparison representatives, using actual CAD meshes.

Run from the repository root: python scripts/design_gallery.py
"""
from pathlib import Path

from parametric_deco.assembly import assemble
from parametric_deco.config import load_config
from parametric_deco.export.views import render_views


REPRESENTATIVES = {'laminar': 'organism-low',
                   'layered-creature': 'creature-alien-six',
                   'radial-weave': 'radial-weave'}


def main():
    root = Path(__file__).resolve().parents[1]
    for style, example in REPRESENTATIVES.items():
        print(f'{style}: {example}', flush=True)
        build = assemble(load_config(root / 'examples' / f'{example}.json'))
        if not build.report.digital_valid:
            raise ValueError(f'{example}: {build.report.to_dict()}')
        render_views(build.assembly, root / 'docs/implementation/images/gallery' / style,
                     views=('front', 'three-quarter'))


if __name__ == '__main__':
    main()
