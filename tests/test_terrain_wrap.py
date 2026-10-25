"""Periodic decal placements supply the mesh boundary that half-open source bounds omit."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest

from rnw.eu5_terrain import (
    DECAL_CACHE,
    DecalStore,
    TerrainRangeError,
    _periodic_heightmaps,  # pyright: ignore[reportPrivateUsage]
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


def _local_x(entry: dict[str, object], x: float) -> float | None:
    """Installed shader contract: transform then IntersectsDecal's [0, 1) test."""
    transform = cast("dict[str, object]", entry["decal_transform"])
    position = cast("dict[str, float]", transform["position"])
    scale = cast("dict[str, float]", transform["scale"])
    size = cast("dict[str, int]", entry["decal_size"])
    u = (x - position["x"]) / (size["x"] * scale["x"]) + 0.5
    return u if 0 <= u < 1 else None


def test_periodic_decals_cover_boundary_vertices_and_halos_without_interior_overlap(
    tmp_path: Path,
) -> None:
    """The upper endpoint and outside normals sample the periodic source, never zero."""
    store = _store(tmp_path)
    before = json.dumps(store.cache, sort_keys=True)
    periodic, files = _periodic_heightmaps(store)
    assert json.dumps(store.cache, sort_keys=True) == before
    assert len(periodic) == len(files) == 2
    assert not any(_local_x(entry, 160) is not None for entry in store.cache)
    for x in (-4.0, -0.25, 0.0, 0.25, 40.0, 80.0, 159.75, 160.0, 160.25, 164.0):
        found = [
            (entry["decal_name"], u)
            for entry in [*store.cache, *periodic]
            if (u := _local_x(entry, x)) is not None
        ]
        reference = [
            (entry["decal_name"], u)
            for entry in store.cache
            if (u := _local_x(entry, x % 160)) is not None
        ]
        assert len(found) == len(reference) == 1
        assert found[0][0] == reference[0][0]
        assert found[0][1] == pytest.approx(reference[0][1])
    for path, raw in files.items():
        instance = cast("dict[str, object]", json.loads(raw.decode("utf-8-sig")))
        name = path.split("/")[4]
        cached = next(entry for entry in periodic if entry["decal_name"] == name)
        transform = cast("dict[str, object]", cached["decal_transform"])
        position = cast("dict[str, float]", transform["position"])
        assert instance["position.x"] == position["x"]
        assert instance["position.y"] == position["y"]
        assert instance["disabled"] is False


def test_a_missing_or_changed_edge_instance_fails_loudly(tmp_path: Path) -> None:
    """A baked cache must not conceal a missing source placement on a changed build."""
    store = _store(tmp_path)
    source = tmp_path / "game/in_game/gfx/terrain2/decals/heightmap_1_16/instances/source.json"
    source.unlink()
    with pytest.raises(TerrainRangeError, match="one unrotated"):
        _ = _periodic_heightmaps(store)


@pytest.mark.parametrize("key", ["position.y", "scale.x"])
def test_editor_and_cached_geometry_must_agree(tmp_path: Path, key: str) -> None:
    """Cache regeneration must reproduce the same periodic placements."""
    store = _store(tmp_path)
    source = tmp_path / "game/in_game/gfx/terrain2/decals/heightmap_1_16/instances/source.json"
    data = cast("dict[str, object]", json.loads(source.read_text()))
    data[key] = 99
    _ = source.write_text(json.dumps(data))
    with pytest.raises(TerrainRangeError, match="cached geometry"):
        _ = _periodic_heightmaps(store)
