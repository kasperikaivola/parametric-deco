"""Coherent edits to current physical stock for identity/validation regressions."""
from copy import deepcopy

from parametric_deco.model import Inventory, digest


def seal(layout):
    layout.pop('fingerprint', None)
    layout['fingerprint'] = digest(layout)
    return layout


def relabel_inventory(inventory, names):
    """Rename physical instance references, preserving cut IDs and revisions."""
    data = deepcopy(inventory.to_dict())
    def references(value, key=None):
        if key == 'definitions':
            return value  # Cut identities/surface geometry are immutable.
        if isinstance(value, dict):
            if key == 'part_mapping':
                return {names.get(k, k): v for k, v in value.items()}
            return {k: references(v, k)
                    for k, v in value.items()}
        if isinstance(value, (tuple, list)):
            return [references(v, key) for v in value]
        if isinstance(value, str) and key not in ('definition_id', 'revision', 'fingerprint', 'role', 'module_id', 'station_id'):
            return names.get(value, value)
        return value
    data = references(data)
    source_layout = data['layout']['source_template'].get('layout')
    if source_layout is not None:
        seal(source_layout)
    seal(data['layout'])
    return Inventory.from_dict(data)


def replace_stock_parts(inventory, replacements):
    """Model coherently manufactured alternate cuts, including source templates."""
    stock = deepcopy(inventory.to_dict())
    def update(data):
        data['definitions'] = [replacements[d['definition_id']].to_dict()
                               if d['definition_id'] in replacements else d for d in data['definitions']]
        for item in data['instances']:
            if item['definition_id'] in replacements:
                item['revision'] = replacements[item['definition_id']].revision
    update(stock)
    update(stock['layout']['source_template'])
    stock['layout']['part_mapping'] = {i['instance_id']: [i['definition_id'], i['revision']]
                                       for i in stock['instances']}
    seal(stock['layout'])
    return Inventory.from_dict(stock)


def edit_source_layout(inventory, edit, *, resign_source=True):
    """Reach the intended nested guard with valid surrounding v3 metadata."""
    data = deepcopy(inventory.to_dict())
    source = data['layout']['source_template']['layout']
    edit(source)
    if resign_source:
        seal(source)
    seal(data['layout'])
    return Inventory.from_dict(data)
