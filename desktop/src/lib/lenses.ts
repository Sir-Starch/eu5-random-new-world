// How each lens looks: what it paints over the physical map, how much relief shows through, which
// lines it draws, what it names and what it writes in a location seen up close (the profiles and
// palettes in ``style``); and the colours of its classes. The bridge sends each lens's classes
// and legend; the colours of the thematic lenses are chosen here, for the map rather than for an
// identifier's hash.

import type { Lens, WorldAtlas } from "./atlas";
import { LAND } from "./atlas";
import {
  CLIMATES,
  COLOURS,
  PRECIOUS_MARKS,
  PROFILES,
  QUALITATIVE,
  RAMP_OPACITY,
  RESOURCES,
  TERRAIN,
  TRIBE_OPACITY,
  VEGETATION,
  hex,
  toHex,
  type LensProfile,
  type RGB,
} from "./style";

export { PRECIOUS_MARKS, PROFILES };

export type { LensProfile };

const BASE: LensProfile = PROFILES.cultures;

export function profile(layer: string): LensProfile {
  return PROFILES[layer] ?? BASE;
}

function hashed(key: string): RGB {
  let h = 2166136261;
  for (let i = 0; i < key.length; i++) h = Math.imul(h ^ key.charCodeAt(i), 16777619);
  return QUALITATIVE[(h >>> 0) % QUALITATIVE.length];
}

/** A colour a little lighter or darker by ``key``, so neighbours of one hue are told apart. */
function nudge([r, g, b]: RGB, key: number): RGB {
  const factor = 1 + (((key * 2654435761) >>> 0) % 7 - 3) * 0.035;
  return [Math.min(255, r * factor), Math.min(255, g * factor), Math.min(255, b * factor)];
}

/** For each class, its neighbours: classes that touch it across the land. */
export function neighbours(atlas: WorldAtlas, classOf: Int32Array, classes: number): Set<number>[] {
  const out = Array.from({ length: classes }, () => new Set<number>());
  const { width, height, labels } = atlas;
  const kind = atlas.data.kind;
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const c = labels[y * width + x];
      if (c < 0 || kind[c] !== LAND) continue;
      const a = classOf[c];
      if (a < 0) continue;
      for (const other of [x + 1 < width ? labels[y * width + x + 1] : -1, y + 1 < height ? labels[(y + 1) * width + x] : -1]) {
        if (other < 0 || other === c || kind[other] !== LAND) continue;
        const b = classOf[other];
        if (b >= 0 && b !== a) {
          out[a].add(b);
          out[b].add(a);
        }
      }
    }
  }
  return out;
}

/** Colours for classes such that no two neighbours share one, largest classes first. */
export function colourClasses(adjacent: Set<number>[], sizes: number[], palette = QUALITATIVE.length): number[] {
  const order = sizes.map((_, k) => k).sort((a, b) => sizes[b] - sizes[a] || a - b);
  const colours = new Array<number>(sizes.length).fill(-1);
  const use = new Array<number>(palette).fill(0);
  for (const k of order) {
    const taken = new Set<number>();
    for (const n of adjacent[k]) if (colours[n] >= 0) taken.add(colours[n]);
    let best = -1;
    for (let step = 0; step < palette; step++) {
      const candidate = (k * 7 + step) % palette;
      if (taken.has(candidate)) continue;
      if (best < 0 || use[candidate] < use[best]) best = candidate;
    }
    if (best < 0) best = k % palette;
    colours[k] = best;
    use[best] += 1;
  }
  return colours;
}

/** A lens with this window's colours: each class's colour in its legend and on its cells, and in
 *  ``opacity`` how strongly each cell's colour covers the physical map (0: the physical map,
 *  faded, as for land no country holds). */
export interface StyledLens extends Lens {
  opacity: Uint8Array;
}

// The bridge's colour for land without a country, culture, value...
const UNCLAIMED = COLOURS.unclaimed;
const FADED = COLOURS.faded;
const TRIBAL = COLOURS.tribal;

export function style(atlas: WorldAtlas, lens: Lens, tribes: boolean, tribesLabel: string): StyledLens {
  const layer = lens.layer;
  const d = atlas.data;
  const kind = d.kind;
  const look = profile(layer);
  const cells = atlas.cells;
  const colours = new Uint8Array(lens.colours);
  const opacity = new Uint8Array(cells);
  let legend = lens.legend.map((entry) => ({ ...entry }));
  let classes = lens.classes;
  const paint = (c: number, rgb: RGB): void => {
    colours[c * 3] = rgb[0];
    colours[c * 3 + 1] = rgb[1];
    colours[c * 3 + 2] = rgb[2];
  };
  const vocabulary = (field: string): string[] => d.raw[field] ?? [];
  const recolour = (pick: (entry: number) => RGB | null): void => {
    const fresh = legend.map((entry, k) => {
      const rgb = pick(k);
      return rgb ? { ...entry, colour: toHex(rgb) } : entry;
    });
    for (let c = 0; c < cells; c++) {
      const k = classes[c];
      if (k >= 0 && kind[c] === LAND) paint(c, hex(fresh[k].colour));
    }
    legend = fresh;
  };
  // The legend entry whose cells use a vocabulary word (the first such cell tells).
  const wordOf = (field: keyof typeof d, words: string[]): (string | null)[] => {
    const column = d[field] as number[];
    const found = legend.map(() => null as string | null);
    for (let c = 0; c < cells; c++) {
      const k = classes[c];
      if (k >= 0 && found[k] === null && kind[c] === LAND && column[c] >= 0) found[k] = words[column[c]] ?? null;
    }
    return found;
  };

  if (layer === "countries") {
    const tribal = d.countries.map((country) => country.kind !== "state");
    if (!tribes) {
      // As the game's political map: tribes are not coloured; their land is one entry.
      const tribeEntries = new Set<number>();
      for (let c = 0; c < cells; c++) {
        const owner = d.owner[c];
        if (owner >= 0 && tribal[owner] && classes[c] >= 0) tribeEntries.add(classes[c]);
      }
      if (tribeEntries.size) {
        const kept = legend.map((_, k) => k).filter((k) => !tribeEntries.has(k));
        const index = new Int32Array(legend.length).fill(-1);
        kept.forEach((k, n) => (index[k] = n));
        const count = [...tribeEntries].reduce((sum, k) => sum + legend[k].count, 0);
        const merged = [...kept.map((k) => legend[k]), { label: tribesLabel, colour: TRIBAL, count }];
        // Largest first, as the bridge orders a legend; the tribes' entry takes its place.
        const order = merged.map((_, k) => k).sort((a, b) => merged[b].count - merged[a].count || a - b);
        const position = new Int32Array(merged.length);
        order.forEach((k, n) => (position[k] = n));
        legend = order.map((k) => merged[k]);
        const remapped = new Int32Array(cells);
        for (let c = 0; c < cells; c++) {
          const k = classes[c];
          remapped[c] = k < 0 ? -1 : position[tribeEntries.has(k) ? kept.length : index[k]];
        }
        classes = remapped;
      }
    }
    for (let c = 0; c < cells; c++) {
      const owner = d.owner[c];
      if (kind[c] !== LAND || owner < 0) continue;
      if (!tribal[owner]) opacity[c] = look.opacity;
      else if (tribes) opacity[c] = TRIBE_OPACITY;
    }
  } else if (layer === "cultures" || layer === "religions" || layer === "areas") {
    const field = layer === "cultures" ? "culture" : layer === "religions" ? "religion" : "";
    const own = new Int32Array(cells).fill(-1);
    for (let c = 0; c < cells; c++) {
      const value = field ? (d[field] as number[])[c] : 0;
      if (kind[c] === LAND && value >= 0 && classes[c] >= 0) own[c] = classes[c];
    }
    const sizes = legend.map(() => 0);
    for (let c = 0; c < cells; c++) if (own[c] >= 0) sizes[own[c]] += atlas.area[c];
    const touching = neighbours(atlas, own, legend.length);
    const picked = colourClasses(touching, sizes);
    recolour((k) => (sizes[k] > 0 ? nudge(QUALITATIVE[picked[k]], k) : null));
    for (let c = 0; c < cells; c++) if (own[c] >= 0) opacity[c] = look.opacity;
  } else if (layer === "land") {
    // The physical map paints itself; its legend shows the colours it uses.
    const words = wordOf("vegetation", vocabulary("vegetation"));
    const fresh = legend.map((entry, k) => {
      const rgb = VEGETATION[words[k] ?? ""];
      return rgb ? { ...entry, colour: toHex(rgb) } : entry;
    });
    legend = fresh;
  } else if (layer === "resources" || layer === "climate" || layer === "terrain") {
    const field = layer === "resources" ? "material" : layer === "climate" ? "climate" : "topography";
    const palette = layer === "resources" ? RESOURCES : layer === "climate" ? CLIMATES : TERRAIN;
    const words = wordOf(field, vocabulary(field));
    recolour((k) => (words[k] ? (palette[words[k] ?? ""] ?? hashed(words[k] ?? "")) : null));
    const column = d[field] as number[];
    for (let c = 0; c < cells; c++) if (kind[c] === LAND && column[c] >= 0) opacity[c] = look.opacity;
  } else if (layer === "development" || layer === "population") {
    // A ramp fades into the physical map at its low end.
    const source = layer === "development" ? d.complexity : d.population;
    let top = 1;
    for (let c = 0; c < cells; c++) if (kind[c] === LAND) top = Math.max(top, source[c]);
    for (let c = 0; c < cells; c++) {
      if (kind[c] !== LAND || source[c] <= 0) continue;
      const share = layer === "development" ? source[c] / top : Math.sqrt(source[c] / top);
      opacity[c] = Math.round(RAMP_OPACITY[0] + RAMP_OPACITY[1] * share);
    }
  }
  // Land that holds nothing of the lens shows the physical map, faded; so does its swatch.
  legend = legend.map((entry) => (entry.colour.toLowerCase() === UNCLAIMED ? { ...entry, colour: FADED } : entry));
  return { ...lens, colours, classes, legend, opacity };
}
