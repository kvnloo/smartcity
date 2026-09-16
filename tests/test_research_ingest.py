"""The ChatGPT research share must not reverse Unreal / SUMO locks."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from smartcity.twin.research import (
    CALIBRATION_CANDIDATE,
    CARLA_RUNS_CHICAGOLAND,
    CESIUMJS_IS_DEFAULT_LOOKDEV,
    GPU_MICRO_CANDIDATE,
    HERO_RENDERER,
    LLM_IN_SAFETY_LOOP,
    LOOKDEV_VIEWER,
    MICRO_DEFAULT,
    MOSS_IS_DEFAULT_MICRO,
    SHARE_URL,
    architecture_locks,
    chicago_sketch_ladder,
)

ROOT = Path(__file__).resolve().parents[1]


def _read(*rel: str) -> str:
    return "\n".join((ROOT / p).read_text(encoding="utf-8") for p in rel)


def test_locks_keep_unreal_sumo_maplibre():
    locks = architecture_locks()
    assert locks["hero_renderer"] == "unreal"
    assert locks["micro_default"] == "sumo"
    assert locks["lookdev_viewer"] == "maplibre"
    assert locks["llm_in_safety_loop"] is False
    assert locks["moss_is_default_micro"] is False
    assert locks["carla_runs_chicagoland"] is False
    assert locks["cesiumjs_is_default_lookdev"] is False
    assert locks["calibration_candidate"] == "jax_differentiable"
    assert locks["gpu_micro_candidate"] == "moss"
    assert HERO_RENDERER == "unreal"
    assert MICRO_DEFAULT == "sumo"
    assert LOOKDEV_VIEWER == "maplibre"
    assert GPU_MICRO_CANDIDATE == "moss"
    assert CALIBRATION_CANDIDATE == "jax_differentiable"
    assert LLM_IN_SAFETY_LOOP is False
    assert MOSS_IS_DEFAULT_MICRO is False
    assert CARLA_RUNS_CHICAGOLAND is False
    assert CESIUMJS_IS_DEFAULT_LOOKDEV is False


def test_readme_and_architecture_still_name_sumo_and_unreal():
    blob = _read("README.md", "docs/ARCHITECTURE.md", "docs/IDEAS.md", "docs/RESEARCH.md").lower()
    assert "unreal" in blob
    assert "sumo" in blob
    assert "unity" in blob  # forbidden, named as such
    assert "not unity" in blob or "unreal, not unity" in blob or "forbidden" in blob


def test_research_doc_grounds_the_share_and_refuses_llm_loop():
    research = _read("docs/RESEARCH.md")
    assert SHARE_URL in research
    assert "kvnloo/smartcity" in research
    assert "Makinoshima" in research
    assert "MOSS" in research
    assert "JAX" in research
    assert "GERS" in research
    assert "50–100 Hz" in research or "50-100 Hz" in research
    assert "Do not put an LLM" in research or "does not steer cars" in research
    assert "CARLA does **not** run Chicagoland" in research
    assert chicago_sketch_ladder()[0] == 100_000
    assert chicago_sketch_ladder()[-1] == 2_000_000


def test_catalog_micro_engine_is_still_sumo():
    data = json.loads((ROOT / "data/catalog/datasets.json").read_text(encoding="utf-8"))
    assert "SUMO" in data["stack"]["micro"]
    assert "Unreal" in data["stack"]["hero_rt"]
    assert "MOSS" not in data["stack"]["micro"]


def test_bench_kernels_cli_prints_protocol_without_fake_moss_fps():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "bench_kernels.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["locks"]["micro_default"] == "sumo"
    assert payload["locks"]["hero_renderer"] == "unreal"
    assert payload["populations"] == chicago_sketch_ladder()
    assert "fake" in payload["kernels"][1]["run"]
    assert "4090" in payload["note"] or "4090" in json.dumps(payload)
