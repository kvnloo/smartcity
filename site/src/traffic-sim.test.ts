import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { runInNewContext } from "node:vm";
import { describe, expect, it } from "vitest";

// The FSD phantom-jam demo is a static page under public/ so Vite copies it
// into dist/ and Pages serves it at ./traffic-sim/. It is a teaching demo,
// not the SUMO twin.
const dir = dirname(fileURLToPath(import.meta.url));
const simDir = join(dir, "..", "public", "traffic-sim");

// Run sim.js the way the browser does (classic script setting a global), in a
// fresh context, so the test exercises the exact shipped file.
function loadSim(): SimApi {
  const ctx: { TrafficSim?: SimApi } = {};
  runInNewContext(readFileSync(join(simDir, "sim.js"), "utf8"), ctx);
  if (!ctx.TrafficSim) throw new Error("sim.js did not define TrafficSim");
  return ctx.TrafficSim;
}

type Ring = {
  t: number;
  n: number;
  L: number;
  x: Float64Array;
  v: Float64Array;
  stops: number;
  step(): void;
  stats(): { mean: number; min: number; sd: number; flow: number };
};
type SimApi = {
  Ring: new (o: { length: number; n: number; seed: number; fsdMask: boolean[] }) => Ring;
  spreadMask(n: number, count: number): boolean[];
  CAR_LEN: number;
};

const N = 34;
const LEN = 600;

function run(sim: SimApi, fsdShare: number, seed: number) {
  const r = new sim.Ring({
    length: LEN,
    n: N,
    seed,
    fsdMask: sim.spreadMask(N, Math.round(fsdShare * N)),
  });
  // Humans-only jams form between 120 and 180 s of sim time (seeds 1-3, 7).
  while (r.t < 180) r.step(); // warm-up
  const stops0 = r.stops;
  let speed = 0;
  let flow = 0;
  let samples = 0;
  let minGap = Infinity;
  let finite = true;
  while (r.t < 240) {
    r.step();
    const s = r.stats();
    speed += s.mean;
    flow += s.flow;
    samples++;
    for (let i = 0; i < r.n; i++) {
      let d = r.x[(i + 1) % r.n] - r.x[i];
      if (d <= 0) d += r.L;
      minGap = Math.min(minGap, d - sim.CAR_LEN);
      finite &&= Number.isFinite(r.x[i]) && Number.isFinite(r.v[i]);
    }
  }
  return { kmh: (speed / samples) * 3.6, flow: flow / samples, stops: r.stops - stops0, minGap, finite };
}

describe("FSD phantom-jam sim", () => {
  it("ships as a static page with a top-down canvas, FSD share slider and live readouts", () => {
    const html = readFileSync(join(simDir, "index.html"), "utf8");
    expect(existsSync(join(simDir, "sim.js"))).toBe(true);
    expect(html).toMatch(/<canvas id="cL"/);
    expect(html).toMatch(/<canvas id="cR"/);
    expect(html).toMatch(/id="share" type="range"/);
    expect(html).toMatch(/cars\/h/); // throughput readout
    expect(html).toMatch(/avg km\/h/); // mean speed readout
    expect(html).toMatch(/src="\.\/sim\.js"/); // relative, works under /smartcity/
  });

  it("grows phantom jams with humans only and dissolves them with 20% FSD", () => {
    const sim = loadSim();
    for (const seed of [1, 2, 3]) {
      const human = run(sim, 0, seed);
      const mixed = run(sim, 0.2, seed);
      const allFsd = run(sim, 1, seed);
      expect(human.stops).toBeGreaterThan(10); // stop-and-go out of nothing
      expect(mixed.stops).toBe(0);
      expect(allFsd.stops).toBe(0);
      expect(mixed.kmh).toBeGreaterThan(human.kmh);
      expect(mixed.flow).toBeGreaterThan(human.flow);
      for (const r of [human, mixed, allFsd]) {
        expect(r.minGap).toBeGreaterThan(0);
        expect(r.finite).toBe(true);
      }
    }
  }, 30_000); // 9 runs x 240 s of sim: ~2 s on a Mac, slower on CI runners

  it("is linked from the lookdev sheet", () => {
    const html = readFileSync(join(dir, "..", "index.html"), "utf8");
    expect(html).toMatch(/href="\.\/traffic-sim\/"/);
  });
});
