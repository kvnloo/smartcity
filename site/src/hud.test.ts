import { describe, expect, it } from "vitest";
import { fidelityLine, formatClock, hottestCorridor, laneLine, lodChipLine, ttiTone } from "./hud";

describe("hud", () => {
  it("formats the world clock", () => {
    expect(formatClock("Mon", "07:30")).toBe("Mon 07:30");
  });

  it("picks the most congested spine", () => {
    const hot = hottestCorridor([
      { id: "i88", name: "I-88", tti: 1.8, speed_mph: 30, inbound_vph: 4000, outbound_vph: 800 },
      { id: "i90", name: "Kennedy", tti: 1.2, speed_mph: 45, inbound_vph: 9000, outbound_vph: 1000 },
    ]);
    expect(hot?.id).toBe("i88");
  });

  it("marks proposed zipper lanes", () => {
    expect(laneLine({ id: "i88-solarpunk", name: "I-88 spine", direction: "inbound", inbound_mult: 1.22, outbound_mult: 0.88, fictional: true })).toMatch(/proposed/);
  });

  it("tones TTI for the HUD", () => {
    expect(ttiTone(1.05)).toBe("clear");
    expect(ttiTone(1.3)).toBe("busy");
    expect(ttiTone(1.9)).toBe("jam");
  });

  it("compresses nested engines for the lookdev strip", () => {
    expect(
      fidelityLine([
        { name: "hero", engine: "unreal_nanite + blender_mesh" },
        { name: "micro", engine: "sumo + slot AIM" },
      ]),
    ).toBe("hero Unreal · micro SUMO");
  });

  it("keeps fidelity mixed-case — never an uppercase LOD clone", () => {
    const line = fidelityLine([
      { name: "hero", engine: "unreal_nanite + blender_mesh" },
      { name: "micro", engine: "sumo + slot AIM" },
      { name: "meso", engine: "sumo meso / CTM" },
      { name: "macro", engine: "od_flow" },
    ]);
    expect(line).toMatch(/^hero Unreal · micro SUMO/);
    expect(line).not.toBe(line.toUpperCase());
    expect(line.startsWith("HERO")).toBe(false);
  });

  it("prints only the device LOD tier on the chip", () => {
    expect(lodChipLine("ultra")).toBe("LOD · ultra");
    expect(lodChipLine("low")).toBe("LOD · low");
    expect(lodChipLine("low")).not.toMatch(/lookdev|unity|unreal|sumo/i);
    expect(lodChipLine("ultra")).not.toBe(
      fidelityLine([
        { name: "hero", engine: "unreal_nanite" },
        { name: "micro", engine: "sumo" },
      ]),
    );
  });
});
