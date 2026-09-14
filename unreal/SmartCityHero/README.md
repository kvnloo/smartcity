# SmartCityHero — Naperville 1.5 km ring

Open **`SmartCityHero.uproject`** in **Unreal Engine 5.4+**. Unity is forbidden.
There is **no Google Maps key** in this project. Hero mesh is OSM extrusion →
glTF from this repo (`python3 scripts/build_blender.py --source osm --preset tiled_500`).

Unreal is the **camera**. SUMO + FastAPI stay the slot clock. Do not import the
40 km net as actors.

## Where glTF lands

1. Export the winning `.blend` as **glTF 2.0**, metres, one up-axis, consistently.
2. Copy `.glb` / `.gltf` (+ bins/textures) into:

   **`Content/City/Naperville/Import`**

   Content Browser path: **`/Game/City/Naperville/Import`**.
3. Import via Interchange (File → Import Into Level, or drag onto the Open World).
   If the file is metres, **Import Uniform Scale = 100** (Unreal units are cm).
4. Enable **Nanite** on building static meshes. Leave Nanite **off** on thin
   rails, wires, lanterns, and foliage cards.
5. Save the Open World as **`/Game/City/Naperville/L_NapervilleHero`**. Then set
   World Partition **cell size 25600** (256 m) and loading range ~1.5 km hero +
   8 km HLOD impostors.

Numbers, CRS, and the city.json offset live in `Config/Georef.json`.

## Origin (UTM 16N)

Unreal (0,0,0) = downtown Naperville **WGS84 −88.147, 41.75** (EPSG:32616
~404636.55 E, 4622655.27 N). +X east, +Y north, +Z up.

Cesium for Unreal (optional, ion token is yours — not in git): same
`OriginLongitude` / `OriginLatitude`.

Blender's `data/processed/city.json` origin is the OSM centroid
(−88.106604, 41.75421), about **3365 m east / 423 m north** of downtown. If the
glTF is still in that frame, place the imported actor at **(336464, 42349, 0)**
UU so downtown sits on the Unreal origin. Or re-export with downtown as 0,0.

## 3080 Ti (10 GB) — already in Config

`Config/DefaultEngine.ini` + `Config/ConsoleVariables.ini`:

| Setting | Value |
| --- | --- |
| Lumen | **software GI** (`r.DynamicGlobalIlluminationMethod=1`) |
| Hardware RT | **off** |
| Virtual Shadow Maps | **off** (directional + contact shadows) |
| Nanite | project enabled; buildings on, wires off |
| World Partition | **~256 m** cells |
| Resolution | 1080p native or 1440p DLSS Quality (DLSS is an NVIDIA plugin, not shipped) |
| Skeletal cars | only inside **80–120 m** (`SkeletalCarCullMeters=100`). Meso = Niagara/Mass, not `AActor`s |

Do not turn on Lumen Hardware Ray Tracing. Do not stream Google 3D Tiles
metro-wide. One downtown tile, later, billed — not this skeleton.

## First open

1. Install UE 5.4 (launcher or source). Generate Visual Studio / Rider project
   files if you want the C++ stub; Blueprint-only still opens the maps/config.
2. Double-click `SmartCityHero.uproject`. First compile of **SmartCityLive**
   needs a C++ toolchain (VS 2022 on Windows). If compile is skipped, disable
   that module in the .uproject and you still have the World Partition level +
   glTF folder.
3. Editor starts the engine **Open World** template (World Partition on).
   **Save As** `/Game/City/Naperville/L_NapervilleHero`.
4. World Settings / World Partition: cell **25600**, loading range covering
   **1500 m**. HLOD for the 8 km micro ring impostors.
5. Sky: slightly hazy, low sun (golden hour). Night reads `GET /lights`.

## SmartCityLive (optional C++)

Game module `SmartCityLive` polls **`GET /twin`** and **`WS /ws`** on
`http://127.0.0.1:43147` (see `DefaultGame.ini`).

```
smartcity serve --host 127.0.0.1 --port 43147
```

- `/twin` — clock, Kennedy / I-88 / Ogden, corridor TTI.
- `/ws` — vehicle lon/lat snapshot. The stub **counts** bodies inside the
  80–120 m cull. It does **not** spawn hundreds of skeletal meshes until you
  add a pawn pool. Meso ribbons stay Mass/Niagara, not this subsystem.
- I-88 extra lane: **`bI88BioswaleActive`**. Drive a **barrier spline** /
  bioswale strip visibility. Do not rebuild the highway. Do not add asphalt.

## Solarpunk lookdev

Match Blender (`blender_scripts/build_city.py`): limestone masses, copper
towers, moss parks, warm lanterns. Retired signal pads stay coral. I-88's
programmable extra lane is a **bioswale + AV chevrons**, not a twelfth lane
of asphalt — see `Content/City/Naperville/I88/`.

| Role | Approx. base color (linear-ish) |
| --- | --- |
| Limestone | 0.62, 0.54, 0.42 |
| Copper | 0.55, 0.36, 0.22 |
| Moss | 0.22, 0.42, 0.24 |
| Retired signals | 0.82, 0.42, 0.22 |

## What not to put in this project

- Unity HDRP, CARLA, or a second renderer.
- Google Maps keys, ion tokens, or billed 3D Tiles in git.
- 400k `AActor` cars. SUMO meso / Niagara for the 40 km ring.
- A custom Cesium or Mass replacement.
- Hardware Lumen on this 10 GB card for a city.

Pipeline details: [`../PIPELINE.md`](../PIPELINE.md). Twin contract:
[`../../docs/IDEAS.md`](../../docs/IDEAS.md).
