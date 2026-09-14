import {
  A_BRAKE,
  A_MAX,
  CAR_LENGTH,
  CAR_WIDTH,
  DIRS,
  HEADWAY,
  LIGHT_ALL_RED,
  LIGHT_GREEN,
  LIGHT_YELLOW,
  MIN_GAP,
  PATH_HALF,
  TILES,
  aabb,
  boxSize,
  mphToMps,
  mulberry32,
  overlaps,
  pose,
  tilesForLane,
  type Dir,
  type Mode,
  type SimConfig,
} from "./geometry";

export interface Car {
  id: number;
  dir: Dir;
  lane: number;
  s: number;
  v: number;
  spawnedAt: number;
  color: string;
  enterAt: number | null;
  reserved: boolean;
  tiles: number[];
}

export interface SimSnapshot {
  time: number;
  cars: Car[];
  mode: Mode;
  light: LightPhase;
  collisions: number;
  completed: number;
  stopped: number;
  meanMph: number;
  throughputPerHour: number;
  meanDelay: number;
  queueMeters: number;
}

export type LightPhase = "NS_GREEN" | "NS_YELLOW" | "EW_GREEN" | "EW_YELLOW" | "ALL_RED";

const COLORS: Record<Dir, [string, string]> = {
  S: ["#7CFFD0", "#3EE0B8"],
  N: ["#9AE7FF", "#4EC4F1"],
  E: ["#FFC978", "#FF9F43"],
  W: ["#FF9B8A", "#FF6B6B"],
};

const LANE_PATHS: { dir: Dir; lane: number }[] = DIRS.flatMap((dir) => [
  { dir, lane: 0 },
  { dir, lane: 1 },
]);

export class TrafficSim {
  config: SimConfig;
  time = 0;
  cars: Car[] = [];
  private nextId = 1;
  private rng: () => number;
  private tileBook: { t0: number; t1: number; id: number }[][];
  private completions: number[] = [];
  private delays: number[] = [];
  collisions = 0;
  completed = 0;
  overlapping = 0;

  constructor(config: SimConfig, seed = 1) {
    this.config = { ...config };
    this.rng = mulberry32(seed);
    this.tileBook = Array.from({ length: TILES * TILES }, () => []);
  }

  setConfig(config: SimConfig): void {
    this.config = { ...config };
  }

  warmup(seconds: number): void {
    const dt = 0.02;
    const steps = Math.max(1, Math.floor(seconds / dt));
    for (let i = 0; i < steps; i++) this.step(dt);
  }

  reset(seed = 1): void {
    this.time = 0;
    this.cars = [];
    this.nextId = 1;
    this.rng = mulberry32(seed);
    this.tileBook = Array.from({ length: TILES * TILES }, () => []);
    this.completions = [];
    this.delays = [];
    this.collisions = 0;
    this.completed = 0;
    this.overlapping = 0;
  }

  step(dt: number): void {
    if (dt <= 0) return;
    if (dt > 0.05) dt = 0.05;
    this.time += dt;
    this.spawn(dt);
    if (this.config.mode === "slot") {
      this.assignSlots();
    }
    this.pruneTiles();
    this.integrate(dt);
    this.finishCars();
    this.detectCollisions();
  }

  snapshot(): SimSnapshot {
    const moving = this.cars.filter((c) => c.v > 0.4);
    const meanMph =
      this.cars.length === 0
        ? 0
        : this.cars.reduce((s, c) => s + c.v, 0) / this.cars.length / 0.44704;
    const recent = this.completions.filter((t) => this.time - t < 25);
    const delayRecent = this.delays.slice(-40);
    return {
      time: this.time,
      cars: this.cars.slice(),
      mode: this.config.mode,
      light: this.lightPhase(),
      collisions: this.overlapping,
      completed: this.completed,
      stopped: this.cars.filter((c) => c.v < 0.45).length,
      meanMph: moving.length ? moving.reduce((s, c) => s + c.v, 0) / moving.length / 0.44704 : meanMph,
      throughputPerHour: (recent.length / 25) * 3600,
      meanDelay: delayRecent.length ? delayRecent.reduce((a, b) => a + b, 0) / delayRecent.length : 0,
      queueMeters: this.queueLength(),
    };
  }

  cruiseSpeed(): number {
    if (this.config.mode === "lights" && this.config.speedRegime === "vision") {
      return mphToMps(this.config.lightsMph);
    }
    return mphToMps(this.config.cruiseMph);
  }

  crossSpeed(): number {
    if (this.config.mode === "lights" && this.config.speedRegime === "vision") {
      return mphToMps(this.config.lightsMph);
    }
    return mphToMps(this.config.crossMph);
  }

  lightPhase(): LightPhase {
    const cycle = 2 * (LIGHT_GREEN + LIGHT_YELLOW + LIGHT_ALL_RED);
    const t = this.time % cycle;
    const y = LIGHT_GREEN;
    const ar = LIGHT_GREEN + LIGHT_YELLOW;
    const mid = LIGHT_GREEN + LIGHT_YELLOW + LIGHT_ALL_RED;
    if (t < y) return "NS_GREEN";
    if (t < ar) return "NS_YELLOW";
    if (t < mid) return "ALL_RED";
    if (t < mid + LIGHT_GREEN) return "EW_GREEN";
    if (t < mid + LIGHT_GREEN + LIGHT_YELLOW) return "EW_YELLOW";
    return "ALL_RED";
  }

  private boxHalf(): number {
    return boxSize() / 2;
  }

  private enterS(): number {
    return PATH_HALF - this.boxHalf();
  }

  private exitS(): number {
    return PATH_HALF + this.boxHalf();
  }

  private spawn(dt: number): void {
    const cap = 160;
    if (this.cars.length >= cap) return;
    for (const lane of LANE_PATHS) {
      if (this.rng() > this.config.arrivalPerLane * dt) continue;
      const last = this.leadInLane(lane.dir, lane.lane, 0);
      if (last && last.s < CAR_LENGTH + MIN_GAP + 8) continue;
      const v0 = this.cruiseSpeed();
      this.cars.push({
        id: this.nextId++,
        dir: lane.dir,
        lane: lane.lane,
        s: CAR_LENGTH * 0.5 + 0.4,
        v: v0,
        spawnedAt: this.time,
        color: COLORS[lane.dir][lane.lane],
        enterAt: null,
        reserved: false,
        tiles: tilesForLane(lane.dir, lane.lane),
      });
    }
  }

  private leadInLane(dir: Dir, lane: number, s: number): Car | undefined {
    let best: Car | undefined;
    for (const car of this.cars) {
      if (car.dir !== dir || car.lane !== lane) continue;
      if (car.s <= s + 0.01) continue;
      if (!best || car.s < best.s) best = car;
    }
    return best;
  }

  private assignSlots(): void {
    const enter = this.enterS();
    const vCross = this.crossSpeed();
    const candidates = this.cars
      .filter((c) => !c.reserved)
      .sort((a, b) => a.s - b.s || a.id - b.id);

    for (const car of candidates) {
      const dist = enter - (car.s + CAR_LENGTH / 2);
      if (dist < -2) {
        car.reserved = true;
        continue;
      }
      const tMin = this.time + earliestArrival(Math.max(0.2, dist), car.v, vCross);
      const step = 0.06;
      const horizon = 18;
      let found = false;
      for (let t = tMin; t < tMin + horizon; t += step) {
        if (this.tryReserve(car, t, vCross)) {
          car.enterAt = t;
          car.reserved = true;
          found = true;
          break;
        }
      }
      if (!found) {
        const fallback = tMin + horizon;
        this.tryReserve(car, fallback, vCross);
        car.enterAt = fallback;
        car.reserved = true;
      }
    }
  }

  private tryReserve(car: Car, enterAt: number, vCross: number): boolean {
    const tileLen = boxSize() / TILES;
    const occupy = (CAR_LENGTH + tileLen) / vCross;
    const pad = 0.16;
    const planned: { index: number; t0: number; t1: number }[] = [];
    for (let i = 0; i < car.tiles.length; i++) {
      const t0 = enterAt + (i * tileLen) / vCross - pad;
      const t1 = t0 + occupy + pad;
      const index = car.tiles[i];
      if (this.tileConflicts(index, t0, t1, car.id)) return false;
      planned.push({ index, t0, t1 });
    }
    for (const p of planned) {
      this.tileBook[p.index].push({ t0: p.t0, t1: p.t1, id: car.id });
    }
    return true;
  }

  private tileConflicts(index: number, t0: number, t1: number, id: number): boolean {
    const list = this.tileBook[index];
    for (const b of list) {
      if (b.id === id) continue;
      if (t0 < b.t1 && t1 > b.t0) return true;
    }
    return false;
  }

  private pruneTiles(): void {
    const cut = this.time - 2;
    for (const list of this.tileBook) {
      for (let i = list.length - 1; i >= 0; i--) {
        if (list[i].t1 < cut) list.splice(i, 1);
      }
    }
  }

  private integrate(dt: number): void {
    const cruise = this.cruiseSpeed();
    const cross = this.crossSpeed();
    const enter = this.enterS();
    const exit = this.exitS();

    for (const car of this.cars) {
      const front = car.s + CAR_LENGTH / 2;
      const lead = this.leadInLane(car.dir, car.lane, car.s);
      let vDes = cruise;

      if (this.config.mode === "slot") {
        const inBox = front > enter && car.s - CAR_LENGTH / 2 < exit;
        if (inBox) {
          vDes = cross;
        } else if (car.enterAt != null && front < enter) {
          const dist = Math.max(0.2, enter - front);
          const remain = car.enterAt - this.time;
          if (remain < 0.04) vDes = cross;
          else vDes = dist / remain;
          vDes = Math.min(cruise, Math.max(2.2, vDes));
          if (front > enter - 8) vDes = Math.min(vDes, cross + 4);
        } else if (car.s - CAR_LENGTH / 2 > exit) {
          vDes = cruise;
        }
      } else {
        vDes = this.lightDesired(car, front, enter, cruise);
      }

      if (lead) {
        const gap = lead.s - car.s - CAR_LENGTH;
        const star = MIN_GAP + HEADWAY * car.v + (car.v * Math.max(0, car.v - lead.v)) / (2 * Math.sqrt(A_MAX * A_BRAKE));
        if (gap < 0.4) vDes = 0;
        else if (gap < star) vDes = Math.min(vDes, Math.max(0, lead.v - 1.6));
      }

      const a = clamp((vDes - car.v) / 0.22, -A_BRAKE, A_MAX);
      car.v = Math.max(0, car.v + a * dt);
      if (car.v < 0.15 && vDes <= 0.25) car.v = 0;
      car.s += car.v * dt;
      if (this.config.mode === "lights" && vDes <= 0.25) {
        const stopLine = enter - 2.2;
        const frontNow = car.s + CAR_LENGTH / 2;
        if (frontNow > stopLine && frontNow < enter) {
          car.v = 0;
          car.s = stopLine - CAR_LENGTH / 2;
        }
      }
    }
  }

  private lightDesired(car: Car, front: number, enter: number, cruise: number): number {
    const stopLine = enter - 2.2;
    const dist = stopLine - front;
    const phase = this.lightPhase();
    const ns = car.dir === "N" || car.dir === "S";
    const green = (ns && phase === "NS_GREEN") || (!ns && phase === "EW_GREEN");
    const yellow = (ns && phase === "NS_YELLOW") || (!ns && phase === "EW_YELLOW");
    const inBox = front >= enter;

    if (green || inBox) return cruise;

    const stopDist = (car.v * car.v) / (2 * A_BRAKE);
    const cannotStop = dist > 0 && stopDist > dist + 0.6;
    if (yellow && cannotStop) return cruise;

    if (dist <= 0.8) return 0;
    return Math.min(cruise, Math.sqrt(Math.max(0, 1.4 * A_BRAKE * dist)));
  }

  private finishCars(): void {
    const end = PATH_HALF * 2 - CAR_LENGTH;
    const free = (PATH_HALF * 2) / this.cruiseSpeed();
    const kept: Car[] = [];
    for (const car of this.cars) {
      if (car.s >= end) {
        this.completed += 1;
        this.completions.push(this.time);
        this.delays.push(Math.max(0, this.time - car.spawnedAt - free));
      } else {
        kept.push(car);
      }
    }
    this.cars = kept;
    if (this.completions.length > 400) this.completions.splice(0, this.completions.length - 200);
    if (this.delays.length > 400) this.delays.splice(0, this.delays.length - 200);
  }

  private detectCollisions(): void {
    const box = this.boxHalf() + 6;
    const bodies = this.cars
      .map((car) => {
        const p = pose(car.dir, car.lane, car.s);
        return {
          car,
          p,
          b: aabb(p.x, p.y, p.heading, CAR_LENGTH, CAR_WIDTH, -0.22),
        };
      })
      .filter((c) => Math.abs(c.p.x) < box && Math.abs(c.p.y) < box);

    let hits = 0;
    for (let i = 0; i < bodies.length; i++) {
      for (let j = i + 1; j < bodies.length; j++) {
        const a = bodies[i];
        const b = bodies[j];
        if (a.car.dir === b.car.dir && a.car.lane === b.car.lane) continue;
        if (overlaps(a.b, b.b)) hits += 1;
      }
    }
    this.overlapping = hits;
    if (hits > 0) this.collisions += 1;
  }

  private queueLength(): number {
    const enter = this.enterS();
    let queued = 0;
    for (const car of this.cars) {
      const front = car.s + CAR_LENGTH / 2;
      if (car.v < 1.2 && front < enter) queued += 1;
    }
    return queued;
  }
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

function earliestArrival(dist: number, vNow: number, vEnd: number): number {
  const a = A_BRAKE;
  const dDec = Math.max(0, (vNow * vNow - vEnd * vEnd) / (2 * a));
  if (vNow > vEnd + 0.4 && dDec <= dist) {
    return (vNow - vEnd) / a + (dist - dDec) / vEnd;
  }
  return dist / Math.max(vNow, vEnd);
}
