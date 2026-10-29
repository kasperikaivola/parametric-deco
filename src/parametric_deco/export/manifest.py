"""Transactional exports and auditable assembly/manufacturing manifests."""

from collections import Counter
from hashlib import sha256
from importlib import metadata, resources
import json
from pathlib import Path
import shutil
import tempfile

from ..config import CuttingBed
from ..geometry.joints import fit_coupon
from ..model import ExportResult, Inventory
from .scene import write_scene
from .svg import place_sheets, svg_document, write_part_svg


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _safe_output_path(out, name):
    if not isinstance(name, str):
        raise ValueError("manifest/output path must be a string")
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError(f"unsafe manifest/output path: {name!r}")
    candidate = out / relative
    if not candidate.resolve().is_relative_to(out.resolve()):
        raise ValueError(f"unsafe manifest/output path: {name!r}")
    for component in (candidate, *candidate.parents):
        if component == out:
            break
        if component.is_symlink():
            raise ValueError(f"symlink in manifest/output path: {name!r}")
    return candidate


def _obsolete_owned_files(out, stage):
    current = {p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()}
    for name in current:
        _safe_output_path(out, name)
    previous = out / "manifest.json"
    if not previous.exists():
        return []
    if previous.is_symlink():
        raise ValueError("symlink in manifest/output path: manifest.json")
    try:
        owned = json.loads(previous.read_text())["files"]
        if not isinstance(owned, dict):
            raise ValueError("files must be an object")
    except (ValueError, KeyError, TypeError) as error:
        raise ValueError(f"invalid previous manifest: {error}") from error
    obsolete = []
    for name, expected_hash in owned.items():
        path = _safe_output_path(out, name)
        if name in current or not path.exists():
            continue
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ValueError(f"modified obsolete generated file: {name}; move it before rebuilding")
        obsolete.append(path)
    return obsolete


def export_build(build, out_dir, force=False):
    out = Path(out_dir)
    if out.exists() and (not out.is_dir() or any(out.iterdir())) and not force:
        raise FileExistsError(f"{out}: output exists; use --force explicitly")
    if not build.report.digital_valid:
        raise ValueError(
            "assembly invalid: "
            + "; ".join(i.message for i in build.report.issues if i.severity == "error")
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".deco-export-", dir=out.parent) as staging:
        stage = Path(staging)
        _export_into(build, stage)
        # Validate ownership before changing anything; never delete arbitrary user paths.
        obsolete = _obsolete_owned_files(out, stage)
        out.mkdir(parents=True, exist_ok=True)
        for path in obsolete:
            path.unlink()
            parent = path.parent
            while parent != out:
                try:
                    parent.rmdir()
                except OSError:
                    break
                parent = parent.parent
        for path in sorted(stage.rglob("*")):
            target = out / path.relative_to(stage)
            if path.is_dir():
                target.mkdir(exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
    paths = tuple(sorted(p for p in out.rglob("*") if p.is_file()))
    return ExportResult(
        paths,
        build.warnings,
        {p.relative_to(out).as_posix(): sha256(p.read_bytes()).hexdigest() for p in paths},
    )


def _export_into(build, out):
    from ..config import config_from_dict

    config = config_from_dict(build.provenance["config"])
    counts = Counter((i.definition_id, i.revision) for i in build.assembly.instances)
    cuts = out / "cuts"
    cuts.mkdir()
    part_counts = []
    for part in build.fabrication_parts:
        count = counts[part.definition_id, part.revision]
        if count:
            write_part_svg(part, cuts / f"{part.definition_id}-{part.revision}.svg")
            part_counts.append((part, count))
    coupon = fit_coupon(config)
    write_part_svg(coupon, cuts / "fit-coupon.svg")
    part_counts.append((coupon, 1))
    (cuts / "scale-check.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="110mm" height="15mm" '
        'viewBox="0 0 110 15"><g id="engrave" fill="none" stroke="blue">'
        '<path d="M5 3 V10 M5 7 H105 M105 3 V10"/></g>'
        '<text x="5" y="14" font-size="3">100 mm between end marks</text></svg>'
    )
    if config.cutting_bed:
        bed = CuttingBed(**build.provenance["config"]["cutting_bed"])
        sheets = place_sheets(part_counts, bed)
        (out / "sheets").mkdir()
        for index, items in enumerate(sheets):
            (out / "sheets" / f"sheet-{index + 1}.svg").write_text(
                svg_document(
                    items,
                    bed.width_mm,
                    bed.height_mm,
                    f"0 {-bed.height_mm:g} {bed.width_mm:g} {bed.height_mm:g}",
                )
            )
    write_json(out / "assembly.json", build.assembly.to_dict())
    write_json(
        out / "inventory.json",
        (
            build.inventory or Inventory(build.assembly.definitions, build.assembly.instances)
        ).to_dict(),
    )
    write_json(out / "validation.json", build.report.to_dict())
    write_scene(build.assembly, out)
    from .views import render_views

    render_views(build.assembly, out / "views")
    viewer = out / "preview"
    viewer.mkdir()
    for filename in ("index.html", "viewer.js", "NOTICE.txt"):
        (viewer / filename).write_text(
            resources.files("parametric_deco.resources").joinpath(filename).read_text()
        )
    (out / "assembly-instructions.md").write_text(
        resources.files("parametric_deco.resources")
        .joinpath(
            "creature-assembly-instructions.md"
            if config.creature
            else "radial-assembly-instructions.md"
            if build.assembly.composition
            else "assembly-instructions.md"
        )
        .read_text()
    )
    if config.creature:
        from ..visuals.visibility import projection_visibility

        write_json(out / "projection-visibility.json", projection_visibility(build.assembly))
    versions = {
        n: metadata.version(n)
        for n in ("parametric-deco", "build123d", "numpy", "shapely", "trimesh", "pillow")
    }
    manifest = {
        "schema_version": 1,
        "units": "mm",
        "coordinate_system": "X right, Y up, Z outward",
        "kerf_compensation": "laser_software_only",
        "contours": "nominal_finished",
        "hole_approximation": {"backplate_segments": 32, "root_segments": 64},
        "nested_layout_valid": config.cutting_bed is not None,
        "parts": [
            {
                "definition_id": d.definition_id,
                "revision": d.revision,
                "quantity": n,
                "fingerprint": d.fingerprint,
            }
            for d, n in part_counts
        ],
        "composition": build.assembly.composition,
        "warnings": build.warnings,
        "validation": build.report.to_dict(),
        "provenance": build.provenance,
        "dependency_versions": versions,
        "hardware": "conservative envelope proxies, not bolt specification",
        "files": {
            p.relative_to(out).as_posix(): sha256(p.read_bytes()).hexdigest()
            for p in sorted(out.rglob("*"))
            if p.is_file()
        },
    }
    write_json(out / "manifest.json", manifest)
