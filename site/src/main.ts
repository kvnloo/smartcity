import "./styles.css";
import type { Map as MapLibreMap } from "maplibre-gl";
import { lookdevPath } from "./camera";
import { mountMosaic } from "./fallback";
import { fidelityLine, formatClock, hottestCorridor, laneLine, lodChipLine, ttiTone, type TwinLookdev } from "./hud";
import { lodConfig, readDeviceHints } from "./lod";
import { corridorLayers, districtLayers, ringLayers } from "./overlays";
import { lookdevStyle, TERRAIN_EXAGGERATION } from "./style";
import { ESRI_IMAGERY } from "./tiles";

window.requestIdleCallback ||= ((cb: IdleRequestCallback) =>
  window.setTimeout(() => cb({ didTimeout: false, timeRemaining: () => 16 }), 1)) as typeof requestIdleCallback;

const lod = lodConfig(
  readDeviceHints(navigator as Navigator & { deviceMemory?: number; connection?: { saveData?: boolean } }, window),
);

const lodChip = document.getElementById("lod-chip")!;
const statusEl = document.getElementById("status")!;
const clockEl = document.getElementById("clock")!;
const lanesEl = document.getElementById("lanes")!;
const hotEl = document.getElementById("hot")!;
const fidelityEl = document.getElementById("fidelity")!;
const fallbackEl = document.getElementById("fallback")!;

lodChip.textContent = lodChipLine(lod.tier);

type TwinPayload = TwinLookdev & {
  geo: {
    corridors: GeoJSON.FeatureCollection;
    districts: GeoJSON.FeatureCollection;
    rings?: GeoJSON.FeatureCollection;
  };
  origin: [number, number];
};

function webglAvailable(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(
      canvas.getContext("webgl2", { failIfMajorPerformanceCaveat: false }) ||
        canvas.getContext("webgl", { failIfMajorPerformanceCaveat: false }),
    );
  } catch {
    return false;
  }
}

function paintHud(twin: TwinPayload) {
  clockEl.textContent = formatClock(twin.weekday_name, twin.clock);
  lanesEl.replaceChildren();
  for (const lane of twin.lanes.slice(0, 3)) {
    const li = document.createElement("li");
    li.textContent = laneLine(lane);
    lanesEl.appendChild(li);
  }
  const hot = hottestCorridor(twin.corridors);
  if (hot) {
    hotEl.className = `hot ${ttiTone(hot.tti)}`;
    hotEl.textContent = `${hot.name} · TTI ${hot.tti} · ${hot.speed_mph} mph · ${hot.inbound_vph} vph in`;
  }
  fidelityEl.textContent = fidelityLine(twin.fidelity) || "hero Unreal · micro SUMO · meso CTM · macro OD";
}

function showMosaic(origin: [number, number], reason: string) {
  statusEl.textContent = reason;
  mountMosaic(fallbackEl, {
    lon: origin[0],
    lat: origin[1],
    z: lod.mosaicZoom,
    radius: lod.mosaicRadius,
    template: ESRI_IMAGERY,
  });
}

function overlayTwin(map: MapLibreMap, twin: TwinPayload) {
  map.addSource("corridors", { type: "geojson", data: twin.geo.corridors });
  for (const layer of corridorLayers()) map.addLayer(layer);

  if (twin.geo.rings) {
    map.addSource("rings", { type: "geojson", data: twin.geo.rings });
    for (const layer of ringLayers()) map.addLayer(layer);
  }

  map.addSource("districts", { type: "geojson", data: twin.geo.districts });
  for (const layer of districtLayers()) map.addLayer(layer);
}

function flyPath(map: MapLibreMap) {
  if (!lod.animation) return;
  const path = lookdevPath(lod.maxPitch);
  let i = 1;
  const flyNext = () => {
    const beat = path[i];
    if (!beat) return;
    map.flyTo({
      center: beat.center,
      zoom: beat.zoom,
      pitch: beat.pitch,
      bearing: beat.bearing,
      duration: beat.duration,
      essential: true,
    });
    i = (i + 1) % path.length;
    if (i === 0) i = 1;
    window.setTimeout(flyNext, beat.duration + 400);
  };
  window.setTimeout(flyNext, 1400);
}

async function boot() {
  const twin = (await fetch("./twin.json").then((r) => {
    if (!r.ok) throw new Error(`twin.json ${r.status}`);
    return r.json();
  })) as TwinPayload;
  paintHud(twin);

  if (!webglAvailable()) {
    showMosaic(twin.origin, "No WebGL — Esri mosaic. Full sim is Unreal + SUMO, not this page.");
    return;
  }

  await import("maplibre-gl/dist/maplibre-gl.css");
  const maplibregl = (await import("maplibre-gl")).default;

  const map = new maplibregl.Map({
    container: "map",
    style: lookdevStyle(lod),
    center: twin.origin,
    zoom: 15.1,
    pitch: Math.min(70, lod.maxPitch),
    bearing: -28,
    maxPitch: lod.maxPitch,
    maxZoom: lod.maxZoom,
    pixelRatio: lod.pixelRatio,
    fadeDuration: lod.fadeDuration,
    maxTileCacheSize: lod.maxTileCacheSize,
    attributionControl: { compact: true },
    antialias: lod.tier === "ultra",
    failIfMajorPerformanceCaveat: false,
    pitchWithRotate: true,
    touchPitch: true,
  });

  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true, showCompass: true }), "top-right");

  map.on("error", (ev) => {
    console.warn(ev.error);
    const msg = ev.error?.message ?? "";
    if (/webgl|context/i.test(msg) && fallbackEl.childElementCount === 0) {
      showMosaic(twin.origin, "Renderer lost — photoreal mosaic still running.");
    } else {
      statusEl.textContent = "Streaming lookdev — a tile source hiccuped.";
    }
  });

  map.on("load", () => {
    if (lod.terrain && map.getSource("terrain")) {
      map.setTerrain({ source: "terrain", exaggeration: TERRAIN_EXAGGERATION });
    }
    overlayTwin(map, twin);
    statusEl.textContent =
      lod.tier === "ultra"
        ? "S25-class LOD · Maxar/Esri + OSM masses + terrain. Unreal still owns the hero street."
        : `Streaming ${lod.tier} LOD · less mesh, no hero sim on this device.`;
    flyPath(map);
  });
}

boot().catch((err) => {
  statusEl.textContent = err instanceof Error ? err.message : "Lookdev failed to boot.";
});
