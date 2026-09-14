"""Intersection policies from the AIM / slot-based papers.

FAIR and BATCH follow Tachet, Santi, Ratti, Frazzoli, Helbing et al.,
"Revisiting Street Intersections Using Slot-Based Systems" (PLOS ONE, 2016).

AIM tile reservations follow Dresner & Stone, "A Multiagent Approach to
Autonomous Intersection Management" (JAIR, 2008).

Traffic-light baseline is a fixed two-phase signal used as the paper's comparator.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from smartcity.config import AIM_DT_S, AIM_GRID, SLOT_DT_S, T_CONFLICT_S, T_FOLLOW_S


def heading_bin(heading: float) -> int:
    """0=E, 1=N, 2=W, 3=S."""
    return int((heading + 45.0) % 360.0 // 90.0)


def turn_code(in_heading: float, out_heading: float) -> str:
    delta = (out_heading - in_heading) % 360.0
    if delta < 40 or delta > 320:
        return "U"
    if 40 <= delta < 140:
        return "L"
    if 140 <= delta <= 220:
        return "T"
    return "R"


def movement_key(in_heading: float, out_heading: float) -> str:
    return f"{heading_bin(in_heading)}{turn_code(in_heading, out_heading)}"


def movements_compatible(a: str, b: str) -> bool:
    """Conservative US right-hand conflict table.

    Compatible: same approach (following), opposite throughs, or both rights.
    Everything else takes the longer T2 gap from Tachet et al.
    """
    if a == b:
        return True
    abin, aturn = a[0], a[1:]
    bbin, bturn = b[0], b[1:]
    if abin == bbin:
        return True
    opposite = (int(abin) + 2) % 4 == int(bbin)
    if aturn == "T" and bturn == "T" and opposite:
        return True
    if aturn == "R" and bturn == "R":
        return True
    return False


@dataclass
class Reservation:
    vehicle_id: int
    movement: str
    t_enter: float
    kind: str = "car"


@dataclass
class SlotManager:
    """Tachet FAIR (FCFS slots) with optional BATCH platooning."""

    name: str
    batch: bool = False
    batch_n: int = 6
    batch_delay_trigger_s: float = 2.5
    reservations: list[Reservation] = field(default_factory=list)
    current_class: str | None = None
    batch_count: int = 0
    last_switch_t: float = 0.0
    granted: int = 0
    denied_wait_s: float = 0.0

    def prune(self, now: float) -> None:
        self.reservations = [r for r in self.reservations if r.t_enter > now - 4.0]

    def request(
        self,
        vehicle_id: int,
        movement: str,
        earliest: float,
        kind: str = "car",
        now: float = 0.0,
    ) -> float:
        self.prune(now)
        earliest = max(earliest, now)
        if kind == "emergency":
            t = self._first_safe(movement, earliest, emergency=True)
            self._commit(vehicle_id, movement, t, kind)
            self.current_class = movement
            self.batch_count = 0
            return t

        if kind == "pedestrian":
            t = self._first_safe("__PED__", earliest)
            self._commit(vehicle_id, "__PED__", t, kind)
            return t

        if self.batch:
            delay_hint = 0.0
            if self.reservations:
                delay_hint = max(0.0, self.reservations[-1].t_enter - earliest)
            use_batch = delay_hint >= self.batch_delay_trigger_s or self.batch_count > 0
            if use_batch:
                t = self._batch_assign(movement, earliest)
                self._commit(vehicle_id, movement, t, kind)
                return t

        t = self._first_safe(movement, earliest)
        self._commit(vehicle_id, movement, t, kind)
        return t

    def _batch_assign(self, movement: str, earliest: float) -> float:
        # Paper: form same-flow platoons (T1) then switch with T2. Only when loaded.
        if self.current_class and movements_compatible(self.current_class, movement):
            if self.batch_count < self.batch_n:
                t = self._first_safe(movement, earliest)
                self.batch_count += 1
                return t
        t = self._first_safe(movement, earliest)
        if self.current_class and not movements_compatible(self.current_class, movement):
            self.batch_count = 1
        else:
            self.batch_count = min(self.batch_n, self.batch_count + 1)
        self.current_class = movement
        return t

    def _first_safe(self, movement: str, earliest: float, emergency: bool = False) -> float:
        t = _quantize(earliest, SLOT_DT_S)
        guard = 0
        while guard < 400:
            guard += 1
            bumped = False
            for r in self.reservations:
                if emergency and r.kind != "emergency":
                    # Emergency takes the slot; civilian reservations stay but we
                    # only need a T1 gap behind other emergency vehicles.
                    if r.kind == "emergency":
                        gap = T_FOLLOW_S
                    else:
                        continue
                elif r.movement == "__PED__" or movement == "__PED__":
                    gap = T_CONFLICT_S + 1.5
                else:
                    gap = T_FOLLOW_S if movements_compatible(movement, r.movement) else T_CONFLICT_S
                if abs(t - r.t_enter) + 1e-9 < gap:
                    t = _quantize(r.t_enter + gap, SLOT_DT_S)
                    bumped = True
                    break
            if not bumped:
                return t
        return t

    def _commit(self, vehicle_id: int, movement: str, t: float, kind: str) -> None:
        self.reservations.append(Reservation(vehicle_id, movement, t, kind))
        self.granted += 1
        self.current_class = movement


class LightManager:
    """Fixed two-phase signal: NS green, then EW green. Paper baseline."""

    def __init__(self, cycle: float = 64.0, green: float = 26.0, yellow: float = 3.0, allred: float = 2.0):
        self.cycle = cycle
        self.green = green
        self.yellow = yellow
        self.allred = allred
        self.granted = 0

    def phase(self, t: float) -> str:
        x = t % self.cycle
        split = self.green + self.yellow + self.allred
        if x < self.green:
            return "NS"
        if x < split:
            return "CLEAR"
        if x < split + self.green:
            return "EW"
        return "CLEAR"

    def request(self, vehicle_id: int, movement: str, earliest: float, kind: str = "car", now: float = 0.0) -> float:
        if kind == "emergency":
            self.granted += 1
            return max(earliest, now)
        t = max(earliest, now)
        for _ in range(int(self.cycle * 4)):
            if self._allowed(movement, t):
                self.granted += 1
                return t
            t += SLOT_DT_S
        self.granted += 1
        return t

    def _allowed(self, movement: str, t: float) -> bool:
        if movement == "__PED__":
            return self.phase(t) == "CLEAR"
        ph = self.phase(t)
        if ph == "CLEAR":
            return False
        bin_ = int(movement[0])
        ns = bin_ in (1, 3)
        if ph == "NS" and ns:
            return True
        if ph == "EW" and not ns:
            return True
        return False

    def prune(self, now: float) -> None:
        return


class AIMManager:
    """Reservation tiles: n×n spacetime occupancy, FCFS (Dresner & Stone)."""

    def __init__(self, grid: int = AIM_GRID, dt: float = AIM_DT_S):
        self.grid = grid
        self.dt = dt
        self.occ: dict[tuple[int, int, int], int] = {}
        self.granted = 0

    def prune(self, now: float) -> None:
        cutoff = int((now - 4.0) / self.dt)
        self.occ = {k: v for k, v in self.occ.items() if k[2] >= cutoff}

    def request(self, vehicle_id: int, movement: str, earliest: float, kind: str = "car", now: float = 0.0) -> float:
        self.prune(now)
        t = max(earliest, now)
        t0 = int(t / self.dt)
        tiles = self._tiles(movement)
        duration = max(3, len(tiles))
        for k in range(0, 240):
            start = t0 + k
            if kind == "emergency" or self._free(tiles, start, duration):
                self._fill(tiles, start, duration, vehicle_id)
                self.granted += 1
                return start * self.dt
        self.granted += 1
        return t + 8.0

    def _tiles(self, movement: str) -> list[tuple[int, int]]:
        n = self.grid
        if movement == "__PED__":
            return [(i, n // 2) for i in range(n)] + [(n // 2, i) for i in range(n)]
        bin_ = int(movement[0])
        turn = movement[1:]
        mid = n // 2
        if turn == "T":
            if bin_ in (0, 2):  # E/W
                row = mid - 1 if bin_ == 0 else mid
                return [(i, row) for i in (range(n) if bin_ == 0 else range(n - 1, -1, -1))]
            col = mid - 1 if bin_ == 1 else mid
            return [(col, j) for j in (range(n) if bin_ == 1 else range(n - 1, -1, -1))]
        if turn == "R":
            # Short corner clip.
            if bin_ == 0:
                return [(i, 1) for i in range(mid, n)]
            if bin_ == 1:
                return [(1, j) for j in range(mid, n)]
            if bin_ == 2:
                return [(i, n - 2) for i in range(mid, -1, -1)]
            return [(n - 2, j) for j in range(mid, -1, -1)]
        # Left: two-segment turn through the center.
        if bin_ == 0:
            return [(i, mid) for i in range(n)] + [(mid, j) for j in range(mid, n)]
        if bin_ == 1:
            return [(mid, j) for j in range(n)] + [(i, mid) for i in range(mid, -1, -1)]
        if bin_ == 2:
            return [(i, mid) for i in range(n - 1, -1, -1)] + [(mid, j) for j in range(mid, -1, -1)]
        return [(mid, j) for j in range(n - 1, -1, -1)] + [(i, mid) for i in range(mid, n)]

    def _free(self, tiles: list[tuple[int, int]], start: int, duration: int) -> bool:
        for k, (x, y) in enumerate(tiles):
            slice_t = start + min(k, duration - 1)
            if (x, y, slice_t) in self.occ:
                return False
            if (x, y, slice_t + 1) in self.occ:
                return False
        return True

    def _fill(self, tiles: list[tuple[int, int]], start: int, duration: int, vid: int) -> None:
        for k, (x, y) in enumerate(tiles):
            slice_t = start + min(k, duration - 1)
            self.occ[(x, y, slice_t)] = vid
            self.occ[(x, y, slice_t + 1)] = vid


def make_manager(policy: str, batch_n: int = 6, batch_delay_trigger_s: float = 2.5):
    policy = policy.lower()
    if policy == "lights":
        return LightManager()
    if policy == "aim":
        return AIMManager()
    if policy == "fair":
        return SlotManager("fair", batch=False)
    return SlotManager("batch", batch=True, batch_n=batch_n, batch_delay_trigger_s=batch_delay_trigger_s)


def _quantize(t: float, dt: float) -> float:
    return round(t / dt) * dt
