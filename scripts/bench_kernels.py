#!/usr/bin/env python3
"""Print the Chicago Sketch kernel bench protocol. Do not invent MOSS FPS."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from smartcity.twin.research import (  # noqa: E402
    CHICAGO_SKETCH,
    GPU_MICRO_CANDIDATE,
    MICRO_DEFAULT,
    MOSS_PUBLISHED_GPU,
    SHARE_URL,
    VRAM_BUDGET_GB,
    architecture_locks,
    chicago_sketch_ladder,
)


def main() -> None:
    protocol = {
        "share": SHARE_URL,
        "locks": architecture_locks(),
        "chicago_sketch_paper": CHICAGO_SKETCH,
        "populations": chicago_sketch_ladder(),
        "kernels": [
            {
                "id": MICRO_DEFAULT,
                "role": "default micro/meso in this repo",
                "run": "python3 scripts/build_sumo_net.py && smartcity micro --seconds 8",
            },
            {
                "id": GPU_MICRO_CANDIDATE,
                "role": "candidate CUDA validator — not default, not the brain",
                "published_on": MOSS_PUBLISHED_GPU,
                "our_vram_budget_gb": VRAM_BUDGET_GB,
                "run": "workstation only; this script will not fake throughput",
            },
            {
                "id": "jax_differentiable",
                "role": "candidate calibrator (Chicago Sketch paper)",
                "metric": "calibration error reduction per GPU-minute",
            },
        ],
        "note": (
            "Do not report 4090 MOSS numbers as 3080 Ti capacity. "
            "Do not put an LLM in the 50-100 Hz loop."
        ),
    }
    print(json.dumps(protocol, indent=2))


if __name__ == "__main__":
    main()
