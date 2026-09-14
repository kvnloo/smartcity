# Architecture — Chicagoland digital twin

This is a **nested city operating system**, not a single simulator. The 3080 Ti
(10 GB) and 10900K cannot draw or tick every vehicle from Waukegan to Joliet.
Weather models solved this decades ago: coarse grid everywhere, fine grid at
the camera. We copy that.

## Nested fidelity (the only performance pattern that matters)

| Ring | Radius | Tick | Engine | What you see |
| --- | --- | --- | --- | --- |
| **hero** | 1.5 km | 1/60 s | Unreal Nanite + Blender mesh | AAA street, characters, slot pads |
| **micro** | 8 km | 0.25 s | Eclipse SUMO + TraCI + AIM/BATCH pads | Naperville + I-88 ramps, every car |
| **meso** | 40 km | 1 s | SUMO meso / cell-transmission | Expressway density, not liveries |
| **macro** | 120 km | 5 s | District OD + LODES + GTFS | Ribbon flows Loop ↔ suburbs |

Unreal never simulates Gary. SUMO never shaders a brick. FastAPI never
integrates chassis physics. Crossing those lines is how this dies on 10 GB.

## Do not write these

| Temptation | Use instead |
| --- | --- |
| Custom car-following | [Eclipse SUMO](https://github.com/eclipse-sumo/sumo) (EPL, very active) |
| Custom OSM graph cutter | [OSMnx](https://github.com/gboeing/osmnx) |
| Building scraper | [Overture Maps](https://docs.overturemaps.org/getting-data/) + DuckDB |
| Photogrammetry scrape | Official Map Tiles API + [Blosm](https://github.com/vvoovv/blosm) or Cesium |
| Chicagoland activity model | Argonne [POLARIS](https://polaris.taps.anl.gov/polaris/index.html) — collaborate |
| Arterial road-diet sandbox | [A/B Street](https://github.com/a-b-street/abstreet) |
| Transit router | OpenTripPlanner / GTFS libraries |
| 400k `AActor` cars | Unreal **Mass Entity** / Niagara ribbons for meso, skeletal meshes only inside ~80 m |

CARLA is a driving-school, not a metro. Cities: Skylines is a toy demand model.
GTA streaming is the camera pattern we want; Rockstar's traffic AI is not.

## Programmatic lanes

Chicago already runs this: **Kennedy Expressway REVLAC** (reversible express
lanes). Travel Midwest: inbound ~23:00 → 12:30 weekdays; Friday outbound starts
13:30. Weekends often idle.

Solarpunk additions (simulated, marked `fictional` in the API):

1. **I-88 programmable AV/bus spine** — one extra lane inbound 05:00–10:00,
   outbound 15:00–19:00 by flipping the same operator. Peak direction gets
   ~+22% capacity per extra lane; the reverse loses ~12%.
2. **Ogden Avenue peak travel lane** — parking lane becomes movement
   06:30–09:30 inbound (Madrid / Sydney pattern on an arterial).
3. **Slot intersections in the micro ring** — Tachet BATCH / Dresner AIM so
   the Naperville grid stops storing delay at reds. Arterials still cap at
   **45 mph**; the paper result is *not stopping*, not a 90 mph downtown.

Tidal lanes move congestion; they do not delete demand. The macro layer still
needs Metra BNSF (one train ≈ 800–1,600 highway seats) or I-88 stays a parking
lot at 07:40 no matter how clever the zipper is.

## Data: open vs paid

Machine-readable catalog: `data/catalog/datasets.json`. Ingest samples:

```bash
python3 scripts/ingest_open_data.py
```

**Open, use these.** OSM / Geofabrik Illinois PBF (speed limits, lanes,
signals). Overture buildings. USGS 3DEP. Chicago SODA (Traffic Tracker,
crashes, zoning). Naperville ArcGIS streetlights. CTA / Metra / Pace GTFS.
Census LODES + TIGER. NOAA. IDOT AADT. CMAP land use. DuPage GIS.

**Paid / gated — approximate, do not scrape.**

| Product | What it is | Stand-in |
| --- | --- | --- |
| INRIX / HERE / TomTom | Probe speeds | Traffic Tracker + OSM `maxspeed` + FHWA-shaped diurnal (`smartcity.twin.demand`) |
| StreetLight / Replica | Origin–destination | LODES + Metra boardings + AADT (`commute_od`) |
| Google Photorealistic 3D Tiles | Textured mesh | Metered API, **hero ring only** |
| Chicago street-light GIS | ~250k poles | 311 outages + spacing model; Naperville poles are actually open |
| POLARIS full scenario | Regional ABM | Our macro OD until a research agreement |

The diurnal is a two-hump Gaussian (AM 07:45, PM 17:15). It is not INRIX. It
is enough to drive zipper timing and spawn rates until a civic license exists.

## Hardware budget (3080 Ti 10 GB)

| Budget | MB |
| --- | --- |
| OS + Unreal editor overhead | ~2500 |
| Nanite hero (Naperville downtown) | ~2000 |
| Lumen software GI | ~1500 |
| Virtual textures / trim | ~1200 |
| Cesium terrain + OSM buildings (hero+micro) | ~1000 |
| Headroom / driver | ~1800 |

Rules: 1080p or 1440p with DLSS Quality. **No Lumen Hardware RT** on this card
for a city. Virtual Shadow Maps low or off. World Partition streaming 2 km.
Google 3D Tiles: downtown tile only, never the metro. Do not run CARLA, Unreal
Editor, and SUMO-GUI at once.

Python micro (this repo) is cheap: slot pads + 400 vehicles on Naperville OSM.
SUMO micro for the 8 km ring is the 10900K job (10 threads). Meso for I-88 is
a few thousand cells.

## Authoring pipeline

```
Geofabrik / Overpass / Overture
        │
        ▼
   Blender (extrude, lookdev, solarpunk materials)
        │ glTF / Datasmith
        ▼
   Unreal World Partition  ← Cesium terrain
        ▲
        │ TraCI / UDP
   SUMO micro/meso  ← FastAPI slot clock + tidal lanes
        ▲
        │
   Macro OD (LODES proxy) + GTFS
```

Generate **geometry** in Blender. Simulate **easy kinematics** there only for
cinematics. Complex traffic, zipper lanes, and region demand live in SUMO +
this backend. Unreal is the renderer and the hero-ring pawn.

Details: `unreal/PIPELINE.md`. SUMO adapter: `python3 scripts/build_sumo_net.py`.

## Solarpunk rules of taste

The future city is **this geology**, not a glass torus. Limestone, copper,
canopy, warm lanterns, retired signal heads as planters. Zoning remap:
`RS`→dwell, `POS`→grow, `M`→make, rights-of-way→move
(`smartcity.twin.zoning`). Street lights occupancy-dim after 01:00 except
emergency corridors. I-88's extra lane is painted as a **bioswale + AV track**,
not a twelfth lane of asphalt.
