# Light Traffic

Interactive recreation of the autonomous-intersection idea from MIT Senseable City Lab’s 2016 paper **[Revisiting Street Intersections Using Slot-Based Systems](https://doi.org/10.1371/journal.pone.0149607)** (Tachet, Santi, Sobolevsky, Reyes-Castro, Frazzoli, Helbing, Ratti).

If every car is autonomous and talking to an intersection manager, traffic lights are optional. Vehicles request a time slot, slow on the approach, then thread the box at around **45 mph** while the next stream zips through the gaps. On the avenues they can cruise much faster — the **90–120 mph** picture people remember from the viral clips. That speed pair is a popular reading of an AV-only city, not a posted limit in the paper. The paper’s actual claim is about **capacity and delay**: a slot/batch controller can about **double** intersection throughput versus fixed lights and cut waiting far more, because the yellow “setup” shrinks to ~1.5 seconds.

This app puts that side by side with a conventional signal so you can see queues form on the left and a weave on the right.

## Run locally

```bash
npm install
npm run dev
```

Open [http://127.0.0.1:43217](http://127.0.0.1:43217).

## What the controls do

- **Split / Slot-based / Traffic lights** — compare or isolate each controller
- **Density** — Poisson arrivals per lane
- **Cruise / Crossing** — highway-block speed vs weave speed (slot side)
- **Today vs tomorrow speeds** — lights stay at a 35 mph city limit, or both sides use the same numbers
- **Camera** — zoom from the approach roads into the reserved tile grid

Space pauses. Reset reseeds both worlds together.

## Papers

- Tachet et al., *PLOS ONE* (2016): [doi:10.1371/journal.pone.0149607](https://doi.org/10.1371/journal.pone.0149607)
- [MIT News write-up](https://news.mit.edu/2016/no-traffic-lights-communicating-vehicles-intersections-more-efficiently-0317)
- Dresner & Stone, *JAIR* (2008), Autonomous Intersection Management — the tile-reservation weave this sim uses for the visual
- [DriveWAVE](https://senseable.mit.edu/wave/) — Senseable City Lab’s later physical installation

The 2016 model is a two-road analytical crossing with FAIR (FCFS) and BATCH (adaptive platoons) versus FIXED signals. It does not include pedestrians, cyclists, or mixed human traffic. One manually driven car would break the schedule.
