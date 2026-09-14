"""8 km micro ring: SUMO XML + TraCI/mock loop (no Eclipse SUMO required)."""

from __future__ import annotations

import pytest
import xml.etree.ElementTree as ET

from smartcity.adapters.sumo import (
    ARTERIAL_CAP_MPS,
    MOTORWAY_CAP_MPS,
    build_micro_spec,
    install_hint,
    write_plain_xml,
)
from smartcity.adapters.traci import MockTraCI, open_client
from smartcity.config import MICRO_TICK_S, SimConfig
from smartcity.micro import MicroLoop
from smartcity.slots import SlotManager
from smartcity.twin.contract import parse_ws


WS_VEHICLE = {"id", "kind", "lon", "lat", "x_m", "y_m", "speed_mph", "heading"}
WS_ROOT = {"type", "t", "policy", "vehicles", "intersections", "metrics", "twin", "source", "ring", "tick_s"}


def test_sumo_plain_xml_writes_micro_ring(tmp_path):
    paths = write_plain_xml(dest=tmp_path)
    assert int(paths["node_count"]) > 40
    assert int(paths["edge_count"]) > 80
    assert float(paths["tick_s"]) == MICRO_TICK_S
    assert paths["net"].endswith("naperville.net.xml")
    assert "naperville.net.xml" in paths["netconvert"]
    assert (tmp_path / "naperville.nod.xml").exists()
    assert (tmp_path / "naperville.edg.xml").exists()
    assert (tmp_path / "naperville.typ.xml").exists()
    assert (tmp_path / "naperville.con.xml").exists()
    assert (tmp_path / "naperville.rou.xml").exists()
    assert (tmp_path / "naperville.sumocfg").exists()
    assert (tmp_path / "facilities.json").exists()
    cfg = ET.parse(tmp_path / "naperville.sumocfg").getroot()
    step = cfg.find("./time/step-length")
    assert step is not None and step.get("value") == "0.25"


def test_arterials_cap_at_45mph(tmp_path):
    paths = write_plain_xml(dest=tmp_path)
    root = ET.parse(paths["edges"]).getroot()
    for edge in root.findall("edge"):
        speed = float(edge.get("speed"))
        typ = edge.get("type") or ""
        if typ in {"motorway", "motorway_link"}:
            assert speed <= MOTORWAY_CAP_MPS + 0.05
        else:
            assert speed <= ARTERIAL_CAP_MPS + 0.05


def test_kennedy_real_zippers_fictional():
    spec = build_micro_spec()
    by_id = {f.id: f for f in spec.facilities}
    assert by_id["kennedy-revlac"].fictional is False
    assert by_id["kennedy-revlac"].kind == "revlac"
    assert by_id["i88-solarpunk"].fictional is True
    assert by_id["i88-solarpunk"].kind == "zipper"
    assert by_id["ogden-tidal"].fictional is True
    assert spec.nodes["z_i88_zip"].type == "zipper"
    assert spec.nodes["z_ogden_zip"].type == "zipper"
    assert spec.nodes["z_ken_w"].type == "priority"
    i88_len = sum(e.length for e in spec.edges.values() if e.id.startswith("z_i88_") and e.id.endswith("_eb") and not e.extra)
    assert i88_len > 7000


def test_install_hint_names_apt_and_docs():
    hint = install_hint()
    assert "apt-get" in hint
    assert "docs/SUMO.md" in hint
    assert "traci" in hint.lower()


def test_mock_traci_is_default_without_sumo():
    client = open_client(live=False)
    assert isinstance(client, MockTraCI)
    assert client.source == "mock"
    client.close()


def test_live_traci_raises_without_sumo():
    with pytest.raises(FileNotFoundError, match="Eclipse SUMO"):
        open_client(live=True)


def test_micro_loop_ticks_quarter_second_and_matches_ws():
    loop = MicroLoop(
        cfg=SimConfig(target_vehicles=24, spawn_per_s=12.0, enable_services=False, seed=3),
        live=False,
    )
    assert loop.cfg.dt == MICRO_TICK_S
    for _ in range(8):
        loop.step()
    assert abs(loop.t - 8 * MICRO_TICK_S) < 1e-9
    snap = loop.snapshot()
    loop.close()
    assert snap["tick_s"] == MICRO_TICK_S
    assert snap["ring"] == "micro"
    assert snap["source"] == "mock"
    assert WS_ROOT <= set(snap)
    assert snap["metrics"]["spawned"] >= 1
    assert isinstance(snap["vehicles"], list)
    if snap["vehicles"]:
        assert WS_VEHICLE <= set(snap["vehicles"][0])
        veh = snap["vehicles"][0]
        assert -89 < veh["lon"] < -87
        assert 41 < veh["lat"] < 43
    kennedy = next(f for f in snap["twin"]["lanes"] if f["id"] == "kennedy-revlac")
    assert kennedy["fictional"] is False
    ogden = next(f for f in snap["twin"]["lanes"] if f["id"] == "ogden-tidal")
    assert ogden["fictional"] is True
    live = parse_ws(snap)
    assert live.source == "mock"
    assert live.ring == "micro"
    assert live.tick_s == MICRO_TICK_S
    assert live.type == "snapshot"
    if live.vehicles:
        assert isinstance(live.vehicles[0].id, str)


def test_slot_pads_still_live_on_the_micro_loop():
    loop = MicroLoop(cfg=SimConfig(target_vehicles=8, spawn_per_s=4.0, enable_services=False), live=False)
    assert loop.managers
    sample = next(iter(loop.managers.values()))
    assert isinstance(sample, SlotManager) or hasattr(sample, "request")
    loop.close()


def test_mock_advances_at_posted_speed():
    spec = build_micro_spec()
    client = MockTraCI(spec=spec, cfg=SimConfig())
    edge = spec.edges["z_i88_w_eb"]
    assert client.add_vehicle("t1", ["z_i88_w_eb", "z_i88_e_eb"], "car", edge.speed)
    x0 = client.vehicles()[0]["x"]
    client.simulation_step(MICRO_TICK_S)
    x1 = client.vehicles()[0]["x"]
    client.close()
    assert abs((x1 - x0) - edge.speed * MICRO_TICK_S) < 1.0


def test_weekend_closes_revlac_extra_lanes():
    loop = MicroLoop(
        cfg=SimConfig(
            target_vehicles=4,
            spawn_per_s=2.0,
            enable_services=False,
            start_hour=8.0,
            start_weekday=5,
        ),
        live=False,
    )
    loop.step()
    closed = getattr(loop.client, "_closed", set())
    assert "z_ken_rev_ib" in closed
    assert "z_ken_rev_ob" in closed
    loop.close()
