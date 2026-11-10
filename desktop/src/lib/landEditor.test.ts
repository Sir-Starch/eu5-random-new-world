import { describe, expect, it } from "vitest";
import {
  BACK,
  DEFAULT_RULE,
  HIGHLANDS,
  LAKE,
  LAND,
  MAX_UNDO,
  MOUNTAINS,
  SEA,
  Sheet,
  backdropRgba,
  clampZoom,
  fitCamera,
  kindsFromRgba,
  refused,
  rgbaFromKinds,
  sayReport,
  toSheet,
  zoomAt,
  type Report,
} from "./landEditor";

function sheet(width = 40, height = 30): Sheet {
  return new Sheet(width, height);
}

function draw(s: Sheet, work: () => void): void {
  s.begin();
  work();
  s.commit();
}

function count(s: Sheet, kind: number): number {
  return s.counts()[kind]!;
}

describe("brush", () => {
  it("dabs a round spot of the size it is given", () => {
    const s = sheet();
    s.stamp(20, 15, 1, LAND);
    expect(count(s, LAND)).toBe(1);
    s.stamp(10, 10, 5, LAND);
    expect(count(s, LAND)).toBe(1 + 21);
    expect(s.get(10, 8)).toBe(LAND);
    expect(s.get(8, 8)).toBe(SEA);
  });

  it("leaves no gap along a stroke, however fast the pointer moved", () => {
    const s = sheet(100, 30);
    s.stroke(2, 5, 90, 20, 3, LAND);
    for (let x = 2; x <= 90; x++) {
      const y = Math.round(5 + ((20 - 5) * (x - 2)) / (90 - 2));
      expect([s.get(x, y), s.get(x, y - 1), s.get(x, y + 1)]).toContain(LAND);
    }
    expect(s.get(90, 20)).toBe(LAND);
  });

  it("paints terrain on ground only, and a lake or land anywhere", () => {
    const s = sheet();
    draw(s, () => s.rectangle(5, 5, 14, 14, 1, LAND));
    draw(s, () => s.stamp(4, 10, 9, MOUNTAINS));
    expect(s.get(8, 10)).toBe(MOUNTAINS);
    expect(s.get(1, 10)).toBe(SEA);
    draw(s, () => s.stamp(12, 8, 3, LAKE));
    expect(s.get(12, 8)).toBe(LAKE);
    draw(s, () => s.stamp(12, 8, 3, HIGHLANDS));
    expect(s.get(12, 8)).toBe(LAKE);
    draw(s, () => s.stamp(12, 8, 3, HIGHLANDS, { ...DEFAULT_RULE, terrainOnGround: false }));
    expect(s.get(12, 8)).toBe(HIGHLANDS);
  });

  it("clips at the edge of the sheet", () => {
    const s = sheet(10, 10);
    s.stamp(0, 0, 9, LAND);
    s.stamp(9, 9, 9, LAND);
    expect(s.get(0, 0)).toBe(LAND);
    expect(s.get(9, 9)).toBe(LAND);
    expect(s.get(-3, 4)).toBe(SEA);
  });
});

describe("shapes", () => {
  it("fills a rectangle between any two corners, and outlines it as thick as the brush", () => {
    const s = sheet();
    s.rectangle(12, 9, 5, 4, 1, LAND);
    expect(count(s, LAND)).toBe(8 * 6);
    const o = sheet();
    o.rectangle(5, 4, 12, 9, 2, LAND, { ...DEFAULT_RULE, filled: false });
    expect(o.get(5, 4)).toBe(LAND);
    expect(o.get(8, 4)).toBe(LAND);
    expect(o.get(8, 7)).toBe(SEA);
  });

  it("fills an ellipse inside its box and leaves its corners out", () => {
    const s = sheet();
    s.ellipse(5, 5, 24, 18, 1, LAND);
    expect(s.get(15, 11)).toBe(LAND);
    expect(s.get(5, 5)).toBe(SEA);
    expect(s.get(24, 18)).toBe(SEA);
    const o = sheet();
    o.ellipse(5, 5, 24, 18, 2, LAND, { ...DEFAULT_RULE, filled: false });
    expect(o.get(15, 11)).toBe(SEA);
    expect(o.get(5, 11)).toBe(LAND);
    expect(count(o, LAND)).toBeLessThan(count(s, LAND));
  });

  it("previews a shape from where it began: restore draws it afresh", () => {
    const s = sheet();
    s.begin();
    s.rectangle(2, 2, 10, 10, 1, LAND);
    s.restore();
    expect(count(s, LAND)).toBe(0);
    s.rectangle(2, 2, 4, 4, 1, LAND);
    expect(s.commit()).toBe(true);
    expect(count(s, LAND)).toBe(9);
    s.begin();
    s.rectangle(2, 2, 10, 10, 1, LAND);
    s.cancel();
    expect(count(s, LAND)).toBe(9);
    expect(s.drawing).toBe(false);
  });
});

describe("fill", () => {
  it("floods the stretch it is in and stops at other kinds, also round bends", () => {
    const s = sheet(20, 12);
    draw(s, () => {
      s.rectangle(0, 5, 14, 5, 1, LAND); // a wall with a gap at the right
    });
    draw(s, () => s.fill(3, 2, LAKE));
    expect(s.get(3, 2)).toBe(LAKE);
    expect(s.get(19, 11)).toBe(LAKE); // round the end of the wall
    expect(s.get(3, 5)).toBe(LAND);
    expect(count(s, LAKE)).toBe(20 * 12 - 15);
    expect(s.fill(3, 2, LAKE)).toBe(0);
  });

  it("leaves what is not ground alone when it is asked for terrain on ground", () => {
    const s = sheet();
    expect(s.fill(1, 1, MOUNTAINS)).toBe(0);
    expect(s.fill(1, 1, MOUNTAINS, { ...DEFAULT_RULE, terrainOnGround: false })).toBe(40 * 30);
  });

  it("does not overflow on a large sheet and reports the dirty box", () => {
    const s = sheet(800, 600);
    expect(s.fill(1, 1, LAND)).toBe(800 * 600);
    expect(s.takeDirty()).toEqual({ x0: 0, y0: 0, x1: 799, y1: 599 });
    expect(s.takeDirty()).toBeNull();
  });
});

describe("undo", () => {
  it("takes back a stroke and brings it again", () => {
    const s = sheet();
    draw(s, () => s.stamp(10, 10, 7, LAND));
    draw(s, () => s.stamp(10, 10, 3, MOUNTAINS));
    const mountains = count(s, MOUNTAINS);
    expect(s.undo()).toBe(true);
    expect(count(s, MOUNTAINS)).toBe(0);
    expect(s.undo()).toBe(true);
    expect(count(s, LAND)).toBe(0);
    expect(s.undo()).toBe(false);
    expect(s.canRedo).toBe(true);
    expect(s.redo()).toBe(true);
    expect(s.redo()).toBe(true);
    expect(count(s, MOUNTAINS)).toBe(mountains);
    expect(s.redo()).toBe(false);
  });

  it("forgets what can be brought again when something new is drawn", () => {
    const s = sheet();
    draw(s, () => s.stamp(10, 10, 5, LAND));
    s.undo();
    draw(s, () => s.stamp(20, 10, 5, LAND));
    expect(s.canRedo).toBe(false);
  });

  it("does not keep a change that changed nothing", () => {
    const s = sheet();
    s.begin();
    s.stamp(5, 5, 3, SEA);
    expect(s.commit()).toBe(false);
    expect(s.canUndo).toBe(false);
  });

  it("keeps only the latest changes", () => {
    const s = sheet(200, 10);
    for (let i = 0; i < MAX_UNDO + 20; i++) draw(s, () => s.stamp(i, 5, 1, LAND));
    let undone = 0;
    while (s.undo()) undone++;
    expect(undone).toBe(MAX_UNDO);
    expect(count(s, LAND)).toBe(20);
  });

  it("replaces the whole picture as one change", () => {
    const s = sheet(10, 10);
    draw(s, () => s.stamp(5, 5, 3, LAND));
    const next = new Uint8Array(100).fill(LAND);
    expect(s.replace(next)).toBe(true);
    expect(count(s, LAND)).toBe(100);
    expect(s.replace(next)).toBe(false);
    s.undo();
    expect(count(s, LAND)).toBe(9);
    expect(s.clear()).toBe(true);
    expect(count(s, LAND)).toBe(0);
    expect(() => s.replace(new Uint8Array(3))).toThrow();
  });
});

describe("pictures", () => {
  const palette = [
    [0, 0, 0],
    [255, 255, 255],
    [160, 82, 45],
    [218, 165, 32],
    [124, 205, 124],
    [30, 144, 255],
  ];

  it("turns kinds into the generator's colours and back", () => {
    const kinds = new Uint8Array([0, 1, 2, 3, 4, 5, 1, 0]);
    const rgba = rgbaFromKinds(kinds, palette);
    expect(Array.from(rgba.slice(8, 12))).toEqual([160, 82, 45, 255]);
    expect(Array.from(kindsFromRgba(rgba, palette))).toEqual(Array.from(kinds));
  });

  it("reads a colour that is a little off as the nearest kind", () => {
    const rgba = new Uint8ClampedArray([250, 252, 255, 255, 10, 4, 2, 255, 150, 90, 50, 255]);
    expect(Array.from(kindsFromRgba(rgba, palette))).toEqual([LAND, SEA, MOUNTAINS]);
  });

  it("draws the area, the Americas, the island groups and the coast margin", () => {
    const classes = { outside: 20, area: 90, islands: 62, americas: 118 };
    const greys = new Uint8Array([20, 90, 118, 62]);
    const margin = new Uint8Array([0, 255, 0, 0]);
    const plain = backdropRgba(greys, margin, classes, { showAmericas: true, showIslands: true, showMargin: false }, 4);
    expect(Array.from(plain.slice(0, 3))).toEqual([...BACK.outside]);
    expect(Array.from(plain.slice(4, 7))).toEqual([...BACK.area]);
    expect(Array.from(plain.slice(8, 11))).toEqual([...BACK.americas]);
    expect(Array.from(plain.slice(12, 15))).toEqual([...BACK.islands]);
    const hidden = backdropRgba(greys, margin, classes, { showAmericas: false, showIslands: false, showMargin: false }, 4);
    expect(Array.from(hidden.slice(8, 11))).toEqual([...BACK.area]);
    expect(Array.from(hidden.slice(12, 15))).toEqual([...BACK.area]);
    const hatched = backdropRgba(greys, margin, classes, { showAmericas: true, showIslands: true, showMargin: true }, 4);
    expect(Array.from(hatched.slice(4, 7))).not.toEqual([...BACK.area]);
  });
});

describe("the camera", () => {
  const box = { width: 800, height: 600 };

  it("fits the sheet in the box and centres it", () => {
    const camera = fitCamera(box, 400, 500);
    expect(camera.scale).toBeCloseTo((600 - 48) / 500);
    expect(camera.x).toBeCloseTo((800 - 400 * camera.scale) / 2);
  });

  it("keeps the pixel under the pointer while zooming, within the limits", () => {
    const camera = fitCamera(box, 400, 500);
    const before = toSheet(camera, 300, 200);
    const after = toSheet(zoomAt(camera, 3, 300, 200), 300, 200);
    expect(after[0]).toBeCloseTo(before[0]);
    expect(after[1]).toBeCloseTo(before[1]);
    expect(zoomAt(camera, 1e9, 0, 0).scale).toBe(clampZoom(1e9));
    expect(zoomAt(camera, 1e-9, 0, 0).scale).toBe(clampZoom(1e-9));
  });
});

describe("what the generator says", () => {
  const report: Report = {
    land: 213,
    mountains: 0,
    highlands: 0,
    lowlands: 0,
    lakes: 0,
    outside: 0,
    kept: 100,
    specks: 0,
    open_lakes: [],
    islands: 0,
    low: 30,
    high: 900,
    refusal: "",
  };

  it("is satisfied with a plain land", () => {
    expect(sayReport(report)).toEqual([{ level: "ok", key: "editor.check.land", values: { share: "21.3" } }]);
    expect(refused(report)).toBe(false);
    expect(refused(null)).toBe(true);
  });

  it("warns of what will be dropped or moved, the worst first, and refuses what cannot be made", () => {
    const warned = sayReport({ ...report, kept: 80, specks: 2, islands: 1 });
    expect(warned.map((line) => line.key)).toEqual([
      "editor.check.dropped",
      "editor.check.specks",
      "editor.check.islands",
      "editor.check.land",
    ]);
    expect(warned[0]!.values).toEqual({ dropped: 20 });
    const lake = { ...report, refusal: "lake_open" as const, open_lakes: [[3, 4] as [number, number]] };
    expect(sayReport(lake)[0]).toEqual({ level: "error", key: "editor.check.lake_open", values: { count: 1 } });
    expect(refused(lake)).toBe(true);
    expect(sayReport({ ...report, refusal: "share" })[0]!.level).toBe("error");
    expect(sayReport({ ...report, refusal: "outside", kept: 20 })[0]!.key).toBe("editor.check.outside_all");
  });
});
