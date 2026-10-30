// Atlases the viewer has unrolled, kept for the few worlds looked at last.

import { app } from "./app.svelte";
import { WorldAtlas } from "./atlas";
import type { PreparedAtlas } from "./atlasPreparation";
import { rememberRelief } from "./relief";
import type { AtlasBundle } from "./types";

const KEEP = 4;
const cache = new Map<string, Promise<WorldAtlas | null>>();
let worker: Worker | null = null;
let serial = 0;
const waiting = new Map<number, { resolve: (value: PreparedAtlas) => void; reject: (error: Error) => void }>();

function prepare(bundle: AtlasBundle): Promise<WorldAtlas> {
  if (!worker) {
    worker = new Worker(new URL("./atlas.worker.ts", import.meta.url), { type: "module" });
    worker.onmessage = (event: MessageEvent<{ id: number; prepared: PreparedAtlas; error?: string }>): void => {
      const { id, prepared, error } = event.data;
      const pending = waiting.get(id);
      waiting.delete(id);
      if (error) pending?.reject(new Error(error));
      else pending?.resolve(prepared);
    };
    worker.onerror = (event): void => {
      for (const pending of waiting.values()) pending.reject(new Error(event.message));
      waiting.clear();
      worker?.terminate();
      worker = null;
    };
  }
  const id = ++serial;
  const ready = new Promise<PreparedAtlas>((resolve, reject) => {
    waiting.set(id, { resolve, reject });
  });
  worker.postMessage({ id, bundle });
  return ready.then(({ field, labels }) => {
    const atlas = new WorldAtlas(bundle, labels);
    rememberRelief(atlas, field);
    return atlas;
  });
}

export function loadAtlas(id: string): Promise<WorldAtlas | null> {
  const key = `${id}|${app.info?.language ?? ""}`;
  let found = cache.get(key);
  if (!found) {
    found = app.call<AtlasBundle | null>("atlas", { id }).then((bundle) =>
      bundle ? prepare(bundle) : null,
    );
    cache.set(key, found);
    void found.then((atlas) => {
      if (!atlas) cache.delete(key);
    }).catch(() => cache.delete(key));
    while (cache.size > KEEP) cache.delete(cache.keys().next().value as string);
  }
  return found;
}

export function forgetAtlas(id: string): void {
  for (const key of [...cache.keys()]) if (key.startsWith(`${id}|`)) cache.delete(key);
}
