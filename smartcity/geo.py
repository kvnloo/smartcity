"""Local-metre <-> WGS84 helpers for Naperville (UTM 16N)."""

from __future__ import annotations

from pyproj import Transformer

_TO_LL = Transformer.from_crs("EPSG:32616", "EPSG:4326", always_xy=True)


def lonlat(origin_e: float, origin_n: float, x: float, y: float) -> tuple[float, float]:
    lon, lat = _TO_LL.transform(origin_e + x, origin_n + y)
    return float(lon), float(lat)
