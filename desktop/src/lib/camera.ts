// Where the map viewer looks: the atlas pixel at the view's top-left corner and how many CSS
// pixels one atlas pixel covers. Pure arithmetic, so it is tested without a canvas.

export interface Camera {
  x: number;
  y: number;
  scale: number;
}

export interface View {
  width: number;
  height: number;
}

export const MIN_SCALE = 0.05;
export const MAX_SCALE = 16;

/** The camera that shows the whole box (or ``box``: left, top, right, bottom) with a margin. */
export function fit(
  view: View,
  width: number,
  height: number,
  box: [number, number, number, number] = [0, 0, width, height],
  margin = 24,
  limit = MAX_SCALE,
): Camera {
  const [left, top, right, bottom] = box;
  const w = Math.max(1, right - left);
  const h = Math.max(1, bottom - top);
  const scale = clampScale(
    Math.min((view.width - 2 * margin) / w, (view.height - 2 * margin) / h),
    limit,
  );
  return {
    x: left + w / 2 - view.width / 2 / scale,
    y: top + h / 2 - view.height / 2 / scale,
    scale,
  };
}

export function clampScale(scale: number, limit = MAX_SCALE): number {
  return Math.min(limit, Math.max(MIN_SCALE, scale));
}

/** Zoom by ``factor`` keeping the atlas point under the screen point (sx, sy) in place. */
export function zoomAt(camera: Camera, factor: number, sx: number, sy: number): Camera {
  const scale = clampScale(camera.scale * factor);
  const ax = camera.x + sx / camera.scale;
  const ay = camera.y + sy / camera.scale;
  return { x: ax - sx / scale, y: ay - sy / scale, scale };
}

export function toAtlas(camera: Camera, sx: number, sy: number): [number, number] {
  return [camera.x + sx / camera.scale, camera.y + sy / camera.scale];
}

export function toScreen(camera: Camera, ax: number, ay: number): [number, number] {
  return [(ax - camera.x) * camera.scale, (ay - camera.y) * camera.scale];
}

/** Keep at least a quarter of the view on the box, so the map cannot be lost off screen. */
export function clamp(camera: Camera, view: View, width: number, height: number): Camera {
  const vw = view.width / camera.scale;
  const vh = view.height / camera.scale;
  const minX = -vw * 0.75;
  const maxX = width - vw * 0.25;
  const minY = -vh * 0.75;
  const maxY = height - vh * 0.25;
  return {
    scale: camera.scale,
    x: Math.min(maxX, Math.max(minX, camera.x)),
    y: Math.min(maxY, Math.max(minY, camera.y)),
  };
}

/** A step of an animation from ``a`` to ``b`` at ``t`` of 0..1, zooming geometrically. */
export function between(a: Camera, b: Camera, t: number, view: View): Camera {
  const e = t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
  const scale = a.scale * (b.scale / a.scale) ** e;
  // Interpolate the view's centre, not its corner, so the zoom does not drift.
  const ca = [a.x + view.width / 2 / a.scale, a.y + view.height / 2 / a.scale];
  const cb = [b.x + view.width / 2 / b.scale, b.y + view.height / 2 / b.scale];
  const cx = ca[0] + (cb[0] - ca[0]) * e;
  const cy = ca[1] + (cb[1] - ca[1]) * e;
  return { x: cx - view.width / 2 / scale, y: cy - view.height / 2 / scale, scale };
}
