// Prepared maps stay in a bounded LRU. A viewer owns a cancellable subscription, so switching
// worlds drops obsolete bridge/worker work without disturbing another comparison pane.
import { app } from "./app.svelte";
import { WorldAtlas } from "./atlas";
import type { PreparedAtlas } from "./atlasPreparation";
import { rememberRelief } from "./relief";
import type { AtlasBundle } from "./types";

const KEEP = 4;
const cache = new Map<string, WorldAtlas>();
interface Pending {
  requestKey: string;
  promise: Promise<WorldAtlas | null>;
  viewers: Set<string>;
  abort: AbortController;
}
const pending = new Map<string, Pending>();
let serial = 0;

function prepare(bundle: AtlasBundle, signal: AbortSignal): Promise<WorldAtlas | null> {
  if (signal.aborted) return Promise.resolve(null);
  return new Promise((resolve, reject) => {
    const worker = new Worker(new URL("./atlas.worker.ts", import.meta.url), { type: "module" });
    const finish = (): void => {
      worker.terminate();
      signal.removeEventListener("abort", cancel);
    };
    const cancel = (): void => { finish(); resolve(null); };
    signal.addEventListener("abort", cancel, { once: true });
    worker.onmessage = (event: MessageEvent<{ prepared: PreparedAtlas; error?: string }>): void => {
      finish();
      if (event.data.error) { reject(new Error(event.data.error)); return; }
      try {
        const { field, labels } = event.data.prepared;
        const atlas = new WorldAtlas(bundle, labels);
        rememberRelief(atlas, field);
        resolve(atlas);
      } catch (error) { reject(error); }
    };
    worker.onerror = (event): void => { finish(); reject(new Error(event.message)); };
    worker.postMessage({ id: 1, bundle });
  });
}

export function loadAtlas(id: string, viewer = "main", revision = ""): Promise<WorldAtlas | null> {
  const key = `${id}|${app.info?.language ?? ""}|${app.now?.game?.directory ?? ""}|${app.now?.game?.build ?? ""}|${revision}`;
  const cached = cache.get(key);
  if (cached) {
    cache.delete(key);
    cache.set(key, cached);
    return Promise.resolve(cached);
  }
  let found = pending.get(key);
  if (!found) {
    const requestKey = `${viewer}:${++serial}`;
    const abort = new AbortController();
    const entry: Pending = { requestKey, abort, viewers: new Set(), promise: Promise.resolve(null) };
    entry.promise = app.call<AtlasBundle | null>("atlas", { id, request_key: requestKey }).then((bundle) =>
      bundle && !abort.signal.aborted ? prepare(bundle, abort.signal) : null,
    ).then((atlas) => {
      if (atlas && !abort.signal.aborted) {
        cache.set(key, atlas);
        while (cache.size > KEEP) cache.delete(cache.keys().next().value as string);
      }
      return atlas;
    }).finally(() => {
      if (pending.get(key) === entry) pending.delete(key);
    });
    found = entry;
    pending.set(key, entry);
  }
  found.viewers.add(viewer);
  return found.promise;
}

export function releaseAtlas(viewer: string): void {
  for (const [key, entry] of pending) {
    if (!entry.viewers.delete(viewer) || entry.viewers.size) continue;
    pending.delete(key);
    entry.abort.abort();
    void app.call("cancel_atlas", { request_key: entry.requestKey });
  }
}

export function forgetAtlas(id: string): void {
  for (const key of cache.keys()) if (key.startsWith(`${id}|`)) cache.delete(key);
  for (const [key, entry] of pending) {
    if (!key.startsWith(`${id}|`)) continue;
    pending.delete(key);
    entry.abort.abort();
    void app.call("cancel_atlas", { request_key: entry.requestKey });
  }
}
