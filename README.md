# SmartCity — Chicagoland digital twin

A nested operating picture for **greater Chicagoland**, with Naperville as the
hero street. Weather-model rings (not one giant microsim): Unreal or Unity +
Blender at 1.5 km, Eclipse SUMO + slot/AIM pads at 8 km, expressway meso to 40 km,
district OD out to the lake.

This repository is onboarded to **[Verified OSS Loop](https://github.com/kvnloo/verified-oss-loop)**
(`rolling`: `preview` → `nightly` → gated `dev`/`main`). Workers never merge
`main` or `dev`. See `AGENTS.md`, `CONTRIBUTING.md`, and `.verified-oss-loop/`.

The 3080 Ti (10 GB) and 10900K are the workstation target. Full-metro
car-following will not fit. Nested fidelity will.

## GitHub Pages lookdev (mobile)

The page on **`nightly`** is a **photoreal camera**, not the sim. Esri/Maxar
imagery, Sentinel-2 underlay, OSM extruded masses, Terrarium DEM, device LOD.
A Galaxy S25 Ultra (`SM-S938`) gets ultra LOD. Phones on Save-Data or 2 GB skip
3D. WebGL-less browsers fall back to an Esri mosaic.

| Channel | Role |
| --- | --- |
| `preview` | feature integration |
| `nightly` | cutting-edge + Pages deploy |
| `dev` / `main` | human-gated |

After the GitHub repo exists (Create repo → **smartcity** under **kvnloo**) and
Pages is set to GitHub Actions:

**https://kvnloo.github.io/smartcity/**

Until then, run the lookdev locally:

```bash
cd site
npm ci
npm test          # TDD: LOD, camera, HUD, tiles, style
npm run dev       # http://127.0.0.1:43180
```

Or `npm run build && npm run preview`.

## Nested rings

| Ring | Engine | Radius | Tick |
| --- | --- | --- | --- |
| hero | Unreal or Unity + Blender mesh | 1.5 km | 1/60 s |
| micro | SUMO + BATCH/AIM pads (this repo) | 8 km | 0.25 s |
| meso | SUMO meso / cell-transmission | 40 km | 1 s |
| macro | LODES proxy + GTFS + tidal clock | 120 km | 5 s |

## Programmatic lanes

Chicago already runs **Kennedy Expressway REVLAC** (inbound ~23:00→12:30
weekdays; Friday flip 13:30). The twin adds a proposed **I-88 AV/bus spine**
and an **Ogden peak travel lane**. Paid probe feeds (INRIX / HERE / StreetLight)
are a FHWA-shaped diurnal + Traffic Tracker until a license exists.

## Verify (TDD gate)

```bash
./.verified-oss-loop/verify.sh
```

That is pytest plus the lookdev Vitest suite and production build. CI
(`.github/workflows/verified-oss-loop.yml`) runs the same and publishes
`site/dist` from `nightly`.

## Run the ops map

```bash
python3 -m pip install -e ".[dev]"
python3 scripts/ingest_open_data.py   # optional: refresh SODA / NOAA / poles
smartcity serve --host 127.0.0.1 --port 43147
```

Open `http://127.0.0.1:43147`. Toggle **Naperville streets** / **Metro
corridors**. Restart at dawn, rush, Kennedy flip, or night.

```bash
smartcity twin --hour 7.5
smartcity bench --seconds 25
pytest -q
python3 scripts/build_sumo_net.py     # nod/edg XML; netconvert if SUMO is installed
```

## Cinematic intersection (Next.js)

Hero-ring look at one slot weave vs lights:

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:43217`.

## Data

Catalog (open vs paid, with stand-ins): `data/catalog/datasets.json` and
`GET /catalog`. Notes: [docs/DATA.md](docs/DATA.md).

We do **not** scrape Google Maps. OSM + Overture build the graph and
footprints. Photorealistic 3D Tiles are an official, metered API for the
**hero ring only** (`unreal/PIPELINE.md`). The Pages site uses Esri World
Imagery + Sentinel-2, which are streamable and ToS-legal for this lookdev.

## Blender city mesh

```bash
python3 scripts/fetch_naperville.py
python3 scripts/process_city.py
python3 scripts/build_blender.py --source osm --preset tiled_500
```

Optional Google 3D Tiles via Blosm (billing key, downtown tile):

```bash
export GOOGLE_MAPS_API_KEY=your_key
python3 scripts/build_blender.py --source google --extent downtown --lod lod3
```

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
| `WS /ws` | Live Naperville vehicles + twin clock |

Papers: Tachet et al., *PLOS ONE* 2016
([doi](https://doi.org/10.1371/journal.pone.0149607)); Dresner & Stone, *JAIR*
2008; [MIT News](https://news.mit.edu/2016/no-traffic-lights-communicating-vehicles-intersections-more-efficiently-0317).
