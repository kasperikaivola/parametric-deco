"""Export comparison representatives and render both views from each saved assembly.

Run from the repository root: python scripts/design_gallery.py
"""
from hashlib import sha256
from pathlib import Path

import numpy as np

from parametric_deco.assembly import assemble
from parametric_deco.config import load_config
from parametric_deco.export.manifest import write_json
from parametric_deco.export.scene import write_scene
from parametric_deco.export.views import render_views
from parametric_deco.model import Assembly, digest
from parametric_deco.validation import instance_bounds


REPRESENTATIVES = {'laminar': 'organism-low',
                   'layered-creature': 'creature-alien-six',
                   'radial-weave': 'radial-weave'}


def main():
    root = Path(__file__).resolve().parents[1]
    evidence = {}
    for style, example in REPRESENTATIVES.items():
        print(f'{style}: {example}', flush=True)
        config = load_config(root / 'examples' / f'{example}.json')
        build = assemble(config)
        if not build.report.digital_valid:
            raise ValueError(f'{example}: {build.report.to_dict()}')
        exported = root / 'build/gallery' / example
        exported.mkdir(parents=True, exist_ok=True)
        write_json(exported / 'config.json', config.to_dict())
        write_json(exported / 'assembly.json', build.assembly.to_dict())
        write_json(exported / 'inventory.json', build.inventory.to_dict())
        write_json(exported / 'validation.json', build.report.to_dict())
        # Reload the exact exported model: front, quarter and GLB share this record.
        import json
        assembly = Assembly.from_dict(json.loads((exported / 'assembly.json').read_text()))
        write_scene(assembly, exported)
        images = root / 'docs/implementation/images/gallery' / style
        render_views(assembly, images, views=('front', 'three-quarter'))
        bounds = np.array([instance_bounds(assembly.definition_for(i), i.transform)
                           for i in assembly.instances if i.role != 'backplate'])
        low, high = bounds[:, 0].min(axis=0), bounds[:, 1].max(axis=0)
        board_bounds = np.array([instance_bounds(assembly.definition_for(i), i.transform)
                                 for i in assembly.instances if i.role == 'backplate'])
        evidence[style] = {
            'example': f'examples/{example}.json',
            'export_directory': f'build/gallery/{example}',
            'assembly_sha256': sha256((exported / 'assembly.json').read_bytes()).hexdigest(),
            'config_hash': digest(config.to_dict()),
            'non_board_cut_fingerprints_hash': digest(sorted(
                d.fingerprint for d in assembly.definitions if d.kind != 'backplate')),
            'non_board_bounds_mm': [low.tolist(), high.tolist()],
            'non_board_center_mm': ((low + high) / 2).tolist(),
            'vertical_board_margins_mm': {
                'bottom': float(low[1] - board_bounds[:, 0, 1].min()),
                'top': float(board_bounds[:, 1, 1].max() - high[1]),
            },
            'placement_offset_mm': (assembly.composition or {}).get('placement_offset_mm'),
            'rotation_deg': (assembly.composition or {}).get('rotation_deg'),
            'instances': len(assembly.instances),
            'validation': build.report.to_dict(),
            'view_assembly_sha256': {view: sha256((exported / 'assembly.json').read_bytes()).hexdigest()
                                     for view in ('front', 'three-quarter')},
            'images_sha256': {view: sha256((images / f'{view}.png').read_bytes()).hexdigest()
                              for view in ('front', 'three-quarter')},
        }
    write_json(root / 'docs/implementation/gallery-evidence.json', evidence)


if __name__ == '__main__':
    main()
