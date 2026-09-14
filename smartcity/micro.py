"""8 km micro ring: SUMO TraCI (or mock) + this package's slot/AIM pads.

Unreal is the camera. SUMO is traffic. Slot reservations stay here.
"""

from __future__ import annotations

import math
from dataclasses import replace

from smartcity.adapters.sumo import SumoNetSpec, build_micro_spec
from smartcity.adapters.traci import TraCIClient, open_client
from smartcity.config import MICRO_TICK_S, MPH_TO_MPS, SimConfig
from smartcity.geo import lonlat
from smartcity.model import CityModel, load_city
from smartcity.services import LaborLedger, ServiceBus
from smartcity.slots import make_manager, movement_key
from smartcity.twin.demand import diurnal_factor
from smartcity.twin.lanes import minutes_of_day, snapshot as lane_snapshot
from smartcity.twin.macro import step_macro

TICK_S = MICRO_TICK_S
RING = "micro"


class MicroLoop:
    """Tick the micro ring at 0.25 s and publish /ws-compatible snapshots."""

    def __init__(
        self,
        city: CityModel | None = None,
        cfg: SimConfig | None = None,
        client: TraCIClient | None = None,
        live: bool | None = None,
    ):
        base = cfg or SimConfig(dt=MICRO_TICK_S)
        self.cfg = replace(base, dt=MICRO_TICK_S)
        self.city = city or load_city()
        self.spec: SumoNetSpec = build_micro_spec(self.city)
        self.client = client or open_client(spec=self.spec, cfg=self.cfg, city=self.city, live=live)
        self.managers = {
            nid: make_manager(self.cfg.policy, self.cfg.batch_n, self.cfg.batch_delay_trigger_s)
            for nid in self.city.graph.nodes
        }
        n_sig = sum(1 for ix in self.city.intersections.values() if ix.had_signals)
        self.labor = LaborLedger(signalized_intersections=max(n_sig, 1))
        self.services = ServiceBus(
            pedestrian_cycle_s=self.cfg.pedestrian_cycle_s,
            pedestrian_window_s=self.cfg.pedestrian_window_s,
        )
        self.t = 0.0
        self._vid = 1
        self._spawn_acc = 0.0
        self._completed = 0
        self._spawned = 0
        self._stops = 0
        self._delay_s = 0.0
        self._twin = step_macro(0.0, self.cfg.start_hour, self.cfg.start_weekday)
        self._seen_speed: dict[str, float] = {}
        self._reserved: dict[str, tuple[str, float]] = {}
        self._apply_tidal()

    def reset(self, cfg: SimConfig | None = None) -> None:
        self.client.close()
        self.__init__(self.city, cfg or self.cfg, client=None, live=None)

    def close(self) -> None:
        self.client.close()

    @property
    def source(self) -> str:
        return getattr(self.client, "source", "mock")

    def step(self) -> None:
        dt = MICRO_TICK_S
        self._apply_tidal()
        self._spawn(dt)
        before = set(self.client.vehicle_ids())
        self.client.simulation_step(dt)
        self.t = self.client.t
        self._twin = step_macro(self.t, self.cfg.start_hour, self.cfg.start_weekday)
        self._slot_tick()
        after = set(self.client.vehicle_ids())
        self._completed += max(0, len(before) - len(after))

    def snapshot(self) -> dict:
        oe, on = self.city.origin_utm
        vehicles = []
        speeds = []
        for raw in self.client.vehicles():
            lon, lat = lonlat(oe, on, float(raw["x"]), float(raw["y"]))
            speed = float(raw["speed"])
            speeds.append(speed)
            kind = raw.get("kind") or "car"
            if kind not in {"car", "bus", "emergency", "delivery"}:
                kind = "car"
            vehicles.append(
                {
                    "id": str(raw["id"]),
                    "kind": kind,
                    "lon": round(lon, 6),
                    "lat": round(lat, 6),
                    "x_m": round(float(raw["x"]), 2),
                    "y_m": round(float(raw["y"]), 2),
                    "speed_mph": round(speed / MPH_TO_MPS, 1),
                    "heading": round(float(raw.get("heading") or 0.0), 1),
                }
            )
        intersections = []
        for nid, ix in self.city.intersections.items():
            if nid not in self.managers:
                continue
            lon, lat = lonlat(oe, on, ix.x, ix.y)
            mgr = self.managers[nid]
            pending = len(getattr(mgr, "reservations", []) or getattr(mgr, "occ", {}))
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
        grants = sum(getattr(m, "granted", 0) for m in self.managers.values())
        delay_saved = max(0.0, self._completed * 18.0 - self._delay_s) if self.cfg.policy != "lights" else 0.0
        mean_speed = (sum(speeds) / max(1, len(speeds))) / MPH_TO_MPS
        return {
            "type": "snapshot",
            "t": round(self.t, 2),
            "policy": self.cfg.policy,
            "vehicles": vehicles,
            "intersections": intersections,
            "metrics": {
                "active": len(vehicles),
                "spawned": self._spawned,
                "completed": self._completed,
                "mean_speed_mph": round(mean_speed, 1),
                "delay_s": round(self._delay_s, 1),
                "stops": self._stops,
                "energy": 0.0,
                "grants": grants,
                "mean_delay_s": round(self._delay_s / max(1, self._completed), 2),
            },
            "services": {
                "buses": self.services.buses,
                "emergencies": self.services.emergencies,
                "deliveries": self.services.deliveries,
                "events": self.services.events,
            },
            "labor": self.labor.yearly(delay_saved, self._completed),
            "twin": self._twin,
            "source": self.source if self.source in {"sumo", "mock"} else "mock",
            "ring": RING,
            "tick_s": MICRO_TICK_S,
        }

    def _apply_tidal(self) -> None:
        clock = lane_snapshot(self.t, self.cfg.start_hour, self.cfg.start_weekday)
        by_id = {row["id"]: row for row in clock["facilities"]}
        for fac in self.spec.facilities:
            row = by_id.get(fac.id)
            extra_on = bool(row and row.get("extra_lanes", 0) > 0)
            inbound = (row or {}).get("direction") == "inbound"
            for eid in fac.inbound_extra:
                self.client.set_lane_allowed(eid, extra_on and inbound)
            for eid in fac.outbound_extra:
                self.client.set_lane_allowed(eid, extra_on and not inbound)

    def _spawn(self, dt: float) -> None:
        minutes = minutes_of_day(self.t, self.cfg.start_hour)
        di = diurnal_factor(minutes)
        rate = self.cfg.spawn_per_s * (0.45 + 0.30 * di)
        self._spawn_acc += rate * dt
        n = int(self._spawn_acc)
        self._spawn_acc -= n
        active = len(self.client.vehicle_ids())
        kinds = ["car"]
        if self.cfg.enable_services:
            kinds.extend(self.services.pop_spawns(self.t))
        extras = [k for k in kinds if k != "car"]
        for kind in extras:
            if self._spawn_one(kind):
                active += 1
        for _ in range(n):
            if active >= self.cfg.target_vehicles:
                break
            if self._spawn_one("car"):
                active += 1

    def _spawn_one(self, kind: str) -> bool:
        route: list[str] = []
        if hasattr(self.client, "random_route"):
            route = self.client.random_route(12)
        else:
            extras = [e.id for e in self.spec.edges.values() if not e.extra]
            if len(extras) >= 4:
                start = (self._vid * 7) % (len(extras) - 3)
                route = extras[start : start + 4]
        if len(route) < 2:
            return False
        vid = f"m{self._vid}"
        self._vid += 1
        speed = self.spec.edges[route[0]].speed
        if kind == "bus":
            speed = min(speed, 16.0)
        if kind == "delivery":
            speed = min(speed, 12.0)
        if not self.client.add_vehicle(vid, route, kind, speed):
            return False
        self._spawned += 1
        return True

    def _slot_tick(self) -> None:
        for raw in self.client.vehicles():
            vid = str(raw["id"])
            nid = self._near_intersection(float(raw["x"]), float(raw["y"]))
            if nid is None:
                self._reserved.pop(vid, None)
                self.client.set_hold(vid, None)
                continue
            existing = self._reserved.get(vid)
            if existing and existing[0] == nid and existing[1] > self.t + 0.05:
                self.client.set_hold(vid, existing[1])
                self._delay_s += MICRO_TICK_S
                continue
            heading = float(raw.get("heading") or 0.0)
            movement = movement_key(heading, heading)
            mgr = self.managers[nid]
            t_slot = mgr.request(raw["id"], movement, self.t, kind=raw.get("kind") or "car", now=self.t)
            self._reserved[vid] = (nid, t_slot)
            if t_slot > self.t + 0.05:
                prev = self._seen_speed.get(vid, 1.0)
                if prev > 1.2 and float(raw["speed"]) < 0.4:
                    self._stops += 1
                self.client.set_hold(vid, t_slot)
                self._delay_s += MICRO_TICK_S
            else:
                self.client.set_hold(vid, None)
            self._seen_speed[vid] = float(raw["speed"])

    def _near_intersection(self, x: float, y: float, max_d: float = 28.0) -> str | None:
        best = None
        best_d = max_d
        for nid, ix in self.city.intersections.items():
            if nid not in self.managers:
                continue
            d = math.hypot(ix.x - x, ix.y - y)
            if d < best_d:
                best_d = d
                best = nid
        return best
