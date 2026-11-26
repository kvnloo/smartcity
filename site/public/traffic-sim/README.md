# FSD phantom-jam sim (teaching demo)

Top-down view of two identical 600 m ring roads with 34 cars each. No accident,
no bottleneck. The left road is human drivers only. The right road mixes in a
share of FSD cars (slider, 0–100 %).

- Humans: Intelligent Driver Model (Treiber 2000) with a 0.7 s perception delay
  and throttle noise. Stop-and-go waves grow out of nothing (Sugiyama 2008).
- FSD: 0.1 s delay, no noise, looks 4 cars ahead, and caps its speed at the
  smoothed speed of traffic ahead, so it coasts into slowdowns. The gap it keeps
  absorbs the wave (Stern 2018 showed one automated car doing this on a real ring).

On the human road a jam forms after 2–3 minutes of sim time (under a minute of
wall time at the default 3× speed); the mixed road never forms one.

Readouts per road: average speed, throughput (cars/h past a point), slowest car,
full stops per minute. The strip under each road is a space-time plot; red
streaks are jam waves rolling backwards.

This is a static page in `site/public/`, so Vite copies it into `site/dist/` and
Pages serves it at `./traffic-sim/`. It is not the SUMO twin. `sim.js` has no DOM
and is tested in node by `site/src/traffic-sim.test.ts`.

Ported from `kvnloo/gods-eye-view@310d56b` (`downstream/traffic-sim/`).
