"""ISF sources and PNG data, without an invented proprietary Wire patch schema."""

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


def export_isf_resources(atlas, out_dir, force=False):
    out = Path(out_dir)
    if out.exists() and any(out.iterdir()) and not force:
        raise FileExistsError(f"{out}: output exists; use --force")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".deco-visuals-", dir=out.parent) as tmp:
        stage = Path(tmp)
        for name, image in atlas.textures.items():
            image.save(stage / atlas.manifest["inputs"][name], compress_level=0)
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
        ("Wire/Arena shader compilation/runtime NOT RUN.",),
        {p.name: sha256(p.read_bytes()).hexdigest() for p in paths},
    )
