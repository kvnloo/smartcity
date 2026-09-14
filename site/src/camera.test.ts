import { describe, expect, it } from "vitest";
import { assertPathInRegion, clampPitch, lookdevPath } from "./camera";

describe("camera path", () => {
  it("never leaves the CMAP bbox", () => {
    expect(assertPathInRegion(lookdevPath(78))).toBe(true);
  });

  it("respects device maxPitch", () => {
    const path = lookdevPath(45);
    expect(Math.max(...path.map((b) => b.pitch))).toBeLessThanOrEqual(45);
  });

  it("starts and ends over Naperville", () => {
    const path = lookdevPath(70);
    expect(path[0].center[0]).toBeCloseTo(-88.147, 3);
    expect(path[path.length - 1].center[0]).toBeCloseTo(-88.147, 3);
  });

  it("clamps pitch into [0, max]", () => {
    expect(clampPitch(90, 60)).toBe(60);
    expect(clampPitch(-4, 60)).toBe(0);
  });
});
