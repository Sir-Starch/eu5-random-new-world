"""A generated land bridge shares the retained terrain and climate at the seam."""

# pyright: reportAny=false

from __future__ import annotations

import numpy as np

from rnw.eu5_biomes import _anchor_biome_votes  # pyright: ignore[reportPrivateUsage]
from rnw.eu5_terrain import _contact_decals  # pyright: ignore[reportPrivateUsage]
from rnw.land_contact import ContactTerrain, contact_box


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
