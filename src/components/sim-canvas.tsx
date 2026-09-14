"use client";

import { useEffect, useRef, type RefObject } from "react";
import { TrafficSim, type SimSnapshot } from "@/lib/sim/engine";
import { type SimConfig } from "@/lib/sim/geometry";
import { renderSim } from "@/lib/sim/render";

interface SimCanvasProps {
  simRef: RefObject<TrafficSim>;
  config: SimConfig;
  paused: boolean;
  zoom: number;
  label: string;
  onStats: (stats: SimSnapshot) => void;
  className?: string;
}

export function SimCanvas({ simRef, config, paused, zoom, label, onStats, className }: SimCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const configRef = useRef(config);
  const pausedRef = useRef(paused);
  const zoomRef = useRef(zoom);
  const labelRef = useRef(label);
  const statsRef = useRef(onStats);

  useEffect(() => {
    configRef.current = config;
    simRef.current.setConfig(config);
  }, [config, simRef]);

  useEffect(() => {
    pausedRef.current = paused;
  }, [paused]);

  useEffect(() => {
    zoomRef.current = zoom;
  }, [zoom]);

  useEffect(() => {
    labelRef.current = label;
  }, [label]);

  useEffect(() => {
    statsRef.current = onStats;
  }, [onStats]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let frame = 0;
    let last = performance.now();
    let statsAcc = 0;

    const loop = (now: number) => {
      frame = requestAnimationFrame(loop);
      const raw = Math.min(0.05, (now - last) / 1000);
      last = now;
      const sim = simRef.current;
      const simDt = raw * configRef.current.timeScale;
      if (!pausedRef.current) {
        const steps = Math.max(1, Math.round(simDt / 0.016));
        const h = simDt / steps;
        for (let i = 0; i < steps; i++) sim.step(h);
      }
      const rect = wrap.getBoundingClientRect();
      renderSim(ctx, sim, rect.width, rect.height, {
        showTiles: configRef.current.showTiles,
        showSpeeds: configRef.current.showSpeeds,
        label: labelRef.current,
        zoom: zoomRef.current,
      });
      statsAcc += raw;
      if (statsAcc > 0.2) {
        statsAcc = 0;
        statsRef.current(sim.snapshot());
      }
    };
    frame = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(frame);
  }, [simRef]);

  return (
    <div ref={wrapRef} className={className}>
      <canvas ref={canvasRef} className="h-full w-full" />
    </div>
  );
}
