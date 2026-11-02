"""Render all 15 example configurations once; scene, views and evidence share one CAD.

python scripts/design_gallery.py [--reuse]
--reuse consumes already exported result.json records (no regeneration).
"""
import argparse
from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path
import shutil

import numpy as np
from shapely.geometry import Point

from parametric_deco.assembly import assemble
from parametric_deco.config import load_config
from parametric_deco.export.manifest import write_json
from parametric_deco.export.scene import write_scene
from parametric_deco.export.views import render_views
from parametric_deco.model import Assembly, BuildResult, Inventory, Issue, ValidationReport, digest
from parametric_deco.validation import instance_bounds
from parametric_deco.supports import verify_supports, physical_paths, path_fraction, path_limit, end_covered, REVISION
from parametric_deco.geometry.symmetry import kind as symmetry_kind, verify_symmetry

REPRESENTATIVES = {'laminar': 'organism-low', 'layered-creature': 'creature-alien-six',
                   'radial-weave': 'radial-weave', 'rib-study': 'single-module'}
EXAMPLES = ('organism-low', 'organism-medium', 'organism-high', 'organism-bilateral',
            'organism-small', 'organism-large', 'creature-alien-two', 'creature-mask',
            'creature-mask-raised', 'creature-alien-six', 'radial-weave',
            'radial-weave-reconfigured', 'single-module', 'intertwined', 'reconfigured')
REPLAYS = {'creature-mask-raised': 'creature-mask',
           'radial-weave-reconfigured': 'radial-weave', 'reconfigured': 'intertwined'}


def save_result(build, path):
    write_json(path, {'assembly': build.assembly.to_dict(), 'inventory': build.inventory.to_dict(),
                      'warnings': build.warnings, 'provenance': build.provenance,
                      'report': build.report.to_dict()})


def load_result(path):
    data = json.loads(path.read_text())
    a = Assembly.from_dict(data['assembly'])
    report = data['report']
    return BuildResult(a, tuple(d for d in a.definitions if d.kind != 'purchased-hardware'),
                       tuple(data['warnings']), data['provenance'],
                       ValidationReport(tuple(Issue(**i) for i in report['issues'])),
                       Inventory.from_dict(data['inventory']))


def upright_evidence(a):
    """Quantify retained local joinery separately from the long-panel end clamps."""
    result = []
    levels = {m['module_id']: m.get('level') for m in (a.composition or {}).get('modules', [])}
    for i in a.instances:
        if i.role not in ('rib', 'blade', 'register'):
            continue
        part = a.definition_for(i)
        entry = {'part_id': i.instance_id, 'role': i.role,
                 'local_bounds_mm': list(part.polygon.bounds),
                 'board_load_path': 'captured join to grid-clamped structural panel'}
        if i.role == 'rib' and levels.get(i.module_id):
            planes = [102, 126, 152] if levels[i.module_id] == 'high' else [20, 44, 70]
            if abs(part.polygon.bounds[1]) < 1e-7:
                planes.insert(0, 0)
                entry['board_foot_bearing'] = True
            entry['local_bearing_heights_mm'] = planes
            entry['crest_above_capture_rail_mm'] = max(0, part.polygon.bounds[3] - planes[-1] - part.thickness_mm)
        elif i.role == 'rib':
            centers = [s.datum_mm for s in part.interfaces]
            entry['joinery'] = 'paired perpendicular spine notches plus top closure bearing/capture'
            entry['joint_datum_mm'] = centers
        elif i.role == 'blade':
            entry['joinery'] = '28 mm closed cap seat, shoulder bearing and transverse retained key'
            entry['decorative_fin'] = True
            entry['physical_bending_stiffness'] = 'NOT RUN'
        else:
            entry['joinery'] = 'closed layer slots; board/lower-plate and cap withdrawal restraint'
        result.append(entry)
    return result


def annotate_mounting(a, images):
    """Overlay station IDs on the already rendered actual hardware, without rerendering."""
    from PIL import Image, ImageDraw, ImageFont
    from parametric_deco.cad import mesh_for
    from parametric_deco.export.views import project_vertices
    selected = [i for i in a.instances if i.role in ('backplate', 'mounting-hardware')]
    for view in ('front', 'three-quarter'):
        projected = []
        for i in selected:
            mesh = mesh_for(a.definition_for(i))
            pose = np.array(i.transform)
            vertices = mesh.vertices @ pose[:3, :3].T + pose[:3, 3]
            projected.append(project_vertices(vertices, view))
        points = np.concatenate(projected)
        low, high = points[:, :2].min(axis=0), points[:, :2].max(axis=0)
        center = (low + high) / 2
        extent = np.maximum(high - low, 1)
        scale = min(980 / extent[0], 710 / extent[1])
        output_path = images / 'mounting' / f'{view}.png'
        image = Image.open(output_path).convert('RGB')
        draw = ImageDraw.Draw(image)
        draw.text((36, 85), 'DECO CONTOURS / cyan R-T = actual medial paths / numbers = end-clamp IDs',
                  fill='#a8cadb', font=ImageFont.load_default(size=16))
        # Actual deco contours retain their true XY/Z poses. Transparent wire
        # outlines reveal the hardware while making each end support legible.
        for panel in a.instances:
            if panel.role not in ('armour', 'cap', 'spine', 'closure'):
                continue
            part = a.definition_for(panel)
            pose = np.array(panel.transform)
            ring = np.array([(*p, part.thickness_mm, 1) for p in (*part.outer, part.outer[0])])
            world = (ring @ pose.T)[:, :3]
            projected_ring = project_vertices(world, view)
            pixels = (projected_ring[:, :2] - center) * scale * (1, -1) + (550, 465)
            draw.line([tuple(p) for p in pixels], fill='#d9b178', width=1)
            if panel.role in ('cap', 'closure') or a.composition.get('family') == 'laminar-organism-v2':
                anchor = part.polygon.representative_point()
                world_anchor = pose @ np.array((anchor.x, anchor.y, part.thickness_mm, 1))
                point = project_vertices(np.array([world_anchor[:3]]), view)[0]
                xy = (point[:2] - center) * scale * (1, -1) + (550, 465)
                draw.text(tuple(xy), panel.module_id, fill='#edca94',
                          font=ImageFont.load_default(size=12), stroke_width=2, stroke_fill='#12151b')
        from parametric_deco.config import config_from_dict
        config = config_from_dict(a.composition['support_config'])
        paths = physical_paths(a, config)
        by_id = {i.instance_id: i for i in a.instances}
        for pid, (path, kind) in paths.items():
            if kind not in ('laminar-medial', 'creature-limb'):
                continue
            part = by_id[pid]
            if kind == 'creature-limb' and part.role != 'cap':
                continue
            z = instance_bounds(a.definition_for(part), part.transform)[1, 2]
            vertices = np.array([[x, y, z] for x, y in path.coords])
            projected_path = project_vertices(vertices, view)
            pixels = (projected_path[:, :2] - center) * scale * (1, -1) + (550, 465)
            for index in range(0, len(pixels) - 1, 3):
                draw.line([tuple(v) for v in pixels[index:index + 2]], fill='#83c3d3', width=1)
            for label, point in (('R', pixels[0]), ('T', pixels[-1])):
                draw.ellipse((*tuple(point - 3), *tuple(point + 3)), outline='#83c3d3', width=1)
                draw.text(tuple(point + (4, -10)), label, fill='#83c3d3', font=ImageFont.load_default(size=12),
                          stroke_width=2, stroke_fill='#12151b')
        for station in a.composition['end_supports']['stations']:
            point = project_vertices(np.array([[*station['xy'], station['top_mm'] + 7]]), view)[0]
            xy = (point[:2] - center) * scale * (1, -1) + (550, 465)
            draw.text(tuple(xy + (5, 2)), station['id'].removeprefix('end-clamp-'),
                      fill='white', font=ImageFont.load_default(size=14), stroke_width=2,
                      stroke_fill='#12151b')
        image.save(output_path)


def manufactured_spans(a):
    from parametric_deco.config import config_from_dict
    config = config_from_dict(a.composition['support_config'])
    paths = physical_paths(a, config)
    result = []
    for pid, (path, kind) in paths.items():
        stations = [s for s in a.composition['end_supports']['stations'] if pid in s['plate_ids']]
        values = [(s['id'], path_fraction(path, kind, Point(s['xy']))) for s in stations]
        fractions = [path_fraction(path, kind, Point(s['xy'])) for s in stations
                     if kind not in ('laminar-medial', 'creature-limb') or path.distance(Point(s['xy'])) <= 60]
        cumulative = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.asarray(path.coords), axis=0), axis=1))]
        root_gap = float(np.interp(min(fractions), np.linspace(0, 1, len(cumulative)), cumulative)) if kind == 'radial-arc' else max(0, min(fractions)) * path.length
        distal_gap = path.length - float(np.interp(max(fractions), np.linspace(0, 1, len(cumulative)), cumulative)) if kind == 'radial-arc' else max(0, 1 - max(fractions)) * path.length
        result.append({'part_id': pid, 'criterion': kind,
                       'fraction_parameter': 'module angle' if kind == 'radial-arc' else 'path arclength',
                       'path_length_mm': path.length,
                       'root_mm': list(path.coords[0]), 'tip_mm': list(path.coords[-1]),
                       'end_region_fraction': path_limit(kind),
                       'path_offset_limit_mm': 60 if kind in ('laminar-medial', 'creature-limb') else None,
                       'root_support_ids': [s['id'] for s in stations if end_covered(path, kind, Point(s['xy']), 0)],
                       'distal_support_ids': [s['id'] for s in stations if end_covered(path, kind, Point(s['xy']), 1)],
                       'station_fractions': sorted(values, key=lambda item: item[1]),
                       'station_path_offsets_mm': {s['id']: path.distance(Point(s['xy'])) for s in stations},
                       'root_unbraced_path_mm': root_gap,
                       'distal_unbraced_path_mm': distal_gap})
    return result


def geometry_signature(a):
    return digest({'cuts': [(d.definition_id, d.revision, d.fingerprint) for d in a.definitions],
                   'instances': [asdict(i) for i in a.instances],
                   'hardware_bounds': a.hardware_bounds})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reuse', action='store_true')
    parser.add_argument('--resume', action='store_true', help='reuse models and already current images')
    args = parser.parse_args()
    reuse = args.reuse or args.resume
    root = Path(__file__).resolve().parents[1]
    builds, evidence = {}, {}
    for example in EXAMPLES:
        print(example, flush=True)
        config = load_config(root / 'examples' / f'{example}.json')
        exported = root / 'build/gallery' / example
        exported.mkdir(parents=True, exist_ok=True)
        if reuse:
            build = load_result(exported / 'result.json')
            if build.provenance['config_hash'] != digest(config.to_dict()):
                raise ValueError(example + ': cached config differs')
        else:
            build = assemble(config, builds[REPLAYS[example]].inventory if example in REPLAYS else None)
            save_result(build, exported / 'result.json')
        if not build.report.digital_valid:
            raise ValueError(f'{example}: {build.report.to_dict()}')
        builds[example] = build
        a = build.assembly
        support_issues = verify_supports(a)
        if support_issues:
            raise ValueError(f"{example}: {support_issues}")
        write_json(exported / 'config.json', config.to_dict())
        write_json(exported / 'assembly.json', a.to_dict())
        write_json(exported / 'inventory.json', build.inventory.to_dict())
        write_json(exported / 'validation.json', build.report.to_dict())
        images = root / 'docs/implementation/images/gallery/examples' / example
        outputs = [images / f'{view}.png' for view in ('front', 'three-quarter')]
        outputs += [images / 'mounting' / f'{view}.png' for view in ('front', 'three-quarter')]
        signature = geometry_signature(a)
        marker = images / 'render-geometry.sha256'
        signature_matches = marker.exists() and marker.read_text().strip() == signature
        current = args.resume and all(p.exists() for p in outputs) and signature_matches
        if not current:
            write_scene(a, exported)
            render_views(a, images, views=('front', 'three-quarter'))
            mounting = replace(a, instances=tuple(i for i in a.instances
                                if i.role in ('backplate', 'mounting-hardware')),
                               connections=(), composition=None)
            render_views(mounting, images / 'mounting', views=('front', 'three-quarter'))
            annotate_mounting(a, images)
        marker.write_text(signature + '\n')
        bounds = np.array([instance_bounds(a.definition_for(i), i.transform)
                           for i in a.instances if i.role not in ('backplate', 'mounting-hardware')])
        low, high = bounds[:, 0].min(axis=0), bounds[:, 1].max(axis=0)
        board = next(d for d in a.definitions if d.kind == 'backplate')
        entry = {'example': f'examples/{example}.json', 'style': config.style,
                 'configuration_kind': 'inventory pose/permutation' if example in REPLAYS else 'geometry preset',
                 'inventory_source': REPLAYS.get(example),
                 'export_directory': f'build/gallery/{example}',
                 'assembly_sha256': sha256((exported / 'assembly.json').read_bytes()).hexdigest(),
                 'config_hash': digest(config.to_dict()),
                 'backplate_fingerprint': board.fingerprint,
                 'backplate_stock_size_mm': [config.envelope.width_mm, config.envelope.height_mm],
                 'non_board_bounds_mm': [low.tolist(), high.tolist()],
                 'non_board_center_mm': ((low + high) / 2).tolist(),
                 'instances': len(a.instances), 'plywood_instances': len(build.inventory.instances),
                 'symmetry': {'group': symmetry_kind(config), 'actual_extruded_material_hardware_and_layer_orbits': 'PASS' if not verify_symmetry(a, config) else 'FAIL'},
                 'mounting': a.composition['end_supports'],
                 'upright_joinery': upright_evidence(a),
                 'manufactured_support_spans': manufactured_spans(a),
                 'validation': build.report.to_dict(),
                 'view_assembly_sha256': {v: sha256((exported / 'assembly.json').read_bytes()).hexdigest()
                                          for v in ('front', 'three-quarter')},
                 'images_sha256': {v: sha256((images / f'{v}.png').read_bytes()).hexdigest()
                                   for v in ('front', 'three-quarter')}}
        evidence[example] = entry
        write_json(images / 'mounting-evidence.json', {'backplate': a.composition['universal_backplate'],
                                                      'end_supports': entry['mounting'],
                                                      'upright_joinery': entry['upright_joinery'],
                                                      'manufactured_support_spans': entry['manufactured_support_spans'],
                                                      'symmetry': entry['symmetry']})
        if example == REPRESENTATIVES.get(config.style):
            alias = root / 'docs/implementation/images/gallery' / config.style
            alias.mkdir(parents=True, exist_ok=True)
            for view in ('front', 'three-quarter'):
                shutil.copyfile(images / f'{view}.png', alias / f'{view}.png')
    write_json(root / 'docs/implementation/gallery-evidence.json', evidence)
    groups = {}
    for name, entry in evidence.items():
        size = 'x'.join(str(int(v)) for v in entry['backplate_stock_size_mm'])
        groups.setdefault(size, set()).add(entry['backplate_fingerprint'])
    if any(len(values) != 1 for values in groups.values()):
        raise ValueError('incompatible physical boards within a shared stock-size group')
    write_json(root / 'docs/implementation/support-validation.json', {
        'manufacturing_revision': REVISION,
        'examples_checked': len(evidence),
        'common_board_fingerprints_by_stock_size': {k: sorted(v) for k, v in groups.items()},
        'checks': 'independent family root/distal paths or arc/straight span, actual grid axes, bores/7mm webs, hardware axes/envelope/corridors, gap tubes, all-parts graph; exact extruded material and complete support/hardware symmetry orbits',
        'physical_validation': 'NOT RUN', 'Wire_Arena_validation': 'NOT RUN',
        'examples': {name: {'end_axes': len(e['mounting']['stations']),
            'structural_panels': len(e['mounting']['spans']),
            'all_parts_reach_backplate': e['mounting']['all_parts_reach_backplate'],
            'manufactured_support_spans': e['manufactured_support_spans']}
            for name, e in evidence.items()},
    })
    text = ['# All implemented families and examples', '',
            'There are **four implemented generators**, with 15 style-bearing example configurations. '
            '`examples/inventory.json` is a saved inventory input, not another design family or preset.', '',
            'Front (+Z onto XY) and three-quarter cameras, materials and framing are matched. '
            'Blue-grey parts are actual modeled end-clamp tubes, bolts, washers, heads and nuts. '
            'Mounting views show the actual deco contours transparently with hardware visible through them, plus the common hole grid; cyan R-T traces identify actual curved root/distal paths, and station numbers/module labels link to exact end-clamp IDs in the evidence. '
            'Original root/clip hardware remains simplified. Physical and Wire/Arena checks are **NOT RUN**.', '',
            'Every 1000 × 1000 example uses the identical manufactured board fingerprint; '
            '800 and 1400 mm size presets require separate board stock sizes with the same equilateral triangular grid (50 mm X, 25√3 mm rows, 25 mm stagger). '
            'Family-specific eye/aperture/trestle cuts are absent from the universal board. '
            'The common board stays behind the artwork voids. Standard laminar presets repeat exact120° sectors including mounts; organism-bilateral is explicitly mirrored instead. Creature geometry and every support stack are exact left/right reflections.', '',
            '| Example | Family / configuration | Front | Three-quarter | End clamps / panel spans | Mounting evidence |',
            '| --- | --- | --- | --- | --- | --- |']
    for name, e in evidence.items():
        image = f'images/gallery/examples/{name}'
        text.append(f'| [{name}](../../{e["example"]}) | {e["style"]} · {e["configuration_kind"]} | '
                    f'![]({image}/front.png) | ![]({image}/three-quarter.png) | '
                    f'{len(e["mounting"]["stations"])} axes / {len(e["mounting"]["spans"])} panels | '
                    f'[front]({image}/mounting/front.png), [off-axis]({image}/mounting/three-quarter.png), '
                    f'[exact stations/joins]({image}/mounting-evidence.json) |')
    text += ['', 'The three replay configurations above use their named source inventory unchanged. '
             'The stock board, cut revisions and physical instance IDs are preserved; only supported placements change. '
             'Any off-grid or obstructed requested placement fails validation instead of drilling new holes.', '',
             'See [mounting design](mounting.md), [machine-readable gallery evidence](gallery-evidence.json) '
             'and the [design guide](../design.md). Older images under `images/flow-organism` are historical '
             'trestle prototypes, not the current universal-board manufacturing revision.', '']
    (root / 'docs/implementation/gallery.md').write_text('\n'.join(text))


if __name__ == '__main__':
    main()
