"""Terrain export retains vanilla primary placement geometry, including its map edges."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import numpy as np

from rnw.eu5_terrain import (
    DECAL_CACHE,
    DecalStore,
    _disable_decals,  # pyright: ignore[reportPrivateUsage]
)

if TYPE_CHECKING:
    from pathlib import Path


def _store(root: Path) -> DecalStore:
    entries: list[dict[str, object]] = []
    for number, x in ((1, 40), (2, 120)):
        name = f"heightmap_{number}_16"
        entries.append(
            {
                "decal_name": name,
                "decal_transform": {
                    "position": {"x": x, "y": 24},
                    "scale": {"x": 2, "y": 2},
                    "rotation": 0,
                },
                "decal_size": {"x": 40, "y": 24},
                "decal_params": {"heightblendmode": "add", "strength": 1, "fade_margin": 0},
            }
        )
        folder = root / "game/in_game/gfx/terrain2/decals" / name / "instances"
        folder.mkdir(parents=True)
        _ = (folder / "source.json").write_text(
            json.dumps(
                {
                    "position.x": x,
                    "position.y": 24,
                    "rotation": 0,
                    "scale.x": 2,
                    "scale.y": 2,
                    "disabled": False,
                    "layer_id": "test",
                }
            )
        )
    target = root / DECAL_CACHE
    target.parent.mkdir(parents=True)
    _ = target.write_text(json.dumps(entries))
    return DecalStore(root, (12, 40))


def test_export_preserves_primary_geometry_and_instances(tmp_path: Path) -> None:
    """Terrain regeneration must not extend or relocate the game's edge sources."""
    store = _store(tmp_path)
    before = json.dumps(store.cache, sort_keys=True)
    instances = {path: path.read_bytes() for path in tmp_path.rglob("source.json")}
    files, cache = _disable_decals(store, np.ones(store.map_shape, dtype=np.int8))
    assert json.dumps(store.cache, sort_keys=True) == before
    assert json.loads(cache.decode("utf-8-sig")) == store.cache
    assert files == {}
    assert {path: path.read_bytes() for path in instances} == instances
