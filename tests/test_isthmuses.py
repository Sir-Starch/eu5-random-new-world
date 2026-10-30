"""Isthmuses: narrow land across the water between two landmasses, never closing a sea off."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np

from rnw.isthmuses import raise_isthmuses
from rnw.topology import label_components

SCALE = 400


def _two(gap: int = 60, rows: int = 700, *, third: bool = False) -> tuple[np.ndarray, np.ndarray]:
    land = np.zeros((rows, 900), dtype=bool)
    land[100:-100, 60 : 440 - gap // 2] = True
    land[100:-100, 460 + gap // 2 : 840] = True
    if third:
        land[250:450, 430:470] = True
    return land, ~land


def _raise(land: np.ndarray, ocean: np.ndarray, seed: int) -> np.ndarray:
    allowed = np.ones(land.shape, dtype=bool)
    return raise_isthmuses(land, ocean, allowed, seed, scale_px=SCALE)


def test_some_seeds_join_two_landmasses_across_a_strait() -> None:
    land, ocean = _two()
    joined = 0
    for seed in range(1, 13):
        raised = _raise(land, ocean, seed)
        assert not (raised & land).any()
        if not raised.any():
            continue
        joined += 1
        parts = label_components((land | raised).astype(np.int32))
        left, right = parts[300, 100], parts[300, 800]
        assert left == right
        # Land that joins them is a neck: narrower than the strait is long in most places.
        assert int(np.count_nonzero(raised[:, 440])) < 140
    assert 2 <= joined <= 10  # a chance, not a rule


def test_a_bridge_never_touches_a_third_landmass_or_the_edge() -> None:
    land, ocean = _two(third=True)
    allowed = np.ones(land.shape, dtype=bool)
    allowed[:, :80] = False
    for seed in range(1, 13):
        raised = raise_isthmuses(land, ocean, allowed, seed, scale_px=SCALE)
        assert not (raised & ~allowed).any()


def test_bridges_do_not_cut_a_bay_off_from_the_sea() -> None:
    """A sea enclosed by the two landmasses stays open to the water north of it."""
    land, ocean = _two(gap=60, rows=700)
    land[100:200, 395:505] = False
    land[100:200, 60:395] = True
    land[100:200, 505:840] = True
    ocean = ~land
    for seed in range(1, 13):
        raised = _raise(land, ocean, seed)
        water = ~(land | raised)
        parts = label_components(water.astype(np.int32))
        reaching = set(np.unique(parts[0, :])) | set(np.unique(parts[:, 0]))
        pieces = set(np.unique(parts[water]))
        before = label_components((~land).astype(np.int32))
        closed_before = set(np.unique(before[~land])) - (
            set(np.unique(before[0, :])) | set(np.unique(before[:, 0]))
        )
        assert len(pieces - reaching) <= len(closed_before)


def test_isthmuses_are_deterministic() -> None:
    land, ocean = _two()
    for seed in (2, 5):
        assert np.array_equal(_raise(land, ocean, seed), _raise(land, ocean, seed))


def test_small_landmasses_are_left_apart() -> None:
    land = np.zeros((300, 400), dtype=bool)
    land[100:120, 50:80] = True
    land[100:120, 140:170] = True
    assert not _raise(land, ~land, 3).any()
