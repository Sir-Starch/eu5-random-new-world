// A world's atlas as the map viewer uses it: the box of locations unrolled from the bridge's
// runs, each layer's colours, legend entries and border values, and what is known of a location.

import type { AtlasBundle, CountryInfo } from "./types";

export const OUTSIDE = -1;
export const LAND = 0;
export const WASTELAND = 1;
export const SEA = 2;
export const LAKE = 3;

export interface Lens {
  layer: string;
  colours: Uint8Array;
  classes: Int32Array;
  values: Int32Array;
  legend: { label: string; colour: string; count: number }[];
  ramp: string[];
}

export interface Match {
  kind: "country" | "culture" | "religion" | "material" | "place" | "area";
  label: string;
  cells: number[];
  colour?: string;
}

export interface Facts {
  cell: number;
  name: string;
  kind: string;
  area: string;
  region: string;
  country: CountryInfo | null;
  culture: string;
  religion: string;
  material: string;
  precious: boolean;
  climate: string;
  vegetation: string;
  topography: string;
  settlement: string;
  population: number;
  complexity: number;
}

export interface Label {
  text: string;
  x: number;
  y: number;
  weight: number;
  colour: string;
}

function bytes(base64: string): Uint8Array {
  const text = atob(base64);
  const out = new Uint8Array(text.length);
  for (let i = 0; i < text.length; i++) out[i] = text.charCodeAt(i);
  return out;
}

function int32(base64: string): Int32Array {
  const raw = bytes(base64);
  return new Int32Array(raw.buffer, raw.byteOffset, raw.byteLength / 4);
}

/** The box's labels from (label, length) runs: each pixel's location, -1 outside. */
export function unroll(base64: string, width: number, height: number): Int32Array {
  const raw = bytes(base64);
  const runs = new Uint32Array(raw.buffer, raw.byteOffset, raw.byteLength / 4);
  const out = new Int32Array(width * height);
  let at = 0;
  for (let i = 0; i < runs.length; i += 2) {
    const value = runs[i] - 1;
    const end = at + runs[i + 1];
    out.fill(value, at, end);
    at = end;
  }
  if (at !== out.length) throw new Error(`The atlas covers ${at} of ${out.length} pixels`);
  return out;
}

export class WorldAtlas {
  readonly data: AtlasBundle;
  readonly width: number;
  readonly height: number;
  readonly cells: number;
  readonly labels: Int32Array;
  /** Pixels of each location, and their sum of columns and rows (for centroids). */
  readonly area: Float64Array;
  readonly sumX: Float64Array;
  readonly sumY: Float64Array;
  readonly box: Int32Array;
  private lenses = new Map<string, Lens>();
  private labelCache = new Map<string, Label[]>();

  constructor(data: AtlasBundle) {
    this.data = data;
    [this.height, this.width] = data.size;
    this.cells = data.cells;
    this.labels = unroll(data.labels, this.width, this.height);
    this.area = new Float64Array(this.cells);
    this.sumX = new Float64Array(this.cells);
    this.sumY = new Float64Array(this.cells);
    this.box = new Int32Array(this.cells * 4);
    for (let c = 0; c < this.cells; c++) {
      this.box[c * 4] = this.width;
      this.box[c * 4 + 1] = this.height;
      this.box[c * 4 + 2] = -1;
      this.box[c * 4 + 3] = -1;
    }
    const { labels, width, height, area, sumX, sumY, box } = this;
    for (let y = 0; y < height; y++) {
      const row = y * width;
      for (let x = 0; x < width; x++) {
        const c = labels[row + x];
        if (c < 0) continue;
        area[c] += 1;
        sumX[c] += x;
        sumY[c] += y;
        const b = c * 4;
        if (x < box[b]) box[b] = x;
        if (y < box[b + 1]) box[b + 1] = y;
        if (x > box[b + 2]) box[b + 2] = x;
        if (y > box[b + 3]) box[b + 3] = y;
      }
    }
  }

  lens(layer: string): Lens {
    let found = this.lenses.get(layer);
    if (!found) {
      const source = this.data.layers[layer];
      found = {
        layer,
        colours: bytes(source.colours),
        classes: int32(source.classes),
        values: int32(source.values),
        legend: source.legend.map(([label, colour, count]) => ({ label, colour, count })),
        ramp: source.ramp,
      };
      this.lenses.set(layer, found);
    }
    return found;
  }

  cellAt(x: number, y: number): number {
    const column = Math.floor(x);
    const row = Math.floor(y);
    if (column < 0 || row < 0 || column >= this.width || row >= this.height) return -1;
    return this.labels[row * this.width + column];
  }

  isLand(cell: number): boolean {
    return cell >= 0 && this.data.kind[cell] === LAND;
  }

  /** The smallest box around ``cells``, in pixels: left, top, right, bottom. */
  bounds(cells: Iterable<number>): [number, number, number, number] | null {
    let left = Infinity;
    let top = Infinity;
    let right = -Infinity;
    let bottom = -Infinity;
    for (const c of cells) {
      const b = c * 4;
      if (this.box[b + 2] < 0) continue;
      left = Math.min(left, this.box[b]);
      top = Math.min(top, this.box[b + 1]);
      right = Math.max(right, this.box[b + 2] + 1);
      bottom = Math.max(bottom, this.box[b + 3] + 1);
    }
    return Number.isFinite(left) ? [left, top, right, bottom] : null;
  }

  centre(cell: number): [number, number] {
    const a = this.area[cell] || 1;
    return [this.sumX[cell] / a, this.sumY[cell] / a];
  }

  word(field: string, index: number): string {
    return index >= 0 ? (this.data.vocabulary[field]?.[index] ?? "") : "";
  }

  facts(cell: number): Facts | null {
    if (cell < 0 || cell >= this.cells) return null;
    const d = this.data;
    const owner = d.owner[cell];
    const material = d.material[cell];
    return {
      cell,
      name: d.names[cell] || d.keys[cell],
      kind: d.kinds[d.kind[cell]] ?? "land",
      area: d.area[cell],
      region: d.region[cell],
      country: owner >= 0 ? d.countries[owner] : null,
      culture: this.word("culture", d.culture[cell]),
      religion: this.word("religion", d.religion[cell]),
      material: this.word("material", material),
      precious: material >= 0 && d.precious.includes(d.raw.material?.[material] ?? ""),
      climate: this.word("climate", d.climate[cell]),
      vegetation: this.word("vegetation", d.vegetation[cell]),
      topography: this.word("topography", d.topography[cell]),
      settlement: this.word("settlement", d.settlement[cell]),
      population: d.population[cell],
      complexity: d.complexity[cell],
    };
  }

  /** Cells sharing a lens's legend entry with ``cell`` (its country, culture...). */
  classCells(layer: string, entry: number): number[] {
    const classes = this.lens(layer).classes;
    const out: number[] = [];
    for (let c = 0; c < this.cells; c++) if (classes[c] === entry) out.push(c);
    return out;
  }

  cellsWhere(field: keyof AtlasBundle, value: number): number[] {
    const column = this.data[field] as number[];
    const out: number[] = [];
    for (let c = 0; c < this.cells; c++) if (column[c] === value) out.push(c);
    return out;
  }

  /** Countries, cultures, religions, resources, areas and places whose name holds ``query``. */
  find(query: string, limit = 40): Match[] {
    const needle = query.trim().toLocaleLowerCase();
    if (!needle) return [];
    const d = this.data;
    const found: Match[] = [];
    d.countries.forEach((country, number) => {
      if (
        country.name.toLocaleLowerCase().includes(needle) ||
        country.tag.toLocaleLowerCase() === needle
      ) {
        found.push({
          kind: "country",
          label: `${country.name} (${country.tag})`,
          cells: this.cellsWhere("owner", number),
          colour: country.color,
        });
      }
    });
    for (const [field, kind] of [
      ["culture", "culture"],
      ["religion", "religion"],
      ["material", "material"],
    ] as const) {
      const shown = d.vocabulary[field] ?? [];
      const raw = d.raw[field] ?? [];
      shown.forEach((label, index) => {
        if (
          label.toLocaleLowerCase().includes(needle) ||
          (raw[index] ?? "").toLocaleLowerCase().includes(needle)
        ) {
          found.push({ kind, label, cells: this.cellsWhere(field, index) });
        }
      });
    }
    const areas = new Map<string, number[]>();
    for (let c = 0; c < this.cells; c++) {
      const name = d.area[c];
      if (d.kind[c] === LAND && name && name.toLocaleLowerCase().includes(needle)) {
        const list = areas.get(name) ?? [];
        list.push(c);
        areas.set(name, list);
      }
    }
    for (const [label, cells] of areas) found.push({ kind: "area", label, cells });
    for (let c = 0; c < this.cells; c++) {
      const name = d.names[c];
      if (name && d.kind[c] !== SEA && name.toLocaleLowerCase().includes(needle)) {
        found.push({ kind: "place", label: name, cells: [c] });
      }
    }
    return found.slice(0, limit);
  }

  /** Where to write each legend entry of a layer: the centre of its largest contiguous mass is
   *  approximated by the centroid of its pixels, weighted by size. */
  labelsFor(layer: string): Label[] {
    const cached = this.labelCache.get(layer);
    if (cached) return cached;
    const lens = this.lens(layer);
    const d = this.data;
    const out: Label[] = [];
    if (layer === "countries") {
      const sx = new Float64Array(d.countries.length);
      const sy = new Float64Array(d.countries.length);
      const sa = new Float64Array(d.countries.length);
      for (let c = 0; c < this.cells; c++) {
        const owner = d.owner[c];
        if (owner < 0 || d.kind[c] !== LAND) continue;
        sx[owner] += this.sumX[c];
        sy[owner] += this.sumY[c];
        sa[owner] += this.area[c];
      }
      d.countries.forEach((country, n) => {
        if (sa[n] > 0) {
          out.push({
            text: country.name,
            x: sx[n] / sa[n],
            y: sy[n] / sa[n],
            weight: sa[n],
            colour: country.color,
          });
        }
      });
    } else if (layer !== "development" && layer !== "population" && layer !== "land") {
      const n = lens.legend.length;
      const sx = new Float64Array(n);
      const sy = new Float64Array(n);
      const sa = new Float64Array(n);
      for (let c = 0; c < this.cells; c++) {
        const k = lens.classes[c];
        if (k < 0 || d.kind[c] !== LAND) continue;
        sx[k] += this.sumX[c];
        sy[k] += this.sumY[c];
        sa[k] += this.area[c];
      }
      lens.legend.forEach((entry, k) => {
        if (sa[k] > 0) {
          out.push({
            text: entry.label,
            x: sx[k] / sa[k],
            y: sy[k] / sa[k],
            weight: sa[k],
            colour: entry.colour,
          });
        }
      });
    }
    out.sort((a, b) => b.weight - a.weight);
    this.labelCache.set(layer, out);
    return out;
  }

  /** Capitals, as pixel positions with their country. */
  capitals(): { x: number; y: number; country: CountryInfo }[] {
    return this.data.countries
      .filter((country) => country.capital >= 0)
      .map((country) => {
        const [x, y] = this.centre(country.capital);
        return { x, y, country };
      });
  }
}

export function hexColour(hex: string): [number, number, number] {
  const value = Number.parseInt(hex.slice(1), 16);
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}
