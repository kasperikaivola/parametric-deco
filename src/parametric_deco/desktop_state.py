"""Qt-free editor validation and revision identity for desktop jobs."""
from hashlib import sha256
import json

from .config import config_from_dict


def fingerprint(config, inventory=None):
    """Include inventory contents: a path alone is not a stable physical request."""
    return sha256(json.dumps({'config': config, 'inventory': inventory},
                             sort_keys=True, allow_nan=False).encode()).hexdigest()


def editable_config(raw):
    """JSON-compatible defaults overlaid by raw edits, including invalid values.

    Semantic validation belongs to PreviewState. Arrays stay mutable lists so
    tree paths and replace_value use exactly the same representation.
    """
    if not isinstance(raw, dict):
        raise ValueError('config must be a JSON object')
    from .config import STYLE_PARAMETERS

    raw = json.loads(json.dumps(raw))
    style = raw.get('style', 'laminar')
    if not isinstance(style, str) or style not in STYLE_PARAMETERS:
        style = 'laminar'
    defaults = json.loads(json.dumps(config_from_dict({'style': style}).to_dict()))

    def overlay(base, value):
        if isinstance(base, dict) and isinstance(value, dict):
            return {**base, **{key: overlay(base.get(key), child)
                              for key, child in value.items()}}
        if isinstance(base, list) and isinstance(value, list):
            return [overlay(base[min(n, len(base)-1)] if base else None, child)
                    for n, child in enumerate(value)]
        return value

    return overlay(defaults, raw)


def replace_value(data, path, text):
    value = json.loads(text)
    parent = data
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value


class PreviewState:
    def __init__(self):
        self.revision = 0
        self.good_revision = None
        self.config = None
        self.error = None
        self.validated = False

    @property
    def ready(self):
        return self.validated and self.good_revision == self.revision and not self.error

    def edit(self, text):
        self.revision += 1
        self.validated = False
        try:
            self.config = config_from_dict(json.loads(text)).to_dict()
            self.error = None
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            self.config = None
            self.error = str(error)
        return self.revision

    def complete(self, revision, success, error=None):
        if revision != self.revision or self.config is None:
            return False
        self.validated = success
        self.error = error
        if success:
            self.good_revision = revision
        return True
