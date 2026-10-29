import { describe, expect, it } from "vitest";
import { MAX_SCALE, between, clamp, fit, toAtlas, toScreen, zoomAt } from "./camera";

const view = { width: 800, height: 600 };

describe("camera", () => {
  it("fits the box with its margin, centred", () => {
    const camera = fit(view, 400, 200);
    expect(camera.scale).toBeCloseTo((800 - 48) / 400);
    const [cx, cy] = toAtlas(camera, 400, 300);
    expect(cx).toBeCloseTo(200);
    expect(cy).toBeCloseTo(100);
  });

  it("keeps the point under the cursor while zooming", () => {
    const camera = fit(view, 400, 200);
    const before = toAtlas(camera, 123, 456);
    const after = toAtlas(zoomAt(camera, 2.5, 123, 456), 123, 456);
    expect(after[0]).toBeCloseTo(before[0]);
    expect(after[1]).toBeCloseTo(before[1]);
    expect(zoomAt(camera, 1e9, 0, 0).scale).toBe(MAX_SCALE);
  });

  it("converts both ways and keeps the map on screen", () => {
    const camera = { x: 10, y: 20, scale: 3 };
    const [sx, sy] = toScreen(camera, 50, 60);
    expect(toAtlas(camera, sx, sy)).toEqual([50, 60]);
    const lost = clamp({ x: 10_000, y: -10_000, scale: 1 }, view, 400, 200);
    expect(lost.x).toBeLessThanOrEqual(400);
    expect(lost.y).toBeGreaterThanOrEqual(-600);
  });

  it("animates from one camera to the other", () => {
    const a = { x: 0, y: 0, scale: 1 };
    const b = { x: 100, y: 50, scale: 4 };
    expect(between(a, b, 0, view)).toEqual(a);
    const end = between(a, b, 1, view);
    expect(end.scale).toBeCloseTo(4);
    expect(end.x).toBeCloseTo(100);
  });
});
