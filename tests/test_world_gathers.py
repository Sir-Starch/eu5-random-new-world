"""Row-major reads keep exact rolled boundaries, currents and strip ordering."""

# NumPy and intentionally partial map/world fixtures.
# pyright: reportAny=false
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from rnw.eu5_newworld import outside_contacts
from rnw.eu5_seas import VanillaWater, courses_over, current_bands
from rnw.model import CellClass
from tests.reference import world_gathers as reference

if TYPE_CHECKING:
    from rnw.eu5_canvas import Canvas
    from rnw.eu5_map import Eu5Map
    from rnw.newworld import NewWorld


@dataclass
class Rolled:
    roll: int
    col0: int
    shape: tuple[int, int]
    mask: np.ndarray
    removed: np.ndarray

    def rolled(self, labels: np.ndarray, rows: slice) -> np.ndarray:
        return np.roll(labels[rows], self.roll, axis=1)


@pytest.mark.parametrize("roll", [0, 1, 38, -7])
@pytest.mark.parametrize("col0", [0, 25])
@pytest.mark.parametrize("height", [7, 1031])
def test_world_reads_equal_the_rolled_reference(roll: int, col0: int, height: int) -> None:
    rng = np.random.default_rng(194 + roll + col0 + height)
    width, crop, cells = 39, 31, 6
    keys = tuple(f"place_{i}" for i in range(9))
    labels = rng.integers(0, len(keys), (height, width), dtype=np.int32)
    generated = rng.integers(-1, cells, (height, crop), dtype=np.int32)
    canvas = cast(
        "Canvas",
        cast(
            "object",
            Rolled(
                roll,
                col0,
                labels.shape,
                rng.random(generated.shape) > 0.2,
                rng.random(len(keys)) > 0.3,
            ),
        ),
    )
    game = cast("Eu5Map", cast("object", SimpleNamespace(labels=labels, keys=keys)))
    world = cast(
        "NewWorld",
        cast(
            "object",
            SimpleNamespace(
                labels=generated,
                classes=(CellClass.SEA, CellClass.LAND) * 3,
                pixels=np.bincount(generated[generated >= 0], minlength=cells),
            ),
        ),
    )
    waters = {
        key: VanillaWater("ocean" if i % 3 == 0 else "deep_ocean", (i * 2300, i * -1900))
        for i, key in enumerate(keys)
    }
    assert outside_contacts(game, canvas, world, len(keys)) == reference.outside_contacts(
        game, canvas, world, len(keys)
    )
    assert courses_over(game, canvas, world, waters) == reference.courses_over(
        game, canvas, world, waters
    )
    assert np.array_equal(
        current_bands(game, canvas, waters), reference.current_bands(game, canvas, waters)
    )
