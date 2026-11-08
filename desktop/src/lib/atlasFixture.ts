// Synthetic atlas shared by numerical and viewer lifecycle regressions.
import type { AtlasBundle } from "./types";

function base64(bytes: Uint8Array): string {
  return Buffer.from(bytes).toString("base64");
}

export function runs(pairs: number[]): string {
  return base64(new Uint8Array(new Uint32Array(pairs).buffer));
}

// A 4 x 2 box: two land locations (0, 1) and sea (2), the last pixel outside.
export function bundle(): AtlasBundle {
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
    population: [100, 0, 0], development: [12500, 0, 0], centre: [0, 0, 0, 2, 1, 1],
    vocabulary: { culture: ["Alpine"], religion: ["Faith"], material: ["Gold", "Salt"], climate: ["Cold"], vegetation: ["Woods"], topography: ["Hills"], settlement: [] },
    raw: { material: ["goods_gold", "salt"] }, precious: ["goods_gold"],
    countries: [{ tag: "AAA", name: "Aland", kind: "state", color: "#c80000", capital: 0, culture: 0, religion: 0, locations: 1 }],
    totals: { countries: 1, states: 1, tribes: 0, cultures: 1, religions: 1, locations: 3, land: 2 },
    layers: { countries: layer },
  };
}
