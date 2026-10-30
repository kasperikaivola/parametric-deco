"""One disposable CAD subprocess. Never imports Qt or changes saved inventory."""
from importlib import resources
import json
from pathlib import Path
import sys
import traceback

from .desktop_state import fingerprint


def run_request(request):
    from .assembly import assemble
    from .config import config_from_dict
    from .model import Inventory

    config = config_from_dict(request['config'])
    inventory_data = request.get('inventory')
    inventory = Inventory.from_dict(inventory_data) if inventory_data is not None else None
    print('Constructing and validating physical CAD…', flush=True)
    build = assemble(config, inventory)
    if not build.report.digital_valid:
        raise ValueError('; '.join(i.message for i in build.report.issues if i.severity == 'error'))
    out = Path(request['out'])
    if request['mode'] == 'export':
        from .export.manifest import export_build
        print('Writing transactional export…', flush=True)
        result = export_build(build, out, force=request.get('force', False))
        paths = len(result.paths)
    elif request['mode'] == 'preview':
        from .export.scene import write_scene
        print('Meshing validated CAD for orbit preview…', flush=True)
        write_scene(build.assembly, out)
        preview = out / 'preview'
        preview.mkdir()
        package = resources.files('parametric_deco.resources')
        html = package.joinpath('index.html').read_text()
        # Local script avoids file:// fetch restrictions without a server or remote access.
        html = html.replace('<script src="viewer.js">',
                            '<script src="scene-data.js"></script><script src="viewer.js">')
        html = html.replace('<p><a href="../manifest.json">Manifest</a> · '
                            '<a href="../assembly.glb">GLB</a> · '
                            '<a href="../assembly-instructions.md">Assembly sequence</a></p>', '')
        (preview / 'index.html').write_text(html)
        (preview / 'viewer.js').write_text(package.joinpath('viewer.js').read_text())
        (preview / 'scene-data.js').write_text('window.decoScene=' +
                                             (out / 'scene.json').read_text() + ';')
        paths = 0
    else:
        raise ValueError('unknown desktop worker mode')
    return {'digital_valid': True, 'fingerprint': fingerprint(config.to_dict(), inventory_data),
            'files': paths, 'warnings': list(build.warnings),
            'validation': build.report.to_dict()}


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
