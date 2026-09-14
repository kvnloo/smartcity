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

sim = CitySim()
state = {"running": True, "speed": 6.0}


class StartBody(BaseModel):
    policy: str = "batch"
    target_vehicles: int = 420
    spawn_per_s: float = 3.5
    seed: int = 7
    enable_services: bool = True
    speed: float = 6.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_runner())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="SmartCity", version="0.1.0", lifespan=lifespan)
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
    return {"ok": True, "t": sim.t, "policy": sim.cfg.policy, "running": state["running"]}


@app.get("/city")
def city() -> dict[str, Any]:
    return sim.city_layers()


@app.get("/snapshot")
def snapshot() -> dict[str, Any]:
    return sim.snapshot()


@app.post("/sim/start")
def start(body: StartBody) -> dict[str, Any]:
    sim.reset(
        SimConfig(
            policy=body.policy,
            target_vehicles=body.target_vehicles,
            spawn_per_s=body.spawn_per_s,
            seed=body.seed,
            enable_services=body.enable_services,
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


@app.websocket("/ws")
async def ws(socket: WebSocket) -> None:
    await socket.accept()
    try:
        while True:
            await socket.send_json(sim.snapshot())
            await asyncio.sleep(0.12)
    except WebSocketDisconnect:
        return


app.mount("/ui", StaticFiles(directory=str(WEB)), name="ui")
