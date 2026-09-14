import type { SimSnapshot } from "@/lib/sim/engine";
import {
  CAR_LENGTH,
  CAR_WIDTH,
  PATH_HALF,
  TILES,
  boxSize,
  pose,
} from "@/lib/sim/geometry";

export function IntersectionView({
  snapshot,
  zoom,
  label,
}: {
  snapshot: SimSnapshot;
  zoom: number;
  label: string;
}) {
  const view = PATH_HALF * 2 / zoom;
  const half = view / 2;
  const road = boxSize() / 2;
  const span = PATH_HALF + 8;
  const slot = snapshot.mode === "slot";

  return (
    <div className="relative h-[min(64vh,680px)] min-h-[380px] w-full overflow-hidden rounded-2xl bg-[#152033] ring-1 ring-white/15">
      <svg viewBox={`${-half} ${-half} ${view} ${view}`} className="h-full w-full" role="img" aria-label={label}>
        <rect x={-half} y={-half} width={view} height={view} fill="#152033" />
        <rect x={-road} y={-span} width={road * 2} height={span * 2} fill="#2c364c" />
        <rect x={-span} y={-road} width={span * 2} height={road * 2} fill="#2c364c" />
        <rect x={-road} y={-span} width={road * 2} height={span * 2} fill="none" stroke="#7b8cb0" strokeWidth={0.35} />
        <rect x={-span} y={-road} width={span * 2} height={road * 2} fill="none" stroke="#7b8cb0" strokeWidth={0.35} />
        <line x1={0} y1={-span} x2={0} y2={-road} stroke="rgba(230,240,255,0.45)" strokeWidth={0.22} strokeDasharray="1.4 1.8" />
        <line x1={0} y1={road} x2={0} y2={span} stroke="rgba(230,240,255,0.45)" strokeWidth={0.22} strokeDasharray="1.4 1.8" />
        <line x1={-span} y1={0} x2={-road} y2={0} stroke="rgba(230,240,255,0.45)" strokeWidth={0.22} strokeDasharray="1.4 1.8" />
        <line x1={road} y1={0} x2={span} y2={0} stroke="rgba(230,240,255,0.45)" strokeWidth={0.22} strokeDasharray="1.4 1.8" />

        {slot ? <SlotGrid road={road} /> : <rect x={-road} y={-road} width={road * 2} height={road * 2} fill="rgba(255,210,90,0.08)" />}
        {snapshot.mode === "lights" ? <TrafficLights phase={snapshot.light} road={road} /> : null}

        {snapshot.cars.map((car) => {
          const p = pose(car.dir, car.lane, car.s);
          return (
            <g key={car.id} transform={`translate(${p.x} ${p.y}) rotate(${(p.heading * 180) / Math.PI})`}>
              <rect
                x={-CAR_LENGTH / 2}
                y={-CAR_WIDTH / 2}
                width={CAR_LENGTH}
                height={CAR_WIDTH}
                rx={0.4}
                fill={car.color}
                stroke="rgba(255,255,255,0.35)"
                strokeWidth={0.12}
              />
              <rect x={CAR_LENGTH / 2 - 0.45} y={-CAR_WIDTH * 0.28} width={0.35} height={0.35} fill="#fff6d8" />
              <rect x={CAR_LENGTH / 2 - 0.45} y={CAR_WIDTH * 0.08} width={0.35} height={0.35} fill="#fff6d8" />
            </g>
          );
        })}
      </svg>
      <div
        className={`absolute top-3 left-3 rounded-lg px-2.5 py-1 text-xs font-medium ${
          slot ? "bg-black/50 text-cyan-200" : "bg-black/50 text-amber-200"
        }`}
      >
        {label}
      </div>
    </div>
  );
}

function SlotGrid({ road }: { road: number }) {
  const size = (road * 2) / TILES;
  const lines = Array.from({ length: TILES + 1 }, (_, i) => -road + i * size);
  return (
    <g>
      <rect x={-road} y={-road} width={road * 2} height={road * 2} fill="rgba(80,220,255,0.08)" />
      {lines.map((p) => (
        <g key={p}>
          <line x1={-road} y1={p} x2={road} y2={p} stroke="rgba(90,230,255,0.28)" strokeWidth={0.12} />
          <line x1={p} y1={-road} x2={p} y2={road} stroke="rgba(90,230,255,0.28)" strokeWidth={0.12} />
        </g>
      ))}
    </g>
  );
}

function TrafficLights({
  phase,
  road,
}: {
  phase: SimSnapshot["light"];
  road: number;
}) {
  const ns = phase === "NS_GREEN" || phase === "NS_YELLOW";
  const ew = phase === "EW_GREEN" || phase === "EW_YELLOW";
  const nsColor = phase === "NS_YELLOW" ? "#FFD24A" : phase === "NS_GREEN" ? "#3DFF9A" : "#FF4D5A";
  const ewColor = phase === "EW_YELLOW" ? "#FFD24A" : phase === "EW_GREEN" ? "#3DFF9A" : "#FF4D5A";
  const posts = [
    { x: -road - 1.6, y: -road - 1.6, ns: true },
    { x: road + 1.6, y: road + 1.6, ns: true },
    { x: road + 1.6, y: -road - 1.6, ns: false },
    { x: -road - 1.6, y: road + 1.6, ns: false },
  ];
  return (
    <g>
      {posts.map((p, i) => (
        <circle
          key={i}
          cx={p.x}
          cy={p.y}
          r={1.15}
          fill={p.ns ? nsColor : ewColor}
          opacity={p.ns ? (ns ? 1 : 0.55) : ew ? 1 : 0.55}
        />
      ))}
    </g>
  );
}
