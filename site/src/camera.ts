/** Cinematic camera beats. Lookdev only — not SUMO. */

export type CameraBeat = {
  center: [number, number];
  zoom: number;
  pitch: number;
  bearing: number;
  duration: number;
};

export const CMAP_BBOX = {
  west: -88.71,
  south: 41.2,
  east: -87.02,
  north: 42.5,
};

export const NAPERVILLE: [number, number] = [-88.147, 41.75];

export function clampPitch(pitch: number, maxPitch: number): number {
  return Math.max(0, Math.min(maxPitch, pitch));
}

export function inBbox(lon: number, lat: number): boolean {
  return lon >= CMAP_BBOX.west && lon <= CMAP_BBOX.east && lat >= CMAP_BBOX.south && lat <= CMAP_BBOX.north;
}

export function lookdevPath(maxPitch: number): CameraBeat[] {
  const p = (n: number) => clampPitch(n, maxPitch);
  return [
    { center: NAPERVILLE, zoom: 15.35, pitch: p(72), bearing: -32, duration: 0 },
    { center: [-88.132, 41.758], zoom: 14.2, pitch: p(64), bearing: 18, duration: 9000 },
    { center: [-88.02, 41.8], zoom: 11.6, pitch: p(56), bearing: 48, duration: 8000 },
    { center: [-87.78, 41.86], zoom: 9.8, pitch: p(52), bearing: 62, duration: 9000 },
    { center: [-87.63, 41.882], zoom: 12.4, pitch: p(60), bearing: 12, duration: 8000 },
    { center: NAPERVILLE, zoom: 14.6, pitch: p(68), bearing: -20, duration: 10000 },
  ];
}

export function assertPathInRegion(path: CameraBeat[]): boolean {
  return path.every((b) => inBbox(b.center[0], b.center[1]));
}
