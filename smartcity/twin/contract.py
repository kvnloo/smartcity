"""Frozen live contract: FastAPI JSON Unreal consumes for zipper state + hero cars.

Field names here are the API. Do not rename them for Unreal convenience — add
a documented extra field instead. Consumers (web/ ops map, this schema) ignore
unknown keys; producers must not drop keys listed on these models.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from smartcity.config import ROOT

SCHEMA_DIR = ROOT / "docs" / "schema"

FacilityId = Literal["kennedy-revlac", "i88-solarpunk", "ogden-tidal"]
FacilityKind = Literal["expressway", "arterial"]
LaneDirection = Literal["inbound", "outbound"]
RingName = Literal["hero", "micro", "meso", "macro"]
WeekdayName = Literal["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
CorridorMode = Literal["road", "rail", "arterial"]
VehicleKind = Literal["car", "bus", "emergency", "delivery"]
SimPolicy = Literal["lights", "fair", "batch", "aim"]
AxisName = Literal["east", "north", "up"]
LengthUnit = Literal["metre"]
WsMessageType = Literal["snapshot"]


class ContractModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
    )


class OriginFrame(ContractModel):
    """Local-metre frame for hero meshes, SUMO edges, and /ws poses.

    Ring fills, Cesium, and Unreal (0,0,0) use `ring_center_*` (Naperville
    downtown). `/ws` `x_m`/`y_m` are relative to the mesh origin in city.json.
    Convert with `downtown_x_m` / `downtown_y_m`.
    """

    crs: Literal["EPSG:32616"] = Field(
        description="UTM zone 16N. Local x_m/y_m are easting/northing minus utm_e/utm_n."
    )
    lon: float = Field(description="Mesh origin longitude, WGS84 degrees.")
    lat: float = Field(description="Mesh origin latitude, WGS84 degrees.")
    utm_e: float = Field(description="Mesh origin easting, metres (EPSG:32616).")
    utm_n: float = Field(description="Mesh origin northing, metres (EPSG:32616).")
    ring_center_lon: float = Field(description="Fidelity-ring centre longitude (downtown Naperville).")
    ring_center_lat: float = Field(description="Fidelity-ring centre latitude (downtown Naperville).")
    downtown_x_m: float = Field(
        description=(
            "Downtown easting minus mesh origin, metres. Unreal uu_x = "
            "(x_m - downtown_x_m) * unreal_uu_per_metre when (0,0,0) is downtown."
        )
    )
    downtown_y_m: float = Field(
        description=(
            "Downtown northing minus mesh origin, metres. Unreal uu_y = "
            "(y_m - downtown_y_m) * unreal_uu_per_metre."
        )
    )
    x_axis: AxisName = Field(description="Local +X. Always east.")
    y_axis: AxisName = Field(description="Local +Y. Always north.")
    z_axis: AxisName = Field(description="Local +Z. Always up.")
    units: LengthUnit = Field(description="SI metre. Not centimetres, not Unreal uu.")
    unreal_uu_per_metre: float = Field(
        description=(
            "Scale from SI metres to default Unreal world units (centimetres). "
            "Use 1.0 if World Settings are metres. Do not multiply x_m by this "
            "alone — subtract downtown_x_m first, or parent to the glTF actor."
        )
    )


class TidalFacilityState(ContractModel):
    """One zipper / reversible facility at the current clock."""

    id: FacilityId = Field(description="Stable id. Switch barrier splines on this, not on the name string.")
    name: str
    kind: FacilityKind
    direction: LaneDirection = Field(
        description="Which way extra capacity currently points. inbound = toward the named core (Loop / Chicago)."
    )
    extra_lanes: int = Field(
        ge=0,
        description="Reversible/programmable lanes currently assigned. 0 when the weekend idle is in effect.",
    )
    fictional: bool = Field(
        description=(
            "false = IDOT Kennedy REVLAC (real Chicago facility). "
            "true = solarpunk proposal (I-88 AV/bus spine or Ogden peak travel lane)."
        )
    )
    inbound_mult: float = Field(description="Dimensionless capacity multiplier applied to inbound vph.")
    outbound_mult: float = Field(description="Dimensionless capacity multiplier applied to outbound vph.")


class FidelityRingState(ContractModel):
    name: RingName
    engine: str = Field(description="Who simulates this ring. Unreal only owns hero.")
    radius_km: float = Field(gt=0, description="Ring radius from downtown Naperville, kilometres.")
    radius_m: float = Field(gt=0, description="Same radius in metres (World Partition / cull sphere).")
    tick_s: float = Field(gt=0, description="Solver tick for this ring, seconds. Not the WebSocket send rate.")
    notes: str


class DistrictNode(ContractModel):
    id: str
    name: str
    lon: float = Field(description="WGS84 degrees.")
    lat: float = Field(description="WGS84 degrees.")
    role: Literal["home", "job"]
    pop_k: int = Field(description="Population in thousands, order-of-magnitude.")


class CorridorFlow(ContractModel):
    id: str = Field(description="Corridor id (i88, i90, ogden, metra-bnsf, …).")
    name: str
    from_district: str = Field(alias="from", description="Origin district id.")
    to: str = Field(description="Destination district id.")
    mode: CorridorMode
    km: int = Field(description="Schematic corridor length, kilometres.")
    speed_mph: float | None = Field(description="Current speed, miles per hour.")
    tti: float = Field(description="Travel-time index: free-flow / current. 1.0 is free flow.")
    inbound_vph: int = Field(
        description=(
            "Inbound vehicles per hour (flow rate). Not an actor count. "
            "Do not spawn inbound_vph skeletal meshes."
        )
    )
    outbound_vph: int = Field(description="Outbound vehicles per hour (flow rate), not an actor count.")
    minutes: float = Field(
        description="Estimated door-to-door travel time along this corridor, minutes. Not clock minutes-from-midnight."
    )
    tidal: str | None = Field(
        description=(
            "Optional zipper family on this corridor: 'kennedy' or 'ogden'. "
            "I-88's zipper is lanes id i88-solarpunk; this field is null on corridor i88."
        )
    )


class CommuteOd(ContractModel):
    from_district: str = Field(alias="from", description="Origin district id.")
    to: str = Field(description="Destination district id.")
    daily_work_trips: int
    source: str


class TwinSnapshot(ContractModel):
    """GET /twin — clock, zipper state, rings, district flows."""

    clock: str = Field(description="HH:MM 24h civil clock for the Chicagoland twin. Naive, not UTC.")
    weekday_name: WeekdayName
    weekend: bool
    origin: OriginFrame
    lanes: list[TidalFacilityState] = Field(description="Zipper state. Bind Unreal barrier splines here.")
    districts: list[DistrictNode]
    corridors: list[CorridorFlow]
    od: list[CommuteOd]
    fidelity: list[FidelityRingState]


class LaneClockSnapshot(ContractModel):
    """GET /lanes — same zipper rows as twin.lanes, plus minutes-from-midnight."""

    clock: str = Field(description="HH:MM 24h civil clock.")
    minutes: int = Field(ge=0, lt=24 * 60, description="Minutes from midnight. Kennedy wrap uses this.")
    weekday: int = Field(ge=0, le=6, description="0=Monday … 6=Sunday.")
    weekday_name: WeekdayName
    weekend: bool
    facilities: list[TidalFacilityState]


class VehiclePose(ContractModel):
    """One hero/micro vehicle. A few hundred of these, not inbound_vph."""

    id: int = Field(description="Stable for the lifetime of this vehicle in the current run.")
    kind: VehicleKind
    lon: float = Field(description="WGS84 degrees.")
    lat: float = Field(description="WGS84 degrees.")
    x_m: float = Field(description="Metres east of origin.utm_e (local +X).")
    y_m: float = Field(description="Metres north of origin.utm_n (local +Y).")
    speed_mph: float = Field(description="Miles per hour, not metres/second.")
    heading: float = Field(
        description=(
            "Degrees from local +X (east) toward +Y (north), counter-clockwise. "
            "0=east, 90=north. Compass heading (0=north, clockwise) = (90 - heading) mod 360. "
            "With Unreal X=east, Y=north, Z=up, actor yaw matches heading."
        )
    )


class IntersectionPad(ContractModel):
    id: str
    lon: float
    lat: float
    x_m: float = Field(description="Metres east of origin (local +X).")
    y_m: float = Field(description="Metres north of origin (local +Y).")
    had_signals: bool = Field(description="Former signalized pad (BATCH/AIM candidate).")
    degree: int
    pending: int
    grants: int


class SimMetrics(ContractModel):
    active: int = Field(description="Vehicles currently moving. This is the hero car count, not vph.")
    spawned: int
    completed: int
    mean_speed_mph: float
    delay_s: float
    stops: int
    energy: float
    grants: int
    mean_delay_s: float


class ServiceEvent(ContractModel):
    t: float = Field(description="Simulation seconds.")
    kind: str
    note: str = ""


class ServicesSnapshot(ContractModel):
    buses: int
    emergencies: int
    deliveries: int
    events: list[ServiceEvent]


class LaborSnapshot(ContractModel):
    signal_ops_hours_year: float
    field_ops_hours_year: float
    traveler_hours_this_run: float
    vehicles_completed: int
    staffed_roles_removed: list[str]


class WsSnapshot(ContractModel):
    """WS /ws and GET /snapshot — live Naperville poses plus nested twin/zipper."""

    type: WsMessageType = Field(description="Every WebSocket frame is this object. No other message types exist.")
    t: float = Field(description="Simulation seconds since /sim/start. dt = 0.25 s.")
    policy: SimPolicy
    vehicles: list[VehiclePose]
    intersections: list[IntersectionPad]
    metrics: SimMetrics
    services: ServicesSnapshot
    labor: LaborSnapshot
    twin: TwinSnapshot


DUMP_KW = {"mode": "json", "by_alias": True}


def dump_contract(model: ContractModel) -> dict:
    return model.model_dump(**DUMP_KW)


def parse_twin(payload: dict) -> TwinSnapshot:
    return TwinSnapshot.model_validate(payload)


def parse_lanes(payload: dict) -> LaneClockSnapshot:
    return LaneClockSnapshot.model_validate(payload)


def parse_ws(payload: dict) -> WsSnapshot:
    return WsSnapshot.model_validate(payload)


def json_schema_bundle() -> dict[str, dict]:
    """Committed JSON Schema documents for Unreal codegen (no Python required)."""
    specs = {
        "twin": TwinSnapshot,
        "lanes": LaneClockSnapshot,
        "ws_snapshot": WsSnapshot,
    }
    out: dict[str, dict] = {}
    for name, model in specs.items():
        schema = model.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"{name}.schema.json"
        schema["title"] = model.__name__
        out[name] = schema
    return out


def write_json_schemas(directory: Path | None = None) -> list[Path]:
    target = directory or SCHEMA_DIR
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, schema in json_schema_bundle().items():
        path = target / f"{name}.schema.json"
        path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)
    return written
