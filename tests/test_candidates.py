from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw import landcache
from rnw.app import candidates
from rnw.eu5_canvas import Canvas
from rnw.newworld import land_stage
from rnw.progress import Cancelled, Progress, active
from rnw.settings import PRESETS
from tests.test_newworld import SMALL

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class MapStub:
    labels: NDArray[np.int32]
    inputs: tuple[str, ...] = ("map.png 1 0",)
    keys: tuple[str, ...] = ()


def test_sketches_use_the_worlds_land_stage_and_leave_no_mod(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    domain = np.ones((160, 192), dtype=np.bool_)
    canvas = Canvas(
        0, 0, domain, (160, 192), np.zeros(1, dtype=np.bool_), np.zeros(1, dtype=np.bool_)
    )

    def load(_root: Path) -> MapStub:
        return MapStub(np.zeros((160, 192), dtype=np.int32))

    def select(_map: MapStub, _band: int, *, expanded: bool) -> Canvas:
        assert expanded
        return canvas

    monkeypatch.setattr(candidates, "load_map", load)
    monkeypatch.setattr(landcache, "select_canvas", select)
    settings = replace(PRESETS["continents"], new_world=SMALL)
    expected, _sea, lakes, _height = land_stage(domain.copy(), 42, SMALL)
    found = candidates.sketch(tmp_path, settings, [42, 91])
    tile = found[0].picture
    assert found[0].seed == 42
    expected_picture = np.empty_like(tile)
    expected_picture[:] = candidates.SEA
    expected_picture[lakes[::8, ::8]] = candidates.LAKE
    expected_picture[expected[::8, ::8]] = candidates.LAND
    assert np.array_equal(tile, expected_picture)
    assert not np.array_equal(tile, found[1].picture)
    assert not list(tmp_path.iterdir())
    assert candidates.contact_sheet(found).ndim == 3


@pytest.mark.parametrize("count", [0, -1, 13])
def test_a_candidate_batch_has_a_bounded_size(count: int) -> None:
    with pytest.raises(candidates.CandidateError):
        _ = candidates.roll(count)


def test_sketching_respects_cancellation(tmp_path: Path) -> None:
    progress = Progress()
    progress.cancel()
    with active(progress), pytest.raises(Cancelled):
        _ = candidates.sketch(tmp_path, PRESETS["continents"], [42])


def test_sketches_made_beside_each_other_equal_one_after_the_other_and_keep_their_land(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sketches do not depend on how many are made at once, and each one's land stage is
    kept for the world made from it."""
    domain = np.ones((160, 192), dtype=np.bool_)
    canvas = Canvas(
        0, 0, domain, (160, 192), np.zeros(1, dtype=np.bool_), np.zeros(1, dtype=np.bool_)
    )

    def load(_root: Path) -> MapStub:
        return MapStub(np.zeros((1, 1), dtype=np.int32))

    def select(_map: MapStub, _band: int, *, expanded: bool) -> Canvas:
        assert expanded
        return canvas

    monkeypatch.setattr(candidates, "load_map", load)
    monkeypatch.setattr(landcache, "select_canvas", select)
    settings = replace(PRESETS["continents"], new_world=SMALL)
    seeds = [3, 5, 8, 13]
    monkeypatch.setenv("RNW_THREADS", "1")
    alone = candidates.sketch(tmp_path, settings, seeds)
    monkeypatch.setenv("RNW_THREADS", "4")
    cache = tmp_path / "cache"
    beside = candidates.sketch(tmp_path, settings, seeds, cache=cache)
    assert [item.seed for item in beside] == seeds
    for first, second in zip(alone, beside, strict=True):
        assert np.array_equal(first.picture, second.picture)
        assert first.land_permille == second.land_permille
    digest = landcache.domain_digest(domain)
    for seed in seeds:
        kept = landcache.read_stage(cache, landcache.stage_key(digest, seed, SMALL), domain.shape)
        assert kept is not None
        expected = land_stage(domain.copy(), seed, SMALL)[:3]
        assert all(np.array_equal(a, b) for a, b in zip(kept, expected, strict=True))


def test_a_composed_sketch_paints_each_continent_where_the_world_puts_it() -> None:
    """A continent's finished coasts land on the map's grid of eighths at its own place, across
    the map's seam too; the rest of the map keeps the game's colours."""
    from rnw.continent_domains import CONTINENTS, Domain  # noqa: PLC0415 - this test alone
    from rnw.newworld import FinishedLand  # noqa: PLC0415 - this test alone

    width = 64
    picture = np.zeros((4, width // 8, 3), dtype=np.uint8)
    picture[:] = candidates.KEPT_SEA
    mask = np.ones((20, 24), dtype=np.bool_)
    land = np.zeros_like(mask)
    land[:, 13:] = True  # the columns from 56 + 13 = 69, that is 5 past the seam
    lakes = np.zeros_like(mask)
    lakes[19, 0] = True
    domain = Domain(CONTINENTS["africa"], 56, width, mask, mask.copy(), first_row=5)
    coasts = FinishedLand(mask, mask, land, ~land & ~lakes, lakes, (), (), None)
    candidates._paint(picture, domain, coasts)  # pyright: ignore[reportPrivateUsage]
    # Rows 5..24 of the map hold the grid rows 8, 16 and 24, that is picture rows 1 to 3.
    assert _all(picture[0:1], candidates.KEPT_SEA)
    # Map column 56 (local 0) is sea; 64 (local 8, column 0 after the seam) sea; 72 (local 16)
    # land.
    assert _all(picture[1:3, 7], candidates.GENERATED_SEA)
    # Local row 19 is map row 24, picture row 3: the lake at its first column.
    assert _all(picture[3:4, 7], candidates.GENERATED_LAKE)
    assert _all(picture[1:, 0], candidates.GENERATED_SEA)
    assert _all(picture[1:, 1], candidates.GENERATED_LAND)
    assert _all(picture[1:, 3:7], candidates.KEPT_SEA)


def _all(pixels: NDArray[np.uint8], colour: tuple[int, int, int]) -> bool:
    """Whether every pixel of ``pixels`` has ``colour``."""
    same: NDArray[np.bool_] = np.equal(pixels, np.array(colour, dtype=np.uint8))
    return bool(same.all())
