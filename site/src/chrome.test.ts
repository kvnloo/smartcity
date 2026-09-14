import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const dir = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(dir, "styles.css"), "utf8");
const html = readFileSync(join(dir, "..", "index.html"), "utf8");
const main = readFileSync(join(dir, "main.ts"), "utf8");
const tiles = readFileSync(join(dir, "tiles.ts"), "utf8");

function ruleBody(selector: string): string {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const m = css.match(new RegExp(`${escaped}\\s*\\{([^}]+)\\}`));
  return m?.[1] ?? "";
}

describe("lookdev chrome", () => {
  it("keeps the LOD chip in the header and fidelity in the sheet", () => {
    const lodAt = html.indexOf('id="lod-chip"');
    const fidAt = html.indexOf('id="fidelity"');
    const headerEnd = html.indexOf("</header>");
    const sheetAt = html.indexOf('class="hud sheet"');
    expect(lodAt).toBeGreaterThan(-1);
    expect(fidAt).toBeGreaterThan(-1);
    expect(lodAt).toBeLessThan(headerEnd);
    expect(fidAt).toBeGreaterThan(sheetAt);
  });

  it("does not uppercase the fidelity strip", () => {
    expect(ruleBody("#fidelity")).toMatch(/text-transform:\s*none/);
    expect(ruleBody("#fidelity")).not.toMatch(/text-transform:\s*uppercase/);
    expect(ruleBody(".chip")).toMatch(/text-transform:\s*uppercase/);
  });

  it("grades the viewport for 07:30 dawn", () => {
    expect(css).toMatch(/--dawn-sun:/);
    expect(ruleBody(".grade")).toMatch(/var\(--dawn-sun\)/);
    expect(ruleBody(".grade")).toMatch(/var\(--dawn-umbra\)/);
  });

  it("pads the 412×915 HUD with notch safe-areas", () => {
    expect(html).toMatch(/viewport-fit=cover/);
    expect(css).toMatch(/env\(safe-area-inset-top\)/);
    expect(css).toMatch(/env\(safe-area-inset-bottom\)/);
    expect(css).toMatch(/env\(safe-area-inset-left\)/);
    expect(css).toMatch(/max-width:\s*430px/);
    expect(css).toMatch(/min\(28dvh,\s*236px\)/);
  });

  it("code-splits MapLibre and never pulls Google tiles or a SUMO runtime", () => {
    expect(main).toMatch(/await import\(\s*["']maplibre-gl["']\s*\)/);
    expect(main).toMatch(/import\(\s*["']maplibre-gl\/dist\/maplibre-gl\.css["']\s*\)/);
    expect(main).not.toMatch(/^import\s+(?!type\s)[^;]*from\s+["']maplibre-gl["']/m);
    expect(main).not.toMatch(/^import\s+["']maplibre-gl\/dist\/maplibre-gl\.css["']/m);
    expect(main).toMatch(/maplibre-gl\/dist\/maplibre-gl\.css/);
    expect(main).not.toMatch(/from\s+["'][^"']*sumo/i);
    expect(tiles).not.toMatch(/google|gstatic|googleapis/i);
  });
});
