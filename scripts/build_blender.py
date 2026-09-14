#!/usr/bin/env python3
"""Launch Blender city builds: OSM extrusion (default) or Google 3D Tiles.

Unreal hero mesh (no Google key):

  python3 scripts/build_blender.py --source osm --preset tiled_500 --export gltf

Writes output/gltf/naperville_tiled_500.glb plus a .import.json sidecar
(origin, metres, up-axis) for the Unreal glTF / Datasmith importer.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from shutil import which

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from smartcity.gltf_export import (
    DOCUMENTED_CLI,
    HERO_RADIUS_M,
    blender_osm_cmd,
    downtown_xy_in_mesh,
    glb_path,
    load_city_meta,
    preferred_blender_bin,
    resolve_origin_lonlat,
    resolve_origin_utm,
    sidecar_dict,
    sidecar_path,
    write_import_sidecar,
)

BLENDER = preferred_blender_bin(ROOT)
DEFAULT_CITY = ROOT / "data" / "processed" / "city.json"


def find_blender() -> Path | None:
    if BLENDER.exists():
        return BLENDER
    found = which("blender")
    return Path(found) if found else None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build a Naperville .blend / glTF 2.0 from OSM extrusion",
        epilog=f"Unreal: {DOCUMENTED_CLI}",
    )
    p.add_argument("--source", choices=("osm", "google"), default="osm")
    p.add_argument("--preset", default="tiled_500", help="OSM extrusion preset")
    p.add_argument("--extent", choices=("downtown", "city"), default="downtown")
    p.add_argument("--lod", default="lod3")
    p.add_argument(
        "--export",
        choices=("blend", "gltf"),
        default="blend",
        help="blend = .blend only (research). gltf = .blend + glTF 2.0 under output/gltf/",
    )
    p.add_argument("--city", default=str(DEFAULT_CITY), help="Processed city.json")
    p.add_argument(
        "--hero-radius",
        type=float,
        default=None,
        help="Metres from origin. glTF default 1500 (hero ring). 0 = whole city.",
    )
    p.add_argument("--max-buildings", type=int, default=None, help="Override preset cap")
    args, extra = p.parse_known_args(argv)
    args.extra = extra
    return args


def write_gltf_sidecar(args: argparse.Namespace, hero_radius: float) -> Path:
    meta = load_city_meta(Path(args.city))
    payload = sidecar_dict(
        preset=args.preset,
        origin_lonlat=resolve_origin_lonlat(meta),
        origin_utm=resolve_origin_utm(meta),
        hero_radius_m=hero_radius,
        source="osm",
    )
    path = sidecar_path(ROOT, args.preset)
    write_import_sidecar(path, payload)
    print(f"wrote sidecar {path.relative_to(ROOT)}", flush=True)
    print(f"  origin_lonlat={payload['origin_lonlat']} units=metres glTF=+Y Unreal=+Z scale={payload['unreal']['import_uniform_scale']}", flush=True)
    print(f"  Unreal target: {glb_path(ROOT, args.preset).relative_to(ROOT)} place_at={payload['unreal']['place_at']}", flush=True)
    return path


def main() -> None:
    args = parse_args()
    extra: list[str] = list(args.extra)

    if args.source == "google":
        if not (os.environ.get("GOOGLE_MAPS_API_KEY") or os.environ.get("GOOGLE_3D_TILES_KEY")):
            sys.exit(
                "Google source needs GOOGLE_MAPS_API_KEY (Maps Tiles API + billing).\n"
                "We do not scrape Google Maps. OSM is the default:\n"
                f"  {DOCUMENTED_CLI}"
            )
        bin_ = find_blender()
        if not bin_:
            sys.exit("Blender not found. Install 5.1+ or place a portable copy under tools/.")
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

    hero_radius = args.hero_radius
    if hero_radius is None:
        hero_radius = HERO_RADIUS_M if args.export == "gltf" else 0.0

    if args.export == "gltf":
        write_gltf_sidecar(args, hero_radius)

    bin_ = find_blender()
    if not bin_:
        msg = (
            "Blender not found at tools/blender-5.1.2-linux-x64/blender or PATH.\n"
            "Install 5.1+ or place a portable copy under tools/.\n"
            f"Documented Unreal command: {DOCUMENTED_CLI}\n"
            f"glTF target: {glb_path(ROOT, args.preset).relative_to(ROOT)}"
        )
        if args.export == "gltf":
            msg += f"\nSidecar written; mesh export skipped."
        sys.exit(msg)

    meta = load_city_meta(Path(args.city))
    clip_cx, clip_cy = downtown_xy_in_mesh(resolve_origin_lonlat(meta), resolve_origin_utm(meta))

    cmd = blender_osm_cmd(
        bin_,
        ROOT,
        preset=args.preset,
        export=args.export,
        city=Path(args.city),
        hero_radius=hero_radius,
        max_buildings=args.max_buildings,
        clip_cx=clip_cx,
        clip_cy=clip_cy,
        extra=extra,
    )
    print(">>", " ".join(cmd), flush=True)
    raise SystemExit(subprocess.call(cmd, cwd=ROOT))


if __name__ == "__main__":
    main()
