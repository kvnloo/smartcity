export type Lane = {
  id: string;
  name: string;
  direction: string;
  inbound_mult: number;
  outbound_mult: number;
  fictional?: boolean;
};

export type Corridor = {
  id: string;
  name: string;
  tti: number;
  speed_mph: number;
  inbound_vph: number;
  outbound_vph: number;
  mode?: string;
};

export type FidelityRing = {
  name: string;
  engine: string;
};

export type TwinLookdev = {
  clock: string;
  weekday_name: string;
  lanes: Lane[];
  corridors: Corridor[];
  fidelity?: FidelityRing[];
};

export function formatClock(weekday: string, clock: string): string {
  return `${weekday} ${clock}`.trim();
}

export function hottestCorridor(rows: Corridor[]): Corridor | undefined {
  return [...rows].sort((a, b) => b.tti - a.tti || b.inbound_vph - a.inbound_vph)[0];
}

export function laneLine(lane: Lane): string {
  const tag = lane.fictional ? "proposed" : "IDOT";
  return `${lane.name} · ${lane.direction} · ×${lane.inbound_mult} in · ${tag}`;
}

export function ttiTone(tti: number): "clear" | "busy" | "jam" {
  if (tti >= 1.55) return "jam";
  if (tti >= 1.2) return "busy";
  return "clear";
}

/** Device LOD pill. Never the nested-engine strip — that is `#fidelity`. */
export function lodChipLine(tier: string): string {
  return `LOD · ${tier}`;
}

export function fidelityLine(rings: FidelityRing[] = []): string {
  const shortEngine = (engine: string): string => {
    const raw = engine.split(/[+]/)[0]!.trim().toLowerCase();
    if (raw.startsWith("unreal")) return "Unreal";
    if (raw.startsWith("sumo meso") || raw.includes("ctm")) return "CTM";
    if (raw.startsWith("sumo")) return "SUMO";
    if (raw.includes("od")) return "OD";
    return raw.split(/[\s_]/)[0] ?? raw;
  };
  return rings.map((r) => `${r.name} ${shortEngine(r.engine)}`).join(" · ");
}
