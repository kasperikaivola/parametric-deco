"""Explicit per-face content atlas; calibration belongs to the projector host."""

from dataclasses import asdict
import math

import numpy as np
from PIL import Image, ImageDraw
from shapely import contains_xy, points, distance, boundary

from ..model import AtlasResult
from ..validation import instance_bounds


def generate_atlas(assembly, width, height):
    if (
        type(width) is not int
        or type(height) is not int
        or min(width, height) < 16
        or max(width, height) > 8192
    ):
        raise ValueError("atlas dimensions must be integers in 16..8192")
    records = []
    for inst in sorted(assembly.instances, key=lambda i: i.instance_id):
        definition = assembly.definition_for(inst)
        for surface in definition.surfaces:
            records.append((inst, definition, surface))
    if not records:
        raise ValueError("atlas has no explicit projecting surfaces")
    columns = math.ceil(math.sqrt(len(records) * width / height))
    rows = math.ceil(len(records) / columns)
    cell_w, cell_h = width // columns, height // rows
    gutter = 2
    tw, th = cell_w - 2 * gutter, cell_h - 2 * gutter
    if min(tw, th) < 4:
        raise ValueError(f"atlas too small for {len(records)} faces and 2 pixel gutters")
    arrays = {
        name: np.zeros((height, width, 4), dtype=np.uint8)
        for name in ("localData", "worldData", "idData", "edgeData")
    }
    instance_ids = {
        i.instance_id: index + 1
        for index, i in enumerate(sorted(assembly.instances, key=lambda i: i.instance_id))
    }
    if len(instance_ids) > 0xFFFFFF:
        raise ValueError("atlas instance IDs exceed RGB24 capacity")
    bounds = [
        instance_bounds(assembly.definition_for(i), i.transform)
        for i in assembly.instances
        if assembly.definition_for(i).surfaces
    ]
    minimum = np.min([b[0] for b in bounds], axis=0)
    maximum = np.max([b[1] for b in bounds], axis=0)
    span = np.maximum(maximum - minimum, 1e-9)
    paths = {p[0]: p[1:3] for p in assembly.effect_paths}
    tiles, mapping = [], {}
    calibration = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    for index, (inst, definition, surface) in enumerate(records):
        x = (index % columns) * cell_w + gutter
        y = (index // columns) * cell_h + gutter
        polygon = surface.polygon
        min_u, min_v, max_u, max_v = polygon.bounds
        du, dv = max_u - min_u, max_v - min_v
        # Pixel centres. PNG rows run down, local V runs up.
        uu, vv = np.meshgrid((np.arange(tw) + 0.5) / tw, 1 - (np.arange(th) + 0.5) / th)
        u, v = min_u + uu * du, min_v + vv * dv
        valid = contains_xy(polygon, u, v)
        local3d = (
            np.array(surface.origin)
            + u[..., None] * np.array(surface.u_axis)
            + v[..., None] * np.array(surface.v_axis)
        )
        transform = np.array(inst.transform)
        world = local3d @ transform[:3, :3].T + transform[:3, 3]
        start, end = paths.get(inst.instance_id, (0.0, 1.0))
        dmin, _, dmax, _ = definition.polygon.bounds
        along = np.clip((local3d[:, :, 0] - dmin) / (dmax - dmin), 0, 1)
        phase = start + (end - start) * along
        local = np.stack((uu, vv, phase, valid), axis=-1)
        coords = np.concatenate(
            (np.clip((world - minimum) / span, 0, 1), valid[:, :, None]), axis=-1
        )
        identity = instance_ids[inst.instance_id]
        ids = np.zeros((th, tw, 4), dtype=np.uint8)
        ids[:, :, :3] = ((identity >> 16) & 255, (identity >> 8) & 255, identity & 255)
        ids[:, :, 3] = valid * 255
        edge = np.clip(distance(points(u, v), boundary(polygon)) / min(du, dv), 0, 1)
        edges = np.stack((edge, phase, np.zeros_like(edge), valid), axis=-1)
        for name, data in (("localData", local), ("worldData", coords), ("edgeData", edges)):
            encoded = np.rint(np.clip(data, 0, 1) * 255).astype(np.uint8)
            encoded[~valid] = 0
            arrays[name][y : y + th, x : x + tw] = encoded
        ids[~valid] = 0
        arrays["idData"][y : y + th, x : x + tw] = ids
        # Labelled asymmetric visual resource, distinct from numeric textures.
        rgb = np.stack(
            (uu * 180 + 50, vv * 180 + 20, (1 - uu) * 110 + 50, valid * 255), axis=-1
        ).astype(np.uint8)
        rgb[~valid] = 0
        patch = Image.fromarray(rgb)
        draw = ImageDraw.Draw(patch)
        draw.text(
            (3, max(1, th // 2 - 6)), f"{inst.instance_id}\n{surface.surface_id}", fill="white"
        )
        draw.line((3, th - 4, tw - 4, th - 4), fill="red", width=2)
        draw.line((3, th - 4, 3, 3), fill="lime", width=2)
        calibration.paste(patch, (x, y))
        tile_id = inst.instance_id + "--" + surface.surface_id
        tile = {
            "tile_id": tile_id,
            "instance_id": inst.instance_id,
            "definition_id": definition.definition_id,
            "revision": definition.revision,
            "surface_id": surface.surface_id,
            "semantic_id_rgb24": identity,
            "pixel_rect": [x, y, tw, th],
            "uv_rect": [x / width, 1 - (y + th) / height, (x + tw) / width, 1 - y / height],
            "local_bounds": [min_u, min_v, max_u, max_v],
            "face": asdict(surface),
            "local_quantization_mm": [du / 255, dv / 255],
            "phase_interval": [start, end],
        }
        tiles.append(tile)
        mapping[tile_id] = index
    textures = {name: Image.fromarray(array) for name, array in arrays.items()}
    textures["calibrationImage"] = calibration
    manifest = {
        "schema_version": 1,
        "content_space": "surface_atlas_unmapped",
        "geometric_mapping_owner": "Arena only",
        "dimensions": [width, height],
        "gutter_pixels": gutter,
        "png_origin": "top-left",
        "shader_uv_origin": "bottom-left",
        "orientation": "PNG top row corresponds to local +V; verify host upload with calibration",
        "world_bounds_mm": [minimum.tolist(), maximum.tolist()],
        "world_quantization_mm": {
            "step": (span / 255).tolist(),
            "maximum_rounding_error": (span / 510).tolist(),
        },
        "sampling": {
            "categorical_ids": "nearest, no mipmaps, no sRGB",
            "coordinates": "nearest, no mipmaps, no sRGB; never colour-correct data",
        },
        "encoding": {
            "localData": "RGBA8 local U,V,global path phase,validity",
            "worldData": "RGBA8 normalized assembly X,Y,Z,validity",
            "idData": "RGBA8 big-endian instance ID RGB24,validity; zero is background",
            "edgeData": "RGBA8 distance to actual face boundary / min face extent,phase,0,validity",
        },
        "inputs": {
            "localData": "local.png",
            "worldData": "world.png",
            "idData": "ids.png",
            "edgeData": "edges.png",
            "calibrationImage": "calibration.png",
        },
        "paths": sorted(assembly.effect_paths, key=lambda p: p[1]),
        "tiles": tiles,
        "excluded_surfaces": "back faces and backing; projector occlusion not computed",
        "host_validation": "not_run",
    }
    return AtlasResult(manifest, textures, mapping)
