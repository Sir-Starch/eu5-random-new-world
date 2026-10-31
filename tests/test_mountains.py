"""Mountain detail is continuous across bands and independent of location identities."""

# pyright: reportAny=false
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw.eu5_mountains import (
    ACROSS_MIN,
    ACROSS_RANGE,
    AXES,
    CELL,
    PLACE,
    REACH,
    SMOOTH,
    STEP,
    Mountain,
    MountainRelief,
    crest_axes,
    mountain_relief,
)
from rnw.eu5_slots import NO_MATERIAL
from rnw.terrain_tiles import LayerFormat

if TYPE_CHECKING:
    from collections.abc import Iterable

    from numpy.typing import NDArray


def ridge() -> NDArray[np.uint16]:
    rows, columns = np.indices((64, 64))
    return (np.maximum(0, 30 - np.abs(columns - 32) - np.abs(rows - 32) // 3) * 1900).astype(
        np.uint16
    )


def test_a_rotated_range_samples_identically_in_arbitrary_bands_and_columns() -> None:
    field = MountainRelief(
        (ridge(),),
        (Mountain(70, 100, 130, 90, 0, 3, 200), Mountain(120, 125, 90, 90, 0, 0, 200)),
    )
    whole = field.sample((10, 20), (160, 190))
    assert int(whole.max()) > 8000
    assert np.all(whole >= 0)
    rows = np.concatenate(
        [field.sample((10, top), (min(17, 180 - top), 190)) for top in range(20, 180, 17)]
    )
    columns = np.concatenate(
        [field.sample((left, 20), (160, min(23, 200 - left))) for left in range(10, 200, 23)],
        axis=1,
    )
    assert np.array_equal(whole, rows)
    assert np.array_equal(whole, columns)
    assert np.count_nonzero(whole[:, :8]) == 0
    assert np.array_equal(field.sources[0], ridge())


@dataclass
class Sources:
    size: int = 1024

    def layer(self, decal: str, kind: str) -> tuple[LayerFormat, NDArray[np.uint16]]:
        del decal, kind
        a = np.zeros((self.size, self.size), dtype=np.uint16)
        a[self.size // 4 : 3 * self.size // 4, self.size // 4 : 3 * self.size // 4] = 40000
        return LayerFormat(self.size, self.size, "<u2"), a


def test_placement_follows_relief_with_stable_seed_and_refuses_changed_sources() -> None:
    elevation = np.zeros((160, 240), dtype=np.int32)
    elevation[35:125, 30:210] = 22000
    first = mountain_relief(Sources(), elevation, seed=73, column0=0)
    assert first.placements
    assert first.placements == mountain_relief(Sources(), elevation, seed=73, column0=0).placements
    assert first.placements != mountain_relief(Sources(), elevation, seed=74, column0=0).placements
    # A stamp is placed where the smoothed relief is high, so at most the smoothing's reach
    # beyond the elevated block.
    reach = 2 * SMOOTH * CELL
    assert all(
        35 - reach <= s.row // 2 < 125 + reach and 30 - reach <= s.column // 2 < 210 + reach
        for s in first.placements
    )
    assert not mountain_relief(Sources(), elevation * 0, seed=73, column0=0).placements
    assert not mountain_relief(
        Sources(), elevation * 0 + PLACE - 3000, seed=73, column0=0
    ).placements
    with pytest.raises(ValueError, match="1024"):
        _ = mountain_relief(Sources(64), elevation, seed=73, column0=0)


def _mean(values: Iterable[int]) -> float:
    items = list(values)
    return sum(items) / len(items)


def test_stamps_differ_in_size_stretch_and_strength_and_are_more_where_it_is_high() -> None:
    low = np.full((400, 600), PLACE + 1500, dtype=np.int32)
    high = np.full((400, 600), PLACE + REACH, dtype=np.int32)
    lower = mountain_relief(Sources(), low, seed=5, column0=0).placements
    higher = mountain_relief(Sources(), high, seed=5, column0=0).placements
    assert len({m.strength for m in higher}) > 20
    assert len({m.across for m in higher}) > 20
    assert len({m.along * 100 // m.across for m in higher}) > 8
    # Vanilla's percentiles: 26 pixels across at the least, about 50 at the median.
    sizes = sorted(m.across // 2 for m in higher)
    assert ACROSS_MIN <= sizes[0] < sizes[len(sizes) // 2] < sizes[-1] <= ACROSS_MIN + ACROSS_RANGE
    assert 38 <= sizes[len(sizes) // 2] <= 65
    # Strength rises a little with height; the number of stamps rises a great deal.
    assert _mean(m.strength for m in higher) > _mean(m.strength for m in lower)
    assert len(higher) > 3 * len(lower)
    assert len(higher) > 0.7 * (400 // STEP) * (600 // STEP)


@dataclass
class BarSources:
    """Three stamps whose crest is a horizontal bar."""

    def layer(self, decal: str, kind: str) -> tuple[LayerFormat, NDArray[np.uint16]]:
        del decal, kind
        a = np.zeros((1024, 1024), dtype=np.uint16)
        a[448:576, 128:896] = 40000
        return LayerFormat(1024, 1024, "<u2"), a


def test_stamps_are_turned_to_run_along_the_range() -> None:
    """A ridge at 30 degrees: each stamp's horizontal crest is turned onto that axis."""
    rows, columns = np.indices((900, 1300))
    across = (rows * 866 - columns * 500) // 1000 - 300
    elevation = np.clip(PLACE + REACH + 3000 - np.abs(across) * 110, 0, None).astype(np.int32)
    placed = mountain_relief(BarSources(), elevation, seed=11, column0=0)
    assert len(placed.placements) > 30
    assert crest_axes(placed.sources) == (0, 0, 0)
    # Axes are in sixteenths of a half turn: 30 degrees falls between 22.5 and 33.75.
    aligned = [m for m in placed.placements if (m.rotation % AXES) in {2, 3}]
    assert len(aligned) >= 0.8 * len(placed.placements)


@pytest.mark.parametrize("axis", [0, 2, 5, 9, 14])
def test_a_rotation_turns_the_crest_onto_its_axis(axis: int) -> None:
    """The sampled crest's principal axis is the one the rotation names."""
    source = BarSources().layer("", "")[1]
    field = MountainRelief((source,), (Mountain(200, 200, 300, 100, 0, axis, 500),))
    sampled = field.sample((0, 0), (400, 400))
    rows, columns = np.nonzero(sampled >= int(sampled.max()) * 45 // 100)
    rows, columns = rows - rows.mean(), columns - columns.mean()
    # Spread along each of the sixteen axes; the crest is where it is greatest.
    spreads = [
        float(
            (
                (columns * math.cos(math.pi * k / AXES) + rows * math.sin(math.pi * k / AXES)) ** 2
            ).sum()
        )
        for k in range(AXES)
    ]
    found = int(np.argmax(spreads))
    assert min((found - axis) % AXES, (axis - found) % AXES) <= 1


@dataclass
class SlotSources:
    """Stamps whose slots are 10 on the left half, 12 on the right and none in a margin."""

    def layer(
        self, decal: str, kind: str
    ) -> tuple[LayerFormat, NDArray[np.uint16] | NDArray[np.uint8]]:
        del decal
        if kind == "height":
            return LayerFormat(1024, 1024, "<u2"), np.full((1024, 1024), 30000, dtype=np.uint16)
        slots = np.full((1024, 1024), NO_MATERIAL, dtype=np.uint8)
        slots[100:900, 100:512] = 12
        slots[100:900, 512:900] = 10
        return LayerFormat(1024, 1024, "u1"), slots


def test_stamp_slots_follow_the_stamp_that_is_highest_and_none_outside_the_stamps() -> None:
    sources = SlotSources()
    field = mountain_relief(sources, np.full((160, 240), 20000, dtype=np.int32), seed=3, column0=0)
    assert len(field.materials) == 3
    window = field.sample_materials((0, 0), (320, 480))
    assert set(np.unique(window).tolist()) <= {10, 12, NO_MATERIAL}
    assert 10 in window
    assert 12 in window
    assert np.array_equal(field.sample((0, 0), (320, 480)), field.stamp((0, 0), (320, 480))[0])
    # Bands and columns agree with the whole window.
    rows = np.concatenate(
        [field.sample_materials((0, top), (min(37, 320 - top), 480)) for top in range(0, 320, 37)]
    )
    columns = np.concatenate(
        [
            field.sample_materials((left, 0), (320, min(41, 480 - left)))
            for left in range(0, 480, 41)
        ],
        axis=1,
    )
    assert np.array_equal(window, rows)
    assert np.array_equal(window, columns)
    # Without material layers no slot is laid.
    bare = MountainRelief(field.sources, field.placements)
    assert np.all(bare.sample_materials((0, 0), (64, 64)) == NO_MATERIAL)


def test_where_stamps_overlap_the_highest_one_decides_the_slot() -> None:
    flat = np.full((64, 64), 30000, dtype=np.uint16)
    low_slot, high_slot = (
        np.full((64, 64), 10, dtype=np.uint8),
        np.full((64, 64), 12, dtype=np.uint8),
    )
    strong = Mountain(100, 100, 90, 90, 0, 0, 900)
    weak = Mountain(100, 100, 90, 90, 1, 0, 100)
    field = MountainRelief((flat, flat), (weak, strong), (high_slot, low_slot))
    heights, slots = field.stamp((40, 40), (120, 120))
    centre = (slice(40, 80), slice(40, 80))
    assert np.all(slots[centre] == 12)  # the strong stamp's, not the lowest slot
    assert int(heights[centre].min()) > 0
    swapped = MountainRelief((flat, flat), (strong, weak), (high_slot, low_slot))
    assert np.array_equal(swapped.stamp((40, 40), (120, 120))[1], slots)
