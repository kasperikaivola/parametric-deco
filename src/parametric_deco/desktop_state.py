"""Qt-free editor validation and revision identity for desktop jobs."""
from hashlib import sha256
import json

from .config import config_from_dict


def fingerprint(config, inventory=None):
    """Include inventory contents: a path alone is not a stable physical request."""
    return sha256(json.dumps({'config': config, 'inventory': inventory},
                             sort_keys=True, allow_nan=False).encode()).hexdigest()


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
