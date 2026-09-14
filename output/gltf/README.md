# glTF 2.0 — Naperville hero mesh for Unreal

Unreal target (unambiguous):

```
output/gltf/naperville_tiled_500.glb
```

Sidecar (origin / units / up-axis, committed even without Blender):

```
output/gltf/naperville_tiled_500.import.json
```

`.glb` / `.gltf` / `.bin` are gitignored. Do not commit giant binaries.

## Command (OSM extrusion, no Google key)

```bash
python3 scripts/build_blender.py --source osm --preset tiled_500 --export gltf
```

That is the Datasmith / glTF importer path. It does **not** call Google 3D Tiles.

Optional bounds (faster smoke):

```bash
python3 scripts/build_blender.py --source osm --preset tiled_500 --export gltf \
  --hero-radius 400 --max-buildings 40
```

`--export gltf` defaults `--hero-radius` to **1500 m** (hero ring). `--hero-radius 0` keeps the whole processed city. `--export blend` (default) is the research `.blend` path and does not clip.

Needs `data/processed/city.json` (`python3 scripts/process_city.py`). Origin is `meta.origin_lonlat` when that file exists, else downtown **(-88.147, 41.75)**.

## Axes and scale (keep these consistent)

| Stage | Units | Up |
| --- | --- | --- |
| Blender scene | metres (1 BU = 1 m) | **+Z** |
| glTF 2.0 file | metres | **+Y** (exporter converts) |
| Unreal world | centimetres | **+Z** |

XY in the file is **EPSG:32616** easting/northing relative to sidecar
`origin_lonlat` (OSM centroid when `city.json` exists). Unreal (0,0,0) is
**downtown −88.147, 41.75**. Place the imported actor at sidecar
`unreal.place_at` (centimetres). Cesium / SmartCityLive use that downtown
origin. The 1.5 km clip is around downtown (`hero_clip_center_mesh_m`), not
the OSM centroid.

## Unreal 5.4+ import

1. Enable **glTF** (Edit → Plugins) **or** Datasmith. Either importer can read this glTF 2.0 GLB.
2. Copy into **`unreal/SmartCityHero/Content/City/Naperville/Import`** (or import `output/gltf/naperville_tiled_500.glb` into that folder).
3. **Convert Scene** on (glTF +Y → Unreal +Z).
4. **Import Uniform Scale = 100** if the mesh is 100× too small (metres → centimetres). If the importer already treats glTF as metres, leave scale at 1 and confirm a 10 m pad is ~1000 Unreal units.
5. Place the actor at sidecar **`unreal.place_at`**. Set **CesiumGeoreference** to **−88.147, 41.75** (not the mesh `origin_lonlat` unless they already match).
6. World Partition cell ~256 m. Nanite on hero buildings. No Lumen Hardware RT on a 3080 Ti.

Read the sidecar before changing georeference. Do not mix this OSM mesh with a Google 3D Tiles tileset at a different origin.

## Lookdev

Limestone masses, copper towers, moss parks, warm lantern boxes at intersections. Retired traffic signals are **pads** (`RetiredSignals`), not heads.

## Export status

This worktree has no Blender binary at `tools/blender-5.1.2-linux-x64/blender` and none on `PATH`. Running the documented command writes the sidecar and exits 1 (`Blender not found` / `Sidecar written; mesh export skipped`). The Python entry, origin/scale tests, and Unreal import contract still ship. Drop Blender 5.1+ at that portable path (or on PATH) and rerun to emit `naperville_tiled_500.glb`. Bounded smoke: add `--hero-radius 400 --max-buildings 40`.
