"""Runtime defaults derived from Tachet et al. (2016) and Dresner & Stone AIM."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CITY_JSON = ROOT / "data" / "processed" / "city.json"

# Tachet et al., PLOS ONE 2016: conflicting-stream setup is ~1.47s longer than same-stream follow.
T_FOLLOW_S = 1.00
T_CONFLICT_S = 2.47
SLOT_DT_S = 0.25

# Dresner & Stone AIM tile grid (coarser than the 24×24 paper default for city-scale RT).
AIM_GRID = 8
AIM_DT_S = 0.25

# Urban speeds. The viral "90–120 mph" figure is not in the papers; arterials cap here.
MPH_TO_MPS = 0.44704
CRUISE_CAP_MPH = 45.0
CROSSING_MPH = 35.0
RESIDENTIAL_MPH = 25.0

DEFAULT_ACCEL = 2.4  # m/s^2 comfortable AV
DEFAULT_DECEL = 3.2
VEHICLE_LENGTH_M = 4.6
MIN_GAP_M = 2.0

HIGHWAY_SPEED_MPH = {
    "motorway": 55.0,
    "motorway_link": 40.0,
    "trunk": 45.0,
    "trunk_link": 35.0,
    "primary": 40.0,
    "primary_link": 30.0,
    "secondary": 35.0,
    "secondary_link": 30.0,
    "tertiary": 30.0,
    "tertiary_link": 25.0,
    "unclassified": 25.0,
    "residential": 25.0,
    "living_street": 20.0,
    "service": 15.0,
}


@dataclass(frozen=True)
class SimConfig:
    policy: str = "batch"  # lights | fair | batch | aim
    dt: float = 0.25
    seed: int = 7
    target_vehicles: int = 420
    spawn_per_s: float = 3.5
    tick_hz_stream: float = 8.0
    enable_services: bool = True
    pedestrian_cycle_s: float = 48.0
    pedestrian_window_s: float = 6.0
    batch_n: int = 6
    batch_delay_trigger_s: float = 2.5
    start_hour: float = 7.0
    start_weekday: int = 0  # 0=Monday
