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
    assert np.array_equal(visible[::2, 528], height[:, 265])
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
    """High retained ground that meets water rises over the shore like a real coast."""
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
    rim = blend.rim
    row = 10 - box[0].start
    column = 100 - box[1].start
    # Row 10 is the first retained row beside water: the cap is its base, then rises a step a row.
    assert rim[row, column] == COAST_HEIGHT + RIM_BASE
    assert rim[row + 3, column] == COAST_HEIGHT + RIM_BASE + 3 * RIM_SLOPE
    assert rim[row + RIM_REACH + 1, column] == NO_RIM
    assert np.all(rim[~retained[box]] == NO_RIM)

    cut = soften_rim(height[box].astype(np.int64), rim)
    assert np.all(cut <= height[box])
    assert np.all(cut[retained[box]] >= np.minimum(height[box][retained[box]], rim[retained[box]]))
    assert cut[row, column] < COAST_HEIGHT + RIM_BASE + 2500
    assert np.all(np.diff(cut[row:, column]) >= 0)  # still climbs inland
    gentle = np.full(rim.shape, 6200, dtype=np.int64)
    assert np.array_equal(soften_rim(gentle, rim), gentle)
    far = np.s_[row + RIM_REACH + 2 :, column]
    assert np.array_equal(cut[far], height[box][far])
