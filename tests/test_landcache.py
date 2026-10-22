from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw import landcache
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
    expected = landcache.get_world(None, domain, seed=42, settings=SMALL, seam=0, drawn=None)
    _ = landcache.get_world(cache, domain, seed=42, settings=SMALL, seam=0, drawn=None)

    def forbidden(*_args: int, **_kwargs: int) -> NewWorld:
        pytest.fail("a cache hit must not regenerate land")

    monkeypatch.setattr(landcache, "generate_new_world", forbidden)
    found = landcache.get_world(
        cache,
        domain,
        seed=42,
        settings=replace(SMALL, precious_permille=99),
        seam=0,
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
    _ = landcache.get_world(tmp_path, domain, seed=1, settings=SMALL, seam=None, drawn=None)
    target = next(tmp_path.iterdir())
    _ = (target / "labels").write_bytes(b"damaged")
    with pytest.raises(landcache.CacheError, match="damaged"):
        _ = landcache.get_world(tmp_path, domain, seed=1, settings=SMALL, seam=None, drawn=None)


def test_cache_identity_contains_every_geography_input() -> None:
    domain = np.ones((160, 192), dtype=np.bool_)
    original = landcache.cache_key(domain, 42, SMALL, None, None)
    assert landcache.cache_key(domain, 43, SMALL, None, None) != original
    assert landcache.cache_key(domain, 42, SMALL, 80, None) != original
    assert (
        landcache.cache_key(domain, 42, replace(SMALL, land_permille=300), None, None) != original
    )
    assert landcache.cache_key(domain, 42, SMALL, None, domain) != original
    domain[50:60, 50:60] = False
    assert landcache.cache_key(domain, 42, SMALL, None, None) != original
