import { useId } from "react";
import type { SimSnapshot } from "@/lib/sim/engine";
import {
  CAR_LENGTH,
  CAR_WIDTH,
  PATH_HALF,
  TILES,
  boxSize,
  mpsToMph,
  pose,
} from "@/lib/sim/geometry";

export function IntersectionView({
  snapshot,
  zoom,
  label,
  showTiles,
  showSpeeds,
}: {
  snapshot: SimSnapshot;
  zoom: number;
  label: string;
  showTiles: boolean;
  showSpeeds: boolean;
}) {
  const gid = useId().replace(/:/g, "");
  const view = (PATH_HALF * 2) / zoom;
  const half = view / 2;
  const road = boxSize() / 2;
  const span = PATH_HALF + 8;
  const slot = snapshot.mode === "slot";
  const carLen = CAR_LENGTH * 2.25;
  const carWid = CAR_WIDTH * 2.2;
  const nightId = `night-${gid}`;

  return (
    <div className="relative h-[min(64vh,680px)] min-h-[380px] w-full overflow-hidden rounded-2xl bg-[#152033] ring-1 ring-white/15">
      <svg viewBox={`${-half} ${-half} ${view} ${view}`} className="h-full w-full" role="img" aria-label={label}>
        <defs>
          <radialGradient id={nightId} cx="50%" cy="42%" r="72%">
            <stop offset="0%" stopColor="#2a3c5c" />
            <stop offset="55%" stopColor="#152033" />
            <stop offset="100%" stopColor="#0a1018" />
          </radialGradient>
        </defs>
        <rect x={-half} y={-half} width={view} height={view} fill={`url(#${nightId})`} />
        <rect x={-road} y={-span} width={road * 2} height={span * 2} fill="#4a5d7e" />
        <rect x={-span} y={-road} width={span * 2} height={road * 2} fill="#4a5d7e" />
        <rect
          x={-road}
          y={-span}
          width={road * 2}
          height={span * 2}
          fill="none"
          stroke="#9eb4d6"
          strokeWidth={0.4}
        />
        <rect
          x={-span}
          y={-road}
          width={span * 2}
          height={road * 2}
          fill="none"
          stroke="#9eb4d6"
          strokeWidth={0.4}
        />
        <line
          x1={0}
          y1={-span}
          x2={0}
          y2={-road}
          stroke="rgba(236,244,255,0.7)"
          strokeWidth={0.28}
          strokeDasharray="1.4 1.8"
        />
        <line
          x1={0}
          y1={road}
          x2={0}
          y2={span}
          stroke="rgba(236,244,255,0.7)"
          strokeWidth={0.28}
          strokeDasharray="1.4 1.8"
        />
        <line
          x1={-span}
          y1={0}
          x2={-road}
          y2={0}
          stroke="rgba(236,244,255,0.7)"
          strokeWidth={0.28}
          strokeDasharray="1.4 1.8"
        />
        <line
          x1={road}
          y1={0}
          x2={span}
          y2={0}
          stroke="rgba(236,244,255,0.7)"
          strokeWidth={0.28}
          strokeDasharray="1.4 1.8"
        />

        {slot && showTiles ? (
          <SlotGrid road={road} />
        ) : (
          <rect x={-road} y={-road} width={road * 2} height={road * 2} fill="rgba(255,210,90,0.08)" />
        )}
        {snapshot.mode === "lights" ? <TrafficLights phase={snapshot.light} road={road} /> : null}

        {snapshot.cars.map((car) => {
          const p = pose(car.dir, car.lane, car.s);
          const mph = Math.round(mpsToMph(car.v));
          return (
            <g key={car.id}>
              <g transform={`translate(${p.x} ${p.y}) rotate(${(p.heading * 180) / Math.PI})`}>
                <rect
                  x={-carLen / 2}
                  y={-carWid / 2}
                  width={carLen}
                  height={carWid}
                  rx={0.55}
                  fill={car.color}
                  stroke="#ffffff"
                  strokeWidth={0.28}
                />
                <rect
                  x={carLen / 2 - 0.7}
                  y={-carWid * 0.28}
                  width={0.5}
                  height={0.42}
                  fill="#fff6d8"
                />
                <rect
                  x={carLen / 2 - 0.7}
                  y={carWid * 0.08}
                  width={0.5}
                  height={0.42}
                  fill="#fff6d8"
                />
              </g>
              {showSpeeds ? (
                <text
                  x={p.x + 1.2}
                  y={p.y - 2.2}
                  fill="rgba(235,244,255,0.9)"
                  fontSize={2.4}
                  fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace"
                >
                  {mph}
                </text>
              ) : null}
            </g>
          );
        })}
      </svg>
      <div
        className={`absolute top-3 left-3 rounded-lg px-2.5 py-1 text-xs font-medium ${
          slot ? "bg-black/50 text-cyan-200" : "bg-black/50 text-amber-200"
        }`}
      >
        {label} · {snapshot.cars.length} vehicles · {Math.round(snapshot.meanMph)} mph
      </div>
    </div>
  );
}

function SlotGrid({ road }: { road: number }) {
  const size = (road * 2) / TILES;
  const lines = Array.from({ length: TILES + 1 }, (_, i) => -road + i * size);
  return (
    <g>
      <rect x={-road} y={-road} width={road * 2} height={road * 2} fill="rgba(80,220,255,0.12)" />
      {lines.map((p) => (
        <g key={p}>
          <line x1={-road} y1={p} x2={road} y2={p} stroke="rgba(90,230,255,0.35)" strokeWidth={0.14} />
          <line x1={p} y1={-road} x2={p} y2={road} stroke="rgba(90,230,255,0.35)" strokeWidth={0.14} />
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
    { x: -road - 2.2, y: -road - 2.2, ns: true },
    { x: road + 2.2, y: road + 2.2, ns: true },
    { x: road + 2.2, y: -road - 2.2, ns: false },
    { x: -road - 2.2, y: road + 2.2, ns: false },
  ];
  return (
    <g>
      {posts.map((p, i) => (
        <g key={i}>
          <rect x={p.x - 1.1} y={p.y - 2.4} width={2.2} height={4.8} rx={0.45} fill="#0d1118" />
          <circle
            cx={p.x}
            cy={p.y}
            r={1.45}
            fill={p.ns ? nsColor : ewColor}
            opacity={p.ns ? (ns ? 1 : 0.45) : ew ? 1 : 0.45}
          />
        </g>
      ))}
    </g>
  );
}
