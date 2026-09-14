const statusEl = document.getElementById("map-status");
const errorEl = document.getElementById("error");
const eventsEl = document.getElementById("events");
const laborEl = document.getElementById("labor");
const lanesEl = document.getElementById("lanes");
const corridorsEl = document.getElementById("corridors");
const ringsEl = document.getElementById("rings");
const playbookEl = document.getElementById("playbook");
const catalogEl = document.getElementById("catalog-line");
const clockEl = document.getElementById("clock");

window.requestIdleCallback ||= (cb) =>
  window.setTimeout(() => cb({ didTimeout: false, timeRemaining: () => 16 }), 1);
window.cancelIdleCallback ||= (id) => window.clearTimeout(id);

const KIND_COLOR = {
  car: "#d7e4d9",
  bus: "#7eb6c9",
  emergency: "#ff6b4a",
  delivery: "#e8c56b",
};

const METRO_BOUNDS = [
  [-88.71, 41.2],
  [-87.02, 42.5],
];

let map = null;
let mapReady = false;
let socket = null;
let cityLoaded = false;
let view = "street";
let overlay = null;
let city = null;

function mapLive() {
  return Boolean(map && mapReady);
}

function setError(msg) {
  if (!msg) {
    errorEl.hidden = true;
    errorEl.textContent = "";
    return;
  }
  errorEl.hidden = false;
  errorEl.textContent = msg;
}

function emptyFc() {
  return { type: "FeatureCollection", features: [] };
}

function asFc(items, extra) {
  return {
    type: "FeatureCollection",
    features: items.map((it) => ({
      type: "Feature",
      properties: extra(it),
      geometry: { type: "Point", coordinates: [it.lon, it.lat] },
    })),
  };
}

function setView(next) {
  view = next;
  document.getElementById("view-street").classList.toggle("on", view === "street");
  document.getElementById("view-metro").classList.toggle("on", view === "metro");
  if (!mapLive()) return;
  const metro = view === "metro";
  if (map.getLayer("corridors")) map.setPaintProperty("corridors", "line-opacity", metro ? 0.9 : 0.4);
  if (map.getLayer("rings")) map.setPaintProperty("rings", "fill-opacity", metro ? 0.07 : 0.03);
  if (map.getLayer("rings-line")) map.setPaintProperty("rings-line", "line-opacity", metro ? 0.55 : 0.25);
  if (map.getLayer("tracker")) map.setPaintProperty("tracker", "fill-opacity", metro ? 0.12 : 0.04);
  if (map.getLayer("districts")) map.setPaintProperty("districts", "circle-opacity", metro ? 1 : 0.4);
  if (metro) {
    map.fitBounds(METRO_BOUNDS, { padding: 40, duration: 800 });
  } else {
    map.easeTo({ center: [-88.147, 41.75], zoom: 12.4, duration: 800 });
  }
}

function applyCityToMap(payload) {
  if (!mapLive() || !payload) return;
  if (payload.origin_lonlat) map.setCenter(payload.origin_lonlat);
  if (map.getSource("roads")) {
    map.getSource("roads").setData(payload.roads);
    return;
  }
  map.addSource("roads", { type: "geojson", data: payload.roads });
  map.addLayer({
    id: "roads",
    type: "line",
    source: "roads",
    paint: { "line-color": "#6fa86a", "line-width": 1.5, "line-opacity": 0.55 },
  });
  map.addSource("vehicles", { type: "geojson", data: emptyFc() });
  map.addLayer({
    id: "vehicles",
    type: "circle",
    source: "vehicles",
    paint: {
      "circle-radius": ["match", ["get", "kind"], "bus", 5.5, "emergency", 6, 3.4],
      "circle-color": [
        "match",
        ["get", "kind"],
        "bus",
        KIND_COLOR.bus,
        "emergency",
        KIND_COLOR.emergency,
        "delivery",
        KIND_COLOR.delivery,
        KIND_COLOR.car,
      ],
      "circle-stroke-width": 0.6,
      "circle-stroke-color": "#132016",
    },
  });
  map.addSource("intersections", { type: "geojson", data: emptyFc() });
  map.addLayer({
    id: "intersections",
    type: "circle",
    source: "intersections",
    paint: {
      "circle-radius": ["case", ["get", "had_signals"], 4.8, 3.1],
      "circle-color": ["case", ["get", "had_signals"], "#c4894a", "#8fbf6a"],
      "circle-opacity": 0.9,
    },
  });
}

function applyOverlayToMap(payload) {
  if (!mapLive() || !payload) return;
  if (!map.getSource("rings")) {
    map.addSource("rings", { type: "geojson", data: payload.rings });
    map.addLayer({
      id: "rings",
      type: "fill",
      source: "rings",
      paint: { "fill-color": ["get", "color"], "fill-opacity": 0.05 },
    });
    map.addLayer({
      id: "rings-line",
      type: "line",
      source: "rings",
      paint: { "line-color": ["get", "color"], "line-width": 1.2, "line-opacity": 0.45 },
    });
    map.addSource("tracker", { type: "geojson", data: payload.tracker });
    map.addLayer({
      id: "tracker",
      type: "fill",
      source: "tracker",
      paint: { "fill-color": "#c4894a", "fill-opacity": 0.08 },
    });
    map.addSource("corridors", { type: "geojson", data: payload.corridors });
    map.addLayer({
      id: "corridors",
      type: "line",
      source: "corridors",
      paint: {
        "line-color": "#c4894a",
        "line-width": ["case", ["==", ["get", "mode"], "rail"], 2.2, 4.2],
        "line-opacity": 0.85,
      },
    });
    map.addSource("districts", { type: "geojson", data: payload.districts });
    map.addLayer({
      id: "districts",
      type: "circle",
      source: "districts",
      paint: {
        "circle-radius": ["case", ["==", ["get", "role"], "job"], 7, 5.5],
        "circle-color": ["case", ["==", ["get", "role"], "job"], "#e8c56b", "#8fbf6a"],
        "circle-stroke-width": 1,
        "circle-stroke-color": "#132016",
      },
    });
    map.addSource("lights", { type: "geojson", data: payload.lights });
    map.addLayer({
      id: "lights",
      type: "circle",
      source: "lights",
      paint: {
        "circle-radius": 2.1,
        "circle-color": "#e8c56b",
        "circle-opacity": 0.55,
      },
      minzoom: 13,
    });
    return;
  }
  map.getSource("rings").setData(payload.rings);
  map.getSource("corridors").setData(payload.corridors);
  map.getSource("districts").setData(payload.districts);
  map.getSource("tracker").setData(payload.tracker);
  map.getSource("lights").setData(payload.lights);
}

async function loadCity() {
  statusEl.textContent = "Loading Naperville streets and metro overlays…";
  const [cityRes, regionRes, catalogRes, playRes] = await Promise.all([
    fetch("/city"),
    fetch("/region"),
    fetch("/catalog"),
    fetch("/playbook"),
  ]);
  if (!cityRes.ok) throw new Error("City layers failed to load");
  city = await cityRes.json();
  overlay = regionRes.ok ? await regionRes.json() : null;
  cityLoaded = true;
  applyCityToMap(city);
  applyOverlayToMap(overlay);
  if (overlay?.twin) paintRings(overlay.twin);
  const counts = city.counts || {};
  statusEl.textContent = `${counts.intersections || "—"} slot pads · ${counts.roads || "—"} road ways`;

  if (catalogRes.ok) {
    const cat = await catalogRes.json();
    const paid = cat.counts?.paid || 0;
    const open = (cat.counts?.open || 0) + (cat.counts?.open_partial || 0);
    catalogEl.textContent = `${open} open datasets in the catalog · ${paid} paid feeds approximated (INRIX, StreetLight, Google 3D Tiles).`;
  }
  if (playRes.ok) {
    const book = await playRes.json();
    playbookEl.innerHTML = "";
    for (const item of book.interventions || []) {
      const li = document.createElement("li");
      li.innerHTML = `<strong>${item.title}</strong> <span class="muted">(${item.status} · ${item.ring})</span><br>${item.note}`;
      playbookEl.appendChild(li);
    }
  }
}

function paintRings(twin) {
  if (!twin) return;
  ringsEl.innerHTML = "";
  for (const ring of twin.fidelity || []) {
    const li = document.createElement("li");
    li.textContent = `${ring.name} · ${ring.radius_km} km · ${ring.engine}`;
    ringsEl.appendChild(li);
  }
}

function paintTwin(twin) {
  if (!twin) return;
  clockEl.textContent = `${twin.weekday_name || ""} ${twin.clock || ""}`.trim();
  document.getElementById("m-clock").textContent = `${twin.weekday_name || ""} ${twin.clock || "—"}`;

  lanesEl.innerHTML = "";
  for (const fac of twin.lanes || []) {
    const li = document.createElement("li");
    const tag = fac.fictional ? "proposed" : "IDOT";
    li.innerHTML = `<strong>${fac.name}</strong> · ${fac.direction} · ×${fac.inbound_mult} in / ×${fac.outbound_mult} out <span class="muted">${tag}</span>`;
    lanesEl.appendChild(li);
  }

  corridorsEl.innerHTML = "";
  const rows = (twin.corridors || []).slice().sort((a, b) => (b.inbound_vph || 0) - (a.inbound_vph || 0));
  for (const cor of rows.slice(0, 8)) {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${cor.name}</strong> · TTI ${cor.tti} · ${cor.speed_mph} mph<br>${cor.inbound_vph} vph in · ${cor.outbound_vph} vph out · ${cor.minutes} min`;
    corridorsEl.appendChild(li);
  }

  if (mapLive() && map.getSource("corridors") && overlay?.corridors) {
    const byId = Object.fromEntries((twin.corridors || []).map((c) => [c.id, c]));
    const next = {
      type: "FeatureCollection",
      features: overlay.corridors.features.map((feat) => {
        const live = byId[feat.properties.id];
        return live ? { ...feat, properties: { ...feat.properties, ...live } } : feat;
      }),
    };
    map.getSource("corridors").setData(next);
    if (map.getLayer("corridors")) {
      map.setPaintProperty("corridors", "line-color", [
        "case",
        [">", ["get", "tti"], 1.55],
        "#e07a4a",
        [">", ["get", "tti"], 1.2],
        "#e8c56b",
        "#8fbf6a",
      ]);
    }
  }
}

function paintSnapshot(snap) {
  if (!snap?.metrics) return;
  if (mapLive() && map.getSource("vehicles")) {
    map.getSource("vehicles").setData(asFc(snap.vehicles, (v) => ({ kind: v.kind, speed: v.speed_mph })));
    map.getSource("intersections").setData(
      asFc(snap.intersections, (i) => ({ had_signals: i.had_signals, pending: i.pending }))
    );
  }
  const m = snap.metrics;
  document.getElementById("m-active").textContent = String(m.active);
  document.getElementById("m-done").textContent = String(m.completed);
  document.getElementById("m-speed").textContent = `${m.mean_speed_mph} mph`;
  document.getElementById("m-delay").textContent = `${m.mean_delay_s}s`;
  document.getElementById("m-stops").textContent = String(m.stops);
  statusEl.textContent = `${snap.policy.toUpperCase()} · ${m.active} moving · ${m.grants} slots granted`;
  paintTwin(snap.twin);

  const labor = snap.labor || {};
  laborEl.innerHTML = "";
  const lines = [
    `${Math.round(labor.signal_ops_hours_year || 0)} technician-hours / year off signal cabinets`,
    `${Math.round(labor.field_ops_hours_year || 0)} peak-hour direction hours no longer staffed`,
    `${labor.traveler_hours_this_run || 0} traveler-hours recovered in this run`,
  ];
  for (const line of lines) {
    const li = document.createElement("li");
    li.textContent = line;
    laborEl.appendChild(li);
  }

  const events = snap.services?.events || [];
  eventsEl.innerHTML = "";
  if (!events.length) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = "No preemption pulses yet — the next ambulance or bus will take a reserved corridor.";
    eventsEl.appendChild(li);
  } else {
    for (const ev of events.slice().reverse()) {
      const li = document.createElement("li");
      li.textContent = `t=${Math.round(ev.t)}s  ${ev.kind} — ${ev.note || "slot"}`;
      eventsEl.appendChild(li);
    }
  }
}

function connectWs() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return;
  const proto = location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${proto}://${location.host}/ws`);
  socket.onopen = () => setError("");
  socket.onerror = () => setError("Lost the city runtime. Refresh, or restart with smartcity serve.");
  socket.onclose = () => {
    socket = null;
    statusEl.textContent = "Runtime disconnected";
    setTimeout(connectWs, 1500);
  };
  socket.onmessage = (ev) => paintSnapshot(JSON.parse(ev.data));
}

function tryMakeMap() {
  if (typeof maplibregl === "undefined") {
    statusEl.textContent = "MapLibre failed to load — live clock still running.";
    return;
  }
  try {
    map = new maplibregl.Map({
      container: "map",
      // WebGL2 only. MapLibre 4's WebGPU/WGSL path dies in software browsers.
      canvasContextAttributes: {
        antialias: false,
        failIfMajorPerformanceCaveat: false,
        contextType: "webgl2",
      },
      style: {
        version: 8,
        sources: {
          carto: {
            type: "raster",
            tiles: ["https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap © CARTO",
          },
        },
        layers: [{ id: "carto", type: "raster", source: "carto" }],
      },
      center: [-88.147, 41.75],
      zoom: 12.4,
    });
    map.on("load", () => {
      mapReady = true;
      applyCityToMap(city);
      applyOverlayToMap(overlay);
    });
    map.on("error", (ev) => {
      const err = ev?.error || ev;
      console.warn("map error", err);
      if (!mapReady) {
        statusEl.textContent = "Map renderer unavailable — live clock still running.";
      }
    });
  } catch (err) {
    map = null;
    statusEl.textContent = "Map renderer unavailable — live clock still running.";
  }
}

document.getElementById("controls").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  setError("");
  statusEl.textContent = "Restarting fleet…";
  const res = await fetch("/sim/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      policy: fd.get("policy"),
      target_vehicles: Number(fd.get("target_vehicles")),
      start_hour: Number(fd.get("start_hour")),
      enable_services: true,
    }),
  });
  if (!res.ok) setError("Could not restart the city.");
});

document.getElementById("pause").addEventListener("click", async () => {
  const res = await fetch("/sim/pause", { method: "POST" });
  const data = await res.json();
  document.getElementById("pause").textContent = data.running ? "Pause" : "Resume";
});

document.getElementById("view-street").addEventListener("click", () => setView("street"));
document.getElementById("view-metro").addEventListener("click", () => setView("metro"));

async function boot() {
  tryMakeMap();
  try {
    await loadCity();
  } catch (err) {
    setError(err.message);
    statusEl.textContent = "City data is not available yet.";
  }
  connectWs();
}

boot();
