"""Reproducible orthographic inspection images, with no display/GPU dependency."""

from pathlib import Path
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..cad import mesh_for


def rasterize_triangles(size, triangles):
    """Resolve orthographic visibility per pixel, with larger depth in front.

    Sorting whole faces by their average depth fails when their projected
    footprints overlap: a face may be in front at one end and behind at the
    other. Barycentric depth interpolation also handles these crossing faces.
    """
    width, height = size
    pixels = np.full((height, width, 3), (18, 21, 27), dtype=np.uint8)
    depth_buffer = np.full((height, width), -np.inf)
    for xy, depth, color in triangles:
        low = np.maximum(np.floor(xy.min(axis=0)).astype(int), 0)
        high = np.minimum(np.ceil(xy.max(axis=0)).astype(int), (width - 1, height - 1))
        if np.any(low > high):
            continue
        (ax, ay), (bx, by), (cx, cy) = xy
        denominator = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(denominator) < 1e-12:
            continue
        y, x = np.ogrid[low[1]:high[1] + 1, low[0]:high[0] + 1]
        x, y = x + 0.5, y + 0.5
        a = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / denominator
        b = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / denominator
        c = 1 - a - b
        z = a * depth[0] + b * depth[1] + c * depth[2]
        region = np.s_[low[1]:high[1] + 1, low[0]:high[0] + 1]
        visible = (a >= -1e-9) & (b >= -1e-9) & (c >= -1e-9) & (z > depth_buffer[region])
        depth_buffer[region][visible] = z[visible]
        pixels[region][visible] = color
    return pixels


def project_vertices(vertices, view):
    """Orthographic coordinates; front is XY, viewed from +Z toward the board.

    The third coordinate is painter depth: larger values render in front. In a
    true front view, changing Z alone must never move a point on the image.
    """
    if view == "front":
        return vertices[:, [0, 1, 2]]
    if view == "three-quarter":
        x, y, z = vertices.T
        yaw, pitch = -0.48, 0.30
        xx = math.cos(yaw) * x + math.sin(yaw) * z
        zz = -math.sin(yaw) * x + math.cos(yaw) * z
        return np.column_stack(
            (
                xx,
                math.cos(pitch) * y - math.sin(pitch) * zz,
                math.sin(pitch) * y + math.cos(pitch) * zz,
            )
        )
    if view in ("side", "joint-section"):
        return vertices[:, [0, 2, 1]] * np.array((1, 1, -1))
    co, si = math.cos(0.5), math.sin(0.5)
    x, y, z = vertices.T
    return np.column_stack(
        (co * x - si * y, 0.35 * (si * x + co * y) + 0.94 * z, 0.35 * z - 0.94 * (si * x + co * y))
    )


def render_views(assembly, out_dir, views=None):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cached = {(d.definition_id, d.revision): mesh_for(d) for d in assembly.definitions}
    colors = {
        "rib": (218, 172, 112),
        "spine": (161, 111, 62),
        "closure": (189, 144, 88),
        "armour": (201, 157, 102),
        "cap": (201, 157, 102),
        "register": (151, 108, 64),
        "blade": (219, 176, 113),
        "retainer": (151, 108, 64),
        "spacer": (163, 116, 70),
        "part": (200, 150, 95),
        "mounting-hardware": (125, 160, 180),
        "backplate": (64, 55, 45),
    }
    font = ImageFont.load_default(size=22)
    modules = sorted({i.module_id for i in assembly.instances if i.role != "backplate"})
    creature = bool(
        assembly.composition and assembly.composition.get("family") == "creature-organism-v3"
    )
    flow = bool(
        assembly.composition
        and assembly.composition.get("family") in ("flow-organism-v1", "laminar-organism-v2")
    )
    section_module = "head" if creature else modules[0] if modules else None
    grid_flow = flow and bool((assembly.composition or {}).get("end_supports"))
    if views is None:
        views = ("front", "three-quarter", "oblique", "side", "exploded", "joint-section")
    for view in views:
        pieces = []
        for i in assembly.instances:
            if view == "joint-section" and i.module_id != section_module and not (grid_flow and i.role == "backplate"):
                continue
            if view == "joint-section" and i.role == "backplate" and not grid_flow:
                continue
            mesh = cached[i.definition_id, i.revision]
            t = np.array(i.transform)
            vertices = mesh.vertices @ t[:3, :3].T + t[:3, 3]
            if view == "exploded":
                vertices = vertices + np.array(
                    (
                        0,
                        0,
                        160
                        if i.role in ("closure", "cap", "blade", "retainer")
                        else 70
                        if i.role in ("rib", "armour")
                        else 0,
                    )
                )
            projected = project_vertices(vertices, view)
            pieces.append((i, mesh, projected, vertices))
        if not pieces:
            image = Image.new("RGB", (1100, 900), (18, 21, 27))
            ImageDraw.Draw(image).text((36, 36), "No surfaces for " + view, font=font, fill="white")
            image.save(out / f"{view}.png")
            continue
        all_points = np.concatenate([p[2] for p in pieces])
        minimum, maximum = all_points[:, :2].min(axis=0), all_points[:, :2].max(axis=0)
        extent = np.maximum(maximum - minimum, 1)
        scale = min(980 / extent[0], 710 / extent[1])
        center = (minimum + maximum) / 2
        image = Image.new("RGB", (1100, 900), (18, 21, 27))
        draw = ImageDraw.Draw(image)
        triangles = []
        for instance, mesh, projected, vertices in pieces:
            for face in mesh.faces:
                xy = (projected[face, :2] - center) * scale * np.array((1, -1)) + np.array(
                    (550, 465)
                )
                normal = np.cross(
                    vertices[face[1]] - vertices[face[0]], vertices[face[2]] - vertices[face[0]]
                )
                shade = 0.55 + 0.45 * abs(np.dot(normal, (0.3, 0.4, 0.85))) / (
                    np.linalg.norm(normal) or 1
                )
                color = tuple(int(c * shade) for c in colors.get(instance.role, colors["part"]))
                triangles.append((projected[face, 2], xy, color, False))
            if view == "front":
                part = assembly.definition_for(instance)
                pose = np.array(instance.transform)
                if abs(pose[2, 2] - 1) < 1e-9:
                    for ring in (part.outer, *part.holes):
                        world = np.array([(*p, part.thickness_mm, 1) for p in ring]) @ pose.T
                        projected_ring = project_vertices(world[:, :3], view)
                        pixels = (projected_ring[:, :2] - center) * scale * np.array(
                            (1, -1)
                        ) + np.array((550, 465))
                        for j in range(len(ring)):
                            segment = pixels[[j, (j + 1) % len(ring)]]
                            triangles.append(
                                (projected_ring[j, 2:3] + 1e-6, segment, (91, 65, 39), True)
                            )
        if view == "joint-section":
            import trimesh

            spine = next((p for p in pieces if p[0].role == "spine"), pieces[0])
            cut_y = float(np.mean(spine[3][:, 1]))
            if grid_flow:
                station = next(s for s in assembly.composition["end_supports"]["stations"]
                               if s["module_id"] == section_module)
                cut_y = station["xy"][1]
            elif creature or flow:
                web = next(p for p in pieces if p[0].role == "register")
                cut_y = web[0].transform[1][3] - assembly.definition_for(web[0]).thickness_mm / 2
            elif (assembly.composition or {}).get("family") == "radial-weave-v1":
                rib = next(p for p in pieces if p[0].role == "rib" and p[0].station_id == "s4")
                pose = np.asarray(rib[0].transform)
                cut_y = float(
                    (pose @ np.array((0, 0, assembly.definition_for(rib[0]).thickness_mm / 2, 1)))[
                        1
                    ]
                )
            for instance, mesh, projected, vertices in pieces:
                world_mesh = trimesh.Trimesh(vertices=vertices, faces=mesh.faces, process=False)
                segments = trimesh.intersections.mesh_plane(world_mesh, [0, 1, 0], [0, cut_y, 0])
                color = colors.get(instance.role, colors["part"])
                for segment in segments:
                    xy = (segment[:, [0, 2]] - center) * scale * np.array((1, -1)) + np.array(
                        (550, 465)
                    )
                    draw.line([tuple(p) for p in xy], fill=color, width=3)
        elif view == "front":
            for _, xy, color, edge in sorted(triangles, key=lambda item: item[0].mean()):
                if edge:
                    draw.line([tuple(p) for p in xy], fill=color, width=1)
                else:
                    draw.polygon([tuple(p) for p in xy], fill=color)
        else:
            image = Image.fromarray(rasterize_triangles(
                image.size, ((xy, depth, color) for depth, xy, color, _ in triangles)
            ))
            draw = ImageDraw.Draw(image)
        label = "FRONT (XY / +Z TOWARD VIEWER)" if view == "front" else view.upper()
        draw.text((36, 26), "PARAMETRIC DECO / " + label, font=font, fill="#ece1cd")
        draw.text(
            (36, 60),
            "Identified nominal geometry · physical/host checks NOT RUN",
            font=font,
            fill="#a7acb5",
        )
        draw.text(
            (36, 850),
            "mm · end-clamp tubes/bolts shown; original root hardware remains simplified",
            fill="#a7acb5",
        )
        if view == "joint-section":
            draw.text(
                (36, 810),
                (
                    "XZ section through head roots: plate/spacer compression and captured alignment webs"
                    if creature
                    else "Actual XZ section through grid bolt, tube, plate and universal board"
                    if grid_flow
                    else "Actual XZ section through trestle-supported lobe"
                    if flow
                    else "Actual XZ mesh section through central radial rib: spine notches and capture tongue"
                    if (assembly.composition or {}).get("family") == "radial-weave-v1"
                    else "Actual XZ mesh section through one spine: common slot datum and closure contact"
                ),
                fill="#edbd74",
            )
        image.save(out / f"{view}.png")

    if creature and "joint-section" in views:
        render_blade_section(assembly, cached, out)


def render_blade_section(assembly, cached, out):
    """Actual local XZ mesh section through one fin/tab/key and supporting plates."""
    import trimesh

    module = next(m for m in assembly.composition["modules"] if m.get("blade_joints"))
    joint = module["blade_joints"][0]
    by_id = {i.instance_id: i for i in assembly.instances}
    blade = by_id[joint["blade_id"]]
    pose = np.array(blade.transform)
    plane_origin = pose[:3, 3] + pose[:3, 2] * assembly.definition_for(blade).thickness_mm / 2
    plane_normal, transverse = pose[:3, 2], pose[:3, 0]
    zcap = module["cap_z_mm"]
    colors = {
        joint["blade_id"]: "#dbb071",
        joint["retainer_id"]: "#91704c",
        module["cap_id"]: "#c99d66",
        module["plate_ids"][-2]: "#75573b",
    }
    image = Image.new("RGB", (1100, 900), (18, 21, 27))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=22)
    draw.text((36, 26), "ACTUAL CAD / TRANSVERSE RIB RETAINER SECTION", font=font, fill="white")
    draw.text(
        (36, 64), "Fin midplane; cap, lower plate and transverse key; mm", font=font, fill="#b0b0b0"
    )
    for identifier, color in colors.items():
        inst = by_id[identifier]
        mesh = cached[inst.definition_id, inst.revision]
        transform = np.array(inst.transform)
        vertices = mesh.vertices @ transform[:3, :3].T + transform[:3, 3]
        world = trimesh.Trimesh(vertices=vertices, faces=mesh.faces, process=False)
        sections = trimesh.intersections.mesh_plane(world, plane_normal, plane_origin)
        for segment in sections:
            local_x = (segment - plane_origin) @ transverse
            local_z = segment[:, 2] - zcap
            xy = np.column_stack((550 + local_x * 9, 530 - local_z * 9))
            draw.line([tuple(point) for point in xy], fill=color, width=4)
    draw.text(
        (36, 760),
        "Rib shoulder bears on cap; key passes through tab below cap.",
        font=font,
        fill="#edbd74",
    )
    draw.text(
        (36, 800),
        "Remove cap/rib subassembly to access keys. Keys need handling restraint.",
        fill="#b0b0b0",
    )
    draw.text(
        (36, 835),
        "Physical fit, key security and handling NOT RUN. Not a bolt section.",
        fill="#b0b0b0",
    )
    image.save(out / "rib-joint.png")
