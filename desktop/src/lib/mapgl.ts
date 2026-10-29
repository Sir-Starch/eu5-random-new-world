// The map's pixels. With WebGL 2 the box of locations is a texture of location numbers and each
// layer a table of colours, so a lens changes by uploading a few kilobytes; borders, outlines and
// the dimming of what is not selected are worked out per screen pixel, sharp at every zoom.
// Without WebGL 2 a canvas draws the same colours at the atlas's own resolution.

import type { Camera } from "./camera";
import type { WorldAtlas } from "./atlas";

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
  setLens(layer: string): void;
  setFlags(hover: number, pinned: number, match: ReadonlySet<number> | null): void;
  draw(camera: Camera, overlays: Overlays, theme: Theme): void;
  dispose(): void;
}

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
uniform vec2 uSize;
uniform vec2 uOrigin;
uniform float uScale;
uniform vec2 uCanvas;
uniform float uDpr;
uniform int uMatch;
uniform int uLensBorders;
uniform int uPolitical;
uniform int uLocations;
uniform int uCoast;
uniform vec3 uInk;
uniform vec3 uAccent;
out vec4 outColour;

const int TEX_W = ${TEX_W};

int cellAt(vec2 p) {
  ivec2 q = ivec2(floor(p));
  if (q.x < 0 || q.y < 0 || q.x >= int(uSize.x) || q.y >= int(uSize.y)) return -1;
  return texelFetch(uLabels, q, 0).r;
}
ivec2 slot(int c) { return ivec2(c % TEX_W, c / TEX_W); }
ivec4 info(int c) { return c < 0 ? ivec4(-2147483647, -2147483647, 0, 4) : texelFetch(uInfo, slot(c), 0); }
vec3 base(int c) { return texelFetch(uColours, slot(c), 0).rgb; }
bool solid(ivec4 i) { return i.a <= 1; }

float grain(vec2 f) {
  return fract(sin(dot(f, vec2(12.9898, 78.233))) * 43758.5453) - 0.5;
}

void main() {
  vec2 frag = vec2(gl_FragCoord.x, uCanvas.y - gl_FragCoord.y);
  vec2 p = uOrigin + frag / uScale;
  int c = cellAt(p);
  vec3 rgb;
  float alpha = 1.0;
  ivec4 me = info(c);
  if (c < 0) {
    rgb = vec3(0.0);
    alpha = 0.0;
  } else {
    rgb = base(c);
    if (uScale < 0.95) {
      float s = 0.25 / uScale;
      vec3 acc = rgb;
      float n = 1.0;
      for (int i = 0; i < 4; i++) {
        vec2 o = vec2((i & 1) == 0 ? -s : s, (i & 2) == 0 ? -s : s);
        int k = cellAt(p + o);
        if (k >= 0) { acc += base(k); n += 1.0; }
      }
      rgb = acc / n;
    }
    if (uMatch == 1 && (me.b & ${MATCH}) == 0 && me.a != 2) {
      float g = dot(rgb, vec3(0.299, 0.587, 0.114));
      rgb = mix(rgb, vec3(g), 0.7) * 0.42;
    }
    if (me.a <= 1) rgb *= 1.0 + 0.035 * grain(floor(gl_FragCoord.xy));
  }

  float one = uDpr / uScale;
  float lens = 0.0, political = 0.0, location = 0.0, coast = 0.0;
  float match = 0.0, hover = 0.0, pinned = 0.0;
  for (int ring = 1; ring <= 3; ring++) {
    float d = one * (ring == 1 ? 1.0 : ring == 2 ? 2.0 : 3.0);
    for (int i = 0; i < 4; i++) {
      vec2 o = i == 0 ? vec2(d, 0.0) : i == 1 ? vec2(-d, 0.0) : i == 2 ? vec2(0.0, d) : vec2(0.0, -d);
      int k = cellAt(p + o);
      if (k == c) continue;
      ivec4 other = info(k);
      bool bothLand = me.a == 0 && other.a == 0;
      if (ring == 1) {
        if (bothLand && other.r != me.r) lens = 1.0;
        if (bothLand) location = 1.0;
        if (solid(me) != solid(other) && c >= 0) coast = 1.0;
        if (((me.b ^ other.b) & ${HOVER}) != 0) hover = 1.0;
      }
      if (ring <= 2) {
        if (bothLand && other.g != me.g) political = max(political, ring == 1 ? 1.0 : 0.55);
        if (((me.b ^ other.b) & ${MATCH}) != 0 && (me.b & ${MATCH}) != 0) match = 1.0;
      }
      if (((me.b ^ other.b) & ${PINNED}) != 0) pinned = max(pinned, ring == 3 ? 0.5 : 1.0);
    }
  }
  if (c >= 0) {
    if (uLocations == 1 && uScale > 2.2 * uDpr) rgb = mix(rgb, uInk, 0.16 * location);
    if (uLensBorders == 1) rgb = mix(rgb, uInk, 0.55 * lens);
    if (uPolitical == 1) rgb = mix(rgb, uInk, 0.85 * political);
    if (uCoast == 1) rgb = mix(rgb, vec3(1.0), 0.16 * coast);
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

class GLRenderer implements Renderer {
  readonly kind = "webgl2" as const;
  private gl: WebGL2RenderingContext;
  private program: WebGLProgram;
  private labels: WebGLTexture | null = null;
  private colours: WebGLTexture | null = null;
  private info: WebGLTexture | null = null;
  private atlas: WorldAtlas | null = null;
  private layer = "";
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

  private texture(): WebGLTexture {
    const gl = this.gl;
    const texture = gl.createTexture();
    if (!texture) throw new Error("No texture");
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return texture;
  }

  setAtlas(atlas: WorldAtlas): void {
    const gl = this.gl;
    this.atlas = atlas;
    this.layer = "";
    this.rows = Math.max(1, Math.ceil(atlas.cells / TEX_W));
    this.flags = new Int32Array(atlas.cells);
    this.infoData = new Int32Array(TEX_W * this.rows * 4);
    for (const texture of [this.labels, this.colours, this.info]) gl.deleteTexture(texture);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    this.labels = this.texture();
    gl.texImage2D(
      gl.TEXTURE_2D, 0, gl.R32I, atlas.width, atlas.height, 0, gl.RED_INTEGER, gl.INT, atlas.labels,
    );
    this.colours = this.texture();
    this.info = this.texture();
  }

  setLens(layer: string): void {
    const atlas = this.atlas;
    if (!atlas || layer === this.layer) return;
    this.layer = layer;
    const gl = this.gl;
    const lens = atlas.lens(layer);
    const rgba = new Uint8Array(TEX_W * this.rows * 4);
    for (let c = 0; c < atlas.cells; c++) {
      rgba[c * 4] = lens.colours[c * 3];
      rgba[c * 4 + 1] = lens.colours[c * 3 + 1];
      rgba[c * 4 + 2] = lens.colours[c * 3 + 2];
      rgba[c * 4 + 3] = 255;
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
    if (!atlas || !this.layer) return;
    const lens = atlas.lens(this.layer);
    const data = this.infoData;
    const { owner, kind } = atlas.data;
    for (let c = 0; c < atlas.cells; c++) {
      data[c * 4] = lens.values[c];
      data[c * 4 + 1] = owner[c];
      data[c * 4 + 2] = this.flags[c];
      data[c * 4 + 3] = kind[c];
    }
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, this.info);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA32I, TEX_W, this.rows, 0, gl.RGBA_INTEGER, gl.INT, data);
  }

  draw(camera: Camera, overlays: Overlays, theme: Theme): void {
    const gl = this.gl;
    const atlas = this.atlas;
    const dpr = window.devicePixelRatio || 1;
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    if (!atlas || !this.layer) return;
    gl.useProgram(this.program);
    const bind = (unit: number, texture: WebGLTexture | null, name: string): void => {
      gl.activeTexture(gl.TEXTURE0 + unit);
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.uniform1i(this.uniform(name), unit);
    };
    bind(0, this.labels, "uLabels");
    bind(1, this.colours, "uColours");
    bind(2, this.info, "uInfo");
    gl.uniform2f(this.uniform("uSize"), atlas.width, atlas.height);
    gl.uniform2f(this.uniform("uOrigin"), camera.x, camera.y);
    gl.uniform1f(this.uniform("uScale"), camera.scale * dpr);
    gl.uniform2f(this.uniform("uCanvas"), this.canvas.width, this.canvas.height);
    gl.uniform1f(this.uniform("uDpr"), dpr);
    gl.uniform1i(this.uniform("uMatch"), this.matching ? 1 : 0);
    gl.uniform1i(this.uniform("uLensBorders"), overlays.lensBorders ? 1 : 0);
    gl.uniform1i(this.uniform("uPolitical"), overlays.political ? 1 : 0);
    gl.uniform1i(this.uniform("uLocations"), overlays.locations ? 1 : 0);
    gl.uniform1i(this.uniform("uCoast"), overlays.coast ? 1 : 0);
    gl.uniform3f(this.uniform("uInk"), ...theme.ink.map((v) => v / 255) as [number, number, number]);
    gl.uniform3f(
      this.uniform("uAccent"),
      ...(theme.accent.map((v) => v / 255) as [number, number, number]),
    );
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }

  dispose(): void {
    const gl = this.gl;
    for (const texture of [this.labels, this.colours, this.info]) gl.deleteTexture(texture);
    gl.deleteProgram(this.program);
  }
}

class CanvasRenderer implements Renderer {
  readonly kind = "canvas" as const;
  private context: CanvasRenderingContext2D;
  private atlas: WorldAtlas | null = null;
  private layer = "";
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

  setLens(layer: string): void {
    if (layer !== this.layer) {
      this.layer = layer;
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
    const lens = atlas.lens(this.layer);
    const context = this.image.getContext("2d");
    if (!context) return;
    const pixels = context.createImageData(atlas.width, atlas.height);
    const out = pixels.data;
    const { labels, width } = atlas;
    const kind = atlas.data.kind;
    for (let i = 0; i < labels.length; i++) {
      const c = labels[i];
      if (c < 0) continue;
      let r = lens.colours[c * 3];
      let g = lens.colours[c * 3 + 1];
      let b = lens.colours[c * 3 + 2];
      const right = i % width < width - 1 ? labels[i + 1] : c;
      const below = i + width < labels.length ? labels[i + width] : c;
      const edge =
        (right >= 0 && right !== c && lens.values[right] !== lens.values[c] && kind[right] === 0) ||
        (below >= 0 && below !== c && lens.values[below] !== lens.values[c] && kind[below] === 0);
      if (this.match && !this.match.has(c) && kind[c] !== 2) {
        const grey = 0.299 * r + 0.587 * g + 0.114 * b;
        r = (r * 0.3 + grey * 0.7) * 0.42;
        g = (g * 0.3 + grey * 0.7) * 0.42;
        b = (b * 0.3 + grey * 0.7) * 0.42;
      }
      if (edge && kind[c] === 0) {
        r *= 0.45;
        g *= 0.45;
        b *= 0.45;
      }
      if (c === this.hover || c === this.pinned) {
        r = r * 0.7 + 255 * 0.3;
        g = g * 0.7 + 255 * 0.3;
        b = b * 0.7 + 255 * 0.3;
      }
      out[i * 4] = r;
      out[i * 4 + 1] = g;
      out[i * 4 + 2] = b;
      out[i * 4 + 3] = 255;
    }
    context.putImageData(pixels, 0, 0);
    this.stale = false;
  }

  draw(camera: Camera): void {
    if (this.stale) this.paint();
    const context = this.context;
    const dpr = window.devicePixelRatio || 1;
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
