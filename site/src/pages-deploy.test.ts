import { describe, expect, it } from "vitest";
import viteConfig from "../vite.config";

describe("GitHub Pages packaging", () => {
  it("keeps a relative Vite base so project Pages resolve", () => {
    expect(viteConfig.base).toBe("./");
  });
});
