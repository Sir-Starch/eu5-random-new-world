// A world's atlas as the map viewer uses it: the box of locations unrolled from the bridge's
// runs, each layer's colours, legend entries and border values, and what is known of a location.

import { style, type StyledLens } from "./lenses";
import { poles } from "./relief";
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
  /** Pixels of what is named. */
  weight: number;
  /** How far the name's point lies from the edge of what is named, in pixels. */
  room: number;
  colour: string;
  kind: "country" | "tribe" | "class" | "region" | "sea";
}

export interface Settlement {
  cell: number;
  x: number;
  y: number;
  city: boolean;
  name: string;
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
  private styled = new Map<string, StyledLens>();
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

  /** A lens as the bridge sent it. */
  source(layer: string): Lens {
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

  /** A lens as the window paints it (``style``); without ``tribes`` the countries lens leaves
   *  tribes uncoloured, as the game's political map does, under one legend entry. */
  lens(layer: string, tribes = true, tribesLabel = "Tribes"): StyledLens {
    const key = layer === "countries" ? `${layer}|${tribes}` : layer;
    let found = this.styled.get(key);
    if (!found) {
      found = style(this, this.source(layer), tribes, tribesLabel);
      this.styled.set(key, found);
    }
    return found;
  }

  /** Whether a country is shown as one: states always, tribes when asked. */
  shown(owner: number, tribes: boolean): boolean {
    return owner >= 0 && (tribes || this.data.countries[owner]?.kind === "state");
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
  classCells(layer: string, entry: number, tribes = true): number[] {
    const classes = this.lens(layer, tribes).classes;
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

  /** The names a lens writes large, each where what it names is broadest (``poles``):
   *  regions and seas on the physical map, countries on the political one, the classes of
   *  cultures, religions and areas. Scattered lenses (resources, climate, terrain, the ramps)
   *  write no large names. */
  labelsFor(layer: string, names: "regions" | "countries" | "classes" | "none", tribes = true): Label[] {
    const key = `${layer}|${names}|${tribes}`;
    const cached = this.labelCache.get(key);
    if (cached) return cached;
    const d = this.data;
    const out: Label[] = [];
    const push = (
      entries: { x: number; y: number; room: number; area: number }[],
      describe: (k: number) => { text: string; colour: string; kind: Label["kind"] } | null,
    ): void => {
      entries.forEach((entry, k) => {
        if (entry.area <= 0) return;
        const about = describe(k);
        if (about?.text) out.push({ ...about, x: entry.x, y: entry.y, weight: entry.area, room: entry.room });
      });
    };
    if (names === "countries") {
      const found = poles(this, (c) => (d.kind[c] === LAND && this.shown(d.owner[c], tribes) ? d.owner[c] : -1), d.countries.length);
      push(found, (k) => {
        const country = d.countries[k];
        return { text: country.name, colour: country.color, kind: country.kind === "state" ? "country" : "tribe" };
      });
    } else if (names === "classes") {
      const lens = this.lens(layer, tribes);
      const found = poles(this, (c) => (d.kind[c] === LAND && lens.opacity[c] > 0 ? lens.classes[c] : -1), lens.legend.length);
      push(found, (k) => ({ text: lens.legend[k].label, colour: lens.legend[k].colour, kind: "class" }));
    } else if (names === "regions") {
      for (const [kinds, field, kind] of [
        [[LAND, WASTELAND], d.region, "region"],
        [[SEA], d.names, "sea"],
      ] as const) {
        const index = new Map<string, number>();
        const titles: string[] = [];
        const classOf = new Int32Array(this.cells).fill(-1);
        for (let c = 0; c < this.cells; c++) {
          const title = field[c];
          if (!title || !(kinds as readonly number[]).includes(d.kind[c]) || title.startsWith("$")) continue;
          let k = index.get(title);
          if (k === undefined) {
            k = titles.length;
            index.set(title, k);
            titles.push(title);
          }
          classOf[c] = k;
        }
        const found = poles(this, (c) => classOf[c], titles.length);
        push(found, (k) => ({ text: titles[k], colour: "", kind }));
      }
    }
    out.sort((a, b) => b.weight - a.weight);
    this.labelCache.set(key, out);
    return out;
  }

  /** Cities and towns, as pixel positions. */
  settlements(): Settlement[] {
    const d = this.data;
    const words = d.raw.settlement ?? [];
    const out: Settlement[] = [];
    for (let c = 0; c < this.cells; c++) {
      const index = d.settlement[c];
      if (index < 0 || d.kind[c] !== LAND) continue;
      const [x, y] = this.centre(c);
      out.push({ cell: c, x, y, city: words[index] === "city", name: d.names[c] || d.keys[c] });
    }
    return out;
  }

  /** Capitals, as pixel positions with their country; states' only, unless ``tribes``. */
  capitals(tribes = true): { x: number; y: number; country: CountryInfo }[] {
    return this.data.countries
      .filter((country) => country.capital >= 0 && (tribes || country.kind === "state"))
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
