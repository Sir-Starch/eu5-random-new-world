import { describe, expect, it } from "vitest";
import { ICONS } from "../components/Icon.svelte";
import { EVENTS, eventStyle, leaning, signed, spread } from "./history";

// The template families of `history_text.TEMPLATES`, which name every kind a chronicle can hold.
const FAMILIES = [
  "foundation", "contact", "exchange", "union", "conflict", "dependency", "protection", "pact",
  "separation", "access", "reform", "migration", "pressure", "repelled", "resisted", "independence",
  "secession",
];

describe("the chronicle's glyphs", () => {
  it("dresses every kind the generator can record, with an icon the window has", () => {
    expect(Object.keys(EVENTS).sort()).toEqual([...FAMILIES].sort());
    for (const kind of FAMILIES) expect(ICONS).toContain(eventStyle(kind).glyph);
  });

  it("draws a kind it does not know as a plain turn", () => {
    expect(eventStyle("something_new")).toEqual({ glyph: "circle", tone: "turn" });
    expect(ICONS).toContain("circle");
  });
});

describe("numbers", () => {
  it("writes opinion with a minus sign", () => {
    expect(signed(-4)).toBe("−4");
    expect(signed(3)).toBe("+3");
    expect(signed(0)).toBe("0");
  });
});

describe("societal values", () => {
  it("names the pole a value leans to and how far", () => {
    const value = { left: "Traditionalist", right: "Innovative" };
    expect(leaning({ ...value, position: -78 })).toEqual({ name: "Traditionalist", strength: 78 });
    expect(leaning({ ...value, position: 12 })).toEqual({ name: "Innovative", strength: 12 });
    expect(leaning({ ...value, position: 0 })).toEqual({ name: "", strength: 0 });
  });

  it("fills a bar from the middle toward the pole", () => {
    expect(spread(-100)).toEqual({ left: 0, width: 50 });
    expect(spread(-50)).toEqual({ left: 25, width: 25 });
    expect(spread(0)).toEqual({ left: 50, width: 0 });
    expect(spread(80)).toEqual({ left: 50, width: 40 });
    expect(spread(300)).toEqual({ left: 50, width: 50 });
  });
});
