import { describe, expect, it } from "vitest";
import { WorldAtlas, unroll } from "./atlas";
import type { AtlasBundle } from "./types";

function base64(bytes: Uint8Array): string {
  return Buffer.from(bytes).toString("base64");
}

function runs(pairs: number[]): string {
  return base64(new Uint8Array(new Uint32Array(pairs).buffer));
}

// A 4 x 2 box: two land locations (0, 1) and sea (2), the last pixel outside.
function bundle(): AtlasBundle {
  const layer = {
    colours: base64(new Uint8Array([200, 0, 0, 0, 200, 0, 0, 0, 200])),
    classes: base64(new Uint8Array(new Int32Array([1, 2, 0]).buffer)),
    values: base64(new Uint8Array(new Int32Array([0, 1, 2]).buffer)),
    legend: [["Sea", "#0000c8", 1], ["Aland", "#c80000", 1], ["Beland", "#00c800", 1]] as [string, string, number][],
    ramp: [],
  };
  return {
    id: "w", name: "W", size: [2, 4], scale: 4, cells: 3,
    labels: runs([1, 2, 2, 2, 3, 3, 0, 1]),
    kinds: ["land", "wasteland", "sea", "lake"], keys: ["a", "b", "s"],
    names: ["Alpha", "Beta", ""], kind: [0, 0, 2], area: ["North", "North", ""], region: ["", "", ""],
    owner: [0, -1, -1], culture: [0, 0, -1], religion: [0, 0, -1], material: [0, 1, -1],
    climate: [0, 0, -1], vegetation: [0, 0, -1], topography: [0, 0, -1], settlement: [-1, -1, -1],
    population: [100, 0, 0], complexity: [5, 0, 0], centre: [0, 0, 0, 2, 1, 1],
    vocabulary: { culture: ["Alpine"], religion: ["Faith"], material: ["Gold", "Salt"], climate: ["Cold"], vegetation: ["Woods"], topography: ["Hills"], settlement: [] },
    raw: { material: ["goods_gold", "salt"] }, precious: ["goods_gold"],
    countries: [{ tag: "AAA", name: "Aland", kind: "state", color: "#c80000", capital: 0, culture: 0, religion: 0, locations: 1 }],
    totals: { countries: 1, states: 1, tribes: 0, cultures: 1, religions: 1, locations: 3, land: 2 },
    layers: { countries: layer },
  };
}

describe("atlas", () => {
  it("unrolls runs into the box and refuses a short one", () => {
    expect([...unroll(runs([1, 2, 0, 2]), 2, 2)]).toEqual([0, 0, -1, -1]);
    expect(() => unroll(runs([1, 3]), 2, 2)).toThrow();
  });

  it("knows each location's pixels, box and facts", () => {
    const atlas = new WorldAtlas(bundle());
    expect([...atlas.area]).toEqual([2, 2, 3]);
    expect(atlas.cellAt(1.5, 0.2)).toBe(0);
    expect(atlas.cellAt(3, 1)).toBe(-1);
    expect(atlas.bounds([0, 1])).toEqual([0, 0, 4, 1]);
    const facts = atlas.facts(0);
    expect(facts?.country?.tag).toBe("AAA");
    expect(facts?.precious).toBe(true);
    expect(atlas.facts(1)?.precious).toBe(false);
  });

  it("finds countries, cultures, resources, areas and places by name", () => {
    const atlas = new WorldAtlas(bundle());
    const kinds = atlas.find("a").map((match) => match.kind);
    expect(kinds).toEqual(expect.arrayContaining(["country", "culture", "material", "place"]));
    expect(atlas.find("aaa")[0]).toMatchObject({ kind: "country", cells: [0] });
    expect(atlas.find("north")[0]).toMatchObject({ kind: "area", cells: [0, 1] });
    expect(atlas.find("  ")).toEqual([]);
  });

  it("reads a lens and the cells of a legend entry", () => {
    const atlas = new WorldAtlas(bundle());
    const lens = atlas.lens("countries");
    expect(lens.legend[1].label).toBe("Aland");
    expect(atlas.classCells("countries", 1)).toEqual([0]);
    expect(atlas.labelsFor("countries", "countries")[0].text).toBe("Aland");
  });
});
