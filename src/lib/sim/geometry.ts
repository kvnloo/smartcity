export type Dir = "N" | "S" | "E" | "W";

export const DIRS: Dir[] = ["N", "S", "E", "W"];

export type Mode = "slot" | "lights";
export type ViewMode = "slot" | "lights" | "split";
export type SpeedRegime = "vision" | "matched";

export interface SimConfig {
  mode: Mode;
  speedRegime: SpeedRegime;
  cruiseMph: number;
  crossMph: number;
  lightsMph: number;
  arrivalPerLane: number;
  timeScale: number;
  showTiles: boolean;
  showSpeeds: boolean;
}

export const CRUISE_MPH_MIN = 90;
export const CRUISE_MPH_MAX = 120;
export const CRUISE_MPH_DEFAULT = 105;
export const CROSS_MPH_MIN = 30;
export const CROSS_MPH_MAX = 55;
export const CROSS_MPH_DEFAULT = 45;

export const DEFAULT_CONFIG: SimConfig = Object.freeze({
  mode: "slot",
  speedRegime: "vision",
  cruiseMph: CRUISE_MPH_DEFAULT,
  crossMph: CROSS_MPH_DEFAULT,
  lightsMph: 35,
  arrivalPerLane: 0.11,
  timeScale: 0.72,
  showTiles: true,
  showSpeeds: false,
}) as SimConfig;

export function sanitizeConfig(config: SimConfig): SimConfig {
  const cruise = Math.round(Number(config.cruiseMph));
  const cross = Math.round(Number(config.crossMph));
  const lights = Math.round(Number(config.lightsMph));
  const arrival = Number(config.arrivalPerLane);
  const timeScale = Number(config.timeScale);
  return {
    ...config,
    speedRegime: config.speedRegime === "matched" ? "matched" : "vision",
    cruiseMph:
      cruise >= CRUISE_MPH_MIN && cruise <= CRUISE_MPH_MAX ? cruise : CRUISE_MPH_DEFAULT,
    crossMph: cross >= CROSS_MPH_MIN && cross <= CROSS_MPH_MAX ? cross : CROSS_MPH_DEFAULT,
    lightsMph: lights >= 20 && lights <= 70 ? lights : 35,
    arrivalPerLane: Number.isFinite(arrival)
      ? Math.min(0.22, Math.max(0, arrival))
      : 0.11,
    timeScale: Number.isFinite(timeScale) ? Math.min(1.4, Math.max(0.25, timeScale)) : 0.72,
    showTiles: Boolean(config.showTiles),
    showSpeeds: Boolean(config.showSpeeds),
  };
}

export const LANE_WIDTH = 3.6;
export const CAR_LENGTH = 4.7;
export const CAR_WIDTH = 1.85;
export const PATH_HALF = 190;
export const TILES = 10;
export const MIN_GAP = 2.4;
export const HEADWAY = 0.55;
export const A_MAX = 6.2;
export const A_BRAKE = 8.8;
export const LIGHT_GREEN = 11.5;
export const LIGHT_YELLOW = 3.2;
export const LIGHT_ALL_RED = 1.1;

export function mphToMps(mph: number): number {
  return mph * 0.44704;
}

export function mpsToMph(mps: number): number {
  return mps / 0.44704;
}

export function boxSize(): number {
  return LANE_WIDTH * 4 + 2.4;
}

export function laneOffset(lane: number): number {
  return LANE_WIDTH * 0.5 + lane * LANE_WIDTH;
}

export function pose(
  dir: Dir,
  lane: number,
  s: number,
  pathHalf = PATH_HALF,
): { x: number; y: number; heading: number } {
  const mag = laneOffset(lane);
  const d = s - pathHalf;
  switch (dir) {
    case "S":
      return { x: -mag, y: d, heading: Math.PI / 2 };
    case "N":
      return { x: mag, y: -d, heading: -Math.PI / 2 };
    case "E":
      return { x: d, y: mag, heading: 0 };
    case "W":
      return { x: -d, y: -mag, heading: Math.PI };
  }
}

export function aabb(
  x: number,
  y: number,
  heading: number,
  length: number,
  width: number,
  pad = 0,
): { minX: number; minY: number; maxX: number; maxY: number } {
  const c = Math.cos(heading);
  const s = Math.sin(heading);
  const hl = length / 2 + pad;
  const hw = width / 2 + pad;
  const xs = [x + c * hl - s * hw, x + c * hl + s * hw, x - c * hl - s * hw, x - c * hl + s * hw];
  const ys = [y + s * hl + c * hw, y + s * hl - c * hw, y - s * hl + c * hw, y - s * hl - c * hw];
  return {
    minX: Math.min(...xs),
    minY: Math.min(...ys),
    maxX: Math.max(...xs),
    maxY: Math.max(...ys),
  };
}

export function overlaps(
  a: { minX: number; minY: number; maxX: number; maxY: number },
  b: { minX: number; minY: number; maxX: number; maxY: number },
): boolean {
  return a.minX < b.maxX && a.maxX > b.minX && a.minY < b.maxY && a.maxY > b.minY;
}

export function tilesForLane(dir: Dir, lane: number, n = TILES): number[] {
  const box = boxSize();
  const mag = laneOffset(lane);
  const origin = -box / 2;
  const size = box / n;
  const x = dir === "S" ? -mag : dir === "N" ? mag : 0;
  const y = dir === "E" ? mag : dir === "W" ? -mag : 0;
  const tiles: number[] = [];
  if (dir === "S" || dir === "N") {
    const col = clampIndex(Math.floor((x - origin) / size), n);
    if (dir === "S") {
      for (let row = 0; row < n; row++) tiles.push(col + row * n);
    } else {
      for (let row = n - 1; row >= 0; row--) tiles.push(col + row * n);
    }
  } else {
    const row = clampIndex(Math.floor((y - origin) / size), n);
    if (dir === "E") {
      for (let col = 0; col < n; col++) tiles.push(col + row * n);
    } else {
      for (let col = n - 1; col >= 0; col--) tiles.push(col + row * n);
    }
  }
  return tiles;
}

function clampIndex(i: number, n: number): number {
  return Math.min(n - 1, Math.max(0, i));
}

export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
