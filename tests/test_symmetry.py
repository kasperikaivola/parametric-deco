"""Independent geometry/orbit checks for the shared equilateral board standard."""
from dataclasses import replace
from pathlib import Path
import numpy as np
import pytest
from shapely import affinity
from shapely.geometry import Point

from parametric_deco.config import load_config, validate_config
from parametric_deco.geometry.backplate import mounting_holes
from parametric_deco.geometry.organism import anatomy
from parametric_deco.geometry.creature_profiles import profiles
from parametric_deco.geometry.symmetry import verify_symmetry
from parametric_deco.supports import verify_supports

ROOT = Path(__file__).resolve().parents[1]


def config(name):
    return load_config(ROOT / 'examples' / (name + '.json'))


@pytest.mark.parametrize('name', ['organism-low', 'organism-medium', 'organism-high', 'organism-small', 'organism-large'])
def test_canonical_artwork_repeated_exactly_in_material_and_height(name):
    c = config(name)
    lobes = {lobe.name: lobe for lobe in anatomy(c)}
    n = c.parameters.focal_count // 3
    for name, lobe in lobes.items():
        prefix, index = name.rsplit('-', 1)
        partner = lobes[prefix + '-' + str((int(index) + n) % c.parameters.focal_count)]
        rotated = affinity.rotate(lobe.shape, 120, origin=(0, 0))
        assert rotated.symmetric_difference(partner.shape).area < 1e-6
        assert lobe.z == partner.z


@pytest.mark.parametrize('name', ['creature-alien-two', 'creature-mask', 'creature-alien-six'])
def test_creature_all_structural_layers_are_reflections(name):
    c = config(name)
    shapes = profiles(settings=c.parameters)
    for key, value in shapes.items():
        partner = key.replace('left', 'TEMP').replace('right', 'left').replace('TEMP', 'right')
        assert partner in shapes
        for left, right in zip(value, shapes[partner], strict=True):
            assert affinity.scale(left, xfact=-1, origin=(0, 0)).symmetric_difference(right).area < 1e-6


def test_square_grid_and_rounded_120_mounts_are_rejected():
    c = config('organism-low')
    assert not validate_config(replace(c, grid=replace(c.grid, pitch_y_mm=50))).digital_valid
    holes = [Point(h.x_mm, h.y_mm) for h in mounting_holes(c)]
    # Rotating (50,0) is EXACTLY (-25,25sqrt3), never the tempting rounded(-25,43).
    exact = Point(-25, 25 * np.sqrt(3))
    rounded = Point(-25, 43)
    assert min(exact.distance(p) for p in holes) < 1e-7
    assert min(rounded.distance(p) for p in holes) > .3


def cached(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location('gallery', ROOT / 'scripts/design_gallery.py')
    gallery = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gallery)
    path = ROOT / 'build/symmetry-v3' / (name + '.json')
    if path.exists():
        return gallery.load_result(path)
    from parametric_deco.assembly import assemble
    return assemble(config(name))


@pytest.mark.parametrize('name', ['organism-low', 'organism-high', 'organism-bilateral', 'creature-alien-two', 'creature-mask', 'creature-alien-six'])
def test_finished_material_hardware_and_layer_orbits(name):
    b = cached(name)
    assert b.report.digital_valid, b.report.to_dict()
    assert not verify_symmetry(b.assembly, config(name))
    assert not verify_supports(b.assembly, config(name))


def test_geometry_symmetry_does_not_excuse_asymmetric_layer_support():
    from copy import deepcopy
    b = cached('creature-mask')
    a = b.assembly
    metadata = deepcopy(a.composition)
    stations = metadata['end_supports']['stations']
    paired = next(s for s in stations if s['xy'][0] < -1 and len(s['plate_ids']) > 1)
    paired['plate_ids'].pop()
    changed = replace(a, composition=metadata)
    assert any(i.code == 'support_symmetry' for i in verify_symmetry(changed, config('creature-mask')))
    # Material is still exactly mirrored; the missing layer is a genuine missing clamp.
    assert not any(i.code == 'material_symmetry' for i in verify_symmetry(changed, config('creature-mask')))


def test_missing_mirrored_hardware_is_detected():
    b = cached('creature-mask')
    a = b.assembly
    shaft = next(p for p in a.instances if '-shaft-' in p.instance_id and p.transform[0][3] < -1)
    changed = replace(a, instances=tuple(p for p in a.instances if p != shaft))
    assert any(i.code == 'material_symmetry' for i in verify_symmetry(changed, config('creature-mask')))


def test_rounded_120_degree_clamp_orbits_are_not_grid_mounts():
    from copy import deepcopy
    a = cached('organism-low').assembly
    metadata = deepcopy(a.composition)
    for station in metadata['end_supports']['stations']:
        station['xy'] = [round(v, 3) for v in station['xy']]
    changed = replace(a, composition=metadata)
    assert any(i.code == 'support_grid' for i in verify_supports(changed, config('organism-low')))


def test_c3_sector_cuts_share_physical_definitions():
    for name in ('organism-low', 'organism-high'):
        inventory = cached(name).inventory
        panels = [i for i in inventory.instances if i.role == 'armour']
        counts = {}
        for panel in panels:
            key = panel.definition_id, panel.revision
            counts[key] = counts.get(key, 0) + 1
        assert len(panels) == 3 * len(counts)
        assert set(counts.values()) == {3}
