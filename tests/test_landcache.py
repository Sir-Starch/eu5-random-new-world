from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from rnw import landcache
from rnw.eu5_canvas import Canvas
from rnw.model import CellClass
from rnw.newworld import generate_new_world, seal_pockets
from rnw.topology import component_counts
from tests.test_newworld import SMALL

if TYPE_CHECKING:
    from pathlib import Path

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
