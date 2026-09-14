# SmartCity — Chicagoland nested twin

Naperville is the hero street. Greater Chicagoland is the operating picture.
Nothing in this repo pretends one simulator can car-follow from Waukegan to
Gary on a **3080 Ti (10 GB)** and a **10900K**. Weather models already solved
that: coarse grid everywhere, fine grid at the camera.

**Locked decisions**

| Decision | Call |
| --- | --- |
| Hero renderer | **Unreal Engine 5.4+** (Nanite, Lumen software GI). Not Unity. |
| Mesh authoring | **Blender 5.1+** (OSM extrusion now; Google 3D Tiles later, billed, hero only) |
| Traffic | Eclipse **SUMO** micro 8 km / meso 40 km. This Python package is the slot clock + tidal operator. |
| Phone | **Lookdev**, not the sim. Galaxy S25 Ultra (`SM-S938`) gets ultra LOD. |
| Public git | **kvnloo/smartcity** → Pages **https://kvnloo.github.io/smartcity/** from `nightly` |
| Contribution | [Verified OSS Loop](https://github.com/kvnloo/verified-oss-loop), scheme `rolling` |
| Google Photorealistic 3D Tiles | **Later.** Do not block. Esri/Maxar + Sentinel-2 + OSM until then. |

Workers never merge `main` or `dev`. Overnight work lands on `nightly`.

The idea dump (solarpunk, papers, what we will not build) lives in
**[docs/IDEAS.md](docs/IDEAS.md)**. Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Data: [docs/DATA.md](docs/DATA.md). Unreal: [unreal/PIPELINE.md](unreal/PIPELINE.md).

## Three products, one geology

```
┌─────────────────────────────────────────────────────────────┐
│  Unreal 5 (workstation)                                      │
│  1.5 km Nanite street · Blender mesh · < few hundred cars    │
│  Lumen software · World Partition · Cesium terrain           │
└──────────────────────────▲──────────────────────────────────┘
                           │ UDP / WebSocket snapshot
┌──────────────────────────┴──────────────────────────────────┐
│  This repo (FastAPI + SUMO)                                  │
│  micro 8 km 0.25 s · meso 40 km 1 s · macro 120 km 5 s       │
│  Kennedy REVLAC (real) · I-88 / Ogden zipper (proposed)      │
│  Tachet BATCH / Dresner AIM pads · 45 mph arterial cap       │
└──────────────────────────▲──────────────────────────────────┘
                           │ baked twin.json + XYZ tiles
┌──────────────────────────┴──────────────────────────────────┐
│  GitHub Pages lookdev (`site/`)                              │
│  Photoreal camera · device LOD · no SUMO · no Nanite         │
│  S25 Ultra: terrain + extruded masses. Thin phones: raster.  │
└─────────────────────────────────────────────────────────────┘
```

If it needs 400,000 actors, it is not Unreal. If it needs a shader, it is not
SUMO. If it needs a GPU phone to run a metro, it is not Pages.

## Nested rings

| Ring | Engine | Radius | Tick | What you see |
| --- | --- | --- | --- | --- |
| hero | Unreal Nanite + Blender mesh | 1.5 km | 1/60 s | AAA street, characters, slot pads |
| micro | SUMO + BATCH/AIM + this repo | 8 km | 0.25 s | Naperville + I-88 ramps, every car |
| meso | SUMO meso / cell-transmission | 40 km | 1 s | Expressway density, not liveries |
| macro | LODES proxy + GTFS + tidal clock | 120 km | 5 s | Ribbon flows Loop ↔ suburbs |

## GitHub Pages lookdev (mobile)

Not the sim. Esri/Maxar photoreal, Sentinel-2 underlay, OSM fill-extrusion,
Terrarium DEM, sky fog. WebGL-less browsers get an Esri mosaic. MapLibre is
code-split so mosaic devices do not download the GL renderer.

```bash
cd site
npm ci
npm test          # LOD, camera, HUD, tiles, style
npm run dev       # http://127.0.0.1:43180
```

CI (`.github/workflows/verified-oss-loop.yml`) builds `site/dist` on `nightly`
and deploys Pages. After you click **Create repo** as `kvnloo/smartcity` and
set Pages → GitHub Actions:

**https://kvnloo.github.io/smartcity/**

Galaxy S25 Ultra UA `SM-S938` forces **ultra** LOD (terrain + buildings + sky).
Save-Data or ~2 GB RAM stays satellite-only.

## Verify (TDD gate)

```bash
./.verified-oss-loop/verify.sh    # pytest + lookdev vitest + site build
python3 -m pytest -q
npm test --prefix site
```

Scheme: `python3 .verified-oss-loop/rollout.py show` → worker base `nightly`,
feature PRs → `preview`. See [rollout](https://github.com/kvnloo/verified-oss-loop/blob/main/docs/rollout.md).

## Ops map (twin clock)

```bash
python3 -m pip install -e ".[dev]"
python3 scripts/ingest_open_data.py   # optional SODA / NOAA / poles
smartcity serve --host 127.0.0.1 --port 43147
smartcity twin --hour 7.5
smartcity bench --seconds 25
python3 scripts/build_sumo_net.py     # 8 km ring XML; netconvert → .net.xml if SUMO is installed
smartcity micro --seconds 8           # TraCI if SUMO is up, else mock (pytest uses this)
```

Open `http://127.0.0.1:43147`. `/ws` is the micro-ring vehicle snapshot (SUMO or
mock). Kennedy inbound at 07:30 is the default clock. SUMO install: [docs/SUMO.md](docs/SUMO.md).
Do not put SUMO in `site/`.

## Blender → Unreal (hero mesh)

```bash
python3 scripts/fetch_naperville.py
python3 scripts/process_city.py
python3 scripts/build_blender.py --source osm --preset tiled_500
```

Export the winning `.blend` as **glTF 2.0**, metres, origin =
`data/processed/city.json` (`origin_lonlat`). Drop into Unreal World Partition
(UTM 16N). Cesium georeference uses the same origin so slot pads sit on SUMO
edges. Google 3D Tiles via Blosm wait for a billing key — OSM is the default.

Next.js cinematic intersection (one weave vs lights): `npm install && npm run dev`
→ `http://127.0.0.1:43217`. That is a slot diagram, not the city.

## Hardware budget (3080 Ti 10 GB)

1080p or 1440p DLSS Quality. **No Lumen Hardware RT.** Virtual Shadow Maps low
or off. World Partition ~256 m cells, 1.5 km hero + 8 km impostors. Google 3D
Tiles, when enabled: one downtown tile, never the metro. Do not run CARLA,
Unreal Editor, and SUMO-GUI at once.

## Programmatic lanes

Chicago already runs **Kennedy Expressway REVLAC** (inbound ~23:00→12:30
weekdays; Friday flip 13:30). The twin adds a proposed **I-88 AV/bus spine**
and an **Ogden peak travel lane** (marked `fictional`). Arterials cap at
**45 mph**. Tachet et al. *PLOS ONE* 2016 and Dresner & Stone AIM: the gain is
*not stopping*, not a 90 mph downtown.

Paid probes (INRIX / StreetLight) stay FHWA-shaped diurnal + Traffic Tracker
until a civic license exists. We do not scrape Google Maps.

## API

| Path | What |
| --- | --- |
| `GET /` | Ops map |
| `GET /twin` | Clock, tidal lanes, corridor vph, districts |
| `GET /lanes` | Kennedy / I-88 / Ogden direction |
| `GET /region` | GeoJSON overlays |
| `GET /catalog` | Open vs paid datasets |
| `GET /lights` | Naperville poles + Chicago spacing model |
| `GET /playbook` | Solarpunk interventions |
| `WS /ws` | Live micro-ring vehicles (SUMO TraCI or mock) + twin clock |
