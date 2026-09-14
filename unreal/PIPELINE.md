# Unreal pipeline — hero ring on a 3080 Ti

Unreal is the **camera**, not the traffic engine. If a tick needs 400,000
vehicles or a 40 km expressway, it does not belong in the game thread.

## What to install (all OSS or Epic-first-party)

1. **Unreal Engine 5.4+** with World Partition.
2. **Cesium for Unreal** — world terrain + optional OSM Buildings (ion token).
3. **glTF importer** or Datasmith for Blender meshes.
4. **Mass Entity / Mass Traffic** (experimental) or Niagara for meso ribbons.
5. A tiny **WebSocket** client to read `GET /twin` + `/ws` from this repo.
   Field names, units, origin, and the UDP-vs-WebSocket call are frozen in
   **[docs/LIVE_CONTRACT.md](../docs/LIVE_CONTRACT.md)** (`docs/schema/*.schema.json`).

Do not write a Cesium alternative. Do not write a Mass alternative.
Do not speak Unity. Do not pull Google 3D Tiles on the live socket.

## Bring Naperville downtown across

```bash
# OSM extrusion (no API key)
python3 scripts/build_blender.py --source osm --preset tiled_500

# Optional photogrammetry, billed, hero ring only
export GOOGLE_MAPS_API_KEY=…
python3 scripts/build_blender.py --source google --extent downtown --lod lod3
```

Export the winning `.blend` as **glTF 2.0**, metres, Y-up or Z-up consistently.
Drop it into a World Partition grid aligned to UTM 16N origin in
`data/processed/city.json` (`origin_lonlat`). Cesium georeference should use
the same origin so slot pads line up with SUMO edges.

## Streaming rules (10 GB VRAM)

- World Partition cell ~256 m. Load 1.5 km (hero) + 8 km **impostors**.
- Nanite on for hero buildings. Disable Nanite on thin rails/wires.
- **Lumen software GI**, not Hardware RT.
- Virtual Shadow Maps: low or off. Directional light + contact shadows.
- Resolution: 1080p native or 1440p DLSS Quality.
- Google 3D Tiles: one downtown tile. Never enable metro-scale 3D Tiles.
- Meso traffic: Niagara ribbons or Mass fragments colored by TTI from `/twin`.
- Hero traffic: at most a few hundred skeletal meshes, culled at 80–120 m.
  Poses are `vehicles[].x_m` / `y_m` on `/ws` (metres, +X east). See the live contract.

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
