import { describe, expect, it } from "vitest";
import { ICONS } from "../components/Icon.svelte";
import { EVENTS, eventStyle, mood, percent, signed, standing } from "./history";

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

describe("feelings and standings", () => {
  it("reads good, bad and flat from the factor", () => {
    expect(mood("trust")).toBe("good");
    expect(mood("grievance")).toBe("bad");
    expect(mood("dependence")).toBe("flat");
    expect(standing("lord")).toBe("rank");
    expect(standing("rival")).toBe("bad");
    expect(standing("trade")).toBe("flat");
  });
});

describe("numbers", () => {
  it("scales a trait to 0-100 and clamps it", () => {
    expect(percent(800)).toBe(80);
    expect(percent(397)).toBe(40);
    expect(percent(1200)).toBe(100);
    expect(percent(-5)).toBe(0);
  });

  it("writes opinion with a minus sign", () => {
    expect(signed(-4)).toBe("−4");
    expect(signed(3)).toBe("+3");
    expect(signed(0)).toBe("0");
  });
});
