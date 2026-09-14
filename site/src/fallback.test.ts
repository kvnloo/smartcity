/** @vitest-environment jsdom */
import { describe, expect, it } from "vitest";
import { mountMosaic } from "./fallback";

describe("mountMosaic", () => {
  it("lays out a 3x3 Esri grid for radius 1", () => {
    const el = document.createElement("div");
    mountMosaic(el, { lon: -88.147, lat: 41.75, z: 15, radius: 1 });
    const imgs = [...el.querySelectorAll("img")];
    expect(imgs).toHaveLength(9);
    expect(el.style.gridTemplateColumns).toBe("repeat(3, 1fr)");
    expect(imgs[4].getAttribute("src")).toContain("/15/12194/8360");
  });
});
