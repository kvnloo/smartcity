"""Tidal lanes, diurnal demand, nested fidelity, catalog."""

from smartcity.adapters.sumo import write_plain_xml
from smartcity.twin.catalog import summary
from smartcity.twin.demand import diurnal_factor
from smartcity.twin.lanes import KENNEDY, I88_GREEN, capacity_multiplier, direction, snapshot
from smartcity.twin.layers import overlay_geojson
from smartcity.twin.macro import step_macro
from smartcity.twin.region import fidelity_for_distance_km
from smartcity.twin.zoning import remap_zone


def test_kennedy_inbound_morning_monday():
    assert direction(KENNEDY, 8 * 60, weekday=0) == "inbound"
    assert direction(KENNEDY, 13 * 60, weekday=0) == "outbound"
    assert direction(KENNEDY, 23 * 60 + 30, weekday=0) == "inbound"
    assert direction(KENNEDY, 12 * 60 + 30, weekday=0) == "outbound"


def test_kennedy_friday_flips_later():
    assert direction(KENNEDY, 13 * 60, weekday=4) == "inbound"
    assert direction(KENNEDY, 13 * 60 + 30, weekday=4) == "outbound"


def test_i88_programmable_spine_morning_only():
    assert direction(I88_GREEN, 7 * 60, weekday=0) == "inbound"
    assert direction(I88_GREEN, 11 * 60, weekday=0) == "outbound"
    assert capacity_multiplier(I88_GREEN, 7 * 60, "inbound", 0) > 1.0
    assert capacity_multiplier(I88_GREEN, 7 * 60, "outbound", 0) < 1.0


def test_weekend_idles_extra_lanes():
    assert capacity_multiplier(KENNEDY, 8 * 60, "inbound", weekday=5) == 1.0
    snap = snapshot(0.0, start_hour=8.0, start_weekday=5)
    assert snap["weekend"] is True
    kennedy = next(f for f in snap["facilities"] if f["id"] == "kennedy-revlac")
    assert kennedy["extra_lanes"] == 0


def test_diurnal_peaks_am_and_is_quiet_at_night():
    am = diurnal_factor(int(7.75 * 60))
    night = diurnal_factor(3 * 60)
    assert am > 1.5
    assert night < 1.15
    assert am > night


def test_macro_morning_inbound_exceeds_outbound():
    twin = step_macro(0.0, start_hour=7.5, start_weekday=0)
    i88 = next(c for c in twin["corridors"] if c["id"] == "i88")
    assert i88["inbound_vph"] > i88["outbound_vph"]
    assert twin["clock"] == "07:30"
    kennedy = next(f for f in twin["lanes"] if f["id"] == "kennedy-revlac")
    assert kennedy["direction"] == "inbound"


def test_nested_fidelity_rings():
    assert fidelity_for_distance_km(0.4).name == "hero"
    assert fidelity_for_distance_km(5).name == "micro"
    assert fidelity_for_distance_km(20).name == "meso"
    assert fidelity_for_distance_km(80).name == "macro"


def test_catalog_marks_paid_probe_data():
    cat = summary()
    ids = {d["id"] for d in cat["datasets"]}
    assert "inrix-speeds" in ids
    assert "osm-highways" in ids
    assert cat["counts"].get("paid", 0) >= 1
    paid = {p["id"] for p in cat["paid_approximations"]}
    assert "inrix-speeds" in paid


def test_solarpunk_zone_remap():
    assert remap_zone("RS-3") == "dwell"
    assert remap_zone("M1-1") == "make"
    assert remap_zone("POS-1") == "grow"


def test_overlay_has_corridors_and_rings():
    geo = overlay_geojson(0.0, start_hour=7.5)
    assert len(geo["corridors"]["features"]) >= 6
    assert len(geo["districts"]["features"]) == 12
    assert len(geo["rings"]["features"]) == 4
    assert geo["twin"]["clock"] == "07:30"


def test_sumo_plain_xml_writes():
    paths = write_plain_xml()
    assert int(paths["node_count"]) > 40
