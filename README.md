# SmartCity — Chicagoland digital twin

A nested operating picture for **greater Chicagoland**, with Naperville as the
hero street. Weather-model rings (not one giant microsim): Unreal + Blender at
1.5 km, Eclipse SUMO + slot/AIM pads at 8 km, expressway meso to 40 km,
district OD out to the lake.

The 3080 Ti (10 GB) and 10900K are the target. Full-metro car-following will
not fit. Nested fidelity will.

This is also a **solarpunk** sketch of the same geology: limestone and copper,
canopy over asphalt, Kennedy-style zipper lanes on I-88, retired signal heads
as planters. Arterials still cap at **45 mph**. The papers’ result is *not
stopping*, not a 90 mph downtown.

Read **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** before writing a new
engine. The short version: never reinvent SUMO, Overture, Cesium, OSMnx, or
Argonne POLARIS.

## Nested rings

| Ring | Engine | Radius | Tick |
| --- | --- | --- | --- |
| hero | Unreal Nanite + Blender mesh | 1.5 km | 1/60 s |
| micro | SUMO + BATCH/AIM pads (this repo) | 8 km | 0.25 s |
| meso | SUMO meso / cell-transmission | 40 km | 1 s |
| macro | LODES proxy + GTFS + tidal clock | 120 km | 5 s |

## Programmatic lanes

Chicago already runs **Kennedy Expressway REVLAC** (inbound ~23:00→12:30
weekdays; Friday flip 13:30). The twin adds a proposed **I-88 AV/bus spine**
and an **Ogden peak travel lane**. Paid probe feeds (INRIX / HERE / StreetLight)
are a FHWA-shaped diurnal + Traffic Tracker until a license exists.

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
**hero ring only** (`unreal/PIPELINE.md`).

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
