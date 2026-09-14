import { describe, expect, it } from "vitest";
import { lodConfig } from "./lod";
import { lookdevStyle } from "./style";

describe("lookdevStyle", () => {
  it("keeps low tier as satellite only — no DEM, no mesh", () => {
    const style = lookdevStyle(lodConfig({ deviceMemory: 2, hardwareConcurrency: 2 }));
    expect(style.sources.s2).toBeTruthy();
    expect(style.sources.esri).toBeTruthy();
    expect(style.sources.terrain).toBeUndefined();
    expect(style.terrain).toBeUndefined();
    expect(style.sky).toBeUndefined();
    expect(style.layers.some((l) => l.id === "building-3d")).toBe(false);
  });

  it("adds DEM, extrusion, sky fog, and morning light for ultra / S25", () => {
    const style = lookdevStyle(lodConfig({ userAgent: "SM-S938B" }));
    expect(style.sources.terrain).toBeTruthy();
    expect(style.sources.openmaptiles).toBeTruthy();
    expect(style.layers.map((l) => l.id)).toEqual(
      expect.arrayContaining(["s2", "esri", "building-3d", "hillshade"]),
    );
    expect(style.sky).toBeTruthy();
    expect(style.light).toBeTruthy();
    expect(style.terrain?.source).toBe("terrain");
  });
});
