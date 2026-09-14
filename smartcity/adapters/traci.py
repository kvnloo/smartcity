"""TraCI client for the 8 km micro ring.

Live Eclipse SUMO is optional. The mock speaks the same methods so pytest
and `smartcity serve` run without netconvert. The mock does **not** implement
Krauss/IDM — vehicles hold posted edge speed (or a slot-pad hold).
"""

from __future__ import annotations

import math
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from smartcity.adapters.sumo import (
    SUMO_OUT,
    SumoEdge,
    SumoNetSpec,
    build_micro_spec,
    install_hint,
    sumo_binaries,
    traci_available,
)
from smartcity.config import MICRO_TICK_S, SimConfig
from smartcity.model import CityModel


def _interp(coords: list[list[float]], s: float) -> tuple[float, float, float]:
    remain = s
    for i in range(len(coords) - 1):
        x0, y0 = coords[i]
        x1, y1 = coords[i + 1]
        seg = math.hypot(x1 - x0, y1 - y0)
        if remain <= seg or i == len(coords) - 2:
            t = 0 if seg < 1e-6 else min(1.0, remain / max(seg, 1e-6))
            heading = math.degrees(math.atan2(y1 - y0, x1 - x0)) % 360.0
            return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, heading
        remain -= seg
    x, y = coords[-1]
    return x, y, 0.0


class TraCIClient(Protocol):
    t: float
    source: str

    def simulation_step(self, dt: float = MICRO_TICK_S) -> None: ...
    def vehicles(self) -> list[dict]: ...
    def set_lane_allowed(self, edge_id: str, allowed: bool) -> None: ...
    def add_vehicle(self, vid: str, edge_ids: list[str], kind: str, speed: float) -> bool: ...
    def set_hold(self, vid: str, hold_until: float | None) -> None: ...
    def remove_vehicle(self, vid: str) -> None: ...
    def vehicle_ids(self) -> list[str]: ...
    def close(self) -> None: ...


@dataclass
class _MockVeh:
    id: str
    kind: str
    edges: list[str]
    edge_i: int = 0
    s: float = 0.0
    speed: float = 0.0
    x: float = 0.0
    y: float = 0.0
    heading: float = 0.0
    hold_until: float | None = None
    done: bool = False


@dataclass
class MockTraCI:
    """In-process TraCI stand-in. No SUMO binary, no car-following."""

    spec: SumoNetSpec
    cfg: SimConfig
    t: float = 0.0
    source: str = "mock"
    rng: random.Random = field(default_factory=lambda: random.Random(7))
    _vehs: dict[str, _MockVeh] = field(default_factory=dict)
    _closed: set[str] = field(default_factory=set)
    _out: dict[str, list[str]] = field(default_factory=dict)
    _vid: int = 1

    def __post_init__(self) -> None:
        self._out = {}
        for edge in self.spec.edges.values():
            self._out.setdefault(edge.frm, []).append(edge.id)

    def simulation_step(self, dt: float = MICRO_TICK_S) -> None:
        self.t += dt
        for veh in list(self._vehs.values()):
            if veh.done:
                continue
            if veh.hold_until is not None and self.t < veh.hold_until:
                veh.speed = 0.0
                continue
            self._advance(veh, dt)

    def vehicles(self) -> list[dict]:
        out = []
        for veh in self._vehs.values():
            if veh.done:
                continue
            edge_id = veh.edges[veh.edge_i] if veh.edge_i < len(veh.edges) else ""
            out.append(
                {
                    "id": veh.id,
                    "kind": veh.kind,
                    "x": veh.x,
                    "y": veh.y,
                    "speed": veh.speed,
                    "heading": veh.heading,
                    "edge": edge_id,
                }
            )
        return out

    def vehicle_ids(self) -> list[str]:
        return [v.id for v in self._vehs.values() if not v.done]

    def set_lane_allowed(self, edge_id: str, allowed: bool) -> None:
        if allowed:
            self._closed.discard(edge_id)
        else:
            self._closed.add(edge_id)

    def add_vehicle(self, vid: str, edge_ids: list[str], kind: str, speed: float) -> bool:
        usable = [e for e in edge_ids if e in self.spec.edges and e not in self._closed]
        if len(usable) < 2:
            return False
        edge = self.spec.edges[usable[0]]
        x, y, h = _interp(edge.coords, 0.0)
        self._vehs[vid] = _MockVeh(
            id=vid,
            kind=kind,
            edges=usable,
            speed=speed,
            x=x,
            y=y,
            heading=h,
        )
        return True

    def set_hold(self, vid: str, hold_until: float | None) -> None:
        veh = self._vehs.get(str(vid))
        if veh is not None:
            veh.hold_until = hold_until

    def remove_vehicle(self, vid: str) -> None:
        veh = self._vehs.get(vid)
        if veh is not None:
            veh.done = True

    def close(self) -> None:
        self._vehs.clear()

    def random_route(self, hops: int = 10) -> list[str]:
        candidates = [e for e in self.spec.edges.values() if e.id not in self._closed]
        if not candidates:
            return []
        edge = self.rng.choice(candidates)
        path = [edge.id]
        node = edge.to
        for _ in range(hops):
            outs = [eid for eid in self._out.get(node, []) if eid not in self._closed]
            if not outs:
                break
            nxt = self.spec.edges[self.rng.choice(outs)]
            path.append(nxt.id)
            node = nxt.to
        return path

    def _advance(self, veh: _MockVeh, dt: float) -> None:
        if veh.edge_i >= len(veh.edges):
            veh.done = True
            return
        edge: SumoEdge = self.spec.edges[veh.edges[veh.edge_i]]
        if edge.id in self._closed:
            veh.edge_i += 1
            veh.s = 0.0
            if veh.edge_i >= len(veh.edges):
                veh.done = True
            return
        veh.speed = edge.speed
        veh.s += veh.speed * dt
        if veh.s >= edge.length - 0.05:
            veh.edge_i += 1
            veh.s = 0.0
            if veh.edge_i >= len(veh.edges):
                veh.done = True
                return
            edge = self.spec.edges[veh.edges[veh.edge_i]]
        veh.x, veh.y, veh.heading = _interp(edge.coords, min(veh.s, edge.length))


class LiveTraCI:
    """Thin wrapper around Eclipse SUMO's TraCI. Import of `traci` is lazy."""

    source = "sumo"

    def __init__(self, cfg_path: Path, step_length: float = MICRO_TICK_S):
        import traci

        sumo = sumo_binaries().get("sumo")
        if not sumo:
            raise FileNotFoundError("sumo binary is not on PATH")
        self._traci = traci
        self.t = 0.0
        self._holds: dict[str, float] = {}
        traci.start(
            [
                sumo,
                "-c",
                str(cfg_path),
                "--step-length",
                str(step_length),
                "--start",
                "--quit-on-end",
                "false",
                "--no-step-log",
                "true",
            ]
        )

    def simulation_step(self, dt: float = MICRO_TICK_S) -> None:
        now = self._traci.simulation.getTime()
        for vid, until in list(self._holds.items()):
            if now < until:
                try:
                    self._traci.vehicle.setSpeed(vid, 0.0)
                except self._traci.TraCIException:
                    self._holds.pop(vid, None)
            else:
                try:
                    self._traci.vehicle.setSpeed(vid, -1)
                except self._traci.TraCIException:
                    pass
                self._holds.pop(vid, None)
        self._traci.simulationStep()
        self.t = self._traci.simulation.getTime()

    def vehicles(self) -> list[dict]:
        out = []
        for vid in self._traci.vehicle.getIDList():
            x, y = self._traci.vehicle.getPosition(vid)
            kind = self._traci.vehicle.getTypeID(vid) or "car"
            if kind not in {"car", "bus", "emergency", "delivery"}:
                kind = "car"
            out.append(
                {
                    "id": vid,
                    "kind": kind,
                    "x": float(x),
                    "y": float(y),
                    "speed": float(self._traci.vehicle.getSpeed(vid)),
                    "heading": float(self._traci.vehicle.getAngle(vid)),
                    "edge": self._traci.vehicle.getRoadID(vid),
                }
            )
        return out

    def vehicle_ids(self) -> list[str]:
        return list(self._traci.vehicle.getIDList())

    def set_lane_allowed(self, edge_id: str, allowed: bool) -> None:
        lane = f"{edge_id}_0"
        try:
            if allowed:
                self._traci.lane.setDisallowed(lane, [])
            else:
                self._traci.lane.setDisallowed(lane, ["all"])
        except self._traci.TraCIException:
            return

    def add_vehicle(self, vid: str, edge_ids: list[str], kind: str, speed: float) -> bool:
        if len(edge_ids) < 2:
            return False
        route = f"r_{vid}"
        try:
            self._traci.route.add(route, edge_ids)
            self._traci.vehicle.add(
                vid, route, typeID=kind if kind in {"car", "bus", "emergency", "delivery"} else "car"
            )
            self._traci.vehicle.setSpeed(vid, speed)
            return True
        except self._traci.TraCIException:
            return False

    def set_hold(self, vid: str, hold_until: float | None) -> None:
        if hold_until is None:
            self._holds.pop(str(vid), None)
            try:
                self._traci.vehicle.setSpeed(str(vid), -1)
            except self._traci.TraCIException:
                return
            return
        self._holds[str(vid)] = hold_until

    def remove_vehicle(self, vid: str) -> None:
        try:
            self._traci.vehicle.remove(vid)
        except self._traci.TraCIException:
            return

    def close(self) -> None:
        try:
            self._traci.close()
        except (self._traci.TraCIException, OSError):
            return


def open_client(
    spec: SumoNetSpec | None = None,
    cfg: SimConfig | None = None,
    city: CityModel | None = None,
    live: bool | None = None,
    dest: Path | None = None,
) -> TraCIClient:
    cfg = cfg or SimConfig(dt=MICRO_TICK_S)
    spec = spec or build_micro_spec(city)
    dest = dest or SUMO_OUT
    if live is None:
        live = os.environ.get("SMARTCITY_SUMO", "").strip().lower() in {"1", "true", "yes"}
    if live:
        bins = sumo_binaries()
        cfg_path = dest / "naperville.sumocfg"
        net_path = dest / "naperville.net.xml"
        if bins.get("sumo") and traci_available() and net_path.exists():
            return LiveTraCI(cfg_path, step_length=cfg.dt)
        raise FileNotFoundError(
            "Eclipse SUMO TraCI was requested but sumo, the traci package, or "
            f"{net_path} is missing.\n" + install_hint()
        )
    return MockTraCI(spec=spec, cfg=cfg, rng=random.Random(cfg.seed))
