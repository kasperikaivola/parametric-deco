"""ISF sources and PNG data, without an invented proprietary Wire patch schema."""

from dataclasses import asdict, replace
from hashlib import sha256
from importlib import resources
import json
import math
from pathlib import Path
import shutil
import tempfile

from ..model import ExportResult


def shader_metadata(source):
    start = source.index("/*") + 2
    end = source.index("*/", start)
    data = json.loads(source[start:end])
    if data.get("ISFVSN") != "2":
        raise ValueError("ISFVSN must be 2")
    return data


def pulse_reference(coordinate, edge, time, speed, phase, width):
    w = max(width, 1e-5)
    delta = abs((coordinate - time * speed - phase + 0.5) % 1 - 0.5)

    def smooth(a, b, x):
        t = min(1.0, max(0.0, (x - a) / (b - a)))
        return t * t * (3 - 2 * t)

    result = (1 - smooth(w * 0.5, w, delta)) * (1 - smooth(0.01, 0.04, edge))
    if not math.isfinite(result):
        raise ValueError("nonfinite shader reference")
    return result


def projection_shader(projection):
    from .settings import EFFECTS, COORDINATES, RANGES
    values = asdict(projection)
    entries = [{"NAME": name, "TYPE": "image"} for name in
               ("localData", "worldData", "worldFineData", "edgeData")]
    for key in ('effect', 'coordinate'):
        options = EFFECTS if key == 'effect' else COORDINATES
        entries.append({"NAME": key, "TYPE": "long", "VALUES": list(range(len(options))),
                        "LABELS": list(options), "DEFAULT": options.index(values[key])})
    for key in ('speed', 'phase', 'repeats', 'width', 'softness', 'edge_width', 'brightness'):
        name = 'edgeWidth' if key == 'edge_width' else key
        lo, hi = RANGES[key]
        entries.append({"NAME": name, "TYPE": "float", "MIN": lo, "MAX": hi,
                        "DEFAULT": values[key]})
    entries.append({"NAME": "edgeOnly", "TYPE": "bool", "DEFAULT": projection.edge_only})
    for key in ('color', 'background'):
        entries.append({"NAME": key, "TYPE": "color", "DEFAULT": values[key]})
    header = {"ISFVSN": "2", "DESCRIPTION": "Parametric Deco configurable surface content",
              "CATEGORIES": ["Generator"], "INPUTS": entries}
    shared = resources.files('parametric_deco.resources').joinpath('projection.glsl').read_text()
    return '/*' + json.dumps(header, indent=2) + '*/\n' + shared + """
void main() {
    vec4 local = IMG_NORM_PIXEL(localData, isf_FragNormCoord);
    vec4 world = IMG_NORM_PIXEL(worldData, isf_FragNormCoord);
    vec4 fine = IMG_NORM_PIXEL(worldFineData, isf_FragNormCoord);
    world.rgb = (255.0 * world.rgb + fine.rgb - 0.5) / 255.0;
    vec4 edge = IMG_NORM_PIXEL(edgeData, isf_FragNormCoord);
    gl_FragColor = decoEffect(local, world, edge, TIME);
}
"""


def export_isf_resources(atlas, out_dir, force=False, *, projection=None):
    out = Path(out_dir)
    if out.exists() and any(out.iterdir()) and not force:
        raise FileExistsError(f"{out}: output exists; use --force")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".deco-visuals-", dir=out.parent) as tmp:
        stage = Path(tmp)
        for name, image in atlas.textures.items():
            image.save(stage / atlas.manifest["inputs"][name], compress_level=0)
        if projection is not None:
            mode = atlas.manifest['surface_selection']['mode']
            projection = replace(projection, atlas_width=atlas.manifest['dimensions'][0],
                                 atlas_height=atlas.manifest['dimensions'][1],
                                 surfaces=mode if mode != 'explicit' else projection.surfaces)
            selection = {**atlas.manifest['surface_selection'],
                         'surface_ids':[tile['tile_id'] for tile in atlas.manifest['tiles']]}
            (stage / 'projection-selection.json').write_text(json.dumps(selection, indent=2)+'\n')
            from .settings import projection_errors
            errors = list(projection_errors(projection))
            if errors:
                raise ValueError('; '.join(errors))
            (stage / 'projection.fs').write_text(projection_shader(projection))
            (stage / 'projection.json').write_text(json.dumps(asdict(projection), indent=2) + '\n')
        for name in ("calibration.fs", "edge-pulse.fs"):
            source = resources.files("parametric_deco.resources").joinpath(name).read_text()
            for entry in shader_metadata(source)["INPUTS"]:
                if entry["TYPE"] == "image" and entry["NAME"] not in atlas.manifest["inputs"]:
                    raise ValueError(f"{name}: missing image input {entry['NAME']}")
            (stage / name).write_text(source)
        (stage / "atlas.json").write_text(
            json.dumps(atlas.manifest, indent=2, allow_nan=False) + "\n"
        )
        out.mkdir(parents=True, exist_ok=True)
        for path in stage.iterdir():
            shutil.copy2(path, out / path.name)
    paths = tuple(sorted(p for p in out.iterdir() if p.is_file()))
    return ExportResult(
        paths,
        (),
        {p.name: sha256(p.read_bytes()).hexdigest() for p in paths},
    )
