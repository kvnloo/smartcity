"""Blender 4.x / 5.x city builder for Naperville.

Reads data/processed/city.json and emits a tiled .blend plus a JSON stats
dump used by the RT research loop. No bpy.ops in the hot path: meshes are
batched with foreach_set.

Scene units are metres, +Z up, XY = UTM 16N relative to city.json origin.
`--export gltf` writes glTF 2.0 (metres, +Y up) for Unreal.

Run:
  blender --background --python blender_scripts/build_city.py -- --preset tiled_500
  python3 scripts/build_blender.py --source osm --preset tiled_500 --export gltf
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from smartcity.gltf_export import SOLARPUNK_MATERIALS, glb_path as default_glb_path, hero_keep

DEFAULT_CITY = ROOT / "data" / "processed" / "city.json"
OUT_DIR = ROOT / "output" / "blends"
STATS_DIR = ROOT / "output" / "research"

# Solarpunk lookdev: limestone, copper, moss, warm lanterns — not generic gray.
COLORS = {
    "asphalt": (0.16, 0.14, 0.12, 1),
    "lane": (0.22, 0.20, 0.16, 1),
    "water": (0.14, 0.32, 0.38, 1),
    "ground": (0.18, 0.22, 0.16, 1),
    "slot": (0.42, 0.72, 0.38, 1),
    "boundary": (0.22, 0.26, 0.22, 1),
}
for _name, _spec in SOLARPUNK_MATERIALS.items():
    COLORS[_name] = _spec["rgba"]


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--city", default=str(DEFAULT_CITY))
    p.add_argument("--preset", default="tiled_500")
    p.add_argument("--out", default="")
    p.add_argument("--export", choices=("blend", "gltf"), default="blend")
    p.add_argument("--out-gltf", default="")
    p.add_argument("--hero-radius", type=float, default=0.0, help="0 = whole city; 1500 = Unreal hero ring")
    p.add_argument("--max-buildings", type=int, default=0, help="0 = preset cap")
    return p.parse_args(argv)


PRESETS = {
    "naive_objects": {"tile": 1e9, "join": False, "road_step": 6.0, "max_buildings": 10_000},
    "tiled_250": {"tile": 250.0, "join": True, "road_step": 8.0, "max_buildings": 10_000},
    "tiled_500": {"tile": 500.0, "join": True, "road_step": 10.0, "max_buildings": 10_000},
    "tiled_1000": {"tile": 1000.0, "join": True, "road_step": 14.0, "max_buildings": 10_000},
    "lod_lite": {"tile": 750.0, "join": True, "road_step": 16.0, "max_buildings": 10_000, "box_buildings": True},
}


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def _set_bsdf(bsdf, name: str, value) -> None:
    sock = bsdf.inputs.get(name)
    if sock is None:
        return
    try:
        sock.default_value = value
    except (TypeError, ValueError):
        pass


def mat(name: str, rgba: tuple[float, float, float, float]):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    spec = SOLARPUNK_MATERIALS.get(name, {})
    if bsdf:
        _set_bsdf(bsdf, "Base Color", spec.get("rgba", rgba))
        _set_bsdf(bsdf, "Roughness", spec.get("roughness", 0.72))
        _set_bsdf(bsdf, "Metallic", spec.get("metallic", 0.0))
        emission = spec.get("emission")
        if emission is not None:
            _set_bsdf(bsdf, "Emission Color", emission)
            _set_bsdf(bsdf, "Emission", emission)
        strength = float(spec.get("emission_strength") or 0.0)
        if strength:
            _set_bsdf(bsdf, "Emission Strength", strength)
    return m


def mesh_from_arrays(name: str, verts: np.ndarray, faces: list[tuple]):
    mesh = bpy.data.meshes.new(name)
    if verts.size == 0 or not faces:
        return mesh
    n_v = verts.shape[0]
    loops = np.concatenate([np.array(f, dtype=np.int32) for f in faces])
    loop_total = np.array([len(f) for f in faces], dtype=np.int32)
    loop_start = np.zeros(len(faces), dtype=np.int32)
    loop_start[1:] = np.cumsum(loop_total)[:-1]
    mesh.vertices.add(n_v)
    mesh.loops.add(int(loops.size))
    mesh.polygons.add(len(faces))
    mesh.vertices.foreach_set("co", verts.astype(np.float32).ravel())
    mesh.loops.foreach_set("vertex_index", loops)
    mesh.polygons.foreach_set("loop_start", loop_start)
    mesh.polygons.foreach_set("loop_total", loop_total)
    mesh.update()
    return mesh


def add_object(name: str, mesh, location=(0, 0, 0), material=None, collection=None):
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    (collection or bpy.context.scene.collection).objects.link(obj)
    if material:
        obj.data.materials.append(material)
    return obj


def resample(coords, step: float):
    if len(coords) < 2:
        return coords
    out = [coords[0]]
    acc = 0.0
    for i in range(len(coords) - 1):
        x0, y0 = coords[i]
        x1, y1 = coords[i + 1]
        seg = math.hypot(x1 - x0, y1 - y0)
        if seg < 1e-6:
            continue
        acc += seg
        while acc >= step:
            acc -= step
            t = 1.0 - acc / seg
            out.append([x0 + (x1 - x0) * t, y0 + (y1 - y0) * t])
        out.append([x1, y1])
    # unique-ish
    cleaned = [out[0]]
    for p in out[1:]:
        if math.hypot(p[0] - cleaned[-1][0], p[1] - cleaned[-1][1]) > 0.4:
            cleaned.append(p)
    return cleaned


def road_strip(coords, width: float, step: float):
    pts = resample(coords, step)
    if len(pts) < 2:
        return None
    half = width * 0.5
    left = []
    right = []
    for i, (x, y) in enumerate(pts):
        if i == 0:
            dx, dy = pts[1][0] - x, pts[1][1] - y
        elif i == len(pts) - 1:
            dx, dy = x - pts[i - 1][0], y - pts[i - 1][1]
        else:
            dx, dy = pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        left.append((x + nx * half, y + ny * half, 0.04))
        right.append((x - nx * half, y - ny * half, 0.04))
    verts = left + right
    faces = []
    n = len(left)
    for i in range(n - 1):
        faces.append((i, i + 1, n + i + 1, n + i))
    return np.array(verts, dtype=np.float64), faces


def extrude_building(ring, height: float, box: bool):
    if box:
        xs = [p[0] for p in ring[:-1]]
        ys = [p[1] for p in ring[:-1]]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        ring = [(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy), (minx, miny)]
    base = ring[:-1] if ring[0] == ring[-1] else ring
    if len(base) < 3:
        return None
    n = len(base)
    verts = [(p[0], p[1], 0.0) for p in base] + [(p[0], p[1], height) for p in base]
    faces = [tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return np.array(verts, dtype=np.float64), faces


def tile_key(x, y, tile):
    return (int(math.floor(x / tile)), int(math.floor(y / tile)))


def offset_verts(verts, ox, oy):
    v = verts.copy()
    v[:, 0] -= ox
    v[:, 1] -= oy
    return v


def combine(chunks, ox, oy):
    if not chunks:
        return None
    verts_list = []
    faces = []
    base = 0
    for verts, fs in chunks:
        v = offset_verts(verts, ox, oy)
        verts_list.append(v)
        faces.extend([tuple(i + base for i in f) for f in fs])
        base += v.shape[0]
    return np.vstack(verts_list), faces


def apply_eevee(scene):
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.eevee.taa_samples = 8
    scene.eevee.use_shadows = False
    scene.eevee.use_volumetric_shadows = False
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0  # 1 Blender unit = 1 metre
    for view in scene.view_layers:
        view.use_pass_z = False


def lantern_box(x, y, z=4.2, half=0.18, h=0.45):
    verts = [
        (x - half, y - half, z),
        (x + half, y - half, z),
        (x + half, y + half, z),
        (x - half, y + half, z),
        (x - half, y - half, z + h),
        (x + half, y - half, z + h),
        (x + half, y + half, z + h),
        (x - half, y + half, z + h),
    ]
    faces = [
        (0, 1, 2, 3),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ]
    return np.array(verts, dtype=np.float64), faces


def export_gltf(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    kwargs = {
        "filepath": str(path),
        "export_format": "GLB",
        "export_yup": True,
        "export_apply": True,
        "export_cameras": False,
        "export_lights": False,
        "export_extras": True,
        "export_animations": False,
    }
    try:
        bpy.ops.export_scene.gltf(**kwargs)
    except TypeError:
        bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB")
    print(f"wrote glTF {path}", flush=True)


def stats_dump(path: Path, t0: float, preset: str):
    scene = bpy.context.scene
    meshes = list(bpy.data.meshes)
    objects = [o for o in bpy.data.objects if o.type == "MESH"]
    n_obj = len(objects)
    tris = 0
    verts = 0
    for m in meshes:
        m.calc_loop_triangles()
        tris += len(m.loop_triangles)
        verts += len(m.vertices)
    dg_t0 = time.perf_counter()
    bpy.context.view_layer.update()
    dg_ms = (time.perf_counter() - dg_t0) * 1000.0
    text = scene.statistics(bpy.context.view_layer)
    payload = {
        "preset": preset,
        "seconds": round(time.perf_counter() - t0, 3),
        "objects": n_obj,
        "meshes": len(meshes),
        "materials": len(bpy.data.materials),
        "verts": verts,
        "tris": tris,
        "depsgraph_ms": round(dg_ms, 3),
        "statistics": text,
        "rt_cost": round(
            0.45 * math.log10(n_obj + 1)
            + 0.45 * math.log10(max(tris, 1) + 1)
            + 0.10 * math.log10(max(dg_ms, 0.01) + 1),
            4,
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def build(
    city_path: Path,
    preset_name: str,
    out_path: Path,
    *,
    export: str = "blend",
    out_gltf: Path | None = None,
    hero_radius: float = 0.0,
    max_buildings: int = 0,
):
    t0 = time.perf_counter()
    preset = PRESETS[preset_name]
    city = json.loads(city_path.read_text(encoding="utf-8"))
    tile = float(preset["tile"])
    join = bool(preset["join"])
    step = float(preset["road_step"])
    box = bool(preset.get("box_buildings"))
    radius = float(hero_radius)
    cap = int(max_buildings) if max_buildings else int(preset["max_buildings"])
    clear_scene()
    scene = bpy.context.scene
    apply_eevee(scene)

    mats = {k: mat(k, v) for k, v in COLORS.items()}
    coll_roads = bpy.data.collections.new("Roads")
    coll_bldg = bpy.data.collections.new("Buildings")
    coll_ix = bpy.data.collections.new("Intersections")
    coll_env = bpy.data.collections.new("Environment")
    coll_lights = bpy.data.collections.new("Lanterns")
    for c in (coll_roads, coll_bldg, coll_ix, coll_env, coll_lights):
        scene.collection.children.link(c)

    meta = city.get("meta") or {}
    origin_ll = meta.get("origin_lonlat") or [-88.147, 41.75]
    origin = bpy.data.objects.new("UTM16N_Origin", None)
    origin.empty_display_type = "PLAIN_AXES"
    origin["crs"] = meta.get("crs") or "EPSG:32616"
    origin["origin_lon"] = float(origin_ll[0])
    origin["origin_lat"] = float(origin_ll[1])
    origin["units"] = "metres"
    origin["up"] = "+Z"
    scene.collection.objects.link(origin)

    if radius > 0:
        minx = miny = -radius
        maxx = maxy = radius
    else:
        minx, miny, maxx, maxy = city["meta"]["bbox_m"]
    ground_v = np.array(
        [
            (minx, miny, -0.05),
            (maxx, miny, -0.05),
            (maxx, maxy, -0.05),
            (minx, maxy, -0.05),
        ],
        dtype=np.float64,
    )
    gmesh = mesh_from_arrays("ground", ground_v, [(0, 1, 2, 3)])
    add_object("Ground", gmesh, material=mats["ground"], collection=coll_env)

    road_tiles: dict = {}
    for road in city["roads"]:
        coords = road["coords"]
        if not coords or not hero_keep(coords[0][0], coords[0][1], radius):
            continue
        strip = road_strip(coords, max(4.0, float(road["width"])), step)
        if strip is None:
            continue
        verts, faces = strip
        cx, cy = verts[0][0], verts[0][1]
        key = tile_key(cx, cy, tile) if join else ("road", road["id"])
        road_tiles.setdefault(key, []).append((verts, faces))

    for key, chunks in road_tiles.items():
        if join:
            ox = key[0] * tile + tile * 0.5
            oy = key[1] * tile + tile * 0.5
            packed = combine(chunks, ox, oy)
            if not packed:
                continue
            verts, faces = packed
            mesh = mesh_from_arrays(f"roads_{key[0]}_{key[1]}", verts, faces)
            add_object(f"Roads_{key[0]}_{key[1]}", mesh, location=(ox, oy, 0), material=mats["asphalt"], collection=coll_roads)
        else:
            verts, faces = chunks[0]
            mesh = mesh_from_arrays(f"road_{key[1]}", verts, faces)
            add_object(f"Road_{key[1]}", mesh, material=mats["asphalt"], collection=coll_roads)

    bldg_tiles: dict = {}
    kept = [b for b in city["buildings"] if hero_keep(b["cx"], b["cy"], radius)][:cap]
    for b in kept:
        extruded = extrude_building(b["rings"][0], float(b["height"]), box)
        if extruded is None:
            continue
        verts, faces = extruded
        key = tile_key(b["cx"], b["cy"], tile) if join else ("b", b["id"])
        bldg_tiles.setdefault(key, []).append((verts, faces, b["height"]))

    for key, chunks in bldg_tiles.items():
        if join:
            ox = key[0] * tile + tile * 0.5
            oy = key[1] * tile + tile * 0.5
            packed = combine([(v, f) for v, f, _h in chunks], ox, oy)
            if not packed:
                continue
            verts, faces = packed
            mesh = mesh_from_arrays(f"bldg_{key[0]}_{key[1]}", verts, faces)
            avg_h = sum(h for _v, _f, h in chunks) / len(chunks)
            mat_use = mats["copper"] if avg_h > 14 else mats["limestone"]
            add_object(f"Buildings_{key[0]}_{key[1]}", mesh, location=(ox, oy, 0), material=mat_use, collection=coll_bldg)
        else:
            verts, faces, h = chunks[0]
            mesh = mesh_from_arrays(f"bldg_{key[1]}", verts, faces)
            add_object(f"Building_{key[1]}", mesh, material=mats["limestone"], collection=coll_bldg)

    def flat_polys(items, name, coll, material, z):
        chunks = []
        for it in items:
            ring = it["rings"][0]
            base = ring[:-1] if ring and ring[0] == ring[-1] else ring
            if len(base) < 3:
                continue
            if not hero_keep(base[0][0], base[0][1], radius):
                continue
            verts = np.array([(p[0], p[1], z) for p in base], dtype=np.float64)
            chunks.append((verts, [tuple(range(len(base)))]))
        if not chunks:
            return
        packed = combine(chunks, 0, 0)
        mesh = mesh_from_arrays(name, packed[0], packed[1])
        add_object(name, mesh, material=material, collection=coll)

    flat_polys(city["parks"], "Parks", coll_env, mats["moss"], 0.02)
    flat_polys(city["water"], "Water", coll_env, mats["water"], 0.01)

    # Slot pads at every intersection. Retired signals stay coral pads, not heads.
    ix_chunks_slot = []
    ix_chunks_old = []
    lantern_chunks = []
    for ix in city["intersections"]:
        if not hero_keep(ix["x"], ix["y"], radius):
            continue
        r = max(6.0, float(ix["radius"]) * 0.55)
        segs = 12
        verts = [(ix["x"], ix["y"], 0.08)]
        faces_idx = []
        for i in range(segs):
            a0 = 2 * math.pi * i / segs
            verts.append((ix["x"] + math.cos(a0) * r, ix["y"] + math.sin(a0) * r, 0.08))
        for i in range(segs):
            faces_idx.append((0, 1 + i, 1 + ((i + 1) % segs)))
        arr = np.array(verts, dtype=np.float64)
        (ix_chunks_old if ix.get("had_signals") else ix_chunks_slot).append((arr, faces_idx))
        lantern_chunks.append(lantern_box(ix["x"], ix["y"]))
    if ix_chunks_slot:
        packed = combine(ix_chunks_slot, 0, 0)
        mesh = mesh_from_arrays("slot_pads", packed[0], packed[1])
        add_object("SlotPads", mesh, material=mats["slot"], collection=coll_ix)
    if ix_chunks_old:
        packed = combine(ix_chunks_old, 0, 0)
        mesh = mesh_from_arrays("retired_signals", packed[0], packed[1])
        add_object("RetiredSignals", mesh, material=mats["retired_pad"], collection=coll_ix)
    if lantern_chunks:
        packed = combine(lantern_chunks, 0, 0)
        mesh = mesh_from_arrays("lanterns", packed[0], packed[1])
        add_object("WarmLanterns", mesh, material=mats["lantern"], collection=coll_lights)

    # Camera over downtown centroid.
    cam_d = bpy.data.cameras.new("Overview")
    cam_d.clip_end = 80000
    cam_d.lens = 24
    cam = bpy.data.objects.new("Overview", cam_d)
    cam.location = (0, -1800, 1400)
    cam.rotation_euler = (math.radians(52), 0, 0)
    scene.collection.objects.link(cam)
    scene.camera = cam

    sun_d = bpy.data.lights.new("Sun", "SUN")
    sun_d.energy = 4.0
    sun = bpy.data.objects.new("Sun", sun_d)
    sun.rotation_euler = (math.radians(42), 0, math.radians(30))
    scene.collection.objects.link(sun)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_path), compress=True)
    if export == "gltf" and out_gltf is not None:
        export_gltf(out_gltf)
    stats_path = STATS_DIR / f"{preset_name}.json"
    payload = stats_dump(stats_path, t0, preset_name)
    payload["blend"] = str(out_path)
    if export == "gltf" and out_gltf is not None:
        payload["gltf"] = str(out_gltf)
        payload["hero_radius_m"] = radius
        payload["units"] = "metres"
        payload["blender_up"] = "+Z"
        payload["gltf_up"] = "+Y"
    stats_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload))


def main():
    args = parse_args()
    out = Path(args.out) if args.out else OUT_DIR / f"naperville_{args.preset}.blend"
    gltf = Path(args.out_gltf) if args.out_gltf else default_glb_path(ROOT, args.preset)
    build(
        Path(args.city),
        args.preset,
        out,
        export=args.export,
        out_gltf=gltf,
        hero_radius=args.hero_radius,
        max_buildings=args.max_buildings,
    )


if __name__ == "__main__":
    main()
