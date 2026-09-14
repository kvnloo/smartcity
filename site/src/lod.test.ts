import { describe, expect, it } from "vitest";
import { detectTier, lodConfig } from "./lod";

describe("detectTier", () => {
  it("forces ultra on Galaxy S25 Ultra UA", () => {
    expect(detectTier({ userAgent: "Mozilla/5.0 SM-S938B", deviceMemory: 2, hardwareConcurrency: 2 })).toBe("ultra");
  });

  it("drops to low when the user asked to save data", () => {
    expect(detectTier({ saveData: true, deviceMemory: 12, hardwareConcurrency: 8 })).toBe("low");
  });

  it("uses ultra for 8GB+/8-core class devices", () => {
    expect(detectTier({ deviceMemory: 8, hardwareConcurrency: 8 })).toBe("ultra");
  });

  it("uses low on tiny phones with 2GB", () => {
    expect(detectTier({ deviceMemory: 2, hardwareConcurrency: 4, innerWidth: 360 })).toBe("low");
  });
});

describe("lodConfig", () => {
  it("does not load terrain or 3D buildings on low", () => {
    const cfg = lodConfig({ deviceMemory: 2, hardwareConcurrency: 2, innerWidth: 360 });
    expect(cfg.terrain).toBe(false);
    expect(cfg.buildings).toBe(false);
    expect(cfg.animation).toBe(false);
    expect(cfg.maxTileCacheSize).toBeLessThanOrEqual(24);
    expect(cfg.mosaicZoom).toBeLessThanOrEqual(14);
  });

  it("gives S25 Ultra terrain, sky, buildings, and a steep pitch", () => {
    const cfg = lodConfig({ userAgent: "SM-S938U", devicePixelRatio: 3.5 });
    expect(cfg.tier).toBe("ultra");
    expect(cfg.terrain).toBe(true);
    expect(cfg.buildings).toBe(true);
    expect(cfg.sky).toBe(true);
    expect(cfg.maxPitch).toBeGreaterThan(70);
    expect(cfg.pixelRatio).toBeLessThanOrEqual(2.25);
  });

  it("disables camera ballet when reduced motion is set", () => {
    const cfg = lodConfig({ deviceMemory: 12, hardwareConcurrency: 8, prefersReducedMotion: true });
    expect(cfg.animation).toBe(false);
  });
});
