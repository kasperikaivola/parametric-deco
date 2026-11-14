"""Map the content atlas onto triangulated physical faces for the GPU preview."""
from dataclasses import asdict
from importlib import resources
import json

import numpy as np
import trimesh
from shapely.geometry import Polygon

from .atlas import generate_atlas
from .isf import export_isf_resources


def write_projection(assembly, out_dir, settings):
    try:
        atlas = generate_atlas(assembly, settings.atlas_width, settings.atlas_height,
                               surfaces=settings.surfaces)
    except ValueError as error:
        # Content packing is optional: keep validated CAD and cutting exports usable.
        projection_dir = out_dir / 'projection'
        projection_dir.mkdir(parents=True, exist_ok=True)
        (projection_dir / 'projection.json').write_text(json.dumps(asdict(settings), indent=2)+'\n')
        (projection_dir / 'error.json').write_text(json.dumps({'error':str(error)}, indent=2)+'\n')
        return {'settings':asdict(settings), 'faces':[], 'textures':{},
                'error':str(error), 'shader':''}
    export_isf_resources(atlas, out_dir / 'projection', force=True, projection=settings)
    instances = {i.instance_id: i for i in assembly.instances}
    faces = []
    for tile in atlas.manifest['tiles']:
        instance = instances[tile['instance_id']]
        face = tile['face']
        polygon = Polygon(face['outer'], face['holes'])
        vertices, triangles = trimesh.creation.triangulate_polygon(polygon, engine='earcut')
        uv_local = np.asarray(vertices)[np.asarray(triangles).ravel()]
        local = (np.asarray(face['origin']) + uv_local[:, 0:1] * np.asarray(face['u_axis'])
                 + uv_local[:, 1:2] * np.asarray(face['v_axis']))
        matrix = np.asarray(instance.transform)
        world = local @ matrix[:3, :3].T + matrix[:3, 3]
        a, b, c, d = tile['local_bounds']
        u0, v0, u1, v1 = tile['uv_rect']
        uv = (uv_local - (a, b)) / (c - a, d - b)
        uv = uv * (u1 - u0, v1 - v0) + (u0, v0)
        faces.append({'instance_id': instance.instance_id, 'role': instance.role,
                      'positions': np.round(world, 5).tolist(), 'uv': uv.tolist()})
    return {'settings': asdict(settings), 'faces': faces,
            'shader': resources.files('parametric_deco.resources').joinpath(
                'projection.glsl').read_text(),
            'textures': {key: '../projection/' + atlas.manifest['inputs'][key]
                         for key in ('localData', 'worldData', 'worldFineData', 'edgeData')}}
