"""In-place parameter edits: snap numbers to the nearest schema-valid value."""

import copy
import json
import math
import re

from .config import STYLE_PARAMETERS, ModuleRecipe, config_from_dict


_OPEN = 0.01
_NUMBER = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z')


class Limit:
    def __init__(self, phrase, kind='float', lo=None, hi=None, options=(),
                 nullable=False, positive=False, nonnegative=False):
        self.phrase = phrase
        self.kind = kind
        self.lo = lo
        self.hi = hi
        self.options = tuple(options)
        self.nullable = nullable
        self.positive = positive
        self.nonnegative = nonnegative


def choices_for(data, path):
    """Typed choices for finite controls; None denotes an automatic override."""
    value = _lookup(data, tuple(path))
    if type(value) is bool:
        return (False, True)
    try:
        limit = limit_for(data, path)
    except (TypeError, KeyError, ValueError, IndexError, OverflowError):
        return ()
    options = limit.options
    if (not options and limit.kind == 'int' and limit.lo is not None
            and limit.hi is not None and 0 <= limit.hi - limit.lo <= 20):
        options = tuple(range(math.ceil(limit.lo), math.floor(limit.hi) + 1))
    return ((None,) if limit.nullable else ()) + options if options else ()


def allowed_text(data, path):
    """Short range shown beside a parameter. Blank when the row has no single range."""
    try:
        return limit_for(data, path).phrase
    except (TypeError, KeyError, ValueError, IndexError):
        return ''


def parse_cell_text(text, previous):
    """Read a table cell. Numbers and JSON stay typed; bare words are strings."""
    stripped = text.strip()
    if stripped == '':
        raise ValueError('value is empty')
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    if isinstance(previous, (int, float)) and not isinstance(previous, bool) and _NUMBER.match(stripped):
        if re.fullmatch(r'[+-]?\d+', stripped):
            return int(stripped)
        return float(stripped)
    if isinstance(previous, str) or previous is None:
        if stripped == 'null':
            return None
        return stripped
    raise ValueError('value must be JSON')


def apply_parameter_edit(data, path, text):
    """Return a new config dict with one edited value clamped to the schema."""
    path = tuple(path)
    if not path:
        raise ValueError('missing parameter')
    data = copy.deepcopy(data)
    previous = _lookup(data, path)
    parsed = parse_cell_text(text, previous)
    if path == ('style',):
        style = parsed if isinstance(parsed, str) else None
        if style not in STYLE_PARAMETERS:
            raise ValueError('use ' + _choices(STYLE_PARAMETERS))
        data['style'] = style
        data['parameters'] = config_from_dict({'style': style}).to_dict()['parameters']
        config_from_dict(data)
        return data
    _set(data, path, parsed)
    _clamp_tree(data, path, previous)
    _repair(data, path)
    try:
        config_from_dict(data)
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        if isinstance(previous, (int, float)) and not isinstance(previous, bool):
            found = _search_number(data, path, parsed, previous, limit_for(data, path))
            if found is not None:
                return found
        raise error
    return data


def limit_for(data, path):
    path = tuple(path)
    value = _lookup(data, path)
    if path == ('cutting_bed',):
        return Limit('null or object', 'keep', nullable=True)
    if isinstance(value, dict):
        return Limit('', 'keep')
    if isinstance(value, (list, tuple)):
        return Limit(_list_phrase(path), 'keep')
    if path and isinstance(path[-1], int):
        return _element_limit(data, path)
    return _field_limit(data, path)


def _field_limit(data, path):
    name = path[-1] if path else ''
    if path[:1] == ('projection',):
        from .visuals.settings import EFFECTS, COORDINATES, RANGES
        if name == 'effect':
            return _enum(*EFFECTS)
        if name == 'coordinate':
            return _enum(*COORDINATES)
        if name == 'surfaces':
            return _enum('broad', 'exterior', 'all')
        if name in RANGES:
            return _closed(*RANGES[name], integer=name.startswith('atlas_'))
    if path == ('lighting', 'voltage_v'):
        return _int_choices(5, 12, 24)
    style = data.get('style')
    params = data.get('parameters') if isinstance(data.get('parameters'), dict) else {}
    if path == ('schema_version',):
        return _only_int(2)
    if path == ('units',):
        return _enum('mm')
    if path == ('style',):
        return _enum(*STYLE_PARAMETERS)
    if path == ('material', 'measurement_status'):
        return _enum('assumed_unmeasured', 'measured')
    if path == ('material', 'grade') or path == ('material', 'finish'):
        return _text(nullable=True)
    if name in ('module_id', 'closure_instance_id') or name.endswith('_instance_id'):
        return _text(ident=True, nullable=(name == 'closure_instance_id' or value_nullable(name)))
    if style == 'laminar' and name == 'arrangement':
        return _enum('whorl', 'bilateral')
    if style == 'laminar' and name == 'symmetry':
        return _enum('rotational', 'bilateral', 'none')
    if style == 'layered-creature' and name == 'posture':
        return _enum('rest', 'raised_crown')
    if path == ('lighting', 'emission'):
        return _enum('auto', 'backwash', 'underside')
    if path == ('lighting', 'min_segment_leds'):
        hi = int(_num(data, ('lighting', 'segment_leds'), 1))
        return Limit('null or ' + _closed(1, hi, integer=True).phrase, 'int', 1, hi,
                     nullable=True)
    if style == 'laminar' and name == 'focal_count' and params.get('symmetry') == 'rotational':
        return _int_choices(3, 6, 9)
    numeric = _numeric_limit(data, path, name, style, params)
    if numeric is not None:
        return numeric
    if isinstance(_lookup(data, path), str):
        return _text()
    return Limit('', 'keep')


def value_nullable(name):
    return name in ('closure_instance_id', 'grade', 'finish', 'secondary_lobes', 'channels',
                    'segmentation')


def _numeric_limit(data, path, name, style, params):
    laminar_int = {
        'focal_count': (3, 9), 'branching': (1, 3), 'complexity': (0, 2),
    }
    laminar_optional = {'secondary_lobes': (0, 1), 'channels': (0, 3), 'segmentation': (0, 5)}
    laminar_float = {
        'phase_deg': (-180, 180), 'anatomy_phase_deg': (-180, 180), 'spread': (0.85, 1.15),
        'curvature': (0.7, 1.3), 'taper': (0.7, 1.3), 'swelling': (0.8, 1.2),
        'angularity': (0, 0.6), 'asymmetry': (0, 0.2),
    }
    creature_int = {
        'cavity_count': (3, 8), 'ribs_per_limb': (3, 7), 'shell_layers': (3, 6),
        'limb_layers': (3, 5),
    }
    creature_float = {
        'scale': (0.9, 1), 'curl': (0.8, 1.2), 'limb_reach': (0.85, 1.05),
        'limb_width': (0.9, 1.1), 'rib_height_mm': (45, 80), 'asymmetry': (0, 0.15),
    }
    if style == 'laminar' and name in laminar_int:
        return _closed(*laminar_int[name], integer=True)
    if style == 'laminar' and name in laminar_optional:
        lo, hi = laminar_optional[name]
        base = _closed(lo, hi, integer=True)
        return Limit('null or ' + base.phrase, 'int', lo, hi, nullable=True)
    if style == 'laminar' and name in laminar_float:
        return _closed(*laminar_float[name])
    if style == 'layered-creature' and name == 'limb_count':
        return _int_choices(2, 4, 6)
    if style == 'layered-creature' and name == 'shell_layers':
        return _shell_layers(data)
    if style == 'layered-creature' and name in creature_int:
        return _closed(*creature_int[name], integer=True)
    if style == 'layered-creature' and name in creature_float:
        return _closed(*creature_float[name])
    if style == 'radial-weave' and name == 'lobes':
        return _only_int(3)
    if style == 'radial-weave' and name == 'ribs_per_module':
        return _only_int(9)
    if style == 'radial-weave' and name == 'radius_mm':
        return _radius_limit(params)
    if style == 'radial-weave' and name == 'amplitude_mm':
        return _amplitude_limit(params)
    if style == 'radial-weave' and name == 'opening_radius_mm':
        return _opening_limit(params)
    if style == 'radial-weave' and name == 'rotation_deg':
        return Limit('multiple of 30', 'float')
    if name in ('x_mm', 'y_mm', 'angle_deg', 'rotation_deg', 'origin_x_mm', 'origin_y_mm'):
        return _free_number(data, path, name, style)
    if path[:1] == ('envelope',):
        return _envelope_limit(data, name, style)
    if path[:1] == ('material',):
        return _material_limit(data, name, style)
    if path[:1] == ('grid',):
        return _grid_limit(data, name, style)
    if path == ('backplate', 'sides'):
        return _closed(3, None, integer=True)
    if path[:1] == ('mounting',):
        return _mounting_limit(data, name)
    if path[:1] == ('cutting_bed',):
        if name == 'spacing_mm':
            return _closed(0, None, nonnegative=True)
        if name in ('width_mm', 'height_mm'):
            return _closed(None, None, positive=True)
    if name in ('length_mm', 'spine_separation_mm', 'spine_height_mm', 'joint_datum_mm',
                'rib_top_mm', 'rib_bottom_mm'):
        return _recipe_field_limit(data, name, style)
    return None


def _element_limit(data, path):
    parent = path[-2]
    index = path[-1]
    if parent == 'stations_mm':
        return _station_limit(data, index)
    if parent == 'rib_widths_mm':
        recipe = _recipe(data)
        return _closed(recipe['spine_separation_mm'] + 30, None, positive=True)
    if parent == 'rib_permutation':
        if index in (0, 1, 7, 8):
            return _only_int(index)
        return _closed(2, 6, integer=True)
    if parent in ('rib_order', 'station_indices'):
        count = len(_recipe(data)['stations_mm'])
        return _closed(0, max(0, count - 1), integer=True)
    if parent in ('spine_instance_ids', 'rib_instance_ids'):
        return _text(ident=True)
    value = _lookup(data, path)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return Limit('any finite number', 'float')
    if isinstance(value, str):
        return _text()
    return Limit('', 'keep')


def _list_phrase(path):
    name = path[-1] if path else ''
    phrases = {
        'stations_mm': 'ascending, each ≥ 55 and ≤ length − 15',
        'rib_widths_mm': '≥ separation + 30, one per station',
        'rib_permutation': 'permutation of 0–8; 0, 1, 7 and 8 stay fixed',
        'rib_order': 'at least 3 unique indices',
        'station_indices': 'at least 3 unique indices',
        'placements': 'one or more modules',
        'spine_instance_ids': 'empty or two ids',
        'rib_instance_ids': 'empty or ids',
    }
    return phrases.get(name, '')


def _envelope_limit(data, name, style):
    if name in ('width_mm', 'height_mm') and style == 'laminar':
        width = _num(data, ('envelope', 'width_mm'), 1000)
        height = _num(data, ('envelope', 'height_mm'), 1000)
        if name == 'width_mm':
            lo = max(800, 0.7 * height)
            hi = min(1400, 1.4 * height)
        else:
            lo = max(800, width / 1.4)
            hi = min(1400, width / 0.7)
        return _closed(lo, hi)
    if name == 'depth_mm':
        if style == 'laminar':
            return _closed(120, 240)
        if style == 'layered-creature':
            return _closed(_creature_depth(data), None, positive=True)
        if style in ('rib-study', 'radial-weave'):
            return _closed(_stack_depth(data), None, positive=True)
    if name in ('width_mm', 'height_mm', 'depth_mm'):
        return _closed(None, None, positive=True)
    return None


def _material_limit(data, name, style):
    nominal = _num(data, ('material', 'nominal_mm'), 6)
    measured = _num(data, ('material', 'measured_mm'), 6)
    clearance = _num(data, ('material', 'clearance_mm'), 0.2)
    if name == 'nominal_mm':
        return _closed(max(_OPEN, measured - 1), measured + 1, positive=True)
    if name == 'measured_mm':
        hi = nominal + 1
        upper = _measured_upper(data, style, clearance)
        if upper is not None:
            hi = min(hi, upper)
        return _closed(max(_OPEN, nominal - 1), hi, positive=True)
    if name == 'clearance_mm':
        hi = _clearance_upper(data, measured)
        return _closed(0, hi, nonnegative=True)
    return None


def _grid_limit(data, name, style):
    params = data.get('parameters') if isinstance(data.get('parameters'), dict) else {}
    hole = _num(data, ('grid', 'hole_diameter_mm'), 6.5)
    edge = _num(data, ('grid', 'edge_margin_mm'), 15)
    pitch = _num(data, ('grid', 'pitch_x_mm'), 50)
    washer = _num(data, ('mounting', 'washer_radius_mm'), 9)
    nearest = _nearest_pitch(data)
    if name == 'pitch_x_mm' and style == 'laminar' and params.get('symmetry') == 'rotational':
        lo = max(_OPEN, (hole + 2 * edge) * 2 / math.sqrt(3))
        return _closed(lo, None, positive=True)
    if name == 'pitch_y_mm' and style == 'laminar' and params.get('symmetry') == 'rotational':
        exact = pitch * math.sqrt(3) / 2
        return _closed(exact, exact)
    if name == 'offset_mm' and style == 'laminar' and params.get('symmetry') == 'rotational':
        return _closed(pitch / 2, pitch / 2)
    if name == 'offset_mm' and style == 'layered-creature':
        return Limit(f'multiple of {_fmt(pitch / 2)}', 'float')
    if name in ('pitch_x_mm', 'pitch_y_mm', 'hole_diameter_mm') and name != 'hole_diameter_mm':
        return _closed(None, None, positive=True)
    if name == 'hole_diameter_mm':
        hi_values = []
        if nearest is not None:
            hi_values.append(nearest - 2 * edge)
        hi_values.extend((2 * (washer - 1e-4), 7))
        hi = min(hi_values)
        lo = max(6.2, 2 * (washer - edge)) if washer > edge else 6.2
        return _closed(lo, hi, positive=True)
    if name == 'edge_margin_mm':
        lo = max(0, washer - hole / 2)
        hi = None if nearest is None else (nearest - hole) / 2
        return _closed(lo, hi, nonnegative=True)
    if name == 'offset_mm':
        return Limit('any finite number', 'float')
    return None


def _mounting_limit(data, name):
    hole = _num(data, ('grid', 'hole_diameter_mm'), 6.5)
    edge = _num(data, ('grid', 'edge_margin_mm'), 15)
    if name == 'washer_radius_mm':
        lo = max(9, hole / 2 + _OPEN)
        hi = min(15 - _OPEN, edge + hole / 2)
        return _closed(lo, hi, positive=True)
    if name == 'root_half_span_mm':
        return _closed(40, 55)
    if name in ('rear_clearance_mm', 'hardware_outward_mm'):
        from .config import FRONT_HARDWARE_MM, REAR_HARDWARE_MM
        lo = REAR_HARDWARE_MM if name == 'rear_clearance_mm' else FRONT_HARDWARE_MM
        return _closed(lo, _allowance_upper(data, name), nonnegative=True)
    return None


def _recipe_field_limit(data, name, style):
    recipe = _recipe(data)
    bottom = recipe['rib_bottom_mm']
    datum = recipe['joint_datum_mm']
    spine = recipe['spine_height_mm']
    top = recipe['rib_top_mm']
    if name == 'rib_bottom_mm':
        return _closed(_OPEN, datum - _OPEN, positive=True)
    if name == 'joint_datum_mm':
        return _closed(bottom + _OPEN, spine - _OPEN, positive=True)
    if name == 'spine_height_mm':
        return _closed(datum + _OPEN, top - _OPEN, positive=True)
    if name == 'rib_top_mm':
        hi = top_budget(data) if style == 'rib-study' else None
        return _closed(spine + _OPEN, hi, positive=True)
    if name == 'spine_separation_mm':
        measured = _num(data, ('material', 'measured_mm'), 6)
        clearance = _num(data, ('material', 'clearance_mm'), 0.2)
        widths = recipe['rib_widths_mm'] or (0,)
        return _closed(4 * (measured + clearance), min(widths) - 30, positive=True)
    if name == 'length_mm':
        stations = recipe['stations_mm'] or (55,)
        return _closed(max(stations) + 15, None, positive=True)
    return None


def _station_limit(data, index):
    recipe = _recipe(data)
    stations = list(recipe['stations_mm'])
    if index < 0 or index >= len(stations):
        return _closed(55, None, positive=True)
    gap = _gap(data)
    length = recipe['length_mm']
    lo = 55 if index == 0 else stations[index - 1] + gap
    if index == len(stations) - 1:
        hi = length - 15
    else:
        hi = stations[index + 1] - gap
    return _closed(lo, hi, positive=True)


def _radius_limit(params):
    opening = params.get('opening_radius_mm', 180)
    amplitude = params.get('amplitude_mm', 65)
    lo = max(250, opening + amplitude + 52)
    return _closed(lo, 340, positive=True)


def _amplitude_limit(params):
    radius = params.get('radius_mm', 300)
    opening = params.get('opening_radius_mm', 180)
    hi = min(80, radius - opening - 52)
    return _closed(50, hi, positive=True)


def _opening_limit(params):
    radius = params.get('radius_mm', 300)
    amplitude = params.get('amplitude_mm', 65)
    return _closed(None, radius - amplitude - 52, positive=True)


def _shell_layers(data):
    hi = _max_shell_layers(data)
    if hi < 3:
        return Limit('no legal value with the other settings', 'int', 3, hi)
    return _closed(3, min(6, hi), integer=True)


def _free_number(data, path, name, style):
    if name == 'origin_x_mm' and style == 'layered-creature':
        return _closed(0, 0)
    if style == 'laminar' and name in ('origin_x_mm', 'origin_y_mm'):
        params = data.get('parameters') if isinstance(data.get('parameters'), dict) else {}
        if params.get('symmetry') == 'rotational':
            return _closed(0, 0)
    return Limit('any finite number', 'float')


def _creature_depth(data, layers=None, measured=None):
    params = data.get('parameters') if isinstance(data.get('parameters'), dict) else {}
    layers = params.get('shell_layers', 6) if layers is None else layers
    measured = _num(data, ('material', 'measured_mm'), 6) if measured is None else measured
    rear = _num(data, ('mounting', 'rear_clearance_mm'), 10)
    hardware = _num(data, ('mounting', 'hardware_outward_mm'), 12)
    return rear + (18 + 2 * (layers - 1)) * measured + hardware


def _max_shell_layers(data):
    measured = _num(data, ('material', 'measured_mm'), 6)
    if measured <= 0:
        return 3
    depth = _num(data, ('envelope', 'depth_mm'), 200)
    rear = _num(data, ('mounting', 'rear_clearance_mm'), 10)
    hardware = _num(data, ('mounting', 'hardware_outward_mm'), 12)
    budget = depth - rear - hardware
    return math.floor((budget / measured - 16) / 2 + 1e-9)


def _stack_depth(data, rib_top=None, measured=None):
    style = data.get('style')
    measured = _num(data, ('material', 'measured_mm'), 6) if measured is None else measured
    rear = _num(data, ('mounting', 'rear_clearance_mm'), 10)
    hardware = _num(data, ('mounting', 'hardware_outward_mm'), 12)
    if style == 'radial-weave':
        relief = 152
    else:
        relief = _recipe(data)['rib_top_mm'] if rib_top is None else rib_top
    return rear + measured * 2 + relief + hardware


def top_budget(data):
    depth = _num(data, ('envelope', 'depth_mm'), 200)
    measured = _num(data, ('material', 'measured_mm'), 6)
    rear = _num(data, ('mounting', 'rear_clearance_mm'), 10)
    hardware = _num(data, ('mounting', 'hardware_outward_mm'), 12)
    return depth - rear - measured * 2 - hardware


def _measured_upper(data, style, clearance):
    bounds = []
    recipe = _recipe(data)
    bounds.append(recipe['spine_separation_mm'] / 4 - clearance)
    gaps = _station_gaps(recipe['stations_mm'])
    if gaps:
        bounds.append(min(gaps) - clearance - 10)
    if style == 'layered-creature':
        layers = data['parameters'].get('shell_layers', 6)
        coeff = 18 + 2 * (layers - 1)
        if coeff > 0:
            depth = _num(data, ('envelope', 'depth_mm'), 200)
            rear = _num(data, ('mounting', 'rear_clearance_mm'), 10)
            hardware = _num(data, ('mounting', 'hardware_outward_mm'), 12)
            bounds.append((depth - rear - hardware) / coeff)
    if style in ('rib-study', 'radial-weave'):
        relief = 152 if style == 'radial-weave' else recipe['rib_top_mm']
        depth = _num(data, ('envelope', 'depth_mm'), 200)
        rear = _num(data, ('mounting', 'rear_clearance_mm'), 10)
        hardware = _num(data, ('mounting', 'hardware_outward_mm'), 12)
        bounds.append((depth - rear - hardware - relief) / 2)
    finite = [bound for bound in bounds if bound is not None and math.isfinite(bound)]
    return min(finite) if finite else None


def _clearance_upper(data, measured):
    recipe = _recipe(data)
    bounds = [recipe['spine_separation_mm'] / 4 - measured]
    gaps = _station_gaps(recipe['stations_mm'])
    if gaps:
        bounds.append(min(gaps) - measured - 10)
    return min(bounds)


def _allowance_upper(data, name):
    """Largest rear or hardware allowance that still fits in the current depth."""
    style = data.get('style')
    depth = _num(data, ('envelope', 'depth_mm'), 200)
    if style == 'layered-creature':
        other = _creature_depth(data) - _num(data, ('mounting', name), 0)
        return max(0, depth - other)
    if style in ('rib-study', 'radial-weave'):
        other = _stack_depth(data) - _num(data, ('mounting', name), 0)
        return max(0, depth - other)
    return None


def _recipe(data):
    if data.get('style') == 'rib-study':
        recipe = data.get('parameters', {}).get('recipe') if isinstance(data.get('parameters'), dict) else None
        if isinstance(recipe, dict):
            return recipe
    base = ModuleRecipe()
    return {
        'length_mm': base.length_mm,
        'spine_separation_mm': base.spine_separation_mm,
        'spine_height_mm': base.spine_height_mm,
        'joint_datum_mm': base.joint_datum_mm,
        'rib_top_mm': base.rib_top_mm,
        'rib_bottom_mm': base.rib_bottom_mm,
        'stations_mm': list(base.stations_mm),
        'rib_widths_mm': list(base.rib_widths_mm),
    }


def _gap(data):
    return _num(data, ('material', 'measured_mm'), 6) + _num(data, ('material', 'clearance_mm'), 0) + 10


def _station_gaps(stations):
    values = [float(item) for item in stations if isinstance(item, (int, float)) and not isinstance(item, bool)]
    return [b - a for a, b in zip(values, values[1:])]


def _nearest_pitch(data):
    pitch_x = _num(data, ('grid', 'pitch_x_mm'), None)
    pitch_y = _num(data, ('grid', 'pitch_y_mm'), None)
    offset = _num(data, ('grid', 'offset_mm'), None)
    if pitch_x is None or pitch_y is None or offset is None or pitch_x <= 0 or pitch_y <= 0:
        return None
    span = min(offset % pitch_x, (-offset) % pitch_x)
    return min(pitch_x, pitch_y, math.hypot(pitch_y, span))


def _closed(lo, hi, integer=False, positive=False, nonnegative=False):
    kind = 'int' if integer else 'float'
    show_lo, show_hi = lo, hi
    if not integer:
        if lo is not None:
            show_lo = math.ceil(float(lo) * 10000 - 1e-8) / 10000
        if hi is not None:
            show_hi = math.floor(float(hi) * 10000 + 1e-8) / 10000
    same = lo is not None and hi is not None and abs(float(lo) - float(hi)) <= 1e-9
    crossed = lo is not None and hi is not None and not same and (
        float(lo) > float(hi) or (show_lo is not None and show_hi is not None and show_lo > show_hi))
    if same:
        phrase = _fmt(lo)
    elif crossed:
        phrase = 'no legal value with the other settings'
    elif integer and lo is not None and hi is not None:
        phrase = f'integer {int(lo)}–{int(hi)}'
    elif lo is not None and hi is not None:
        if float(lo) < 0:
            phrase = f'{_fmt(show_lo)} to {_fmt(show_hi)}'
        else:
            phrase = f'{_fmt(show_lo)}–{_fmt(show_hi)}'
    elif positive and hi is not None:
        phrase = f'> 0 and ≤ {_fmt(show_hi)}'
    elif nonnegative and hi is not None:
        phrase = f'0–{_fmt(show_hi)}'
    elif integer and lo is not None:
        phrase = f'integer ≥ {int(lo)}'
    elif lo is not None:
        phrase = f'≥ {_fmt(show_lo)}'
    elif positive:
        phrase = '> 0'
    elif nonnegative:
        phrase = '≥ 0'
    elif hi is not None:
        phrase = f'≤ {_fmt(show_hi)}'
    else:
        phrase = 'any finite number'
    return Limit(phrase, kind, lo, hi, positive=positive, nonnegative=nonnegative)


def _only_int(value):
    return Limit(f'only {int(value)}', 'int', options=(int(value),))


def _int_choices(*options):
    phrase = 'integer ' + _choices(int(item) for item in options)
    return Limit(phrase, 'int', options=tuple(int(item) for item in options))


def _enum(*options):
    return Limit(_choices(options), 'enum', options=tuple(options))


def _text(nullable=False, ident=False):
    if ident and nullable:
        phrase = 'id or null'
    elif ident:
        phrase = 'id'
    elif nullable:
        phrase = 'text or null'
    else:
        phrase = 'text'
    return Limit(phrase, 'id' if ident else 'text', nullable=nullable)


def _choices(items):
    items = [str(item) for item in items]
    if not items:
        return ''
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f'{items[0]} or {items[1]}'
    return ', '.join(items[:-1]) + ' or ' + items[-1]


def _fmt(value):
    value = float(value)
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    return f'{value:.4f}'.rstrip('0').rstrip('.')


def _rint(value):
    value = float(value)
    if value >= 0:
        return int(math.floor(value + 0.5))
    return int(math.ceil(value - 0.5))


def _nearest_option(value, options, previous):
    def key(option):
        prev = 0 if previous is None else abs(float(option) - float(previous))
        return (abs(float(option) - float(value)), prev, option)
    return min(options, key=key)


def _clamp_tree(data, path, previous):
    value = _lookup(data, path)
    if isinstance(value, dict):
        prev = previous if isinstance(previous, dict) else {}
        for key in list(value):
            _clamp_tree(data, (*path, key), prev.get(key))
        return
    if isinstance(value, list):
        prev = previous if isinstance(previous, list) else []
        if path and path[-1] == 'rib_permutation':
            _set(data, path, _repair_permutation(value))
            return
        for index in range(len(value)):
            _clamp_tree(data, (*path, index), prev[index] if index < len(prev) else None)
        if path and path[-1] in ('rib_order', 'station_indices'):
            count = len(_recipe(data)['stations_mm'])
            _set(data, path, _repair_unique(value, 0, max(0, count - 1)))
        return
    _clamp_at(data, path, previous)


def _clamp_at(data, path, previous):
    limit = limit_for(data, path)
    value = _lookup(data, path)
    if limit.kind == 'keep':
        return
    if limit.kind == 'enum':
        if value not in limit.options:
            raise ValueError('use ' + limit.phrase)
        return
    if limit.kind in ('text', 'id'):
        if value is None and limit.nullable:
            return
        if not isinstance(value, str):
            raise ValueError('use ' + limit.phrase)
        return
    if value is None and limit.nullable:
        return
    if value is None:
        raise ValueError('use ' + (limit.phrase or 'a number'))
    _set(data, path, _clamp_number(value, limit, previous))


def _clamp_number(value, limit, previous):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError('need a finite number')
    number = float(value)
    if limit.options:
        picked = _nearest_option(number, limit.options, _as_previous(previous))
        return int(picked)
    if limit.kind == 'int':
        number = _rint(number)
    if limit.positive and number <= 0:
        number = _OPEN
    if limit.nonnegative and number < 0:
        number = 0
    if limit.lo is not None and number < limit.lo:
        number = float(limit.lo)
    if limit.hi is not None and number > limit.hi:
        number = float(limit.hi)
    if limit.kind != 'int':
        number = _quantize_inward(number, limit)
    if limit.kind == 'int':
        return int(number)
    if abs(number - round(number)) < 1e-9:
        return int(round(number))
    return float(number)


def _quantize_inward(number, limit):
    if limit.hi is not None and number >= float(limit.hi) - 1e-8:
        number = math.floor(float(limit.hi) * 10000 + 1e-8) / 10000
    elif limit.lo is not None and number <= float(limit.lo) + 1e-8:
        number = math.ceil(float(limit.lo) * 10000 - 1e-8) / 10000
    if limit.lo is not None and number < float(limit.lo):
        number = float(limit.lo)
    if limit.hi is not None and number > float(limit.hi):
        number = float(limit.hi)
    return number


def _as_previous(previous):
    if isinstance(previous, bool) or not isinstance(previous, (int, float)):
        return None
    if not math.isfinite(float(previous)):
        return None
    return previous


def _repair(data, path):
    if 'rib_permutation' in path:
        prefix = path[:path.index('rib_permutation') + 1]
        _set(data, prefix, _repair_permutation(_lookup(data, prefix)))
    for name in ('rib_order', 'station_indices'):
        if name in path and isinstance(path[-1], int):
            prefix = path[:path.index(name) + 1]
            current = _lookup(data, prefix)
            if isinstance(current, list):
                count = len(_recipe(data)['stations_mm'])
                hi = max(0, count - 1)
                _set(data, prefix, _restore_unique(current, path[-1], 0, hi))
    style = data.get('style')
    params = data.get('parameters') if isinstance(data.get('parameters'), dict) else {}
    if style == 'laminar' and path == ('parameters', 'arrangement'):
        if params.get('arrangement') == 'bilateral' and params.get('symmetry') == 'rotational':
            params['symmetry'] = 'bilateral'
    if style == 'laminar' and path == ('parameters', 'symmetry'):
        if params.get('symmetry') == 'rotational':
            params['arrangement'] = 'whorl'
    if style == 'laminar' and params.get('symmetry') == 'rotational':
        if _covers(path, ('parameters', 'focal_count')) or _covers(path, ('parameters', 'symmetry')):
            current = params.get('focal_count', 6)
            params['focal_count'] = _nearest_option(current, (3, 6, 9), _as_previous(current))
        if _covers(path, ('grid',)) or path == ('parameters', 'symmetry'):
            _repair_c3(data)
    if style == 'laminar' and path == ('parameters', 'symmetry'):
        if params.get('symmetry') == 'bilateral':
            params['arrangement'] = 'bilateral'
    if style == 'laminar' and params.get('symmetry') == 'bilateral':
        current = params.get('focal_count', 6)
        if isinstance(current, int) and not isinstance(current, bool) and current % 2:
            params['focal_count'] = min(8, current + 1)
    if style == 'layered-creature' and _covers(path, ('grid',)):
        _repair_creature_grid(data)
    if style == 'layered-creature' and path[:1] == ('parameters',) and path[-1] != 'ribs_per_limb':
        _repair_creature_ribs(data)
    if style == 'radial-weave' and path == ('parameters', 'rotation_deg'):
        value = params.get('rotation_deg')
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            params['rotation_deg'] = round(value / 30) * 30


def _repair_creature_ribs(data):
    """More/shorter limbs keep the densest rib count that still fits every limb."""
    from dataclasses import replace
    from .geometry.creature_profiles import rib_spacing_issues
    try:
        creature = config_from_dict({'style': 'layered-creature',
                                     'parameters': {**data['parameters'],
                                                    'ribs_per_limb': 3}}).parameters
    except (ValueError, TypeError, KeyError):
        return
    wanted = data['parameters'].get('ribs_per_limb', 6)
    if not isinstance(wanted, int) or isinstance(wanted, bool):
        return
    material = data.get('material') if isinstance(data.get('material'), dict) else {}
    t, fit = material.get('measured_mm', 6), material.get('clearance_mm', 0.2)
    for count in range(min(wanted, 7), 2, -1):
        if not rib_spacing_issues(replace(creature, ribs_per_limb=count), t, fit):
            data['parameters']['ribs_per_limb'] = count
            return


def _repair_c3(data):
    grid = data.get('grid')
    pitch = _num(data, ('grid', 'pitch_x_mm'), None)
    if not isinstance(grid, dict) or pitch is None:
        return
    grid['pitch_y_mm'] = pitch * math.sqrt(3) / 2
    grid['offset_mm'] = pitch / 2
    grid['origin_x_mm'] = 0
    grid['origin_y_mm'] = 0


def _repair_creature_grid(data):
    grid = data.get('grid')
    pitch = _num(data, ('grid', 'pitch_x_mm'), None)
    offset = _num(data, ('grid', 'offset_mm'), None)
    if not isinstance(grid, dict) or pitch is None or pitch <= 0 or offset is None:
        return
    grid['origin_x_mm'] = 0
    half = pitch / 2
    grid['offset_mm'] = _rint(offset / half) * half


def _repair_permutation(values):
    nums = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            nums.append(0)
        else:
            nums.append(_rint(value))
    if len(nums) != 9:
        nums = list(range(9))
    nums[0], nums[1], nums[7], nums[8] = 0, 1, 7, 8
    middle = (2, 3, 4, 5, 6)
    requested = [min(6, max(2, nums[index])) for index in middle]
    unused = {2, 3, 4, 5, 6}
    assigned = {}
    for index, want in zip(middle, requested):
        if want in unused:
            assigned[index] = want
            unused.remove(want)
    for index, want in zip(middle, requested):
        if index in assigned:
            continue
        choice = min(unused, key=lambda item: (abs(item - want), item))
        assigned[index] = choice
        unused.remove(choice)
    for index, choice in assigned.items():
        nums[index] = choice
    return nums


def _repair_unique(values, lo, hi):
    used = set()
    assigned = []
    for value in values:
        number = lo if isinstance(value, bool) or not isinstance(value, (int, float)) else _rint(value)
        number = min(hi, max(lo, number))
        if number in used:
            options = [item for item in range(lo, hi + 1) if item not in used]
            number = number if not options else min(options, key=lambda item: (abs(item - number), item))
        used.add(number)
        assigned.append(number)
    return assigned


def _restore_unique(values, index, lo, hi):
    """Give a duplicated slot back the value this edit overwrote."""
    current = list(values)
    if not current or not 0 <= index < len(current):
        return _repair_unique(current, lo, hi)
    target = current[index]
    dupes = [slot for slot, item in enumerate(current) if item == target and slot != index]
    if not dupes:
        return current
    present = {item for item in current if isinstance(item, int)}
    missing = [number for number in range(lo, hi + 1) if number not in present]
    if len(missing) == 1:
        current[dupes[0]] = missing[0]
        return current
    return _repair_unique(current, lo, hi)


def _covers(path, target):
    if len(path) <= len(target):
        return target[:len(path)] == path
    return path[:len(target)] == target


def _search_number(data, path, requested, previous, limit):
    def accept(candidate):
        trial = copy.deepcopy(data)
        _set(trial, path, candidate)
        _repair(trial, path)
        try:
            config_from_dict(trial)
        except (ValueError, TypeError, KeyError, OverflowError):
            return None
        return trial

    if limit.options:
        ordered = sorted(limit.options, key=lambda option: (
            abs(float(option) - float(requested)),
            0 if _as_previous(previous) is None else abs(float(option) - float(previous)),
            option,
        ))
        for option in ordered:
            found = accept(int(option))
            if found is not None:
                return found
        return None
    if _as_previous(previous) is None:
        return None
    if limit.kind == 'int':
        start = _clamp_number(requested, limit, previous)
        found = accept(start)
        if found is not None:
            return found
        good = int(previous)
        step = 1 if good > start else -1
        number = start
        for _ in range(512):
            if number == good:
                break
            number += step
            found = accept(number)
            if found is not None:
                return found
        return accept(good)
    good = float(previous)
    bad = float(requested)
    best = accept(good)
    if best is None or abs(good - bad) < 1e-12:
        return best
    for _ in range(40):
        mid = (good + bad) / 2
        found = accept(mid)
        if found is not None:
            good = mid
            best = found
        else:
            bad = mid
    chosen = good
    chosen_trial = best
    for places in range(0, 7):
        quantized = round(good, places)
        found = accept(quantized)
        if found is not None and abs(quantized - float(requested)) < abs(chosen - float(requested)) - 1e-12:
            chosen = quantized
            chosen_trial = found
    return chosen_trial


def _lookup(data, path):
    current = data
    for key in path:
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
            current = current[key]
        else:
            return None
    return current


def _set(data, path, value):
    parent = data
    for key in path[:-1]:
        child = parent[key]
        if isinstance(child, tuple):
            child = list(child)
            parent[key] = child
        parent = child
    if isinstance(parent, tuple):
        raise ValueError('cannot replace a value inside an immutable row')
    parent[path[-1]] = value


def _num(data, path, default):
    value = _lookup(data, path)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        return default
    return float(value)
