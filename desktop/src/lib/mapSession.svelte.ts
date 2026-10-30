// What a map shows and what of it is lit, shared by the viewer that draws it and the inspector
// that chooses its lens, finds places and lists its legend.

import type { WorldAtlas } from "./atlas";
import type { Overlays } from "./mapgl";

export type MapOverlays = Overlays & { labels: boolean };

export interface Highlight {
  label: string;
  cells: Set<number>;
  colour?: string;
}

const STORE = "rnw.map";
const OVERLAYS: MapOverlays = {
  lensBorders: true,
  political: true,
  locations: false,
  coast: true,
  labels: true,
};

function remembered(): { overlays: MapOverlays; tribes: boolean } {
  try {
    const value = JSON.parse(localStorage.getItem(STORE) ?? "{}") as {
      overlays?: Partial<MapOverlays>;
      tribes?: boolean;
    };
    return { overlays: { ...OVERLAYS, ...value.overlays }, tribes: value.tribes === true };
  } catch {
    return { overlays: { ...OVERLAYS }, tribes: false };
  }
}

export class MapSession {
  /** The atlas of the world the viewer shows; null while it loads or when none is shown. */
  atlas = $state.raw<WorldAtlas | null>(null);
  layer = $state("land");
  overlays = $state<MapOverlays>(remembered().overlays);
  /** Tribes coloured and bordered like states; the game's political map leaves them out. */
  tribes = $state(remembered().tribes);
  /** What a legend entry, a search result or a link in a location's card isolated. */
  match = $state.raw<Highlight | null>(null);
  /** What the pointer rests on in the legend or the search results, lit for a moment. */
  preview = $state.raw<Set<number> | null>(null);
  pinned = $state(-1);
  /** The viewer's way to bring cells into view; nothing while no viewer is shown. */
  zoomTo: (cells: Iterable<number>) => void = () => {};

  /** Light only these cells; the same label again lets go of them. */
  isolate(label: string, cells: number[], colour?: string, zoom = false): void {
    if (this.match?.label === label) {
      this.match = null;
      return;
    }
    this.match = { label, cells: new Set(cells), colour };
    if (zoom) this.zoomTo(cells);
  }

  /** The cells of one entry of the current lens's legend. */
  classCells(index: number): number[] {
    return this.atlas ? this.atlas.classCells(this.layer, index, this.tribes) : [];
  }

  remember(): void {
    try {
      localStorage.setItem(STORE, JSON.stringify({ overlays: $state.snapshot(this.overlays), tribes: this.tribes }));
    } catch {
      // Storage is a convenience.
    }
  }
}

/** The main window's map. */
export const map = new MapSession();
