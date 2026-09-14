# SmartCity — Naperville slot network

City-scale runtime for a traffic-light-free Naperville: OpenStreetMap extract, the slot / AIM algorithms from the papers, a live operations map, a cinematic Next.js intersection, and Blender scripts that mesh the city.

Vehicles request a time slot, bleed speed on the approach, and cross without a red phase. Emergency, transit, delivery, and pedestrian pulses ride the same reservation fabric — which is how the operations roster shrinks.

The 90–120 mph figure people remember from the viral clips is a popular reading of an AV-only city, not a posted limit in the papers. This runtime caps arterials at **45 mph**. The papers’ result is **not stopping**, and roughly **double** intersection capacity versus fixed lights.

## What’s in the repo

| Piece | What it is |
| --- | --- |
| `smartcity/` | Python city OS: FAIR, BATCH, AIM, lights baseline, services, FastAPI |
| `web/` | Live Naperville map (MapLibre) talking to the runtime |
| `src/` | Next.js cinematic two-world intersection (slot weave vs lights) |
| `blender_scripts/` | OSM → tiled `.blend` builder + RT research loop |
| `data/processed/city.json` | Local-metre Naperville extract (UTM 16N) |

Papers: Tachet et al., *PLOS ONE* 2016 ([doi](https://doi.org/10.1371/journal.pone.0149607)); Dresner & Stone, *JAIR* 2008; [MIT News](https://news.mit.edu/2016/no-traffic-lights-communicating-vehicles-intersections-more-efficiently-0317).

## Run the Naperville city OS

```bash
python3 -m pip install -e ".[dev]"
smartcity serve --host 127.0.0.1 --port 43147
```

Open `http://127.0.0.1:43147`. Switch FAIR / BATCH / AIM / lights from the panel.

```bash
smartcity bench --seconds 25
pytest -q
```

## Cinematic intersection (Next.js)

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:43217`.

## How the Blender city is built (not a Google Maps scrape)

We are **not** pulling Google Maps into Blender. Scraping Maps / Street View tiles into a mesh is against Google’s terms.

**What runs today**

1. `scripts/fetch_naperville.py` downloads **OpenStreetMap** (Overpass): roads, building footprints, parks, water, signal heads, city boundary.
2. `scripts/process_city.py` projects that to metres (UTM 16N) → `data/processed/city.json`.
3. `blender_scripts/build_city.py` **extrudes** those 2D footprints into boxes and road strips, then tiles/joins meshes so EEVEE stays real-time.

That is why the `.blend` looks schematic (prisms on a ground plane), and why many houses are missing: OSM building coverage in Naperville is incomplete. It is also why slot pads line up with the traffic graph — both come from the same OSM ways.

**The real Google path: Photorealistic 3D Tiles + Blosm**

The project that reconstructs *textured* Google cities in Blender is **[Blosm](https://github.com/vvoovv/blosm/wiki/Import-of-Google-3D-Cities)** talking to the official [Map Tiles API](https://developers.google.com/maps/documentation/tile/3d-tiles). You need a billing-enabled, unrestricted API key. Blosm warns: start at ~1×1 km; a few km² at high LOD is millions of triangles.

```bash
export GOOGLE_MAPS_API_KEY=your_key   # Maps Tiles API enabled
python3 scripts/build_blender.py --source google --extent downtown --lod lod3
```

`--extent city` walks the OSM bbox in ~1 km tiles. High LOD (`lod5`) plus the whole city will hammer quota and the viewport.

Until a key is set, use the OSM extrusion path:

```bash
python3 scripts/fetch_naperville.py
python3 scripts/process_city.py
python3 scripts/build_blender.py --source osm --preset tiled_500
python3 scripts/research_loop.py
```

The research loop scores object count, triangles, and depsgraph time, then copies the winner to `output/blends/naperville_city.blend`.
