// @vitest-environment happy-dom
import { beforeEach, describe, expect, it, vi } from "vitest";
import { bundle } from "./atlasFixture";
import { prepareAtlas } from "./atlasPreparation";
import type { AtlasBundle } from "./types";

const bridge = vi.hoisted(() => ({ call: vi.fn(), info: { language: "english" }, now: { game: { directory: "game" } } }));
vi.mock("./app.svelte", () => ({ app: bridge }));

class FakeWorker {
  static instances: FakeWorker[] = [];
  onmessage: ((event: unknown) => void) | null = null;
  onerror: ((event: unknown) => void) | null = null;
  terminate = vi.fn();
  data: AtlasBundle | null = null;
  constructor() { FakeWorker.instances.push(this); }
  postMessage(message: { bundle: AtlasBundle }): void { this.data = message.bundle; }
  finish(): void {
    this.onmessage?.({ data: { prepared: prepareAtlas(this.data!) } });
  }
}

async function tick(): Promise<void> { for (let i = 0; i < 8; i++) await Promise.resolve(); }

beforeEach(() => {
  vi.resetModules();
  bridge.call.mockReset();
  bridge.call.mockImplementation(async (method: string) => method === "atlas" ? bundle() : null);
  bridge.info.language = "english";
  FakeWorker.instances = [];
  vi.stubGlobal("Worker", FakeWorker);
});

describe("atlas loading lifecycle", () => {
  it("reuses prepared maps and expires them when their files or language change", async () => {
    const { loadAtlas } = await import("./atlasCache");
    const first = loadAtlas("A", "main", "revision-1");
    await tick();
    FakeWorker.instances[0].finish();
    const atlas = await first;
    expect(atlas).not.toBeNull();
    expect(await loadAtlas("A", "main", "revision-1")).toBe(atlas);
    expect(bridge.call).toHaveBeenCalledTimes(1);
    const changed = loadAtlas("A", "main", "revision-2");
    await tick(); FakeWorker.instances[1].finish(); await changed;
    bridge.info.language = "russian";
    const translated = loadAtlas("A", "main", "revision-2");
    await tick(); FakeWorker.instances[2].finish(); await translated;
    expect(bridge.call).toHaveBeenCalledTimes(3);
  });

  it("cancels obsolete bridge requests and never prepares their late replies", async () => {
    const replies: ((value: AtlasBundle) => void)[] = [];
    bridge.call.mockImplementation((method: string) => method === "atlas" ? new Promise((resolve) => replies.push(resolve)) : Promise.resolve(null));
    const { loadAtlas, releaseAtlas } = await import("./atlasCache");
    const old = loadAtlas("A", "main");
    releaseAtlas("main");
    const latest = loadAtlas("B", "main");
    replies[0](bundle());
    await tick();
    expect(FakeWorker.instances).toHaveLength(0);
    expect(await old).toBeNull();
    replies[1](bundle());
    await tick();
    FakeWorker.instances[0].finish();
    expect(await latest).not.toBeNull();
    expect(bridge.call).toHaveBeenCalledWith("cancel_atlas", { request_key: "main:1" });
  });

  it("keeps a shared comparison request alive until its last viewer leaves", async () => {
    const { loadAtlas, releaseAtlas } = await import("./atlasCache");
    const main = loadAtlas("A", "main");
    const comparison = loadAtlas("A", "compare-left");
    expect(main).toBe(comparison);
    await tick();
    releaseAtlas("main");
    expect(FakeWorker.instances[0].terminate).not.toHaveBeenCalled();
    releaseAtlas("compare-left");
    expect(FakeWorker.instances[0].terminate).toHaveBeenCalledOnce();
    expect(await comparison).toBeNull();
    // Returning to the cancelled map starts a fresh request.
    const retry = loadAtlas("A", "main");
    await tick(); FakeWorker.instances[1].finish();
    expect(await retry).not.toBeNull();
  });

  it("retries failed preparation and keeps the newer request when a cancelled one finishes", async () => {
    const { loadAtlas, releaseAtlas } = await import("./atlasCache");
    const broken = loadAtlas("A");
    const rejected = expect(broken).rejects.toThrow("worker failed");
    await tick();
    FakeWorker.instances[0].onerror?.({ message: "worker failed" });
    await rejected;
    const replies: ((value: AtlasBundle) => void)[] = [];
    bridge.call.mockImplementation((method: string) => method === "atlas" ? new Promise((resolve) => replies.push(resolve)) : Promise.resolve(null));
    const old = loadAtlas("A", "main");
    releaseAtlas("main");
    const retry = loadAtlas("A", "main");
    replies[0](bundle());
    await old;
    expect(loadAtlas("A", "compare-left")).toBe(retry);
    replies[1](bundle());
    await tick(); FakeWorker.instances[1].finish();
    expect(await retry).not.toBeNull();
  });

  it("retains recently used maps when the bounded cache fills", async () => {
    const { loadAtlas } = await import("./atlasCache");
    const maps = [];
    for (const id of ["A", "B", "C", "D"]) {
      const request = loadAtlas(id);
      await tick(); FakeWorker.instances.at(-1)!.finish(); maps.push(await request);
    }
    expect(await loadAtlas("A")).toBe(maps[0]);
    const fifth = loadAtlas("E");
    await tick(); FakeWorker.instances.at(-1)!.finish(); await fifth;
    expect(await loadAtlas("A")).toBe(maps[0]);
    expect(FakeWorker.instances).toHaveLength(5);
    const evicted = loadAtlas("B");
    await tick(); FakeWorker.instances.at(-1)!.finish(); await evicted;
    expect(FakeWorker.instances).toHaveLength(6);
  });
});
