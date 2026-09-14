import { describe, expect, it } from "vitest";
import { fidelityLine, formatClock, hottestCorridor, laneLine, ttiTone } from "./hud";

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
    ).toBe("hero unreal_nanite · micro sumo");
  });
});
