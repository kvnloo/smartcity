import type { StyleSpecification } from "maplibre-gl";
import type { LodConfig } from "./lod";
import { ESRI_IMAGERY, OSM_TILEJSON, S2_CLOUDLESS, TERRARIUM_DEM } from "./tiles";

/** Prairie DEM is almost flat; keep exaggeration honest. */
export const TERRAIN_EXAGGERATION = 1.12;

/** 07:30 inbound rush — sun just east of due east, ~14° above the horizon. */
const DAWN_LIGHT = {
  anchor: "map" as const,
  color: "#ffd4a8",
  intensity: 0.4,
  position: [1.22, 105, 76] as [number, number, number],
};

const DAWN_SKY = {
  "sky-color": "#3a587c",
  "horizon-color": "#f3b57a",
  "fog-color": "#d0c4b4",
  "fog-ground-blend": 0.68,
  "horizon-fog-blend": 0.86,
  "sky-horizon-blend": 0.62,
  "atmosphere-blend": 0.72,
};

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
      paint: {
        "raster-saturation": -0.1,
        "raster-contrast": 0.08,
        "raster-hue-rotate": 8,
        "raster-brightness-min": 0.04,
        "raster-resampling": "linear",
        "raster-fade-duration": lod.fadeDuration,
      },
    },
    {
      id: "esri",
      type: "raster",
      source: "esri",
      minzoom: 11,
      paint: {
        "raster-opacity": ["interpolate", ["linear"], ["zoom"], 11, 0, 12.4, 1],
        "raster-saturation": -0.08,
        "raster-contrast": 0.14,
        "raster-brightness-min": 0.05,
        "raster-brightness-max": 0.9,
        "raster-hue-rotate": 10,
        "raster-resampling": "linear",
        "raster-fade-duration": lod.fadeDuration,
      },
    },
  ];

  if (lod.hillshade) {
    layers.push({
      id: "hillshade",
      type: "hillshade",
      source: "terrain",
      paint: {
        "hillshade-exaggeration": 0.26,
        "hillshade-shadow-color": "#1a2430",
        "hillshade-highlight-color": "#ffe2b8",
        "hillshade-accent-color": "#6a5a48",
        "hillshade-illumination-direction": 105,
        "hillshade-illumination-anchor": "map",
      },
    });
  }

  if (lod.buildings) {
    layers.push(
      {
        id: "building-footprint",
        type: "fill",
        source: "openmaptiles",
        "source-layer": "building",
        minzoom: lod.buildingMinZoom,
        paint: {
          "fill-color": "#1c1814",
          "fill-opacity": 0.22,
          "fill-outline-color": "#2e2820",
        },
      },
      {
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
            6,
            "#e6c9a6",
            28,
            "#d4b394",
            80,
            "#c4a486",
            160,
            "#b39278",
          ],
          "fill-extrusion-height": ["coalesce", ["get", "render_height"], ["get", "height"], 9],
          "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], ["get", "min_height"], 0],
          "fill-extrusion-opacity": 0.88,
          "fill-extrusion-vertical-gradient": true,
        },
      },
    );
  }

  const style: StyleSpecification = {
    version: 8,
    glyphs: "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf",
    sources,
    layers,
    transition: { duration: lod.fadeDuration, delay: 0 },
  };

  if (lod.lights) {
    style.light = DAWN_LIGHT;
  }

  if (lod.sky) {
    style.sky = DAWN_SKY;
  }

  if (lod.terrain) {
    style.terrain = { source: "terrain", exaggeration: TERRAIN_EXAGGERATION };
  }

  return style;
}
