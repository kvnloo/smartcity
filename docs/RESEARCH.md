# Research ingest — Chicagoland Twin Research share

Source: [ChatGPT scheduled task](https://chatgpt.com/s/t_6aaa00205bf8819195d165eccf7f500f)
(`t_6aaa00205bf8819195d165eccf7f500f`, 2026-09-16). Title: **Chicagoland Twin
Research**. Machine-readable locks: `smartcity.twin.research`.

The share **could not open `kvnloo/smartcity`** (GitHub 404). It also must not
use GitHub Pages as a stand-in for the sim. This file grounds that loop in
*this* tree.

## What we keep (already locked here)

| Role | This repo | Share temptation |
| --- | --- | --- |
| Hero camera | **Unreal 5.4+** Nanite, Lumen software | CesiumJS / deck.gl as the product |
| Phone camera | MapLibre lookdev in `site/` | Photoreal Cesium on the 3080 Ti during CUDA |
| Micro 8 km | **Eclipse SUMO** + TraCI + AIM/BATCH | MOSS as the default brain |
| Meso 40 km | SUMO meso / CTM | One GPU micro for the whole metro |
| Macro 120 km | LODES + GTFS + tidal clock | Invent OD matrices |
| Zipper | Kennedy real; I-88 / Ogden `fictional` | LLM intersection arbiter (LISA) |
| Live poses | `docs/LIVE_CONTRACT.md` WebSocket `/ws` | UDP in v1 |

Do not swap SUMO for MOSS because a 4090 paper reported 2.46 M vehicles.
Do not put an LLM in a 50–100 Hz safety-critical trajectory loop.
CARLA does **not** run Chicagoland; it may later microscope a few hundred metres.

## What the share actually changed

Two kernels, not one adaptive god-sim:

```
observations (Traffic Tracker, AADT, GTFS-RT, CMAP)
        │
        ▼
 JAX differentiable twin     ← candidate calibrator / nowcast / policy search
 (Chicago Sketch paper)         Makinoshima et al. 2026
        │ candidate policy
        ▼
 SUMO (default) or MOSS (candidate)   ← “does this still work in the ugly details?”
        │
        ▼
 experiment store (Parquet) → Unreal hero / MapLibre lookdev
```

The differentiable kernel answers **what should we change?**
The microscopic kernel answers **does that survive IDM, lanes, and zippers?**

That matches nested fidelity. It does **not** replace Unreal or Pages.

### Chicago Sketch numbers (paper, not our bench)

~1,000 nodes, 2,571 links, **1,000,020 vehicles**, >10,000 calibration
parameters. Reported 173× real-time, 30 min of observations calibrated in
455 s, one-hour nowcast in 21 s, control optimization in 728 s.

MOSS headline (different paper/machine): ~2.46 M vehicles, 3,600 sim-seconds
in 37.7 s on **Xeon + RTX 4090 24 GB**. Our envelope is a **3080 Ti / 10 GB**
budget in this repo (FE cards are 12 GB; still not a 4090).

### World model

Canonical join key: **Overture GERS** road id → OSM lanes → IDOT AADT →
Chicago Traffic Tracker speeds → CMAP demand → sim metrics.
Store as **GeoParquet + DuckDB**, already the catalog’s Overture path.
Do not leak SUMO edge ids, OSM way ids, and custom ids through Unreal.

Precompute ActivitySim / CMAP daily plans. Do not run ActivitySim inside the
0.25 s TraCI loop.

POLARIS stays a **licensed planning oracle**, not the OSS runtime.

### Renderer split (VRAM)

Unreal at the camera. Headless sim on the 10900K / optional CUDA. Do not
photoreal-render metro Chicago **and** run a max-size GPU traffic kernel at
once. deck.gl / CesiumJS are optional experiment viewers, not a second hero
engine. Pages stays MapLibre.

## First experiment (workstation, not this cloud VM)

Highest value **before more visual features**, per the share:

1. Chicago Sketch network (same demand the paper used).
2. Populations `100k → 250k → 500k → 1M → 1.5M → 2M`.
3. Identical demand in **SUMO meso** (we can run this), **MOSS** (CUDA, workstation),
   and a **minimal JAX link-based** kernel (CUDA or CPU truncated windows).
4. Record wall-clock, peak VRAM, CPU, vehicle-seconds/sec, count error vs
   held-out Traffic Tracker / AADT, and **calibration error reduction per GPU-minute**.

The decisive number is not FPS.

`python3 scripts/bench_kernels.py` prints the protocol. It does not fake MOSS
throughput on a machine without the binary.

## Hierarchical control (already our slot clock)

```
network optimizer (seconds) → reservation / AIM pads (~100 ms) → vehicle safety
```

Hermes / an LLM may **design** policies and propose experiments. It does not
steer cars. LISA-style LLM intersection arbitration is out.

## Continuous loop

The ChatGPT task is instructed to run daily and attack the architecture.
Once **kvnloo/smartcity** exists and the GitHub connector can see it, point
that loop at `nightly` HEAD instead of a PRD. Until then, ingest shares here.
