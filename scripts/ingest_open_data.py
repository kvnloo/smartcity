"""Fetch small open samples. Never download Illinois PBF or Overture parquet here."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode

import requests

from smartcity.config import ROOT
from smartcity.twin.catalog import summary

OPEN = ROOT / "data" / "open"
UA = {"User-Agent": "SmartCityTwin/0.2 (research; chicagoland digital twin)"}


def _write(name: str, payload) -> Path:
    OPEN.mkdir(parents=True, exist_ok=True)
    path = OPEN / name
    if isinstance(payload, (bytes, bytearray)):
        path.write_bytes(payload)
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _get_json(url: str, timeout: int = 45) -> object:
    res = requests.get(url, headers={**UA, "Accept": "application/json"}, timeout=timeout)
    res.raise_for_status()
    return res.json()


def fetch_soda() -> dict[str, str]:
    out: dict[str, str] = {}
    jobs = [
        (
            "chicago_traffic_segments.json",
            "https://data.cityofchicago.org/resource/t2qc-9pjd.json?$limit=40",
        ),
        (
            "chicago_congestion_sample.json",
            "https://data.cityofchicago.org/resource/kf7e-cur8.json?$limit=40&$order=time%20DESC",
        ),
        (
            "chicago_crashes_sample.json",
            "https://data.cityofchicago.org/resource/85ca-t3if.json?$limit=25",
        ),
        (
            "chicago_streetlights_out.json",
            "https://data.cityofchicago.org/resource/cddf-wev5.json?$limit=25",
        ),
        (
            "chicago_zoning_sample.json",
            "https://data.cityofchicago.org/resource/nifi-zqag.json?$limit=40&$select=zone_class,zone_type,pd_num",
        ),
    ]
    for name, url in jobs:
        try:
            payload = _get_json(url)
            _write(name, payload)
            n = len(payload) if isinstance(payload, list) else 1
            out[name] = f"ok ({n})"
        except Exception as exc:  # noqa: BLE001 — ingest must continue
            out[name] = f"fail: {exc}"
    return out


def fetch_naperville_lights(pages: int = 4, page_size: int = 500) -> str:
    base = "https://portal.naperville.il.us/arcgis2/rest/services/DPW/Streetlighting/MapServer/0/query"
    features = []
    exceeded = False
    for i in range(pages):
        qs = urlencode(
            {
                "where": "1=1",
                "outFields": "POLENUMBER,SUBTYPE,MATERIAL",
                "f": "geojson",
                "resultRecordCount": page_size,
                "resultOffset": i * page_size,
            }
        )
        try:
            payload = _get_json(f"{base}?{qs}", timeout=60)
        except Exception as exc:  # noqa: BLE001
            return f"fail after {len(features)}: {exc}"
        batch = payload.get("features") or []
        features.extend(batch)
        exceeded = bool(payload.get("exceededTransferLimit") or (payload.get("properties") or {}).get("exceededTransferLimit"))
        if len(batch) < page_size:
            exceeded = False
            break
    fc = {"type": "FeatureCollection", "features": features, "exceededTransferLimit": exceeded}
    _write("naperville_streetlights.geojson", fc)
    return f"ok ({len(features)} poles, truncated={exceeded})"


def fetch_noaa() -> str:
    try:
        pts = _get_json("https://api.weather.gov/points/41.75,-88.15")
        forecast_url = ((pts.get("properties") or {}).get("forecast")) if isinstance(pts, dict) else None
        payload = {"points": pts}
        if forecast_url:
            payload["forecast"] = _get_json(forecast_url)
        _write("noaa_naperville.json", payload)
        return "ok"
    except Exception as exc:  # noqa: BLE001
        return f"fail: {exc}"


def main() -> None:
    print("catalog", json.dumps(summary()["counts"]))
    print("soda", fetch_soda())
    print("lights", fetch_naperville_lights())
    print("noaa", fetch_noaa())
    print("wrote", OPEN)


if __name__ == "__main__":
    main()
