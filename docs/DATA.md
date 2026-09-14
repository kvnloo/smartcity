# Data catalog

See `data/catalog/datasets.json` (the API also serves `GET /catalog`).

Samples live in `data/open/`. They are **calibration scraps**, not the metro:

| File | Source |
| --- | --- |
| `chicago_traffic_segments.json` | Traffic Tracker current region speeds |
| `chicago_congestion_sample.json` | Historical tracker |
| `chicago_crashes_sample.json` | Vision Zero |
| `chicago_streetlights_out.json` | 311 outages (not the inventory) |
| `chicago_zoning_sample.json` | SODA `nifi-zqag` attributes |
| `naperville_streetlights.geojson` | City ArcGIS poles (paged) |
| `noaa_naperville.json` | weather.gov points + forecast |

Refresh:

```bash
python3 scripts/ingest_open_data.py
```

Do **not** commit Geofabrik PBFs, Overture parquet, or LODES CSVs. Clip those
on the workstation with osmium / DuckDB / `gunzip`, then point the catalog at
the local path.

Google 3D Tiles and Cesium ion keys stay in `.env`. The repo runs without them
using OSM extrusions.
