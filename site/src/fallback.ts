import { ESRI_IMAGERY, fillTemplate, mosaicCells, mosaicSize } from "./tiles";

export type MosaicOpts = {
  lon: number;
  lat: number;
  z: number;
  radius: number;
  template?: string;
};

/** Photoreal stills when WebGL is missing. Not the sim. */
export function mountMosaic(el: HTMLElement, opts: MosaicOpts): void {
  const radius = Math.max(0, opts.radius);
  const z = opts.z;
  const template = opts.template ?? ESRI_IMAGERY;
  const cells = mosaicCells(opts.lon, opts.lat, z, radius);
  const n = mosaicSize(radius);
  el.hidden = false;
  el.style.display = "grid";
  el.style.gridTemplateColumns = `repeat(${n}, 1fr)`;
  el.style.gridTemplateRows = `repeat(${n}, 1fr)`;
  el.replaceChildren();
  for (const cell of cells) {
    const img = document.createElement("img");
    img.src = fillTemplate(template, z, cell.x, cell.y);
    img.alt = "";
    img.draggable = false;
    img.decoding = "async";
    el.appendChild(img);
  }
}
