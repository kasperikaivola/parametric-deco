"""Removable plywood edge clamps, rear-facing-to-host strips and immutable supplement.

All geometry is nominal finished stock. No base plywood is drilled or changed.
The host, not a rendered glow, provides front occlusion.
"""
from dataclasses import asdict, replace
import math

import numpy as np
from shapely import affinity
from shapely.geometry import Point, box

from .model import Inventory, PartDefinition, PartInstance, digest
from .validation import instance_bounds, xy_footprint, boxes_overlap
from .cad import overlap_volume
from .geometry.symmetry import kind as symmetry_kind, matrices, mapped_id, canonical_id

KEY = 'lighting_supplement'
ROLES = {'led-tray', 'led-pad', 'led-jaw', 'led-input'}
RETENTION_REVISION = 'checked-tie-path-v2'
TIE_WIDTH = 2.5
TIE_THICKNESS = 1.0
TIE_HEAD = (5.0, 5.0, 3.0)
INPUT_CABLE_DIAMETER = 5.0


def prepare_inventory(config, inventory):
    """Separate supplementary parts before style-specific immutable layout validation."""
    if inventory is None:
        return None, None
    inventory = Inventory.from_dict(inventory.to_dict())
    layout = dict(inventory.layout or {})
    saved = layout.pop(KEY, None)
    if saved is None:
        if config.lighting.enabled:
            raise ValueError('lighting requires a lit inventory; generate new supplemental cuts')
        return inventory, None
    if digest({k: v for k, v in saved.items() if k != 'fingerprint'}) != saved['fingerprint']:
        raise ValueError('lighting inventory supplement fingerprint mismatch')
    if (config.lighting.enabled and
            saved['metadata'].get('retention_revision') != RETENTION_REVISION):
        raise ValueError('lighting inventory retention predates verified tie paths; '
                         'generate new supplemental cuts')
    ids = set(saved['instance_ids'])
    parts = {(i.definition_id, i.revision) for i in inventory.instances if i.instance_id in ids}
    actual = Inventory(tuple(d for d in inventory.definitions
                             if (d.definition_id, d.revision) in parts),
                       tuple(i for i in inventory.instances if i.instance_id in ids))
    if digest(actual.to_dict()) != digest(saved['inventory']):
        raise ValueError('lighting inventory parts changed or missing')
    base = Inventory(tuple(d for d in inventory.definitions
                           if (d.definition_id, d.revision) not in parts),
                     tuple(i for i in inventory.instances if i.instance_id not in ids),
                     None if saved['base_layout_none'] else layout)
    return base, saved


def _pose(host, x, y, u, v, z):
    local = np.eye(4)
    local[:3, 0] = (u[0], u[1], 0)
    local[:3, 1] = (v[0], v[1], 0)
    local[:3, 3] = (x, y, z)
    return tuple(map(tuple, np.asarray(host.transform) @ local))


def _point(pose, xyz):
    return (np.asarray(pose) @ np.array((*xyz, 1)))[:3].tolist()


def _polygon_world(poly, pose):
    t = np.asarray(pose)
    return affinity.affine_transform(poly, [t[0, 0], t[0, 1], t[1, 0], t[1, 1],
                                            t[0, 3], t[1, 3]])


def _clear(assembly, definitions, instances, existing):
    """Check actual solids against artwork and previously selected clamps."""
    w, h, depth = assembly.envelope_mm
    for inst in instances:
        part = definitions[inst.definition_id]
        bounds = instance_bounds(part, inst.transform)
        if (np.any(bounds[0] < (-w/2, -h/2, 0)) or
                np.any(bounds[1] > (w/2, h/2, depth))):
            return False
        footprint = xy_footprint(part, inst.transform)
        for other, otherpart in existing:
            if (boxes_overlap(bounds, instance_bounds(otherpart, other.transform)) and
                footprint.intersection(xy_footprint(otherpart, other.transform)).area > 1e-8 and
                overlap_volume(part, inst.transform, otherpart, other.transform) > 1e-5):
                return False
        for b in assembly.hardware_bounds:
            if boxes_overlap(bounds, np.array((b[1:4], b[4:7]))):
                return False
    return True


def _retention_spec(stock, length, width, strip_thickness, input_anchor):
    envelopes = []

    def add(kind, bounds):
        envelopes.append({'kind': kind, 'local_bounds_mm': list(bounds)})

    if input_anchor:
        rear, upper = -stock, INPUT_CABLE_DIAMETER
        add('input-cable', (-2.5, -12, 0, 2.5, -.5, upper))
        for y in (-8, -3):
            add('tie-upper', (-5.5, y-TIE_WIDTH/2, upper,
                              5.5, y+TIE_WIDTH/2, upper+TIE_THICKNESS))
            add('tie-rear', (-5.5, y-TIE_WIDTH/2, rear-TIE_THICKNESS,
                             5.5, y+TIE_WIDTH/2, rear))
            for x in (-5, 5):
                add('tie-leg', (x-TIE_THICKNESS/2, y-TIE_WIDTH/2, rear-TIE_THICKNESS,
                                x+TIE_THICKNESS/2, y+TIE_WIDTH/2, upper+TIE_THICKNESS))
            add('tie-head', (-5-TIE_HEAD[0]/2, y-TIE_HEAD[1]/2, rear-TIE_HEAD[2],
                             -5+TIE_HEAD[0]/2, y+TIE_HEAD[1]/2, rear))
    else:
        rear, upper = -2*stock, -stock+strip_thickness
        for x in (-length/2+3, length/2-3):
            add('tie-upper', (x-TIE_WIDTH/2, 4.5, upper,
                              x+TIE_WIDTH/2, 11.5+width, upper+TIE_THICKNESS))
            add('tie-rear', (x-TIE_WIDTH/2, 4.5, rear-TIE_THICKNESS,
                             x+TIE_WIDTH/2, 11.5+width, rear))
            for y in (5, 11+width):
                add('tie-leg', (x-TIE_WIDTH/2, y-TIE_THICKNESS/2, rear-TIE_THICKNESS,
                                x+TIE_WIDTH/2, y+TIE_THICKNESS/2, upper+TIE_THICKNESS))
            add('tie-head', (x-TIE_HEAD[0]/2, 5-TIE_HEAD[1]/2, rear-TIE_HEAD[2],
                             x+TIE_HEAD[0]/2, 5+TIE_HEAD[1]/2, rear))
    return {'revision': RETENTION_REVISION, 'input_anchor': input_anchor,
            'tie_width_mm': TIE_WIDTH, 'tie_thickness_mm': TIE_THICKNESS,
            'tie_head_max_mm': list(TIE_HEAD),
            'cable_diameter_max_mm': INPUT_CABLE_DIAMETER if input_anchor else None,
            'envelopes': envelopes}


def retention_geometry(segment):
    """Purchased tie/cable bounding solids: preview and clearance, never cut inventory."""
    result = []
    for n, record in enumerate(segment['retention']['envelopes']):
        x0, y0, z0, x1, y1, z1 = record['local_bounds_mm']
        name = segment['segment_id']+f'-retention-{n}'
        part = PartDefinition.from_polygon(name, box(x0,y0,x1,y1), z1-z0,
                                           kind=record['kind'])
        pose = np.asarray(segment['carrier_frame']).copy()
        pose[:3, 3] += pose[:3, 2]*z0
        inst = PartInstance(name, name, part.revision, tuple(map(tuple, pose)),
                            segment.get('module_id', 'backing'),
                            'led-cable' if record['kind'] == 'input-cable' else 'led-tie')
        result.append((inst, part))
    return result


def _retention_clear(assembly, segment, existing):
    geometry = retention_geometry(segment)
    return _clear(assembly, {p.definition_id:p for _,p in geometry},
                   [i for i,_ in geometry], existing)


def _candidate(assembly, host, config, distance, index, input_anchor=False):
    part = assembly.definition_for(host)
    polygon = part.polygon
    ring = polygon.exterior
    length = config.lighting.segment_leds * config.lighting.led_pitch_mm
    if input_anchor:
        length = 24
    a = ring.interpolate(distance - 1)
    b = ring.interpolate(distance + 1)
    norm = math.hypot(b.x-a.x, b.y-a.y)
    if norm < 1e-8:
        return None
    u = np.array((b.x-a.x, b.y-a.y))/norm
    v = np.array((-u[1], u[0]))
    p = ring.interpolate(distance)
    if not polygon.contains(Point(p.x+v[0]*2, p.y+v[1]*2)):
        u, v = -u, -v
    stock = config.material.measured_mm
    width = config.lighting.strip_width_mm
    gap = stock - config.lighting.strip_thickness_mm
    if not input_anchor and gap < TIE_THICKNESS + config.lighting.clearance_mm:
        raise ValueError('lighting strip thickness + 1 mm tie body + clearance must fit '
                         'one stock thickness; reduce strip_thickness_mm')
    depth = width + 15 if not input_anchor else 16
    half = length/2
    pose = _pose(host, p.x, p.y, u, v, 0)
    strip = box(-half, 8, half, 8+width)
    # Full strip footprint and margin, not just its centre ray, must hit intact plywood.
    if not input_anchor and not polygon.covers(_polygon_world(strip.buffer(
            config.lighting.clearance_mm), _pose(
                PartInstance('local', part.definition_id, part.revision),
                p.x, p.y, u, v, 0))):
        return None
    bolt_xs = (-half-4, half+4)
    bolt_holes = [Point(x, -6).buffer(1.7, quad_segs=8) for x in bolt_xs]
    local_pose = _pose(PartInstance('local', part.definition_id, part.revision),
                       p.x, p.y, u, v, 0)
    for x in bolt_xs:
        if polygon.intersects(_polygon_world(Point(x, -6).buffer(3.5), local_pose)):
            return None
    # Pads must have actual bearing on the host at both ends.
    pads = [box(-half-8, -12, -half-1, depth), box(half+1, -12, half+8, depth)]
    if any(polygon.intersection(_polygon_world(pad, local_pose)).area < 25 for pad in pads):
        return None
    tray = box(-half-8, -12, half+8, depth)
    for hole in bolt_holes:
        tray = tray.difference(hole)
    # Four 3 x 2 mm tie slots, clear of the strip edges; end ties retain without adhesive.
    slots = [box(x-1.5, y-1, x+1.5, y+1)
             for x in (-half+3, half-3) for y in (5, 11+width)]
    if input_anchor:
        slots = [box(x-1, y-1.5, x+1, y+1.5)
                 for x in (-5, 5) for y in (-8, -3)]
    for slot in slots:
        tray = tray.difference(slot)
    name = 'led-input' if input_anchor else f'led-{index:02d}'
    definitions, instances = [], []

    def add(suffix, poly, z, role):
        if poly.geom_type != 'Polygon' or not poly.is_valid:
            return False
        d = PartDefinition.from_polygon(name+'-'+suffix, poly, stock, kind=role)
        definitions.append(d)
        instances.append(PartInstance(d.definition_id, d.definition_id, d.revision,
                                      _pose(host, p.x, p.y, u, v, z), host.module_id, role))
        return True

    if not add('tray', tray, -stock if input_anchor else -2*stock,
               'led-input' if input_anchor else 'led-tray'):
        return None
    # Separate end jaws leave the full strip aperture open, and seat on both host faces.
    for j, (pad, hole) in enumerate(zip(pads, bolt_holes)):
        shape = pad.difference(hole)
        # A second hole serves as a reusable cable-tie anchor.
        shape = shape.difference(box(bolt_xs[j]-1.5, -11, bolt_xs[j]+1.5, -9))
        if not input_anchor and not add(f'pad-{j}', shape, -stock, 'led-pad'):
            return None
        if not add(f'jaw-{j}', shape, part.thickness_mm, 'led-jaw'):
            return None
    emitter = _point(pose, (0, 8+width/2, -gap))
    target = _point(pose, (0, 8+width/2, 0))
    if input_anchor:
        emitter = _point(pose, (0, -6, INPUT_CABLE_DIAMETER/2))
    min_bolt = part.thickness_mm + (2 if input_anchor else 3)*stock + 7
    bolt_length = 5*math.ceil(min_bolt/5)
    tray_rear = -stock if input_anchor else -2*stock
    bolt_envelopes = [
        {'position_mm': _point(pose, (x, -6, tray_rear-3)),
         'diameter_mm': 7, 'height_mm': bolt_length+3,
         'length_mm': bolt_length, 'insertion': 'rear_to_front'} for x in bolt_xs]
    segment = {
        'segment_id': name, 'host_instance': host.instance_id,
        'target_instance': host.instance_id, 'part_instances': [i.instance_id for i in instances],
        'strip_length_mm': length, 'led_count': config.lighting.segment_leds,
        'emitter_position_mm': emitter, 'target_position_mm': target,
        'emission_direction': np.asarray(host.transform)[:3, 2].tolist(),
        'emitter_to_host_mm': gap, 'shield_margin_mm': config.lighting.clearance_mm,
        'strip_local_bounds_mm': [-half, 8, half, 8+width],
        'carrier_frame': np.asarray(pose).tolist(),
        'strip_start_mm': _point(pose, (-half, 8+width/2, -gap)),
        'strip_end_mm': _point(pose, (half, 8+width/2, -gap)),
        'bolt_length_min_mm': min_bolt, 'bolt_envelopes': bolt_envelopes,
        'retention': _retention_spec(stock, length, width,
                                    config.lighting.strip_thickness_mm, input_anchor),
        'checks': {'full_emitter_footprint_hits_host': not input_anchor,
                   'front_occluded_by_host': not input_anchor,
                   'solid_clearance': True},
    }
    if not _retention_clear(assembly, segment, [(host, part), *zip(instances, definitions)]):
        return None
    segment['checks']['retention_body_head_cable_clear'] = True
    return definitions, instances, segment


def _hardware_clear(assembly, segment, existing):
    for n, hardware in enumerate(segment['bolt_envelopes']):
        x, y, z = hardware['position_mm']
        part = PartDefinition.from_polygon('led-bolt-envelope',
                Point(x, y).buffer(hardware['diameter_mm']/2, quad_segs=8),
                hardware['height_mm'])
        pose = np.eye(4)
        pose[2, 3] = z
        inst = PartInstance(f'led-bolt-{n}', part.definition_id, part.revision,
                            tuple(map(tuple, pose)))
        if not _clear(assembly, {part.definition_id: part}, [inst], existing):
            return False
    return _retention_clear(assembly, segment, existing)


def _emission_clear(assembly, segment, config, existing):
    x0, y0, x1, y1 = segment['strip_local_bounds_mm']
    stock = config.material.measured_mm
    prism = PartDefinition.from_polygon('led-clearance', box(x0, y0, x1, y1), stock)
    pose = np.asarray(segment['carrier_frame']).copy()
    pose[:3, 3] -= pose[:3, 2]*stock
    inst = PartInstance('led-clearance', prism.definition_id, prism.revision,
                        tuple(map(tuple, pose)))
    obstacles = [(i, p) for i, p in existing if i.instance_id != segment['host_instance']]
    return _clear(assembly, {prism.definition_id: prism}, [inst], obstacles)


def _generate(config, assembly):
    light = config.lighting
    definitions, instances, segments = [], [], []
    existing = [(i, assembly.definition_for(i)) for i in assembly.instances]
    # One per module per pass prevents dense head stacks monopolising the budget.
    hosts = [i for i in assembly.instances if i.role in ('armour', 'cap', 'closure', 'spine')
             and i.transform[2][2] > .999]
    modules = sorted({i.module_id for i in hosts})
    if len(modules) > light.max_segments:
        raise ValueError('lighting.max_segments must cover every sculptural module')
    rejected = {host.instance_id: set() for host in hosts}
    separation = max(30.0, light.strip_width_mm + 2*light.clearance_mm)
    counts = {module: 0 for module in modules}
    symmetry_attempts = 0
    by_id = {i.instance_id: i for i in hosts}

    def place_one(module):
        nonlocal symmetry_attempts
        choices = sorted((i for i in hosts if i.module_id == module),
                         key=lambda i: (-i.transform[2][3], i.instance_id))
        if canonical_id(module, config) != module:
            return False
        previous = [np.array(s['emitter_position_mm'][:2]) for s in segments]
        for host in choices:
            ring = assembly.definition_for(host).polygon.exterior
            samples = list(enumerate(np.linspace(0, ring.length, 600, endpoint=False)))

            def score(sample):
                _, distance = sample
                p = ring.interpolate(distance)
                world = np.asarray(_point(host.transform, (p.x, p.y, 0)))[:2]
                spread = min((float(np.linalg.norm(world-p)) for p in previous), default=0)
                return (-spread, -float(np.linalg.norm(world)), distance)

            for sample_id, distance in sorted(samples, key=score):
                if sample_id in rejected[host.instance_id]:
                    continue
                rejected[host.instance_id].add(sample_id)
                candidate = _candidate(assembly, host, config, distance, len(segments))
                if candidate is None:
                    continue
                ds, ins, segment = candidate
                centre = np.array(segment['emitter_position_mm'][:2])
                if any(np.linalg.norm(centre-p) < separation for p in previous):
                    continue
                orbit = [(ds, ins, segment)]
                for group_index, matrix in enumerate(matrices(config)[1:], 1):
                    partner = by_id.get(mapped_id(host.instance_id, config, group_index))
                    if partner is None:
                        orbit = []
                        break
                    origin = np.array(segment['carrier_frame'])[:2, 3]
                    target = matrix @ origin
                    local = np.linalg.inv(np.array(partner.transform)) @ np.array(
                        (*target, partner.transform[2][3], 1))
                    partner_ring = assembly.definition_for(partner).polygon.exterior
                    projected = partner_ring.interpolate(partner_ring.project(Point(local[:2])))
                    if projected.distance(Point(local[:2])) > 1e-6:
                        orbit = []
                        break
                    if any(row[2]['host_instance'] == partner.instance_id and np.linalg.norm(
                            np.array(row[2]['carrier_frame'])[:2,3]-target) < 1e-6 for row in orbit):
                        continue
                    candidate = _candidate(assembly, partner, config,
                        partner_ring.project(Point(local[:2])), len(segments)+len(orbit))
                    if candidate is None:
                        orbit = []
                        break
                    orbit.append(candidate)
                if not orbit or len(segments)+len(orbit) > light.max_segments:
                    continue
                trial = list(existing)
                centres = list(previous)
                valid = True
                for od, oi, os in orbit:
                    centre = np.array(os['emitter_position_mm'][:2])
                    if (any(np.linalg.norm(centre-p) < separation for p in centres) or
                            not _clear(assembly, {d.definition_id:d for d in od}, oi, trial) or
                            not _hardware_clear(assembly, os, trial) or
                            not _emission_clear(assembly, os, config, trial)):
                        valid = False
                        break
                    trial.extend(zip(oi, od))
                    centres.append(centre)
                if not valid:
                    continue
                if any(not _emission_clear(assembly, os, config, trial) for _, _, os in orbit):
                    continue
                symmetry_attempts += int(len(orbit) > 1)
                for od, oi, os in orbit:
                    owner = by_id[os['host_instance']].module_id
                    os['checks']['emitter_corridor_clear'] = True
                    os['module_id'] = owner
                    definitions.extend(od)
                    instances.extend(oi)
                    existing.extend(zip(oi, od))
                    segments.append(os)
                    counts[owner] += 1
                return True
        return False

    # First guarantee module coverage; subsequent passes spend the density budget
    # fairly. Rejected samples never become feasible as only obstacles are added.
    for module in modules:
        if counts[module] == 0 and not place_one(module):
            raise ValueError(f'lighting: no collision-free concealed clamp fits module {module}; '
                             'reduce strip dimensions/segment_leds or change geometry')
    while len(segments) < light.max_segments:
        added = False
        for module in modules:
            if len(segments) >= light.max_segments:
                break
            added = place_one(module) or added
        if not added:
            break
    if len(segments) < 2:
        raise ValueError('lighting: fewer than two distributed carriers fit; change geometry')
    # Bottom edge of the existing backplate; two ties anchor the incoming cable.
    backing = next(i for i in assembly.instances if i.role == 'backplate')
    ring = assembly.definition_for(backing).polygon.exterior
    candidates = sorted(np.linspace(0, ring.length, 160, endpoint=False),
                        key=lambda d: ring.interpolate(d).y)
    anchor = None
    for distance in candidates:
        candidate = _candidate(assembly, backing, config, distance, 0, True)
        if candidate:
            ds, ins, anchor = candidate
            if anchor['emitter_position_mm'][1] >= 0:
                anchor = None
                continue
            if (_clear(assembly, {d.definition_id: d for d in ds}, ins, existing) and
                    _hardware_clear(assembly, anchor, existing)):
                definitions.extend(ds)
                instances.extend(ins)
                break
            anchor = None
    if anchor is None:
        raise ValueError('lighting: bottom input clamp cannot fit envelope/rear clearance')
    for segment in segments:
        if (not _emission_clear(assembly, segment, config, existing) or
                not _retention_clear(assembly, segment, existing)):
            raise ValueError('lighting: completed carrier placement blocks an emitter corridor')
    if not _retention_clear(assembly, anchor, existing):
        raise ValueError('lighting: bottom input tie/head/cable clearance blocked')
    # Stable nearest-neighbour serial route from the single input.
    pending = list(segments)
    ordered, jumpers = [], []
    previous = anchor['emitter_position_mm']
    source = 'input'
    while pending:
        s = min(pending, key=lambda s: (math.dist(previous, s['strip_start_mm']), s['segment_id']))
        pending.remove(s)
        jumpers.append({'from': source, 'to': s['segment_id'],
                        'signals': ['V+', 'DATA', 'GND'],
                        'data_from_pin': 'DATA' if source == 'input' else 'DOUT',
                        'data_to_pin': 'DIN',
                        'waypoints_mm': [previous, s['strip_start_mm']],
                        'minimum_cut_length_mm': math.ceil(math.dist(previous, s['strip_start_mm'])
                                                          + light.wire_slack_mm),
                        'routing_status': 'manual_dress_around_structure_required'})
        previous, source = s['strip_end_mm'], s['segment_id']
        ordered.append(s)
    current = sum(s['led_count'] for s in ordered)*light.current_per_led_ma/1000
    per_segment = light.segment_leds*light.current_per_led_ma/1000
    if per_segment > light.injection_limit_a:
        raise ValueError('lighting: one segment exceeds injection_limit_a; shorten segment')
    branches, group = [], []
    for s in ordered:
        if group and (len(group)+1)*per_segment > light.injection_limit_a:
            branches.append(group)
            group = []
        group.append(s['segment_id'])
    if group:
        branches.append(group)
    starts = {group[0] for group in branches}
    for jumper in jumpers:
        if jumper['to'] in starts:
            jumper['signals'] = ['DATA', 'GND']
    segment_lookup = {s['segment_id']: s for s in ordered}
    feeds = []
    for group in branches:
        destination = segment_lookup[group[0]]['strip_start_mm']
        feeds.append({'from': 'input', 'to': group[0], 'signals': ['V+', 'GND'],
                      'segment_ids': group, 'estimated_current_a': len(group)*per_segment,
                      'required_wire_continuous_a': len(group)*per_segment*1.25,
                      'waypoints_mm': [anchor['emitter_position_mm'], destination],
                      'minimum_cut_length_mm': math.ceil(math.dist(
                          anchor['emitter_position_mm'], destination)+light.wire_slack_mm),
                      'fuse': 'select below wire/connector rating and above normal load'})
    metadata = {
        'schema_version': 1, 'units': 'mm', 'config': asdict(light), 'segments': ordered,
        'retention_revision': RETENTION_REVISION,
        'density': {'requested_max_segments': light.max_segments,
                    'achieved_segments': len(ordered), 'per_module': counts,
                    'minimum_xy_separation_mm': separation,
                    'capacity_limited': len(ordered) < light.max_segments},
        'symmetry': {'policy': 'complete physical symmetry orbits; single bottom input exempt',
                     'group': symmetry_kind(config),
                     'pair_attempts': symmetry_attempts,
                     'exact_symmetry_guaranteed': True},
        'data_route': [s['segment_id'] for s in ordered], 'jumpers': jumpers,
        'input': {'position_mm': anchor['emitter_position_mm'], 'signals': ['V+', 'DATA', 'GND'],
                  'part_instances': anchor['part_instances'], 'host_instance': backing.instance_id,
                  'segment_id': anchor['segment_id'], 'carrier_frame': anchor['carrier_frame'],
                  'retention': anchor['retention'],
                  'bolt_envelopes': anchor['bolt_envelopes'],
                  'strain_relief': 'two reusable cable ties through input tray slots',
                  'port_semantics': 'controller serial pixel data input; NOT firmware programming'},
        'power': {'voltage_v': light.voltage_v, 'estimated_max_current_a': current,
                  'estimated_max_power_w': current*light.voltage_v,
                  'input_connector_required_continuous_a': current*1.25,
                  'injection_groups': branches, 'feeds': feeds,
                  'branch_limit_a': light.injection_limit_a,
                  'topology': 'fused internal branches from the ONE bottom input; common ground'},
        'bom': [
            {'item': 'M3 through bolts', 'quantity': 2*(len(segments)+1),
             'variants': [{'length_mm': length, 'quantity': 2*sum(
                 5*math.ceil(s['bolt_length_min_mm']/5) == length for s in ordered+[anchor])}
                 for length in sorted({5*math.ceil(s['bolt_length_min_mm']/5)
                                        for s in ordered+[anchor]})],
             'note': 'two per clamp; length includes 7 mm for washers/nut/thread; verify stock'},
            {'item': 'M3 locking nuts', 'quantity': 2*(len(segments)+1)},
            {'item': 'M3 flat washers, OD 7 mm maximum', 'quantity': 4*(len(segments)+1)},
            {'item': 'reusable ties, body <= 2.5 x 1 mm, locking head <= 5 x 5 x 3 mm',
             'head_placement': 'behind tray at first slot; input slots outside board',
             'minimum_length_mm': max(100, 10*math.ceil((2*(light.strip_width_mm+6+
                 config.material.measured_mm+light.strip_thickness_mm)+20)/10)),
             'quantity': 2*(len(segments)+1)},
            {'item': 'purchased addressable strip', 'length_mm': sum(
                s['strip_length_mm'] for s in segments),
             'led_count': sum(s['led_count'] for s in segments)},
            {'item': 'external regulated supply, controller, fused branches, wire and connector',
             'quantity': 1, 'note': 'user supplied; select using actual rated continuous current'},
        ],
        'validation': {name: 'NOT RUN' for name in ('physical_fit', 'optical', 'electrical',
                                                    'thermal', 'Wire_Arena')},
    }
    return definitions, instances, metadata


def placement_fingerprint(assembly):
    """Hash physical stock/poses, ignoring derived evidence and sub-1e-8 mm noise.

    Supported replay recomputes grid transforms with roundoff near 1e-13 mm.
    Geometry fingerprints remain exact; this only normalizes numeric serialization.
    """
    def normalized(value):
        if isinstance(value, dict):
            return {k: normalized(v) for k, v in value.items()}
        if isinstance(value, (tuple, list)):
            return [normalized(v) for v in value]
        if (isinstance(value, (int, float, np.integer, np.floating))
                and not isinstance(value, (bool, np.bool_))):
            result = round(float(value), 8)
            return result if result else 0.0
        return value

    physical = {k: v for k, v in assembly.to_dict().items() if k not in ('composition', 'lighting')}
    return digest(normalized(physical))


def add_lighting(config, build, original_inventory=None, saved=None):
    if not config.lighting.enabled:
        return replace(build, inventory=original_inventory) if saved else build
    identity = placement_fingerprint(build.assembly)
    if saved:
        if saved['config'] != asdict(config.lighting) or saved['base_assembly_hash'] != identity:
            raise ValueError('lighting inventory placement/config changed; detach carriers and '
                             'generate new supplemental cuts explicitly')
        supplemental = Inventory.from_dict(saved['inventory'])
        definitions, instances = supplemental.definitions, supplemental.instances
        metadata = saved['metadata']
    else:
        definitions, instances, metadata = _generate(config, build.assembly)
        supplemental = Inventory(tuple(definitions), tuple(instances))
        saved = {'config': asdict(config.lighting), 'base_assembly_hash': identity,
                 'base_layout_none': build.inventory.layout is None,
                 'inventory': supplemental.to_dict(), 'metadata': metadata,
                 'instance_ids': [i.instance_id for i in instances]}
        saved['fingerprint'] = digest(saved)
    hardware_bounds = []
    for clamp in [*metadata['segments'], metadata['input']]:
        for bolt in clamp['bolt_envelopes']:
            x, y, z = bolt['position_mm']
            r = bolt['diameter_mm']/2
            hardware_bounds.append(('lighting', x-r, y-r, z, x+r, y+r, z+bolt['height_mm']))
    assembly = replace(build.assembly, hardware_bounds=(*build.assembly.hardware_bounds,
                       *hardware_bounds), definitions=(*build.assembly.definitions, *definitions),
                       instances=(*build.assembly.instances, *instances), lighting=metadata)
    layout = {**(build.inventory.layout or {}), KEY: saved}
    inventory = Inventory((*build.inventory.definitions, *definitions),
                          (*build.inventory.instances, *instances), layout)
    return replace(build, assembly=assembly, fabrication_parts=(*build.fabrication_parts,
                   *definitions), inventory=inventory, warnings=(*build.warnings,
                   'LED physical fit, optical, electrical/thermal and Wire/Arena checks NOT RUN.',
                   'Lighting jumper lines are routing guides; manually dress and secure cables.',
                   f"Lighting density: {len(metadata['segments'])}/{config.lighting.max_segments} "
                   'requested maximum segments; see capacity_limited and per_module counts.'))


def preview_assembly(assembly):
    """Add purchased-strip dimensional proxies only to views; never to cut inventory."""
    if not assembly.lighting:
        return assembly
    definitions, instances = list(assembly.definitions), list(assembly.instances)
    config = assembly.lighting['config']
    for segment in assembly.lighting['segments']:
        x0, y0, x1, y1 = segment['strip_local_bounds_mm']
        part = PartDefinition.from_polygon(segment['segment_id']+'-purchased-strip',
                                           box(x0, y0, x1, y1),
                                           config['strip_thickness_mm'], kind='led-strip')
        pose = np.array(segment['carrier_frame'])
        stock = assembly.definition_for(next(i for i in assembly.instances
                    if i.instance_id == segment['part_instances'][0])).thickness_mm
        pose[:3, 3] -= pose[:3, 2]*stock
        definitions.append(part)
        instances.append(PartInstance(part.definition_id, part.definition_id, part.revision,
                                       tuple(map(tuple, pose)), next(i.module_id for i in assembly.instances
                    if i.instance_id == segment['host_instance']), 'led-strip'))
    for clamp in [*assembly.lighting['segments'], assembly.lighting['input']]:
        for inst, part in retention_geometry(clamp):
            definitions.append(part)
            instances.append(inst)
    return replace(assembly, definitions=tuple(definitions), instances=tuple(instances))
