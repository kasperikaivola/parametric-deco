"""GLB in metres and a dependency-free viewer scene in millimetres."""

import json
from pathlib import Path

import numpy as np
import trimesh

from ..cad import mesh_for


def write_scene(assembly, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    scene = trimesh.Scene()
    meshes = {}
    for definition in assembly.definitions:
        key = definition.definition_id + "@" + definition.revision
        mesh = mesh_for(definition)
        meshes[key] = {
            "vertices": np.round(mesh.vertices, 5).tolist(),
            "triangles": mesh.faces.tolist(),
        }
    records = []
    for instance in assembly.instances:
        definition = assembly.definition_for(instance)
        key = definition.definition_id + "@" + definition.revision
        source = meshes[key]
        mesh = trimesh.Trimesh(
            vertices=np.array(source["vertices"]) * 0.001, faces=source["triangles"], process=False
        )
        color = [150, 105, 63, 255] if instance.role == "backplate" else [205, 158, 99, 255]
        mesh.visual.vertex_colors = color
        transform = np.array(instance.transform)
        transform[:3, 3] *= 0.001
        scene.add_geometry(
            mesh,
            node_name=instance.instance_id,
            geom_name=key + "-" + instance.instance_id,
            transform=transform,
            metadata={
                "definition_id": definition.definition_id,
                "revision": definition.revision,
                "units": "m",
            },
        )
        records.append(
            {
                "id": instance.instance_id,
                "mesh": key,
                "transform": instance.transform,
                "role": instance.role,
                "module_id": instance.module_id,
            }
        )
    # Labelled conservative root hardware envelopes; not a detailed fastener design.
    for index, b in enumerate(assembly.hardware_bounds):
        low, high = np.array(b[1:4]), np.array(b[4:7])
        mesh = trimesh.creation.cylinder(
            radius=(high[0] - low[0]) * 0.0005, height=(high[2] - low[2]) * 0.001, sections=16
        )
        mesh.apply_translation((low + high) * 0.0005)
        mesh.visual.vertex_colors = [100, 110, 120, 180]
        scene.add_geometry(
            mesh,
            node_name=f"hardware-envelope-{index}",
            metadata={"simplified_hardware_envelope": True},
        )
    (out / "assembly.glb").write_bytes(scene.export(file_type="glb"))
    (out / "scene.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "units": "mm",
                "meshes": meshes,
                "instances": records,
                "hardware_bounds": assembly.hardware_bounds,
            },
            separators=(",", ":"),
        )
    )
