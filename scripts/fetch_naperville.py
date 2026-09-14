#!/usr/bin/env python3
"""Download OpenStreetMap coverage for Naperville, Illinois.

Uses Overpass (with mirrors) and clips features to the city boundary.
Writes compact GeoJSON under data/raw/.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OSM_RELATION = 124885  # Naperville city boundary
AREA_ID = 3600000000 + OSM_RELATION

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "naperville-aim-city/1.0 (research)"})


def overpass(ql: str, timeout: int = 240) -> dict[str, Any]:
    last_err: Exception | None = None
    for url in OVERPASS_ENDPOINTS:
        try:
            print(f"  Overpass {url} …", flush=True)
            resp = SESSION.post(url, data={"data": ql}, timeout=timeout)
            if resp.status_code == 429:
                time.sleep(20)
                continue
            resp.raise_for_status()
            data = resp.json()
            n = len(data.get("elements", []))
            print(f"    {n} elements", flush=True)
            return data
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print(f"    failed: {exc}", flush=True)
            time.sleep(4)
    raise RuntimeError(f"All Overpass endpoints failed: {last_err}")


def way_coords(el: dict[str, Any]) -> list[list[float]]:
    geom = el.get("geometry") or []
    return [[pt["lon"], pt["lat"]] for pt in geom if "lon" in pt and "lat" in pt]


def relation_polygons(el: dict[str, Any]) -> list[Polygon]:
    """Rebuild polygons from out-geom members (outer/inner)."""
    outers: list[list[list[float]]] = []
    inners: list[list[list[float]]] = []
    for mem in el.get("members") or []:
        if mem.get("type") != "way" or "geometry" not in mem:
            continue
        coords = [[p["lon"], p["lat"]] for p in mem["geometry"]]
        if len(coords) < 4:
            continue
        role = mem.get("role") or "outer"
        (outers if role != "inner" else inners).append(coords)
    polys: list[Polygon] = []
    for outer in outers:
        poly = Polygon(outer)
        if not poly.is_valid:
            poly = make_valid(poly)
        if poly.is_empty:
            continue
        for inner in inners:
            hole = Polygon(inner)
            if hole.is_valid and poly.contains(hole.representative_point()):
                try:
                    poly = poly.difference(hole)
                except Exception:
                    pass
        if isinstance(poly, Polygon) and not poly.is_empty:
            polys.append(poly)
        elif isinstance(poly, MultiPolygon):
            polys.extend([p for p in poly.geoms if isinstance(p, Polygon)])
    return polys


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    mb = path.stat().st_size / 1e6
    print(f"  wrote {path.relative_to(ROOT)} ({mb:.1f} MB)", flush=True)


def boundary_polygon() -> tuple[Polygon, dict[str, float]]:
    print("Fetching city boundary…", flush=True)
    data = overpass(
        f"[out:json][timeout:90]; rel({OSM_RELATION}); out geom;",
        timeout=120,
    )
    save_json(RAW / "boundary.osm.json", data)
    els = data.get("elements") or []
    if not els:
        raise RuntimeError("No Naperville boundary returned")
    rel = els[0]
    polys = relation_polygons(rel)
    if not polys:
        raise RuntimeError("Could not rebuild Naperville polygon")
    geom = unary_union(polys)
    if isinstance(geom, MultiPolygon):
        geom = max(geom.geoms, key=lambda g: g.area)
    minx, miny, maxx, maxy = geom.bounds
    bbox = {
        "south": miny - 0.002,
        "west": minx - 0.002,
        "north": maxy + 0.002,
        "east": maxx + 0.002,
    }
    save_json(
        RAW / "boundary.geojson",
        {
            "type": "Feature",
            "properties": {
                "name": rel.get("tags", {}).get("name", "Naperville"),
                "osm_relation": OSM_RELATION,
                "bbox": bbox,
            },
            "geometry": json.loads(json.dumps(geom.__geo_interface__)),
        },
    )
    return geom, bbox


def fetch_layer(name: str, ql: str, timeout: int = 240) -> dict[str, Any]:
    print(f"Fetching {name}…", flush=True)
    data = overpass(ql, timeout=timeout)
    save_json(RAW / f"{name}.osm.json", data)
    return data


def elements_to_features(
    elements: list[dict[str, Any]],
    city: Polygon,
    kind: str,
) -> list[dict[str, Any]]:
    feats: list[dict[str, Any]] = []
    for el in elements:
        tags = el.get("tags") or {}
        etype = el.get("type")
        geom = None
        if etype == "node":
            pt = Point(el["lon"], el["lat"])
            if not city.covers(pt):
                continue
            geom = pt
        elif etype == "way":
            coords = way_coords(el)
            if len(coords) < 2:
                continue
            closed = len(coords) >= 4 and coords[0] == coords[-1]
            if kind in {"building", "water", "park", "landuse"} and closed:
                poly = Polygon(coords)
                if not poly.is_valid:
                    poly = make_valid(poly)
                if poly.is_empty:
                    continue
                geom = poly
            else:
                geom = LineString(coords)
            if not geom.intersects(city):
                continue
            geom = geom.intersection(city)
            if geom.is_empty:
                continue
        elif etype == "relation" and kind in {"building", "water", "park"}:
            polys = relation_polygons(el)
            if not polys:
                continue
            geom = unary_union(polys)
            if not geom.intersects(city):
                continue
            geom = geom.intersection(city)
            if geom.is_empty:
                continue
        else:
            continue
        feats.append(
            {
                "type": "Feature",
                "id": el.get("id"),
                "properties": {
                    "osm_id": el.get("id"),
                    "osm_type": etype,
                    **{k: v for k, v in tags.items() if k in KEEP_TAGS},
                },
                "geometry": json.loads(json.dumps(geom.__geo_interface__)),
            }
        )
    return feats


KEEP_TAGS = {
    "name",
    "highway",
    "lanes",
    "maxspeed",
    "oneway",
    "bridge",
    "tunnel",
    "layer",
    "building",
    "building:levels",
    "height",
    "roof:levels",
    "amenity",
    "landuse",
    "leisure",
    "natural",
    "water",
    "waterway",
    "crossing",
    "traffic_signals",
}


def bbox_clause(bbox: dict[str, float]) -> str:
    return f'{bbox["south"]},{bbox["west"]},{bbox["north"]},{bbox["east"]}'


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    city, bbox = boundary_polygon()
    bb = bbox_clause(bbox)

    highways = fetch_layer(
        "highways",
        f"[out:json][timeout:180]; way[highway]({bb}); out geom;",
        timeout=240,
    )
    buildings = fetch_layer(
        "buildings",
        f"""[out:json][timeout:240];
        (
          way["building"]({bb});
          rel["building"]({bb});
        );
        out geom;""",
        timeout=300,
    )
    water = fetch_layer(
        "water",
        f"""[out:json][timeout:120];
        (
          way["natural"="water"]({bb});
          rel["natural"="water"]({bb});
          way["waterway"~"river|stream|canal|riverbank"]({bb});
          way["landuse"="reservoir"]({bb});
        );
        out geom;""",
        timeout=180,
    )
    parks = fetch_layer(
        "parks",
        f"""[out:json][timeout:120];
        (
          way["leisure"~"park|garden|golf_course|pitch|playground"]({bb});
          rel["leisure"~"park|garden|golf_course"]({bb});
          way["landuse"="grass"]({bb});
        );
        out geom;""",
        timeout=180,
    )
    signals = fetch_layer(
        "signals",
        f"""[out:json][timeout:90];
        (
          node["highway"="traffic_signals"]({bb});
          node["crossing"="traffic_signals"]({bb});
        );
        out;""",
        timeout=120,
    )

    layers = {
        "roads": elements_to_features(highways.get("elements") or [], city, "road"),
        "buildings": elements_to_features(buildings.get("elements") or [], city, "building"),
        "water": elements_to_features(water.get("elements") or [], city, "water"),
        "parks": elements_to_features(parks.get("elements") or [], city, "park"),
        "signals": elements_to_features(signals.get("elements") or [], city, "signal"),
    }
    manifest = {
        "city": "Naperville, Illinois",
        "osm_relation": OSM_RELATION,
        "fetched_at": started,
        "bbox": bbox,
        "counts": {k: len(v) for k, v in layers.items()},
    }
    for name, feats in layers.items():
        save_json(
            RAW / f"{name}.geojson",
            {"type": "FeatureCollection", "features": feats},
        )
    save_json(RAW / "manifest.json", manifest)
    print("Manifest:", json.dumps(manifest["counts"], indent=2))


if __name__ == "__main__":
    main()
