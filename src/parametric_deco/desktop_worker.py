"""One disposable CAD subprocess. Never imports Qt or changes saved inventory."""
from dataclasses import asdict
from importlib import resources
import json
from pathlib import Path
import sys
import traceback

from .desktop_state import fingerprint, cad_fingerprint


def run_request(request):
    from .assembly import assemble
    from .config import config_from_dict
    from .model import Inventory

    config = config_from_dict(request['config'])
    inventory_data = request.get('inventory')
    inventory = Inventory.from_dict(inventory_data) if inventory_data is not None else None
    if request['mode'] == 'projection':
        from .model import Assembly
        from .visuals.preview import write_projection
        source, out = Path(request['source']), Path(request['out'])
        out.mkdir(parents=True, exist_ok=True)
        assembly = Assembly.from_dict(json.loads((source / 'assembly.json').read_text()))
        scene = json.loads((source / 'scene.json').read_text())
        scene['projection'] = write_projection(assembly, out, config.projection)
        (out / 'scene.json').write_text(json.dumps(scene))
        (out / 'assembly.json').write_text((source / 'assembly.json').read_text())
        _write_preview(out)
        return {'digital_valid': True, 'fingerprint': cad_fingerprint(config.to_dict(), inventory_data),
                'files': 0, 'projection_settings': asdict(config.projection),
                'projection_error': scene['projection'].get('error')}
    print('PROGRESS phase=construct fraction=0.02', flush=True)
    build = assemble(config, inventory)
    if not build.report.digital_valid:
        raise ValueError('; '.join(i.message for i in build.report.issues if i.severity == 'error'))
    out = Path(request['out'])
    if request['mode'] == 'export':
        from .export.manifest import export_build
        print('PROGRESS phase=export fraction=0.88', flush=True)
        result = export_build(build, out, force=request.get('force', False))
        paths = len(result.paths)
    elif request['mode'] == 'preview':
        from .export.scene import write_scene
        print('PROGRESS phase=mesh fraction=0.93', flush=True)
        write_scene(build.assembly, out, config.projection)
        (out / 'assembly.json').write_text(json.dumps(build.assembly.to_dict()))
        _write_preview(out)
        paths = 0
    else:
        raise ValueError('unknown desktop worker mode')
    identity = fingerprint if request['mode'] == 'export' else cad_fingerprint
    return {'digital_valid': True, 'fingerprint': identity(config.to_dict(), inventory_data),
            'files': paths, 'projection_settings': asdict(config.projection),
            'warnings': list(build.warnings), 'validation': build.report.to_dict(),
            'projection_error': (json.loads((out/'scene.json').read_text()).get(
                'projection', {}).get('error'))}


def _write_preview(out):
    preview = out / 'preview'
    preview.mkdir(exist_ok=True)
    package = resources.files('parametric_deco.resources')
    html = package.joinpath('index.html').read_text()
    html = html.replace('<script src="viewer.js">',
                        '<script src="scene-data.js"></script><script src="viewer.js">')
    html = html.replace('<p><a href="../manifest.json">Manifest</a> · '
                        '<a href="../assembly.glb">GLB</a> · '
                        '<a href="../assembly-instructions.md">Assembly sequence</a></p>', '')
    (preview / 'index.html').write_text(html)
    for name in ('viewer.js', 'projection.js'):
        (preview / name).write_text(package.joinpath(name).read_text())
    (preview / 'scene-data.js').write_text('window.decoScene=' +
                                         (out / 'scene.json').read_text() + ';')


def main():
    request_path, result_path = map(Path, sys.argv[1:3])
    try:
        result = run_request(json.loads(request_path.read_text()))
    except Exception as error:
        traceback.print_exc()
        result_path.write_text(json.dumps({'error': str(error)}))
        return 1
    result_path.write_text(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
