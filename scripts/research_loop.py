#!/usr/bin/env python3
"""Research loop: try Blender city-build presets and pick the best RT cost.

RT cost is a weighted log mix of object count, triangle count, and depsgraph
update time — the three knobs that dominate EEVEE viewport hitching on a
city-scale mesh (Blosm / segment-mesh guidance: tile for culling, join inside
a tile, never one object per building).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLENDER = ROOT / "tools" / "blender-5.1.2-linux-x64" / "blender"
SCRIPT = ROOT / "blender_scripts" / "build_city.py"
OUT = ROOT / "output" / "research"
PRESETS = ["naive_objects", "tiled_250", "tiled_500", "tiled_1000", "lod_lite"]


def run_preset(name: str) -> dict:
    cmd = [
        str(BLENDER),
        "--background",
        "--python",
        str(SCRIPT),
        "--",
        "--preset",
        name,
    ]
    print(">>", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    path = OUT / f"{name}.json"
    if proc.returncode != 0 or not path.exists():
        print(proc.stdout[-3000:], file=sys.stderr)
        print(proc.stderr[-4000:], file=sys.stderr)
        raise SystemExit(f"blender failed on {name} (code {proc.returncode})")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for name in PRESETS:
        row = run_preset(name)
        results.append(row)
        print(f"  {name}: objects={row['objects']} tris={row['tris']} dg={row['depsgraph_ms']}ms cost={row['rt_cost']}")

    # Prefer lowest RT cost, but never pick naive if a tiled preset exists.
    ranked = sorted(results, key=lambda r: (r["rt_cost"], r["objects"], r["tris"]))
    winner = ranked[0]
    report = {
        "winner": winner["preset"],
        "rationale": (
            "Tile meshes so EEVEE can cull off-camera city blocks; join geometry "
            "inside a tile to cut object overhead; keep a handful of shared materials. "
            "Naive per-building objects lose to draw-call count long before triangle count."
        ),
        "results": results,
        "copy_winner_to": "output/blends/naperville_city.blend",
    }
    (OUT / "loop_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    src = ROOT / "output" / "blends" / f"naperville_{winner['preset']}.blend"
    dst = ROOT / "output" / "blends" / "naperville_city.blend"
    if src.exists():
        dst.write_bytes(src.read_bytes())
    print(json.dumps({"winner": winner["preset"], "rt_cost": winner["rt_cost"]}, indent=2))


if __name__ == "__main__":
    main()
