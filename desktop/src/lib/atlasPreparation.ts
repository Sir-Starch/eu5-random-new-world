// The expensive first map calculations, shared by the worker and its equality check.
import { WorldAtlas, type Label } from "./atlas";
import { relief, type Relief } from "./relief";
import type { AtlasBundle } from "./types";

export interface PreparedAtlas {
  field: Relief;
  labels: Label[];
}

export function prepareAtlas(bundle: AtlasBundle): PreparedAtlas {
  const atlas = new WorldAtlas(bundle);
  return { field: relief(atlas), labels: atlas.labelsFor("land", "regions") };
}
