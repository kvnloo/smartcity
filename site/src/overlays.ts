import type { LayerSpecification } from "maplibre-gl";

export function corridorLayers(): LayerSpecification[] {
  return [
    {
      id: "corridors-glow",
      type: "line",
      source: "corridors",
      paint: {
        "line-color": ["case", ["==", ["get", "mode"], "rail"], "#f0d78a", "#e0a36a"],
        "line-width": ["interpolate", ["linear"], ["zoom"], 8, 5, 14, 11],
        "line-opacity": ["interpolate", ["linear"], ["zoom"], 8, 0.28, 15, 0.1],
        "line-blur": 2.4,
      },
    },
    {
      id: "corridors",
      type: "line",
      source: "corridors",
      paint: {
        "line-color": ["case", ["==", ["get", "mode"], "rail"], "#e8c56b", "#c4894a"],
        "line-width": ["interpolate", ["linear"], ["zoom"], 8, 1.25, 14, 3.1],
        "line-opacity": ["interpolate", ["linear"], ["zoom"], 8, 0.92, 15, 0.5],
      },
    },
  ];
}

export function ringLayers(): LayerSpecification[] {
  return [
    {
      id: "rings-fill",
      type: "fill",
      source: "rings",
      maxzoom: 14,
      paint: {
        "fill-color": ["coalesce", ["get", "color"], "#e8c56b"],
        "fill-opacity": ["interpolate", ["linear"], ["zoom"], 7, 0.07, 13, 0.018],
        "fill-antialias": true,
      },
    },
    {
      id: "rings-glow",
      type: "line",
      source: "rings",
      paint: {
        "line-color": ["coalesce", ["get", "color"], "#e8c56b"],
        "line-width": ["interpolate", ["linear"], ["zoom"], 8, 6.5, 15, 2.4],
        "line-opacity": ["interpolate", ["linear"], ["zoom"], 8, 0.32, 15, 0.08],
        "line-blur": 3.6,
      },
    },
    {
      id: "rings",
      type: "line",
      source: "rings",
      paint: {
        "line-color": ["coalesce", ["get", "color"], "#e8c56b"],
        "line-width": ["interpolate", ["linear"], ["zoom"], 8, 1.7, 15, 0.9],
        "line-opacity": ["interpolate", ["linear"], ["zoom"], 8, 0.72, 15, 0.16],
        "line-dasharray": [1.4, 1.6],
      },
    },
    {
      id: "ring-names",
      type: "symbol",
      source: "rings",
      minzoom: 7,
      maxzoom: 12.5,
      layout: {
        "symbol-placement": "line",
        "text-field": ["concat", ["get", "name"], " ", ["to-string", ["get", "radius_km"]], " km"],
        "text-font": ["Noto Sans Regular"],
        "text-size": 11,
        "text-letter-spacing": 0.06,
        "text-max-angle": 28,
        "text-padding": 2,
        "symbol-spacing": 420,
      },
      paint: {
        "text-color": "#f4efe6",
        "text-halo-color": "#0b120f",
        "text-halo-width": 1.15,
        "text-opacity": 0.88,
      },
    },
  ];
}

export function districtLayers(): LayerSpecification[] {
  return [
    {
      id: "districts",
      type: "circle",
      source: "districts",
      minzoom: 7,
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 3, 12, 5.5],
        "circle-color": ["case", ["==", ["get", "role"], "job"], "#e8c56b", "#8fbf6a"],
        "circle-stroke-width": 1,
        "circle-stroke-color": "#132016",
        "circle-opacity": 0.9,
      },
    },
    {
      id: "district-names",
      type: "symbol",
      source: "districts",
      minzoom: 8,
      layout: {
        "text-field": ["get", "name"],
        "text-font": ["Noto Sans Regular"],
        "text-size": ["interpolate", ["linear"], ["zoom"], 8, 10, 13, 13],
        "text-offset": [0, 1.15],
        "text-anchor": "top",
        "text-padding": 2,
      },
      paint: {
        "text-color": "#f4efe6",
        "text-halo-color": "#0b120f",
        "text-halo-width": 1.2,
      },
    },
  ];
}
