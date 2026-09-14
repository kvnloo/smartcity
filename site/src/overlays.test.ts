import { describe, expect, it } from "vitest";
import { corridorLayers, districtLayers, ringLayers } from "./overlays";

describe("twin overlays", () => {
  it("paints nested rings as a metro diagram that fades at street zoom", () => {
    const ids = ringLayers().map((l) => l.id);
    expect(ids).toEqual(expect.arrayContaining(["rings-fill", "rings-glow", "rings", "ring-names"]));
    const line = ringLayers().find((l) => l.id === "rings");
    expect(line?.type).toBe("line");
    if (line?.type === "line") {
      expect(JSON.stringify(line.paint?.["line-opacity"])).toContain("zoom");
    }
    const fill = ringLayers().find((l) => l.id === "rings-fill");
    expect(fill?.type).toBe("fill");
    if (fill?.type === "fill") {
      expect(fill.maxzoom).toBeLessThanOrEqual(14.5);
    }
  });

  it("labels rings with lowercase names plus kilometres, not an uppercase LOD chip", () => {
    const names = ringLayers().find((l) => l.id === "ring-names");
    expect(names?.type).toBe("symbol");
    if (names?.type === "symbol") {
      const field = JSON.stringify(names.layout?.["text-field"]);
      expect(field).toMatch(/name/);
      expect(field).toMatch(/km/);
      expect(field).not.toMatch(/uppercase|upcase/i);
    }
  });

  it("keeps corridor glow under the spine and districts as job/dwell dots", () => {
    expect(corridorLayers().map((l) => l.id)).toEqual(["corridors-glow", "corridors"]);
    expect(districtLayers().some((l) => l.id === "district-names")).toBe(true);
  });
});
