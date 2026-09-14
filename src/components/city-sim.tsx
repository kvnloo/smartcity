"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { Pause, Play, RotateCcw } from "lucide-react";
import { IntersectionView } from "@/components/intersection-view";
import { PaperPanel } from "@/components/paper-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { TrafficSim, type SimSnapshot } from "@/lib/sim/engine";
import { DEFAULT_CONFIG, type SimConfig, type SpeedRegime, type ViewMode } from "@/lib/sim/geometry";

export function CitySim() {
  const [view, setView] = useState<ViewMode>("split");
  const [paused, setPaused] = useState(false);
  const [zoom, setZoom] = useState(3.4);
  const [config, setConfig] = useState<SimConfig>(DEFAULT_CONFIG);
  const seedRef = useRef(7);
  const pausedRef = useRef(false);
  const configRef = useRef(config);
  const [bundle] = useState(() => {
    const slot = makeSim("slot", 7);
    const lights = makeSim("lights", 7);
    return {
      slot,
      lights,
      slotStats: slot.snapshot(),
      lightStats: lights.snapshot(),
    };
  });
  const slotSimRef = useRef(bundle.slot);
  const lightSimRef = useRef(bundle.lights);
  const [slotStats, setSlotStats] = useState<SimSnapshot>(bundle.slotStats);
  const [lightStats, setLightStats] = useState<SimSnapshot>(bundle.lightStats);

  useEffect(() => {
    pausedRef.current = paused;
  }, [paused]);

  useEffect(() => {
    configRef.current = config;
    slotSimRef.current.setConfig({ ...config, mode: "slot" });
    lightSimRef.current.setConfig({ ...config, mode: "lights" });
  }, [config]);

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

  useEffect(() => {
    const id = window.setInterval(() => {
      const scale = configRef.current.timeScale;
      const dt = 0.04 * scale;
      if (!pausedRef.current) {
        const n = 2;
        for (let i = 0; i < n; i++) {
          slotSimRef.current.step(dt / n);
          lightSimRef.current.step(dt / n);
        }
      }
      setSlotStats(slotSimRef.current.snapshot());
      setLightStats(lightSimRef.current.snapshot());
    }, 50);
    return () => window.clearInterval(id);
  }, []);

  const reset = () => {
    seedRef.current += 1;
    slotSimRef.current.reset(seedRef.current);
    lightSimRef.current.reset(seedRef.current);
    slotSimRef.current.setConfig({ ...config, mode: "slot" });
    lightSimRef.current.setConfig({ ...config, mode: "lights" });
    slotSimRef.current.warmup(12);
    lightSimRef.current.warmup(12);
    setSlotStats(slotSimRef.current.snapshot());
    setLightStats(lightSimRef.current.snapshot());
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
              config={{ ...config, mode: "lights" }}
              zoom={zoom}
              label="Traffic lights"
              stats={lightStats}
              empty={config.arrivalPerLane <= 0.01}
            />
            <SimPane
              className={showSlot ? "" : "hidden"}
              config={{ ...config, mode: "slot" }}
              zoom={zoom}
              label="Slot-based weave"
              stats={slotStats}
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

              <RangeField
                label="Traffic density"
                display={`${config.arrivalPerLane.toFixed(2)} veh/s per lane`}
                min={0}
                max={0.22}
                step={0.01}
                value={config.arrivalPerLane}
                onChange={(v) => patch({ arrivalPerLane: v })}
              />
              <RangeField
                label="Cruise speed"
                display={`${config.cruiseMph} mph`}
                min={90}
                max={120}
                step={1}
                value={config.cruiseMph}
                onChange={(v) => patch({ cruiseMph: v })}
              />
              <RangeField
                label="Crossing speed"
                display={`${config.crossMph} mph`}
                min={30}
                max={55}
                step={1}
                value={config.crossMph}
                onChange={(v) => patch({ crossMph: v })}
              />
              <RangeField
                label="Playback"
                display={`${config.timeScale.toFixed(2)}×`}
                min={0.25}
                max={1.4}
                step={0.05}
                value={config.timeScale}
                onChange={(v) => patch({ timeScale: v })}
              />
              <RangeField
                label="Camera"
                display={zoom > 2.8 ? "Intersection" : "Approaches"}
                min={1.6}
                max={4.6}
                step={0.05}
                value={zoom}
                onChange={setZoom}
              />

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
  config,
  zoom,
  label,
  stats,
  empty,
  className,
}: {
  config: SimConfig;
  zoom: number;
  label: string;
  stats: SimSnapshot;
  empty: boolean;
  className?: string;
}) {
  return (
    <div className={className}>
      <div className="relative">
        <IntersectionView snapshot={stats} zoom={zoom} label={label} />
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

function makeSim(mode: "slot" | "lights", seed: number): TrafficSim {
  const sim = new TrafficSim({ ...DEFAULT_CONFIG, mode }, seed);
  sim.warmup(12);
  return sim;
}

function RangeField({
  label,
  display,
  min,
  max,
  step,
  value,
  onChange,
}: {
  label: string;
  display: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="block space-y-2">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="text-zinc-200">{label}</span>
        <span className="font-mono text-xs text-cyan-200/80">{display}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-muted accent-cyan-300"
      />
    </label>
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
