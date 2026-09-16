"""Ground the 2026-09-16 Chicagoland Twin Research share against this repo.

The ChatGPT scheduled-task share could not see `kvnloo/smartcity` (GitHub 404).
This module is the mapping: keep locked engines, record candidates, refuse
to put an LLM in the safety loop.
"""

from __future__ import annotations

SHARE_URL = "https://chatgpt.com/s/t_6aaa00205bf8819195d165eccf7f500f"
SHARE_TITLE = "Chicagoland Twin Research"
SHARE_DATE = "2026-09-16"

# This tree. Do not swap these because a paper used a 4090.
HERO_RENDERER = "unreal"
LOOKDEV_VIEWER = "maplibre"
MICRO_DEFAULT = "sumo"
MESO_DEFAULT = "sumo_meso"
MACRO_DEFAULT = "od_flow"
SLOT_CLOCK = "fastapi_aim"

# Candidates from the share. Benchmark on the 3080 Ti before any swap.
CALIBRATION_CANDIDATE = "jax_differentiable"
GPU_MICRO_CANDIDATE = "moss"
MICROSCOPE = "carla_or_waymax"
PLANNING_ORACLE = "polaris"
WORLD_STORE = "geoparquet_duckdb_gers"

LLM_IN_SAFETY_LOOP = False
CARLA_RUNS_CHICAGOLAND = False
MOSS_IS_DEFAULT_MICRO = False
CESIUMJS_IS_DEFAULT_LOOKDEV = False

# Makinoshima et al. 2026 Chicago Sketch (share numbers).
CHICAGO_SKETCH = {
    "nodes": 1000,
    "links": 2571,
    "vehicles": 1_000_020,
    "realtime_factor": 173.0,
    "paper": "Makinoshima et al. 2026 differentiable agent-based traffic twin",
}

# Share sometimes said 12 GB. This repo budgets 10 GB as the envelope.
VRAM_BUDGET_GB = 10
MOSS_PUBLISHED_GPU = "RTX 4090 24GB"

KERNEL_ROLES = {
    "unreal": "hero camera, never the traffic engine",
    "sumo": "default micro 8 km + meso 40 km until a 3080 Ti bench says otherwise",
    "jax_differentiable": "candidate calibrator / nowcaster / policy search (Chicago Sketch paper)",
    "moss": "candidate CUDA micro validator, not the brain, not the default",
    "polaris": "licensed regional planning oracle, not the OSS runtime",
    "carla_or_waymax": "hundreds of metres microscope, never metro Chicagoland",
    "maplibre": "GitHub Pages lookdev, not the sim",
}


def architecture_locks() -> dict[str, object]:
    return {
        "hero_renderer": HERO_RENDERER,
        "lookdev_viewer": LOOKDEV_VIEWER,
        "micro_default": MICRO_DEFAULT,
        "meso_default": MESO_DEFAULT,
        "macro_default": MACRO_DEFAULT,
        "slot_clock": SLOT_CLOCK,
        "calibration_candidate": CALIBRATION_CANDIDATE,
        "gpu_micro_candidate": GPU_MICRO_CANDIDATE,
        "microscope": MICROSCOPE,
        "planning_oracle": PLANNING_ORACLE,
        "world_store": WORLD_STORE,
        "llm_in_safety_loop": LLM_IN_SAFETY_LOOP,
        "carla_runs_chicagoland": CARLA_RUNS_CHICAGOLAND,
        "moss_is_default_micro": MOSS_IS_DEFAULT_MICRO,
        "cesiumjs_is_default_lookdev": CESIUMJS_IS_DEFAULT_LOOKDEV,
        "vram_budget_gb": VRAM_BUDGET_GB,
        "share_url": SHARE_URL,
    }


def chicago_sketch_ladder() -> list[int]:
    """Vehicle counts the share wants measured on the 3080 Ti before more visuals."""
    return [100_000, 250_000, 500_000, 1_000_000, 1_500_000, 2_000_000]
