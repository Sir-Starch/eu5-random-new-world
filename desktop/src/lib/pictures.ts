// A world's mod picture at full size, fetched once per version of the file.

import { app } from "./app.svelte";

const cache = new Map<string, Promise<string>>();

export function picture(id: string, version: string): Promise<string> {
  const key = `${id}|${version}`;
  let found = cache.get(key);
  if (!found) {
    found = app.call<string>("picture", { id }).then((url) => url ?? "");
    cache.set(key, found);
    while (cache.size > 8) cache.delete(cache.keys().next().value as string);
  }
  return found;
}
