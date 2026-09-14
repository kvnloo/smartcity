"use client";

import { useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import { Pause, Play, RotateCcw } from "lucide-react";
import { SimCanvas } from "@/components/sim-canvas";
import { PaperPanel } from "@/components/paper-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { TrafficSim, type SimSnapshot } from "@/lib/sim/engine";
import { DEFAULT_CONFIG, type SimConfig, type SpeedRegime, type ViewMode } from "@/lib/sim/geometry";

const EMPTY: SimSnapshot = {
  time: 0,
  cars: [],
  mode: "slot",
  light: "NS_GREEN",
  collisions: 0,
  completed: 0,
  stopped: 0,
  meanMph: 0,
  throughputPerHour: 0,
  meanDelay: 0,
  queueMeters: 0,
};

export function CitySim() {
  const [view, setView] = useState<ViewMode>("split");
  const [paused, setPaused] = useState(false);
  const [zoom, setZoom] = useState(2.05);
  const [config, setConfig] = useState<SimConfig>(DEFAULT_CONFIG);
  const [slotStats, setSlotStats] = useState<SimSnapshot>(EMPTY);
  const [lightStats, setLightStats] = useState<SimSnapshot>(EMPTY);
  const seedRef = useRef(7);
  const slotSimRef = useRef(new TrafficSim({ ...DEFAULT_CONFIG, mode: "slot" }, 7));
  const lightSimRef = useRef(new TrafficSim({ ...DEFAULT_CONFIG, mode: "lights" }, 7));

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.code === "Space" && !(e.target instanceof HTMLInputElement)) {
        e.preventDefault();
        setPaused((p) => !p);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const reset = () => {
    seedRef.current += 1;
    slotSimRef.current.reset(seedRef.current);
    lightSimRef.current.reset(seedRef.current);
    slotSimRef.current.setConfig({ ...config, mode: "slot" });
    lightSimRef.current.setConfig({ ...config, mode: "lights" });
    setSlotStats(EMPTY);
    setLightStats(EMPTY);
  };

  const patch = (partial: Partial<SimConfig>) => setConfig((c) => ({ ...c, ...partial }));
  const showSlot = view !== "lights";
  const showLights = view !== "slot";

  return (
    <div className="flex flex-1 flex-col">
      <header className="flex flex-col gap-4 border-b border-white/10 px-4 py-4 sm:px-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          <p className="mb-1 text-[11px] font-medium tracking-[0.22em] text-cyan-300/80 uppercase">
            Light Traffic
          </p>
          <h1 className="font-heading text-3xl leading-none tracking-tight text-zinc-50 sm:text-4xl">
            A city that never hits a red light
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-zinc-400 sm:text-base">
            Autonomous cars cruise at highway speed, then drop to about 45 mph and thread a
            reserved slot. Switch on today&apos;s signals to watch the same intersection stall.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <ModeButton active={view === "split"} onClick={() => setView("split")}>
            Split
          </ModeButton>
          <ModeButton active={view === "slot"} onClick={() => setView("slot")}>
            Slot-based
          </ModeButton>
          <ModeButton active={view === "lights"} onClick={() => setView("lights")}>
            Traffic lights
          </ModeButton>
        </div>
      </header>

      <div className="grid flex-1 gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_340px] lg:p-5">
        <section className="flex min-h-[520px] flex-col gap-3">
          <div className={`grid min-h-[440px] flex-1 gap-3 ${showSlot && showLights ? "lg:grid-cols-2" : ""}`}>
            <SimPane
              className={showLights ? "" : "hidden"}
              simRef={lightSimRef}
              config={{ ...config, mode: "lights" }}
              paused={paused}
              zoom={zoom}
              label="Traffic lights"
              stats={lightStats}
              onStats={setLightStats}
              empty={config.arrivalPerLane <= 0.01}
            />
            <SimPane
              className={showSlot ? "" : "hidden"}
              simRef={slotSimRef}
              config={{ ...config, mode: "slot" }}
              paused={paused}
              zoom={zoom}
              label="Slot-based weave"
              stats={slotStats}
              onStats={setSlotStats}
              empty={config.arrivalPerLane <= 0.01}
            />
          </div>
          {paused ? (
            <div className="rounded-lg border border-amber-400/20 bg-amber-400/10 px-3 py-2 text-sm text-amber-100">
              Paused — press space or play to resume.
            </div>
          ) : null}
        </section>

        <aside className="flex flex-col gap-4">
          <Card className="border-white/10 bg-card/70 backdrop-blur-md">
            <CardContent className="space-y-5 pt-5">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <div className="text-sm text-zinc-200">Intersection manager</div>
                  <p className="text-xs text-muted-foreground">Space pauses · same seed on reset</p>
                </div>
                <div className="flex gap-1.5">
                  <Button size="icon-sm" variant="outline" onClick={() => setPaused((p) => !p)}>
                    {paused ? <Play /> : <Pause />}
                  </Button>
                  <Button size="icon-sm" variant="outline" onClick={reset}>
                    <RotateCcw />
                  </Button>
                </div>
              </div>

              <Field label="Traffic density" value={`${config.arrivalPerLane.toFixed(2)} veh/s per lane`}>
                <Slider
                  min={0}
                  max={0.22}
                  step={0.01}
                  value={[config.arrivalPerLane]}
                  onValueChange={(v) => patch({ arrivalPerLane: first(v) })}
                />
              </Field>
              <Field label="Cruise speed" value={`${config.cruiseMph} mph`}>
                <Slider
                  min={90}
                  max={120}
                  step={1}
                  value={[config.cruiseMph]}
                  onValueChange={(v) => patch({ cruiseMph: first(v) })}
                />
              </Field>
              <Field label="Crossing speed" value={`${config.crossMph} mph`}>
                <Slider
                  min={30}
                  max={55}
                  step={1}
                  value={[config.crossMph]}
                  onValueChange={(v) => patch({ crossMph: first(v) })}
                />
              </Field>
              <Field label="Playback" value={`${config.timeScale.toFixed(2)}×`}>
                <Slider
                  min={0.25}
                  max={1.4}
                  step={0.05}
                  value={[config.timeScale]}
                  onValueChange={(v) => patch({ timeScale: first(v) })}
                />
              </Field>
              <Field label="Camera" value={zoom > 2.4 ? "Intersection" : "Approaches"}>
                <Slider min={1.35} max={3.2} step={0.05} value={[zoom]} onValueChange={(v) => setZoom(first(v))} />
              </Field>

              <Separator />

              <ToggleRow
                label="Today vs tomorrow speeds"
                hint={
                  config.speedRegime === "vision"
                    ? `Lights stay at ${config.lightsMph} mph. Slots cruise at ${config.cruiseMph}, cross at ${config.crossMph}.`
                    : "Both sides use the same cruise and crossing speeds."
                }
                checked={config.speedRegime === "vision"}
                onCheckedChange={(checked) =>
                  patch({ speedRegime: (checked ? "vision" : "matched") as SpeedRegime })
                }
              />
              <ToggleRow
                label="Show reservation tiles"
                hint="AIM-style space–time grid inside the box."
                checked={config.showTiles}
                onCheckedChange={(checked) => patch({ showTiles: checked })}
              />
              <ToggleRow
                label="Speed labels"
                hint="Print mph on each car."
                checked={config.showSpeeds}
                onCheckedChange={(checked) => patch({ showSpeeds: checked })}
              />
            </CardContent>
          </Card>
          <PaperPanel />
        </aside>
      </div>
    </div>
  );
}

function SimPane({
  simRef,
  config,
  paused,
  zoom,
  label,
  stats,
  onStats,
  empty,
  className,
}: {
  simRef: RefObject<TrafficSim>;
  config: SimConfig;
  paused: boolean;
  zoom: number;
  label: string;
  stats: SimSnapshot;
  onStats: (s: SimSnapshot) => void;
  empty: boolean;
  className?: string;
}) {
  return (
    <div className={`relative min-h-[420px] overflow-hidden rounded-2xl ring-1 ring-white/10 ${className ?? ""}`}>
      <SimCanvas
        simRef={simRef}
        config={config}
        paused={paused}
        zoom={zoom}
        label={label}
        onStats={onStats}
        className="absolute inset-0"
      />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent p-3">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Stat k="Throughput" v={`${Math.round(stats.throughputPerHour)} /h`} />
          <Stat k="Mean speed" v={`${Math.round(stats.meanMph)} mph`} />
          <Stat k="Stopped" v={`${stats.stopped}`} />
          <Stat k="Delay" v={`${stats.meanDelay.toFixed(1)} s`} />
        </div>
      </div>
      {empty ? (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50 text-sm text-zinc-300">
          No traffic — raise density to spawn cars.
        </div>
      ) : null}
      {stats.collisions > 0 && config.mode === "slot" ? (
        <div className="absolute top-14 left-3 rounded-md bg-red-500/20 px-2 py-1 text-xs text-red-100">
          {stats.collisions} overlapping paths
        </div>
      ) : null}
    </div>
  );
}

function Stat({ k, v }: { k: string; v: string }) {
  return (
    <div className="rounded-md bg-black/35 px-2 py-1.5 backdrop-blur-sm">
      <div className="text-[10px] tracking-wide text-zinc-400 uppercase">{k}</div>
      <div className="font-mono text-sm text-zinc-50">{v}</div>
    </div>
  );
}

function Field({
  label,
  value,
  children,
}: {
  label: string;
  value: string;
  children: ReactNode;
}) {
  return (
    <div className="block space-y-2">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="text-zinc-200">{label}</span>
        <span className="font-mono text-xs text-cyan-200/80">{value}</span>
      </div>
      {children}
    </div>
  );
}

function ToggleRow({
  label,
  hint,
  checked,
  onCheckedChange,
}: {
  label: string;
  hint: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div>
        <div className="text-sm text-zinc-200">{label}</div>
        <p className="text-xs text-muted-foreground">{hint}</p>
      </div>
      <Switch checked={checked} onCheckedChange={onCheckedChange} />
    </div>
  );
}

function first(v: number | readonly number[]): number {
  if (typeof v === "number") return v;
  return v[0] ?? 0;
}

function ModeButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <Button variant={active ? "default" : "outline"} onClick={onClick}>
      {children}
    </Button>
  );
}
