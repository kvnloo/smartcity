"""City-scale simulator: vehicles + per-intersection managers from the papers."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import networkx as nx

from smartcity.config import (
    CROSSING_MPH,
    CRUISE_CAP_MPH,
    DEFAULT_ACCEL,
    DEFAULT_DECEL,
    MPH_TO_MPS,
    SimConfig,
)
from smartcity.geo import lonlat
from smartcity.model import CityModel, load_city
from smartcity.services import LaborLedger, ServiceBus
from smartcity.slots import make_manager, movement_key
from smartcity.twin.demand import diurnal_factor
from smartcity.twin.lanes import minutes_of_day
from smartcity.twin.macro import step_macro

CROSS_MPS = CROSSING_MPH * MPH_TO_MPS
CRUISE_CAP_MPS = CRUISE_CAP_MPH * MPH_TO_MPS


def _interp(coords: list[list[float]], s: float) -> tuple[float, float, float]:
    remain = s
    for i in range(len(coords) - 1):
        x0, y0 = coords[i]
        x1, y1 = coords[i + 1]
        seg = math.hypot(x1 - x0, y1 - y0)
        if remain <= seg or i == len(coords) - 2:
            t = 0 if seg < 1e-6 else min(1.0, remain / seg)
            heading = math.degrees(math.atan2(y1 - y0, x1 - x0)) % 360.0
            return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, heading
        remain -= seg
    x, y = coords[-1]
    return x, y, 0.0


@dataclass
class Vehicle:
    id: int
    kind: str
    nodes: list[str]
    u: str
    v: str
    s: float
    speed: float
    v_max: float
    spawned_t: float
    x: float = 0.0
    y: float = 0.0
    heading: float = 0.0
    reserved_t: float | None = None
    reserved_node: str | None = None
    movement: str | None = None
    delay_s: float = 0.0
    stops: int = 0
    energy: float = 0.0
    done: bool = False
    dest: str = ""
    occupancy: float = 1.15


@dataclass
class SimStats:
    t: float = 0.0
    spawned: int = 0
    completed: int = 0
    active: int = 0
    delay_s: float = 0.0
    stops: int = 0
    energy: float = 0.0
    grants: int = 0
    mean_speed_mph: float = 0.0
    lights_equivalent_delay_s: float = 0.0


class CitySim:
    def __init__(self, city: CityModel | None = None, cfg: SimConfig | None = None):
        self.cfg = cfg or SimConfig()
        self.city = city or load_city()
        self.rng = random.Random(self.cfg.seed)
        self.t = 0.0
        self._vid = 1
        self.vehicles: dict[int, Vehicle] = {}
        self.managers = {
            nid: make_manager(self.cfg.policy, self.cfg.batch_n, self.cfg.batch_delay_trigger_s)
            for nid in self.city.graph.nodes
        }
        self.services = ServiceBus(
            pedestrian_cycle_s=self.cfg.pedestrian_cycle_s,
            pedestrian_window_s=self.cfg.pedestrian_window_s,
        )
        n_sig = sum(1 for ix in self.city.intersections.values() if ix.had_signals)
        self.labor = LaborLedger(signalized_intersections=max(n_sig, 1))
        self.stats = SimStats()
        self.nodes = [n for n in self.city.graph.nodes if self.city.graph.degree(n) >= 2]
        if len(self.nodes) < 8:
            self.nodes = list(self.city.graph.nodes)
        self._spawn_acc = 0.0
        self._ped_on = False
        self._twin = step_macro(0.0, self.cfg.start_hour, self.cfg.start_weekday)

    def reset(self, cfg: SimConfig | None = None) -> None:
        if cfg:
            self.cfg = cfg
        self.__init__(self.city, self.cfg)

    def step(self) -> None:
        dt = self.cfg.dt
        self.t += dt
        self._twin = step_macro(self.t, self.cfg.start_hour, self.cfg.start_weekday)
        self._spawn(dt)
        if self.cfg.enable_services and self.cfg.policy != "lights":
            self._service_holds()
        speeds = []
        for veh in list(self.vehicles.values()):
            if veh.done:
                continue
            self._drive(veh, dt)
            if not veh.done:
                speeds.append(veh.speed)
        self.stats.t = self.t
        self.stats.active = sum(1 for v in self.vehicles.values() if not v.done)
        self.stats.mean_speed_mph = (sum(speeds) / max(1, len(speeds))) / MPH_TO_MPS
        self.stats.grants = sum(getattr(m, "granted", 0) for m in self.managers.values())

    def snapshot(self) -> dict:
        oe, on = self.city.origin_utm
        vehicles = []
        for v in self.vehicles.values():
            if v.done:
                continue
            lon, lat = lonlat(oe, on, v.x, v.y)
            vehicles.append(
                {
                    "id": str(v.id),
                    "kind": v.kind,
                    "lon": round(lon, 6),
                    "lat": round(lat, 6),
                    "x_m": round(v.x, 2),
                    "y_m": round(v.y, 2),
                    "speed_mph": round(v.speed / MPH_TO_MPS, 1),
                    "heading": round(v.heading, 1),
                }
            )
        intersections = []
        for nid, ix in self.city.intersections.items():
            if nid not in self.managers:
                continue
            lon, lat = lonlat(oe, on, ix.x, ix.y)
            mgr = self.managers[nid]
            pending = len(getattr(mgr, "reservations", []) or getattr(mgr, "occ", {}) )
            intersections.append(
                {
                    "id": nid,
                    "lon": round(lon, 6),
                    "lat": round(lat, 6),
                    "x_m": round(ix.x, 2),
                    "y_m": round(ix.y, 2),
                    "had_signals": ix.had_signals,
                    "degree": ix.degree,
                    "pending": int(pending) if not isinstance(pending, int) else pending,
                    "grants": getattr(mgr, "granted", 0),
                }
            )
        delay_saved = max(0.0, self.stats.completed * 18.0 - self.stats.delay_s) if self.cfg.policy != "lights" else 0.0
        return {
            "type": "snapshot",
            "t": round(self.t, 2),
            "policy": self.cfg.policy,
            "vehicles": vehicles,
            "intersections": intersections,
            "metrics": {
                "active": self.stats.active,
                "spawned": self.stats.spawned,
                "completed": self.stats.completed,
                "mean_speed_mph": round(self.stats.mean_speed_mph, 1),
                "delay_s": round(self.stats.delay_s, 1),
                "stops": self.stats.stops,
                "energy": round(self.stats.energy, 1),
                "grants": self.stats.grants,
                "mean_delay_s": round(self.stats.delay_s / max(1, self.stats.completed), 2),
            },
            "services": {
                "buses": self.services.buses,
                "emergencies": self.services.emergencies,
                "deliveries": self.services.deliveries,
                "events": self.services.events,
            },
            "labor": self.labor.yearly(delay_saved, self.stats.completed),
            "twin": self._twin,
        }

    def city_layers(self) -> dict:
        oe, on = self.city.origin_utm
        def line(coords):
            return [list(lonlat(oe, on, x, y)) for x, y in coords]

        roads = []
        for u, v, data in self.city.graph.edges(data=True):
            if data["id"].endswith("r"):
                continue
            roads.append(
                {
                    "type": "Feature",
                    "properties": {"name": data.get("name"), "highway": data.get("highway")},
                    "geometry": {"type": "LineString", "coordinates": line(data["coords"])},
                }
            )
        buildings = []
        for b in self.city.buildings:
            ring = line(b["rings"][0])
            buildings.append(
                {
                    "type": "Feature",
                    "properties": {"height": b["height"], "type": b["type"]},
                    "geometry": {"type": "Polygon", "coordinates": [ring]},
                }
            )
        return {
            "origin_lonlat": self.city.meta["origin_lonlat"],
            "origin_utm": list(self.city.origin_utm),
            "crs": self.city.meta.get("crs", "EPSG:32616"),
            "bbox_m": self.city.meta["bbox_m"],
            "counts": self.city.meta["counts"],
            "roads": {"type": "FeatureCollection", "features": roads},
            "buildings": {"type": "FeatureCollection", "features": buildings[:1800]},
        }

    def _spawn(self, dt: float) -> None:
        kinds = ["car"]
        if self.cfg.enable_services:
            kinds.extend(self.services.pop_spawns(self.t))
        tti = 1.3
        i88 = next((c for c in (self._twin or {}).get("corridors", []) if c["id"] == "i88"), None)
        if i88 and i88.get("tti"):
            tti = float(i88["tti"])
        minutes = minutes_of_day(self.t, self.cfg.start_hour)
        di = diurnal_factor(minutes)
        rate = self.cfg.spawn_per_s * (0.50 + 0.28 * di) * min(1.55, 0.72 + 0.28 * tti)
        self._spawn_acc += rate * dt
        n = int(self._spawn_acc)
        self._spawn_acc -= n
        want = n + len([k for k in kinds if k != "car"])
        active = self.stats.active
        for extra in kinds:
            if extra == "car":
                continue
            self._spawn_one(extra)
        for _ in range(n):
            if active + want >= self.cfg.target_vehicles:
                break
            self._spawn_one("car")
            active += 1

    def _spawn_one(self, kind: str) -> None:
        g = self.city.graph
        if len(self.nodes) < 2:
            return
        src = self.rng.choice(self.nodes)
        dests = list(nx.descendants(g, src))
        if not dests:
            return
        dest = self.rng.choice(dests)
        try:
            path = nx.shortest_path(g, src, dest, weight="length")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return
        if len(path) < 2:
            return
        u, v = path[0], path[1]
        data = g[u][v]
        vmax = min(CRUISE_CAP_MPS, float(data["speed"]))
        if kind == "bus":
            vmax = min(vmax, 16.0)
        if kind == "delivery":
            vmax = min(vmax, 12.0)
        if kind == "emergency":
            vmax = min(CRUISE_CAP_MPS, vmax * 1.15)
        x, y, h = _interp(data["coords"], 0.0)
        vid = self._vid
        self._vid += 1
        occ = {"car": 1.15, "bus": 18.0, "emergency": 1.5, "delivery": 1.0}[kind]
        self.vehicles[vid] = Vehicle(
            id=vid,
            kind=kind,
            nodes=path,
            u=u,
            v=v,
            s=0.0,
            speed=vmax * 0.85,
            v_max=vmax,
            spawned_t=self.t,
            x=x,
            y=y,
            heading=h,
            dest=dest,
            occupancy=occ,
        )
        self.stats.spawned += 1

    def _service_holds(self) -> None:
        active = self.services.pedestrian_window_open(self.t)
        if active and not self._ped_on:
            for nid, ix in self.city.intersections.items():
                if ix.had_signals and nid in self.managers:
                    self.managers[nid].request(-1, "__PED__", self.t, kind="pedestrian", now=self.t)
            self._ped_on = True
            self.services.pedestrian_holds += 1
        if active and not self._ped_on:
            for nid, ix in self.city.intersections.items():
                if ix.had_signals and nid in self.managers:
                    self.managers[nid].request(-1, "__PED__", self.t, kind="pedestrian", now=self.t)
            self._ped_on = True
        elif not active:
            self._ped_on = False

    def _drive(self, veh: Vehicle, dt: float) -> None:
        g = self.city.graph
        if not g.has_edge(veh.u, veh.v):
            veh.done = True
            return
        data = g[veh.u][veh.v]
        length = float(data["length"])
        remain = max(0.0, length - veh.s)
        self._maybe_reserve(veh, remain, data)
        v_cmd = self._speed_command(veh, remain)
        accel = max(-DEFAULT_DECEL, min(DEFAULT_ACCEL, (v_cmd - veh.speed) / dt))
        new_speed = max(0.0, veh.speed + accel * dt)
        if veh.speed > 1.2 and new_speed < 0.4:
            veh.stops += 1
            self.stats.stops += 1
        veh.energy += (abs(accel) * dt) + (0.35 * dt if new_speed < 0.5 else 0.0)
        self.stats.energy += abs(accel) * dt
        veh.speed = new_speed
        veh.s += veh.speed * dt
        ff = min(veh.v_max, CRUISE_CAP_MPS)
        if veh.speed < ff * 0.85:
            extra = dt * (1.0 - veh.speed / max(ff, 0.1))
            veh.delay_s += extra
            self.stats.delay_s += extra * veh.occupancy
        if veh.s >= length - 0.05:
            self._advance_edge(veh)
            return
        veh.x, veh.y, veh.heading = _interp(data["coords"], veh.s)

    def _maybe_reserve(self, veh: Vehicle, remain: float, data: dict) -> None:
        lookahead = max(40.0, veh.v_max * 6.0)
        if remain > lookahead:
            return
        if veh.reserved_node == veh.v:
            return
        path = veh.nodes
        try:
            i = path.index(veh.v)
        except ValueError:
            return
        in_h = float(data["heading"])
        if i + 1 < len(path) and self.city.graph.has_edge(veh.v, path[i + 1]):
            out_h = float(self.city.graph[veh.v][path[i + 1]]["heading"])
        else:
            out_h = in_h
        movement = movement_key(in_h, out_h)
        if veh.kind == "emergency":
            movement = movement  # still a geometric movement; priority is the kind
        earliest = self.t + remain / max(veh.speed, CROSS_MPS * 0.5)
        mgr = self.managers.get(veh.v)
        if mgr is None:
            return
        t_slot = mgr.request(veh.id, movement, earliest, kind=veh.kind, now=self.t)
        veh.reserved_t = t_slot
        veh.reserved_node = veh.v
        veh.movement = movement

    def _speed_command(self, veh: Vehicle, remain: float) -> float:
        v_cap = min(veh.v_max, CRUISE_CAP_MPS)
        if veh.reserved_t is None:
            return v_cap
        t_remain = veh.reserved_t - self.t
        if t_remain <= 0.05:
            return min(v_cap, CROSS_MPS if remain < 40 else v_cap)
        v_need = remain / t_remain
        if self.cfg.policy == "lights":
            return max(0.0, min(v_cap, v_need))
        # Tachet "slower is faster": bleed speed early, avoid a full stop.
        v_min = 2.2 if veh.kind != "delivery" else 1.4
        return max(v_min, min(v_cap, v_need))

    def _advance_edge(self, veh: Vehicle) -> None:
        path = veh.nodes
        try:
            i = path.index(veh.v)
        except ValueError:
            veh.done = True
            return
        if i + 1 >= len(path):
            veh.done = True
            self.stats.completed += 1
            return
        veh.u = veh.v
        veh.v = path[i + 1]
        veh.s = 0.0
        veh.reserved_t = None
        veh.reserved_node = None
        if self.city.graph.has_edge(veh.u, veh.v):
            data = self.city.graph[veh.u][veh.v]
            cap = min(CRUISE_CAP_MPS, float(data["speed"]))
            if veh.kind == "delivery":
                cap = min(cap, 12.0)
            veh.v_max = cap
            veh.x, veh.y, veh.heading = _interp(data["coords"], 0.0)
        else:
            veh.done = True
            self.stats.completed += 1


def demo_metrics(seconds: float = 45.0, policy: str = "batch", seed: int = 7) -> dict:
    sim = CitySim(cfg=SimConfig(policy=policy, seed=seed, target_vehicles=220, spawn_per_s=4.0))
    steps = int(seconds / sim.cfg.dt)
    for _ in range(steps):
        sim.step()
    snap = sim.snapshot()
    snap["graph"] = {
        "nodes": sim.city.graph.number_of_nodes(),
        "edges": sim.city.graph.number_of_edges(),
    }
    return snap
