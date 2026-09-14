"""Street-light inventory: real poles where open, spacing model elsewhere.

Naperville publishes pole points. Chicago publishes 311 outages and says
~250,000 lights — the GIS inventory is gated. Approximate from highway
length and typical spacing rather than guessing a point cloud.
"""

from __future__ import annotations

import json
from pathlib import Path

from smartcity.config import ROOT

OPEN = ROOT / "data" / "open"

# CDOT public talking point.
CHICAGO_LIGHTS_OFFICIAL = 250_000

# One luminaire per this many metres of centerline (both sides averaged in).
SPACING_M = {
    "motorway": 90.0,
    "trunk": 55.0,
    "primary": 42.0,
    "secondary": 45.0,
    "tertiary": 48.0,
    "residential": 52.0,
    "unclassified": 55.0,
    "service": 70.0,
}


def _load_poles(path: Path, cap: int = 800) -> list[dict]:
    if not path.exists():
        return []
    try:
        fc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    poles = []
    for feat in fc.get("features") or []:
        geom = feat.get("geometry") or {}
        if geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        props = feat.get("properties") or {}
        poles.append(
            {
                "lon": coords[0],
                "lat": coords[1],
                "id": props.get("POLENUMBER"),
                "material": props.get("MATERIAL"),
                "subtype": props.get("SUBTYPE"),
            }
        )
        if len(poles) >= cap:
            break
    return poles


def approximate_from_lengths(length_by_highway: dict[str, float]) -> int:
    total = 0.0
    for hw, metres in length_by_highway.items():
        space = SPACING_M.get(hw, 55.0)
        total += metres / space
    return int(total)


def inventory(city=None) -> dict:
    poles = _load_poles(OPEN / "naperville_streetlights.geojson")
    outages = 0
    out_path = OPEN / "chicago_streetlights_out.json"
    if out_path.exists():
        try:
            rows = json.loads(out_path.read_text(encoding="utf-8"))
            outages = len(rows) if isinstance(rows, list) else 0
        except (OSError, json.JSONDecodeError):
            outages = 0
    approx = None
    if city is not None:
        lengths: dict[str, float] = {}
        for _u, _v, data in city.graph.edges(data=True):
            hw = str(data.get("highway") or "residential")
            lengths[hw] = lengths.get(hw, 0.0) + float(data.get("length") or 0.0)
        approx = approximate_from_lengths(lengths)
    return {
        "naperville_poles_loaded": len(poles),
        "naperville_poles": poles[:400],
        "naperville_spacing_model": approx,
        "chicago_inventory": CHICAGO_LIGHTS_OFFICIAL,
        "chicago_inventory_access": "gated",
        "chicago_311_outages_sample": outages,
        "solarpunk": {
            "note": "Replace always-on HPS with occupancy-dimmed canopy LEDs. Dark-sky at 1–6am except emergency corridors.",
            "dim_fraction_night": 0.35,
        },
    }
