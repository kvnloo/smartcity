"""Load processed Naperville city.json and build a driveable routing graph."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx

from smartcity.config import CITY_JSON, HIGHWAY_SPEED_MPH, MPH_TO_MPS


def _dist(a: list[float], b: list[float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _heading(a: list[float], b: list[float]) -> float:
    return (math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) + 360.0) % 360.0


@dataclass
class Intersection:
    id: str
    x: float
    y: float
    radius: float
    degree: int
    had_signals: bool
    arms: list[float] = field(default_factory=list)


@dataclass
class CityModel:
    meta: dict[str, Any]
    graph: nx.DiGraph
    intersections: dict[str, Intersection]
    roads: list[dict[str, Any]]
    buildings: list[dict[str, Any]]
    parks: list[dict[str, Any]]
    water: list[dict[str, Any]]
    signals: list[dict[str, Any]]
    origin_utm: tuple[float, float]

    @property
    def bbox_m(self) -> list[float]:
        return list(self.meta["bbox_m"])


def load_city(path: Path | None = None) -> CityModel:
    raw = json.loads((path or CITY_JSON).read_text(encoding="utf-8"))
    meta = raw["meta"]
    origin = tuple(meta["origin_utm"])
    intersections = {
        ix["id"]: Intersection(
            id=ix["id"],
            x=ix["x"],
            y=ix["y"],
            radius=float(ix.get("radius") or 12.0),
            degree=int(ix.get("degree") or 0),
            had_signals=bool(ix.get("had_signals")),
        )
        for ix in raw["intersections"]
    }
    graph = _build_graph(raw["roads"], intersections)
    _annotate_arms(graph, intersections)
    return CityModel(
        meta=meta,
        graph=graph,
        intersections=intersections,
        roads=raw["roads"],
        buildings=raw["buildings"],
        parks=raw["parks"],
        water=raw["water"],
        signals=raw["signals"],
        origin_utm=(float(origin[0]), float(origin[1])),
    )


def _nearest_ix(
    pt: list[float],
    intersections: dict[str, Intersection],
    max_d: float | None = None,
) -> Intersection | None:
    best: Intersection | None = None
    best_d = 1e9
    for ix in intersections.values():
        d = math.hypot(pt[0] - ix.x, pt[1] - ix.y)
        if d < best_d:
            best_d = d
            best = ix
    limit = max_d if max_d is not None else (max(24.0, best.radius * 1.8) if best else 24.0)
    if best is None or best_d > limit:
        return None
    return best


def _ensure_node(
    graph: nx.DiGraph,
    intersections: dict[str, Intersection],
    pt: list[float],
) -> str:
    hit = _nearest_ix(pt, intersections)
    if hit is not None:
        if hit.id not in graph:
            graph.add_node(hit.id, x=hit.x, y=hit.y, kind="intersection")
        return hit.id
    nid = f"n{int(round(pt[0]))}_{int(round(pt[1]))}"
    if nid not in graph:
        graph.add_node(nid, x=pt[0], y=pt[1], kind="joint")
        intersections[nid] = Intersection(
            id=nid, x=pt[0], y=pt[1], radius=8.0, degree=1, had_signals=False
        )
    return nid


def _build_graph(roads: list[dict[str, Any]], intersections: dict[str, Intersection]) -> nx.DiGraph:
    graph: nx.DiGraph = nx.DiGraph()
    for ix in intersections.values():
        graph.add_node(ix.id, x=ix.x, y=ix.y, kind="intersection")

    edge_i = 0
    for road in roads:
        if not road.get("driveable"):
            continue
        coords: list[list[float]] = road["coords"]
        if len(coords) < 2:
            continue
        speed = (road.get("maxspeed_mph") or HIGHWAY_SPEED_MPH.get(road.get("highway"), 25.0)) * MPH_TO_MPS
        width = float(road["width"])
        start_id = _ensure_node(graph, intersections, coords[0])
        bucket: list[list[float]] = [coords[0]]
        for pt in coords[1:]:
            bucket.append(pt)
            hit = _nearest_ix(pt, intersections, max_d=22.0)
            near_end = hit is not None and hit.id != start_id
            if not near_end:
                continue
            _add_edge_ids(graph, start_id, hit.id, bucket, road, speed, width, edge_i)
            edge_i += 1
            start_id = hit.id
            bucket = [pt]
        end_id = _ensure_node(graph, intersections, coords[-1])
        if end_id != start_id and len(bucket) >= 2:
            _add_edge_ids(graph, start_id, end_id, bucket, road, speed, width, edge_i)
            edge_i += 1

    isolated = [n for n, d in graph.degree() if d == 0]
    graph.remove_nodes_from(isolated)
    return graph


def _add_edge_ids(
    graph: nx.DiGraph,
    a_id: str,
    b_id: str,
    coords: list[list[float]],
    road: dict[str, Any],
    speed: float,
    width: float,
    edge_i: int,
) -> None:
    if a_id == b_id:
        return
    ax, ay = graph.nodes[a_id]["x"], graph.nodes[a_id]["y"]
    bx, by = graph.nodes[b_id]["x"], graph.nodes[b_id]["y"]
    a = Intersection(a_id, ax, ay, 10.0, 0, False)
    b = Intersection(b_id, bx, by, 10.0, 0, False)
    _add_edge(graph, a, b, coords, road, speed, width, edge_i)


def _add_edge(
    graph: nx.DiGraph,
    a: Intersection,
    b: Intersection,
    coords: list[list[float]],
    road: dict[str, Any],
    speed: float,
    width: float,
    edge_i: int,
) -> None:
    if a.id == b.id:
        return
    length = sum(_dist(coords[i], coords[i + 1]) for i in range(len(coords) - 1))
    if length < 8.0:
        return
    heading = _heading(coords[0], coords[-1])
    key = f"e{edge_i}"
    graph.add_edge(
        a.id,
        b.id,
        id=key,
        coords=coords,
        length=length,
        speed=speed,
        width=width,
        highway=road.get("highway"),
        name=road.get("name"),
        heading=heading,
    )
    graph.add_edge(
        b.id,
        a.id,
        id=f"{key}r",
        coords=list(reversed(coords)),
        length=length,
        speed=speed,
        width=width,
        highway=road.get("highway"),
        name=road.get("name"),
        heading=_heading(coords[-1], coords[0]),
    )


def _annotate_arms(graph: nx.DiGraph, intersections: dict[str, Intersection]) -> None:
    for nid, ix in intersections.items():
        if nid not in graph:
            continue
        headings = []
        for _, _, data in graph.out_edges(nid, data=True):
            headings.append(float(data["heading"]))
        ix.arms = headings
        ix.degree = graph.degree(nid) // 2
