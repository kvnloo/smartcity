"""City-wide services that share the same reservation fabric as traffic.

Emergency preemption, transit pulses, pedestrian windows, and curb/delivery
slots are all just priority kinds on the intersection manager — so the city
does not need a separate timing shop, crossing-guard roster, or radio dispatcher
to "make a hole" in traffic.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LaborLedger:
    """Order-of-magnitude hours the slot city no longer has to staff."""

    signalized_intersections: int
    population: int = 149_540

    def yearly(self, delay_saved_s: float, vehicles_done: int, occupancy: float = 1.15) -> dict[str, float]:
        # Signal retiming / cabinet maintenance ~40 staff-hours / intersection / year.
        signal_ops = self.signalized_intersections * 40.0
        # Peak-hour crossing / traffic direction, ~2 hours/day * 250 days at 8 sites.
        field_ops = 8 * 2.0 * 250.0
        person_hours = delay_saved_s * occupancy / 3600.0
        return {
            "signal_ops_hours_year": signal_ops,
            "field_ops_hours_year": field_ops,
            "traveler_hours_this_run": round(person_hours, 3),
            "vehicles_completed": vehicles_done,
            "staffed_roles_removed": [
                "signal timing engineer (network-wide splits)",
                "cabinet technician patrol",
                "peak-hour traffic direction",
                "crossing-guard posts at converted arterials",
            ],
        }


@dataclass
class ServiceBus:
    pedestrian_cycle_s: float = 48.0
    pedestrian_window_s: float = 6.0
    next_bus_t: float = 25.0
    next_emergency_t: float = 90.0
    next_delivery_t: float = 18.0
    buses: int = 0
    emergencies: int = 0
    deliveries: int = 0
    pedestrian_holds: int = 0
    events: list[dict] = field(default_factory=list)

    def pop_spawns(self, t: float) -> list[str]:
        kinds: list[str] = []
        if t >= self.next_emergency_t:
            kinds.append("emergency")
            self.emergencies += 1
            self.next_emergency_t = t + 80.0
            self.events.append({"t": t, "kind": "emergency", "note": "corridor preemption"})
        if t >= self.next_bus_t:
            kinds.append("bus")
            self.buses += 1
            self.next_bus_t = t + 22.0
            self.events.append({"t": t, "kind": "bus", "note": "transit slot pulse"})
        if t >= self.next_delivery_t:
            kinds.append("delivery")
            self.deliveries += 1
            self.next_delivery_t = t + 16.0
        self.events = self.events[-12:]
        return kinds

    def pedestrian_window_open(self, t: float) -> bool:
        return (t % self.pedestrian_cycle_s) < self.pedestrian_window_s
