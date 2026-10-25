"""A decal rebuilt in bands is the same decal for every band size and thread count."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw.eu5_mountains import Mountain, MountainRelief
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
from rnw.terrain_tiles import LayerFormat, TileFormatError, parse_info, read_level0, write_layer

if TYPE_CHECKING:
    from numpy.typing import NDArray

ROWS, COLUMNS = 340, 290
DECAL = Decal("heightmap_x_16", 25, 20, 290, 250)


@dataclass(eq=False)
class FakeStore:
    """The two methods of ``DecalStore`` that ``_rebuild_decal`` reads, with synthetic layers."""

    game_dir: Path = Path()
    decal: Decal = DECAL
    layers: dict[str, tuple[LayerFormat, np.ndarray]] = field(default_factory=dict)

    def layer(self, _decal: str, kind: str) -> tuple[LayerFormat, np.ndarray]:
        """Vanilla layers: a ramp of heights and stripes of materials."""
        if kind not in self.layers:
            rows, columns = self.decal.rows * 2, self.decal.columns * 2
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
        relief=lambda rows, columns: relief[rows][
            :, np.arange(columns.start, columns.stop) % COLUMNS
        ].astype(np.int32),
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


@pytest.mark.parametrize("band", [17, 170])
@pytest.mark.parametrize("mountains", [False, True])
def test_wrapped_terrain_equals_one_continuous_continent(band: int, *, mountains: bool) -> None:
    """Separate edge decals and a decal spanning the noise cut reproduce the unrolled land.

    A continent with relief, a river and location borders is computed once in the
    middle of a map, then moved onto the display seam. Decoded heights and material
    samples must agree exactly, including the shoreline on either side of the seam.
    """
    height, width, roll = 180, 400, 200
    rows, columns = np.indices((height, width))
    land = (rows >= 20) & (rows < 160) & (columns >= 100) & (columns < 300)
    codes = land.astype(np.int8)
    labels = np.where(land, np.where(columns < 200, 1, 3), 0).astype(np.int32)
    relief = np.where(land, 12000 + columns * 19 + rows * 11, 0).astype(np.int32)
    rivers = land & (rows == 80)
    _, original_tables = _world(7)
    water = np.zeros(9, dtype=bool)
    water[0] = True
    tables = replace(original_tables, water=water)

    def inputs(shift: int) -> TerrainInputs:
        moved_relief = np.roll(relief, -shift, axis=1)

        def sample(row_slice: slice, column_slice: slice) -> np.ndarray:
            columns: NDArray[np.int64] = (
                np.arange(column_slice.start, column_slice.stop, dtype=np.int64) % width
            )
            return moved_relief[row_slice][:, columns]

        return TerrainInputs(
            codes=np.roll(codes, -shift, axis=1),
            vanilla_water=np.roll(~land, -shift, axis=1),
            relief=sample,
            labels=np.roll(labels, -shift, axis=1),
            rivers=np.roll(rivers, -shift, axis=1),
            noise_roll=shift,
            mountains=MountainRelief(
                (np.full((64, 64), 40000, dtype=np.uint16),),
                (Mountain(140, 400, 112, 0, 1), Mountain(210, 430, 144, 0, 3)),
            )
            if mountains
            else None,
        )

    def render(decal: Decal, source: TerrainInputs) -> tuple[np.ndarray, np.ndarray]:
        with ThreadPoolExecutor(max_workers=2) as pool:
            files, materials = _rebuild_decal(
                decal,
                FakeStore(decal=decal),  # pyright: ignore[reportArgumentType]
                source,
                tables,
                seed=42,
                pool=pool,
                band=band,
            )
        layer, spans = parse_info(files[f"in_game/{decal.name}_height.info"].decode())
        heights = read_level0(layer, spans, files[f"in_game/{decal.name}_height.bin"])
        return heights, materials

    reference = render(Decal("continuous", 5, 0, 170, width), inputs(0))
    if mountains:
        bare = render(Decal("continuous", 5, 0, 170, width), replace(inputs(0), mountains=None))
        assert np.any(reference[0] > bare[0])
        assert np.all(reference[0] >= bare[0])
        river_row = (80 - 5) * 2
        assert np.array_equal(
            reference[0][river_row : river_row + 2], bare[0][river_row : river_row + 2]
        )
        assert np.array_equal(reference[1], bare[1])
    wrapped = inputs(roll)
    # One edge decal on each side, and a single decal that crosses the outside cut.
    left = render(Decal("left", 5, 0, 170, 60), wrapped)
    right = render(Decal("right", 5, width - 60, 170, 60), wrapped)
    whole = render(Decal("whole", 5, 0, 170, width), wrapped)
    for index in (0, 1):
        expected = np.roll(reference[index], -roll * 2, axis=1)
        assert np.array_equal(left[index], expected[:, :120])
        assert np.array_equal(right[index], expected[:, -120:])
        assert np.array_equal(whole[index], expected)


@dataclass(eq=False)
class EdgeStore:
    """Two independent source tiles with distinguishable samples at both edges."""

    map_shape: tuple[int, int] = (ROWS, COLUMNS)
    decals: tuple[Decal, ...] = (
        Decal("heightmap_1_16", 0, 0, ROWS, COLUMNS // 2),
        Decal("heightmap_2_16", 0, COLUMNS // 2, ROWS, COLUMNS // 2),
    )

    def layer(self, name: str, kind: str) -> tuple[LayerFormat, np.ndarray]:
        decal = next(d for d in self.decals if d.name == name)
        r, c = np.indices((ROWS * 2, decal.columns * 2))
        c += decal.column0 * 2
        values = r * 17 + c * 29
        image = (
            (values % 60_000).astype(np.uint16)
            if kind == "height"
            else (values % 16).astype(np.uint8)
        )
        return LayerFormat(image.shape[1], image.shape[0], image.dtype.str), image

    def paths(self, name: str, kind: str) -> tuple[str, Path, Path]:
        return f"in_game/{name}_{kind}", Path(), Path()


def test_layer_header_must_match_its_samples() -> None:
    """A changed footprint cannot silently write stale source dimensions."""
    with pytest.raises(TileFormatError, match="disagree with declared"):
        _ = write_layer(np.zeros((12, 24), dtype=np.uint16), LayerFormat(20, 12, "<u2"))


@pytest.mark.parametrize("roll", [0, 2, COLUMNS - 2])
@pytest.mark.parametrize(("band", "threads"), [(13, 1), (500, 3)])
def test_padded_sources_equal_periodic_independently_rebuilt_tiles(
    monkeypatch: pytest.MonkeyPatch, roll: int, band: int, threads: int
) -> None:
    """Every interior and halo sample agrees, including a noise cut inside the padding."""
    from rnw import eu5_terrain  # noqa: PLC0415

    monkeypatch.setattr(eu5_terrain, "WRAP_PADDING", 4)
    store = EdgeStore()
    inputs, tables = _world(11)
    inputs = replace(inputs, noise_roll=roll)
    reference: dict[str, list[np.ndarray]] = {"height": [], "materials": []}
    padded: dict[str, list[np.ndarray]] = {"height": [], "materials": []}
    with ThreadPoolExecutor(max_workers=threads) as pool:
        for decal in store.decals:
            for wrapped, result in ((False, reference), (True, padded)):
                plan = eu5_terrain._padded_decal(decal, COLUMNS) if wrapped else decal  # pyright: ignore[reportPrivateUsage]
                files, _ = _rebuild_decal(
                    plan,
                    store,  # pyright: ignore[reportArgumentType]
                    inputs,
                    tables,
                    seed=11,
                    pool=pool,
                    band=band,
                )
                for kind in reference:
                    stem = f"in_game/{decal.name}_{kind}"
                    layer, spans = parse_info(files[f"{stem}.info"].decode())
                    result[kind].append(read_level0(layer, spans, files[f"{stem}.bin"]))
    for kind, images in reference.items():
        first, last = images
        assert np.array_equal(padded[kind][0], np.concatenate([last[:, -8:], first], axis=1))
        assert np.array_equal(padded[kind][1], np.concatenate([last, first[:, :8]], axis=1))
