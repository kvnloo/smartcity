"""Solarpunk land-use remap.

Municipal zoning is a legal overlay, not a mesh. We keep the source codes
and project them onto four living uses the Unreal layer can paint:

  dwell  — people sleep here
  grow   — food / canopy
  make   — repair, light industry, studios
  move   — rights of way, yards, stations
"""

from __future__ import annotations

import json
from pathlib import Path

from smartcity.config import ROOT

OPEN = ROOT / "data" / "open"

PREFIX_MAP = (
    ("POS", "grow"),
    ("PD", "dwell"),
    ("PMD", "make"),
    ("RS", "dwell"),
    ("RT", "dwell"),
    ("RM", "dwell"),
    ("B", "make"),
    ("C", "make"),
    ("M", "make"),
    ("T", "move"),
    ("SD", "dwell"),
)


def remap_zone(zone_class: str | None) -> str:
    raw = (zone_class or "").upper().replace(" ", "")
    for prefix, use in PREFIX_MAP:
        if raw.startswith(prefix):
            return use
    return "dwell"


def load_chicago_sample(limit: int = 80) -> list[dict]:
    path = OPEN / "chicago_zoning_sample.json"
    if not path.exists():
        return []
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(rows, list):
        return []
    out = []
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        zc = row.get("zone_class") or row.get("zone_type") or row.get("zoning_classification")
        out.append(
            {
                "zone_class": zc,
                "use": remap_zone(str(zc) if zc else ""),
                "ordinance": row.get("ordinance_num"),
            }
        )
    return out


def palette() -> dict[str, str]:
    return {
        "dwell": "#c4a574",
        "grow": "#6fa86a",
        "make": "#c4894a",
        "move": "#7eb6c9",
    }
