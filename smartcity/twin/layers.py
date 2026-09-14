"""GeoJSON overlays for the Chicagoland ops map."""

from __future__ import annotations

from smartcity.twin import demand, lights, macro
from smartcity.twin.region import CORRIDORS, DISTRICTS, NAPERVILLE, RINGS, circle_ring


def overlay_geojson(sim_t: float = 0.0, start_hour: float = 7.0, start_weekday: int = 0) -> dict:
    twin = macro.step_macro(sim_t, start_hour, start_weekday)
    flow = {c["id"]: c for c in twin["corridors"]}
    corridors = []
    for cor in CORRIDORS:
        f = flow.get(cor["id"], {})
        corridors.append(
            {
                "type": "Feature",
                "properties": {
                    "id": cor["id"],
                    "name": cor["name"],
                    "mode": cor.get("mode", "road"),
                    "tti": f.get("tti"),
                    "inbound_vph": f.get("inbound_vph"),
                    "outbound_vph": f.get("outbound_vph"),
                    "speed_mph": f.get("speed_mph"),
                    "tidal": cor.get("tidal"),
                },
                "geometry": {"type": "LineString", "coordinates": cor["coords"]},
            }
        )
    districts = [
        {
            "type": "Feature",
            "properties": {"id": d["id"], "name": d["name"], "role": d["role"], "pop_k": d.get("pop_k")},
            "geometry": {"type": "Point", "coordinates": [d["lon"], d["lat"]]},
        }
        for d in DISTRICTS
    ]
    rings = []
    colors = {"hero": "#e8c56b", "micro": "#8fbf6a", "meso": "#7eb6c9", "macro": "#6b7c74"}
    for ring in RINGS:
        rings.append(
            {
                "type": "Feature",
                "properties": {
                    "name": ring.name,
                    "engine": ring.engine,
                    "radius_km": ring.radius_km,
                    "color": colors[ring.name],
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [circle_ring(NAPERVILLE["lon"], NAPERVILLE["lat"], ring.radius_km)],
                },
            }
        )
    tracker = []
    for reg in demand.tracker_regions():
        if not all(reg.get(k) for k in ("west", "east", "south", "north")):
            continue
        tracker.append(
            {
                "type": "Feature",
                "properties": {
                    "name": reg["name"],
                    "speed_mph": reg["speed_mph"],
                    "source": "chicago_traffic_tracker",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [reg["west"], reg["south"]],
                            [reg["east"], reg["south"]],
                            [reg["east"], reg["north"]],
                            [reg["west"], reg["north"]],
                            [reg["west"], reg["south"]],
                        ]
                    ],
                },
            }
        )
    poles = lights.inventory()["naperville_poles"]
    light_feats = [
        {
            "type": "Feature",
            "properties": {"id": p.get("id"), "material": p.get("material")},
            "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
        }
        for p in poles
    ]
    return {
        "corridors": {"type": "FeatureCollection", "features": corridors},
        "districts": {"type": "FeatureCollection", "features": districts},
        "rings": {"type": "FeatureCollection", "features": rings},
        "tracker": {"type": "FeatureCollection", "features": tracker},
        "lights": {"type": "FeatureCollection", "features": light_feats},
        "twin": twin,
    }
