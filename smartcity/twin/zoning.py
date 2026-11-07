"""Solarpunk land-use remap.

Municipal zoning is a legal overlay, not a mesh. We keep the source codes
and project them onto four living uses the Unreal layer can paint:

  dwell  — people sleep here
  grow   — food / canopy
  make   — repair, light industry, studios
  move   — rights of way, yards, stations
"""

from __future__ import annotations


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




