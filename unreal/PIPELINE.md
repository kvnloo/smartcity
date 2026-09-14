# Unreal pipeline — hero ring on a 3080 Ti

Unreal is the **camera**, not the traffic engine. If a tick needs 400,000
vehicles or a 40 km expressway, it does not belong in the game thread.

## What to install (all OSS or Epic-first-party)

1. **Unreal Engine 5.4+** with World Partition.
2. **Cesium for Unreal** — world terrain + optional OSM Buildings (ion token).
3. **glTF importer** or Datasmith for Blender meshes.
4. **Mass Entity / Mass Traffic** (experimental) or Niagara for meso ribbons.
5. A tiny **UDP/WebSocket** plugin to read `GET /twin` + `/ws` from this repo.

Do not write a Cesium alternative. Do not write a Mass alternative.

## Bring Naperville downtown across

```bash
# OSM extrusion → glTF 2.0 (no API key). Unreal target:
#   output/gltf/naperville_tiled_500.glb
# Sidecar (origin, metres, up-axis):
#   output/gltf/naperville_tiled_500.import.json
python3 scripts/build_blender.py --source osm --preset tiled_500 --export gltf

# Optional photogrammetry, billed, hero ring only — not required for this mesh
export GOOGLE_MAPS_API_KEY=…
python3 scripts/build_blender.py --source google --extent downtown --lod lod3
```

The `--export gltf` path is the one Unreal Datasmith / the built-in glTF
importer should load. Scene is **metres**, Blender **+Z up**, glTF file **+Y
up**, Unreal **+Z up**. If the import looks 100× too small, set import
uniform scale to **100** (metres → Unreal centimetres). Origin is
`data/processed/city.json` `origin_lonlat` (else -88.147, 41.75). Place the
actor at `(0,0,0)` and point Cesium georeference at that lon/lat so slot
pads line up with SUMO edges. Details: `output/gltf/README.md`.

## Streaming rules (10 GB VRAM)

- World Partition cell ~256 m. Load 1.5 km (hero) + 8 km **impostors**.
- Nanite on for hero buildings. Disable Nanite on thin rails/wires.
- **Lumen software GI**, not Hardware RT.
- Virtual Shadow Maps: low or off. Directional light + contact shadows.
- Resolution: 1080p native or 1440p DLSS Quality.
- Google 3D Tiles: one downtown tile. Never enable metro-scale 3D Tiles.
- Meso traffic: Niagara ribbons or Mass fragments colored by TTI from `/twin`.
- Hero traffic: at most a few hundred skeletal meshes, culled at 80–120 m.
  Their positions come from SUMO TraCI or the FastAPI `/ws` snapshot.

## Talking to SUMO

`python3 scripts/build_sumo_net.py` writes `output/sumo/naperville.nod.xml` and
`.edg.xml`. With Eclipse SUMO installed:

```
netconvert --node-files naperville.nod.xml --edge-files naperville.edg.xml \
  --output-file naperville.net.xml
```

Run SUMO with TraCI. This backend remains the **slot clock** and **tidal
operator**: at each 0.25 s, FastAPI publishes Kennedy / I-88 direction and
BATCH reservations. A Unreal subsystem applies extra-lane meshes (move a
barrier spline, do not rebuild the highway).

For the 40 km ring, convert Geofabrik Illinois (clipped) with
`netconvert --osm-file` and `--keep-edges.by-vclass passenger`, then enable
SUMO **meso**. Do not import that net into Unreal as actors.

## Solarpunk lookdev

Materials travel from Blender: limestone buildings, copper towers, moss parks,
warm lanterns. Retired signal pads stay the coral mesh from `build_city.py`.
I-88 extra lane: a narrow green strip + AV chevrons, not more asphalt.

Sky: slightly hazy, low sun (golden-hour default). Night: occupancy-dimmed
street lights (`GET /lights`).
