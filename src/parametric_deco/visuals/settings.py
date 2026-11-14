"""Projection content settings, independent of manufactured geometry."""
from dataclasses import dataclass, fields
import math

EFFECTS = ('pulse', 'rings', 'checker', 'solid')
COORDINATES = ('path', 'local_u', 'local_v', 'world_x', 'world_y', 'world_z', 'radial')
RANGES = {
    'speed': (-2, 2), 'phase': (0, 1), 'repeats': (0.1, 32), 'width': (0, 1),
    'softness': (0.001, 0.5), 'edge_width': (0.001, 0.2), 'brightness': (0, 2),
    'atlas_width': (16, 8192), 'atlas_height': (16, 8192),
}


@dataclass(frozen=True)
class Projection:
    enabled: bool = False
    effect: str = 'pulse'
    coordinate: str = 'path'
    speed: float = 0.1
    phase: float = 0
    repeats: float = 1
    width: float = 0.12
    softness: float = 0.02
    edge_only: bool = False
    edge_width: float = 0.04
    brightness: float = 1
    color: tuple = (0.2, 0.7, 1.0, 1.0)
    background: tuple = (0.0, 0.0, 0.0, 1.0)
    atlas_width: int = 1024
    atlas_height: int = 1024
    surfaces: str = 'broad'


def projection_errors(settings):
    for field in fields(settings):
        name, value = field.name, getattr(settings, field.name)
        message = None
        if name in ('enabled', 'edge_only'):
            if type(value) is not bool:
                message = 'must be boolean'
        elif name in ('effect', 'coordinate', 'surfaces'):
            options = {'effect': EFFECTS, 'coordinate': COORDINATES,
                       'surfaces': ('broad', 'exterior', 'all')}[name]
            if value not in options:
                message = 'use ' + ', '.join(options)
        elif name in RANGES:
            lo, hi = RANGES[name]
            if (type(value) not in (int, float) or not math.isfinite(value)
                    or not lo <= value <= hi
                    or (name.startswith('atlas_') and type(value) is not int)):
                message = f'must be finite {lo}..{hi}' + (
                    ' integer' if name.startswith('atlas_') else '')
        elif name in ('color', 'background'):
            if (not isinstance(value, (tuple, list)) or len(value) != 4
                    or any(type(v) not in (int, float) or not math.isfinite(v)
                           or not 0 <= v <= 1 for v in value)):
                message = 'requires four RGBA numbers in 0..1'
        if message:
            yield f'projection.{name}: {message}'
