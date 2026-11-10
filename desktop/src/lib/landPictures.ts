// The land editor's pictures as the page reads and writes them: PNG data URLs to and from the
// kinds of a sheet, and small coloured thumbnails of a drawing.

import { BACK, SHOWN, kindsFromRgba, rgbaFromKinds } from "./landEditor";

function canvasOf(width: number, height: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) throw new Error("The page cannot draw");
  return [canvas, context];
}

async function decode(url: string): Promise<ImageData> {
  const image = new Image();
  image.src = url;
  await image.decode();
  const [, context] = canvasOf(image.naturalWidth, image.naturalHeight);
  context.drawImage(image, 0, 0);
  return context.getImageData(0, 0, image.naturalWidth, image.naturalHeight);
}

/** The kinds of a picture the generator drew, in its palette's colours. */
export async function kindsOfUrl(url: string, palette: readonly (readonly number[])[]): Promise<Uint8Array> {
  const data = await decode(url);
  return kindsFromRgba(data.data, palette);
}

/** The red channel of a grey picture: the area's classes, or the coast margin. */
export async function greysOfUrl(url: string): Promise<Uint8Array> {
  const data = await decode(url);
  const greys = new Uint8Array(data.width * data.height);
  for (let i = 0; i < greys.length; i++) greys[i] = data.data[i * 4]!;
  return greys;
}

/** A drawing as the PNG data URL the generator reads (its palette's colours, opaque). */
export function urlOfKinds(kinds: Uint8Array, width: number, height: number, palette: readonly (readonly number[])[]): string {
  const [canvas, context] = canvasOf(width, height);
  const rgba = rgbaFromKinds(kinds, palette);
  context.putImageData(new ImageData(rgba, width, height), 0, 0);
  return canvas.toDataURL("image/png");
}

/** A small picture of a drawing on the area's sea, every ``every``th pixel, for a gallery. */
export function thumbnail(kinds: Uint8Array, width: number, height: number, every: number, area: Uint8Array | null): string {
  const w = Math.ceil(width / every);
  const h = Math.ceil(height / every);
  const [canvas, context] = canvasOf(w, h);
  const out = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const at = y * every * width + x * every;
      const shown = SHOWN[kinds[at]!]!;
      const outside = area !== null && area[at] === 0;
      const base = outside ? BACK.outside : BACK.area;
      const alpha = shown[3] / 255;
      const o = (y * w + x) * 4;
      out[o] = Math.round(base[0] * (1 - alpha) + shown[0] * alpha);
      out[o + 1] = Math.round(base[1] * (1 - alpha) + shown[1] * alpha);
      out[o + 2] = Math.round(base[2] * (1 - alpha) + shown[2] * alpha);
      out[o + 3] = 255;
    }
  }
  context.putImageData(new ImageData(out, w, h), 0, 0);
  return canvas.toDataURL("image/png");
}
