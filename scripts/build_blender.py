#!/usr/bin/env python3
"""Launch Blender city builds: OSM extrusion (default) or Google 3D Tiles."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLENDER = ROOT / "tools" / "blender-5.1.2-linux-x64" / "blender"


def blender_bin() -> Path:
    if BLENDER.exists():
        return BLENDER
    found = shutil_which("blender")
    if not found:
        sys.exit("Blender not found. Install 5.1+ or place a portable copy under tools/.")
    return Path(found)


def shutil_which(name: str) -> str | None:
    from shutil import which

    return which(name)


def main() -> None:
    p = argparse.ArgumentParser(description="Build a Naperville .blend from maps")
    p.add_argument("--source", choices=("osm", "google"), default="osm")
    p.add_argument("--preset", default="tiled_500", help="OSM extrusion preset")
    p.add_argument("--extent", choices=("downtown", "city"), default="downtown")
    p.add_argument("--lod", default="lod3")
    args, extra = p.parse_known_args()
    bin_ = blender_bin()
    if args.source == "osm":
        script = ROOT / "blender_scripts" / "build_city.py"
        cmd = [str(bin_), "--background", "--python", str(script), "--", "--preset", args.preset, *extra]
    else:
        if not (os.environ.get("GOOGLE_MAPS_API_KEY") or os.environ.get("GOOGLE_3D_TILES_KEY")):
            sys.exit(
                "Google source needs GOOGLE_MAPS_API_KEY (Maps Tiles API + billing).\n"
                "We do not scrape Google Maps. See blender_scripts/import_google_city.py."
            )
        script = ROOT / "blender_scripts" / "import_google_city.py"
        cmd = [
            str(bin_),
            "--background",
            "--python",
            str(script),
            "--",
            "--extent",
            args.extent,
            "--lod",
            args.lod,
            *extra,
        ]
    print(">>", " ".join(cmd), flush=True)
    raise SystemExit(subprocess.call(cmd, cwd=ROOT))


if __name__ == "__main__":
    main()
