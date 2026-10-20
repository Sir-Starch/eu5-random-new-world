"""A decal rebuilt in bands is the same decal for every band size and thread count."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pytest

from rnw.eu5_slots import SlotTables
from rnw.eu5_terrain import (
    BAND_HALO,
    CAP_REACH,
    Decal,
    TerrainInputs,
    TerrainRangeError,
    _rebuild_decal,  # pyright: ignore[reportPrivateUsage]
    _write_where,  # pyright: ignore[reportPrivateUsage]
)
from rnw.fields import upsample
from rnw.terrain_tiles import LayerFormat

ROWS, COLUMNS = 340, 290
DECAL = Decal("heightmap_x_16", 25, 20, 290, 250)


@dataclass(eq=False)
class FakeStore:
    """The two methods of ``DecalStore`` that ``_rebuild_decal`` reads, with synthetic layers."""

    game_dir: Path = Path()
    layers: dict[str, tuple[LayerFormat, np.ndarray]] = field(default_factory=dict)

    def layer(self, _decal: str, kind: str) -> tuple[LayerFormat, np.ndarray]:
        """Vanilla layers: a ramp of heights and stripes of materials."""
        if kind not in self.layers:
            rows, columns = DECAL.rows * 2, DECAL.columns * 2
            ramp = (np.arange(rows * columns, dtype=np.int64) % 60_000).reshape(rows, columns)
            if kind == "height":
                self.layers[kind] = (LayerFormat(columns, rows, "<u2"), ramp.astype(np.uint16))
            else:
                self.layers[kind] = (LayerFormat(columns, rows, "u1"), (ramp % 16).astype(np.uint8))
        return self.layers[kind]

    def paths(self, decal: str, kind: str) -> tuple[str, Path, Path]:
        """Stem only; the files are not read."""
        return f"in_game/{decal}_{kind}", Path(), Path()


def _world(seed: int) -> tuple[TerrainInputs, SlotTables]:
    """One big continent (inland distances beyond the coast cap), islands, lakes and rivers."""
    generator = np.random.default_rng(seed)
    shape = (ROWS, COLUMNS)
    coarse = generator.random((ROWS // 40 + 2, COLUMNS // 40 + 2))
    land = upsample((coarse * 1000).astype(np.int64), 40, shape) > 430
    land[20:320, 30:250] = True  # a continent wider than twice the coast cap
    land[:, :8] = False
    land[:8] = False
    codes = np.where(land, 1, 0).astype(np.int8)
    codes[:6] = -1
    codes[:, -9:] = -1
    water = ~land
    labels = (
        upsample(generator.integers(0, 9, (ROWS // 30 + 2, COLUMNS // 30 + 2)), 30, shape) % 9
    ).astype(np.int32)
    relief = upsample(
        generator.integers(40_000, 52_000, (ROWS // 25 + 2, COLUMNS // 25 + 2)), 25, shape
    )
    rivers = (generator.random(shape) < 0.004) & land
    inputs = TerrainInputs(
        codes=codes,
        vanilla_water=water,
        relief=lambda rows, columns: relief[rows, columns].astype(np.int32),
        labels=labels,
        rivers=rivers,
    )
    count = 9
    tables = SlotTables(
        water=np.array([False, False, True, False, False, False, True, False, False]),
        coast_slot=generator.integers(0, 5, count, dtype=np.int64),
        topography=generator.integers(0, 4, count, dtype=np.int64),
        vegetation=generator.integers(0, 4, count, dtype=np.int64),
        climate=generator.integers(0, 3, count, dtype=np.int64),
        level_one=generator.integers(0, 500, count, dtype=np.int64),
        level_two=generator.integers(0, 400, count, dtype=np.int64),
        materials=generator.integers(8, 18, count, dtype=np.int64),
    )
    return inputs, tables


def _rebuild(seed: int, band: int, threads: int) -> tuple[dict[str, bytes], np.ndarray]:
    inputs, tables = _world(seed)
    with ThreadPoolExecutor(max_workers=threads) as pool:
        return _rebuild_decal(
            DECAL,
            FakeStore(),  # pyright: ignore[reportArgumentType]
            inputs,
            tables,
            seed=seed,
            pool=pool,
            band=band,
        )


@pytest.mark.parametrize("seed", [3, 11])
def test_every_band_size_and_thread_count_builds_the_same_decal(seed: int) -> None:
    """Bands of 17 and 130 rows, one thread or three, and one band for the decal agree."""
    whole_files, whole_image = _rebuild(seed, DECAL.rows, 1)
    assert len(whole_files) == 4
    assert np.unique(whole_image).size > 6
    for band, threads in ((17, 1), (17, 3), (130, 2), (DECAL.rows - 1, 2)):
        files, image = _rebuild(seed, band, threads)
        assert np.array_equal(image, whole_image), (band, threads)
        assert files == whole_files, (band, threads)


def test_the_halo_covers_the_coast_cap() -> None:
    """The cap reach is what sets the halo; a change of either must change the other."""
    assert BAND_HALO >= CAP_REACH + 2


def test_samples_that_do_not_fit_a_layer_fail_loudly() -> None:
    """A height above 16 bits or a negative one is an error, not a wrapped value."""
    target = np.zeros((2, 2), dtype=np.uint16)
    mask = np.ones((2, 2), dtype=bool)
    _write_where(target, np.full((2, 2), 65_535, dtype=np.int64), mask)
    assert target[0, 0] == 65_535
    with pytest.raises(TerrainRangeError, match="do not fit"):
        _write_where(target, np.full((2, 2), 65_536, dtype=np.int64), mask)
    with pytest.raises(TerrainRangeError, match="do not fit"):
        _write_where(target, np.full((2, 2), -1, dtype=np.int64), mask)
    _write_where(target, np.full((2, 2), -1, dtype=np.int64), ~mask)  # masked out: not checked
