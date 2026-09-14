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
}

export function SimCanvas({ simRef, config, paused, zoom, label, onStats }: SimCanvasProps) {
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

    const sizeOf = () => {
      const rect = wrap.getBoundingClientRect();
      return {
        w: Math.max(320, Math.floor(rect.width || wrap.clientWidth || 640)),
        h: Math.max(280, Math.floor(rect.height || wrap.clientHeight || 420)),
      };
    };

    let frame = 0;
    let last = performance.now();
    let statsAcc = 0;
    let first = true;

    const draw = () => {
      const { w, h } = sizeOf();
      try {
        renderSim(ctx, simRef.current, w, h, {
          showTiles: configRef.current.showTiles,
          showSpeeds: configRef.current.showSpeeds,
          label: labelRef.current,
          zoom: zoomRef.current,
        });
      } catch (err) {
        console.error("renderSim failed", err);
      }
    };

    const tick = (now: number) => {
      const raw = Math.min(0.05, Math.max(0, (now - last) / 1000));
      last = now;
      const sim = simRef.current;
      const simDt = (raw || 1 / 60) * configRef.current.timeScale;
      if (!pausedRef.current) {
        const steps = Math.max(1, Math.round(simDt / 0.016) || 1);
        const stepDt = simDt / steps;
        for (let i = 0; i < steps; i++) sim.step(Math.max(stepDt, 0.008));
      }
      draw();
      statsAcc += raw || 0.016;
      if (first || statsAcc > 0.2) {
        first = false;
        statsAcc = 0;
        statsRef.current(sim.snapshot());
      }
    };

    tick(performance.now());
    const loop = (now: number) => {
      frame = requestAnimationFrame(loop);
      tick(now);
    };
    frame = requestAnimationFrame(loop);
    const ro = new ResizeObserver(() => draw());
    ro.observe(wrap);
    return () => {
      cancelAnimationFrame(frame);
      ro.disconnect();
    };
  }, [simRef]);

  return (
    <div
      ref={wrapRef}
      className="relative h-[min(64vh,680px)] min-h-[380px] w-full overflow-hidden rounded-2xl bg-[#1a2438] ring-1 ring-white/15"
    >
      <canvas ref={canvasRef} className="absolute inset-0 size-full" />
    </div>
  );
}
