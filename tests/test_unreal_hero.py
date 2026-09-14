"""Unreal 5.4 Naperville hero skeleton — 3080 Ti budget, no Unity, no Maps key."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERO = ROOT / "unreal" / "SmartCityHero"
UPROJECT = HERO / "SmartCityHero.uproject"
ENGINE_INI = HERO / "Config" / "DefaultEngine.ini"
GAME_INI = HERO / "Config" / "DefaultGame.ini"
CVARS_INI = HERO / "Config" / "ConsoleVariables.ini"
GEOREF = HERO / "Config" / "Georef.json"
README = HERO / "README.md"
PIPELINE = ROOT / "unreal" / "PIPELINE.md"
GLTF_IMPORT = HERO / "Content" / "City" / "Naperville" / "Import"
I88_DIR = HERO / "Content" / "City" / "Naperville" / "I88"
SOURCE = HERO / "Source"


def _read(*paths: Path) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in paths if p.is_file())


def _hero_text_files() -> list[Path]:
    skip = {".png", ".uasset", ".umap", ".dll", ".pdb"}
    out = []
    for path in HERO.rglob("*"):
        if path.is_file() and path.suffix.lower() not in skip:
            out.append(path)
    return out


def test_uproject_is_unreal_54_with_live_module():
    data = json.loads(UPROJECT.read_text(encoding="utf-8"))
    assert str(data["EngineAssociation"]).startswith("5.4")
    names = {m["Name"] for m in data.get("Modules", [])}
    assert "SmartCityLive" in names
    assert (HERO / "Source" / "SmartCityHero.Target.cs").is_file()
    assert (HERO / "Source" / "SmartCityHeroEditor.Target.cs").is_file()
    assert (SOURCE / "SmartCityLive" / "SmartCityLive.Build.cs").is_file()


def test_hero_is_not_unity():
    names = [p.name.lower() for p in HERO.rglob("*")]
    assert not any(n.endswith(".unity") or n.endswith(".unitypackage") for n in names)
    assert "projectsettings" not in names
    assert "packages-lock.json" not in names
    blob = _read(UPROJECT, README, PIPELINE).lower()
    assert "unity" in blob
    assert "not unity" in blob or "unreal, not unity" in blob or "forbidden" in blob


def test_gltf_lands_in_content_city_naperville():
    assert GLTF_IMPORT.is_dir()
    drop_notes = list(GLTF_IMPORT.glob("*"))
    assert drop_notes, "Import folder needs a placeholder so git keeps it"
    readme = README.read_text(encoding="utf-8")
    pipeline = PIPELINE.read_text(encoding="utf-8")
    assert "SmartCityHero.uproject" in readme or "SmartCityHero.uproject" in pipeline
    assert "Content/City/Naperville/Import" in readme
    assert "gltf" in readme.lower()
    assert "World Partition" in readme
    assert "256" in readme


def test_origin_is_naperville_utm_16n():
    geo = json.loads(GEOREF.read_text(encoding="utf-8"))
    lon, lat = geo["origin_lonlat"]
    assert abs(lon - (-88.147)) < 0.02
    assert abs(lat - 41.75) < 0.02
    assert "32616" in str(geo["crs"])
    game = GAME_INI.read_text(encoding="utf-8")
    assert "-88.147" in game
    assert "41.75" in game


def test_3080_ti_lumen_software_vsm_nanite():
    engine = ENGINE_INI.read_text(encoding="utf-8")
    cvars = CVARS_INI.read_text(encoding="utf-8") if CVARS_INI.is_file() else ""
    blob = engine + "\n" + cvars
    assert "r.DynamicGlobalIlluminationMethod=1" in blob
    assert "r.Lumen.HardwareRayTracing=False" in blob or "r.Lumen.HardwareRayTracing=0" in blob
    assert "r.RayTracing=False" in blob or "r.RayTracing=0" in blob
    assert "r.Shadow.Virtual.Enable=0" in blob
    assert "r.Nanite.ProjectEnabled=True" in blob or "r.Nanite.ProjectEnabled=1" in blob
    assert "WorldPartition" in engine or "256" in _read(GAME_INI, GEOREF, README)


def test_skeletal_cars_culled_inside_hero_radius():
    blob = _read(GAME_INI, GEOREF, README)
    assert "80" in blob and "120" in blob
    assert "1500" in blob or "1.5" in blob


def test_no_google_maps_key_in_hero_project():
    for path in _hero_text_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "AIza" not in text
        assert "GOOGLE_MAPS_API_KEY=" not in text
        assert "GOOGLE_3D_TILES_KEY=" not in text


def test_i88_extra_lane_is_bioswale_not_asphalt():
    notes = _read(README, *I88_DIR.glob("*"))
    assert I88_DIR.is_dir()
    assert "bioswale" in notes.lower()
    assert "asphalt" in notes.lower()
    assert "limestone" in README.read_text(encoding="utf-8").lower()
    assert "copper" in README.read_text(encoding="utf-8").lower()
    assert "moss" in README.read_text(encoding="utf-8").lower()


def test_smartcitylive_stub_reads_twin_and_ws():
    sources = _read(*SOURCE.rglob("*.h"), *SOURCE.rglob("*.cpp"), *SOURCE.rglob("*.cs"))
    assert "/twin" in sources
    assert "/ws" in sources
    assert "43147" in sources or "43147" in _read(GAME_INI)
    assert "bioswale" in sources.lower() or "Bioswale" in sources
