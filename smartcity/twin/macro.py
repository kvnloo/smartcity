"""Macro commute layer: district graph + Metra/I-88 flow.

This is the Cities: Skylines / POLARIS-lite ring. It does not draw every car.
It moves OD counts so Unreal and SUMO know where to spend micro budget.
"""

from __future__ import annotations

from smartcity.twin import demand, lanes
from smartcity.twin.region import CORRIDORS, DISTRICTS, RINGS

# Daily vehicles (both dirs) used when LODES pair is missing. AADT-ish / 1.2
# so we do not pretend every AADT vehicle is a Loop commute.
CORRIDOR_DAILY = {
    "i88": 52000,
    "i290": 48000,
    "i90": 70000,
    "i94s": 62000,
    "i94n": 40000,
    "i55": 45000,
    "i294": 38000,
    "ogden": 18000,
    "metra-bnsf": 22000,
}


def _facility_for_corridor(cor: dict, tidal: list[dict]) -> dict | None:
    if cor.get("tidal") == "kennedy":
        return next(f for f in tidal if f["id"] == "kennedy-revlac")
    if cor["id"] == "i88":
        return next(f for f in tidal if f["id"] == "i88-solarpunk")
    if cor.get("tidal") == "ogden":
        return next(f for f in tidal if f["id"] == "ogden-tidal")
    return None


def step_macro(sim_t: float, start_hour: float = 7.0, start_weekday: int = 0) -> dict:
    minutes = lanes.minutes_of_day(sim_t, start_hour)
    clock = lanes.snapshot(sim_t, start_hour, start_weekday)
    speeds = {row["id"]: row for row in demand.region_speeds(minutes)}
    od = {(r["from"], r["to"]): r["daily_work_trips"] for r in demand.commute_od()}
    flows = []
    for cor in CORRIDORS:
        sp = speeds.get(cor["id"], speeds.get("i88"))
        tti = sp["travel_time_index"] if sp else 1.3
        daily = CORRIDOR_DAILY.get(cor["id"], 20000)
        pair = od.get((cor["from"], cor["to"]), 0)
        daily = max(daily, int(pair * 1.35))
        inbound = daily * demand.peak_share(minutes, inbound=True)
        outbound = daily * demand.peak_share(minutes, inbound=False)
        if cor.get("mode") == "rail":
            tti = min(tti, 1.12)
        fac = _facility_for_corridor(cor, clock["facilities"])
        if fac:
            inbound *= fac["inbound_mult"]
            outbound *= fac["outbound_mult"]
        ff = (sp or {}).get("free_flow_mph") or cor.get("free_flow_mph") or 55
        minutes_travel = 60.0 * cor["km"] / 1.609 * tti / max(ff, 1)
        flows.append(
            {
                "id": cor["id"],
                "name": cor["name"],
                "from": cor["from"],
                "to": cor["to"],
                "mode": cor.get("mode", "road"),
                "km": cor["km"],
                "speed_mph": sp["speed_mph"] if sp else None,
                "tti": round(tti, 2),
                "inbound_vph": int(inbound),
                "outbound_vph": int(outbound),
                "minutes": round(minutes_travel, 1),
                "tidal": cor.get("tidal"),
            }
        )
    return {
        "clock": clock["clock"],
        "weekday_name": clock["weekday_name"],
        "weekend": clock["weekend"],
        "lanes": clock["facilities"],
        "districts": DISTRICTS,
        "corridors": flows,
        "od": demand.commute_od(),
        "fidelity": [
            {
                "name": r.name,
                "engine": r.engine,
                "radius_km": r.radius_km,
                "tick_s": r.tick_s,
                "notes": r.notes,
            }
            for r in RINGS
        ],
    }
