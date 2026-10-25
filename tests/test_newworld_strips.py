"""World statistics and relief do not depend on how the raster is cut into strips."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from functools import partial

import numpy as np
import pytest

from rnw import newworld
from rnw.fields import upsample
from tests.reference import newworld as reference_newworld


@pytest.mark.parametrize("strip", [1, 5, 64, 100_000])
def test_cell_sums_equal_the_whole_raster_sums(monkeypatch: pytest.MonkeyPatch, strip: int) -> None:
    """Pixels, centre sums and elevation sums per cell agree for any strip height."""
    generator = np.random.default_rng(strip)
    shape = (83, 61)
    labels = (
        upsample(generator.integers(0, 9, (shape[0] // 12 + 2, shape[1] // 12 + 2)), 12, shape) % 9
    ).astype(np.int32)
    labels[:4, :7] = -1
    elevation = generator.integers(-30_000, 60_000, shape, dtype=np.int32)
    monkeypatch.setattr(newworld, "STRIP_ROWS", strip)
    native = newworld._cell_sums(labels, elevation, 11)  # pyright: ignore[reportPrivateUsage]
    expected = reference_newworld.cell_sums(labels, elevation, 11)
    for ours, theirs in zip(native, expected, strict=True):
        assert np.array_equal(ours, theirs)
    assert int(native[0][9]) == 0


def _domains() -> list[tuple[np.ndarray, int | None]]:
    """A plain domain with a seam, one with a protected islet and a thin arm, a ragged one."""
    plain = np.ones((140, 330), dtype=bool)
    islet = np.ones((120, 260), dtype=bool)
    islet[50:62, 100:112] = False
    islet[:20, 200:] = False
    ragged = np.zeros((150, 300), dtype=bool)
    ragged[10:140, 15:200] = True
    ragged[60:80, 200:290] = True
    return [(plain, 170), (islet, None), (ragged, None)]


@pytest.mark.parametrize("strip", [8, 24, 1024])
@pytest.mark.parametrize("domain_index", [0, 1, 2])
def test_the_strip_coast_model_equals_the_whole_raster_one(
    monkeypatch: pytest.MonkeyPatch, strip: int, domain_index: int
) -> None:
    """Land, ocean, lakes and elevation agree: edge offset, penalty and land budget."""
    from tests.test_newworld import SMALL  # noqa: PLC0415 - the settings of the world tests

    domain, seam = _domains()[domain_index]
    monkeypatch.setattr(newworld, "STRIP_ROWS", strip)
    native = newworld.land_stage(domain.copy(), 7 + domain_index, SMALL, seam)
    expected = reference_newworld.land_model(domain.copy(), 7 + domain_index, SMALL, seam)
    for ours, theirs in zip(native, expected, strict=True):
        assert np.array_equal(ours, theirs)
    assert native[0].any()
    assert (~native[0] & domain).any()


def test_the_threshold_counts_like_a_partition() -> None:
    """The counted threshold is the partitioned one for any share, and a zero share is refused."""
    generator = np.random.default_rng(5)
    values = generator.integers(-3000, 3000, (50, 40), dtype=np.int32)
    mask = generator.random(values.shape) < 0.7
    chosen = values[mask]
    for permille in (1, 137, 450, 999, 1000):
        keep = chosen.size * permille // 1000
        expected = int(np.partition(chosen, chosen.size - keep)[chosen.size - keep])
        assert newworld._threshold(values, mask, permille) == expected  # pyright: ignore[reportPrivateUsage]
    with pytest.raises(ValueError, match="keeps no pixel"):
        _ = newworld._threshold(values, mask, 0)  # pyright: ignore[reportPrivateUsage]


def test_the_land_field_has_no_fixed_high_variance_positions() -> None:
    """Changing seeds moves lattice nodes, instead of favouring the same map pixels.

    With a fixed origin a node has about four times the variance of a cell's centre.
    At a positive sea level that favours land at the same nodes in every world.
    """
    samples = np.array(
        [
            newworld._field(  # pyright: ignore[reportPrivateUsage]
                seed,
                "new_world_elevation",
                shape=(33, 33),
                period=32,
                octaves=1,
                persistence_permille=500,
            )[[0, 16, 32], [0, 16, 32]]
            for seed in range(256)
        ]
    )
    variances = np.var(samples, axis=0)
    assert variances.max() / variances.min() < 1.5


@pytest.mark.parametrize("strip", [1, 7, 64])
def test_the_seeded_field_origin_is_shared_by_all_strips(
    monkeypatch: pytest.MonkeyPatch, strip: int
) -> None:
    """The noise stays continuous at strip boundaries and at the world-map seam."""
    field = partial(
        newworld._field,  # pyright: ignore[reportPrivateUsage]
        42,
        "new_world_elevation",
        shape=(79, 131),
        period=53,
        octaves=4,
        persistence_permille=470,
    )
    monkeypatch.setattr(newworld, "STRIP_ROWS", 1000)
    whole = field()
    monkeypatch.setattr(newworld, "STRIP_ROWS", strip)
    actual = field()
    assert np.array_equal(actual, whole)
