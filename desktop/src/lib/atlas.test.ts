import { describe, expect, it } from "vitest";
import { WorldAtlas, developmentText, unroll } from "./atlas";
import { bundle, runs } from "./atlasFixture";
import { prepareAtlas } from "./atlasPreparation";
import { relief, rememberRelief } from "./relief";

describe("atlas", () => {
  it("prepares identical physical fields and region names away from the renderer", () => {
    const data = bundle();
    const expected = new WorldAtlas(data);
    const prepared = prepareAtlas(data);
    expect(prepared.field).toEqual(relief(expected));
    expect(prepared.labels).toEqual(expected.labelsFor("land", "regions"));
    const restored = new WorldAtlas(data, prepared.labels);
    rememberRelief(restored, prepared.field);
    expect(relief(restored)).toBe(prepared.field);
    expect(restored.labelsFor("land", "regions", false)).toBe(prepared.labels);
  });
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
    expect(facts?.rule).toBe("");
    const ruled = new WorldAtlas({ ...bundle(), region: ["Ziageilra", "Ziageilra", ""], rule: ["Alaska", "Alaska", ""] });
    expect(ruled.facts(1)).toMatchObject({ region: "Ziageilra", rule: "Alaska" });
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

describe("development", () => {
  it("is written as the decimal the game shows", () => {
    expect(developmentText(12500)).toBe("12.5");
    expect(developmentText(7250)).toBe("7.25");
    expect(developmentText(3000)).toBe("3");
    expect(developmentText(0)).toBe("0");
  });
});
