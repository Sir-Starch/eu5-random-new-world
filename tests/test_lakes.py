"""Lakes sized and spread like the installed game's: count, size tail, rim and determinism."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np

from rnw.lakes import blob, carve_lakes, lake_sites
from rnw.topology import euclidean_distance, label_components


def _continent(rows: int = 1400, columns: int = 1800, edge: int = 60) -> np.ndarray:
    land = np.zeros((rows, columns), dtype=bool)
    land[edge:-edge, edge:-edge] = True
    return land


def test_lakes_keep_a_rim_of_land_and_stay_on_land() -> None:
    land = _continent()
    carved = carve_lakes(land, 5, smallest=80, largest=22_000)
    assert carved.any()
    assert not (carved & ~land).any()
    away = euclidean_distance(~land, 40) >= 8 * 14
    assert not (carved & ~away).any()


def test_lake_count_and_sizes_follow_the_vanilla_tail() -> None:
    """Of the lakes of at least 80 pixels (the smaller are filled with land): vanilla has 11.2
    per million land pixels, quartiles 127/214/503, 1,100 at the 90th percentile."""
    land = _continent(3000, 3400, 100)
    counts: list[float] = []
    sizes: list[int] = []
    for seed in (1, 2, 3):
        carved = carve_lakes(land, seed, smallest=80, largest=22_000)
        parts = label_components(carved.astype(np.int32))
        found = np.bincount(parts[carved])
        found = found[found >= 80]
        counts.append(len(found) / int(np.count_nonzero(land)) * 1e6)
        sizes.extend(found.tolist())
    assert 9 < float(np.mean(counts)) < 14
    low, middle, high = np.percentile(sizes, [25, 50, 75])
    assert 100 < low < 150
    assert 150 < middle < 250
    assert 300 < high < 600
    assert max(sizes) > 5000
    assert max(sizes) <= 22_000 * 1.35


def test_lakes_are_deterministic_and_vary_with_the_seed() -> None:
    land = _continent(900, 1200, 50)
    first = carve_lakes(land, 9, smallest=80, largest=22_000)
    assert np.array_equal(first, carve_lakes(land, 9, smallest=80, largest=22_000))
    assert not np.array_equal(first, carve_lakes(land, 10, smallest=80, largest=22_000))


def test_no_lake_is_drawn_without_land_to_hold_it() -> None:
    land = np.zeros((500, 500), dtype=bool)
    land[240:260, 240:260] = True
    assert not carve_lakes(land, 3, smallest=80, largest=22_000).any()
    assert lake_sites(land, 3, smallest=80, largest=22_000) == []


def test_a_blob_has_the_area_it_was_asked_for() -> None:
    """The ellipse with a noisy outline averages the area of the plain ellipse."""
    areas: list[int] = []
    for key in range(1, 9):
        window = (slice(0, 400), slice(0, 400))
        shape = blob(window, (200, 200), (90, 40), 5, key * 7919)
        areas.append(int(np.count_nonzero(shape)))
    expected = np.pi * 90 * 40
    assert 0.8 * expected < float(np.mean(areas)) < 1.25 * expected
