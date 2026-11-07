from __future__ import annotations

import os
import pickle
import time
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from rnw import landcache, newworld
from rnw.eu5_canvas import Canvas, OceanRemainder
from rnw.eu5_pacific import IslandGroup
from rnw.islands import Footprint
from rnw.model import CellClass
from rnw.newworld import generate_new_world, land_stage, seal_pockets
from rnw.topology import component_counts
from tests.test_newworld import SMALL

if TYPE_CHECKING:
    from pathlib import Path

    from rnw.eu5_map import Eu5Map
    from rnw.newworld import NewWorld


def test_a_cached_continent_equals_the_uncached_one_and_skips_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    domain = np.ones((160, 192), dtype=np.bool_)
    cache = tmp_path / "land"
    expected = landcache.get_world(None, domain, seed=42, settings=SMALL, drawn=None)
    _ = landcache.get_world(cache, domain, seed=42, settings=SMALL, drawn=None)

    def forbidden(*_args: int, **_kwargs: int) -> NewWorld:
        pytest.fail("a cache hit must not regenerate land")

    monkeypatch.setattr(landcache, "generate_new_world", forbidden)
    found = landcache.get_world(
        cache,
        domain,
        seed=42,
        settings=replace(SMALL, precious_permille=99),
        drawn=None,
    )
    for actual, wanted in (
        (found.labels, expected.labels),
        (found.elevation, expected.elevation),
        (found.pixels, expected.pixels),
        (found.centroids, expected.centroids),
        (found.interior, expected.interior),
        (found.mean_elevation, expected.mean_elevation),
        (found.spread, expected.spread),
    ):
        assert np.array_equal(actual, wanted)
    assert found.classes == expected.classes
    assert found.edges == expected.edges


def test_corrupt_cache_fails_instead_of_rebuilding(tmp_path: Path) -> None:
    domain = np.ones((160, 192), dtype=np.bool_)
    _ = landcache.get_world(tmp_path, domain, seed=1, settings=SMALL, drawn=None)
    target = next(tmp_path.iterdir())
    _ = (target / "labels").write_bytes(b"damaged")
    with pytest.raises(landcache.CacheError, match="damaged"):
        _ = landcache.get_world(tmp_path, domain, seed=1, settings=SMALL, drawn=None)


def test_cache_identity_contains_every_geography_input() -> None:
    domain = np.ones((160, 192), dtype=np.bool_)
    original = landcache.cache_key(domain, 42, SMALL, None)
    assert landcache.cache_key(domain, 43, SMALL, None) != original
    assert landcache.cache_key(domain, 42, replace(SMALL, land_permille=300), None) != original
    assert landcache.cache_key(domain, 42, SMALL, domain) != original
    assert landcache.cache_key(domain, 42, SMALL, None, domain) != original
    domain[50:60, 50:60] = False
    assert landcache.cache_key(domain, 42, SMALL, None) != original


def test_projecting_cached_cells_preserves_identity_across_the_raster_seam(tmp_path: Path) -> None:
    """Land and sea crossing any projection cut keep their colour, graph and identity."""
    domain = np.ones((160, 400), dtype=np.bool_)
    expected = seal_pockets(generate_new_world(domain, seed=3, settings=SMALL))
    world = landcache.get_world(tmp_path, domain, seed=3, settings=SMALL, drawn=None)
    assert np.array_equal(world.labels, expected.labels)
    assert world.classes == expected.classes
    assert world.edges == expected.edges
    for cut in (97, 200, 310):
        crossing = np.unique(
            world.labels[:, cut - 1][world.labels[:, cut - 1] == world.labels[:, cut]]
        )
        cells = cast("list[int]", crossing.tolist())
        assert {world.classes[cell] for cell in cells} >= {CellClass.LAND, CellClass.SEA}
        canvas = Canvas(cut, 0, domain, domain.shape, np.zeros(0, bool), np.zeros(0, bool))
        projected = np.full(domain.shape, -1, dtype=np.int32)
        canvas.put(projected, world.labels)
        assert np.array_equal(projected[:, -1], world.labels[:, cut - 1])
        assert np.array_equal(projected[:, 0], world.labels[:, cut])
        assert np.array_equal(
            component_counts(projected, wrap_x=True), np.ones(len(world.classes), dtype=np.int64)
        )
        # Planar inspection would misclassify exactly these wrapped identities as split.
        assert all(
            size > 1 for size in cast("list[int]", component_counts(projected)[crossing].tolist())
        )


def test_the_cache_keeps_the_moves_of_island_groups_and_keys_on_the_groups(tmp_path: Path) -> None:
    domain = np.ones((160, 192), dtype=np.bool_)
    grid = np.zeros(domain.shape, dtype=bool)
    grid[70:74, 90:100] = True
    found = np.nonzero(grid)
    groups = [Footprint(found[0].astype(np.int32), found[1].astype(np.int32))]
    first = landcache.get_world(tmp_path, domain, seed=5, settings=SMALL, drawn=None, groups=groups)
    again = landcache.get_world(tmp_path, domain, seed=5, settings=SMALL, drawn=None, groups=groups)
    assert first.moves.shape == (1, 2)
    assert np.array_equal(first.moves, again.moves)
    plain = landcache.cache_key(domain, 5, SMALL, None)
    assert landcache.cache_key(domain, 5, SMALL, None, None, groups) != plain


def test_a_kept_land_stage_makes_the_same_world_without_drawing_the_land_again(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The world made from a sketched continent's kept land equals the one made from scratch."""
    domain = np.ones((160, 192), dtype=np.bool_)
    domain[:, :6] = False
    expected = landcache.get_world(None, domain, seed=7, settings=SMALL, drawn=None)
    untouched = domain.copy()
    stage = land_stage(domain.copy(), 7, SMALL)[:3]
    assert np.array_equal(domain, untouched)
    key = landcache.stage_key(landcache.domain_digest(domain), 7, SMALL)
    landcache.keep_stage(tmp_path, key, stage)
    kept = landcache.read_stage(tmp_path, key, (160, 192))
    assert kept is not None
    assert all(np.array_equal(a, b) for a, b in zip(kept, stage, strict=True))

    def forbidden(*_args: object, **_kwargs: object) -> object:
        pytest.fail("a kept land stage must not be drawn again")

    monkeypatch.setattr(newworld, "land_stage", forbidden)
    found = landcache.get_world(tmp_path, domain, seed=7, settings=SMALL, drawn=None)
    assert np.array_equal(found.labels, expected.labels)
    assert np.array_equal(found.elevation, expected.elevation)
    assert found.classes == expected.classes
    assert found.edges == expected.edges


def test_a_land_stage_is_keyed_by_canvas_seed_and_settings(tmp_path: Path) -> None:
    domain = np.ones((160, 192), dtype=np.bool_)
    digest = landcache.domain_digest(domain)
    original = landcache.stage_key(digest, 42, SMALL)
    assert landcache.stage_key(digest, 43, SMALL) != original
    assert landcache.stage_key(digest, 42, replace(SMALL, land_permille=300)) != original
    assert landcache.stage_key(digest, 42, replace(SMALL, precious_permille=99)) == original
    domain[5, 5] = False
    assert landcache.stage_key(landcache.domain_digest(domain), 42, SMALL) != original
    assert landcache.read_stage(tmp_path, original, (160, 192)) is None


def test_a_damaged_land_stage_fails_instead_of_being_drawn_again(tmp_path: Path) -> None:
    domain = np.ones((160, 192), dtype=np.bool_)
    key = landcache.stage_key(landcache.domain_digest(domain), 1, SMALL)
    landcache.keep_stage(tmp_path, key, land_stage(domain.copy(), 1, SMALL)[:3])
    target = landcache.stage_path(tmp_path, key)
    _ = target.write_bytes(target.read_bytes()[:-7])
    with pytest.raises(landcache.CacheError, match="damaged"):
        _ = landcache.get_world(tmp_path, domain, seed=1, settings=SMALL, drawn=None)


def test_pruning_keeps_the_most_recently_used_entries(tmp_path: Path) -> None:
    """Old entries beyond the kept number go; recent ones and foreign files stay."""
    old = time.time() - 2 * landcache.RECENT_SECONDS
    worlds: list[Path] = []
    for number in range(landcache.KEPT_WORLDS + 3):
        entry = tmp_path / f"{number:064x}"
        entry.mkdir()
        _ = (entry / "labels").write_bytes(b"x")
        os.utime(entry, (old + number, old + number))
        worlds.append(entry)
    stages = tmp_path / landcache.STAGES
    stages.mkdir()
    for number in range(landcache.KEPT_STAGES + 2):
        stage = stages / f"{number:064x}{landcache.STAGE_SUFFIX}"
        _ = stage.write_bytes(b"x")
        os.utime(stage, (old + number, old + number))
    recent = tmp_path / f"{999:064x}"
    recent.mkdir()
    foreign = tmp_path / "notes.txt"
    _ = foreign.write_text("mine", encoding="utf-8")
    landcache.prune(tmp_path)
    kept = sorted(item.name for item in tmp_path.iterdir() if item.name != landcache.STAGES)
    # The recent entry counts towards the kept number: it is the most recently used.
    assert kept == sorted(
        [recent.name, foreign.name] + [w.name for w in worlds[-(landcache.KEPT_WORLDS - 1) :]]
    )
    assert len(list(stages.iterdir())) == landcache.KEPT_STAGES


@dataclass(frozen=True, slots=True)
class _MapStub:
    inputs: tuple[str, ...]
    keys: tuple[str, ...] = ("a", "b", "c")


def _canvas() -> Canvas:
    generator = np.random.default_rng(11)
    mask = generator.random((37, 53)) < 0.6
    return Canvas(
        roll=17,
        col0=5,
        mask=mask,
        shape=(37, 120),
        removed=np.array([True, False, True]),
        trimmed=np.array([False, False, True]),
        ocean_parts=(
            OceanRemainder(2, np.array([[1, 2, 5], [2, 3, 9]], dtype=np.int64), 9),
            OceanRemainder(0, np.zeros((0, 3), dtype=np.int64), 0),
        ),
        groups=(IslandGroup((1, 2), (7,)), IslandGroup((), ())),
        footprints=(
            Footprint(np.array([3, 4], dtype=np.int32), np.array([8, 8], dtype=np.int32)),
            Footprint(np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32)),
        ),
        opened=np.array([False, True, False]),
        expanded=True,
    )


def test_a_cached_canvas_is_the_selected_one_and_is_not_selected_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    canvas = _canvas()
    calls: list[tuple[int, bool]] = []

    def select(_map: object, band: int, *, expanded: bool) -> Canvas:
        calls.append((band, expanded))
        return canvas

    def plain_select(_map: object, _band: int, *, expanded: bool) -> Canvas:
        assert not expanded
        return plain

    monkeypatch.setattr(landcache, "select_canvas", select)
    game_map = cast("Eu5Map", cast("object", _MapStub(("locations.png 10 abc",))))
    first = landcache.get_canvas(tmp_path, game_map, 40, expanded=True)
    again = landcache.get_canvas(tmp_path, game_map, 40, expanded=True)
    assert calls == [(40, True)]
    assert first is canvas
    assert pickle.dumps(again) == pickle.dumps(canvas)
    _ = landcache.get_canvas(tmp_path, game_map, 41, expanded=True)
    _ = landcache.get_canvas(
        tmp_path, cast("Eu5Map", cast("object", _MapStub(("other 1 x",)))), 40, expanded=True
    )
    assert calls == [(40, True), (41, True), (40, True)]
    plain = replace(canvas, ocean_parts=(), groups=(), footprints=(), opened=None, expanded=False)
    monkeypatch.setattr(landcache, "select_canvas", plain_select)
    _ = landcache.get_canvas(tmp_path, game_map, 40, expanded=False)
    read = landcache.get_canvas(tmp_path, game_map, 40, expanded=False)
    assert pickle.dumps(read) == pickle.dumps(plain)


def test_a_damaged_canvas_fails_instead_of_being_selected_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def select(_map: object, _band: int, *, expanded: bool) -> Canvas:
        assert expanded
        return _canvas()

    monkeypatch.setattr(landcache, "select_canvas", select)
    game_map = cast("Eu5Map", cast("object", _MapStub(("locations.png 10 abc",))))
    _ = landcache.get_canvas(tmp_path, game_map, 40, expanded=True)
    target = next((tmp_path / landcache.CANVASES).iterdir())
    _ = target.write_bytes(target.read_bytes()[:100])
    with pytest.raises(landcache.CacheError, match="damaged"):
        _ = landcache.get_canvas(tmp_path, game_map, 40, expanded=True)
