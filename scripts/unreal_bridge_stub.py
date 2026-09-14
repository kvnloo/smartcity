"""Print one GET /twin snapshot for Unreal engineers (no editor plugin required)."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from smartcity.twin.contract import TwinSnapshot, dump_contract  # noqa: E402
from smartcity.twin.macro import step_macro  # noqa: E402


def _from_server(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    p = argparse.ArgumentParser(
        description="Dump one live-contract /twin snapshot (zipper + rings + origin)."
    )
    p.add_argument("--hour", type=float, default=7.5, help="Civil start hour (default 07:30 inbound rush).")
    p.add_argument("--weekday", type=int, default=0, help="0=Monday … 6=Sunday.")
    p.add_argument(
        "--url",
        default="",
        help="If set, GET this URL instead of computing in-process (e.g. http://127.0.0.1:43147/twin).",
    )
    args = p.parse_args()
    raw = _from_server(args.url) if args.url else step_macro(0.0, args.hour, args.weekday)
    twin = TwinSnapshot.model_validate(raw)
    print(
        "live-contract-v1  GET /twin  — cars live on WS /ws; zipper lives on twin.lanes",
        file=sys.stderr,
    )
    origin = twin.origin
    print(
        f"mesh EPSG:32616 lon={origin.lon} lat={origin.lat}  "
        f"Unreal (0,0,0)=downtown {origin.ring_center_lon},{origin.ring_center_lat}  "
        f"uu=(x_m-downtown_x_m)×{origin.unreal_uu_per_metre:g}",
        file=sys.stderr,
    )
    print(json.dumps(dump_contract(twin), indent=2))


if __name__ == "__main__":
    main()
