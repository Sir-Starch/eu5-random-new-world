// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from "vitest";
import { flushSync, mount, unmount } from "svelte";
import WorldView from "../components/WorldView.svelte";
import { app } from "./app.svelte";
import { map } from "./mapSession.svelte";
import { loadAtlas } from "./atlasCache";
import { WorldAtlas } from "./atlas";
import { bundle } from "./atlasFixture";
import type { State, Static } from "./types";

vi.mock("./atlasCache", () => ({ loadAtlas: vi.fn(async () => {
  const data = bundle();
  data.history = { countries: { AAA: {
    government: "Republic", rank: "Duchy", origin: { year: 1037, text: "Founded", place: -1, kind: "origin", label: "Origin" },
    values: [], chronicle: [], partners: [], more: 0,
  } }, regions: {} };
  return new WorldAtlas(data);
}) }));
// Exercise the actual viewer and card; drawing pixels is covered by the atlas tests.
vi.mock("./mapgl", () => ({
  OCEAN_CSS: "blue", paintBox: vi.fn(),
  createRenderer: (canvas: HTMLCanvasElement) => ({
    canvas, kind: "test", dispose: vi.fn(), draw: vi.fn(), setAtlas: vi.fn(),
    setLens: vi.fn(), setFlags: vi.fn(),
  }),
}));

let view: ReturnType<typeof mount> | undefined;

function snapshot(id: string, fraction: number): State {
  return {
    selection: id, busy: true, task: "queue", phase: "running", fraction,
    world: { id, name: id, atlas: true, revealed: true },
  } as State;
}

async function settle(): Promise<void> {
  flushSync();
  await Promise.resolve();
  flushSync();
}

afterEach(async () => {
  if (view) await unmount(view);
  view = undefined;
  app.now = null;
  app.info = null;
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("world viewer during background work", () => {
  it("keeps the pinned place and highlight across fresh progress snapshots", async () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    app.info = { language: "english", strings: {} } as Static;
    app.now = snapshot("viewed", 0.1);
    view = mount(WorldView, { target: document.body });
    await settle();
    expect(loadAtlas).toHaveBeenCalledTimes(1);
    map.pinned = 0;
    map.match = { label: "Country", cells: new Set([0]) };
    flushSync();
    const tab = document.querySelector<HTMLButtonElement>('[role="tab"]:nth-child(2)');
    expect(tab).not.toBeNull();
    tab!.click();
    flushSync();
    const card = document.querySelector(".card");
    expect(card?.textContent).toContain("Republic");
    for (const fraction of [0.2, 0.5, 0.9]) {
      app.now = snapshot("viewed", fraction);
      await settle();
      expect(document.querySelector(".card")).toBe(card);
      expect(card?.textContent).toContain("Republic");
      expect(map.pinned).toBe(0);
      expect(map.match?.label).toBe("Country");
      expect(loadAtlas).toHaveBeenCalledTimes(1);
    }
    // Choosing another world still loads its atlas and clears the old world's selection.
    app.now = snapshot("other", 0.9);
    await settle();
    expect(loadAtlas).toHaveBeenCalledTimes(2);
    expect(loadAtlas).toHaveBeenLastCalledWith("other");
    expect(map.pinned).toBe(-1);
    expect(map.match).toBeNull();
    // Changing the language must still reload the localized atlas.
    app.info = { language: "russian", strings: {} } as Static;
    await settle();
    expect(loadAtlas).toHaveBeenCalledTimes(3);
  });
});
