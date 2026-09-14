"""Pure-Python glTF 2.0 export contract for Unreal (no bpy).

Blender scene: metres, +Z up, XY = UTM 16N metres relative to origin.
glTF 2.0 file: metres, +Y up (Blender's exporter converts).
Unreal world: centimetres, +Z up. Import uniform scale 100 unless the
importer already converts metres.

Origin: `data/processed/city.json` meta.origin_lonlat when present, else
downtown Naperville (-88.147, 41.75). Never Google 3D Tiles.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FALLBACK_ORIGIN_LONLAT = (-88.147, 41.75)
CRS = "EPSG:32616"
METRE_SCALE = 1.0
UNREAL_CM_PER_METRE = 100.0
BLENDER_UP = "+Z"
GLTF_UP = "+Y"
UNREAL_UP = "+Z"
HERO_RADIUS_M = 1500.0
DEFAULT_PRESET = "tiled_500"
DOCUMENTED_CLI = "python3 scripts/build_blender.py --source osm --preset tiled_500 --export gltf"
PORTABLE_BLENDER = Path("tools") / "blender-5.1.2-linux-x64" / "blender"

SOLARPUNK_MATERIALS: dict[str, dict[str, Any]] = {
    "limestone": {
        "rgba": (0.72, 0.62, 0.48, 1.0),
        "metallic": 0.02,
        "roughness": 0.78,
        "emission_strength": 0.0,
    },
    "copper": {
        "rgba": (0.72, 0.38, 0.18, 1.0),
        "metallic": 0.86,
        "roughness": 0.32,
        "emission_strength": 0.0,
    },
    "moss": {
        "rgba": (0.18, 0.38, 0.16, 1.0),
        "metallic": 0.0,
        "roughness": 0.92,
        "emission_strength": 0.0,
    },
    "lantern": {
        "rgba": (1.0, 0.74, 0.38, 1.0),
        "metallic": 0.12,
        "roughness": 0.35,
        "emission": (1.0, 0.62, 0.22, 1.0),
        "emission_strength": 12.0,
    },
    "retired_pad": {
        "rgba": (0.82, 0.42, 0.22, 1.0),
        "metallic": 0.05,
        "roughness": 0.5,
        "emission": (0.82, 0.28, 0.12, 1.0),
        "emission_strength": 2.0,
    },
}


def preferred_blender_bin(root: Path) -> Path:
    return root / PORTABLE_BLENDER


def resolve_origin_lonlat(meta: dict[str, Any] | None) -> tuple[float, float]:
    if meta:
        origin = meta.get("origin_lonlat")
        if origin is not None and len(origin) >= 2:
            return float(origin[0]), float(origin[1])
    return FALLBACK_ORIGIN_LONLAT


def resolve_origin_utm(meta: dict[str, Any] | None) -> tuple[float, float] | None:
    if meta:
        origin = meta.get("origin_utm")
        if origin is not None and len(origin) >= 2:
            return float(origin[0]), float(origin[1])
    return None


def load_city_meta(city_path: Path) -> dict[str, Any] | None:
    if not city_path.is_file():
        return None
    data = json.loads(city_path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("meta"), dict):
        return data["meta"]
    if isinstance(data, dict) and "origin_lonlat" in data:
        return data
    return None


def hero_keep(x: float, y: float, radius_m: float) -> bool:
    if radius_m <= 0:
        return True
    return (x * x + y * y) <= radius_m * radius_m


def unreal_import_scale(metres: float = METRE_SCALE) -> float:
    return metres * UNREAL_CM_PER_METRE


def export_dir(root: Path) -> Path:
    return root / "output" / "gltf"


def glb_path(root: Path, preset: str) -> Path:
    return export_dir(root) / f"naperville_{preset}.glb"


def sidecar_path(root: Path, preset: str) -> Path:
    return export_dir(root) / f"naperville_{preset}.import.json"


def blender_osm_cmd(
    blender: Path,
    root: Path,
    *,
    preset: str = DEFAULT_PRESET,
    export: str = "gltf",
    city: Path | None = None,
    hero_radius: float | None = None,
    max_buildings: int | None = None,
    extra: list[str] | None = None,
) -> list[str]:
    """OSM extrusion only. Never points at import_google_city.py."""
    script = root / "blender_scripts" / "build_city.py"
    cmd = [str(blender), "--background", "--python", str(script), "--", "--preset", preset]
    if city is not None:
        cmd += ["--city", str(city)]
    if export == "gltf":
        cmd += ["--export", "gltf", "--out-gltf", str(glb_path(root, preset))]
    if hero_radius is not None:
        cmd += ["--hero-radius", str(hero_radius)]
    if max_buildings is not None:
        cmd += ["--max-buildings", str(max_buildings)]
    if extra:
        cmd.extend(extra)
    return cmd


def sidecar_dict(
    *,
    preset: str,
    origin_lonlat: tuple[float, float],
    origin_utm: tuple[float, float] | None,
    hero_radius_m: float,
    source: str = "osm",
) -> dict[str, Any]:
    lon, lat = origin_lonlat
    return {
        "asset": f"naperville_{preset}.glb",
        "format": "glTF 2.0",
        "source": source,
        "preset": preset,
        "units": "metres",
        "scale": METRE_SCALE,
        "crs": CRS,
        "origin_lonlat": [lon, lat],
        "origin_utm": [origin_utm[0], origin_utm[1]] if origin_utm else None,
        "hero_radius_m": hero_radius_m,
        "axes": {
            "blender": BLENDER_UP,
            "gltf": GLTF_UP,
            "unreal": UNREAL_UP,
        },
        "unreal": {
            "importer": "glTF importer (built-in) or Datasmith",
            "import_uniform_scale": unreal_import_scale(),
            "convert_scene": True,
            "world_partition_cell_m": 256,
            "place_at": [0.0, 0.0, 0.0],
            "cesium_georeference_origin_lonlat": [lon, lat],
        },
        "notes": [
            "Blender scene is metres, +Z up, XY = EPSG:32616 easting/northing relative to origin.",
            "glTF 2.0 is metres, +Y up (Blender exporter converts Z-up → Y-up).",
            "Unreal is centimetres, +Z up. If the mesh is 100× too small, set import uniform scale to 100.",
            "Cesium georeference must use the same origin_lonlat so slot pads line up with SUMO.",
            "This asset is OSM extrusion. Do not substitute Google Photorealistic 3D Tiles.",
        ],
    }


def write_import_sidecar(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
