"""A drawing that marks mountains, highlands, lowlands and lakes in colour."""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import io
from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np
import pytest
from PIL import Image

from rnw import landcache, landmask
from rnw.app import library, service
from rnw.app.worldcode import encode, new_code
from rnw.landmask import (
    HIGHLANDS,
    KIND_COLORS,
    LAKE,
    LAND,
    LOWLANDS,
    MOUNTAINS,
    SEA,
    LandMaskError,
)
from rnw.model import CellClass
from rnw.newworld import generate_new_world
from rnw.relief import HINT_STEP, ReliefHints, generate_relief
from tests.fakes import build_game, build_world
from tests.test_newworld import SMALL

if TYPE_CHECKING:
    from pathlib import Path


def _picture(land: np.ndarray) -> bytes:
    """A picture of land (white) and sea (black), as a painter saves it."""
    buffer = io.BytesIO()
    Image.fromarray(np.where(land, 255, 0).astype(np.uint8)).save(buffer, format="PNG")
    return buffer.getvalue()


def _blob(height: int = 96, width: int = 88) -> np.ndarray:
    land = np.zeros((height, width), dtype=bool)
    land[height // 4 : 3 * height // 4, width // 4 : 3 * width // 4] = True
    return land


def _domain(height: int = 420, width: int = 380) -> np.ndarray:
    domain = np.zeros((height, width), dtype=bool)
    domain[20:-20, 20:-20] = True
    return domain


def _coloured(kinds: np.ndarray, mode: str = "RGB") -> bytes:
    pixels = np.array(KIND_COLORS, dtype=np.uint8)[kinds]
    buffer = io.BytesIO()
    Image.fromarray(pixels).convert(mode).save(buffer, format="PNG")
    return buffer.getvalue()


def _kinds(height: int = 96, width: int = 88) -> np.ndarray:
    """A continent with a mountain range, highlands, a plain and a lake."""
    kinds = np.where(_blob(height, width), LAND, SEA).astype(np.uint8)
    kinds[30:36, 25:65] = MOUNTAINS
    kinds[45:55, 25:45] = HIGHLANDS
    kinds[58:68, 50:62] = LOWLANDS
    kinds[44:50, 55:62] = LAKE
    return kinds


def test_colours_are_read_as_kinds_and_written_back_the_same() -> None:
    """Mountains, highlands, lowlands and lakes survive a round trip; the id is of the drawing."""
    kinds = _kinds()
    mask = landmask.from_bytes(_coloured(kinds))
    assert mask.kinds is not None
    assert np.array_equal(mask.kinds, kinds)
    assert mask.count(MOUNTAINS) == 6 * 40
    assert mask.count(LAKE) == 6 * 7
    assert not mask.land[kinds == LAKE].any()
    assert mask.land[kinds == MOUNTAINS].all()
    again = landmask.from_bytes(mask.png())
    assert again.kinds is not None
    assert np.array_equal(again.kinds, kinds)
    assert again.id == mask.id
    assert again.sha256 == mask.sha256
    assert landmask.from_bytes(_coloured(kinds, "RGBA")).id == mask.id
    plain = landmask.from_bytes(_picture(mask.land))
    assert plain.kinds is None
    assert plain.id != mask.id


def test_a_picture_of_greys_is_read_as_it_always_was() -> None:
    """Land and sea alone keep their kinds None, their grey PNG and their id."""
    land = _blob()
    mask = landmask.from_bytes(_picture(land))
    assert mask.kinds is None
    assert mask.count(LAND) == int(land.sum())
    assert mask.count(SEA) == int((~land).sum())
    assert mask.count(MOUNTAINS) == 0
    grey = Image.open(io.BytesIO(mask.png()))
    assert grey.mode == "L"
    ramp = np.arange(land.shape[1], dtype=np.int64) % 30 - 15
    smooth = np.clip(np.where(land, 255, 0).astype(np.int64) + ramp, 0, 255).astype(np.uint8)
    buffer = io.BytesIO()
    Image.fromarray(smooth).save(buffer, format="PNG")
    assert landmask.from_bytes(buffer.getvalue()).kinds is None
    assert landmask.from_kinds(np.where(land, LAND, SEA).astype(np.uint8)).id == mask.id


def test_a_blurred_colour_falls_back_to_land_or_sea() -> None:
    """Only a pixel clearly of a colour is of it: a stroke's blended edge is land or sea."""
    kinds = _kinds()
    mountains = np.array(KIND_COLORS[MOUNTAINS], dtype=np.int64)
    near = np.clip(mountains + np.array([12, -9, 15]), 0, 255)
    pixels = np.array(KIND_COLORS, dtype=np.uint8)[kinds].astype(np.int64)
    pixels[kinds == MOUNTAINS] = near
    half = (np.array(KIND_COLORS[LAKE]) + np.array(KIND_COLORS[SEA])) // 2
    pixels[20, 10] = half
    buffer = io.BytesIO()
    Image.fromarray(pixels.astype(np.uint8)).save(buffer, format="PNG")
    mask = landmask.from_bytes(buffer.getvalue())
    assert mask.kinds is not None
    assert (mask.kinds == MOUNTAINS).sum() == (kinds == MOUNTAINS).sum()
    assert mask.kinds[20, 10] == SEA
    brown = np.array(KIND_COLORS[MOUNTAINS], dtype=np.int64)
    pixels[kinds == MOUNTAINS] = (brown + 255) // 2
    buffer = io.BytesIO()
    Image.fromarray(pixels.astype(np.uint8)).save(buffer, format="PNG")
    pale = landmask.from_bytes(buffer.getvalue())
    assert pale.kinds is None or not (pale.kinds == MOUNTAINS).any()


def test_a_transparent_colour_is_sea() -> None:
    kinds = _kinds()
    rgba = np.concatenate(
        [np.array(KIND_COLORS, dtype=np.uint8)[kinds], np.full((*kinds.shape, 1), 255, np.uint8)],
        axis=2,
    )
    rgba[kinds == MOUNTAINS, 3] = 0
    buffer = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buffer, format="PNG")
    mask = landmask.from_bytes(buffer.getvalue())
    assert mask.count(MOUNTAINS) == 0
    assert not mask.land[kinds == MOUNTAINS].any()


def test_a_kind_that_does_not_exist_is_refused() -> None:
    with pytest.raises(ValueError, match="none of the"):
        _ = landmask.from_kinds(np.full((70, 70), 9, dtype=np.uint8))


def test_lakes_are_cut_from_the_land_and_the_hints_follow_the_picture() -> None:
    """Fitted to a canvas, a lake is water, and the grids hold where the ground is marked."""
    mask = landmask.from_bytes(_coloured(_kinds()))
    shape = (480, 440)
    drawing = landmask.fit_drawing(mask, shape)
    assert drawing.lakes is not None
    assert drawing.hints is not None
    assert not (drawing.land & drawing.lakes).any()
    assert drawing.lakes[5 * 47, 5 * 58]
    assert drawing.hints.fits(shape)
    grid = drawing.hints.mountains
    assert grid.shape == (480 // HINT_STEP + 1, 440 // HINT_STEP + 1)
    assert grid[33 * 5 // HINT_STEP, 45 * 5 // HINT_STEP] > 700
    assert grid[10, 10] == 0
    assert drawing.hints.lowlands[63 * 5 // HINT_STEP, 56 * 5 // HINT_STEP] > 700
    again = landmask.fit_drawing(mask, shape)
    assert again.hints is not None
    assert np.array_equal(again.hints.mountains, grid)
    assert np.array_equal(again.land, drawing.land)
    plain = landmask.fit_drawing(landmask.from_bytes(_picture(_blob())), shape)
    assert plain.lakes is None
    assert plain.hints is None
    assert np.array_equal(plain.land, landmask.fit(landmask.from_bytes(_picture(_blob())), shape))


def _land(height: int = 320, width: int = 384) -> np.ndarray:
    land = np.zeros((height, width), dtype=bool)
    land[24:-24, 24:-24] = True
    return land


def _hints(shape: tuple[int, int], **cover: tuple[slice, slice]) -> ReliefHints:
    grids: dict[str, np.ndarray] = {}
    for name in ("mountains", "highlands", "lowlands"):
        grid = np.zeros((-(-shape[0] // HINT_STEP) + 1, -(-shape[1] // HINT_STEP) + 1), np.int32)
        if name in cover:
            grid[cover[name]] = 1000
        grids[name] = grid
    return ReliefHints(**grids, flanks=grids["mountains"].copy())


def test_painted_mountains_rise_and_lowlands_are_kept_flat() -> None:
    """The same land and seed: higher where mountains are painted, flat where lowlands are."""
    land = _land()
    rows, columns = (
        slice(100 // HINT_STEP, 160 // HINT_STEP),
        slice(80 // HINT_STEP, 300 // HINT_STEP),
    )
    plain = generate_relief(land, seed=7)
    painted = generate_relief(land, seed=7, hints=_hints(land.shape, mountains=(rows, columns)))
    inside = (slice(112, 148), slice(96, 288))
    assert painted[inside].mean() > plain[inside].mean() + 6000
    assert painted[inside].max() > 20000
    far = (slice(250, 296), slice(40, 120))
    assert np.array_equal(painted[far], plain[far])
    assert not np.any(painted[~land])
    flat = generate_relief(land, seed=7, hints=_hints(land.shape, lowlands=(rows, columns)))
    assert flat[inside].mean() < plain[inside].mean() or np.array_equal(flat[inside], plain[inside])
    assert flat[inside].std() <= plain[inside].std() + 1
    raised = generate_relief(land, seed=7, hints=_hints(land.shape, highlands=(rows, columns)))
    assert raised[inside].mean() > plain[inside].mean() or plain[inside].mean() > 12000


def test_relief_without_hints_is_exactly_what_it_was() -> None:
    """No hints, or hints that mark nothing, change no pixel."""
    land = _land()
    plain = generate_relief(land, seed=3)
    assert np.array_equal(generate_relief(land, seed=3, hints=_hints(land.shape)), plain)
    assert np.array_equal(generate_relief(land, seed=3, hints=None), plain)
    with pytest.raises(ValueError, match="not those of this raster"):
        _ = generate_relief(land, seed=3, hints=_hints((64, 64)))


def _island() -> tuple[np.ndarray, np.ndarray]:
    """A canvas with a square continent drawn in it."""
    domain = _domain()
    drawn = np.zeros(domain.shape, dtype=bool)
    drawn[80:340, 60:320] = True
    return domain, drawn


def _centre(mask: np.ndarray) -> tuple[int, int]:
    rows, columns = np.nonzero(mask)
    return int(rows.mean()), int(columns.mean())


def test_a_marked_lake_stays_a_lake_of_any_size() -> None:
    """A water that land encloses is a lake or a sea by its size; a marked one is a lake."""
    settings = replace(SMALL, min_lake_px=40, max_lake_px=400)
    domain, drawn = _island()
    small = np.zeros(domain.shape, dtype=bool)
    small[200:204, 200:204] = True
    huge = np.zeros(domain.shape, dtype=bool)
    huge[130:300, 110:270] = True
    for lake in (small, huge):
        land = drawn & ~lake
        plain = generate_new_world(domain, seed=5, settings=settings, drawn=land)
        marked = generate_new_world(domain, seed=5, settings=settings, drawn=land, lakes_drawn=lake)
        row, column = _centre(lake)
        assert marked.classes[int(marked.labels[row, column])] is CellClass.LAKE
        assert plain.classes[int(plain.labels[row, column])] is not CellClass.LAKE


def test_a_marked_lake_that_opens_to_the_sea_is_refused() -> None:
    domain, drawn = _island()
    lake = np.zeros(domain.shape, dtype=bool)
    lake[150:190, 60:140] = True
    with pytest.raises(LandMaskError, match="opens to the sea"):
        _ = generate_new_world(
            domain, seed=5, settings=SMALL, drawn=drawn & ~lake, lakes_drawn=lake
        )


def test_lakes_without_a_drawn_land_are_refused() -> None:
    domain = _domain()
    lake = np.zeros(domain.shape, dtype=bool)
    with pytest.raises(ValueError, match="belong to a drawn land"):
        _ = generate_new_world(domain, seed=5, settings=SMALL, lakes_drawn=lake)


def test_painted_mountains_make_a_mountainous_world() -> None:
    """The world's relief follows the picture's mountains, on the cells it builds."""
    domain, drawn = _island()
    rows = slice(190 // HINT_STEP, 230 // HINT_STEP)
    columns = slice(90 // HINT_STEP, 290 // HINT_STEP)
    hints = _hints(domain.shape, mountains=(rows, columns))
    plain = generate_new_world(domain, seed=5, settings=SMALL, drawn=drawn)
    marked = generate_new_world(domain, seed=5, settings=SMALL, drawn=drawn, hints=hints)
    band = (slice(195, 225), slice(100, 280))
    assert marked.elevation[band].mean() > plain.elevation[band].mean() + 5000
    assert marked.labels.shape == plain.labels.shape


def test_the_cache_key_follows_the_lakes_and_the_hints() -> None:
    domain, drawn = _island()
    base = landcache.cache_key(domain, 1, SMALL, drawn)
    lake = np.zeros(domain.shape, dtype=bool)
    lake[200:210, 200:210] = True
    hints = _hints(domain.shape, mountains=(slice(2, 9), slice(2, 9)))
    assert landcache.cache_key(domain, 1, SMALL, drawn, None, (), None, None, None) == base
    assert landcache.cache_key(domain, 1, SMALL, drawn, None, (), None, lake, None) != base
    assert landcache.cache_key(domain, 1, SMALL, drawn, None, (), None, None, hints) != base


def test_a_world_drawn_with_colours_is_found_again_from_its_folder(tmp_path: Path) -> None:
    """The colours travel with the world: its folder keeps the picture the code's id names."""
    mask = landmask.from_bytes(_coloured(_kinds()))
    code = new_code("continents", 7, {"mask": {"id": mask.id}})
    game = build_game(tmp_path / "game")
    data = tmp_path / "data"
    world = replace(build_world(data, game), code=encode(code))
    _ = (library.folder(data, world) / library.LAND_MASK).write_bytes(mask.png())
    found = service.required_land_mask(data, world)
    assert found is not None
    assert found.id == mask.id
    assert found.kinds is not None
    assert mask.kinds is not None
    assert np.array_equal(found.kinds, mask.kinds)
    plain = landmask.from_bytes(_picture(mask.land))
    _ = (library.folder(data, world) / library.LAND_MASK).write_bytes(plain.png())
    with pytest.raises(service.LandImageError):
        _ = service.required_land_mask(data, world)
