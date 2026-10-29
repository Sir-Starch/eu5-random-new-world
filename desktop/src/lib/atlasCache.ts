// Atlases the viewer has unrolled, kept for the few worlds looked at last.

import { app } from "./app.svelte";
import { WorldAtlas } from "./atlas";
import type { AtlasBundle } from "./types";

const KEEP = 4;
const cache = new Map<string, Promise<WorldAtlas | null>>();

export function loadAtlas(id: string): Promise<WorldAtlas | null> {
  const key = `${id}|${app.info?.language ?? ""}`;
  let found = cache.get(key);
  if (!found) {
    found = app.call<AtlasBundle | null>("atlas", { id }).then((bundle) =>
      bundle ? new WorldAtlas(bundle) : null,
    );
    cache.set(key, found);
    found.then((atlas) => {
      if (!atlas) cache.delete(key);
    });
    while (cache.size > KEEP) cache.delete(cache.keys().next().value as string);
  }
  return found;
}

export function forgetAtlas(id: string): void {
  for (const key of [...cache.keys()]) if (key.startsWith(`${id}|`)) cache.delete(key);
}
