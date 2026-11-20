"""A generated land bridge shares the retained terrain and climate at the seam."""

# pyright: reportAny=false

from __future__ import annotations

import numpy as np

from rnw.eu5_biomes import _anchor_biome_votes  # pyright: ignore[reportPrivateUsage]
from rnw.eu5_terrain import _contact_decals  # pyright: ignore[reportPrivateUsage]
from rnw.land_contact import (
    NO_RIM,
    RIM_BASE,
    RIM_REACH,
    RIM_SLOPE,
    ContactTerrain,
    contact_box,
    soften_rim,
)
from rnw.relief import COAST_HEIGHT


def test_rock_and_climate_join_the_retained_side_then_fade() -> None:
    generated = np.zeros((40, 300), dtype=bool)
    generated[:, :265] = True
    interface = np.zeros_like(generated)
    interface[:, 264] = True
    box = contact_box(interface)
    assert box is not None
    retained = ~generated
    height = np.broadcast_to(
        np.linspace(5700, 5950, len(generated), dtype=np.uint16)[:, None], generated.shape
    )
    blend = ContactTerrain(box, height[box]).blend(generated, retained)
    assert blend is not None
    relief = np.full(generated.shape, 20000, dtype=np.int32)
    blend.condition(relief)
    assert np.array_equal(relief[:, 264], height[:, 265])
    assert np.array_equal(relief[retained], height[retained])
    assert np.all(relief[:, 0] == 20000)
    assert np.all(np.abs(np.diff(relief, axis=1)) < 120)

    visible = np.full((80, 600), 30000, dtype=np.int64)
    materials = _contact_decals(blend, visible, first=0, column=0, width=300)
    assert materials is not None
    # A decal sample lies a quarter of a pixel from its pixel's middle; the height slopes 6 a row.
    assert np.all(np.abs(visible[::2, 528] - height[:, 265]) <= 6)
    assert np.all(visible[:, 530:] == 30000)
    assert np.all(materials[:, 530])
    assert not materials[:, :530].any()

    new = np.tile(np.repeat(np.arange(3, dtype=np.int32), 100), (40, 1))[box]
    old = np.ones_like(new)
    votes = blend.biome_votes(new, old, 4)
    assert votes[2] == (1, 1000)
    assert 0 < votes[1][1] < 1000
    assert 0 not in votes
    scores = np.tile(np.array([20, 0], dtype=np.int64), (3, 1))
    _anchor_biome_votes(
        scores,
        ["tropical|forest", "arid|desert"],
        np.arange(3, dtype=np.int64),
        [{}, {"climate": "arid", "vegetation": "desert"}],
        votes,
    )
    assert scores[2].tolist() == [0, 20]
    assert scores[0].tolist() == [20, 0]


def test_the_retained_shore_cut_by_the_generated_sea_is_not_a_wall() -> None:
    """High retained ground that meets water the sea cut rises over the shore like a real coast."""
    generated = np.zeros((60, 200), dtype=bool)
    generated[:, :80] = True
    retained = np.zeros_like(generated)
    retained[10:, 80:] = True  # water above row 10: the sea cut the retained ground there
    interface = np.zeros_like(generated)
    interface[10:, 79] = True
    box = contact_box(interface)
    assert box is not None
    height = np.full(generated.shape, 14000, dtype=np.uint16)
    height[:, 150:] = 7000
    blend = ContactTerrain(box, height[box]).blend(generated, retained)
    assert blend is not None
    rim = blend.fine_rim.astype(np.int64)
    row = 2 * (10 - box[0].start)
    column = 2 * (100 - box[1].start)
    # The first retained row beside the water is capped at the base, the rows after it rise.
    assert COAST_HEIGHT + RIM_BASE <= rim[row, column] <= COAST_HEIGHT + RIM_BASE + RIM_SLOPE
    assert np.all(np.diff(rim[row : row + 2 * RIM_REACH, column]) >= 0)
    assert rim[row + 2 * RIM_REACH + 2, column] == NO_RIM
    assert np.all(rim[: row - 2, column] == NO_RIM)  # the water itself

    heights = np.repeat(np.repeat(height[box].astype(np.int64), 2, axis=0), 2, axis=1)
    cut = soften_rim(heights, rim)
    assert np.all(cut <= heights)
    assert cut[row, column] < COAST_HEIGHT + RIM_BASE + 2500
    assert np.all(np.diff(cut[row : row + 2 * RIM_REACH, column]) >= 0)  # still climbs inland
    gentle = np.full(rim.shape, 6200, dtype=np.int64)
    assert np.array_equal(soften_rim(gentle, rim), gentle)
    far = np.s_[row + 2 * RIM_REACH + 2 :, column]
    assert np.array_equal(cut[far], heights[far])

    # Installed water (low, as the sea floor is) leaves the retained shore as it was.
    low = height.copy()
    low[:10] = 2234
    plain = ContactTerrain(box, low[box]).blend(generated, retained)
    assert plain is not None
    assert np.all(plain.fine_rim == NO_RIM)
    assert np.array_equal(plain.height[retained[box]], low[box][retained[box]])
