"""Greater Chicagoland geography and nested simulation fidelity.

A 3080 Ti cannot micro-simulate every intersection from Waukegan to Joliet.
Pattern: weather-model nested grids — coarse everywhere, fine at the camera.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from smartcity.geo import utm

# CMAP 7-county + NW Indiana fringe
CHICAGOLAND_BBOX = {
    "west": -88.71,
    "south": 41.20,
    "east": -87.02,
    "north": 42.50,
}

NAPERVILLE = {"lon": -88.147, "lat": 41.750}

# Local-metre origin for the Naperville mesh / SUMO / /ws x_m,y_m. Must match
# data/processed/city.json meta.origin_lonlat and meta.origin_utm (UTM 16N).
# Unreal (0,0,0), Cesium, and SmartCityLive stay on NAPERVILLE (downtown).
MESH_CRS = "EPSG:32616"
MESH_ORIGIN_LONLAT = (-88.106604, 41.75421)
MESH_ORIGIN_UTM = (408001.19, 4623078.76)


def downtown_in_mesh_m() -> tuple[float, float]:
    """Downtown in city.json metres. OSM centroid is kilometres east of the camera."""
    de, dn = utm(NAPERVILLE["lon"], NAPERVILLE["lat"])
    return round(de - MESH_ORIGIN_UTM[0], 2), round(dn - MESH_ORIGIN_UTM[1], 2)


def mesh_xy_to_unreal_uu(x_m: float, y_m: float, frame: dict | None = None) -> tuple[float, float, float]:
    """Convert /ws mesh metres to Unreal centimetres with downtown at (0,0,0)."""
    origin = frame or origin_frame()
    scale = float(origin["unreal_uu_per_metre"])
    return (
        (x_m - float(origin["downtown_x_m"])) * scale,
        (y_m - float(origin["downtown_y_m"])) * scale,
        0.0,
    )


def origin_frame() -> dict:
    """Frozen Unreal/SUMO frame. Positions in the live contract are metres from the mesh origin."""
    lon, lat = MESH_ORIGIN_LONLAT
    utm_e, utm_n = MESH_ORIGIN_UTM
    downtown_x_m, downtown_y_m = downtown_in_mesh_m()
    return {
        "crs": MESH_CRS,
        "lon": lon,
        "lat": lat,
        "utm_e": utm_e,
        "utm_n": utm_n,
        "ring_center_lon": NAPERVILLE["lon"],
        "ring_center_lat": NAPERVILLE["lat"],
        "downtown_x_m": downtown_x_m,
        "downtown_y_m": downtown_y_m,
        "x_axis": "east",
        "y_axis": "north",
        "z_axis": "up",
        "units": "metre",
        "unreal_uu_per_metre": 100.0,
    }

# Super-nodes for the macroscopic layer (district / Cities: Skylines scale).
DISTRICTS = [
    {"id": "naperville", "name": "Naperville", "lon": -88.147, "lat": 41.750, "role": "home", "pop_k": 150},
    {"id": "aurora", "name": "Aurora", "lon": -88.320, "lat": 41.760, "role": "home", "pop_k": 180},
    {"id": "downers", "name": "Downers Grove", "lon": -88.011, "lat": 41.795, "role": "home", "pop_k": 50},
    {"id": "oakbrook", "name": "Oak Brook", "lon": -87.929, "lat": 41.833, "role": "job", "pop_k": 8},
    {"id": "loop", "name": "Chicago Loop", "lon": -87.629, "lat": 41.882, "role": "job", "pop_k": 45},
    {"id": "ohare", "name": "O'Hare", "lon": -87.907, "lat": 41.974, "role": "job", "pop_k": 12},
    {"id": "evanston", "name": "Evanston", "lon": -87.687, "lat": 42.045, "role": "home", "pop_k": 78},
    {"id": "schaumburg", "name": "Schaumburg", "lon": -88.084, "lat": 42.033, "role": "job", "pop_k": 78},
    {"id": "joliet", "name": "Joliet", "lon": -88.082, "lat": 41.525, "role": "home", "pop_k": 150},
    {"id": "hydepark", "name": "Hyde Park", "lon": -87.590, "lat": 41.795, "role": "home", "pop_k": 30},
    {"id": "gary", "name": "Gary", "lon": -87.337, "lat": 41.593, "role": "home", "pop_k": 69},
    {"id": "waukegan", "name": "Waukegan", "lon": -87.845, "lat": 42.364, "role": "home", "pop_k": 89},
]

DISTRICT_BY_ID = {d["id"]: d for d in DISTRICTS}

# Expressway / rail corridors that actually move the suburb–core commute.
# Coordinates are schematic centerlines (good enough for the ops map until
# Geofabrik motorway ways are clipped in).
CORRIDORS = [
    {
        "id": "i88",
        "name": "I-88 Reagan",
        "from": "naperville",
        "to": "loop",
        "via": ["downers", "oakbrook"],
        "km": 45,
        "free_flow_mph": 55.0,
        "coords": [
            [-88.320, 41.760],
            [-88.147, 41.750],
            [-88.011, 41.795],
            [-87.929, 41.833],
            [-87.820, 41.874],
            [-87.720, 41.876],
            [-87.629, 41.882],
        ],
    },
    {
        "id": "i290",
        "name": "I-290 Eisenhower",
        "from": "oakbrook",
        "to": "loop",
        "via": [],
        "km": 22,
        "free_flow_mph": 55.0,
        "coords": [
            [-87.929, 41.833],
            [-87.850, 41.874],
            [-87.740, 41.875],
            [-87.645, 41.876],
            [-87.629, 41.882],
        ],
    },
    {
        "id": "i90",
        "name": "I-90 Kennedy",
        "from": "ohare",
        "to": "loop",
        "via": [],
        "km": 27,
        "tidal": "kennedy",
        "free_flow_mph": 55.0,
        "coords": [
            [-87.907, 41.974],
            [-87.800, 41.950],
            [-87.720, 41.918],
            [-87.668, 41.892],
            [-87.629, 41.882],
        ],
    },
    {
        "id": "i94s",
        "name": "I-94 Dan Ryan",
        "from": "hydepark",
        "to": "loop",
        "via": [],
        "km": 14,
        "free_flow_mph": 55.0,
        "coords": [
            [-87.590, 41.795],
            [-87.630, 41.830],
            [-87.645, 41.860],
            [-87.629, 41.882],
        ],
    },
    {
        "id": "i55",
        "name": "I-55 Stevenson",
        "from": "joliet",
        "to": "loop",
        "via": [],
        "km": 55,
        "free_flow_mph": 55.0,
        "coords": [
            [-88.082, 41.525],
            [-87.920, 41.620],
            [-87.780, 41.730],
            [-87.680, 41.820],
            [-87.629, 41.882],
        ],
    },
    {
        "id": "i294",
        "name": "I-294 Tri-State",
        "from": "schaumburg",
        "to": "ohare",
        "via": [],
        "km": 18,
        "free_flow_mph": 55.0,
        "coords": [
            [-88.084, 41.750],
            [-88.084, 41.900],
            [-88.084, 42.033],
            [-87.950, 42.010],
            [-87.907, 41.974],
        ],
    },
    {
        "id": "i94n",
        "name": "I-94 Edens",
        "from": "waukegan",
        "to": "loop",
        "via": ["evanston"],
        "km": 58,
        "free_flow_mph": 55.0,
        "coords": [
            [-87.845, 42.364],
            [-87.760, 42.150],
            [-87.687, 42.045],
            [-87.650, 41.940],
            [-87.629, 41.882],
        ],
    },
    {
        "id": "metra-bnsf",
        "name": "Metra BNSF",
        "from": "naperville",
        "to": "loop",
        "via": ["downers"],
        "km": 45,
        "mode": "rail",
        "free_flow_mph": 70.0,
        "coords": [
            [-88.320, 41.760],
            [-88.147, 41.751],
            [-88.011, 41.796],
            [-87.920, 41.840],
            [-87.740, 41.870],
            [-87.640, 41.878],
        ],
    },
    {
        "id": "ogden",
        "name": "Ogden Avenue",
        "from": "naperville",
        "to": "loop",
        "via": ["downers"],
        "km": 42,
        "mode": "arterial",
        "tidal": "ogden",
        "free_flow_mph": 35.0,
        "coords": [
            [-88.147, 41.772],
            [-88.050, 41.790],
            [-87.920, 41.830],
            [-87.780, 41.850],
            [-87.650, 41.870],
        ],
    },
]


@dataclass(frozen=True)
class FidelityRing:
    """Which solver owns which geography on a 3080 Ti / 10900K."""

    name: str
    engine: str
    radius_km: float
    tick_s: float
    notes: str


# Camera at Naperville downtown. Do not run SUMO micro on Gary.
RINGS = [
    FidelityRing("hero", "unreal_nanite + blender_mesh", 1.5, 1 / 60, "AAA street, Lumen, characters. ~2 km²."),
    FidelityRing("micro", "sumo + slot AIM", 8.0, 0.25, "Naperville + I-88 on-ramps. TraCI."),
    FidelityRing("meso", "sumo meso / CTM", 40.0, 1.0, "I-88/I-290/I-90 spines. Cell-transmission."),
    FidelityRing("macro", "od_flow", 120.0, 5.0, "CMAP district graph. LODES demand."),
]


def fidelity_for_distance_km(km: float) -> FidelityRing:
    for ring in RINGS:
        if km <= ring.radius_km:
            return ring
    return RINGS[-1]


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def circle_ring(lon: float, lat: float, radius_km: float, n: int = 64) -> list[list[float]]:
    """Approximate geodesic circle in WGS84 for MapLibre fills."""
    dlat = radius_km / 111.32
    coords = []
    for i in range(n + 1):
        ang = 2 * math.pi * i / n
        dlon = (radius_km / (111.32 * math.cos(math.radians(lat)))) * math.cos(ang)
        coords.append([lon + dlon, lat + dlat * math.sin(ang)])
    return coords
