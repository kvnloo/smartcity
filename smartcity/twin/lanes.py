"""Programmatic / tidal lanes.

Chicago already has this: IDOT Kennedy Expressway REVLAC (reversible express
lanes), inbound through the morning, outbound after midday.

Other cities run the same pattern under different names — zipper / tidal /
contraflow / peak-hour lanes (Madrid Calle 30, Sydney Harbour Bridge,
São Paulo mini-anel, Boston I-93 zipper). The move is not exotic. The
solarpunk expansion is applying it to I-88 (Naperville–Loop) and donating
an arterial parking lane to movement at peak.

Schedule source: Travel Midwest Kennedy reversibles FAQ.
https://www.travelmidwest.com/Help/FAQs
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TidalFacility:
    id: str
    name: str
    kind: str  # expressway | arterial
    inbound_name: str
    extra_lanes: int = 2
    # weekday minutes-from-midnight when extra capacity points inbound
    inbound_from: int = 23 * 60  # 23:00
    inbound_until: int = 12 * 60 + 30  # 12:30
    friday_inbound_until: int | None = None
    fictional: bool = False


KENNEDY = TidalFacility(
    id="kennedy-revlac",
    name="Kennedy Expressway reversible express lanes",
    kind="expressway",
    inbound_name="Loop",
    extra_lanes=2,
    inbound_from=23 * 60,
    inbound_until=12 * 60 + 30,
    friday_inbound_until=13 * 60 + 30,
    fictional=False,
)

I88_GREEN = TidalFacility(
    id="i88-solarpunk",
    name="I-88 programmable AV/bus spine",
    kind="expressway",
    inbound_name="Loop",
    extra_lanes=1,
    inbound_from=5 * 60,
    inbound_until=10 * 60,
    fictional=True,
)

OGDEN = TidalFacility(
    id="ogden-tidal",
    name="Ogden Avenue peak travel lane",
    kind="arterial",
    inbound_name="Chicago",
    extra_lanes=1,
    inbound_from=6 * 60 + 30,
    inbound_until=9 * 60 + 30,
    fictional=True,
)

FACILITIES = [KENNEDY, I88_GREEN, OGDEN]


def minutes_of_day(sim_t: float, start_hour: float = 7.0) -> int:
    """Map simulation seconds onto a 24h clock. t=0 → start_hour."""
    return int(start_hour * 60 + sim_t / 60.0) % (24 * 60)


def weekday_index(sim_t: float, start_hour: float = 7.0, start_weekday: int = 0) -> int:
    """0=Monday … 6=Sunday. Simulation day 0 is start_weekday."""
    total_min = start_hour * 60 + sim_t / 60.0
    days = int(total_min // (24 * 60))
    return (start_weekday + days) % 7


def _wrap_in(m: int, start: int, end: int) -> bool:
    if start <= end:
        return start <= m < end
    return m >= start or m < end


def inbound_until(facility: TidalFacility, weekday: int) -> int:
    if facility.friday_inbound_until is not None and weekday == 4:
        return facility.friday_inbound_until
    return facility.inbound_until


def direction(facility: TidalFacility, minutes: int, weekday: int = 0) -> str:
    until = inbound_until(facility, weekday)
    return "inbound" if _wrap_in(minutes, facility.inbound_from, until) else "outbound"


def capacity_multiplier(facility: TidalFacility, minutes: int, travel_dir: str, weekday: int = 0) -> float:
    """Peak direction gets the extra lanes; opposite loses them.

    Weekends: REVLAC often idles; we treat extra lanes as unused (1.0 / 1.0).
    """
    if weekday >= 5:
        return 1.0
    facing = direction(facility, minutes, weekday)
    if travel_dir == facing:
        return 1.0 + 0.22 * facility.extra_lanes
    return max(0.62, 1.0 - 0.12 * facility.extra_lanes)


def snapshot(sim_t: float, start_hour: float = 7.0, start_weekday: int = 0) -> dict:
    m = minutes_of_day(sim_t, start_hour)
    wd = weekday_index(sim_t, start_hour, start_weekday)
    hh, mm = divmod(m, 60)
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return {
        "clock": f"{hh:02d}:{mm:02d}",
        "minutes": m,
        "weekday": wd,
        "weekday_name": names[wd],
        "weekend": wd >= 5,
        "facilities": [
            {
                "id": f.id,
                "name": f.name,
                "kind": f.kind,
                "direction": direction(f, m, wd),
                "extra_lanes": 0 if wd >= 5 else f.extra_lanes,
                "fictional": f.fictional,
                "inbound_mult": round(capacity_multiplier(f, m, "inbound", wd), 2),
                "outbound_mult": round(capacity_multiplier(f, m, "outbound", wd), 2),
            }
            for f in FACILITIES
        ],
    }
