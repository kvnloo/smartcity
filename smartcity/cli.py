from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import uvicorn

from smartcity.sim import demo_metrics
from smartcity.twin.macro import step_macro

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    p = argparse.ArgumentParser(prog="smartcity")
    sub = p.add_subparsers(dest="cmd", required=True)
    serve = sub.add_parser("serve", help="Run the city control API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=43147)
    bench = sub.add_parser("bench", help="Headless policy comparison")
    bench.add_argument("--seconds", type=float, default=25.0)
    bench.add_argument("--policy", default="all")
    twin = sub.add_parser("twin", help="Print the Chicagoland macro snapshot")
    twin.add_argument("--hour", type=float, default=7.5)
    twin.add_argument("--weekday", type=int, default=0)
    sub.add_parser("ingest", help="Refresh open-data samples into data/open/")
    sub.add_parser("sumo", help="Write SUMO nod/edg XML from Naperville")
    args = p.parse_args()
    if args.cmd == "serve":
        uvicorn.run("smartcity.api:app", host=args.host, port=args.port, reload=False)
        return
    if args.cmd == "twin":
        print(json.dumps(step_macro(0.0, start_hour=args.hour, start_weekday=args.weekday), indent=2))
        return
    if args.cmd == "ingest":
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "ingest_open_data.py")])
        return
    if args.cmd == "sumo":
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "build_sumo_net.py")])
        return
    policies = ["lights", "fair", "batch", "aim"] if args.policy == "all" else [args.policy]
    out = {pol: demo_metrics(seconds=args.seconds, policy=pol, seed=7)["metrics"] for pol in policies}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
