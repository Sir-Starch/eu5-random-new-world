// The physical map under every lens, worked out once per atlas: the land's colour from its
// vegetation and climate, softened across the edges of locations; a relief shade from a height
// that each location's topography suggests, smoothed and roughened into ridges where it is
// mountainous; the depth of the water by its distance from the shore. The atlas holds no
// heightmap, so the relief is drawn from what it holds rather than measured.
//
// Fields are at half the atlas's resolution: the viewer filters them linearly, and the coasts
// stay sharp because land and water are told apart by the full-resolution labels.

import type { WorldAtlas } from "./atlas";
import { LAND, LAKE, SEA, WASTELAND } from "./atlas";

export const STEP = 2;

type RGB = [number, number, number];

// The land by vegetation: sand to rainforest.
export const VEGETATION: Record<string, RGB> = {
  desert: [226, 206, 152],
  sparse: [198, 188, 130],
  grasslands: [166, 192, 106],
  woods: [116, 160, 86],
  forest: [74, 128, 72],
  jungle: [48, 114, 68],
};
// How far each climate pulls the land toward a colour (0..1): snow in the cold, dust in the dry.
const CLIMATE: Record<string, [RGB, number]> = {
  arctic: [[240, 244, 248], 0.78],
  subpolar: [[214, 224, 218], 0.36],
  cold_arid: [[196, 184, 160], 0.3],
  cold_semi_arid: [[196, 186, 150], 0.16],
  arid: [[234, 212, 160], 0.22],
  hot_semi_arid: [[222, 196, 138], 0.12],
  mediterranean: [[206, 196, 128], 0.08],
};
// Topography: how high it stands (0..1), how rough it is (0..1), and the rock it shows.
const TOPOGRAPHY: Record<string, { height: number; rough: number; rock: number }> = {
  wetlands: { height: 0, rough: 0.02, rock: 0 },
  flatland: { height: 0.05, rough: 0.06, rock: 0 },
  plateau: { height: 0.3, rough: 0.16, rock: 0.14 },
  hills: { height: 0.24, rough: 0.45, rock: 0.1 },
  mountains: { height: 0.55, rough: 1, rock: 0.36 },
  hills_wasteland: { height: 0.45, rough: 0.8, rock: 0.5 },
  mountain_wasteland: { height: 0.7, rough: 1, rock: 0.6 },
};
const ROCK: RGB = [148, 136, 122];
const WETLAND: RGB = [98, 132, 100];
const SNOW: RGB = [246, 247, 250];

/** The land of a location on the physical map, before softening and shade. */
export function physicalColour(atlas: WorldAtlas, cell: number): RGB {
  const d = atlas.data;
  const raw = d.raw;
  const vegetation = raw.vegetation?.[d.vegetation[cell]] ?? "";
  const climate = raw.climate?.[d.climate[cell]] ?? "";
  const topography = raw.topography?.[d.topography[cell]] ?? "";
  let rgb: RGB = [...(VEGETATION[vegetation] ?? VEGETATION.grasslands)];
  const tint = CLIMATE[climate];
  if (tint) rgb = mix(rgb, tint[0], tint[1]);
  if (topography === "wetlands") rgb = mix(rgb, WETLAND, 0.32);
  const rock = TOPOGRAPHY[topography]?.rock ?? 0;
  const barren = d.kind[cell] === WASTELAND ? 0.55 : rock;
  if (barren > 0) rgb = mix(rgb, ROCK, barren);
  const cold = climate === "arctic" || climate === "subpolar" || climate === "cold_arid";
  if (cold && (d.kind[cell] === WASTELAND || topography === "mountains")) rgb = mix(rgb, SNOW, 0.45);
  return rgb;
}

function mix(a: RGB, b: RGB, share: number): RGB {
  return [
    a[0] + (b[0] - a[0]) * share,
    a[1] + (b[1] - a[1]) * share,
    a[2] + (b[2] - a[2]) * share,
  ];
}

export interface Relief {
  width: number;
  height: number;
  /** Per field pixel: the land's colour and, in alpha, its shade (128 is level ground). */
  land: Uint8Array;
  /** Per field pixel: the water's distance from the shore in field pixels, up to 255. */
  depth: Uint8Array;
}

/** A box blur along rows then columns, ``passes`` times: close to a gaussian. ``values`` stay
 *  as they were. */
export function blur(values: Float32Array, width: number, height: number, radius: number, passes = 2): Float32Array {
  let source: Float32Array = Float32Array.from(values);
  let target: Float32Array = new Float32Array(values.length);
  const span = 2 * radius + 1;
  for (let pass = 0; pass < passes; pass++) {
    for (let y = 0; y < height; y++) {
      const row = y * width;
      let sum = 0;
      for (let x = -radius; x <= radius; x++) sum += source[row + Math.min(width - 1, Math.max(0, x))];
      for (let x = 0; x < width; x++) {
        target[row + x] = sum / span;
        sum += source[row + Math.min(width - 1, x + radius + 1)] - source[row + Math.max(0, x - radius)];
      }
    }
    [source, target] = [target, source];
    for (let x = 0; x < width; x++) {
      let sum = 0;
      for (let y = -radius; y <= radius; y++) sum += source[Math.min(height - 1, Math.max(0, y)) * width + x];
      for (let y = 0; y < height; y++) {
        target[y * width + x] = sum / span;
        sum +=
          source[Math.min(height - 1, y + radius + 1) * width + x] - source[Math.max(0, y - radius) * width + x];
      }
    }
    [source, target] = [target, source];
  }
  return source;
}

/** Chamfer distance (3-4, in tenths of thirds) from every pixel to the nearest ``seed`` pixel. */
export function distance(seed: Uint8Array, width: number, height: number): Float32Array {
  const far = 1e9;
  const out = new Float32Array(seed.length);
  for (let i = 0; i < seed.length; i++) out[i] = seed[i] ? 0 : far;
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const i = y * width + x;
      let v = out[i];
      if (v === 0) continue;
      if (x > 0) v = Math.min(v, out[i - 1] + 3);
      if (y > 0) {
        v = Math.min(v, out[i - width] + 3);
        if (x > 0) v = Math.min(v, out[i - width - 1] + 4);
        if (x < width - 1) v = Math.min(v, out[i - width + 1] + 4);
      }
      out[i] = v;
    }
  }
  for (let y = height - 1; y >= 0; y--) {
    for (let x = width - 1; x >= 0; x--) {
      const i = y * width + x;
      let v = out[i];
      if (v === 0) continue;
      if (x < width - 1) v = Math.min(v, out[i + 1] + 3);
      if (y < height - 1) {
        v = Math.min(v, out[i + width] + 3);
        if (x < width - 1) v = Math.min(v, out[i + width + 1] + 4);
        if (x > 0) v = Math.min(v, out[i + width - 1] + 4);
      }
      out[i] = v;
    }
  }
  for (let i = 0; i < out.length; i++) out[i] /= 3;
  return out;
}

/** Smooth noise in -1..1 from a hashed lattice, the same for the same position. */
function lattice(x: number, y: number): number {
  let h = (Math.imul(x | 0, 374761393) + Math.imul(y | 0, 668265263)) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) & 0xffff) / 32767.5 - 1;
}

function noise(x: number, y: number): number {
  const x0 = Math.floor(x);
  const y0 = Math.floor(y);
  const fx = x - x0;
  const fy = y - y0;
  const sx = fx * fx * (3 - 2 * fx);
  const sy = fy * fy * (3 - 2 * fy);
  const top = lattice(x0, y0) + (lattice(x0 + 1, y0) - lattice(x0, y0)) * sx;
  const bottom = lattice(x0, y0 + 1) + (lattice(x0 + 1, y0 + 1) - lattice(x0, y0 + 1)) * sx;
  return top + (bottom - top) * sy;
}

/** Ridges: folded noise over three octaves, 0..1. */
function ridges(x: number, y: number): number {
  let sum = 0;
  let amplitude = 0.5;
  let frequency = 1 / 9;
  for (let octave = 0; octave < 3; octave++) {
    sum += amplitude * (1 - Math.abs(noise(x * frequency, y * frequency)));
    amplitude *= 0.5;
    frequency *= 2.1;
  }
  return sum / 0.875;
}

const cache = new WeakMap<WorldAtlas, Relief>();

/** The physical fields of an atlas, worked out on first use. */
export function relief(atlas: WorldAtlas): Relief {
  const known = cache.get(atlas);
  if (known) return known;
  const width = Math.ceil(atlas.width / STEP);
  const height = Math.ceil(atlas.height / STEP);
  const size = width * height;
  const kind = atlas.data.kind;
  const raw = atlas.data.raw.topography ?? [];

  // Each location's colour, height and roughness.
  const colour = new Float32Array(atlas.cells * 3);
  const high = new Float32Array(atlas.cells);
  const rough = new Float32Array(atlas.cells);
  for (let c = 0; c < atlas.cells; c++) {
    if (kind[c] !== LAND && kind[c] !== WASTELAND) continue;
    const rgb = physicalColour(atlas, c);
    colour.set(rgb, c * 3);
    const topography = TOPOGRAPHY[raw[atlas.data.topography[c]] ?? ""] ?? TOPOGRAPHY.flatland;
    const wasteland = kind[c] === WASTELAND ? TOPOGRAPHY.mountain_wasteland : null;
    high[c] = (wasteland ?? topography).height;
    rough[c] = (wasteland ?? topography).rough;
  }

  // Sample the box: land mask, colours, heights.
  const mask = new Float32Array(size);
  const water = new Uint8Array(size);
  const reds = new Float32Array(size);
  const greens = new Float32Array(size);
  const blues = new Float32Array(size);
  const heights = new Float32Array(size);
  const roughness = new Float32Array(size);
  for (let y = 0; y < height; y++) {
    const ay = Math.min(atlas.height - 1, y * STEP + 1);
    for (let x = 0; x < width; x++) {
      const ax = Math.min(atlas.width - 1, x * STEP + 1);
      const c = atlas.labels[ay * atlas.width + ax];
      const i = y * width + x;
      // Beyond the New World's own sea zones the viewer draws open ocean.
      if (c < 0 || kind[c] === SEA || kind[c] === LAKE) {
        water[i] = 1;
        continue;
      }
      mask[i] = 1;
      reds[i] = colour[c * 3];
      greens[i] = colour[c * 3 + 1];
      blues[i] = colour[c * 3 + 2];
      heights[i] = high[c];
      roughness[i] = rough[c];
    }
  }

  // Soften colours within the land (normalised by the land's own share, so no sea bleeds in).
  const share = blur(mask, width, height, 2);
  const soft = [blur(reds, width, height, 2), blur(greens, width, height, 2), blur(blues, width, height, 2)];

  // Height: smoothed slopes, roughened into ridges where the land is rough, to the shore.
  const base = blur(heights, width, height, 6, 3);
  const grain = blur(roughness, width, height, 3);
  const shore = distance(water, width, height);
  const lift = new Float32Array(size);
  for (let i = 0; i < size; i++) {
    if (!mask[i]) continue;
    const x = i % width;
    const y = (i - x) / width;
    const coast = Math.min(1, shore[i] / 6);
    lift[i] = (base[i] + (grain[i] > 0.01 ? grain[i] * 0.2 * ridges(x, y) : 0)) * coast;
  }

  // Shade from the north-west, as maps are lit.
  const land = new Uint8Array(size * 4);
  const light = [-0.55, -0.62, 0.56];
  const z = 9;
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const i = y * width + x;
      const weight = share[i];
      if (weight > 0.001) {
        const variation = 1 + 0.035 * noise(x / 3.1, y / 3.1);
        land[i * 4] = clamp((soft[0][i] / weight) * variation);
        land[i * 4 + 1] = clamp((soft[1][i] / weight) * variation);
        land[i * 4 + 2] = clamp((soft[2][i] / weight) * variation);
      }
      const left = lift[y * width + Math.max(0, x - 1)];
      const right = lift[y * width + Math.min(width - 1, x + 1)];
      const up = lift[Math.max(0, y - 1) * width + x];
      const down = lift[Math.min(height - 1, y + 1) * width + x];
      const nx = (left - right) * z;
      const ny = (up - down) * z;
      const length = Math.hypot(nx, ny, 1);
      const lit = (nx * light[0] + ny * light[1] + light[2]) / length;
      // Level ground lit at the light's own height reads as 128.
      land[i * 4 + 3] = clamp((lit / light[2]) * 128);
    }
  }

  const depth = new Uint8Array(size);
  const fromLand = distance(Uint8Array.from(mask, (m) => (m ? 1 : 0)), width, height);
  for (let i = 0; i < size; i++) depth[i] = water[i] ? Math.min(255, Math.round(fromLand[i])) : 0;

  const found = { width, height, land, depth };
  cache.set(atlas, found);
  return found;
}

function clamp(value: number): number {
  return Math.max(0, Math.min(255, Math.round(value)));
}

/**
 * Where to write the name of each class: per class, the pixel deepest inside it (farthest from
 * any other class or the water), and how deep that is. A class's deepest point lies in its
 * largest, roundest part, so a scattered class is named once, where it is broadest.
 */
export function poles(
  atlas: WorldAtlas,
  classOf: (cell: number) => number,
  classes: number,
): { x: number; y: number; room: number; area: number }[] {
  const { width, height, labels } = atlas;
  const cellClass = new Int32Array(atlas.cells);
  for (let c = 0; c < atlas.cells; c++) cellClass[c] = classOf(c);
  const pixel = new Int32Array(width * height);
  for (let i = 0; i < pixel.length; i++) pixel[i] = labels[i] < 0 ? -1 : cellClass[labels[i]];
  const edge = new Uint8Array(pixel.length);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const i = y * width + x;
      const k = pixel[i];
      if (k < 0) {
        edge[i] = 1;
        continue;
      }
      if (
        x === 0 || y === 0 || x === width - 1 || y === height - 1 ||
        pixel[i - 1] !== k || pixel[i + 1] !== k || pixel[i - width] !== k || pixel[i + width] !== k
      ) {
        edge[i] = 1;
      }
    }
  }
  const depth = distance(edge, width, height);
  const out = Array.from({ length: classes }, () => ({ x: 0, y: 0, room: -1, area: 0 }));
  for (let i = 0; i < pixel.length; i++) {
    const k = pixel[i];
    if (k < 0 || k >= classes) continue;
    const entry = out[k];
    entry.area += 1;
    if (depth[i] > entry.room) {
      entry.room = depth[i];
      entry.x = (i % width) + 0.5;
      entry.y = Math.floor(i / width) + 0.5;
    }
  }
  return out;
}
