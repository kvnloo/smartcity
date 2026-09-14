import { TrafficSim, type LightPhase } from "./engine";
import {
  CAR_LENGTH,
  CAR_WIDTH,
  PATH_HALF,
  TILES,
  aabb,
  boxSize,
  mpsToMph,
  pose,
} from "./geometry";

const ROAD = "#2a3348";
const ROAD_EDGE = "#6d7ea3";
const MARK = "rgba(230, 240, 255, 0.55)";
const BOX_FILL = "rgba(70, 210, 255, 0.10)";

export interface RenderOptions {
  showTiles: boolean;
  showSpeeds: boolean;
  label: string;
  zoom: number;
}

export function renderSim(
  ctx: CanvasRenderingContext2D,
  sim: TrafficSim,
  width: number,
  height: number,
  options: RenderOptions,
): void {
  if (width < 2 || height < 2) return;
  const dpr = Math.max(1, window.devicePixelRatio || 1);
  if (ctx.canvas.width !== Math.floor(width * dpr) || ctx.canvas.height !== Math.floor(height * dpr)) {
    ctx.canvas.width = Math.floor(width * dpr);
    ctx.canvas.height = Math.floor(height * dpr);
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  const view = (PATH_HALF * 2) / options.zoom;
  const scale = Math.min(width, height) / view;
  const ox = width / 2;
  const oy = height / 2;
  const toX = (x: number) => ox + x * scale;
  const toY = (y: number) => oy + y * scale;

  drawBackdrop(ctx, width, height);
  drawCityBlocks(ctx, toX, toY, scale);
  drawRoads(ctx, toX, toY, scale);
  if (options.showTiles && sim.config.mode === "slot") drawTiles(ctx, toX, toY, scale, sim);
  else drawIntersectionPlate(ctx, toX, toY, scale);
  drawLaneMarks(ctx, toX, toY, scale);
  if (sim.config.mode === "lights") drawLights(ctx, toX, toY, scale, sim.lightPhase());
  drawCars(ctx, sim, toX, toY, scale, options.showSpeeds);
  drawHud(ctx, width, options.label, sim.config.mode);
}

function drawBackdrop(ctx: CanvasRenderingContext2D, w: number, h: number): void {
  const g = ctx.createRadialGradient(w * 0.5, h * 0.42, 20, w * 0.5, h * 0.5, Math.max(w, h) * 0.72);
  g.addColorStop(0, "#24344f");
  g.addColorStop(0.55, "#121826");
  g.addColorStop(1, "#0a1018");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
}

function drawCityBlocks(
  ctx: CanvasRenderingContext2D,
  toX: (x: number) => number,
  toY: (y: number) => number,
  scale: number,
): void {
  ctx.save();
  ctx.strokeStyle = "rgba(90, 130, 170, 0.07)";
  ctx.lineWidth = 1;
  const step = 28;
  for (let x = -220; x <= 220; x += step) {
    ctx.beginPath();
    ctx.moveTo(toX(x), toY(-220));
    ctx.lineTo(toX(x), toY(220));
    ctx.stroke();
  }
  for (let y = -220; y <= 220; y += step) {
    ctx.beginPath();
    ctx.moveTo(toX(-220), toY(y));
    ctx.lineTo(toX(220), toY(y));
    ctx.stroke();
  }
  ctx.fillStyle = "rgba(18, 28, 42, 0.55)";
  const block = 22;
  for (const sx of [-1, 1]) {
    for (const sy of [-1, 1]) {
      const x0 = toX(sx * (boxSize() / 2 + 6));
      const y0 = toY(sy * (boxSize() / 2 + 6));
      const w = block * scale;
      ctx.fillRect(sx < 0 ? x0 - w : x0, sy < 0 ? y0 - w : y0, w, w);
    }
  }
  ctx.restore();
}

function roadHalf(): number {
  return boxSize() / 2;
}

function drawRoads(
  ctx: CanvasRenderingContext2D,
  toX: (x: number) => number,
  toY: (y: number) => number,
  scale: number,
): void {
  const h = roadHalf();
  const span = PATH_HALF + 20;
  ctx.fillStyle = ROAD;
  ctx.fillRect(toX(-h), toY(-span), h * 2 * scale, span * 2 * scale);
  ctx.fillRect(toX(-span), toY(-h), span * 2 * scale, h * 2 * scale);

  ctx.strokeStyle = ROAD_EDGE;
  ctx.lineWidth = 1.5;
  ctx.strokeRect(toX(-h), toY(-span), h * 2 * scale, span * 2 * scale);
  ctx.strokeRect(toX(-span), toY(-h), span * 2 * scale, h * 2 * scale);
}

function drawIntersectionPlate(
  ctx: CanvasRenderingContext2D,
  toX: (x: number) => number,
  toY: (y: number) => number,
  scale: number,
): void {
  const h = roadHalf();
  ctx.fillStyle = "rgba(255, 210, 90, 0.04)";
  ctx.fillRect(toX(-h), toY(-h), h * 2 * scale, h * 2 * scale);
}

function drawTiles(
  ctx: CanvasRenderingContext2D,
  toX: (x: number) => number,
  toY: (y: number) => number,
  scale: number,
  sim: TrafficSim,
): void {
  const box = boxSize();
  const h = box / 2;
  const size = box / TILES;
  ctx.fillStyle = BOX_FILL;
  ctx.fillRect(toX(-h), toY(-h), box * scale, box * scale);
  const used = occupiedTiles(sim);
  for (const index of used) {
    const col = index % TILES;
    const row = Math.floor(index / TILES);
    ctx.fillStyle = "rgba(90, 230, 255, 0.14)";
    ctx.fillRect(toX(-h + col * size), toY(-h + row * size), size * scale, size * scale);
  }
  ctx.strokeStyle = "rgba(90, 230, 255, 0.16)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= TILES; i++) {
    const p = -h + i * size;
    ctx.beginPath();
    ctx.moveTo(toX(-h), toY(p));
    ctx.lineTo(toX(h), toY(p));
    ctx.moveTo(toX(p), toY(-h));
    ctx.lineTo(toX(p), toY(h));
    ctx.stroke();
  }
  ctx.strokeStyle = "rgba(90, 230, 255, 0.35)";
  ctx.lineWidth = 1.5;
  ctx.strokeRect(toX(-h), toY(-h), box * scale, box * scale);
  ctx.fillStyle = "rgba(90, 230, 255, 0.55)";
  ctx.font = "10px ui-monospace, SFMono-Regular, Menlo, monospace";
  ctx.fillText("SLOT GRID", toX(-h) + 6, toY(-h) - 6);
}

function drawLaneMarks(
  ctx: CanvasRenderingContext2D,
  toX: (x: number) => number,
  toY: (y: number) => number,
  scale: number,
): void {
  ctx.save();
  ctx.strokeStyle = MARK;
  ctx.setLineDash([7, 9]);
  ctx.lineWidth = Math.max(1, 0.12 * scale);
  const h = roadHalf();
  const span = PATH_HALF + 8;
  ctx.beginPath();
  ctx.moveTo(toX(0), toY(-span));
  ctx.lineTo(toX(0), toY(-h));
  ctx.moveTo(toX(0), toY(h));
  ctx.lineTo(toX(0), toY(span));
  ctx.moveTo(toX(-span), toY(0));
  ctx.lineTo(toX(-h), toY(0));
  ctx.moveTo(toX(h), toY(0));
  ctx.lineTo(toX(span), toY(0));
  ctx.stroke();
  ctx.restore();
}

function drawLights(
  ctx: CanvasRenderingContext2D,
  toX: (x: number) => number,
  toY: (y: number) => number,
  scale: number,
  phase: LightPhase,
): void {
  const h = roadHalf() + 2.8;
  const nsOn = phase === "NS_GREEN" || phase === "NS_YELLOW";
  const ewOn = phase === "EW_GREEN" || phase === "EW_YELLOW";
  const nsColor = phase === "NS_YELLOW" ? "#FFD24A" : phase === "NS_GREEN" ? "#3DFF9A" : "#FF4D5A";
  const ewColor = phase === "EW_YELLOW" ? "#FFD24A" : phase === "EW_GREEN" ? "#3DFF9A" : "#FF4D5A";
  const posts: { x: number; y: number; ns: boolean }[] = [
    { x: -h, y: -h, ns: true },
    { x: h, y: h, ns: true },
    { x: h, y: -h, ns: false },
    { x: -h, y: h, ns: false },
  ];
  for (const p of posts) {
    const color = p.ns ? nsColor : ewColor;
    const lit = p.ns ? nsOn : ewOn;
    ctx.fillStyle = "#0d1118";
    fillRoundRect(ctx, toX(p.x) - 6, toY(p.y) - 14, 12, 28, 4);
    ctx.beginPath();
    ctx.fillStyle = color;
    ctx.shadowColor = color;
    ctx.shadowBlur = lit ? 16 : 4;
    ctx.arc(toX(p.x), toY(p.y), Math.max(3.5, 0.7 * scale), 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
  }
}

function drawCars(
  ctx: CanvasRenderingContext2D,
  sim: TrafficSim,
  toX: (x: number) => number,
  toY: (y: number) => number,
  scale: number,
  showSpeeds: boolean,
): void {
  const cruise = sim.cruiseSpeed();
  const box = boxSize() / 2 + 1;
  for (const car of sim.cars) {
    const p = pose(car.dir, car.lane, car.s);
    const x = toX(p.x);
    const y = toY(p.y);
    const mph = mpsToMph(car.v);
    const inBox = Math.abs(p.x) < box && Math.abs(p.y) < box;
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(p.heading);
    const len = Math.max(22, CAR_LENGTH * scale * 1.25);
    const wid = Math.max(11, CAR_WIDTH * scale * 1.25);
    ctx.shadowColor = car.color;
    ctx.shadowBlur = inBox ? 18 : 10;
    ctx.fillStyle = "rgba(8, 10, 16, 0.45)";
    ctx.beginPath();
    roundRect(ctx, -len / 2 + 1, -wid / 2 + 2, len, wid, Math.max(2, 0.28 * scale));
    ctx.fill();
    ctx.shadowBlur = 14;
    const body = ctx.createLinearGradient(-len / 2, 0, len / 2, 0);
    body.addColorStop(0, shade(car.color, 0.55));
    body.addColorStop(0.45, car.color);
    body.addColorStop(1, shade(car.color, 0.7));
    ctx.fillStyle = body;
    ctx.beginPath();
    roundRect(ctx, -len / 2, -wid / 2, len, wid, Math.max(2, 0.3 * scale));
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.fillStyle = "rgba(8, 16, 28, 0.55)";
    ctx.beginPath();
    roundRect(ctx, -len * 0.12, -wid * 0.32, len * 0.38, wid * 0.64, 1.4);
    ctx.fill();
    ctx.fillStyle = "rgba(255, 255, 245, 0.9)";
    ctx.fillRect(len / 2 - 2.4, -wid * 0.28, 2.2, wid * 0.18);
    ctx.fillRect(len / 2 - 2.4, wid * 0.1, 2.2, wid * 0.18);
    ctx.fillStyle = "rgba(255, 80, 80, 0.8)";
    ctx.fillRect(-len / 2, -wid * 0.26, 1.8, wid * 0.16);
    ctx.fillRect(-len / 2, wid * 0.1, 1.8, wid * 0.16);
    ctx.restore();

    if (showSpeeds) {
      ctx.fillStyle = "rgba(235, 244, 255, 0.8)";
      ctx.font = `${Math.max(9, scale * 0.7)}px ui-monospace, SFMono-Regular, Menlo, monospace`;
      ctx.fillText(`${Math.round(mph)}`, x + 6, y - 8);
    } else if (car.v > cruise * 0.82) {
      ctx.fillStyle = "rgba(154, 231, 255, 0.35)";
      ctx.beginPath();
      ctx.arc(x, y, 9, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

function drawHud(ctx: CanvasRenderingContext2D, width: number, label: string, mode: string): void {
  ctx.fillStyle = "rgba(6, 10, 16, 0.72)";
  fillRoundRect(ctx, 12, 12, 200, 36, 10);
  ctx.fillStyle = mode === "slot" ? "#7CFFD0" : "#FFC978";
  ctx.font = "600 12px ui-sans-serif, system-ui, sans-serif";
  ctx.fillText(label, 24, 35);
}

function fillRoundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
): void {
  ctx.beginPath();
  roundRect(ctx, x, y, w, h, r);
  ctx.fill();
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
): void {
  const radius = Math.min(r, w / 2, h / 2);
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + w, y, x + w, y + h, radius);
  ctx.arcTo(x + w, y + h, x, y + h, radius);
  ctx.arcTo(x, y + h, x, y, radius);
  ctx.arcTo(x, y, x + w, y, radius);
  ctx.closePath();
}

function shade(hex: string, amt: number): string {
  const n = parseInt(hex.slice(1), 16);
  const r = Math.round(((n >> 16) & 255) * amt);
  const g = Math.round(((n >> 8) & 255) * amt);
  const b = Math.round((n & 255) * amt);
  return `rgb(${r},${g},${b})`;
}

export function occupiedTiles(sim: TrafficSim): Set<number> {
  const box = boxSize();
  const origin = -box / 2;
  const size = box / TILES;
  const used = new Set<number>();
  for (const car of sim.cars) {
    const p = pose(car.dir, car.lane, car.s);
    const body = aabb(p.x, p.y, p.heading, CAR_LENGTH, CAR_WIDTH);
    const c0 = Math.floor((body.minX - origin) / size);
    const c1 = Math.floor((body.maxX - origin) / size);
    const r0 = Math.floor((body.minY - origin) / size);
    const r1 = Math.floor((body.maxY - origin) / size);
    for (let c = c0; c <= c1; c++) {
      for (let r = r0; r <= r1; r++) {
        if (c < 0 || r < 0 || c >= TILES || r >= TILES) continue;
        used.add(c + r * TILES);
      }
    }
  }
  return used;
}
