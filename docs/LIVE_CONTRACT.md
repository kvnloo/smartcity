# Live contract — Unreal ↔ FastAPI

This is the **frozen JSON Unreal speaks**. Hero street: zipper state + a few
hundred cars. Field names below are the API. Schema files are the types.
Do not guess; do not invent a parallel Unity feed; do not stream Google 3D Tiles
on this socket.

| This | Not this |
| --- | --- |
| `GET /twin`, `GET /lanes`, `WS /ws` from `smartcity serve` | `site/public/twin.json` (GitHub Pages lookdev) |
| Unreal 5.4+ Nanite hero | Unity |
| OSM / Blender glTF at the mesh origin | Google Photorealistic 3D Tiles |
| Metres, mph, vph | Unreal default centimetres (scale them) |

Contract id: **`live-contract-v1`**. Producers (`smartcity.twin.contract`) forbid extra keys. Unreal should still **ignore unknown keys** so a later additive field does not crash the editor.

Run the twin:

```bash
python3 -m pip install -e ".[dev]"
smartcity serve --host 127.0.0.1 --port 43147
python3 scripts/unreal_bridge_stub.py            # one /twin snapshot, no server
python3 scripts/unreal_bridge_stub.py --url http://127.0.0.1:43147/twin
```

Canonical 07:30 Monday payloads: `tests/fixtures/twin_0730_monday.json` and
`tests/fixtures/lanes_0730_monday.json`. JSON Schema (no Python): `docs/schema/`.
OpenAPI when the server is up: `http://127.0.0.1:43147/openapi.json`.

## Endpoints Unreal implements against

| Method | Path | Pydantic / schema | Cadence | What to bind |
| --- | --- | --- | --- | --- |
| `GET` | `/twin` | `TwinSnapshot` · `docs/schema/twin.schema.json` | 1 Hz is enough | Clock, zipper (`lanes`), ring radii, origin, corridor TTI/vph |
| `GET` | `/lanes` | `LaneClockSnapshot` · `docs/schema/lanes.schema.json` | 1 Hz, or skip if you already parse `twin.lanes` | Same zipper rows + `minutes` from midnight |
| `WS` | `/ws` | `WsSnapshot` · `docs/schema/ws_snapshot.schema.json` | ~8 Hz (120 ms) | `vehicles[]` poses. Nested `twin` repeats zipper. |
| `GET` | `/snapshot` | same as one `/ws` frame | HTTP fallback | Same object if you have not wired WebSocket yet |
| `GET` | `/city` | not the tick schema | once at boot | `origin_lonlat`, `origin_utm`, `crs`, `bbox_m` (metres) |

Every `/ws` frame is a `WsSnapshot`. There are no other message types. The client sends nothing; the server pushes.

Default spawn cap is **420** vehicles (`target_vehicles`). That is the “few hundred cars.” `corridors[].inbound_vph` is an hourly **flow rate**, not a mesh count.

## Units

| Quantity | Field(s) | Unit |
| --- | --- | --- |
| Local pose | `x_m`, `y_m`, `bbox_m`, `origin.utm_*` | **metre** (SI). +X east, +Y north, +Z up |
| Ring radius | `fidelity[].radius_m` | metre |
| Ring radius | `fidelity[].radius_km` | kilometre (same radius) |
| Corridor length | `corridors[].km` | kilometre |
| Speed | `speed_mph`, `mean_speed_mph` | **mph** (miles per hour), not m/s |
| Flow | `inbound_vph`, `outbound_vph` | **vph** (vehicles per hour) |
| Travel time | `corridors[].minutes` | minutes of travel, **not** clock minutes |
| Clock minutes | `lanes.minutes` | minutes from midnight, 0…1439 |
| Heading | `vehicles[].heading` | degrees from +X (east) toward +Y (north), counter-clockwise. 0 = east, 90 = north |
| Clock | `clock` | `HH:MM` 24h civil time for the twin (naive, not UTC) |
| Sim time | `t` | seconds since `/sim/start`. Internal `dt` = 0.25 s |
| TTI | `tti` | dimensionless, free-flow / current |
| Multipliers | `inbound_mult`, `outbound_mult` | dimensionless capacity |

Compass heading (0 = north, clockwise) = `(90 - heading) mod 360`.

Default Unreal world units are **centimetres**. `origin.unreal_uu_per_metre` is `100`. Spawn with `FVector(x_m * 100, y_m * 100, z_m * 100)` unless World Settings are metres (then use `1`). glTF from Blender is exported in metres; the importer must use the same scale as these poses.

## Origin

Two different points exist. Mixing them is the usual alignment bug.

| Name | Where | WGS84 | Role |
| --- | --- | --- | --- |
| **Mesh origin** | `twin.origin.lon/lat` and `GET /city` `origin_lonlat` | **-88.106604, 41.75421** | Local metres, SUMO edges, Unreal World Partition, `/ws` `x_m`/`y_m` |
| **Ring centre** | `twin.origin.ring_center_lon/lat` | **-88.147, 41.75** | Downtown Naperville. Fidelity rings and the Pages camera |

Mesh CRS is **EPSG:32616** (UTM zone 16N).

```
easting  = origin.utm_e + x_m
northing = origin.utm_n + y_m
```

`origin.utm_e` = `408001.19`, `origin.utm_n` = `4623078.76` (must match `data/processed/city.json` `meta.origin_utm`).

`site/public/twin.json` `"origin": [-88.147, 41.75]` is the **ring centre**, not the mesh origin. Unreal must not use the Pages file.

## Nested rings

Radii are measured from the ring centre (downtown), not from the mesh origin.

| `fidelity[].name` | `radius_km` | `radius_m` | `tick_s` | Engine | Unreal |
| --- | --- | --- | --- | --- | --- |
| `hero` | 1.5 | 1500 | 1/60 | `unreal_nanite + blender_mesh` | Nanite street, skeletal cars, zipper splines |
| `micro` | 8 | 8000 | 0.25 | `sumo + slot AIM` | Impostors / culled poses from `/ws` |
| `meso` | 40 | 40000 | 1 | `sumo meso / CTM` | Niagara / Mass ribbons from `tti`, not liveries |
| `macro` | 120 | 120000 | 5 | `od_flow` | HUD / corridor polylines |

Unreal never simulates Gary. Do not spawn `inbound_vph` actors on I-88.

## Zipper / tidal lanes

Bind barrier splines to `twin.lanes[]` (same objects as `GET /lanes` `facilities[]`). Snap the spline when `direction` or `extra_lanes` changes. Do not rebuild the highway mesh.

| `id` | `fictional` | `kind` | Extra lanes (weekday) | Weekday inbound window | What it is |
| --- | --- | --- | --- | --- | --- |
| `kennedy-revlac` | **`false`** (IDOT / real) | `expressway` | 2 | 23:00 → 12:30; Friday inbound until 13:30 | Kennedy Expressway REVLAC |
| `i88-solarpunk` | **`true`** (proposal) | `expressway` | 1 | 05:00 → 10:00 | I-88 programmable AV/bus spine |
| `ogden-tidal` | **`true`** (proposal) | `arterial` | 1 | 06:30 → 09:30 | Ogden Avenue peak travel lane |

On **weekend** (`weekend: true`) every facility reports `extra_lanes: 0` and multipliers `1.0` / `1.0` (REVLAC idle).

`direction` is `"inbound"` or `"outbound"`. Inbound means extra capacity points toward the named core (Loop / Chicago). Peak direction gets `1 + 0.22 * extra_lanes`; the reverse gets `max(0.62, 1 - 0.12 * extra_lanes)`.

Corridor `i90` has `"tidal": "kennedy"` (I-90 Kennedy). Corridor `ogden` has `"tidal": "ogden"`. Corridor **`i88` has `"tidal": null`** — the I-88 zipper is still `lanes` id `i88-solarpunk`. Always drive Unreal zippers from `lanes` / `facilities`, not from `corridors[].tidal`.

Paint I-88 extra lane as bioswale + AV chevrons, not more asphalt. Arterials stay capped at 45 mph; that cap is the sim, not a JSON field.

## `GET /twin` example (07:30 Monday)

Full golden file: `tests/fixtures/twin_0730_monday.json`.

```json
{
  "clock": "07:30",
  "weekday_name": "Mon",
  "weekend": false,
  "origin": {
    "crs": "EPSG:32616",
    "lon": -88.106604,
    "lat": 41.75421,
    "utm_e": 408001.19,
    "utm_n": 4623078.76,
    "ring_center_lon": -88.147,
    "ring_center_lat": 41.75,
    "x_axis": "east",
    "y_axis": "north",
    "z_axis": "up",
    "units": "metre",
    "unreal_uu_per_metre": 100.0
  },
  "lanes": [
    {
      "id": "kennedy-revlac",
      "name": "Kennedy Expressway reversible express lanes",
      "kind": "expressway",
      "direction": "inbound",
      "extra_lanes": 2,
      "fictional": false,
      "inbound_mult": 1.44,
      "outbound_mult": 0.76
    },
    {
      "id": "i88-solarpunk",
      "name": "I-88 programmable AV/bus spine",
      "kind": "expressway",
      "direction": "inbound",
      "extra_lanes": 1,
      "fictional": true,
      "inbound_mult": 1.22,
      "outbound_mult": 0.88
    },
    {
      "id": "ogden-tidal",
      "name": "Ogden Avenue peak travel lane",
      "kind": "arterial",
      "direction": "inbound",
      "extra_lanes": 1,
      "fictional": true,
      "inbound_mult": 1.22,
      "outbound_mult": 0.88
    }
  ],
  "corridors": [
    {
      "id": "i88",
      "name": "I-88 Reagan",
      "from": "naperville",
      "to": "loop",
      "mode": "road",
      "km": 45,
      "speed_mph": 29.7,
      "tti": 1.85,
      "inbound_vph": 16408,
      "outbound_vph": 1830,
      "minutes": 56.4,
      "tidal": null
    }
  ],
  "fidelity": [
    {
      "name": "hero",
      "engine": "unreal_nanite + blender_mesh",
      "radius_km": 1.5,
      "radius_m": 1500.0,
      "tick_s": 0.016666666666666666,
      "notes": "AAA street, Lumen, characters. ~2 km²."
    }
  ]
}
```

`districts[]` and `od[]` are in the golden file. JSON key `from` is the origin district id (reserved word in some languages — map it to `FromDistrict`).

`weekday_name` is `Mon`…`Sun`. `weekend` is Saturday/Sunday.

## `GET /lanes` example (07:30 Monday)

Same zipper rows as `twin.lanes`, plus clock math:

```json
{
  "clock": "07:30",
  "minutes": 450,
  "weekday": 0,
  "weekday_name": "Mon",
  "weekend": false,
  "facilities": [
    {
      "id": "kennedy-revlac",
      "name": "Kennedy Expressway reversible express lanes",
      "kind": "expressway",
      "direction": "inbound",
      "extra_lanes": 2,
      "fictional": false,
      "inbound_mult": 1.44,
      "outbound_mult": 0.76
    },
    {
      "id": "i88-solarpunk",
      "name": "I-88 programmable AV/bus spine",
      "kind": "expressway",
      "direction": "inbound",
      "extra_lanes": 1,
      "fictional": true,
      "inbound_mult": 1.22,
      "outbound_mult": 0.88
    },
    {
      "id": "ogden-tidal",
      "name": "Ogden Avenue peak travel lane",
      "kind": "arterial",
      "direction": "inbound",
      "extra_lanes": 1,
      "fictional": true,
      "inbound_mult": 1.22,
      "outbound_mult": 0.88
    }
  ]
}
```

`weekday` is `0=Monday` … `6=Sunday`. Golden file: `tests/fixtures/lanes_0730_monday.json`.

## `WS /ws` example (one frame, truncated)

`GET /snapshot` returns the same shape. `type` is always `"snapshot"`.

```json
{
  "type": "snapshot",
  "t": 10.0,
  "policy": "batch",
  "vehicles": [
    {
      "id": 1,
      "kind": "car",
      "lon": -88.103858,
      "lat": 41.756298,
      "x_m": 231.26,
      "y_m": 228.82,
      "speed_mph": 25.2,
      "heading": 90.9
    },
    {
      "id": 2,
      "kind": "bus",
      "lon": -88.099926,
      "lat": 41.739586,
      "x_m": 534.45,
      "y_m": -1630.88,
      "speed_mph": 24.9,
      "heading": 171.2
    }
  ],
  "intersections": [
    {
      "id": "x585_-683",
      "lon": -88.095896,
      "lat": 41.74508,
      "x_m": 877.33,
      "y_m": -1025.12,
      "had_signals": false,
      "degree": 4,
      "pending": 0,
      "grants": 0
    }
  ],
  "metrics": {
    "active": 68,
    "spawned": 68,
    "completed": 0,
    "mean_speed_mph": 24.1,
    "delay_s": 12.0,
    "stops": 0,
    "energy": 40.0,
    "grants": 20,
    "mean_delay_s": 0.0
  },
  "services": {
    "buses": 0,
    "emergencies": 0,
    "deliveries": 0,
    "events": []
  },
  "twin": { }
}
```

`kind` is `car` | `bus` | `emergency` | `delivery`. `policy` is `lights` | `fair` | `batch` | `aim`. Nested `twin` is a full `TwinSnapshot` (origin + zipper + rings). `metrics.active` is the live car count.

`intersections[]` is hundreds of slot pads (graph nodes). Do **not** spawn an `AActor` per pad. Use pads inside ~80–120 m of the camera, or ignore them and only draw `/ws` vehicles.

`labor` and `services` are ops-map HUD. Unreal may ignore them.

## UDP vs WebSocket on a 3080 Ti editor

The editor already spends ~2.5 GB before the city. Hero traffic is **a few hundred** skeletal meshes, culled at 80–120 m. That budget does not need a custom UDP plugin.

**Use WebSocket `/ws` for cars.** Localhost JSON at ~8 Hz for ≤ ~500 poses is tens of KB per frame. Parse off the game thread. Interpolate on the game thread toward `x_m`/`y_m` (hero visual tick is 1/60 s; the sim tick is 0.25 s; the socket is 8 Hz).

**Use HTTP `GET /twin` or `GET /lanes` at 1 Hz for zipper state** (or read `twin.lanes` from the same WS frame). Zipper flips on the civil clock, not at 8 Hz. A dropped UDP datagram on a reverse would leave the barrier on the wrong side of I-90. Zipper must stay TCP/WebSocket.

**Do not implement UDP for this contract.** UDP is reserved for a later SUMO TraCI binary pose stream when the 8 km micro ring has thousands of vehicles. Even then, zipper stays on `/twin` / `/ws`. There is no UDP packet format in v1.

Practical editor setup (10 GB VRAM): 1080p or 1440p DLSS Quality, Lumen **software** GI, no Hardware RT, World Partition ~256 m cells, hero 1.5 km + 8 km impostors. Do not run CARLA + Unreal Editor + SUMO-GUI at once.

## Unreal subsystem recipe

1. Boot: `GET /city` once if you need road GeoJSON; otherwise `GET /twin` is enough for origin + rings + zipper.
2. Set the georeference / World Partition origin to `origin.lon/lat` (mesh origin), CRS EPSG:32616. Place downtown cinematic cameras near `ring_center_*`.
3. Spawn at most a few hundred vehicle pawns. Pool them. Cull at 80–120 m. `kind` selects the livery.
4. Connect `ws://127.0.0.1:43147/ws`. On each `type=snapshot` frame, update pooled pawns by `vehicles[].id` using `x_m`, `y_m`, `heading` (yaw = heading if X=east, Y=north, Z=up).
5. Each time `twin.lanes[]` `direction` or `extra_lanes` changes, move the matching barrier spline. `kennedy-revlac` is real IDOT REVLAC; `i88-solarpunk` and `ogden-tidal` are proposed (`fictional: true`).
6. Color meso ribbons from `corridors[].tti`. Never spawn `inbound_vph` meshes.
7. Do not read `site/public/twin.json`. Do not pull Google tiles on this bus.

## Existing consumers (do not break)

The **ops map** (`web/app.js`) still reads `/city` (`origin_lonlat`, `roads`), `/region`, `/ws` (`vehicles.lon/lat`, `metrics`, `twin.lanes`, `twin.corridors`, `twin.fidelity`). Additive fields (`origin`, `x_m`, `radius_m`, `type`) are ignored there.

**Pages lookdev** (`site/public/twin.json`) stays a baked HUD overlay: `clock`, `lanes` (including `fictional`), `corridors`, `fidelity[].radius_km`, camera `origin` as downtown `[lon, lat]`. It is not a `/ws` stand-in.

## Regenerating schema

```bash
python3 -c "from smartcity.twin.contract import write_json_schemas; write_json_schemas()"
python3 -m pytest -q tests/test_live_contract.py
```
