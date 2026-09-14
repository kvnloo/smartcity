"""Import Naperville as Google Photorealistic 3D Tiles via Blosm.

This is the legal Google path. The Maps JavaScript / raster tiles APIs
cannot be scraped into a mesh. Photorealistic 3D Tiles are the product
Google publishes for 3D city reconstruction:

  https://developers.google.com/maps/documentation/tile/3d-tiles
  https://github.com/vvoovv/blosm/wiki/Import-of-Google-3D-Cities

Requires:
  GOOGLE_MAPS_API_KEY or GOOGLE_3D_TILES_KEY
  Maps Tiles API enabled, billing account, unrestricted key.

Start with --extent downtown (≈1 km). Whole-city imports at high LOD
will blow triangle counts and quota (Blosm warns about this).

  blender --background --python blender_scripts/import_google_city.py -- --extent downtown --lod lod3
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
BLOSM_DIR = ROOT / "tools" / "blosm"
CACHE_DIR = ROOT / "data" / "google_tiles"
OUT_DIR = ROOT / "output" / "blends"
MANIFEST = ROOT / "data" / "raw" / "manifest.json"
BLOSM_REPO = "https://github.com/prochitecture/blosm.git"

# Naperville downtown fallback if OSM manifest is missing.
FALLBACK_BBOX = {
    "west": -88.155,
    "south": 41.768,
    "east": -88.142,
    "north": 41.778,
}

LOD_HELP = {
    "lod2": "districts",
    "lod3": "groups of buildings (recommended start)",
    "lod4": "separate buildings",
    "lod5": "buildings with details",
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--extent", choices=("downtown", "city"), default="downtown")
    p.add_argument("--lod", default="lod3", choices=sorted(LOD_HELP))
    p.add_argument("--tile-deg", type=float, default=0.01, help="≈1 km at this latitude")
    p.add_argument("--out", default="")
    p.add_argument("--key", default="")
    return p.parse_args(argv)


def api_key(args) -> str:
    return (
        args.key
        or os.environ.get("GOOGLE_MAPS_API_KEY")
        or os.environ.get("GOOGLE_3D_TILES_KEY")
        or ""
    ).strip()


def city_bbox() -> dict:
    if MANIFEST.exists():
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        return data["bbox"]
    return FALLBACK_BBOX


def downtown_bbox(full: dict) -> dict:
    # ~1.1 km box around the processed-city origin if we have it, else bbox center.
    cx = (full["west"] + full["east"]) / 2
    cy = (full["south"] + full["north"]) / 2
    half_lon = 0.0065
    half_lat = 0.005
    return {
        "west": cx - half_lon,
        "east": cx + half_lon,
        "south": cy - half_lat,
        "north": cy + half_lat,
    }


def tiles(bbox: dict, step: float) -> list[dict]:
    out = []
    lat = bbox["south"]
    while lat < bbox["north"] - 1e-9:
        lon = bbox["west"]
        nlat = min(lat + step * 0.8, bbox["north"])
        while lon < bbox["east"] - 1e-9:
            nlon = min(lon + step, bbox["east"])
            out.append({"west": lon, "south": lat, "east": nlon, "north": nlat})
            lon = nlon
        lat = nlat
    return out


def ensure_blosm() -> Path:
    if (BLOSM_DIR / "__init__.py").exists():
        return BLOSM_DIR
    BLOSM_DIR.parent.mkdir(parents=True, exist_ok=True)
    if BLOSM_DIR.exists():
        shutil.rmtree(BLOSM_DIR)
    print(f"Cloning Blosm into {BLOSM_DIR} …", flush=True)
    subprocess.check_call(["git", "clone", "--depth", "1", "--branch", "release", BLOSM_REPO, str(BLOSM_DIR)])
    return BLOSM_DIR


def install_addon(addon_dir: Path) -> None:
    scripts = Path(bpy.utils.user_resource("SCRIPTS", path="addons", create=True))
    dest = scripts / "blosm"
    if dest.exists():
        shutil.rmtree(dest)
    zip_path = addon_dir.parent / "blosm.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in addon_dir.rglob("*"):
            if ".git" in path.parts:
                continue
            zf.write(path, Path("blosm") / path.relative_to(addon_dir))
    bpy.ops.preferences.addon_install(filepath=str(zip_path), overwrite=True)
    bpy.ops.preferences.addon_enable(module="blosm")
    bpy.ops.wm.save_userpref()


def main() -> None:
    args = parse_args()
    key = api_key(args)
    if not key:
        print(
            "No Google 3D Tiles key.\n"
            "Set GOOGLE_MAPS_API_KEY (Maps Tiles API enabled, billing on, unrestricted key).\n"
            "Docs: https://developers.google.com/maps/documentation/tile/get-api-key\n"
            "We cannot scrape Google Maps raster tiles into Blender — that violates Google's ToS.\n"
            "Until a key is set, use the OSM extrusion path: blender_scripts/build_city.py",
            file=sys.stderr,
        )
        sys.exit(2)

    full = city_bbox()
    extent = downtown_bbox(full) if args.extent == "downtown" else full
    chunks = tiles(extent, args.tile_deg) if args.extent == "city" else [extent]
    print(f"Importing {len(chunks)} tile(s) at {args.lod} ({LOD_HELP[args.lod]})", flush=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_dir = ensure_blosm()
    install_addon(addon_dir)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    prefs = bpy.context.preferences.addons["blosm"].preferences
    prefs.googleMapsApiKey = key
    prefs.dataDir = str(CACHE_DIR)

    scene = bpy.context.scene
    blosm = scene.blosm
    blosm.dataType = "3d-tiles"
    blosm.threedTilesSource = "google"
    blosm.lodOf3dTiles = args.lod
    blosm.join3dTilesObjects = True

    for i, box in enumerate(chunks):
        print(f"  tile {i + 1}/{len(chunks)} {box}", flush=True)
        blosm.minLon = box["west"]
        blosm.minLat = box["south"]
        blosm.maxLon = box["east"]
        blosm.maxLat = box["north"]
        # Keep later tiles in the same local frame as the first import.
        if hasattr(blosm, "relativeToInitialImport"):
            blosm.relativeToInitialImport = i > 0
        result = bpy.ops.blosm.import_data()
        print(f"    ops result={result}", flush=True)

    out = Path(args.out) if args.out else OUT_DIR / f"naperville_google_{args.extent}_{args.lod}.blend"
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out), compress=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
