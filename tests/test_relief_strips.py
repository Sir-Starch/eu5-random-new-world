"""The relief of a land mask is the same for any strip height and thread count."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw import relief
from rnw.fields import PERMILLE, block_mean, upsample, warped_noise
from rnw.topology import label_components
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


def _with_lake(seed: int, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """Land with a round lake cut out of it, and the lake."""
    land = _land(seed, shape)
    rows, columns = np.indices(shape)
    lake = land & ((rows - shape[0] // 2) ** 2 + (columns - shape[1] // 2) ** 2 < 14**2)
    return land & ~lake, lake


@pytest.mark.parametrize("window", [1, 150])
def test_strips_equal_the_whole_raster_with_lakes(
    monkeypatch: pytest.MonkeyPatch, window: int
) -> None:
    land, lake = _with_lake(4, (203, 317))
    assert lake.any()
    monkeypatch.setattr(relief, "band_rows", _fixed(max(relief.STRIP_FLOOR, window)))
    monkeypatch.setattr(relief, "worker_count", _fixed(3))
    result = relief.generate_relief(land, seed=4, lakes=lake)
    assert np.array_equal(result, reference_relief.generate_relief(land, seed=4, lakes=lake))


@pytest.mark.parametrize("window", [1, 150])
def test_the_hill_spread_is_the_same_in_any_strip_and_leaves_the_relief_alone(
    monkeypatch: pytest.MonkeyPatch, window: int
) -> None:
    land, lake = _with_lake(4, (203, 317))
    monkeypatch.setattr(relief, "worker_count", _fixed(3))
    monkeypatch.setattr(relief, "band_rows", _fixed(10_000))
    whole = np.zeros(land.shape, dtype=np.int16)
    _ = relief.generate_relief(land, seed=4, lakes=lake, margins=True, spread=whole)
    monkeypatch.setattr(relief, "band_rows", _fixed(max(relief.STRIP_FLOOR, window)))
    spread = np.ones(land.shape, dtype=np.int16)
    result = relief.generate_relief(land, seed=4, lakes=lake, margins=True, spread=spread)
    assert np.array_equal(result, relief.generate_relief(land, seed=4, lakes=lake, margins=True))
    assert np.array_equal(spread, whole)
    assert np.all(spread[~land] == 0)
    assert np.any(spread[land] > 200)
    assert np.any(spread[land] < -200)
    with pytest.raises(ValueError, match="land's shape"):
        _ = relief.generate_relief(land, seed=4, spread=np.zeros((3, 3), dtype=np.int16))


def test_a_lake_does_not_raise_a_cone_of_land_round_it() -> None:
    """The inland rise follows the distance to the sea: round a lake the ground is level."""
    shape = (420, 420)
    land = np.zeros(shape, dtype=bool)
    land[20:400, 20:400] = True
    rows, columns = np.indices(shape)
    distance = np.hypot(rows - 210, columns - 210)
    lake = land & (distance < 20)
    land &= ~lake
    ring = (distance > 28) & (distance < 36)
    cone = relief.generate_relief(land, seed=9)
    level = relief.generate_relief(land, seed=9, lakes=lake)
    assert np.all(level[lake] == 0)
    # Without the lake counted as land the ring stands a pit's wall below the open ground; with it,
    # the ring is as high as ground at the same distance from the sea.
    assert level[ring].mean() > cone[ring].mean() + 500


def _painted(shape: tuple[int, int]) -> relief.ReliefHints:
    """Mountains, highlands and lowlands marked on three bands of the raster."""
    rows, columns = -(-shape[0] // relief.HINT_STEP) + 1, -(-shape[1] // relief.HINT_STEP) + 1
    grids = [np.zeros((rows, columns), dtype=np.int32) for _ in range(4)]
    grids[0][rows // 5 : rows // 5 + 6, 3:-3] = 1000
    grids[3][max(0, rows // 5 - 4) : rows // 5 + 10, 1:-1] = 400
    grids[1][rows // 2 : rows // 2 + 7, 3:-3] = 1000
    grids[2][-9:-3, 3:-3] = 1000
    return relief.ReliefHints(grids[0], grids[1], grids[2], grids[3])


@pytest.mark.parametrize("window", [1, 150, 400])
def test_strips_equal_the_whole_raster_with_painted_hints(
    monkeypatch: pytest.MonkeyPatch, window: int
) -> None:
    """Painted mountains, highlands and lowlands do not depend on where a strip begins."""
    land = _land(5, (203, 317))
    hints = _painted(land.shape)
    monkeypatch.setattr(relief, "band_rows", _fixed(max(relief.STRIP_FLOOR, 400)))
    monkeypatch.setattr(relief, "worker_count", _fixed(1))
    whole = relief.generate_relief(land, seed=5, hints=hints)
    monkeypatch.setattr(relief, "band_rows", _fixed(max(relief.STRIP_FLOOR, window)))
    monkeypatch.setattr(relief, "worker_count", _fixed(3))
    assert np.array_equal(relief.generate_relief(land, seed=5, hints=hints), whole)
    assert not np.array_equal(whole, relief.generate_relief(land, seed=5))


@pytest.mark.parametrize("seed", [0, 3])
def test_a_landmass_measures_its_tilt_from_its_own_active_coasts_without_breaks(seed: int) -> None:
    generator = np.random.default_rng(seed)
    coarse = generator.integers(0, 1000, (960 // 60 + 2, 1440 // 60 + 2))
    land = upsample(coarse, 60, (960, 1440)) > 520
    step = relief.MARGIN_STEP
    grid = relief._margin_grid(land, seed, 256)[:-1, :-1]  # pyright: ignore[reportPrivateUsage]
    cells = block_mean(land.astype(np.int64) * PERMILLE, step) >= PERMILLE // 2
    parts = label_components(cells.astype(np.int32))
    # A distance to a fixed set of coasts changes by at most a cell between neighbouring cells.
    for here, there in (
        ((slice(None), slice(1, None)), (slice(None), slice(None, -1))),
        ((slice(1, None), slice(None)), (slice(None, -1), slice(None))),
    ):
        same = cells[here] & cells[there] & (parts[here] == parts[there])
        assert np.abs(grid[here] - grid[there])[same].max(initial=0) <= step * 8 + 8
