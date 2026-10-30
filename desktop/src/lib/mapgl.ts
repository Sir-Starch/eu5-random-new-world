// The map's pixels. Every lens is painted over the physical map (``relief``): the land's colour
// and relief shade and the water's depth, filtered smoothly; a thematic lens covers the land with
// its colour per location, as strongly as the lens says (``lenses``), and land that holds nothing
// of the lens shows the physical map faded. With WebGL 2 the box of locations is a texture of
// location numbers and each lens a table of colours, so a lens changes by uploading a few
// kilobytes; borders, coasts, outlines and the dimming of what is not selected are worked out per
// screen pixel, sharp at every zoom. Without WebGL 2 a canvas draws the same colours at the
// atlas's own resolution.

import type { Camera } from "./camera";
import { LAKE, LAND, SEA, type WorldAtlas } from "./atlas";
import { profile, type StyledLens } from "./lenses";
import { relief, STEP, type Relief } from "./relief";

const TEX_W = 1024;
export const HOVER = 1;
export const PINNED = 2;
export const MATCH = 4;

export interface Overlays {
  lensBorders: boolean;
  political: boolean;
  locations: boolean;
  coast: boolean;
}

export interface Theme {
  ink: [number, number, number];
  accent: [number, number, number];
}

export interface Renderer {
  readonly kind: "webgl2" | "canvas";
  readonly canvas: HTMLCanvasElement;
  setAtlas(atlas: WorldAtlas): void;
  /** Show ``layer``; without ``tribes`` tribes are neither coloured nor bordered. */
  setLens(layer: string, tribes: boolean, tribesLabel: string): void;
  setFlags(hover: number, pinned: number, match: ReadonlySet<number> | null): void;
  /** Draw at ``camera``; ``dpr`` overrides the screen's pixel ratio (1 for a picture). */
  draw(camera: Camera, overlays: Overlays, theme: Theme, dpr?: number): void;
  dispose(): void;
}

// -- colours shared by both renderers ---------------------------------------------------------

const SHALLOW: [number, number, number] = [0.23, 0.43, 0.64];
const DEEP: [number, number, number] = [0.1, 0.21, 0.4];
const LAKE_SHALLOW: [number, number, number] = [0.38, 0.6, 0.8];
const LAKE_DEEP: [number, number, number] = [0.25, 0.46, 0.7];
const COAST_DEPTH = 16;
/** The open ocean around the New World's sea zones; the viewer's background is the same. */
export const OCEAN: [number, number, number] = [0.085, 0.18, 0.35];
export const OCEAN_CSS = `rgb(${OCEAN.map((v) => Math.round(v * 255)).join(", ")})`;

const VERTEX = `#version 300 es
in vec2 aPos;
void main() { gl_Position = vec4(aPos, 0.0, 1.0); }`;

const FRAGMENT = `#version 300 es
precision highp float;
precision highp int;
precision highp isampler2D;
uniform isampler2D uLabels;
uniform sampler2D uColours;
uniform isampler2D uInfo;
uniform sampler2D uRelief;
uniform sampler2D uDepth;
uniform vec2 uSize;
uniform vec2 uField;
uniform vec2 uOrigin;
uniform float uScale;
uniform vec2 uCanvas;
uniform float uDpr;
uniform int uMatch;
uniform int uPhysical;
uniform float uShade;
uniform float uLensInk;
uniform float uPoliticalInk;
uniform int uPoliticalRings;
uniform int uLocations;
uniform int uCoast;
uniform vec3 uInk;
uniform vec3 uAccent;
out vec4 outColour;

const int TEX_W = ${TEX_W};
const vec3 SHALLOW = vec3(${SHALLOW.join(", ")});
const vec3 DEEP = vec3(${DEEP.join(", ")});
const vec3 LAKE_SHALLOW = vec3(${LAKE_SHALLOW.join(", ")});
const vec3 LAKE_DEEP = vec3(${LAKE_DEEP.join(", ")});
const vec3 OCEAN = vec3(${OCEAN.join(", ")});

int cellAt(vec2 p) {
  ivec2 q = ivec2(floor(p));
  if (q.x < 0 || q.y < 0 || q.x >= int(uSize.x) || q.y >= int(uSize.y)) return -1;
  return texelFetch(uLabels, q, 0).r;
}
ivec2 slot(int c) { return ivec2(c % TEX_W, c / TEX_W); }
ivec4 info(int c) { return c < 0 ? ivec4(-2147483647, -2147483647, 0, 4) : texelFetch(uInfo, slot(c), 0); }
bool solid(ivec4 i) { return i.a <= 1; }

// The colour of the map at atlas point p; alpha 0 outside the New World.
vec4 surface(vec2 p) {
  if (p.x < 0.0 || p.y < 0.0 || p.x >= uSize.x || p.y >= uSize.y) return vec4(uMatch == 1 ? OCEAN * 0.6 : OCEAN, 1.0);
  int c = cellAt(p);
  ivec4 me = info(c);
  int kind = c < 0 ? ${SEA} : me.a;
  vec2 uv = p / (float(${STEP}) * uField);
  vec3 rgb;
  if (kind == ${SEA} || kind == ${LAKE}) {
    float t = smoothstep(0.0, float(${COAST_DEPTH}), texture(uDepth, uv).r * 255.0);
    rgb = kind == ${LAKE} ? mix(LAKE_SHALLOW, LAKE_DEEP, t) : mix(mix(SHALLOW, DEEP, t), OCEAN, smoothstep(float(${COAST_DEPTH}), float(${COAST_DEPTH * 3}), texture(uDepth, uv).r * 255.0));
  } else {
    vec4 relief = texture(uRelief, uv);
    vec3 land = relief.rgb;
    if (uPhysical == 0) {
      vec4 theme = texelFetch(uColours, slot(c), 0);
      if (theme.a < 0.004) {
        float g = dot(land, vec3(0.299, 0.587, 0.114));
        land = mix(land, vec3(g * 1.02, g, g * 0.94), 0.62) * 0.93 + 0.04;
      } else {
        land = mix(land, theme.rgb, theme.a);
      }
    }
    rgb = land * mix(1.0, relief.a * (255.0 / 128.0), uShade);
  }
  if (uMatch == 1 && (me.b & ${MATCH}) == 0) {
    float g = dot(rgb, vec3(0.299, 0.587, 0.114));
    rgb = mix(rgb, vec3(g), 0.7) * 0.42;
  }
  return vec4(rgb, 1.0);
}

void main() {
  vec2 frag = vec2(gl_FragCoord.x, uCanvas.y - gl_FragCoord.y);
  vec2 p = uOrigin + frag / uScale;
  int c = cellAt(p);
  ivec4 me = info(c);
  vec4 colour;
  if (uScale < 0.95) {
    // Zoomed out: average a few points of the screen pixel, so coasts and borders do not step.
    float s = 0.25 / uScale;
    colour = (surface(p + vec2(-s, -s)) + surface(p + vec2(s, -s)) + surface(p + vec2(-s, s)) + surface(p + vec2(s, s))) * 0.25;
  } else {
    colour = surface(p);
  }
  vec3 rgb = colour.rgb;
  float alpha = 1.0;

  float one = uDpr / uScale;
  float lens = 0.0, political = 0.0, location = 0.0, shore = 0.0, foam = 0.0;
  float match = 0.0, hover = 0.0, pinned = 0.0;
  for (int ring = 1; ring <= 3; ring++) {
    float d = one * float(ring);
    for (int i = 0; i < 4; i++) {
      vec2 o = i == 0 ? vec2(d, 0.0) : i == 1 ? vec2(-d, 0.0) : i == 2 ? vec2(0.0, d) : vec2(0.0, -d);
      int k = cellAt(p + o);
      if (k == c) continue;
      ivec4 other = info(k);
      bool bothLand = me.a == ${LAND} && other.a == ${LAND};
      bool claimed = me.g >= 0 || other.g >= 0;
      if (ring == 1) {
        if (bothLand && other.r != me.r) lens = 1.0;
        if (bothLand) location = 1.0;
        if (solid(me) && !solid(other) && c >= 0) shore = 1.0;
        if (((me.b ^ other.b) & ${HOVER}) != 0) hover = 1.0;
      }
      if (!solid(me) && solid(other) && k >= 0) foam = max(foam, ring == 1 ? 1.0 : ring == 2 ? 0.3 : 0.0);
      if (ring <= uPoliticalRings && bothLand && claimed && other.g != me.g) {
        political = max(political, ring == 1 ? 1.0 : 0.3);
      }
      if (ring <= 2 && ((me.b ^ other.b) & ${MATCH}) != 0 && (me.b & ${MATCH}) != 0) match = 1.0;
      if (((me.b ^ other.b) & ${PINNED}) != 0) pinned = max(pinned, ring == 3 ? 0.5 : 1.0);
    }
  }
  if (uCoast == 1) {
    rgb = mix(rgb, uInk, 0.3 * shore);
    rgb = mix(rgb, vec3(0.86, 0.93, 1.0), 0.13 * foam);
  }
  if (c >= 0) {
    if (uLocations == 1 && uScale > 2.2 * uDpr) rgb = mix(rgb, uInk, 0.16 * location);
    rgb = mix(rgb, uInk, uLensInk * lens);
    // Country borders of other lenses come in as the map is brought closer.
    float near = uPoliticalRings == 2 ? 1.0 : smoothstep(0.3, 0.9, uScale / uDpr);
    rgb = mix(rgb, uInk, uPoliticalInk * political * near);
    if ((me.b & ${HOVER}) != 0) rgb = mix(rgb, vec3(1.0), 0.22);
    if ((me.b & ${PINNED}) != 0) rgb = mix(rgb, uAccent, 0.18);
  }
  if (match > 0.0) { rgb = mix(rgb, uAccent, 0.95); alpha = 1.0; }
  if (hover > 0.0 && (me.b & ${HOVER}) != 0) { rgb = vec3(1.0); }
  if (pinned > 0.0) { rgb = mix(rgb, uAccent, pinned); alpha = max(alpha, pinned); }
  outColour = vec4(rgb * alpha, alpha);
}`;

function compile(gl: WebGL2RenderingContext, type: number, source: string): WebGLShader {
  const shader = gl.createShader(type);
  if (!shader) throw new Error("No shader");
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    throw new Error(gl.getShaderInfoLog(shader) ?? "Shader did not compile");
  }
  return shader;
}

/** What a lens puts in the per-location tables: its border value, the owner shown (-1 for a
 *  tribe when tribes are hidden), the flags and the kind. */
function infoOf(atlas: WorldAtlas, lens: StyledLens, tribes: boolean, flags: Int32Array, out: Int32Array): void {
  const { owner, kind } = atlas.data;
  for (let c = 0; c < atlas.cells; c++) {
    out[c * 4] = lens.values[c];
    out[c * 4 + 1] = atlas.shown(owner[c], tribes) ? owner[c] : -1;
    out[c * 4 + 2] = flags[c];
    out[c * 4 + 3] = kind[c];
  }
}

class GLRenderer implements Renderer {
  readonly kind = "webgl2" as const;
  private gl: WebGL2RenderingContext;
  private program: WebGLProgram;
  private labels: WebGLTexture | null = null;
  private colours: WebGLTexture | null = null;
  private info: WebGLTexture | null = null;
  private relief: WebGLTexture | null = null;
  private depth: WebGLTexture | null = null;
  private field: Relief | null = null;
  private atlas: WorldAtlas | null = null;
  private layer = "";
  private tribes = false;
  private lens: StyledLens | null = null;
  private rows = 1;
  private infoData = new Int32Array(0);
  private flags = new Int32Array(0);
  private matching = false;
  private uniforms = new Map<string, WebGLUniformLocation | null>();

  constructor(
    readonly canvas: HTMLCanvasElement,
    gl: WebGL2RenderingContext,
  ) {
    this.gl = gl;
    const program = gl.createProgram();
    if (!program) throw new Error("No program");
    gl.attachShader(program, compile(gl, gl.VERTEX_SHADER, VERTEX));
    gl.attachShader(program, compile(gl, gl.FRAGMENT_SHADER, FRAGMENT));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error(gl.getProgramInfoLog(program) ?? "Program did not link");
    }
    this.program = program;
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const position = gl.getAttribLocation(program, "aPos");
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
  }

  private uniform(name: string): WebGLUniformLocation | null {
    if (!this.uniforms.has(name)) {
      this.uniforms.set(name, this.gl.getUniformLocation(this.program, name));
    }
    return this.uniforms.get(name) ?? null;
  }

  private texture(smooth = false): WebGLTexture {
    const gl = this.gl;
    const texture = gl.createTexture();
    if (!texture) throw new Error("No texture");
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, smooth ? gl.LINEAR_MIPMAP_LINEAR : gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, smooth ? gl.LINEAR : gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return texture;
  }

  setAtlas(atlas: WorldAtlas): void {
    const gl = this.gl;
    this.atlas = atlas;
    this.layer = "";
    this.lens = null;
    this.rows = Math.max(1, Math.ceil(atlas.cells / TEX_W));
    this.flags = new Int32Array(atlas.cells);
    this.infoData = new Int32Array(TEX_W * this.rows * 4);
    for (const texture of [this.labels, this.colours, this.info, this.relief, this.depth]) gl.deleteTexture(texture);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    this.labels = this.texture();
    gl.texImage2D(
      gl.TEXTURE_2D, 0, gl.R32I, atlas.width, atlas.height, 0, gl.RED_INTEGER, gl.INT, atlas.labels,
    );
    this.colours = this.texture();
    this.info = this.texture();
    const field = relief(atlas);
    this.field = field;
    this.relief = this.texture(true);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, field.width, field.height, 0, gl.RGBA, gl.UNSIGNED_BYTE, field.land);
    gl.generateMipmap(gl.TEXTURE_2D);
    this.depth = this.texture(true);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.R8, field.width, field.height, 0, gl.RED, gl.UNSIGNED_BYTE, field.depth);
    gl.generateMipmap(gl.TEXTURE_2D);
  }

  setLens(layer: string, tribes: boolean, tribesLabel: string): void {
    const atlas = this.atlas;
    if (!atlas || (layer === this.layer && tribes === this.tribes)) return;
    this.layer = layer;
    this.tribes = tribes;
    const gl = this.gl;
    const lens = atlas.lens(layer, tribes, tribesLabel);
    this.lens = lens;
    const rgba = new Uint8Array(TEX_W * this.rows * 4);
    for (let c = 0; c < atlas.cells; c++) {
      rgba[c * 4] = lens.colours[c * 3];
      rgba[c * 4 + 1] = lens.colours[c * 3 + 1];
      rgba[c * 4 + 2] = lens.colours[c * 3 + 2];
      rgba[c * 4 + 3] = lens.opacity[c];
    }
    gl.bindTexture(gl.TEXTURE_2D, this.colours);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, TEX_W, this.rows, 0, gl.RGBA, gl.UNSIGNED_BYTE, rgba);
    this.writeInfo();
  }

  setFlags(hover: number, pinned: number, match: ReadonlySet<number> | null): void {
    if (!this.atlas) return;
    this.flags.fill(0);
    if (match) for (const c of match) this.flags[c] |= MATCH;
    if (hover >= 0) this.flags[hover] |= HOVER;
    if (pinned >= 0) this.flags[pinned] |= PINNED;
    this.matching = match !== null;
    this.writeInfo();
  }

  private writeInfo(): void {
    const atlas = this.atlas;
    if (!atlas || !this.lens) return;
    infoOf(atlas, this.lens, this.tribes, this.flags, this.infoData);
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, this.info);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA32I, TEX_W, this.rows, 0, gl.RGBA_INTEGER, gl.INT, this.infoData);
  }

  draw(camera: Camera, overlays: Overlays, theme: Theme, ratio?: number): void {
    const gl = this.gl;
    const atlas = this.atlas;
    const field = this.field;
    const dpr = ratio ?? (window.devicePixelRatio || 1);
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    if (!atlas || !field || !this.layer) return;
    const look = profile(this.layer);
    gl.useProgram(this.program);
    const bind = (unit: number, texture: WebGLTexture | null, name: string): void => {
      gl.activeTexture(gl.TEXTURE0 + unit);
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.uniform1i(this.uniform(name), unit);
    };
    bind(0, this.labels, "uLabels");
    bind(1, this.colours, "uColours");
    bind(2, this.info, "uInfo");
    bind(3, this.relief, "uRelief");
    bind(4, this.depth, "uDepth");
    gl.uniform2f(this.uniform("uSize"), atlas.width, atlas.height);
    gl.uniform2f(this.uniform("uField"), field.width, field.height);
    gl.uniform2f(this.uniform("uOrigin"), camera.x, camera.y);
    gl.uniform1f(this.uniform("uScale"), camera.scale * dpr);
    gl.uniform2f(this.uniform("uCanvas"), this.canvas.width, this.canvas.height);
    gl.uniform1f(this.uniform("uDpr"), dpr);
    gl.uniform1i(this.uniform("uMatch"), this.matching ? 1 : 0);
    gl.uniform1i(this.uniform("uPhysical"), look.physical ? 1 : 0);
    gl.uniform1f(this.uniform("uShade"), look.shade);
    gl.uniform1f(this.uniform("uLensInk"), overlays.lensBorders ? look.borders : 0);
    gl.uniform1f(this.uniform("uPoliticalInk"), overlays.political ? look.political : 0);
    gl.uniform1i(this.uniform("uPoliticalRings"), this.layer === "countries" ? 2 : 1);
    gl.uniform1i(this.uniform("uLocations"), overlays.locations ? 1 : 0);
    gl.uniform1i(this.uniform("uCoast"), overlays.coast ? 1 : 0);
    gl.uniform3f(this.uniform("uInk"), ...(theme.ink.map((v) => v / 255) as [number, number, number]));
    gl.uniform3f(
      this.uniform("uAccent"),
      ...(theme.accent.map((v) => v / 255) as [number, number, number]),
    );
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }

  dispose(): void {
    const gl = this.gl;
    for (const texture of [this.labels, this.colours, this.info, this.relief, this.depth]) gl.deleteTexture(texture);
    gl.deleteProgram(this.program);
  }
}

// -- the same colours on the processor: the minimap and the canvas renderer -------------------

/** The colour of one location's pixel (-1: the open sea) at field pixel ``f`` for a lens, as
 *  the shader paints it without lines: RGBA 0..255 into ``out`` at ``o``. */
export function paintPixel(
  atlas: WorldAtlas,
  lens: StyledLens,
  field: Relief,
  cell: number,
  f: number,
  out: Uint8ClampedArray,
  o: number,
): void {
  const kind = cell < 0 ? SEA : atlas.data.kind[cell];
  let r: number;
  let g: number;
  let b: number;
  if (kind === SEA || kind === LAKE) {
    const t = Math.min(1, field.depth[f] / COAST_DEPTH);
    const smooth = t * t * (3 - 2 * t);
    const [a, z] = kind === LAKE ? [LAKE_SHALLOW, LAKE_DEEP] : [SHALLOW, DEEP];
    const far = kind === LAKE ? 0 : Math.min(1, Math.max(0, (field.depth[f] - COAST_DEPTH) / (2 * COAST_DEPTH)));
    const open = far * far * (3 - 2 * far);
    r = (a[0] + (z[0] - a[0]) * smooth + (OCEAN[0] - z[0]) * open) * 255;
    g = (a[1] + (z[1] - a[1]) * smooth + (OCEAN[1] - z[1]) * open) * 255;
    b = (a[2] + (z[2] - a[2]) * smooth + (OCEAN[2] - z[2]) * open) * 255;
  } else {
    const look = profile(lens.layer);
    r = field.land[f * 4];
    g = field.land[f * 4 + 1];
    b = field.land[f * 4 + 2];
    if (!look.physical) {
      const opacity = lens.opacity[cell] / 255;
      if (opacity === 0) {
        const grey = 0.299 * r + 0.587 * g + 0.114 * b;
        r = (r + (grey * 1.02 - r) * 0.62) * 0.93 + 10;
        g = (g + (grey - g) * 0.62) * 0.93 + 10;
        b = (b + (grey * 0.94 - b) * 0.62) * 0.93 + 10;
      } else {
        r += (lens.colours[cell * 3] - r) * opacity;
        g += (lens.colours[cell * 3 + 1] - g) * opacity;
        b += (lens.colours[cell * 3 + 2] - b) * opacity;
      }
    }
    const shade = 1 + ((field.land[f * 4 + 3] * 2) / 255 - 1) * look.shade;
    r *= shade;
    g *= shade;
    b *= shade;
  }
  out[o] = r;
  out[o + 1] = g;
  out[o + 2] = b;
  out[o + 3] = 255;
}

/** The whole box at ``width`` x ``height`` pixels, for the minimap. */
export function paintBox(atlas: WorldAtlas, lens: StyledLens, width: number, height: number): ImageData {
  const field = relief(atlas);
  const image = new ImageData(width, height);
  for (let y = 0; y < height; y++) {
    const ay = Math.min(atlas.height - 1, Math.floor(((y + 0.5) / height) * atlas.height));
    for (let x = 0; x < width; x++) {
      const ax = Math.min(atlas.width - 1, Math.floor(((x + 0.5) / width) * atlas.width));
      const c = atlas.labels[ay * atlas.width + ax];
      const f = Math.floor(ay / STEP) * field.width + Math.floor(ax / STEP);
      paintPixel(atlas, lens, field, c, f, image.data, (y * width + x) * 4);
    }
  }
  return image;
}

class CanvasRenderer implements Renderer {
  readonly kind = "canvas" as const;
  private context: CanvasRenderingContext2D;
  private atlas: WorldAtlas | null = null;
  private layer = "";
  private tribes = false;
  private tribesLabel = "";
  private image: HTMLCanvasElement = document.createElement("canvas");
  private match: ReadonlySet<number> | null = null;
  private hover = -1;
  private pinned = -1;
  private stale = true;

  constructor(readonly canvas: HTMLCanvasElement) {
    const context = canvas.getContext("2d");
    if (!context) throw new Error("No canvas");
    this.context = context;
  }

  setAtlas(atlas: WorldAtlas): void {
    this.atlas = atlas;
    this.image.width = atlas.width;
    this.image.height = atlas.height;
    this.layer = "";
    this.stale = true;
  }

  setLens(layer: string, tribes: boolean, tribesLabel: string): void {
    if (layer !== this.layer || tribes !== this.tribes) {
      this.layer = layer;
      this.tribes = tribes;
      this.tribesLabel = tribesLabel;
      this.stale = true;
    }
  }

  setFlags(hover: number, pinned: number, match: ReadonlySet<number> | null): void {
    this.hover = hover;
    this.pinned = pinned;
    this.match = match;
    this.stale = true;
  }

  private paint(): void {
    const atlas = this.atlas;
    if (!atlas || !this.layer) return;
    const lens = atlas.lens(this.layer, this.tribes, this.tribesLabel);
    const field = relief(atlas);
    const context = this.image.getContext("2d");
    if (!context) return;
    const pixels = context.createImageData(atlas.width, atlas.height);
    const out = pixels.data;
    const { labels, width } = atlas;
    const { kind, owner } = atlas.data;
    const shown = (c: number): number => (atlas.shown(owner[c], this.tribes) ? owner[c] : -1);
    for (let i = 0; i < labels.length; i++) {
      const c = labels[i];
      const x = i % width;
      const y = (i - x) / width;
      paintPixel(atlas, lens, field, c, Math.floor(y / STEP) * field.width + Math.floor(x / STEP), out, i * 4);
      if (c < 0) continue;
      const right = x < width - 1 ? labels[i + 1] : c;
      const below = i + width < labels.length ? labels[i + width] : c;
      const edge = [right, below].some(
        (k) => k >= 0 && k !== c && kind[k] === LAND && kind[c] === LAND && shown(k) !== shown(c) && (shown(k) >= 0 || shown(c) >= 0),
      );
      let factor = edge ? 0.45 : 1;
      if (this.match && !this.match.has(c) && kind[c] !== SEA) factor *= 0.42;
      if (c === this.hover || c === this.pinned) factor *= 1.25;
      if (factor !== 1) {
        out[i * 4] *= factor;
        out[i * 4 + 1] *= factor;
        out[i * 4 + 2] *= factor;
      }
    }
    context.putImageData(pixels, 0, 0);
    this.stale = false;
  }

  draw(camera: Camera, _overlays: Overlays, _theme: Theme, ratio?: number): void {
    if (this.stale) this.paint();
    const context = this.context;
    const dpr = ratio ?? (window.devicePixelRatio || 1);
    context.setTransform(1, 0, 0, 1, 0, 0);
    context.clearRect(0, 0, this.canvas.width, this.canvas.height);
    context.imageSmoothingEnabled = camera.scale < 1;
    context.setTransform(
      camera.scale * dpr, 0, 0, camera.scale * dpr, -camera.x * camera.scale * dpr,
      -camera.y * camera.scale * dpr,
    );
    context.drawImage(this.image, 0, 0);
  }

  dispose(): void {}
}

/** A renderer for ``canvas``; when WebGL 2 is missing or fails, the canvas is replaced by a
 *  fresh one (a canvas keeps the first kind of context it gave) and drawn without it. */
export function createRenderer(canvas: HTMLCanvasElement, atlas: WorldAtlas): Renderer {
  const gl = canvas.getContext("webgl2", {
    antialias: false,
    premultipliedAlpha: true,
    preserveDrawingBuffer: true,
  });
  if (!gl) return new CanvasRenderer(canvas);
  const size = gl.getParameter(gl.MAX_TEXTURE_SIZE) as number;
  if (atlas.width <= size && atlas.height <= size) {
    try {
      return new GLRenderer(canvas, gl);
    } catch (error) {
      console.warn("WebGL 2 map unavailable, drawing on a canvas", error);
    }
  }
  const fresh = canvas.cloneNode(false) as HTMLCanvasElement;
  canvas.replaceWith(fresh);
  return new CanvasRenderer(fresh);
}

