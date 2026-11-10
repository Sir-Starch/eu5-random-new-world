// The land editor's drawing: a sheet of kinds (sea, land, mountains, highlands, lowlands, lake),
// the tools that change it and the undo of every change. Nothing here touches the page, so the
// tools are tested without one; the component draws the sheet and passes the pointer to it.

export const SEA = 0;
export const LAND = 1;
export const MOUNTAINS = 2;
export const HIGHLANDS = 3;
export const LOWLANDS = 4;
export const LAKE = 5;
export const KINDS = 6;

export type Tool = "brush" | "eraser" | "fill" | "line" | "rectangle" | "ellipse" | "pan";
export const TOOLS: readonly Tool[] = ["brush", "eraser", "fill", "line", "rectangle", "ellipse", "pan"];

export const MIN_SIZE = 1;
export const MAX_SIZE = 64;
/** How many changes can be undone. */
export const MAX_UNDO = 80;
/** The undo gives up its oldest changes beyond this many changed pixels in all. */
export const MAX_UNDO_PIXELS = 24_000_000;

/** What the editor shows for each kind (sea lets the area under it show): red, green, blue, alpha. */
export const SHOWN: readonly (readonly [number, number, number, number])[] = [
  [0, 0, 0, 0],
  [118, 166, 92, 240],
  [128, 98, 78, 245],
  [214, 176, 80, 240],
  [176, 218, 150, 235],
  [64, 128, 214, 245],
];

/** The kinds that are ground: terrain is painted on these and a lake or the sea over them. */
export function isGround(kind: number): boolean {
  return kind === LAND || kind === MOUNTAINS || kind === HIGHLANDS || kind === LOWLANDS;
}

/** The kinds that mark the kind of ground (they are painted only on ground when asked). */
export function isTerrain(kind: number): boolean {
  return kind === MOUNTAINS || kind === HIGHLANDS || kind === LOWLANDS;
}

/** One change of the sheet: the pixels that differ, as they were and as they became. */
interface Change {
  at: Uint32Array;
  before: Uint8Array;
  after: Uint8Array;
}

export interface Box {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

/** How a stroke treats what is under it. */
export interface Rule {
  /** Terrain (mountains, highlands, lowlands) is painted on ground only, never on sea or lakes. */
  terrainOnGround: boolean;
  /** Shapes: filled, or only their outline (as thick as the brush). */
  filled: boolean;
}

export const DEFAULT_RULE: Rule = { terrainOnGround: true, filled: true };

export class Sheet {
  readonly width: number;
  readonly height: number;
  kinds: Uint8Array;
  private base: Uint8Array | null = null;
  private undone: Change[] = [];
  private redone: Change[] = [];
  private pixels = 0;
  private box: Box | null = null;

  constructor(width: number, height: number, kinds?: Uint8Array) {
    if (kinds && kinds.length !== width * height) throw new Error("The picture is not the sheet's size");
    this.width = width;
    this.height = height;
    this.kinds = kinds ? kinds.slice() : new Uint8Array(width * height);
  }

  get(x: number, y: number): number {
    return x < 0 || y < 0 || x >= this.width || y >= this.height ? SEA : this.kinds[y * this.width + x]!;
  }

  // -- what changed, for drawing ---------------------------------------------------------------

  /** The box of pixels changed since the last call, or null. */
  takeDirty(): Box | null {
    const box = this.box;
    this.box = null;
    return box;
  }

  private touch(x: number, y: number): void {
    const box = this.box;
    if (!box) this.box = { x0: x, y0: y, x1: x, y1: y };
    else {
      if (x < box.x0) box.x0 = x;
      if (y < box.y0) box.y0 = y;
      if (x > box.x1) box.x1 = x;
      if (y > box.y1) box.y1 = y;
    }
  }

  private touchAll(): void {
    this.box = { x0: 0, y0: 0, x1: this.width - 1, y1: this.height - 1 };
  }

  // -- one change: begin, draw, then commit (or cancel) --------------------------------------

  /** Start a change; what is drawn until ``commit`` is one step of the undo. */
  begin(): void {
    this.base = this.kinds.slice();
  }

  /** Throw away what was drawn since ``begin`` and draw again from the start (a shape's preview). */
  restore(): void {
    if (!this.base) return;
    const base = this.base;
    const kinds = this.kinds;
    for (let i = 0; i < kinds.length; i++) {
      if (kinds[i] !== base[i]) {
        kinds[i] = base[i]!;
        this.touch(i % this.width, Math.floor(i / this.width));
      }
    }
  }

  /** End the change; returns whether the sheet is different now. */
  commit(): boolean {
    const base = this.base;
    this.base = null;
    if (!base) return false;
    const kinds = this.kinds;
    let count = 0;
    for (let i = 0; i < kinds.length; i++) if (kinds[i] !== base[i]) count++;
    if (!count) return false;
    const change: Change = { at: new Uint32Array(count), before: new Uint8Array(count), after: new Uint8Array(count) };
    let at = 0;
    for (let i = 0; i < kinds.length; i++) {
      if (kinds[i] !== base[i]) {
        change.at[at] = i;
        change.before[at] = base[i]!;
        change.after[at] = kinds[i]!;
        at++;
      }
    }
    this.undone.push(change);
    this.pixels += count;
    this.redone = [];
    while (this.undone.length > MAX_UNDO || (this.pixels > MAX_UNDO_PIXELS && this.undone.length > 1)) {
      this.pixels -= this.undone.shift()!.at.length;
    }
    return true;
  }

  /** End the change and put the sheet back as it was at ``begin``. */
  cancel(): void {
    this.restore();
    this.base = null;
  }

  get drawing(): boolean {
    return this.base !== null;
  }

  get canUndo(): boolean {
    return this.undone.length > 0;
  }

  get canRedo(): boolean {
    return this.redone.length > 0;
  }

  undo(): boolean {
    const change = this.undone.pop();
    if (!change) return false;
    this.apply(change, change.before);
    this.pixels -= change.at.length;
    this.redone.push(change);
    return true;
  }

  redo(): boolean {
    const change = this.redone.pop();
    if (!change) return false;
    this.apply(change, change.after);
    this.pixels += change.at.length;
    this.undone.push(change);
    return true;
  }

  private apply(change: Change, values: Uint8Array): void {
    for (let i = 0; i < change.at.length; i++) {
      const at = change.at[i]!;
      this.kinds[at] = values[i]!;
      this.touch(at % this.width, Math.floor(at / this.width));
    }
  }

  /** Put another picture on the sheet as one change; returns whether it differs. */
  replace(next: Uint8Array): boolean {
    if (next.length !== this.kinds.length) throw new Error("The picture is not the sheet's size");
    this.begin();
    this.kinds.set(next);
    this.touchAll();
    return this.commit();
  }

  clear(): boolean {
    return this.replace(new Uint8Array(this.kinds.length));
  }

  // -- the tools -------------------------------------------------------------------------------

  private put(x: number, y: number, kind: number, rule: Rule): void {
    if (x < 0 || y < 0 || x >= this.width || y >= this.height) return;
    const at = y * this.width + x;
    const old = this.kinds[at]!;
    if (old === kind) return;
    if (isTerrain(kind) && rule.terrainOnGround && !isGround(old)) return;
    this.kinds[at] = kind;
    this.touch(x, y);
  }

  /** A round dab of ``size`` pixels across, centred on a pixel. */
  stamp(x: number, y: number, size: number, kind: number, rule: Rule = DEFAULT_RULE): void {
    const radius = (size - 1) / 2;
    const reach = Math.ceil(radius);
    const limit = (radius + 0.5) * (radius + 0.5);
    for (let dy = -reach; dy <= reach; dy++) {
      for (let dx = -reach; dx <= reach; dx++) {
        if (dx * dx + dy * dy <= limit) this.put(x + dx, y + dy, kind, rule);
      }
    }
  }

  /** Dabs along the line from one pixel to another, close enough to leave no gaps. */
  stroke(x0: number, y0: number, x1: number, y1: number, size: number, kind: number, rule: Rule = DEFAULT_RULE): void {
    const steps = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0));
    const spacing = Math.max(1, Math.floor(size / 4));
    if (!steps) {
      this.stamp(x0, y0, size, kind, rule);
      return;
    }
    for (let step = 0; step <= steps; step += spacing) {
      this.stamp(Math.round(x0 + ((x1 - x0) * step) / steps), Math.round(y0 + ((y1 - y0) * step) / steps), size, kind, rule);
    }
    this.stamp(x1, y1, size, kind, rule);
  }

  /** The rectangle with these two corners, filled or as an outline ``size`` thick. */
  rectangle(x0: number, y0: number, x1: number, y1: number, size: number, kind: number, rule: Rule = DEFAULT_RULE): void {
    const left = Math.min(x0, x1);
    const right = Math.max(x0, x1);
    const top = Math.min(y0, y1);
    const bottom = Math.max(y0, y1);
    if (rule.filled) {
      for (let y = top; y <= bottom; y++) for (let x = left; x <= right; x++) this.put(x, y, kind, rule);
      return;
    }
    this.stroke(left, top, right, top, size, kind, rule);
    this.stroke(right, top, right, bottom, size, kind, rule);
    this.stroke(right, bottom, left, bottom, size, kind, rule);
    this.stroke(left, bottom, left, top, size, kind, rule);
  }

  /** The ellipse inside the rectangle with these two corners, filled or as an outline. */
  ellipse(x0: number, y0: number, x1: number, y1: number, size: number, kind: number, rule: Rule = DEFAULT_RULE): void {
    const left = Math.min(x0, x1);
    const right = Math.max(x0, x1);
    const top = Math.min(y0, y1);
    const bottom = Math.max(y0, y1);
    const cx = (left + right) / 2;
    const cy = (top + bottom) / 2;
    const rx = (right - left) / 2 + 0.5;
    const ry = (bottom - top) / 2 + 0.5;
    const inside = (x: number, y: number, shrink: number): boolean => {
      const a = rx - shrink;
      const b = ry - shrink;
      if (a <= 0 || b <= 0) return false;
      return ((x - cx) / a) ** 2 + ((y - cy) / b) ** 2 <= 1;
    };
    const thickness = rule.filled ? Infinity : Math.max(1, size);
    for (let y = top; y <= bottom; y++) {
      for (let x = left; x <= right; x++) {
        if (inside(x, y, 0) && (rule.filled || !inside(x, y, thickness))) this.put(x, y, kind, rule);
      }
    }
  }

  /** Paint the whole stretch of equal pixels the pixel belongs to (its four neighbours join it). */
  fill(x: number, y: number, kind: number, rule: Rule = DEFAULT_RULE): number {
    if (x < 0 || y < 0 || x >= this.width || y >= this.height) return 0;
    const width = this.width;
    const height = this.height;
    const target = this.kinds[y * width + x]!;
    if (target === kind) return 0;
    if (isTerrain(kind) && rule.terrainOnGround && !isGround(target)) return 0;
    const kinds = this.kinds;
    const seeds: number[] = [y * width + x];
    let painted = 0;
    while (seeds.length) {
      const seed = seeds.pop()!;
      if (kinds[seed] !== target) continue;
      const row = Math.floor(seed / width);
      let left = seed % width;
      let right = left;
      while (left > 0 && kinds[row * width + left - 1] === target) left--;
      while (right < width - 1 && kinds[row * width + right + 1] === target) right++;
      for (let column = left; column <= right; column++) {
        kinds[row * width + column] = kind;
        this.touch(column, row);
        painted++;
      }
      for (const next of [row - 1, row + 1]) {
        if (next < 0 || next >= height) continue;
        let inRun = false;
        for (let column = left; column <= right; column++) {
          const same = kinds[next * width + column] === target;
          if (same && !inRun) seeds.push(next * width + column);
          inRun = same;
        }
      }
    }
    return painted;
  }

  /** How many pixels there are of each kind. */
  counts(): number[] {
    const found = new Array<number>(KINDS).fill(0);
    for (const kind of this.kinds) found[kind] = (found[kind] ?? 0) + 1;
    return found;
  }
}

/** The kind of every pixel of an RGBA picture, each the nearest of the ``palette``'s colours. */
export function kindsFromRgba(rgba: Uint8ClampedArray | Uint8Array, palette: readonly (readonly number[])[]): Uint8Array {
  const count = rgba.length / 4;
  const kinds = new Uint8Array(count);
  const cache = new Map<number, number>();
  for (let i = 0; i < count; i++) {
    const r = rgba[i * 4]!;
    const g = rgba[i * 4 + 1]!;
    const b = rgba[i * 4 + 2]!;
    const key = (r << 16) | (g << 8) | b;
    let kind = cache.get(key);
    if (kind === undefined) {
      let best = Infinity;
      kind = SEA;
      palette.forEach((colour, index) => {
        const d = (r - colour[0]!) ** 2 + (g - colour[1]!) ** 2 + (b - colour[2]!) ** 2;
        if (d < best) {
          best = d;
          kind = index;
        }
      });
      cache.set(key, kind);
    }
    kinds[i] = kind;
  }
  return kinds;
}

/** An RGBA picture of kinds in the given colours (opaque, for the pictures sent to the generator). */
export function rgbaFromKinds(kinds: Uint8Array, colours: readonly (readonly number[])[], alpha = 255): Uint8ClampedArray<ArrayBuffer> {
  const rgba = new Uint8ClampedArray(kinds.length * 4);
  for (let i = 0; i < kinds.length; i++) {
    const colour = colours[kinds[i]!] ?? colours[0]!;
    rgba[i * 4] = colour[0]!;
    rgba[i * 4 + 1] = colour[1]!;
    rgba[i * 4 + 2] = colour[2]!;
    rgba[i * 4 + 3] = colour[3] ?? alpha;
  }
  return rgba;
}

/** The area's own classes, as the greys of the generator's picture say them. */
export interface Classes {
  outside: number;
  area: number;
  islands: number;
  americas: number;
}

export interface Backdrop {
  showAmericas: boolean;
  showIslands: boolean;
  showMargin: boolean;
}

/** What the sheet is drawn on: outside, the area's sea, the Americas, the island groups and the
 * coast margin where land is dropped, from the greys of the generator's picture. */
export const BACK = {
  outside: [20, 22, 27],
  area: [34, 62, 100],
  americas: [58, 100, 146],
  islands: [44, 96, 104],
  hatch: [226, 96, 90],
} as const;

export function backdropRgba(
  greys: Uint8Array,
  margin: Uint8Array,
  classes: Classes,
  show: Backdrop,
  width: number,
): Uint8ClampedArray<ArrayBuffer> {
  const rgba = new Uint8ClampedArray(greys.length * 4);
  for (let i = 0; i < greys.length; i++) {
    const grey = greys[i]!;
    let colour: readonly number[] = BACK.outside;
    if (grey === classes.area) colour = BACK.area;
    else if (grey === classes.americas) colour = show.showAmericas ? BACK.americas : BACK.area;
    else if (grey === classes.islands) colour = show.showIslands ? BACK.islands : BACK.area;
    let r = colour[0]!;
    let g = colour[1]!;
    let b = colour[2]!;
    if (show.showMargin && margin[i] === 255) {
      const x = i % width;
      const y = Math.floor(i / width);
      if ((x + y) % 6 < 2) {
        r = Math.round(r * 0.45 + BACK.hatch[0] * 0.55);
        g = Math.round(g * 0.45 + BACK.hatch[1] * 0.55);
        b = Math.round(b * 0.45 + BACK.hatch[2] * 0.55);
      }
    }
    rgba[i * 4] = r;
    rgba[i * 4 + 1] = g;
    rgba[i * 4 + 2] = b;
    rgba[i * 4 + 3] = 255;
  }
  return rgba;
}

// -- the view: where the sheet lies in the window --------------------------------------------

export interface Camera {
  x: number;
  y: number;
  scale: number;
}

export const MIN_ZOOM = 0.1;
export const MAX_ZOOM = 24;

export function clampZoom(scale: number): number {
  return Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, scale));
}

/** The sheet at the largest scale that fits the box with a margin, centred. */
export function fitCamera(box: { width: number; height: number }, width: number, height: number, margin = 24): Camera {
  const scale = clampZoom(Math.min((box.width - margin * 2) / width, (box.height - margin * 2) / height));
  return { scale, x: (box.width - width * scale) / 2, y: (box.height - height * scale) / 2 };
}

/** The pixel of the sheet under a point of the box (fractions: floor them for the pixel). */
export function toSheet(camera: Camera, px: number, py: number): [number, number] {
  return [(px - camera.x) / camera.scale, (py - camera.y) / camera.scale];
}

/** The camera zoomed by ``factor`` with the point under (px, py) staying where it is. */
export function zoomAt(camera: Camera, factor: number, px: number, py: number): Camera {
  const scale = clampZoom(camera.scale * factor);
  const [sx, sy] = toSheet(camera, px, py);
  return { scale, x: px - sx * scale, y: py - sy * scale };
}

// -- what the generator says about a picture ----------------------------------------------

/** The generator's report on a picture (``land_check``); the percentages are in thousandths. */
export interface Report {
  land: number;
  mountains: number;
  highlands: number;
  lowlands: number;
  lakes: number;
  outside: number;
  kept: number;
  specks: number;
  open_lakes: [number, number][];
  islands: number;
  /** The least and the most land a world may have, in thousandths of the sheet. */
  low: number;
  high: number;
  refusal: "" | "share" | "outside" | "lake_open";
}

export type Level = "ok" | "warn" | "error";

export interface Line {
  level: Level;
  key: string;
  values: Record<string, unknown>;
}

/** The sentences a report is told in, as keys of the window's strings with their values, the
 * worst first. The picture can be made into a world when none of them is an error. */
export function sayReport(report: Report): Line[] {
  const lines: Line[] = [];
  const share = (report.land / 10).toFixed(1);
  if (report.refusal === "share") {
    lines.push({ level: "error", key: "editor.check.share", values: { share, low: report.low / 10, high: report.high / 10 } });
  }
  if (report.refusal === "outside") lines.push({ level: "error", key: "editor.check.outside_all", values: { kept: report.kept } });
  if (report.refusal === "lake_open") {
    lines.push({ level: "error", key: "editor.check.lake_open", values: { count: report.open_lakes.length } });
  }
  if (!report.refusal && report.kept < 100) {
    lines.push({ level: "warn", key: "editor.check.dropped", values: { dropped: 100 - report.kept } });
  }
  if (report.specks) lines.push({ level: "warn", key: "editor.check.specks", values: { count: report.specks } });
  if (report.islands) lines.push({ level: "warn", key: "editor.check.islands", values: { count: report.islands } });
  if (!report.refusal) lines.push({ level: "ok", key: "editor.check.land", values: { share } });
  return lines;
}

export function refused(report: Report | null): boolean {
  return !report || report.refusal !== "";
}
