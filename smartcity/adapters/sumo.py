"""Optional Eclipse SUMO bridge.

SUMO owns car-following, lane-changing, and meso CTM. This repo owns slot
pads and the Chicagoland clock. Do not reimplement Krauss / IDM here.

The 8 km micro ring is Naperville OSM plus schematic I-88 ramps / Ogden
zipper / Kennedy REVLAC extra lanes. Compile with:

    python3 scripts/build_sumo_net.py

which writes plain XML always and runs netconvert when Eclipse SUMO is on PATH.
"""

from __future__ import annotations

import json
import math
import shutil
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path

from smartcity.config import (
    ARTERIAL_CAP_MPH,
    MICRO_RADIUS_KM,
    MICRO_TICK_S,
    MOTORWAY_CAP_MPH,
    MPH_TO_MPS,
    ROOT,
)
from smartcity.model import CityModel, load_city
from smartcity.twin.lanes import I88_GREEN, KENNEDY, OGDEN

SUMO_OUT = ROOT / "output" / "sumo"

ARTERIAL_CAP_MPS = ARTERIAL_CAP_MPH * MPH_TO_MPS
MOTORWAY_CAP_MPS = MOTORWAY_CAP_MPH * MPH_TO_MPS

# Schematic 8 km spines sit just outside the OSM extract but inside the micro ring.
_I88_Y = 5600.0
_I88_X0 = -6000.0
_I88_X1 = 2000.0
_OGDEN_Y = 2200.0
_KEN_Y = 4200.0
_KEN_X0 = 2200.0
_KEN_X1 = 4700.0


def sumo_binaries() -> dict[str, str | None]:
    return {
        "netconvert": shutil.which("netconvert"),
        "sumo": shutil.which("sumo"),
        "sumo-gui": shutil.which("sumo-gui"),
        "traci": "traci" if traci_available() else None,
    }


def traci_available() -> bool:
    try:
        import traci  # noqa: F401

        return True
    except ImportError:
        return False


def install_hint() -> str:
    return (
        "Eclipse SUMO / netconvert is not on PATH. Plain nod/edg XML is still written; "
        "a TraCI mock loop can tick without SUMO. To compile naperville.net.xml:\n"
        "  Debian/Ubuntu:  sudo apt-get update && sudo apt-get install -y sumo sumo-tools\n"
        "  then:           export SUMO_HOME=/usr/share/sumo\n"
        "  Python client:  python3 -m pip install traci\n"
        "  Docker (off):   docker compose -f docker-compose.sumo.yml up --build\n"
        "Docs: docs/SUMO.md"
    )


def edge_speed_mps(highway: str | None, posted_mps: float) -> float:
    """Arterials cap at 45 mph. Motorways (I-88 / Kennedy) may run 55."""
    hw = highway or "unclassified"
    posted = float(posted_mps)
    if hw in ("motorway", "motorway_link"):
        cap = MOTORWAY_CAP_MPS if hw == "motorway" else min(MOTORWAY_CAP_MPS, 40.0 * MPH_TO_MPS)
        return min(posted, cap)
    return min(posted, ARTERIAL_CAP_MPS)


@dataclass
class SumoNode:
    id: str
    x: float
    y: float
    type: str = "priority"


@dataclass
class SumoEdge:
    id: str
    frm: str
    to: str
    speed: float
    num_lanes: int
    highway: str
    name: str
    coords: list[list[float]]
    length: float
    tidal: str | None = None
    fictional: bool = False
    extra: bool = False


@dataclass
class TidalLanes:
    id: str
    name: str
    kind: str
    fictional: bool
    zipper_nodes: list[str] = field(default_factory=list)
    inbound_extra: list[str] = field(default_factory=list)
    outbound_extra: list[str] = field(default_factory=list)


@dataclass
class SumoNetSpec:
    nodes: dict[str, SumoNode]
    edges: dict[str, SumoEdge]
    facilities: list[TidalLanes]
    tick_s: float = MICRO_TICK_S
    radius_km: float = MICRO_RADIUS_KM


def build_micro_spec(city: CityModel | None = None) -> SumoNetSpec:
    """Naperville graph + 8 km schematic zipper / REVLAC spines."""
    city = city or load_city()
    nodes: dict[str, SumoNode] = {}
    edges: dict[str, SumoEdge] = {}
    for nid, data in city.graph.nodes(data=True):
        nodes[str(nid)] = SumoNode(id=str(nid), x=float(data.get("x", 0.0)), y=float(data.get("y", 0.0)))
    for u, v, data in city.graph.edges(data=True):
        eid = str(data.get("id") or f"{u}_{v}")
        hw = str(data.get("highway") or "unclassified")
        coords = [list(pt) for pt in data.get("coords") or []]
        if len(coords) < 2:
            coords = [
                [float(city.graph.nodes[u]["x"]), float(city.graph.nodes[u]["y"])],
                [float(city.graph.nodes[v]["x"]), float(city.graph.nodes[v]["y"])],
            ]
        length = float(data.get("length") or _poly_len(coords))
        edges[eid] = SumoEdge(
            id=eid,
            frm=str(u),
            to=str(v),
            speed=edge_speed_mps(hw, float(data.get("speed") or 25.0 * MPH_TO_MPS)),
            num_lanes=1,
            highway=hw,
            name=str(data.get("name") or ""),
            coords=coords,
            length=max(length, 1.0),
        )
    facilities = _inject_schematic_ring(city, nodes, edges)
    return SumoNetSpec(nodes=nodes, edges=edges, facilities=facilities)


def write_plain_xml(city: CityModel | None = None, dest: Path | None = None) -> dict[str, str]:
    """Emit SUMO plain XML for the 8 km micro ring. netconvert compiles .net.xml."""
    city = city or load_city()
    dest = dest or SUMO_OUT
    dest.mkdir(parents=True, exist_ok=True)
    spec = build_micro_spec(city)
    nod_path = dest / "naperville.nod.xml"
    edg_path = dest / "naperville.edg.xml"
    typ_path = dest / "naperville.typ.xml"
    con_path = dest / "naperville.con.xml"
    rou_path = dest / "naperville.rou.xml"
    cfg_path = dest / "naperville.sumocfg"
    fac_path = dest / "facilities.json"
    net_path = dest / "naperville.net.xml"

    nodes_el = ET.Element("nodes")
    for node in spec.nodes.values():
        ET.SubElement(
            nodes_el,
            "node",
            id=node.id,
            x=f"{node.x:.3f}",
            y=f"{node.y:.3f}",
            type=node.type,
        )
    edges_el = ET.Element("edges")
    for edge in spec.edges.values():
        attrib = {
            "id": edge.id,
            "from": edge.frm,
            "to": edge.to,
            "numLanes": str(edge.num_lanes),
            "speed": f"{edge.speed:.2f}",
            "type": _type_id(edge.highway),
        }
        if edge.name:
            attrib["name"] = edge.name
        if len(edge.coords) >= 2:
            attrib["shape"] = " ".join(f"{p[0]:.3f},{p[1]:.3f}" for p in edge.coords)
        el = ET.SubElement(edges_el, "edge", attrib)
        if edge.tidal:
            el.set("spreadType", "center")
            ET.SubElement(el, "param", key="tidal", value=edge.tidal)
            ET.SubElement(el, "param", key="fictional", value="true" if edge.fictional else "false")
            ET.SubElement(el, "param", key="extra", value="true" if edge.extra else "false")

    types_el = ET.Element("types")
    for tid, prio, lanes, mph in (
        ("motorway", 14, 2, MOTORWAY_CAP_MPH),
        ("motorway_link", 12, 1, 40.0),
        ("primary", 12, 1, 40.0),
        ("secondary", 10, 1, 35.0),
        ("tertiary", 8, 1, 30.0),
        ("arterial", 11, 1, ARTERIAL_CAP_MPH),
        ("residential", 4, 1, 25.0),
        ("unclassified", 4, 1, 25.0),
        ("service", 3, 1, 15.0),
        ("living_street", 3, 1, 20.0),
    ):
        ET.SubElement(
            types_el,
            "type",
            id=tid,
            priority=str(prio),
            numLanes=str(lanes),
            speed=f"{edge_speed_mps(tid, mph * MPH_TO_MPS):.2f}",
        )

    cons_el = ET.Element("connections")
    for fac in spec.facilities:
        if fac.kind != "zipper":
            continue
        for extra_id, gen_id in _zipper_pairs(spec, fac):
            ET.SubElement(
                cons_el,
                "connection",
                **{"from": extra_id, "to": gen_id, "fromLane": "0", "toLane": "0"},
            )

    _write_xml(nodes_el, nod_path)
    _write_xml(edges_el, edg_path)
    _write_xml(types_el, typ_path)
    _write_xml(cons_el, con_path)
    _write_xml(_routes_xml(), rou_path)
    _write_xml(_sumocfg_xml(), cfg_path)
    fac_path.write_text(
        json.dumps(
            {
                "tick_s": spec.tick_s,
                "radius_km": spec.radius_km,
                "ring": "micro",
                "facilities": [asdict(f) for f in spec.facilities],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    netconvert_args = [
        "--node-files",
        str(nod_path),
        "--edge-files",
        str(edg_path),
        "--type-files",
        str(typ_path),
        "--connection-files",
        str(con_path),
        "--output-file",
        str(net_path),
        "--no-internal-links",
        "true",
        "--ignore-errors",
        "true",
    ]
    return {
        "nodes": str(nod_path),
        "edges": str(edg_path),
        "types": str(typ_path),
        "connections": str(con_path),
        "routes": str(rou_path),
        "config": str(cfg_path),
        "facilities": str(fac_path),
        "net": str(net_path),
        "netconvert": "netconvert " + " ".join(netconvert_args),
        "node_count": str(len(spec.nodes)),
        "edge_count": str(len(spec.edges)),
        "tick_s": str(spec.tick_s),
        "install_hint": install_hint(),
        "netconvert_args": " ".join(netconvert_args),
    }


def netconvert_argv(paths: dict[str, str], netconvert: str = "netconvert") -> list[str]:
    return [netconvert, *paths["netconvert_args"].split()]


def _write_xml(root: ET.Element, path: Path) -> None:
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def _poly_len(coords: list[list[float]]) -> float:
    return sum(math.hypot(coords[i + 1][0] - coords[i][0], coords[i + 1][1] - coords[i][1]) for i in range(len(coords) - 1))


def _type_id(highway: str) -> str:
    if highway in ("motorway", "motorway_link", "primary", "secondary", "tertiary", "residential", "service", "living_street", "unclassified", "arterial"):
        return highway
    if highway in ("primary_link", "secondary_link", "tertiary_link"):
        return highway.replace("_link", "")
    if highway in ("trunk", "trunk_link"):
        return "arterial"
    return "unclassified"


def _add_node(nodes: dict[str, SumoNode], nid: str, x: float, y: float, typ: str = "priority") -> SumoNode:
    node = SumoNode(id=nid, x=x, y=y, type=typ)
    nodes[nid] = node
    return node


def _add_edge(
    edges: dict[str, SumoEdge],
    eid: str,
    frm: str,
    to: str,
    nodes: dict[str, SumoNode],
    *,
    speed: float,
    highway: str,
    name: str,
    num_lanes: int = 1,
    tidal: str | None = None,
    fictional: bool = False,
    extra: bool = False,
) -> SumoEdge:
    a, b = nodes[frm], nodes[to]
    coords = [[a.x, a.y], [b.x, b.y]]
    edge = SumoEdge(
        id=eid,
        frm=frm,
        to=to,
        speed=speed,
        num_lanes=num_lanes,
        highway=highway,
        name=name,
        coords=coords,
        length=max(_poly_len(coords), 1.0),
        tidal=tidal,
        fictional=fictional,
        extra=extra,
    )
    edges[eid] = edge
    return edge


def _nearest_city_node(city: CityModel, x: float, y: float) -> str:
    best = None
    best_d = 1e18
    for nid, data in city.graph.nodes(data=True):
        d = math.hypot(float(data["x"]) - x, float(data["y"]) - y)
        if d < best_d:
            best_d = d
            best = nid
    return str(best)


def _pair(edges: dict[str, SumoEdge], nodes: dict[str, SumoNode], a: str, b: str, base: str, **kwargs) -> None:
    _add_edge(edges, f"{base}_eb", a, b, nodes, **kwargs)
    _add_edge(edges, f"{base}_wb", b, a, nodes, **kwargs)


def _inject_schematic_ring(
    city: CityModel,
    nodes: dict[str, SumoNode],
    edges: dict[str, SumoEdge],
) -> list[TidalLanes]:
    """I-88 / Ogden zippers (fictional) and Kennedy REVLAC (real schedule, schematic geom)."""
    i88_w = _add_node(nodes, "z_i88_w", _I88_X0, _I88_Y)
    i88_zip = _add_node(nodes, "z_i88_zip", (_I88_X0 + _I88_X1) / 2.0, _I88_Y, "zipper")
    i88_e = _add_node(nodes, "z_i88_e", _I88_X1, _I88_Y)
    i88_speed = edge_speed_mps("motorway", MOTORWAY_CAP_MPS)
    _pair(
        edges,
        nodes,
        i88_w.id,
        i88_zip.id,
        "z_i88_w",
        speed=i88_speed,
        highway="motorway",
        name="I-88 Reagan",
        num_lanes=2,
        tidal=I88_GREEN.id,
        fictional=True,
    )
    _pair(
        edges,
        nodes,
        i88_zip.id,
        i88_e.id,
        "z_i88_e",
        speed=i88_speed,
        highway="motorway",
        name="I-88 Reagan",
        num_lanes=2,
        tidal=I88_GREEN.id,
        fictional=True,
    )
    _add_edge(
        edges,
        "z_i88_av_eb",
        i88_w.id,
        i88_zip.id,
        nodes,
        speed=i88_speed,
        highway="motorway",
        name="I-88 AV/bus spine",
        tidal=I88_GREEN.id,
        fictional=True,
        extra=True,
    )
    _add_edge(
        edges,
        "z_i88_av_wb",
        i88_e.id,
        i88_zip.id,
        nodes,
        speed=i88_speed,
        highway="motorway",
        name="I-88 AV/bus spine",
        tidal=I88_GREEN.id,
        fictional=True,
        extra=True,
    )

    north = _nearest_city_node(city, i88_zip.x, city.bbox_m[3])
    nx, ny = nodes[north].x, nodes[north].y
    ramp_j = _add_node(nodes, "z_i88_ramp", i88_zip.x, (i88_zip.y + ny) / 2.0, "zipper")
    _add_edge(
        edges,
        "z_i88_off",
        i88_zip.id,
        ramp_j.id,
        nodes,
        speed=edge_speed_mps("motorway_link", 40.0 * MPH_TO_MPS),
        highway="motorway_link",
        name="I-88 off-ramp",
        tidal=I88_GREEN.id,
        fictional=True,
    )
    _add_edge(
        edges,
        "z_i88_off_city",
        ramp_j.id,
        north,
        nodes,
        speed=edge_speed_mps("motorway_link", 40.0 * MPH_TO_MPS),
        highway="motorway_link",
        name="I-88 off-ramp",
        tidal=I88_GREEN.id,
        fictional=True,
    )
    _add_edge(
        edges,
        "z_i88_on_city",
        north,
        ramp_j.id,
        nodes,
        speed=edge_speed_mps("motorway_link", 40.0 * MPH_TO_MPS),
        highway="motorway_link",
        name="I-88 on-ramp",
        tidal=I88_GREEN.id,
        fictional=True,
    )
    _add_edge(
        edges,
        "z_i88_on",
        ramp_j.id,
        i88_zip.id,
        nodes,
        speed=edge_speed_mps("motorway_link", 40.0 * MPH_TO_MPS),
        highway="motorway_link",
        name="I-88 on-ramp",
        tidal=I88_GREEN.id,
        fictional=True,
    )

    og_w = _add_node(nodes, "z_ogden_w", _I88_X0, _OGDEN_Y)
    og_zip = _add_node(nodes, "z_ogden_zip", (_I88_X0 + _I88_X1) / 2.0, _OGDEN_Y, "zipper")
    og_e = _add_node(nodes, "z_ogden_e", _I88_X1, _OGDEN_Y)
    og_speed = edge_speed_mps("arterial", ARTERIAL_CAP_MPS)
    _pair(
        edges,
        nodes,
        og_w.id,
        og_zip.id,
        "z_ogden_w",
        speed=og_speed,
        highway="arterial",
        name="Ogden Avenue",
        tidal=OGDEN.id,
        fictional=True,
    )
    _pair(
        edges,
        nodes,
        og_zip.id,
        og_e.id,
        "z_ogden_e",
        speed=og_speed,
        highway="arterial",
        name="Ogden Avenue",
        tidal=OGDEN.id,
        fictional=True,
    )
    _add_edge(
        edges,
        "z_ogden_peak_eb",
        og_w.id,
        og_zip.id,
        nodes,
        speed=og_speed,
        highway="arterial",
        name="Ogden peak travel lane",
        tidal=OGDEN.id,
        fictional=True,
        extra=True,
    )
    _add_edge(
        edges,
        "z_ogden_peak_wb",
        og_e.id,
        og_zip.id,
        nodes,
        speed=og_speed,
        highway="arterial",
        name="Ogden peak travel lane",
        tidal=OGDEN.id,
        fictional=True,
        extra=True,
    )
    og_city = _nearest_city_node(city, og_zip.x, og_zip.y)
    _add_edge(
        edges,
        "z_ogden_in",
        og_zip.id,
        og_city,
        nodes,
        speed=og_speed,
        highway="arterial",
        name="Ogden Avenue",
        tidal=OGDEN.id,
        fictional=True,
    )
    _add_edge(
        edges,
        "z_ogden_out",
        og_city,
        og_zip.id,
        nodes,
        speed=og_speed,
        highway="arterial",
        name="Ogden Avenue",
        tidal=OGDEN.id,
        fictional=True,
    )

    ken_w = _add_node(nodes, "z_ken_w", _KEN_X0, _KEN_Y)
    ken_e = _add_node(nodes, "z_ken_e", _KEN_X1, _KEN_Y)
    ken_speed = edge_speed_mps("motorway", MOTORWAY_CAP_MPS)
    _pair(
        edges,
        nodes,
        ken_w.id,
        ken_e.id,
        "z_ken",
        speed=ken_speed,
        highway="motorway",
        name="Kennedy Expressway",
        num_lanes=2,
        tidal=KENNEDY.id,
        fictional=False,
    )
    _add_edge(
        edges,
        "z_ken_rev_ib",
        ken_w.id,
        ken_e.id,
        nodes,
        speed=ken_speed,
        highway="motorway",
        name="Kennedy REVLAC",
        num_lanes=2,
        tidal=KENNEDY.id,
        fictional=False,
        extra=True,
    )
    _add_edge(
        edges,
        "z_ken_rev_ob",
        ken_e.id,
        ken_w.id,
        nodes,
        speed=ken_speed,
        highway="motorway",
        name="Kennedy REVLAC",
        num_lanes=2,
        tidal=KENNEDY.id,
        fictional=False,
        extra=True,
    )

    return [
        TidalLanes(
            id=KENNEDY.id,
            name=KENNEDY.name,
            kind="revlac",
            fictional=False,
            inbound_extra=["z_ken_rev_ib"],
            outbound_extra=["z_ken_rev_ob"],
        ),
        TidalLanes(
            id=I88_GREEN.id,
            name=I88_GREEN.name,
            kind="zipper",
            fictional=True,
            zipper_nodes=["z_i88_zip", "z_i88_ramp"],
            inbound_extra=["z_i88_av_eb"],
            outbound_extra=["z_i88_av_wb"],
        ),
        TidalLanes(
            id=OGDEN.id,
            name=OGDEN.name,
            kind="zipper",
            fictional=True,
            zipper_nodes=["z_ogden_zip"],
            inbound_extra=["z_ogden_peak_eb"],
            outbound_extra=["z_ogden_peak_wb"],
        ),
    ]


def _zipper_pairs(spec: SumoNetSpec, fac: TidalLanes) -> list[tuple[str, str]]:
    pairs = []
    if fac.id == I88_GREEN.id:
        pairs.append(("z_i88_av_eb", "z_i88_e_eb"))
        pairs.append(("z_i88_av_wb", "z_i88_w_wb"))
        pairs.append(("z_i88_on", "z_i88_e_eb"))
    if fac.id == OGDEN.id:
        pairs.append(("z_ogden_peak_eb", "z_ogden_e_eb"))
        pairs.append(("z_ogden_peak_wb", "z_ogden_w_wb"))
    return [(a, b) for a, b in pairs if a in spec.edges and b in spec.edges]


def _routes_xml() -> ET.Element:
    """vTypes only. SUMO owns Krauss; this file does not describe car-following."""
    routes = ET.Element("routes")
    ET.SubElement(
        routes,
        "vType",
        id="car",
        accel="2.4",
        decel="3.2",
        sigma="0.25",
        length="4.6",
        minGap="2.0",
        maxSpeed=f"{MOTORWAY_CAP_MPS:.2f}",
    )
    ET.SubElement(
        routes,
        "vType",
        id="bus",
        accel="1.2",
        decel="2.8",
        length="12.0",
        minGap="2.5",
        maxSpeed="16.00",
        vClass="bus",
    )
    ET.SubElement(
        routes,
        "vType",
        id="emergency",
        accel="2.8",
        decel="4.5",
        length="5.5",
        maxSpeed=f"{MOTORWAY_CAP_MPS:.2f}",
        vClass="emergency",
    )
    ET.SubElement(
        routes,
        "vType",
        id="delivery",
        accel="1.8",
        decel="3.0",
        length="6.5",
        maxSpeed="12.00",
        vClass="delivery",
    )
    return routes


def _sumocfg_xml() -> ET.Element:
    cfg = ET.Element("configuration")
    inp = ET.SubElement(cfg, "input")
    ET.SubElement(inp, "net-file", value="naperville.net.xml")
    ET.SubElement(inp, "route-files", value="naperville.rou.xml")
    timing = ET.SubElement(cfg, "time")
    ET.SubElement(timing, "begin", value="0")
    ET.SubElement(timing, "step-length", value=f"{MICRO_TICK_S}")
    proc = ET.SubElement(cfg, "processing")
    ET.SubElement(proc, "lateral-resolution", value="0")
    traci = ET.SubElement(cfg, "traci_server")
    ET.SubElement(traci, "port", value="8813")
    return cfg
