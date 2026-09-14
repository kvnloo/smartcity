"""Approximate paid probe-speed products with open data + research curves.

INRIX / HERE / TomTom are gated. Chicago Traffic Tracker + OSM maxspeed + a
weekday diurnal (FHWA urban interstate shape) is good enough to drive a twin
until a civic license shows up.

StreetLight / Replica OD tables are gated. Census LODES + Metra boardings
+ IDOT AADT is the honest substitute.

Congestion-on-I-88 is the Naperville story: free-flow at 02:00, crawl 7:15.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from smartcity.config import ROOT

OPEN = ROOT / "data" / "open"

# Daily one-way work trips, district → district. Proxy for LODES until the
# LEHD files are ingested. Order of magnitude from ACS / Metra / AADT, not
# invented downtown fantasy.
LODES_PROXY_DAILY = {
    ("naperville", "loop"): 18500,
    ("naperville", "oakbrook"): 6200,
    ("naperville", "schaumburg"): 2100,
    ("aurora", "loop"): 14200,
    ("aurora", "naperville"): 4800,
    ("downers", "loop"): 7800,
    ("joliet", "loop"): 9100,
    ("schaumburg", "loop"): 6400,
    ("evanston", "loop"): 8900,
    ("hydepark", "loop"): 7200,
    ("ohare", "loop"): 4100,
    ("waukegan", "loop"): 5300,
    ("gary", "loop"): 4700,
    ("oakbrook", "loop"): 3900,
}


def diurnal_factor(minutes: int) -> float:
    """Travel-time multiplier. 1.0 = free flow. Peaks ~1.85 at 7:45 and 17:15."""
    hour = minutes / 60.0
    am = math.exp(-0.5 * ((hour - 7.75) / 0.85) ** 2)
    pm = math.exp(-0.5 * ((hour - 17.25) / 1.05) ** 2)
    midday = 0.12 * math.exp(-0.5 * ((hour - 12.2) / 1.4) ** 2)
    night = 0.04
    return 1.0 + 0.85 * am + 0.80 * pm + midday + night


def corridor_speed_mph(free_flow: float, minutes: int, incident: float = 0.0) -> float:
    tt = diurnal_factor(minutes) * (1.0 + incident)
    return max(8.0, free_flow / tt)


def _speeds_from_rows(rows: list) -> list[float]:
    speeds: list[float] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in ("current_speed", "speed", "avg_speed"):
            if key not in row:
                continue
            try:
                val = float(row[key])
            except (TypeError, ValueError):
                continue
            if 4.0 < val < 80.0:
                speeds.append(val)
            break
    return speeds


@lru_cache(maxsize=1)
def load_tracker_rows() -> tuple[dict, ...]:
    path = OPEN / "chicago_traffic_segments.json"
    if not path.exists():
        return tuple()
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return tuple()
    if isinstance(rows, list):
        return tuple(r for r in rows if isinstance(r, dict))
    return tuple()


def load_tracker_bias() -> float:
    """Nighttime city-street GPS should not yank interstate free-flow around.

    We only bias if the tracker mean is in a congested band (< 18 mph).
    """
    speeds = _speeds_from_rows(list(load_tracker_rows()))
    if len(speeds) < 5:
        return 1.0
    mean = sum(speeds) / len(speeds)
    if mean < 18.0:
        return min(1.35, 22.0 / max(mean, 8.0))
    return 1.0


def tracker_regions() -> list[dict]:
    cleaned = []
    for row in load_tracker_rows():
        try:
            west, east = float(row["_west"]), float(row["_east"])
            south, north = float(row["_south"]), float(row["_north"])
            speed = float(row.get("current_speed") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        if not (40 < south < 43 and 40 < north < 43):
            continue
        cleaned.append(
            {
                "id": str(row.get("_region_id", "")),
                "name": row.get("region"),
                "speed_mph": speed if speed > 4 else None,
                "west": west,
                "east": east,
                "south": south,
                "north": north,
            }
        )
    return cleaned


def region_speeds(minutes: int) -> list[dict]:
    bias = load_tracker_bias()
    specs = [
        ("i88", "I-88 Reagan", 55.0),
        ("i90", "I-90 Kennedy", 55.0),
        ("i290", "I-290 Eisenhower", 55.0),
        ("i55", "I-55 Stevenson", 55.0),
        ("i94", "I-94 Edens/Dan Ryan", 55.0),
        ("i94n", "I-94 Edens", 55.0),
        ("i94s", "I-94 Dan Ryan", 55.0),
        ("i294", "I-294 Tri-State", 55.0),
        ("ogden", "Ogden Avenue", 35.0),
        ("washington", "Washington Street", 30.0),
        ("metra-bnsf", "Metra BNSF", 70.0),
    ]
    out = []
    for cid, name, ff in specs:
        incident = 0.0
        mph = corridor_speed_mph(ff, minutes, incident=incident)
        if cid != "metra-bnsf" and bias > 1.0:
            mph = max(8.0, mph / bias)
        out.append(
            {
                "id": cid,
                "name": name,
                "free_flow_mph": ff,
                "speed_mph": round(mph, 1),
                "travel_time_index": round(ff / mph, 2),
                "source": "diurnal+tracker_bias" if bias != 1.0 else "diurnal_fhwa_shape",
            }
        )
    return out


def commute_od() -> list[dict]:
    """StreetLight-shaped OD without a StreetLight license."""
    rows = []
    for (orig, dest), daily in LODES_PROXY_DAILY.items():
        rows.append(
            {
                "from": orig,
                "to": dest,
                "daily_work_trips": daily,
                "source": "lodes_proxy",
            }
        )
    return rows


def peak_share(minutes: int, inbound: bool) -> float:
    """Fraction of daily OD happening in this hour, both directions split."""
    hour = minutes / 60.0
    if inbound:
        am = math.exp(-0.5 * ((hour - 7.6) / 0.9) ** 2)
        return 0.04 + 0.22 * am
    pm = math.exp(-0.5 * ((hour - 17.2) / 1.1) ** 2)
    return 0.04 + 0.20 * pm
