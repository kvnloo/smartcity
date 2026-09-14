"""FastAPI control plane for the Naperville SmartCity runtime."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from smartcity.config import SimConfig
from smartcity.sim import CitySim
from smartcity.twin.catalog import summary as catalog_summary
from smartcity.twin.contract import LaneClockSnapshot, TwinSnapshot, WsSnapshot, dump_contract
from smartcity.twin.lanes import snapshot as lane_snapshot
from smartcity.twin.lanes import snapshot as lane_snapshot
from smartcity.twin.layers import overlay_geojson
from smartcity.twin.lights import inventory as lights_inventory
from smartcity.twin.macro import step_macro
from smartcity.twin.playbook import INTERVENTIONS

sim = CitySim()
state = {"running": True, "speed": 6.0}


class StartBody(BaseModel):
    policy: str = "batch"
    target_vehicles: int = 420
    spawn_per_s: float = 3.5
    seed: int = 7
    enable_services: bool = True
    speed: float = 6.0
    start_hour: float = 7.0
    start_weekday: int = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_runner())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="SmartCity", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB = Path(__file__).resolve().parents[1] / "web"


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


async def _runner() -> None:
    acc = 0.0
    last = asyncio.get_event_loop().time()
    while True:
        now = asyncio.get_event_loop().time()
        acc += (now - last) * state["speed"]
        last = now
        dt = sim.cfg.dt
        stepped = 0
        while acc >= dt and stepped < 24:
            if state["running"]:
                sim.step()
            acc -= dt
            stepped += 1
        if stepped == 0:
            acc = min(acc, dt * 4)
        await asyncio.sleep(0.016)


@app.get("/health")
def health() -> dict[str, Any]:
    twin = sim._twin or {}
    return {
        "ok": True,
        "t": sim.t,
        "policy": sim.cfg.policy,
        "running": state["running"],
        "clock": twin.get("clock"),
        "weekday": twin.get("weekday_name"),
    }


@app.get("/city")
def city() -> dict[str, Any]:
    return sim.city_layers()


@app.get("/snapshot", response_model=WsSnapshot)
def snapshot() -> WsSnapshot:
    return WsSnapshot.model_validate(sim.snapshot())


@app.post("/sim/start")
def start(body: StartBody) -> dict[str, Any]:
    sim.reset(
        SimConfig(
            policy=body.policy,
            target_vehicles=body.target_vehicles,
            spawn_per_s=body.spawn_per_s,
            seed=body.seed,
            enable_services=body.enable_services,
            start_hour=body.start_hour,
            start_weekday=body.start_weekday,
        )
    )
    state["running"] = True
    state["speed"] = body.speed
    return {"ok": True, "policy": body.policy}


@app.post("/sim/pause")
def pause() -> dict[str, bool]:
    state["running"] = not state["running"]
    return {"running": state["running"]}


@app.post("/sim/speed")
def set_speed(body: dict[str, float]) -> dict[str, float]:
    state["speed"] = float(body.get("speed", 6.0))
    return {"speed": state["speed"]}


@app.get("/catalog")
def catalog() -> dict[str, Any]:
    return catalog_summary()


@app.get("/twin", response_model=TwinSnapshot)
def twin() -> TwinSnapshot:
    return TwinSnapshot.model_validate(step_macro(sim.t, sim.cfg.start_hour, sim.cfg.start_weekday))


@app.get("/lanes", response_model=LaneClockSnapshot)
def lanes() -> LaneClockSnapshot:
    return LaneClockSnapshot.model_validate(lane_snapshot(sim.t, sim.cfg.start_hour, sim.cfg.start_weekday))


@app.get("/region")
def region() -> dict[str, Any]:
    return overlay_geojson(sim.t, sim.cfg.start_hour, sim.cfg.start_weekday)


@app.get("/lights")
def lights() -> dict[str, Any]:
    return lights_inventory(sim.city)


@app.get("/playbook")
def playbook() -> dict[str, Any]:
    return {"interventions": INTERVENTIONS}


@app.websocket("/ws")
async def ws(socket: WebSocket) -> None:
    await socket.accept()
    try:
        while True:
            await socket.send_json(dump_contract(WsSnapshot.model_validate(sim.snapshot())))
            await asyncio.sleep(0.12)
    except WebSocketDisconnect:
        return


app.mount("/ui", StaticFiles(directory=str(WEB)), name="ui")
