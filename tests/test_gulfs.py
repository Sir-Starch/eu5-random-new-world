"""Inland seas: a basin inside the land, a rim around it and a strait to the open sea."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np

from rnw.gulfs import carve_inland_seas
from rnw.topology import euclidean_distance, label_components

SCALE = 400


def _world(rows: int = 1500, columns: int = 1900, edge: int = 90) -> tuple[np.ndarray, np.ndarray]:
    land = np.zeros((rows, columns), dtype=bool)
    land[edge:-edge, edge:-edge] = True
    return land, ~land


def _made(seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    land, ocean = _world()
    return land, ocean, carve_inland_seas(land, ocean, seed, scale_px=SCALE)


def test_seas_are_cut_in_land_and_reach_the_open_sea() -> None:
    cut_any = 0
    for seed in range(1, 9):
        land, ocean, carved = _made(seed)
        assert not (carved & ~land).any()
        if not carved.any():
            continue
        cut_any += 1
        water = ~(land & ~carved)
        parts = label_components(water.astype(np.int32))
        assert set(np.unique(parts[carved])) <= set(np.unique(parts[ocean]))
    assert cut_any >= 4


def test_a_sea_is_inland_with_a_narrow_mouth() -> None:
    """The sea lies away from the old coast and meets it only along a short strait."""
    _land, ocean, carved = _made(3)
    parts = label_components(carved.astype(np.int32))
    sizes = np.bincount(parts[carved], minlength=int(parts.max()) + 1)
    sea = parts == int(np.argmax(sizes))
    assert np.count_nonzero(sea) > 1000
    from_coast = euclidean_distance(ocean, 200)
    assert bool((sea & (from_coast >= 8 * 20)).any())  # a rim of land, not a coastal bay
    shore = np.pad(ocean, 1)
    touching = sea & (shore[:-2, 1:-1] | shore[2:, 1:-1] | shore[1:-1, :-2] | shore[1:-1, 2:])
    assert 0 < np.count_nonzero(touching) < np.count_nonzero(sea) // 20


def test_seas_are_deterministic_and_vary_with_the_seed() -> None:
    land, ocean = _world()
    first = carve_inland_seas(land, ocean, 4, scale_px=SCALE)
    assert np.array_equal(first, carve_inland_seas(land, ocean, 4, scale_px=SCALE))
    others = [carve_inland_seas(land, ocean, seed, scale_px=SCALE) for seed in (5, 6, 7)]
    assert any(not np.array_equal(first, other) for other in others)


def test_land_too_small_for_a_sea_is_left_alone() -> None:
    land = np.zeros((600, 600), dtype=bool)
    land[250:350, 250:350] = True
    assert not carve_inland_seas(land, ~land, 2, scale_px=SCALE).any()


def test_the_inputs_are_not_changed() -> None:
    land, ocean = _world()
    before = land.copy(), ocean.copy()
    _ = carve_inland_seas(land, ocean, 2, scale_px=SCALE)
    assert np.array_equal(land, before[0])
    assert np.array_equal(ocean, before[1])
