const statusEl = document.getElementById("map-status");
const errorEl = document.getElementById("error");
const eventsEl = document.getElementById("events");
const laborEl = document.getElementById("labor");

const KIND_COLOR = {
  car: "#d7e4d9",
  bus: "#7eb6ff",
  emergency: "#ff6b4a",
  delivery: "#e6c15a",
};

const map = new maplibregl.Map({
  container: "map",
  style: {
    version: 8,
    sources: {
      osm: {
        type: "raster",
        tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
        tileSize: 256,
        attribution: "© OpenStreetMap",
      },
    },
    layers: [{ id: "osm", type: "raster", source: "osm" }],
  },
  center: [-88.147, 41.75],
  zoom: 12.4,
});

let socket;
let cityLoaded = false;

function setError(msg) {
  if (!msg) {
    errorEl.hidden = true;
    errorEl.textContent = "";
    return;
  }
  errorEl.hidden = false;
  errorEl.textContent = msg;
}

async function loadCity() {
  statusEl.textContent = "Loading Naperville streets…";
  const res = await fetch("/city");
  if (!res.ok) throw new Error("City layers failed to load");
  const city = await res.json();
  if (city.origin_lonlat) map.setCenter(city.origin_lonlat);
  if (map.getSource("roads")) {
    map.getSource("roads").setData(city.roads);
    return;
  }
  map.addSource("roads", { type: "geojson", data: city.roads });
  map.addLayer({
    id: "roads",
    type: "line",
    source: "roads",
    paint: { "line-color": "#3dceae", "line-width": 1.6, "line-opacity": 0.55 },
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
      "circle-stroke-color": "#06241c",
    },
  });
  map.addSource("intersections", { type: "geojson", data: emptyFc() });
  map.addLayer({
    id: "intersections",
    type: "circle",
    source: "intersections",
    paint: {
      "circle-radius": ["case", ["get", "had_signals"], 4.8, 3.1],
      "circle-color": ["case", ["get", "had_signals"], "#e07a4a", "#3dceae"],
      "circle-opacity": 0.9,
    },
  });
  cityLoaded = true;
  statusEl.textContent = `${city.counts.intersections} slot pads · ${city.counts.roads} road ways`;
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

function paintSnapshot(snap) {
  if (!cityLoaded || !map.getSource("vehicles")) return;
  map.getSource("vehicles").setData(asFc(snap.vehicles, (v) => ({ kind: v.kind, speed: v.speed_mph })));
  map.getSource("intersections").setData(
    asFc(snap.intersections, (i) => ({ had_signals: i.had_signals, pending: i.pending }))
  );
  const m = snap.metrics;
  document.getElementById("m-t").textContent = `${m ? snap.t.toFixed(0) : 0}s`;
  document.getElementById("m-active").textContent = String(m.active);
  document.getElementById("m-done").textContent = String(m.completed);
  document.getElementById("m-speed").textContent = `${m.mean_speed_mph} mph`;
  document.getElementById("m-delay").textContent = `${m.mean_delay_s}s`;
  document.getElementById("m-stops").textContent = String(m.stops);
  statusEl.textContent = `${snap.policy.toUpperCase()} · ${m.active} moving · ${m.grants} slots granted`;

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
  const proto = location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${proto}://${location.host}/ws`);
  socket.onopen = () => setError("");
  socket.onerror = () => setError("Lost the city runtime. Refresh, or restart with smartcity serve.");
  socket.onclose = () => {
    statusEl.textContent = "Runtime disconnected";
    setTimeout(connectWs, 1500);
  };
  socket.onmessage = (ev) => paintSnapshot(JSON.parse(ev.data));
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

map.on("load", async () => {
  try {
    await loadCity();
    connectWs();
  } catch (err) {
    setError(err.message);
    statusEl.textContent = "City data is not available yet.";
  }
});
