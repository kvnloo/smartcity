"""glTF 2.0 export path: origin, metres, hero ring, Unreal sidecar."""

import json
import os
import subprocess
import sys
from pathlib import Path
from shutil import which

from smartcity.gltf_export import (
    BLENDER_UP,
    CRS,
    DOCUMENTED_CLI,
    FALLBACK_ORIGIN_LONLAT,
    GLTF_UP,
    HERO_RADIUS_M,
    METRE_SCALE,
    SOLARPUNK_MATERIALS,
    UNREAL_CM_PER_METRE,
    UNREAL_UP,
    blender_osm_cmd,
    glb_path,
    hero_keep,
    load_city_meta,
    preferred_blender_bin,
    resolve_origin_lonlat,
    resolve_origin_utm,
    sidecar_dict,
    sidecar_path,
    unreal_import_scale,
    write_import_sidecar,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "city_origin.json"


def test_fallback_origin_is_downtown_naperville():
    assert resolve_origin_lonlat(None) == (-88.147, 41.75)
    assert FALLBACK_ORIGIN_LONLAT == (-88.147, 41.75)
    assert resolve_origin_lonlat({}) == FALLBACK_ORIGIN_LONLAT
    assert resolve_origin_lonlat({"origin_lonlat": []}) == FALLBACK_ORIGIN_LONLAT


def test_origin_from_city_meta_fixture():
    meta = load_city_meta(FIXTURE)
    lon, lat = resolve_origin_lonlat(meta)
    utm = resolve_origin_utm(meta)
    assert lon == -88.106604
    assert lat == 41.75421
    assert utm == (408001.19, 4623078.76)
    assert meta["crs"] == CRS


def test_origin_prefers_processed_city_json_when_present():
    city = ROOT / "data" / "processed" / "city.json"
    if not city.is_file():
        return
    meta = load_city_meta(city)
    lon, lat = resolve_origin_lonlat(meta)
    assert lon == meta["origin_lonlat"][0]
    assert lat == meta["origin_lonlat"][1]
    assert (lon, lat) != FALLBACK_ORIGIN_LONLAT


def test_metres_scale_and_unreal_centimetres():
    assert METRE_SCALE == 1.0
    assert UNREAL_CM_PER_METRE == 100.0
    assert unreal_import_scale() == 100.0
    assert unreal_import_scale(2.0) == 200.0


def test_up_axis_contract_blender_z_gltf_y_unreal_z():
    assert BLENDER_UP == "+Z"
    assert GLTF_UP == "+Y"
    assert UNREAL_UP == "+Z"


def test_export_paths_are_under_output_gltf():
    assert glb_path(ROOT, "tiled_500") == ROOT / "output" / "gltf" / "naperville_tiled_500.glb"
    assert sidecar_path(ROOT, "tiled_500") == ROOT / "output" / "gltf" / "naperville_tiled_500.import.json"


def test_hero_keep_inclusive_radius_in_metres():
    assert HERO_RADIUS_M == 1500.0
    assert hero_keep(0.0, 0.0, 1500.0) is True
    assert hero_keep(1500.0, 0.0, 1500.0) is True
    assert hero_keep(1500.1, 0.0, 1500.0) is False
    assert hero_keep(2000.0, 0.0, 0.0) is True
    assert hero_keep(-400.0, 800.0, 1500.0) is True


def test_osm_blender_cmd_exports_gltf_and_never_calls_google():
    blender = ROOT / "tools" / "blender-5.1.2-linux-x64" / "blender"
    cmd = blender_osm_cmd(
        blender,
        ROOT,
        preset="tiled_500",
        export="gltf",
        hero_radius=HERO_RADIUS_M,
        max_buildings=40,
    )
    joined = " ".join(cmd)
    assert str(blender) == cmd[0]
    assert "--background" in cmd
    assert str(ROOT / "blender_scripts" / "build_city.py") in cmd
    assert "--preset" in cmd and "tiled_500" in cmd
    assert "--export" in cmd and "gltf" in cmd
    assert str(glb_path(ROOT, "tiled_500")) in cmd
    assert "--hero-radius" in cmd and "1500.0" in cmd
    assert "import_google_city" not in joined
    assert "google" not in joined.lower()
    assert "3d-tiles" not in joined.lower()
    assert "GOOGLE" not in joined


def test_preferred_blender_bin_is_portable_copy():
    assert preferred_blender_bin(ROOT) == ROOT / "tools" / "blender-5.1.2-linux-x64" / "blender"


def test_sidecar_points_unreal_at_glb_and_city_origin(tmp_path: Path):
    meta = load_city_meta(FIXTURE)
    payload = sidecar_dict(
        preset="tiled_500",
        origin_lonlat=resolve_origin_lonlat(meta),
        origin_utm=resolve_origin_utm(meta),
        hero_radius_m=HERO_RADIUS_M,
        source="osm",
    )
    assert payload["format"] == "glTF 2.0"
    assert payload["asset"] == "naperville_tiled_500.glb"
    assert payload["units"] == "metres"
    assert payload["scale"] == 1.0
    assert payload["crs"] == "EPSG:32616"
    assert payload["source"] == "osm"
    assert payload["origin_lonlat"] == [-88.106604, 41.75421]
    assert payload["axes"]["blender"] == "+Z"
    assert payload["axes"]["gltf"] == "+Y"
    assert payload["axes"]["unreal"] == "+Z"
    assert payload["unreal"]["import_uniform_scale"] == 100.0
    assert payload["unreal"]["place_at"] == [0.0, 0.0, 0.0]
    out = write_import_sidecar(tmp_path / "naperville_tiled_500.import.json", payload)
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "glTF 2.0" in text
    assert "Datasmith" in text


def test_solarpunk_materials_cover_lookdev():
    names = set(SOLARPUNK_MATERIALS)
    assert {"limestone", "copper", "moss", "lantern", "retired_pad"} <= names
    assert SOLARPUNK_MATERIALS["copper"]["metallic"] > 0.5
    assert SOLARPUNK_MATERIALS["limestone"]["metallic"] < 0.1
    assert SOLARPUNK_MATERIALS["lantern"]["emission_strength"] > 1.0
    assert SOLARPUNK_MATERIALS["moss"]["roughness"] > 0.7


def test_documented_cli_is_osm_tiled_500_gltf():
    assert DOCUMENTED_CLI == "python3 scripts/build_blender.py --source osm --preset tiled_500 --export gltf"


def test_cli_help_lists_export_gltf():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_blender.py"), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "--export" in proc.stdout
    assert "gltf" in proc.stdout
    assert "tiled_500" in proc.stdout


def test_google_source_still_requires_key():
    env = os.environ.copy()
    env.pop("GOOGLE_MAPS_API_KEY", None)
    env.pop("GOOGLE_3D_TILES_KEY", None)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_blender.py"), "--source", "google"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode != 0
    text = proc.stderr + proc.stdout
    assert "GOOGLE_MAPS_API_KEY" in text
    assert "import_google_city" not in " ".join(
        blender_osm_cmd(preferred_blender_bin(ROOT), ROOT, preset="tiled_500", export="gltf")
    )


def test_export_gltf_without_blender_writes_sidecar():
    if preferred_blender_bin(ROOT).exists() or which("blender"):
        return
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_blender.py"),
            "--source",
            "osm",
            "--preset",
            "tiled_500",
            "--export",
            "gltf",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    text = proc.stderr + proc.stdout
    assert "Blender not found" in text
    data = json.loads(sidecar_path(ROOT, "tiled_500").read_text(encoding="utf-8"))
    assert data["format"] == "glTF 2.0"
    assert data["asset"] == "naperville_tiled_500.glb"
    assert data["units"] == "metres"
