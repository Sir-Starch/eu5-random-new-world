// How each lens looks: what it paints over the physical map, how much relief shows through, which
// lines it draws, what it names and what it writes in a location seen up close; and the colours
// of its classes. The bridge sends each lens's classes and legend; the colours of the thematic
// lenses are chosen here, for the map rather than for an identifier's hash.

import type { Lens, WorldAtlas } from "./atlas";
import { LAND } from "./atlas";
import { VEGETATION } from "./relief";

export interface LensProfile {
  /** The land is the physical map itself rather than a colour per location. */
  physical: boolean;
  /** How much of the relief's shade shows on the land, 0..1. */
  shade: number;
  /** Ink of the lines where the lens's own value changes, 0 for none. */
  borders: number;
  /** Ink of country borders when they are shown. */
  political: number;
  /** Names written large: regions and seas, countries, the lens's classes, or none. */
  names: "regions" | "countries" | "classes" | "none";
  /** What is written in each location when it is large enough to hold it. */
  spots: "resource" | "population" | "development" | null;
  /** Opacity of the lens's colour over the physical map, 0..255; a ramp fades with its value. */
  opacity: number;
}

const BASE: LensProfile = {
  physical: false,
  shade: 0.6,
  borders: 0,
  political: 0.32,
  names: "none",
  spots: null,
  opacity: 225,
};

export const PROFILES: Record<string, LensProfile> = {
  land: { ...BASE, physical: true, shade: 1, political: 0.3, names: "regions" },
  countries: { ...BASE, shade: 0.7, political: 0.82, names: "countries", opacity: 232 },
  cultures: { ...BASE, borders: 0.42, political: 0.22, names: "classes", opacity: 218 },
  religions: { ...BASE, borders: 0.42, political: 0.22, names: "classes", opacity: 218 },
  resources: { ...BASE, shade: 0.55, political: 0.2, spots: "resource", opacity: 228 },
  development: { ...BASE, shade: 0.5, political: 0.28, spots: "development" },
  population: { ...BASE, shade: 0.5, political: 0.28, spots: "population" },
  climate: { ...BASE, shade: 0.8, borders: 0.18, political: 0.22, opacity: 200 },
  terrain: { ...BASE, shade: 1, political: 0.22, opacity: 205 },
  areas: { ...BASE, borders: 0.38, political: 0.3, names: "classes", opacity: 210 },
};

export function profile(layer: string): LensProfile {
  return PROFILES[layer] ?? BASE;
}

type RGB = [number, number, number];

function hex(colour: string): RGB {
  const value = Number.parseInt(colour.slice(1), 16);
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

function toHex([r, g, b]: RGB): string {
  return `#${[r, g, b].map((v) => Math.round(v).toString(16).padStart(2, "0")).join("")}`;
}

// Muted colours that stay apart from one another, for classes that only need to differ from
// their neighbours: cultures, religions, areas.
const QUALITATIVE: RGB[] = [
  "#c9a26b", "#8fb27a", "#c97f6b", "#7fa6c4", "#b58fc0", "#d4c27a", "#6fb5a8", "#c48aa0",
  "#a3a36a", "#9db4d8", "#d19a5a", "#84c2a0", "#b77c5c", "#9a8fc8", "#cdb79a", "#7c9c8a",
].map(hex);

// Climates from the poles to the equator.
const CLIMATES: Record<string, RGB> = {
  arctic: hex("#e8eef4"),
  subpolar: hex("#a9c3d6"),
  cold_arid: hex("#b9a88c"),
  cold_semi_arid: hex("#c8bd92"),
  continental: hex("#7fae86"),
  oceanic: hex("#6cb4b0"),
  mediterranean: hex("#cfb35e"),
  subtropical: hex("#9cc46a"),
  hot_semi_arid: hex("#d9a066"),
  arid: hex("#e6c98a"),
  tropical: hex("#3f9a5c"),
};

const TERRAIN: Record<string, RGB> = {
  flatland: hex("#a9c480"),
  wetlands: hex("#5f9c8e"),
  plateau: hex("#c9b07e"),
  hills: hex("#a88c62"),
  mountains: hex("#85705c"),
  hills_wasteland: hex("#9a9284"),
  mountain_wasteland: hex("#7a746e"),
};

// Raw materials by family, so the map reads as farmland, hunting grounds, plantations, quarries
// and mines rather than as confetti: crops yellow-green, animals brown, the sea blue, cash crops
// purple to red, wood green, building stone grey-beige, metals steel, riches gold.
const RESOURCES: Record<string, RGB> = {
  // crops
  wheat: hex("#e6cf6a"), maize: hex("#e0c24e"), rice: hex("#d8d892"), potato: hex("#c4b168"),
  legumes: hex("#a9c46a"), millet: hex("#d2c07a"), fruit: hex("#e39a5a"), chili: hex("#d8743c"),
  olives: hex("#9aa65a"), wine: hex("#9a4a6a"), sugar: hex("#e8b8c0"),
  // animals
  livestock: hex("#b98a5a"), horses: hex("#a47548"), wild_game: hex("#8a6a44"), fur: hex("#6e5a48"),
  wool: hex("#d9ccb2"), ivory: hex("#efe4cc"), beeswax: hex("#d9b24a"), elephants: hex("#9b8d7c"),
  camels: hex("#c8a874"),
  // the sea
  fish: hex("#4f9fc4"), whale: hex("#3f7aa4"),
  // cash crops
  cotton: hex("#e4e0f0"), tobacco: hex("#8c6a2e"), dyes: hex("#b04a8a"), incense: hex("#c08ab0"),
  fiber_crops: hex("#a5b48a"), medicaments: hex("#6aa88a"), cocoa: hex("#6b4226"),
  coffee: hex("#5a3a2a"), tea: hex("#5f8a4a"), silk: hex("#d6a0c8"), spices: hex("#b4502e"),
  pepper: hex("#7a3a2a"), cloves: hex("#8a4a3a"), saffron: hex("#e07a2a"),
  // wood and stone
  lumber: hex("#4f7a3a"), stone: hex("#9a9a94"), marble: hex("#d6d6d2"), clay: hex("#b5704a"),
  sand: hex("#e0cc98"),
  // minerals and metals
  coal: hex("#45454c"), iron: hex("#6e7884"), copper: hex("#c06a3a"), tin: hex("#a8b4bc"),
  lead: hex("#5e6470"), mercury: hex("#b8b8cc"), salt: hex("#f2f2ee"), saltpeter: hex("#d8d4c4"),
  alum: hex("#c8d0d8"), sulfur: hex("#d8d050"),
  // riches
  goods_gold: hex("#f2c230"), silver: hex("#c8ccd6"), gems: hex("#3cc8b4"), pearls: hex("#f0e6f0"),
  amber: hex("#e09a28"),
};

export const PRECIOUS_MARKS: Record<string, string> = {
  goods_gold: "#f2c230",
  silver: "#dfe3ea",
  gems: "#3cc8b4",
  pearls: "#f6eef6",
  amber: "#e09a28",
};

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
const UNCLAIMED = "#5c6054";
const FADED = "#8f8b7e";
const TRIBAL = "#a69c84";

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
      else if (tribes) opacity[c] = 150;
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
      opacity[c] = Math.round(105 + 140 * share);
    }
  }
  // Land that holds nothing of the lens shows the physical map, faded; so does its swatch.
  legend = legend.map((entry) => (entry.colour.toLowerCase() === UNCLAIMED ? { ...entry, colour: FADED } : entry));
  return { ...lens, colours, classes, legend, opacity };
}
