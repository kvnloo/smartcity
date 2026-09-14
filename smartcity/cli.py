from __future__ import annotations

import argparse
import json

import uvicorn

from smartcity.sim import demo_metrics


def main() -> None:
    p = argparse.ArgumentParser(prog="smartcity")
    sub = p.add_subparsers(dest="cmd", required=True)
    serve = sub.add_parser("serve", help="Run the city control API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=43147)
    bench = sub.add_parser("bench", help="Headless policy comparison")
    bench.add_argument("--seconds", type=float, default=25.0)
    bench.add_argument("--policy", default="all")
    args = p.parse_args()
    if args.cmd == "serve":
        uvicorn.run("smartcity.api:app", host=args.host, port=args.port, reload=False)
        return
    policies = ["lights", "fair", "batch", "aim"] if args.policy == "all" else [args.policy]
    out = {pol: demo_metrics(seconds=args.seconds, policy=pol, seed=7)["metrics"] for pol in policies}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
