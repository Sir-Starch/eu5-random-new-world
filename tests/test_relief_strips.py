"""The relief of a land mask is the same for any strip height and thread count."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw import relief
from rnw.fields import upsample, warped_noise
from tests.reference import relief as reference_relief

if TYPE_CHECKING:
    from collections.abc import Callable


def _fixed(value: int) -> Callable[..., int]:
    """A stand-in for a sizing function that always answers ``value``."""

    def answer(*_arguments: object, **_options: object) -> int:
        return value

    return answer


def _land(seed: int, shape: tuple[int, int]) -> np.ndarray:
    generator = np.random.default_rng(seed)
    coarse = generator.integers(0, 1000, (shape[0] // 50 + 2, shape[1] // 50 + 2))
    land = upsample(coarse, 50, shape) > 420
    land[:4] = False
    land[:, :4] = False
    return land


@pytest.mark.parametrize(("seed", "shape"), [(1, (203, 317)), (2, (352, 130)), (3, (97, 61))])
@pytest.mark.parametrize("window", [1, 150, 400])
def test_strips_of_any_height_equal_the_whole_raster(
    monkeypatch: pytest.MonkeyPatch, seed: int, shape: tuple[int, int], window: int
) -> None:
    """Fields, the foothill blur and the inland ramp agree across strip edges."""
    land = _land(seed, shape)
    monkeypatch.setattr(relief, "band_rows", _fixed(max(relief.STRIP_FLOOR, window)))
    monkeypatch.setattr(relief, "worker_count", _fixed(3))
    result = relief.generate_relief(land, seed=seed)
    assert np.array_equal(result, reference_relief.generate_relief(land, seed=seed))
    assert result.dtype == np.int32
    assert np.unique(result[land]).size > 50
    assert int(result.max()) > relief.COAST_HEIGHT


def test_a_window_must_start_on_the_noise_lattice() -> None:
    """Windows that do not hold whole lattice cells are refused, not shifted."""
    with pytest.raises(ValueError, match="multiple of the step"):
        _ = warped_noise(3, (20, 20), step=8, period=32, octaves=1, warp_px=4, row0=4)
