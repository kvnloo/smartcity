import { describe, expect, it } from "vitest";
import { lodConfig } from "./lod";
import { lookdevStyle } from "./style";
import { ESRI_IMAGERY, OSM_TILEJSON, S2_CLOUDLESS, TERRARIUM_DEM } from "./tiles";

function hexRgb(hex: string): { r: number; g: number; b: number } {
  const h = hex.replace("#", "");
  return {
    r: Number.parseInt(h.slice(0, 2), 16),
    g: Number.parseInt(h.slice(2, 4), 16),
    b: Number.parseInt(h.slice(4, 6), 16),
  };
}

function layerPaint(style: ReturnType<typeof lookdevStyle>, id: string) {
  const layer = style.layers.find((l) => l.id === id);
  expect(layer, id).toBeTruthy();
  return (layer as { paint?: Record<string, unknown> }).paint ?? {};
}

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

  it("grades Esri toward 07:30 warmth without Google tiles", () => {
    const style = lookdevStyle(lodConfig({ userAgent: "SM-S938B" }));
    const esri = layerPaint(style, "esri");
    expect(esri["raster-hue-rotate"]).toBeGreaterThan(0);
    expect(esri["raster-hue-rotate"]).toBeLessThan(25);
    expect(esri["raster-brightness-max"]).toBeLessThan(1);
    expect(esri["raster-resampling"]).toBe("linear");
    const urls = [ESRI_IMAGERY, S2_CLOUDLESS, TERRARIUM_DEM, OSM_TILEJSON, JSON.stringify(style.sources)];
    for (const u of urls) {
      expect(u).not.toMatch(/google|gstatic|googleapis|photorealistic/i);
    }
  });

  it("lights extruded masses from a low eastern sun", () => {
    const style = lookdevStyle(lodConfig({ userAgent: "SM-S938U" }));
    expect(style.light?.anchor).toBe("map");
    const pos = style.light?.position as [number, number, number];
    expect(pos[1]).toBeGreaterThanOrEqual(80);
    expect(pos[1]).toBeLessThanOrEqual(125);
    expect(pos[2]).toBeGreaterThanOrEqual(65);
    const hill = layerPaint(style, "hillshade");
    expect(hill["hillshade-illumination-direction"]).toBeGreaterThanOrEqual(80);
    expect(hill["hillshade-illumination-direction"]).toBeLessThanOrEqual(125);
    expect(hill["hillshade-illumination-anchor"]).toBe("map");
  });

  it("uses a dawn sky whose horizon is warmer than the zenith", () => {
    const sky = lookdevStyle(lodConfig({ userAgent: "SM-S938B" })).sky!;
    const zenith = hexRgb(String(sky["sky-color"]));
    const horizon = hexRgb(String(sky["horizon-color"]));
    expect(horizon.r).toBeGreaterThan(zenith.r);
    expect(horizon.r).toBeGreaterThan(200);
    expect(zenith.b).toBeGreaterThan(zenith.r);
  });

  it("grounds limestone extrusions on the aerial", () => {
    const style = lookdevStyle(lodConfig({ userAgent: "SM-S938B" }));
    const ids = style.layers.map((l) => l.id);
    expect(ids.indexOf("building-footprint")).toBeGreaterThan(-1);
    expect(ids.indexOf("building-footprint")).toBeLessThan(ids.indexOf("building-3d"));
    const extrusion = layerPaint(style, "building-3d");
    expect(extrusion["fill-extrusion-vertical-gradient"]).toBe(true);
    expect(extrusion["fill-extrusion-opacity"]).toBeGreaterThanOrEqual(0.8);
    expect(extrusion["fill-extrusion-opacity"]).toBeLessThan(1);
  });
});
