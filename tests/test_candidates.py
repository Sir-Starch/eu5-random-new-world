from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import numpy as np
import pytest

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

    def select(_map: MapStub, _band: int) -> Canvas:
        return canvas

    monkeypatch.setattr(candidates, "load_map", load)
    monkeypatch.setattr(candidates, "select_canvas", select)
    settings = replace(PRESETS["continents"], new_world=SMALL)
    expected, _sea, lakes, _height = land_stage(domain.copy(), 42, SMALL, 0)
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
