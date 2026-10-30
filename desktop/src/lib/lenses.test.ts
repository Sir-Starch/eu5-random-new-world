import { describe, expect, it } from "vitest";
import { WorldAtlas } from "./atlas";
import { colourClasses, PROFILES } from "./lenses";
import { blur, distance, poles, relief } from "./relief";
import type { AtlasBundle } from "./types";

function base64(bytes: Uint8Array): string {
  return Buffer.from(bytes).toString("base64");
}

// A 6 x 2 box: a state (cell 0, two columns), a tribe (cell 1, two columns), unclaimed land
// (cell 2) and sea (cell 3).
//   0 0 1 1 2 3
//   0 0 1 1 2 3
function bundle(): AtlasBundle {
  const labels = [1, 1, 2, 2, 3, 4, 1, 1, 2, 2, 3, 4];
  const runs: number[] = [];
  for (const value of labels) runs.push(value, 1);
  const layer = {
    colours: base64(new Uint8Array([200, 0, 0, 0, 200, 0, 92, 96, 84, 30, 58, 110])),
    classes: base64(new Uint8Array(new Int32Array([1, 2, 3, 0]).buffer)),
    values: base64(new Uint8Array(new Int32Array([0, 1, -1, -1]).buffer)),
    legend: [
      ["Sea", "#1e3a6e", 1],
      ["Aland", "#c80000", 1],
      ["Tribeland", "#00c800", 1],
      ["No country", "#5c6054", 1],
    ] as [string, string, number][],
    ramp: [],
  };
  return {
    id: "w", name: "W", size: [2, 6], scale: 4, cells: 4,
    labels: base64(new Uint8Array(new Uint32Array(runs).buffer)),
    kinds: ["land", "wasteland", "sea", "lake"], keys: ["a", "b", "c", "s"],
    names: ["Alpha", "Beta", "Gamma", "Sound"], kind: [0, 0, 0, 2],
    area: ["North", "North", "North", ""], region: ["Plains", "Plains", "Plains", ""],
    owner: [0, 1, -1, -1], culture: [0, 0, 0, -1], religion: [0, 0, 0, -1], material: [0, 1, 1, -1],
    climate: [0, 0, 0, -1], vegetation: [0, 0, 0, -1], topography: [0, 1, 0, -1], settlement: [0, -1, -1, -1],
    population: [100, 10, 0, 0], complexity: [5, 1, 0, 0], centre: [0, 1, 0, 3, 0, 4, 0, 5],
    vocabulary: { culture: ["Alpine"], religion: ["Faith"], material: ["Gold", "Fish"], climate: ["Tropical"], vegetation: ["Woods"], topography: ["Flatland", "Mountains"], settlement: ["City"] },
    raw: { material: ["goods_gold", "fish"], climate: ["tropical"], vegetation: ["woods"], topography: ["flatland", "mountains"], settlement: ["city"] },
    precious: ["goods_gold"],
    countries: [
      { tag: "AAA", name: "Aland", kind: "state", color: "#c80000", capital: 0, culture: 0, religion: 0, locations: 1 },
      { tag: "BBB", name: "Tribeland", kind: "tribe", color: "#00c800", capital: 1, culture: 0, religion: 0, locations: 1 },
    ],
    totals: { countries: 2, states: 1, tribes: 1, cultures: 1, religions: 1, locations: 4, land: 3 },
    layers: { countries: layer },
  };
}

describe("relief", () => {
  it("measures distance and blurs without losing a level field", () => {
    const seed = new Uint8Array([1, 0, 0, 0, 0]);
    expect([...distance(seed, 5, 1)]).toEqual([0, 1, 2, 3, 4]);
    const level = blur(new Float32Array(20).fill(3), 5, 4, 1);
    expect([...level].every((value) => Math.abs(value - 3) < 1e-6)).toBe(true);
    const spike = new Float32Array(25);
    spike[12] = 1;
    const spread = blur(spike, 5, 5, 1);
    expect(spike[12]).toBe(1);
    expect(spread[12]).toBeLessThan(1);
  });

  it("names each class inside itself and draws land, water and shade", () => {
    const atlas = new WorldAtlas(bundle());
    const found = poles(atlas, (c) => (c < 2 ? c : -1), 2);
    for (const [k, pole] of found.entries()) {
      expect(atlas.cellAt(pole.x, pole.y)).toBe(k);
      expect(pole.area).toBe(4);
    }
    const field = relief(atlas);
    expect(field.width).toBe(3);
    expect(field.land[3]).toBeGreaterThan(0);
    expect(field.depth[2]).toBe(1);
  });
});

describe("lenses", () => {
  it("has a look for every lens", () => {
    for (const layer of ["land", "countries", "cultures", "religions", "resources", "development", "population", "climate", "terrain", "areas"]) {
      expect(PROFILES[layer]).toBeDefined();
    }
    expect(PROFILES.land.physical).toBe(true);
    expect(PROFILES.resources.names).toBe("none");
  });

  it("gives neighbours different colours", () => {
    const path = [new Set([1]), new Set([0, 2]), new Set([1, 3]), new Set([2])];
    const colours = colourClasses(path, [4, 3, 2, 1]);
    for (const [k, near] of path.entries()) for (const n of near) expect(colours[n]).not.toBe(colours[k]);
    const star = Array.from({ length: 21 }, (_, k) => new Set(k === 0 ? Array.from({ length: 20 }, (_, n) => n + 1) : [0]));
    const coloured = colourClasses(star, star.map((_, k) => 21 - k));
    expect(coloured.slice(1)).not.toContain(coloured[0]);
  });

  it("leaves tribes uncoloured under one entry, as the game's political map does", () => {
    const atlas = new WorldAtlas(bundle());
    const states = atlas.lens("countries", false, "Tribes");
    expect(states.opacity[0]).toBeGreaterThan(0);
    expect(states.opacity[1]).toBe(0);
    expect(states.legend[states.classes[1]].label).toBe("Tribes");
    expect(states.legend[states.classes[0]].label).toBe("Aland");
    expect(states.legend.map((entry) => entry.label)).not.toContain("Tribeland");
    expect(atlas.labelsFor("countries", "countries", false).map((label) => label.text)).toEqual(["Aland"]);
    expect(atlas.capitals(false).map((capital) => capital.country.tag)).toEqual(["AAA"]);
    const all = atlas.lens("countries", true, "Tribes");
    expect(all.opacity[1]).toBeGreaterThan(0);
    expect(all.legend[all.classes[1]].label).toBe("Tribeland");
    expect(atlas.settlements().map((place) => place.name)).toEqual(["Alpha"]);
  });
});
