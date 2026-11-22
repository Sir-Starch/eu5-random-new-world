// The physical map under every lens, worked out once per atlas: the land's colour from its
// vegetation and climate, softened across the edges of locations and turned to bare rock and
// snow where the ground is high; a height that each location's topography suggests, smoothed over
// the land alone (no sea pulls it down, so the ground does not fall away into a cliff at the
// shore) and roughened into wandering ridges where it is mountainous; the light that falls on
// that height from four sides at once; the depth of the water by its distance from the shore.
// The atlas holds no heightmap, so the relief is drawn from what it holds rather than measured.
//
// Fields are at half the atlas's resolution: the viewer filters them linearly, and the coasts
// stay sharp because land and water are told apart by the full-resolution labels. The classic
// window draws the same map with the same numbers (rnw.gui.mapstyle, lenses.json).

import type { WorldAtlas } from "./atlas";
import { LAND, LAKE, SEA, WASTELAND } from "./atlas";
import { CLIMATE_TINTS, COLOURS, hex, RELIEF, TOPOGRAPHY, VEGETATION, type RGB } from "./style";

export { VEGETATION };

export const STEP = 2;
/** The water's depth is kept in this many steps to a field pixel, so a shelf does not step. */
export const DEPTH_SCALE = 4;
const ROUGH = 0.01;
const SOME_LAND = 0.001;

const ROCK = hex(COLOURS.rock);
const WETLAND = hex(COLOURS.wetland);
const SNOW = hex(COLOURS.snow);

/** The land of a location on the physical map, before softening and shade. */
export function physicalColour(atlas: WorldAtlas, cell: number): RGB {
  const d = atlas.data;
  const raw = d.raw;
  const vegetation = raw.vegetation?.[d.vegetation[cell]] ?? "";
  const climate = raw.climate?.[d.climate[cell]] ?? "";
  const topography = raw.topography?.[d.topography[cell]] ?? "";
  let rgb: RGB = [...(VEGETATION[vegetation] ?? VEGETATION.grasslands)];
  const tint = CLIMATE_TINTS[climate];
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
  /** Per field pixel: the land's colour and, in alpha, its shade (128 is level ground, 1 to 255
   *  from full shadow to full light). */
  land: Uint8Array;
  /** Per field pixel: the water's distance from the shore, in steps of 1 / ``DEPTH_SCALE`` of
   *  a field pixel, up to 255. */
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

/** Ridge lines: folded noise over three octaves, 0..1, the field bent by a slow noise so the
 *  crests wander instead of following the lattice. */
function ridges(x: number, y: number): number {
  const bentX = x + RELIEF.warp * noise(x / 11 + 7.1, y / 11);
  const bentY = y + RELIEF.warp * noise(x / 11, y / 11 + 3.7);
  let sum = 0;
  let amplitude = 0.5;
  let frequency = 1 / 9;
  for (let octave = 0; octave < 3; octave++) {
    sum += amplitude * (1 - Math.abs(noise(bentX * frequency, bentY * frequency)));
    amplitude *= 0.5;
    frequency *= 2.1;
  }
  return sum / 0.875;
}

/** ``values`` smoothed over where ``weight`` is: each pixel the mean of the weighted pixels
 *  around it, so where there is no weight nothing pulls the mean down. */
export function spread(
  values: Float32Array,
  weight: Float32Array,
  width: number,
  height: number,
  radius: number,
  passes = 2,
): Float32Array {
  const share = blur(weight, width, height, radius, passes);
  const product = new Float32Array(values.length);
  for (let i = 0; i < product.length; i++) product[i] = values[i] * weight[i];
  const total = blur(product, width, height, radius, passes);
  for (let i = 0; i < total.length; i++) total[i] = share[i] > SOME_LAND ? total[i] / Math.max(share[i], SOME_LAND) : 0;
  return total;
}

/** Exact Euclidean distance (Felzenszwalb and Huttenlocher) from every pixel to the nearest
 *  ``seed`` pixel, in pixels; a field with no seed is 1e9 everywhere. */
export function euclid(seed: Uint8Array, width: number, height: number): Float32Array {
  const far = 1e20;
  const out = new Float32Array(seed.length);
  const longest = Math.max(width, height);
  const f = new Float64Array(longest);
  const d = new Float64Array(longest);
  const v = new Int32Array(longest);
  const z = new Float64Array(longest + 1);
  const pass = (n: number): void => {
    let k = 0;
    v[0] = 0;
    z[0] = -far;
    z[1] = far;
    for (let q = 1; q < n; q++) {
      let cut: number;
      for (;;) {
        const p = v[k];
        cut = (f[q] + q * q - (f[p] + p * p)) / (2 * q - 2 * p);
        if (cut <= z[k] && k > 0) k--;
        else break;
      }
      k++;
      v[k] = q;
      z[k] = cut;
      z[k + 1] = far;
    }
    k = 0;
    for (let q = 0; q < n; q++) {
      while (z[k + 1] < q) k++;
      d[q] = (q - v[k]) * (q - v[k]) + f[v[k]];
    }
  };
  for (let x = 0; x < width; x++) {
    for (let y = 0; y < height; y++) f[y] = seed[y * width + x] ? 0 : far;
    pass(height);
    for (let y = 0; y < height; y++) out[y * width + x] = d[y];
  }
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) f[x] = out[y * width + x];
    pass(width);
    for (let x = 0; x < width; x++) out[y * width + x] = Math.min(1e9, Math.sqrt(d[x]));
  }
  return out;
}

/** The light on a height field: 0 on level ground, towards -1 in shadow and 1 in light. The
 *  slope is a Sobel difference; every light of ``RELIEF.lights`` lights the surface as a matt
 *  one, and their mean, squeezed by a tanh, is the shade. */
function shade(lift: Float32Array, width: number, height: number): Float32Array {
  const out = new Float32Array(lift.length);
  const sun = Math.sin((RELIEF.light_height * Math.PI) / 180);
  const flat = Math.cos((RELIEF.light_height * Math.PI) / 180);
  const lights = RELIEF.lights.map(([azimuth, share]) => [
    Math.sin((azimuth * Math.PI) / 180) * flat,
    -Math.cos((azimuth * Math.PI) / 180) * flat,
    share,
  ]);
  for (let y = 0; y < height; y++) {
    const up = Math.max(0, y - 1) * width;
    const here = y * width;
    const down = Math.min(height - 1, y + 1) * width;
    for (let x = 0; x < width; x++) {
      const l = Math.max(0, x - 1);
      const r = Math.min(width - 1, x + 1);
      const slopeX = (lift[up + r] + 2 * lift[here + r] + lift[down + r] - (lift[up + l] + 2 * lift[here + l] + lift[down + l])) / 8;
      const slopeY = (lift[down + l] + 2 * lift[down + x] + lift[down + r] - (lift[up + l] + 2 * lift[up + x] + lift[up + r])) / 8;
      const nx = -slopeX * RELIEF.z;
      const ny = -slopeY * RELIEF.z;
      const length = Math.sqrt(nx * nx + ny * ny + 1);
      let total = 0;
      for (const [dx, dy, share] of lights) total += share * ((nx * dx + ny * dy + sun) / length / sun - 1);
      out[here + x] = Math.tanh(total * RELIEF.gain);
    }
  }
  return out;
}

function smoothstep(edge0: number, edge1: number, value: number): number {
  const t = Math.min(1, Math.max(0, (value - edge0) / (edge1 - edge0)));
  return t * t * (3 - 2 * t);
}

/** Land colour ``rgb`` where the ground is high turned towards bare, warm grey rock, and on the
 *  crests above ``line`` (the snow line of the climate there) towards snow: the colour itself
 *  says where the mountains are, not only the shade. Written into ``out`` at ``o``. */
function upland(rgb: RGB, base: number, lift: number, line: number, out: Float32Array, o: number): void {
  const rise = smoothstep(RELIEF.upland[0], RELIEF.upland[1], base) * RELIEF.upland[2];
  const grey = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2];
  const cap = smoothstep(line, line + RELIEF.snow.width, lift) * RELIEF.snow.share;
  const rock = [grey * 1.06 * 0.96 + 8, grey * 0.96 + 8, grey * 0.9 * 0.96 + 8];
  for (let c = 0; c < 3; c++) {
    const bare = rgb[c] + (rock[c] - rgb[c]) * rise;
    out[o + c] = bare + (SNOW[c] - bare) * cap;
  }
}

const cache = new WeakMap<WorldAtlas, Relief>();

/** Install fields computed by the atlas worker; renderers keep using the same cache. */
export function rememberRelief(atlas: WorldAtlas, field: Relief): void {
  cache.set(atlas, field);
}

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
  const snowLine = new Float32Array(atlas.cells).fill(RELIEF.snow.default);
  for (let c = 0; c < atlas.cells; c++) {
    if (kind[c] !== LAND && kind[c] !== WASTELAND) continue;
    snowLine[c] = RELIEF.snow.lines[atlas.data.raw.climate?.[atlas.data.climate[c]] ?? ""] ?? RELIEF.snow.default;
    const rgb = physicalColour(atlas, c);
    colour.set(rgb, c * 3);
    // A wasteland has the relief of its own topography (a flat wild, a dune, a plateau); one the
    // style does not know stands as a mountain, a land as a plain.
    const fallback = kind[c] === WASTELAND ? TOPOGRAPHY.mountain_wasteland : TOPOGRAPHY.flatland;
    const topography = TOPOGRAPHY[raw[atlas.data.topography[c]] ?? ""] ?? fallback;
    high[c] = topography.height;
    rough[c] = topography.rough;
  }

  // Sample the box: land mask, colours, heights.
  const mask = new Float32Array(size);
  const water = new Uint8Array(size);
  const lake = new Uint8Array(size);
  const sampled = new Int32Array(size).fill(-1);
  const reds = new Float32Array(size);
  const greens = new Float32Array(size);
  const blues = new Float32Array(size);
  const heights = new Float32Array(size);
  const roughness = new Float32Array(size);
  const lines = new Float32Array(size);
  for (let y = 0; y < height; y++) {
    const ay = Math.min(atlas.height - 1, y * STEP + 1);
    for (let x = 0; x < width; x++) {
      const ax = Math.min(atlas.width - 1, x * STEP + 1);
      const c = atlas.labels[ay * atlas.width + ax];
      const i = y * width + x;
      // Beyond the New World's own sea zones the viewer draws open ocean.
      if (c < 0 || kind[c] === SEA || kind[c] === LAKE) {
        water[i] = 1;
        if (c >= 0 && kind[c] === LAKE) {
          lake[i] = 1;
          sampled[i] = c;
        }
        continue;
      }
      mask[i] = 1;
      reds[i] = colour[c * 3];
      greens[i] = colour[c * 3 + 1];
      blues[i] = colour[c * 3 + 2];
      heights[i] = high[c];
      roughness[i] = rough[c];
      lines[i] = snowLine[c];
    }
  }

  // A lake lies in the land: its surface is as high as the land that meets it, not a pit whose
  // walls the shade would draw as a crater, and only the sea is a shore.
  const lakeHigh = lakeHeights(atlas, sampled, mask, lake, heights, width, height);
  for (let i = 0; i < size; i++) if (lake[i]) heights[i] = lakeHigh[sampled[i]];

  // Soften colours within the land (normalised by the land's own share, so no sea bleeds in).
  const share = blur(mask, width, height, 2);
  const soft = [blur(reds, width, height, 2), blur(greens, width, height, 2), blur(blues, width, height, 2)];
  const softLine = blur(lines, width, height, 2);

  // Height: smoothed over the land alone, roughened into ridges where the land is rough.
  const surface = new Float32Array(size);
  for (let i = 0; i < size; i++) surface[i] = mask[i] || lake[i] ? 1 : 0;
  const base = spread(heights, surface, width, height, 6, 3);
  const grain = spread(roughness, surface, width, height, 3);
  const lift = new Float32Array(size);
  for (let i = 0; i < size; i++) {
    const x = i % width;
    const y = (i - x) / width;
    lift[i] = base[i] + (grain[i] > ROUGH ? grain[i] * RELIEF.ridge * ridges(x, y) : 0);
  }
  const lit = shade(lift, width, height);

  const land = new Uint8Array(size * 4);
  const tinted = new Float32Array(3);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const i = y * width + x;
      const weight = share[i];
      if (weight > SOME_LAND) {
        const variation = 1 + 0.035 * noise(x / 3.1, y / 3.1);
        upland(
          [(soft[0][i] / weight) * variation, (soft[1][i] / weight) * variation, (soft[2][i] / weight) * variation],
          base[i],
          lift[i],
          softLine[i] / weight,
          tinted,
          0,
        );
        land[i * 4] = clamp(tinted[0]);
        land[i * 4 + 1] = clamp(tinted[1]);
        land[i * 4 + 2] = clamp(tinted[2]);
      }
      // Level ground and water read 128; light 255 and shadow 1.
      land[i * 4 + 3] = mask[i] ? Math.min(255, Math.max(1, Math.round(128 + 127 * lit[i]))) : 128;
    }
  }

  // The water's distance from the land in quarter pixels: no stairs in the shelf.
  const depth = new Uint8Array(size);
  const fromLand = euclid(Uint8Array.from(mask, (m) => (m ? 1 : 0)), width, height);
  for (let i = 0; i < size; i++) depth[i] = water[i] ? Math.min(255, Math.round(fromLand[i] * DEPTH_SCALE)) : 0;

  const found = { width, height, land, depth };
  cache.set(atlas, found);
  return found;
}

/**
 * The height of each lake location: the mean height of the land its pixels touch (up, down, left
 * and right), or flatland's for a lake that touches none. ``sampled`` holds each pixel's location.
 */
function lakeHeights(
  atlas: WorldAtlas,
  sampled: Int32Array,
  mask: Float32Array,
  lake: Uint8Array,
  heights: Float32Array,
  width: number,
  height: number,
): Float32Array {
  const total = new Float64Array(atlas.cells);
  const count = new Float64Array(atlas.cells);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const i = y * width + x;
      if (!lake[i]) continue;
      const c = sampled[i];
      if (x > 0 && mask[i - 1]) { total[c] += heights[i - 1]; count[c]++; }
      if (x < width - 1 && mask[i + 1]) { total[c] += heights[i + 1]; count[c]++; }
      if (y > 0 && mask[i - width]) { total[c] += heights[i - width]; count[c]++; }
      if (y < height - 1 && mask[i + width]) { total[c] += heights[i + width]; count[c]++; }
    }
  }
  const out = new Float32Array(atlas.cells);
  for (let c = 0; c < atlas.cells; c++) out[c] = count[c] > 0 ? total[c] / count[c] : TOPOGRAPHY.flatland.height;
  return out;
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
