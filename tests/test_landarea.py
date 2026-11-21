"""The area a New World fills, as a picture to draw on: cut from the canvas, kept in the cache."""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import io
from typing import TYPE_CHECKING, final

import numpy as np
import pytest
from PIL import Image

from rnw import landarea, landcache, landmask
from rnw.app import service
from rnw.continent_domains import CONTINENTS, Domain
from rnw.contract import FileFingerprint
from rnw.eu5_canvas import Canvas
from rnw.islands import Footprint
from rnw.model import CellClass
from rnw.settings import PRESETS
from tests.fakes import build_game

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from numpy.typing import NDArray


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


@final
class _Counter:
    def __init__(self) -> None:
        self.loads: int = 0
        self.selections: int = 0


def _fingerprint(digest: str) -> Callable[[Path], tuple[FileFingerprint, ...]]:
    """A stand-in for the map's fingerprints that names one digest."""

    def fingerprints(_root: Path) -> tuple[FileFingerprint, ...]:
        return (FileFingerprint("map.png", 1, digest * 32),)

    return fingerprints


@pytest.fixture
def counted(monkeypatch: pytest.MonkeyPatch) -> _Counter:
    """The game's map and the canvas stood in for, counting how often each is made."""
    counter = _Counter()

    @final
    class MapStub:
        keys: tuple[str, ...] = ("a", "b")
        inputs: tuple[str, ...] = ("map 1 0",)
        # The whole map: land (location 1) in its left half, sea (location 0) in its right.
        classes: tuple[CellClass, ...] = (CellClass.SEA, CellClass.LAND)
        labels: NDArray[np.int32] = np.repeat(
            np.array([[1] * 64 + [0] * 64], dtype=np.int32), 96, axis=0
        )

    def load(_root: Path) -> MapStub:
        counter.loads += 1
        return MapStub()

    def select(_map: MapStub, _band: int, *, expanded: bool) -> Canvas:
        assert expanded
        counter.selections += 1
        return _canvas()

    monkeypatch.setattr(landarea, "load_map", load)
    monkeypatch.setattr(landcache, "select_canvas", select)
    monkeypatch.setattr(landarea, "input_fingerprints", _fingerprint("ab"))
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
    # Where the sheet lies on the map and the map's land, for the editor's view of the world.
    assert first.origin == again.origin == (0, 0, 96, 128)
    assert first.world is not None
    assert again.world is not None
    assert np.array_equal(first.world, again.world)
    assert first.world.shape == (96 // landarea.WORLD_STEP, 128 // landarea.WORLD_STEP)
    assert first.world[:, :4].all()
    assert not first.world[:, 4:].any()
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
    monkeypatch.setattr(landarea, "input_fingerprints", _fingerprint("cd"))
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


def _domain(first_row: int, first_column: int, rows: int, columns: int, map_width: int) -> Domain:

    mask = np.ones((rows, columns), dtype=np.bool_)
    return Domain(
        CONTINENTS["africa"], first_column, map_width, mask, mask.copy(), first_row=first_row
    )


def test_the_areas_of_the_other_continents_are_marked_on_the_map_as_it_is_drawn_for_the_view() -> (
    None
):
    step = landarea.WORLD_STEP
    width = 32 * step
    # One domain inside the map, one across its seam (it begins four world pixels before the end).
    inside = _domain(2 * step, 4 * step, 3 * step, 5 * step, width)
    across = _domain(8 * step, width - 4 * step, 2 * step, 8 * step, width)
    marked = landarea.world_areas([inside, across], (16 * step, width))
    assert marked.shape == (16, 32)
    assert marked[2:5, 4:9].all()
    assert marked[8:10, 28:32].all()
    assert marked[8:10, 0:4].all()
    assert marked.sum() == 3 * 5 + 2 * 8
    assert not landarea.world_areas([], (16 * step, width)).any()


def test_the_other_continents_areas_are_kept_with_the_area(tmp_path: Path) -> None:
    sheet = landarea.from_canvas(_canvas())
    others = np.zeros((6, 8), dtype=np.bool_)
    others[1:3, 2:5] = True
    kept = landarea.LandArea(
        sheet.shape,
        sheet.area,
        sheet.americas,
        sheet.islands,
        (0, 0, 96, 128),
        np.ones((6, 8), dtype=np.bool_),
        others,
    )
    target = tmp_path / "area.npz"
    landarea.write_area(target, kept)
    back = landarea.read_area(target)
    assert back is not None
    assert back.others is not None
    assert np.array_equal(back.others, others)
    alone = landarea.LandArea(
        sheet.shape, sheet.area, sheet.americas, sheet.islands, (0, 0, 96, 128), kept.world
    )
    landarea.write_area(target, alone)
    again = landarea.read_area(target)
    assert again is not None
    assert again.others is None
