// How the lenses look, read from the generator's own file, so the classic window
// (rnw.gui.mapstyle) and this one draw the same map: palettes, water, the physical map's colours
// and each lens's profile.

import STYLE from "../../../src/rnw/gui/lenses.json";

export type RGB = [number, number, number];

export interface LensProfile {
  /** The land is the physical map itself rather than a colour per location. */
  physical: boolean;
  /** How much of the relief's shade shows on the land, 0..1. */
  shade: number;
  /** Ink of the lines where the lens's own value changes, 0 for none. */
  borders: number;
  /** Ink of country borders when they are shown. */
  political: number;
  /** Names written large: regions and seas, countries, the lens's classes, or none. */
  names: "regions" | "countries" | "classes" | "none";
  /** What is written in each location when it is large enough to hold it. */
  spots: "resource" | "population" | "development" | null;
  /** Opacity of the lens's colour over the physical map, 0..255; a ramp fades with its value. */
  opacity: number;
}

export function hex(colour: string): RGB {
  const value = Number.parseInt(colour.slice(1), 16);
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

export function toHex([r, g, b]: RGB): string {
  return `#${[r, g, b].map((v) => Math.round(v).toString(16).padStart(2, "0")).join("")}`;
}

function table(source: Record<string, string>): Record<string, RGB> {
  return Object.fromEntries(Object.entries(source).map(([key, colour]) => [key, hex(colour)]));
}

/** A colour as the shader takes it: 0..1 per channel. */
export function unit(colour: string): RGB {
  return hex(colour).map((value) => value / 255) as RGB;
}

export const PROFILES = STYLE.profiles as Record<string, LensProfile>;
export const QUALITATIVE: RGB[] = STYLE.qualitative.map(hex);
export const CLIMATES = table(STYLE.palettes.climate);
export const TERRAIN = table(STYLE.palettes.terrain);
export const RESOURCES = table(STYLE.palettes.resources);
export const PRECIOUS_MARKS: Record<string, string> = STYLE.precious;
export const VEGETATION = table(STYLE.vegetation);
export const CLIMATE_TINTS: Record<string, [RGB, number]> = Object.fromEntries(
  Object.entries(STYLE.climate_tints).map(([key, [colour, share]]) => [key, [hex(String(colour)), Number(share)]]),
);
export const TOPOGRAPHY: Record<string, { height: number; rough: number; rock: number }> = STYLE.topography;
export const COLOURS = STYLE.colours;
export const COAST_DEPTH: number = STYLE.coast_depth;
export const TRIBE_OPACITY: number = STYLE.tribe_opacity;
export const RAMP_OPACITY: [number, number] = [STYLE.ramp_opacity[0], STYLE.ramp_opacity[1]];
