"""The area a New World fills, as a picture to draw on: cut from the canvas, kept in the cache."""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import io
from typing import TYPE_CHECKING

import numpy as np
import pytest
from PIL import Image

from rnw import landarea, landcache, landmask
from rnw.app import service
from rnw.contract import FileFingerprint
from rnw.eu5_canvas import Canvas
from rnw.islands import Footprint
from rnw.settings import PRESETS
from tests.fakes import build_game

if TYPE_CHECKING:
    from pathlib import Path


def _canvas() -> Canvas:
    mask = np.zeros((96, 128), dtype=np.bool_)
    mask[8:88, 8:120] = True
    americas = np.zeros_like(mask)
    americas[30:60, 40:80] = True
    rows, columns = np.meshgrid(np.arange(60, 72), np.arange(100, 112), indexing="ij")
    island = Footprint(rows.ravel().astype(np.int32), columns.ravel().astype(np.int32))
    return Canvas(
        0,
        0,
        mask,
        (96, 128),
        np.zeros(1, dtype=np.bool_),
        np.zeros(1, dtype=np.bool_),
        footprints=(island,),
        template=americas,
    )


def test_the_layers_are_cut_every_fourth_pixel_of_the_canvas() -> None:
    """Area, Americas and island groups at a quarter of the size; any step is a cut of it."""
    canvas = _canvas()
    area = landarea.from_canvas(canvas)
    assert area.shape == (96, 128)
    assert area.picture_shape == (24, 32)
    assert np.array_equal(area.area, canvas.mask[::4, ::4])
    assert canvas.template is not None
    assert np.array_equal(area.americas, canvas.template[::4, ::4])
    assert area.islands[15, 25]
    assert area.islands.sum() == 9
    coarse = area.at(8)
    assert coarse.picture_shape == (12, 16)
    assert np.array_equal(coarse.area, canvas.mask[::8, ::8])
    with pytest.raises(ValueError, match="multiples of 4"):
        _ = area.at(6)


def test_the_template_picture_is_grey_and_draws_no_land_by_itself() -> None:
    """Outside, area, island groups and the Americas are four greys, all sea to the reader."""
    area = landarea.from_canvas(_canvas())
    picture = area.picture()
    assert picture[0, 0] == landarea.OUTSIDE_GREY
    assert picture[5, 5] == landarea.AREA_GREY
    assert picture[12, 15] == landarea.AMERICAS_GREY
    assert picture[15, 25] == landarea.ISLANDS_GREY
    decoded = np.asarray(Image.open(io.BytesIO(area.png())))
    assert np.array_equal(decoded, picture)
    assert (
        max(
            landarea.OUTSIDE_GREY,
            landarea.AREA_GREY,
            landarea.ISLANDS_GREY,
            landarea.AMERICAS_GREY,
        )
        < landmask.THRESHOLD
    )


class _Counter:
    def __init__(self) -> None:
        self.loads = 0
        self.selections = 0


@pytest.fixture
def counted(monkeypatch: pytest.MonkeyPatch) -> _Counter:
    """The game's map and the canvas stood in for, counting how often each is made."""
    counter = _Counter()

    class MapStub:
        keys = ("a",)
        inputs = ("map 1 0",)

    def load(_root: Path) -> MapStub:
        counter.loads += 1
        return MapStub()

    def select(_map: MapStub, _band: int, *, expanded: bool) -> Canvas:
        assert expanded
        counter.selections += 1
        return _canvas()

    monkeypatch.setattr(landarea, "load_map", load)
    monkeypatch.setattr(landcache, "select_canvas", select)
    monkeypatch.setattr(
        landarea, "input_fingerprints", lambda _root: (FileFingerprint("map.png", 1, "ab" * 32),)
    )
    return counter


def test_the_area_is_kept_so_the_map_is_read_once(tmp_path: Path, counted: _Counter) -> None:
    """The second look at the area reads neither the map nor the canvas."""
    cache = tmp_path / "cache"
    first = landarea.get_area(cache, tmp_path, 100, expanded=True)
    assert (counted.loads, counted.selections) == (1, 1)
    again = landarea.get_area(cache, tmp_path, 100, expanded=True)
    assert (counted.loads, counted.selections) == (1, 1)
    for one, other in ((first.area, again.area), (first.americas, again.americas)):
        assert np.array_equal(one, other)
    assert np.array_equal(first.islands, again.islands)
    assert first.shape == again.shape
    other_band = landarea.get_area(cache, tmp_path, 120, expanded=True)
    assert counted.loads == 2
    assert np.array_equal(other_band.area, first.area)


def test_without_a_cache_the_area_is_made_every_time(tmp_path: Path, counted: _Counter) -> None:
    _ = landarea.get_area(None, tmp_path, 100, expanded=True)
    _ = landarea.get_area(None, tmp_path, 100, expanded=True)
    assert counted.loads == 2
    assert not list(tmp_path.iterdir())


def test_the_key_follows_the_files_the_settings_and_the_code(
    tmp_path: Path, counted: _Counter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A patched game, another band or another code is another area."""
    _ = counted
    key = landarea.area_key(tmp_path, 100, expanded=True)
    assert landarea.area_key(tmp_path, 100, expanded=True) == key
    assert landarea.area_key(tmp_path, 101, expanded=True) != key
    assert landarea.area_key(tmp_path, 100, expanded=False) != key
    monkeypatch.setattr(
        landarea, "input_fingerprints", lambda _root: (FileFingerprint("map.png", 1, "cd" * 32),)
    )
    assert landarea.area_key(tmp_path, 100, expanded=True) != key
    monkeypatch.setattr(landcache, "code_identity", lambda: "other code")
    assert landarea.area_key(tmp_path, 100, expanded=True) != key


def test_a_damaged_entry_is_made_again(tmp_path: Path, counted: _Counter) -> None:
    cache = tmp_path / "cache"
    _ = landarea.get_area(cache, tmp_path, 100, expanded=True)
    (entry,) = (cache / landcache.AREAS).glob(f"*{landcache.AREA_SUFFIX}")
    _ = entry.write_bytes(b"not an archive")
    area = landarea.get_area(cache, tmp_path, 100, expanded=True)
    assert counted.loads == 2
    assert area.area.any()


def test_the_template_is_written_from_the_kept_area(tmp_path: Path, counted: _Counter) -> None:
    """Saving the template twice reads the map once, and the file is the area's picture."""
    game = build_game(tmp_path / "game")
    data = tmp_path / "data"
    first = tmp_path / "out" / "template.png"
    second = tmp_path / "template2.png"
    assert service.land_template(game, first, PRESETS["continents"], data=data) == (32, 24)
    assert service.land_template(game, second, PRESETS["continents"], data=data) == (32, 24)
    assert counted.loads == 1
    assert first.read_bytes() == second.read_bytes()
    assert np.array_equal(np.asarray(Image.open(first)), landarea.from_canvas(_canvas()).picture())
