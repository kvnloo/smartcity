import { describe, expect, it } from "vitest";
import { fillTemplate, lonLatToTile, mosaicCells, mosaicSize } from "./tiles";

describe("lonLatToTile", () => {
  it("pins Naperville at z15 to the Esri tile we probed", () => {
    expect(lonLatToTile(-88.147, 41.75, 15)).toEqual({ x: 8360, y: 12194 });
  });

  it("keeps the Loop on a neighboring column at z15", () => {
    const nape = lonLatToTile(-88.147, 41.75, 15);
    const loop = lonLatToTile(-87.629, 41.882, 15);
    expect(loop.x).toBeGreaterThan(nape.x);
    expect(loop.y).toBeLessThan(nape.y);
  });
});

describe("mosaic", () => {
  it("is a square of (2r+1)^2 cells centered on the origin tile", () => {
    const cells = mosaicCells(-88.147, 41.75, 15, 1);
    expect(cells).toHaveLength(9);
    expect(mosaicSize(1)).toBe(3);
    expect(cells[4]).toMatchObject({ x: 8360, y: 12194, col: 1, row: 1 });
  });

  it("fills Esri {z}/{y}/{x} in that order", () => {
    expect(fillTemplate("https://example/{z}/{y}/{x}", 15, 8360, 12194)).toBe(
      "https://example/15/12194/8360",
    );
  });
});
