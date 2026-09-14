/** Device-aware LOD. Mobile lookdev is not the Unreal/Unity/Blender sim. */

export type LodTier = "low" | "medium" | "ultra";

export type DeviceHints = {
  deviceMemory?: number;
  hardwareConcurrency?: number;
  devicePixelRatio?: number;
  saveData?: boolean;
  userAgent?: string;
  innerWidth?: number;
  prefersReducedMotion?: boolean;
};

export type LodConfig = {
  tier: LodTier;
  maxPitch: number;
  terrain: boolean;
  buildings: boolean;
  sky: boolean;
  hillshade: boolean;
  pixelRatio: number;
  maxZoom: number;
  buildingMinZoom: number;
  animation: boolean;
  lights: boolean;
  fadeDuration: number;
  maxTileCacheSize: number;
  mosaicRadius: number;
  mosaicZoom: number;
};

const S25_ULTRA = /SM-S938/i;

export function detectTier(h: DeviceHints): LodTier {
  if (S25_ULTRA.test(h.userAgent ?? "")) return "ultra";
  if (h.saveData) return "low";
  const mem = h.deviceMemory ?? 4;
  const cores = h.hardwareConcurrency ?? 4;
  const width = h.innerWidth ?? 390;
  if (mem >= 8 && cores >= 8) return "ultra";
  if (mem >= 4 && cores >= 6 && width >= 700) return "medium";
  if (mem >= 4 && cores >= 6) return "medium";
  return "low";
}

export function lodConfig(h: DeviceHints): LodConfig {
  const tier = detectTier(h);
  const dpr = Math.min(h.devicePixelRatio ?? 1, tier === "ultra" ? 2.25 : 1.75);
  const motion = !(h.prefersReducedMotion ?? false);
  if (tier === "ultra") {
    return {
      tier,
      maxPitch: 78,
      terrain: true,
      buildings: true,
      sky: true,
      hillshade: true,
      pixelRatio: dpr,
      maxZoom: 17.5,
      buildingMinZoom: 13.5,
      animation: motion,
      lights: true,
      fadeDuration: 0,
      maxTileCacheSize: 96,
      mosaicRadius: 2,
      mosaicZoom: 16,
    };
  }
  if (tier === "medium") {
    return {
      tier,
      maxPitch: 60,
      terrain: false,
      buildings: true,
      sky: true,
      hillshade: false,
      pixelRatio: Math.min(dpr, 1.75),
      maxZoom: 16.5,
      buildingMinZoom: 14.5,
      animation: motion,
      lights: false,
      fadeDuration: 0,
      maxTileCacheSize: 48,
      mosaicRadius: 1,
      mosaicZoom: 15,
    };
  }
  return {
    tier,
    maxPitch: 45,
    terrain: false,
    buildings: false,
    sky: false,
    hillshade: false,
    pixelRatio: Math.min(dpr, 1.25),
    maxZoom: 15.5,
    buildingMinZoom: 99,
    animation: false,
    lights: false,
    fadeDuration: 0,
    maxTileCacheSize: 24,
    mosaicRadius: 1,
    mosaicZoom: 14,
  };
}

export function readDeviceHints(
  nav: {
    userAgent?: string;
    deviceMemory?: number;
    hardwareConcurrency?: number;
    connection?: { saveData?: boolean };
  } = {},
  win: {
    devicePixelRatio?: number;
    innerWidth?: number;
    matchMedia?: (q: string) => { matches: boolean };
  } = {},
): DeviceHints {
  return {
    userAgent: nav.userAgent,
    deviceMemory: nav.deviceMemory,
    hardwareConcurrency: nav.hardwareConcurrency,
    saveData: Boolean(nav.connection?.saveData),
    devicePixelRatio: win.devicePixelRatio,
    innerWidth: win.innerWidth,
    prefersReducedMotion: win.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false,
  };
}
