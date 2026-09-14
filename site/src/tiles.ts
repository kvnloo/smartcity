/** XYZ helpers for photoreal rasters. Esri uses {z}/{y}/{x}. */

export const ESRI_IMAGERY =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";

export const S2_CLOUDLESS =
  "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2024_3857/default/g/{z}/{y}/{x}.jpg";

export const TERRARIUM_DEM = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png";

export const OSM_TILEJSON = "https://tiles.openfreemap.org/planet";

export type TileXY = { x: number; y: number };

export type MosaicCell = TileXY & { col: number; row: number };

export function lonLatToTile(lon: number, lat: number, z: number): TileXY {
  const n = 2 ** z;
  const x = Math.floor(((lon + 180) / 360) * n);
  const latRad = (lat * Math.PI) / 180;
  const y = Math.floor(((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n);
  return { x, y };
}

export function fillTemplate(template: string, z: number, x: number, y: number): string {
  return template.replaceAll("{z}", String(z)).replaceAll("{x}", String(x)).replaceAll("{y}", String(y));
}

export function mosaicCells(lon: number, lat: number, z: number, radius: number): MosaicCell[] {
  const c = lonLatToTile(lon, lat, z);
  const cells: MosaicCell[] = [];
  for (let dy = -radius; dy <= radius; dy++) {
    for (let dx = -radius; dx <= radius; dx++) {
      cells.push({ x: c.x + dx, y: c.y + dy, col: dx + radius, row: dy + radius });
    }
  }
  return cells;
}

export function mosaicSize(radius: number): number {
  return radius * 2 + 1;
}
