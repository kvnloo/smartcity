# Ideas bible — what this twin is for

This is the unbuilt map. `ROADMAP.md` is the gated list. Agents do not rewrite
that file; they may mint one `needs-discussion` issue from it. This document
is allowed to be greedy.

## One-sentence product

A nested Chicagoland operating picture that looks like an AAA game at the
camera, runs real traffic codes in the rings behind it, and never asks a
Galaxy phone to be a 3080 Ti.

## Why nested (copy weather, not GTA marketing)

Metro car-following is an N-body problem we will not win on 10 GB. Nested
fidelity is the only pattern that has shipped at this scale:

- **Hero 1.5 km** — Unreal Nanite + Blender. Skeletal cars only inside ~80–120 m.
- **Micro 8 km** — SUMO + TraCI + AIM/BATCH pads. Every vehicle, ugly meshes.
- **Meso 40 km** — SUMO meso / cell-transmission. Density, not liveries.
- **Macro 120 km** — LODES proxy + GTFS. Ribbons Loop ↔ suburbs.

Unreal never ticks Gary. SUMO never shaders a brick. Pages never runs TraCI.

## Renderer lock: Unreal, not Unity

Nanite + World Partition + Cesium for Unreal is the 3080 Ti path. Unity HDRP
is a second engine we will not staff. Mass Entity / Niagara for meso ribbons.
A tiny WebSocket subsystem reads `GET /twin` and `/ws`
([docs/LIVE_CONTRACT.md](LIVE_CONTRACT.md)). Do not invent UDP for zipper state.

Do not write a Cesium alternative. Do not write a Mass alternative. Do not
import the 40 km SUMO net as `AActor`s.

## Mesh lock: Blender first, Google later

Default: OSM footprints + `render_height` extrusion, solarpunk materials
(limestone, copper, moss, warm lanterns). Preset `tiled_500` is the 3080 Ti
budget. Export glTF 2.0, metres, origin from `city.json`.

Google Photorealistic 3D Tiles: Enterprise SKU, billed per root tileset, 3 h
session, **ToS forbids cache/offline/ML/bake**. When a key exists, one downtown
tile via Blosm. Never the metro. Never on GitHub Pages.

Until then: Esri/Maxar (lookdev), Sentinel-2 underlay, USGS Terrarium DEM,
OpenFreeMap masses, USGS 3DEP on the workstation.

## Phone lock: lookdev ≠ sim

S25 Ultra has juice for MapLibre terrain + extrusion + a cinematic fly-path.
It does not have Unreal, SUMO, or 400k vehicles. LOD:

| Tier | Who | Loads |
| --- | --- | --- |
| ultra | `SM-S938` or 8 GB / 8 cores | DEM, hillshade, 3D buildings, sky fog, animation |
| medium | 4 GB / 6 cores | buildings, sky, no terrain |
| low | save-data or 2 GB | satellite + HUD only |
| no WebGL | software GL, some VMs | Esri mosaic stills |

MapLibre is dynamically imported. Mosaic devices skip the 800 kB GL chunk.

## Two kernels (research ingest)

A 2026-09-16 research loop ([docs/RESEARCH.md](RESEARCH.md)) argued: do not make
one GPU micro-simulator the brain. Calibrate / nowcast / search policy on a
**differentiable** kernel (JAX, Chicago Sketch paper). Validate ugly
car-following on **SUMO** (default) or **MOSS** (CUDA candidate on the 3080 Ti).
Join observations on **Overture GERS** into GeoParquet + DuckDB. Precompute
CMAP/ActivitySim plans; never tick ActivitySim at 0.25 s.

The loop could not see `kvnloo/smartcity` yet. This tree is the ground truth.

## Traffic ideas we will actually implement

1. **Kennedy REVLAC as a first-class clock** — already real. Expose inbound/outbound, never “invent” Chicago’s zipper.
2. **I-88 AV/bus spine** — proposed, `fictional: true`. Bioswale + chevrons, not asphalt. +22% / −12% capacity flip.
3. **Ogden peak travel lane** — parking becomes movement 06:30–09:30 inbound.
4. **Slot pads at retired signals** — Tachet BATCH reservations; Dresner AIM policy. 45 mph cap.
5. **Metra BNSF as the real capacity add** — one train deletes delay the zipper only moves.
6. **Occupancy-dim canopy LEDs** — Naperville poles are open GIS; Chicago inventory is gated.

Papers: Tachet et al., *PLOS ONE* 2016 ([doi](https://doi.org/10.1371/journal.pone.0149607));
Dresner & Stone, *JAIR* 2008;
[MIT News](https://news.mit.edu/2016/no-traffic-lights-communicating-vehicles-intersections-more-efficiently-0317).

## Data ideas (open first, paid later)

Open: OSM / Geofabrik Illinois, Overture, USGS 3DEP, Chicago SODA, Naperville
ArcGIS lights, CTA/Metra/Pace GTFS, LODES + TIGER, NOAA, IDOT AADT, CMAP,
DuPage GIS.

Stand-ins until licensed: INRIX → diurnal + Traffic Tracker; StreetLight →
LODES OD; Google 3D Tiles → OSM extrusion; POLARIS → our macro OD.

Do not scrape Google Maps. Do not commit Geofabrik PBFs or Overture parquet.

## Solarpunk taste (non-negotiable)

This geology: limestone, copper, canopy, warm lanterns. Retired signal heads
as planters. Zoning paint: `RS` dwell, `POS` grow, `M` make, ROW move.
The future is not a glass torus and not a twelfth lane of I-88.

## What we will not write

| Temptation | Use instead |
| --- | --- |
| Custom car-following | Eclipse SUMO |
| Custom OSM cutter | OSMnx |
| Building scraper | Overture + DuckDB |
| Photogrammetry scrape | Official Map Tiles API + Blosm |
| Chicagoland ABM | Argonne POLARIS (collaborate) |
| Arterial road-diet sandbox | A/B Street |
| Transit router | OTP / GTFS libs |
| 400k `AActor` cars | Mass / Niagara; skeletal only inside ~80 m |
| CARLA as the metro | CARLA is a driving school; microscope later, never Chicagoland |
| Cities: Skylines demand | LODES + GTFS |
| Unity “just in case” | Unreal only |
| MOSS as the default brain | SUMO until a 3080 Ti bench; JAX calibrates, MOSS may validate |
| LLM at 50–100 Hz | Hierarchical AIM / CBF; LLM designs policies, does not steer |

## Hardware envelope

| Budget | MB |
| --- | --- |
| OS + Unreal editor | ~2500 |
| Nanite hero downtown | ~2000 |
| Lumen software GI | ~1500 |
| Virtual textures | ~1200 |
| Cesium + OSM hero | ~1000 |
| Headroom | ~1800 |

Python micro (slot pads + hundreds of vehicles) is cheap. SUMO 8 km is the
10900K job. Meso I-88 is a few thousand cells.

## Authoring pipeline (target)

```
Geofabrik / Overpass / Overture
        │
        ▼
   Blender (extrude, lookdev, solarpunk materials)
        │ glTF / Datasmith
        ▼
   Unreal World Partition  ← Cesium terrain
        ▲
        │ WebSocket /twin + /ws
   SUMO micro/meso  ← FastAPI slot clock + tidal lanes
        ▲
        │
   Macro OD (LODES proxy) + GTFS
```

Pages is a **fork** of that pipeline: baked `site/public/twin.json` + XYZ
rasters. It does not import glTF.

## Live contract Unreal should speak

Frozen in **[docs/LIVE_CONTRACT.md](LIVE_CONTRACT.md)** (schema under `docs/schema/`).

- `GET /twin` — clock, lanes, corridor TTI, districts, rings, origin
- `GET /lanes` — Kennedy / I-88 / Ogden multipliers
- `GET /lights` — poles
- `WS /ws` — vehicle snapshot + clock
- Barrier spline, not net rebuild, when a zipper flips
- Kennedy REVLAC is real (`fictional: false`); I-88 / Ogden are proposed (`true`)

## Verified OSS Loop

Onboarded from [kvnloo/verified-oss-loop](https://github.com/kvnloo/verified-oss-loop)
with `--with-automation --scheme rolling`. Claims expire. Receipts bind
`head_revision`. Mutation is `n/a` (mixed Python + lookdev TS). Preview
automerge and nightly automerge are allowed; `dev`/`main` are human.

## Open questions (do not block)

- Cesium ion token (terrain). Optional; Terrarium DEM already works for lookdev.
- Epic account / source build vs launcher 5.4 vs 5.5 — workstation choice.
- INRIX / StreetLight civic license.
- POLARIS research agreement.
- Google Map Tiles API billing (hero tile only).
- Whether Mass Traffic or a thin custom fragment wins for meso ribbons.
