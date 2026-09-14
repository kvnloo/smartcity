"""Optional Eclipse SUMO bridge.

SUMO owns car-following, lane-changing, and meso CTM. This repo owns slot
pads and the Chicagoland clock. Do not reimplement Krauss / IDM here.
"""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from smartcity.config import ROOT
from smartcity.model import CityModel, load_city

SUMO_OUT = ROOT / "output" / "sumo"


def sumo_binaries() -> dict[str, str | None]:
    return {
        "netconvert": shutil.which("netconvert"),
        "sumo": shutil.which("sumo"),
        "sumo-gui": shutil.which("sumo-gui"),
        "traci": None,
    }


def write_plain_xml(city: CityModel | None = None, dest: Path | None = None) -> dict[str, str]:
    """Emit SUMO plain nod/edg XML from the Naperville metre graph."""
    city = city or load_city()
    dest = dest or SUMO_OUT
    dest.mkdir(parents=True, exist_ok=True)
    nodes = ET.Element("nodes")
    seen = set()
    for nid, data in city.graph.nodes(data=True):
        ET.SubElement(
            nodes,
            "node",
            id=str(nid),
            x=f"{float(data.get('x', 0.0)):.3f}",
            y=f"{float(data.get('y', 0.0)):.3f}",
            type="priority",
        )
        seen.add(nid)
    edges = ET.Element("edges")
    for u, v, data in city.graph.edges(data=True):
        if str(data.get("id", "")).endswith("r"):
            continue
        eid = str(data.get("id") or f"{u}_{v}")
        speed = float(data.get("speed") or 13.4)
        ET.SubElement(
            edges,
            "edge",
            id=eid,
            **{"from": str(u), "to": str(v), "numLanes": "1", "speed": f"{speed:.2f}"},
        )
    nod_path = dest / "naperville.nod.xml"
    edg_path = dest / "naperville.edg.xml"
    ET.ElementTree(nodes).write(nod_path, encoding="utf-8", xml_declaration=True)
    ET.ElementTree(edges).write(edg_path, encoding="utf-8", xml_declaration=True)
    net_path = dest / "naperville.net.xml"
    return {
        "nodes": str(nod_path),
        "edges": str(edg_path),
        "net": str(net_path),
        "netconvert": (
            f"netconvert --node-files {nod_path} --edge-files {edg_path} --output-file {net_path}"
        ),
        "node_count": str(len(seen)),
    }


def traci_available() -> bool:
    try:
        import traci  # noqa: F401

        return True
    except ImportError:
        return False
