import type { StyleSpecification } from "maplibre-gl";
import type { LodConfig } from "./lod";
import { ESRI_IMAGERY, OSM_TILEJSON, S2_CLOUDLESS, TERRARIUM_DEM } from "./tiles";

export function lookdevStyle(lod: LodConfig): StyleSpecification {
  const sources: StyleSpecification["sources"] = {
    s2: {
      type: "raster",
      tiles: [S2_CLOUDLESS],
      tileSize: 256,
      maxzoom: 13,
      attribution: "Sentinel-2 cloudless © EOX IT Services GmbH",
    },
    esri: {
      type: "raster",
      tiles: [ESRI_IMAGERY],
      tileSize: 256,
      minzoom: 11,
      maxzoom: 19,
      attribution:
        "Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
    },
  };
  if (lod.buildings) {
    sources.openmaptiles = { type: "vector", url: OSM_TILEJSON };
  }
  if (lod.terrain || lod.hillshade) {
    sources.terrain = {
      type: "raster-dem",
      tiles: [TERRARIUM_DEM],
      encoding: "terrarium",
      tileSize: 256,
      maxzoom: 15,
      attribution: "Mapzen Terrarium DEM",
    };
  }

  const layers: StyleSpecification["layers"] = [
    {
      id: "s2",
      type: "raster",
      source: "s2",
      maxzoom: 14,
      paint: { "raster-saturation": -0.08, "raster-contrast": 0.06 },
    },
    {
      id: "esri",
      type: "raster",
      source: "esri",
      minzoom: 11,
      paint: {
        "raster-opacity": ["interpolate", ["linear"], ["zoom"], 11, 0, 12.4, 1],
        "raster-saturation": -0.04,
        "raster-contrast": 0.1,
        "raster-brightness-min": 0.04,
      },
    },
  ];

  if (lod.hillshade) {
    layers.push({
      id: "hillshade",
      type: "hillshade",
      source: "terrain",
      paint: {
        "hillshade-exaggeration": 0.22,
        "hillshade-shadow-color": "#1a2418",
        "hillshade-highlight-color": "#f3ead2",
        "hillshade-illumination-direction": 265,
      },
    });
  }

  if (lod.buildings) {
    layers.push({
      id: "building-3d",
      type: "fill-extrusion",
      source: "openmaptiles",
      "source-layer": "building",
      minzoom: lod.buildingMinZoom,
      paint: {
        "fill-extrusion-color": [
          "interpolate",
          ["linear"],
          ["coalesce", ["get", "render_height"], 12],
          8,
          "#d8c4a4",
          40,
          "#c9b497",
          120,
          "#b7a48c",
        ],
        "fill-extrusion-height": ["coalesce", ["get", "render_height"], ["get", "height"], 9],
        "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0],
        "fill-extrusion-opacity": 0.86,
        "fill-extrusion-vertical-gradient": true,
      },
    });
  }

  const style: StyleSpecification = {
    version: 8,
    glyphs: "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf",
    sources,
    layers,
    transition: { duration: lod.fadeDuration, delay: 0 },
  };

  if (lod.lights) {
    style.light = {
      anchor: "viewport",
      color: "#fff1d6",
      intensity: 0.48,
      position: [1.12, 96, 28],
    };
  }

  if (lod.sky) {
    style.sky = {
      "sky-color": "#6f93b8",
      "horizon-color": "#e0c48a",
      "fog-color": "#c5d0d4",
      "fog-ground-blend": 0.62,
      "horizon-fog-blend": 0.82,
      "sky-horizon-blend": 0.7,
      "atmosphere-blend": 0.58,
    };
  }

  if (lod.terrain) {
    style.terrain = { source: "terrain", exaggeration: 1.18 };
  }

  return style;
}
