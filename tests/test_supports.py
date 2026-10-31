"""Independent failures for clustered supports, missing stock interfaces and floating parts."""
from copy import deepcopy
from functools import lru_cache
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import Point, Polygon, box, LineString

from parametric_deco.config import load_config
from parametric_deco.geometry.backplate import generate_backplate, mounting_holes
from parametric_deco.model import PartDefinition, PartInstance
from parametric_deco.supports import span_axis, verify_supports
from parametric_deco.validation import xy_footprint

ROOT = Path(__file__).resolve().parents[1]


def build_example(name):
    # Reuse exact gallery CAD when this focused local check follows rendering.
    # CI creates the same examples through the public pipeline when no cache exists.
    path = ROOT / 'build/gallery' / name / 'result.json'
    if path.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location('design_gallery', ROOT / 'scripts/design_gallery.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.load_result(path)
    from parametric_deco.assembly import assemble
    return assemble(load_config(ROOT / 'examples' / f'{name}.json'))


@lru_cache(maxsize=16)
def independent_laminar_paths(config):
    from parametric_deco.geometry.organism import anatomy
    return {lobe.name: lobe.path for lobe in anatomy(config)}


def independent_path(a, config, part):
    pose = np.array(part.transform)
    if config.style == 'laminar':
        points = independent_laminar_paths(config)[part.module_id]
    elif config.style == 'layered-creature':
        if part.module_id == 'head':
            return None
        from parametric_deco.geometry.creature_profiles import limb_recipe, smooth
        points = smooth(limb_recipe(part.module_id, config.parameters)[0]) * config.parameters.scale
    elif config.style == 'radial-weave':
        index = int(part.module_id[1:])
        angles = np.linspace(index * np.pi / 3 + np.deg2rad(config.parameters.rotation_deg - 29.25),
                             index * np.pi / 3 + np.deg2rad(config.parameters.rotation_deg + 29.25), 401)
        radii = config.parameters.radius_mm + (1 if part.module_id[0] == 'a' else -1) * config.parameters.amplitude_mm * np.sin(3 * (angles - np.deg2rad(config.parameters.rotation_deg)))
        if part.role == 'closure':
            radii -= 26
        return LineString(np.column_stack((radii * np.cos(angles), radii * np.sin(angles))))
    else:
        spine = next(i for i in a.instances if i.module_id == part.module_id and i.role == 'spine')
        lo, _, hi, _ = a.definition_for(spine).polygon.bounds
        points = np.array(((lo, 0), (hi, 0)))
    vertices = np.array([(*p, 0, 1) for p in points]) @ pose.T
    return LineString(vertices[:, :2])


def test_same_physical_board_for_every_nominal_preset():
    boards = {}
    for path in (ROOT / 'examples').glob('*.json'):
        if path.name == 'inventory.json':
            continue
        c = load_config(path)
        b = generate_backplate(c).definitions[0]
        key = (c.envelope.width_mm, c.envelope.height_mm)
        boards.setdefault(key, set()).add((b.definition_id, b.revision, b.fingerprint))
        assert len(b.holes) == len(mounting_holes(c))
        for hole in mounting_holes(c):
            assert any(Polygon(r).centroid.distance(Point(hole.x_mm, hole.y_mm)) < 1e-7
                       for r in b.holes)
    assert set(boards) == {(800, 800), (1000, 1000), (1400, 1400)}
    assert all(len(values) == 1 for values in boards.values())


@pytest.mark.parametrize('name', ['organism-low', 'organism-medium', 'organism-high',
    'organism-bilateral', 'organism-small', 'organism-large', 'creature-alien-two',
    'creature-mask', 'creature-mask-raised', 'creature-alien-six', 'radial-weave',
    'radial-weave-reconfigured', 'single-module', 'intertwined', 'reconfigured'])
def test_actual_end_stations_bores_columns_and_all_parts_load_paths(name):
    build = build_example(name)
    a = build.assembly
    assert build.report.digital_valid, build.report.to_dict()
    assert not verify_supports(a)
    by_id = {i.instance_id: i for i in a.instances}
    plan = a.composition['end_supports']
    stations = {s['id']: s for s in plan['stations']}
    physical_grid = {(round(h.x_mm, 6), round(h.y_mm, 6))
                     for h in mounting_holes(load_config(ROOT / 'examples' / f'{name}.json'))}
    for s in stations.values():
        assert tuple(round(v, 6) for v in s['xy']) in physical_grid
        # No offset adapters: every real tube/shaft/washer axis is the same board bore.
        for hid in s['hardware_ids']:
            assert np.allclose(np.array(by_id[hid].transform)[:2, 3], s['xy'])
    config = load_config(ROOT / 'examples' / f'{name}.json')
    for part in a.instances:
        if part.role not in ('armour', 'cap', 'spine', 'closure') or abs(part.transform[2][2]) < 1 - 1e-8:
            continue
        path = independent_path(a, config, part)
        if path is None:  # Broad head shells are not directional appendages.
            continue
        matching = [station for station in stations.values() if part.instance_id in station['plate_ids']]
        if config.style == 'radial-weave':
            center = np.deg2rad(int(part.module_id[1:]) * 60 + config.parameters.rotation_deg)
            values = [((np.arctan2(station['xy'][1], station['xy'][0]) - center + np.pi) % (2 * np.pi) - np.pi + np.deg2rad(29.25)) / np.deg2rad(58.5)
                      for station in matching]
        else:
            values = [path.project(Point(station['xy']), normalized=True) for station in matching
                      if config.style not in ('laminar', 'layered-creature') or path.distance(Point(station['xy'])) <= 60]
        limit = .315 if config.style == 'radial-weave' else .30
        assert min(values) <= limit + 1e-6, (part.instance_id, values)
        assert max(values) >= 1 - limit - 1e-6, (part.instance_id, values)
    if name == 'radial-weave':
        levels = {m['module_id']: m['level'] for m in a.composition['modules']}
        assert all(a.definition_for(i).polygon.bounds[3] <= 76 + 1e-6
                   for i in a.instances if i.role == 'rib' and levels[i.module_id] == 'low')


@pytest.fixture(scope='module')
def single():
    return build_example('single-module').assembly


def test_two_holes_in_one_root_cluster_are_not_end_support(single):
    metadata = deepcopy(single.composition)
    span = metadata['end_supports']['spans'][0]
    first = metadata['end_supports']['stations'][0]['xy']
    for station in metadata['end_supports']['stations']:
        station['xy'] = list(first)
    span['station_ids'] = [span['station_ids'][0]] * 2
    assert any(i.code == 'end_support_path' for i in verify_supports(replace(single, composition=metadata)))


def test_missing_tube_and_shifted_board_axis_fail(single):
    station = single.composition['end_supports']['stations'][0]
    tube = next(name for name in station['hardware_ids'] if '-tube-' in name)
    damaged = replace(single, instances=tuple(i for i in single.instances if i.instance_id != tube))
    codes = {i.code for i in verify_supports(damaged)}
    assert {'support_hardware', 'support_column'} <= codes
    metadata = deepcopy(single.composition)
    metadata['end_supports']['stations'][0]['xy'][0] += 1
    codes = {i.code for i in verify_supports(replace(single, composition=metadata))}
    assert {'support_grid', 'support_bore', 'support_hardware'} <= codes


def test_missing_board_bore_and_unconnected_cut_fail(single):
    board = next(i for i in single.instances if i.role == 'backplate')
    old = single.definition_for(board)
    station = single.composition['end_supports']['stations'][0]
    x, y = station['xy']
    damaged = PartDefinition.from_polygon(old.definition_id,
        old.polygon.union(Point(x, y).buffer(3.3)), old.thickness_mm, kind='backplate')
    a = replace(single, definitions=tuple(damaged if d == old else d for d in single.definitions),
                instances=tuple(replace(i, revision=damaged.revision) if i == board else i for i in single.instances))
    assert any(i.code == 'support_bore' for i in verify_supports(a))
    cut = PartDefinition.from_polygon('floating-probe', box(-5, -5, 5, 5), 6)
    a = replace(single, definitions=(*single.definitions, cut),
                instances=(*single.instances, PartInstance('floating-probe', cut.definition_id, cut.revision)))
    assert any(i.code == 'floating_part' for i in verify_supports(a))


def test_shared_radial_column_preserves_aperture_and_saved_hardware():
    base = build_example('radial-weave')
    replay = build_example('radial-weave-reconfigured')
    assert replay.inventory.to_dict() == base.inventory.to_dict()
    for build in (base, replay):
        a = build.assembly
        assert not verify_supports(a)
        for i in a.instances:
            if i.role != 'backplate':
                assert xy_footprint(a.definition_for(i), i.transform).distance(Point(0, 0)) >= 180 - 1e-6
        shared = [s for s in a.composition['end_supports']['stations'] if len(s.get('shared_modules', [])) > 1]
        assert shared
        for station in shared:
            assert len([h for h in station['hardware_ids'] if '-shaft-' in h]) == 1
            assert len(set(station['hardware_ids'])) == len(station['hardware_ids'])
            modules = {i.module_id for i in a.instances if i.instance_id in station['plate_ids']}
            assert modules == set(station['shared_modules'])
            assert len(modules) > 1


def test_saved_support_inventory_rejects_changed_physical_role():
    from parametric_deco.assembly import assemble
    build = build_example('single-module')
    inventory = build.inventory
    changed = replace(inventory.instances[1], role='spacer')
    damaged = replace(inventory, instances=(inventory.instances[0], changed, *inventory.instances[2:]))
    with pytest.raises(ValueError, match='inventory role'):
        assemble(load_config(ROOT / 'examples/single-module.json'), damaged)


def test_laminar_section_uses_actual_grid_column_without_old_trestles(tmp_path):
    from parametric_deco.export.views import render_views
    a = build_example('organism-low').assembly
    assert not any(i.role == 'register' for i in a.instances)
    render_views(a, tmp_path, views=('joint-section',))
    assert (tmp_path / 'joint-section.png').is_file()


def test_curled_jaw_rectangle_extremes_do_not_support_actual_distal_tail():
    build = build_example('creature-mask')
    a = build.assembly
    config = load_config(ROOT / 'examples/creature-mask.json')
    part = next(i for i in a.instances if i.instance_id == 'jaw-left-armour-0')
    path = independent_path(a, config, part)
    metadata = deepcopy(a.composition)
    removed = [s for s in metadata['end_supports']['stations']
               if part.instance_id in s['plate_ids'] and path.project(Point(s['xy']), normalized=True) >= .70]
    removed_ids = {s['id'] for s in removed}
    hardware = {hid for s in removed for hid in s['hardware_ids']}
    metadata['end_supports']['stations'] = [s for s in metadata['end_supports']['stations'] if s['id'] not in removed_ids]
    remaining = [s for s in metadata['end_supports']['stations'] if part.instance_id in s['plate_ids']]
    axis, lo, hi = span_axis(xy_footprint(a.definition_for(part), part.transform))
    rectangle = [(np.dot(s['xy'], axis) - lo) / (hi - lo) for s in remaining]
    assert min(rectangle) <= .30 and max(rectangle) >= .70  # The old proof still passes.
    actual = [path.project(Point(s['xy']), normalized=True) for s in remaining]
    assert max(actual) < .65
    assert path.length * (1 - max(actual)) > 150  # A real curled tail is unsupported.
    # Falsified saved end claims must not override the geometry-derived path.
    for span in metadata['end_supports']['spans']:
        span['placed_station_fractions'] = [0, 1]
    broken = replace(a, composition=metadata, instances=tuple(i for i in a.instances if i.instance_id not in hardware))
    assert any(i.code == 'end_support_path' and part.instance_id in i.part_ids
               for i in verify_supports(broken, config))


def test_deficient_v1_stock_is_rejected_without_remachining():
    from parametric_deco.model import Assembly, Inventory, ValidationReport, digest
    from parametric_deco.supports import (
        _prepare_source, _select_stations, _machined_inventory, supported_build,
    )
    build = build_example('creature-mask')
    config = load_config(ROOT / 'examples/creature-mask.json')
    template = Inventory.from_dict(build.inventory.layout['source_template'])
    identifiers = {i.instance_id for i in template.instances}
    original = Assembly(template.definitions, template.instances,
        tuple(c for c in build.assembly.connections if c.family != 'end-clamp-v1'
              and c.a in identifiers and c.b in identifiers),
        build.assembly.mounting_grid, envelope_mm=build.assembly.envelope_mm,
        composition=build.assembly.composition)
    source = replace(build, assembly=original, inventory=template, report=ValidationReport())
    prepared = _prepare_source(source, config)
    # Reproduce the reviewed v1 rectangle-only stock, not a newly claimed path.
    stock = _machined_inventory(prepared, _select_stations(prepared.assembly, config), config)
    layout = deepcopy(stock.layout)
    layout['support_revision'] = 'separated-end-clamps-v1'
    layout.pop('fingerprint')
    layout['fingerprint'] = digest(layout)
    stock = replace(stock, layout=layout)
    before = stock.to_dict()
    with pytest.raises(ValueError, match='requires new cuts'):
        supported_build(config, stock, lambda *_: source)
    assert stock.to_dict() == before
