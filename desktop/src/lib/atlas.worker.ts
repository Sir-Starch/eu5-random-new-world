// One worker for the app: relief and region names never occupy the window's event loop.
import { prepareAtlas } from "./atlasPreparation";
import type { AtlasBundle } from "./types";

self.onmessage = (event: MessageEvent<{ id: number; bundle: AtlasBundle }>): void => {
  const { id, bundle } = event.data;
  try {
    const prepared = prepareAtlas(bundle);
    self.postMessage({ id, prepared }, { transfer: [prepared.field.land.buffer, prepared.field.depth.buffer] });
  } catch (error) {
    self.postMessage({ id, error: String(error) });
  }
};
