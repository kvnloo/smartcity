#!/usr/bin/env python3
"""Project Naperville OSM GeoJSON into a compact city.json for Blender.

Origin is the city centroid in UTM zone 16N (metres). Intersections are
derived from the road graph so slot-based AIM pads can be placed later.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import networkx as nx
from pyproj import Transformer
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon, shape
from shapely.ops import transform as shp_transform

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

HIGHWAY_WIDTH = {
    "motorway": 22.0,
    "motorway_link": 10.0,
    "trunk": 18.0,
    "trunk_link": 8.0,
    "primary": 14.0,
    "primary_link": 7.0,
    "secondary": 12.0,
    "secondary_link": 7.0,
    "tertiary": 10.0,
    "tertiary_link": 6.5,
    "unclassified": 7.0,
    "residential": 8.0,
    "living_street": 6.5,
    "service": 5.0,
    "track": 4.0,
    "footway": 2.0,
    "path": 2.0,
    "cycleway": 2.5,
    "pedestrian": 4.0,
    "steps": 2.0,
}

SKIP_HIGHWAYS = {
    "footway",
    "path",
    "steps",
    "cycleway",
    "bridleway",
    "corridor",
    "proposed",
    "construction",
    "abandoned",
    "platform",
    "raceway",
}

DRIVEABLE = {
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
    "tertiary",
    "tertiary_link",
    "unclassified",
    "residential",
    "living_street",
    "service",
}


def parse_speed_mph(raw: str | None) -> float | None:
    if not raw:
        return None
    text = str(raw).strip().lower()
    m = re.search(r"(\d+(\.\d+)?)", text)
    if not m:
        return None
    val = float(m.group(1))
    if "km" in text:
        return val * 0.621371
    return val


def parse_height_m(tags: dict[str, Any]) -> float:
    raw = tags.get("height")
    if raw:
        m = re.search(r"(\d+(\.\d+)?)", str(raw))
        if m:
            val = float(m.group(1))
            if "ft" in str(raw).lower() or "'" in str(raw):
                return val * 0.3048
            return val
    levels = tags.get("building:levels") or tags.get("levels")
    if levels:
        try:
            return max(3.2, float(str(levels).split(";")[0]) * 3.2)
        except ValueError:
            pass
    btype = str(tags.get("building") or "yes")
    defaults = {
        "house": 7.5,
        "detached": 7.5,
        "apartments": 14.0,
        "residential": 9.0,
        "commercial": 12.0,
        "retail": 10.0,
        "industrial": 11.0,
        "warehouse": 10.0,
        "school": 12.0,
        "church": 14.0,
        "garage": 4.0,
        "garages": 4.0,
        "shed": 3.0,
        "garage_detached": 4.0,
    }
    return defaults.get(btype, 8.5)


def parse_lanes(tags: dict[str, Any]) -> float | None:
    raw = tags.get("lanes")
    if not raw:
        return None
    try:
        return float(str(raw).split(";")[0].split("-")[0])
    except ValueError:
        return None


def road_width(tags: dict[str, Any]) -> float:
    lanes = parse_lanes(tags)
    hwy = tags.get("highway") or "residential"
    base = HIGHWAY_WIDTH.get(hwy, 7.0)
    if lanes:
        return max(base, lanes * 3.4 + 1.2)
    return base


def round_pts(coords: list[list[float]], nd: int = 2) -> list[list[float]]:
    return [[round(x, nd), round(y, nd)] for x, y in coords]


def geom_rings(geom) -> list[list[list[float]]]:
    rings: list[list[list[float]]] = []
    if geom.is_empty:
        return rings
    if isinstance(geom, Polygon):
        if geom.exterior and len(geom.exterior.coords) >= 4:
            rings.append(round_pts(list(geom.exterior.coords)))
    elif isinstance(geom, MultiPolygon):
        for g in geom.geoms:
            rings.extend(geom_rings(g))
    return rings


def geom_lines(geom) -> list[list[list[float]]]:
    lines: list[list[list[float]]] = []
    if geom.is_empty:
        return lines
    if isinstance(geom, LineString):
        coords = list(geom.coords)
        if len(coords) >= 2:
            lines.append(round_pts(coords))
    elif isinstance(geom, MultiLineString):
        for g in geom.geoms:
            lines.extend(geom_lines(g))
    elif isinstance(geom, (Polygon, MultiPolygon)):
        # water/park as polygons handled separately
        pass
    return lines


def load_fc(name: str) -> list[dict[str, Any]]:
    path = RAW / f"{name}.geojson"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("features") or []


def node_key(x: float, y: float, quant: float = 1.5) -> tuple[int, int]:
    return (int(round(x / quant)), int(round(y / quant)))


def heading_deg(p0: list[float], p1: list[float]) -> float:
    return (math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0])) + 360.0) % 360.0


def build_intersections(roads: list[dict[str, Any]], signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    graph = nx.Graph()
    for road in roads:
        coords = road["coords"]
        if len(coords) < 2:
            continue
        keys = [node_key(x, y) for x, y in coords]
        for i, key in enumerate(keys):
            if key not in graph:
                graph.add_node(key, x=coords[i][0], y=coords[i][1], roads=set())
            graph.nodes[key]["roads"].add(road["id"])
        for a, b in zip(keys, keys[1:]):
            if a != b:
                graph.add_edge(a, b)

    signal_keys = {node_key(s["x"], s["y"], quant=8.0) for s in signals}
    out: list[dict[str, Any]] = []
    for key, data in graph.nodes(data=True):
        deg = graph.degree(key)
        had_signals = key in signal_keys or any(
            node_key(data["x"], data["y"], 8.0) == sk for sk in list(signal_keys)[:0]
        )
        # snap signals by distance
        near_signal = False
        for s in signals:
            if (s["x"] - data["x"]) ** 2 + (s["y"] - data["y"]) ** 2 <= 18.0**2:
                near_signal = True
                break
        if deg < 3 and not near_signal:
            continue
        # arms
        arms = []
        for nbr in graph.neighbors(key):
            nd = graph.nodes[nbr]
            arms.append(
                {
                    "heading": round(heading_deg([data["x"], data["y"]], [nd["x"], nd["y"]]), 1),
                }
            )
        # radius from connected road widths
        widths = [r["width"] for r in roads if r["id"] in data["roads"]]
        radius = max(10.0, (max(widths) if widths else 8.0) * 1.15)
        out.append(
            {
                "id": f"x{key[0]}_{key[1]}",
                "x": round(data["x"], 2),
                "y": round(data["y"], 2),
                "degree": int(deg),
                "had_signals": near_signal,
                "radius": round(radius, 2),
                "arm_count": len(arms),
                "highway_count": len(data["roads"]),
            }
        )
    return out


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    boundary_fc = json.loads((RAW / "boundary.geojson").read_text(encoding="utf-8"))
    city_ll = shape(boundary_fc["geometry"])
    centroid = city_ll.centroid
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32616", always_xy=True)
    origin_e, origin_n = transformer.transform(centroid.x, centroid.y)

    def to_local(geom):
        def _xy(x, y, z=None):
            e, n = transformer.transform(x, y)
            return (e - origin_e, n - origin_n)

        return shp_transform(_xy, geom)

    city = to_local(city_ll)
    minx, miny, maxx, maxy = city.bounds

    roads: list[dict[str, Any]] = []
    for feat in load_fc("roads"):
        tags = feat.get("properties") or {}
        hwy = tags.get("highway")
        if hwy in SKIP_HIGHWAYS:
            continue
        geom = to_local(shape(feat["geometry"]))
        for coords in geom_lines(geom):
            if len(coords) < 2:
                continue
            length = LineString(coords).length
            if length < 4.0:
                continue
            roads.append(
                {
                    "id": int(tags.get("osm_id") or feat.get("id") or 0),
                    "name": tags.get("name"),
                    "highway": hwy,
                    "driveable": hwy in DRIVEABLE,
                    "width": round(road_width(tags), 2),
                    "maxspeed_mph": parse_speed_mph(tags.get("maxspeed")),
                    "bridge": tags.get("bridge") in {"yes", "true", "1"},
                    "coords": coords,
                    "length": round(length, 2),
                }
            )

    buildings: list[dict[str, Any]] = []
    for feat in load_fc("buildings"):
        tags = feat.get("properties") or {}
        geom = to_local(shape(feat["geometry"]))
        rings = geom_rings(geom)
        if not rings:
            continue
        poly = Polygon(rings[0])
        if not poly.is_valid:
            continue
        area = poly.area
        if area < 18.0:
            continue
        c = poly.centroid
        buildings.append(
            {
                "id": int(tags.get("osm_id") or feat.get("id") or 0),
                "type": tags.get("building") or "yes",
                "name": tags.get("name"),
                "height": round(parse_height_m(tags), 2),
                "area": round(area, 1),
                "cx": round(c.x, 2),
                "cy": round(c.y, 2),
                "rings": rings,
            }
        )

    def poly_features(name: str, kind: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for feat in load_fc(name):
            geom = to_local(shape(feat["geometry"]))
            tags = feat.get("properties") or {}
            rings = geom_rings(geom)
            if not rings:
                continue
            poly = Polygon(rings[0])
            if poly.area < 40:
                continue
            out.append(
                {
                    "id": int(tags.get("osm_id") or 0),
                    "kind": kind,
                    "name": tags.get("name"),
                    "rings": rings,
                    "area": round(poly.area, 1),
                }
            )
        return out

    water = poly_features("water", "water")
    parks = poly_features("parks", "park")

    signals: list[dict[str, Any]] = []
    for feat in load_fc("signals"):
        geom = to_local(shape(feat["geometry"]))
        if geom.is_empty:
            continue
        signals.append({"x": round(geom.x, 2), "y": round(geom.y, 2)})

    drive_roads = [r for r in roads if r["driveable"] and r["highway"] != "service"]
    intersections = build_intersections(driveable_priority(drive_roads, roads), signals)

    city_json = {
        "meta": {
            "name": "Naperville, Illinois",
            "crs": "EPSG:32616",
            "origin_lonlat": [round(centroid.x, 6), round(centroid.y, 6)],
            "origin_utm": [round(origin_e, 2), round(origin_n, 2)],
            "bbox_m": [round(minx, 1), round(miny, 1), round(maxx, 1), round(maxy, 1)],
            "boundary": round_pts(list(city.exterior.coords), 1),
            "counts": {
                "roads": len(roads),
                "buildings": len(buildings),
                "water": len(water),
                "parks": len(parks),
                "signals": len(signals),
                "intersections": len(intersections),
            },
        },
        "roads": roads,
        "buildings": buildings,
        "water": water,
        "parks": parks,
        "signals": signals,
        "intersections": intersections,
    }
    out = PROCESSED / "city.json"
    out.write_text(json.dumps(city_json), encoding="utf-8")
    print(json.dumps(city_json["meta"]["counts"], indent=2))
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")


def driveable_priority(drive_roads: list[dict[str, Any]], all_roads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if drive_roads:
        return drive_roads
    return [r for r in all_roads if r["driveable"]]


if __name__ == "__main__":
    main()
