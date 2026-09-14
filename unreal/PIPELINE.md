# Unreal pipeline — hero ring on a 3080 Ti

Unreal is the **camera**, not the traffic engine. Unity is forbidden. If a tick
needs 400,000 vehicles or a 40 km expressway, it does not belong in the game
thread.

## Open this (UE 5.4+)

Open [`SmartCityHero/SmartCityHero.uproject`](SmartCityHero/SmartCityHero.uproject).
Drop glTF into [`SmartCityHero/Content/City/Naperville/Import`](SmartCityHero/Content/City/Naperville/Import)
(`/Game/City/Naperville/Import`). Origin, cell size, and city.json offset:
[`SmartCityHero/Config/Georef.json`](SmartCityHero/Config/Georef.json). Human
walkthrough: [`SmartCityHero/README.md`](SmartCityHero/README.md).

No Google Maps key. OSM glTF only until a billed hero tile exists.

## What to install (all OSS or Epic-first-party)

1. **Unreal Engine 5.4+** with World Partition.
2. **Cesium for Unreal** — world terrain + optional OSM Buildings (ion token).
3. **glTF importer** (Interchange) or Datasmith for Blender meshes.
4. **Mass Entity / Mass Traffic** (experimental) or Niagara for meso ribbons.
5. Optional C++ module **SmartCityLive** in this project — `GET /twin` + `WS /ws`.
   Field names, units, origin, and the UDP-vs-WebSocket call are frozen in
   **[docs/LIVE_CONTRACT.md](../docs/LIVE_CONTRACT.md)** (`docs/schema/*.schema.json`).

Do not write a Cesium alternative. Do not write a Mass alternative.
Do not speak Unity. Do not pull Google 3D Tiles on the live socket.

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

The `--export gltf` path is the one Unreal Datasmith / Interchange should load.
Scene is **metres**, Blender **+Z up**, glTF file **+Y up**, Unreal **+Z up**.
If the import looks 100× too small, set import uniform scale to **100**. Mesh
XY is relative to `city.json` (often the OSM centroid). Unreal (0,0,0), Cesium,
and **SmartCityLive** stay on downtown **−88.147, 41.75** — place the actor at
sidecar `unreal.place_at` (also in
[`SmartCityHero/Config/Georef.json`](SmartCityHero/Config/Georef.json)). The
1.5 km hero clip is centered on downtown, not the OSM centroid. Drop the GLB
into [`SmartCityHero/Content/City/Naperville/Import`](SmartCityHero/Content/City/Naperville/Import).
Details: `output/gltf/README.md`.

## Streaming rules (10 GB VRAM)

- World Partition cell ~256 m. Load 1.5 km (hero) + 8 km **impostors**.
- Nanite on for hero buildings. Disable Nanite on thin rails/wires.
- **Lumen software GI**, not Hardware RT.
- Virtual Shadow Maps: low or off. Directional light + contact shadows.
- Resolution: 1080p native or 1440p DLSS Quality.
- Google 3D Tiles: one downtown tile. Never enable metro-scale 3D Tiles.
- Meso traffic: Niagara ribbons or Mass fragments colored by TTI from `/twin`.
- Hero traffic: at most a few hundred skeletal meshes, culled at 80–120 m.
  Poses are `vehicles[].x_m` / `y_m` on `/ws` (metres from `city.json`, +X east).
  Unreal `(0,0,0)` is downtown: `uu = (x_m - origin.downtown_x_m) * 100`. See the live contract.

## Talking to SUMO

`python3 scripts/build_sumo_net.py` is the path to a compiled
`output/sumo/naperville.net.xml` when Eclipse SUMO's **netconvert** is
installed. It always writes nod/edg/typ/con XML, zipper connections, a 0.25 s
`.sumocfg`, and `facilities.json` (Kennedy REVLAC real; I-88 / Ogden zippers
`fictional`). Without SUMO, the TraCI **mock** in `smartcity.micro` still
publishes `/ws` snapshots. Install: `docs/SUMO.md`.

```
netconvert --node-files naperville.nod.xml --edge-files naperville.edg.xml \
  --type-files naperville.typ.xml --connection-files naperville.con.xml \
  --output-file naperville.net.xml
```

Live TraCI: `SMARTCITY_SUMO=1 smartcity serve`. This backend remains the
**slot clock** and **tidal operator**: at each 0.25 s it publishes Kennedy /
I-88 direction and BATCH reservations. A Unreal subsystem applies extra-lane
meshes (move a barrier spline, do not rebuild the highway).

For the 40 km ring, convert Geofabrik Illinois (clipped) with
`netconvert --osm-file` and `--keep-edges.by-vclass passenger`, then enable
SUMO **meso**. Do not import that net into Unreal as actors.

## Solarpunk lookdev

Materials travel from Blender: limestone buildings, copper towers, moss parks,
warm lanterns. Retired signal pads stay the coral mesh from `build_city.py`.
I-88 extra lane: a narrow green strip + AV chevrons, not more asphalt.

Sky: slightly hazy, low sun (golden-hour default). Night: occupancy-dimmed
street lights (`GET /lights`).
