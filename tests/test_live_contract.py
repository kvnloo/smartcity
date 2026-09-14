"""Frozen Unreal live contract: field names, units, origin, zipper flags, rings."""

from __future__ import annotations

import json

from smartcity.config import CITY_JSON, ROOT
from smartcity.twin.contract import (
    SCHEMA_DIR,
    dump_contract,
    json_schema_bundle,
    parse_lanes,
    parse_twin,
    parse_ws,
)
from smartcity.twin.lanes import snapshot as lane_snapshot
from smartcity.twin.macro import step_macro
from smartcity.twin.region import (
    MESH_CRS,
    MESH_ORIGIN_LONLAT,
    MESH_ORIGIN_UTM,
    mesh_xy_to_unreal_uu,
    origin_frame,
)

FIXTURES = ROOT / "tests" / "fixtures"
LOOKDEV = ROOT / "site" / "public" / "twin.json"

WEB_TWIN_KEYS = {"clock", "weekday_name", "lanes", "corridors", "fidelity"}
WEB_LANE_KEYS = {"id", "name", "direction", "fictional", "inbound_mult", "outbound_mult"}
WEB_SNAP_KEYS = {"metrics", "vehicles", "intersections", "twin", "labor", "services", "policy"}
LOOKDEV_KEYS = {"clock", "weekday_name", "lanes", "corridors", "fidelity", "playbook", "geo", "origin", "note"}


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_twin_payload_validates_at_default_rush():
    raw = step_macro(0.0, start_hour=7.5, start_weekday=0)
    twin = parse_twin(raw)
    dumped = dump_contract(twin)
    assert dumped["clock"] == "07:30"
    assert dumped["weekday_name"] == "Mon"
    assert dumped["weekend"] is False
    assert WEB_TWIN_KEYS <= dumped.keys()


def test_lanes_payload_validates_and_shares_twin_rows():
    raw = lane_snapshot(0.0, start_hour=7.5, start_weekday=0)
    lanes = parse_lanes(raw)
    twin = parse_twin(step_macro(0.0, start_hour=7.5, start_weekday=0))
    assert dump_contract(lanes)["facilities"] == dump_contract(twin)["lanes"]
    assert lanes.minutes == 7 * 60 + 30


def test_kennedy_is_real_i88_and_ogden_are_fictional():
    twin = parse_twin(step_macro(0.0, start_hour=7.5, start_weekday=0))
    by_id = {row.id: row for row in twin.lanes}
    assert set(by_id) == {"kennedy-revlac", "i88-solarpunk", "ogden-tidal"}
    assert by_id["kennedy-revlac"].fictional is False
    assert by_id["kennedy-revlac"].kind == "expressway"
    assert by_id["kennedy-revlac"].direction == "inbound"
    assert by_id["kennedy-revlac"].extra_lanes == 2
    assert by_id["i88-solarpunk"].fictional is True
    assert by_id["i88-solarpunk"].kind == "expressway"
    assert by_id["ogden-tidal"].fictional is True
    assert by_id["ogden-tidal"].kind == "arterial"


def test_ring_radii_km_and_metres():
    twin = parse_twin(step_macro(0.0, start_hour=7.5, start_weekday=0))
    rings = {row.name: row for row in twin.fidelity}
    assert rings["hero"].radius_km == 1.5
    assert rings["hero"].radius_m == 1500.0
    assert rings["micro"].radius_km == 8.0
    assert rings["micro"].radius_m == 8000.0
    assert rings["meso"].radius_km == 40.0
    assert rings["meso"].radius_m == 40000.0
    assert rings["macro"].radius_km == 120.0
    assert rings["macro"].radius_m == 120000.0
    assert rings["hero"].engine.startswith("unreal")
    assert "unity" not in rings["hero"].engine.lower()


def test_origin_matches_processed_city_json():
    meta = json.loads(CITY_JSON.read_text(encoding="utf-8"))["meta"]
    frame = origin_frame()
    assert frame["crs"] == meta["crs"] == MESH_CRS
    assert frame["lon"] == meta["origin_lonlat"][0] == MESH_ORIGIN_LONLAT[0]
    assert frame["lat"] == meta["origin_lonlat"][1] == MESH_ORIGIN_LONLAT[1]
    assert frame["utm_e"] == meta["origin_utm"][0] == MESH_ORIGIN_UTM[0]
    assert frame["utm_n"] == meta["origin_utm"][1] == MESH_ORIGIN_UTM[1]
    assert frame["units"] == "metre"
    assert frame["unreal_uu_per_metre"] == 100.0
    assert frame["x_axis"] == "east"
    assert frame["y_axis"] == "north"
    assert frame["downtown_x_m"] == round(frame["downtown_x_m"], 2)
    assert frame["downtown_y_m"] == round(frame["downtown_y_m"], 2)
    assert frame["downtown_x_m"] < -3000
    assert abs(frame["downtown_y_m"]) < 500
    twin = parse_twin(step_macro(0.0, 7.5, 0))
    assert dump_contract(twin)["origin"] == frame


def test_unreal_uu_puts_downtown_at_origin_and_mesh_origin_at_place_at():
    frame = origin_frame()
    downtown_uu = mesh_xy_to_unreal_uu(frame["downtown_x_m"], frame["downtown_y_m"], frame)
    assert downtown_uu == (0.0, 0.0, 0.0)
    mesh_origin_uu = mesh_xy_to_unreal_uu(0.0, 0.0, frame)
    assert mesh_origin_uu == (
        -frame["downtown_x_m"] * 100.0,
        -frame["downtown_y_m"] * 100.0,
        0.0,
    )
    georef = json.loads((ROOT / "unreal/SmartCityHero/Config/Georef.json").read_text(encoding="utf-8"))
    place = georef["city_json"]["place_city_json_gltf_at_uu"]
    assert mesh_origin_uu[0] == place[0]
    assert mesh_origin_uu[1] == place[1]


def test_committed_json_schemas_match_models():
    bundle = json_schema_bundle()
    for name, schema in bundle.items():
        path = SCHEMA_DIR / f"{name}.schema.json"
        committed = json.loads(path.read_text(encoding="utf-8"))
        assert committed == json.loads(json.dumps(schema, sort_keys=True)), path.name


def test_golden_twin_0730_monday():
    payload = dump_contract(parse_twin(step_macro(0.0, start_hour=7.5, start_weekday=0)))
    assert payload == _load_fixture("twin_0730_monday.json")


def test_golden_lanes_0730_monday():
    payload = dump_contract(parse_lanes(lane_snapshot(0.0, start_hour=7.5, start_weekday=0)))
    assert payload == _load_fixture("lanes_0730_monday.json")


def test_ws_snapshot_validates_and_keeps_ops_map_keys():
    from smartcity.config import SimConfig
    from smartcity.sim import CitySim

    sim = CitySim(cfg=SimConfig(target_vehicles=12, spawn_per_s=20, enable_services=False, seed=7))
    for _ in range(12):
        sim.step()
    snap = parse_ws(sim.snapshot())
    dumped = dump_contract(snap)
    assert dumped["type"] == "snapshot"
    assert WEB_SNAP_KEYS <= dumped.keys()
    assert snap.twin.lanes[0].id == "kennedy-revlac"
    assert snap.metrics.active == len(snap.vehicles)
    for veh in snap.vehicles:
        assert isinstance(veh.id, str)
        assert veh.kind in {"car", "bus", "emergency", "delivery"}
        assert veh.lon < -87.0
        assert veh.x_m != 0.0 or veh.y_m != 0.0
    for pad in snap.intersections[:3]:
        assert isinstance(pad.x_m, float)


def test_lookdev_twin_json_keeps_ops_and_hud_fields():
    """GitHub Pages lookdev is a baked subset — not the Unreal live contract."""
    data = json.loads(LOOKDEV.read_text(encoding="utf-8"))
    assert LOOKDEV_KEYS <= data.keys()
    assert data["clock"] == "07:30"
    assert data["weekday_name"] == "Mon"
    assert data["origin"] == [-88.147, 41.75]
    by_id = {row["id"]: row for row in data["lanes"]}
    assert by_id["kennedy-revlac"]["fictional"] is False
    assert by_id["i88-solarpunk"]["fictional"] is True
    assert by_id["ogden-tidal"]["fictional"] is True
    for row in data["lanes"]:
        assert WEB_LANE_KEYS <= row.keys()
    rings = {row["name"]: row["radius_km"] for row in data["fidelity"]}
    assert rings == {"hero": 1.5, "micro": 8.0, "meso": 40.0, "macro": 120.0}
    # Lookdev origin is downtown (ring centre), not the mesh /ws frame.
    live = dump_contract(parse_twin(step_macro(0.0, 7.5, 0)))
    assert data["origin"][0] == live["origin"]["ring_center_lon"]
    assert data["origin"][1] == live["origin"]["ring_center_lat"]
    assert data["origin"] != [live["origin"]["lon"], live["origin"]["lat"]]


def test_fastapi_twin_lanes_and_openapi_use_the_models():
    from fastapi.testclient import TestClient

    from smartcity.api import app

    with TestClient(app) as client:
        twin = client.get("/twin")
        assert twin.status_code == 200
        parse_twin(twin.json())
        lanes = client.get("/lanes")
        assert lanes.status_code == 200
        parse_lanes(lanes.json())
        spec = client.get("/openapi.json").json()
        schemas = spec["components"]["schemas"]
        assert "TwinSnapshot" in schemas
        assert "LaneClockSnapshot" in schemas
        assert "WsSnapshot" in schemas
        city = client.get("/city").json()
        assert city["origin_lonlat"]
        assert city["crs"] == "EPSG:32616"
        assert len(city["origin_utm"]) == 2
        snap = client.get("/snapshot")
        assert snap.status_code == 200
        ws = parse_ws(snap.json())
        assert ws.type == "snapshot"
        assert ws.source in {"sumo", "mock", "inproc"}
        assert ws.ring == "micro"
