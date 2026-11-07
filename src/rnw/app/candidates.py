"""Sketches of continents to choose from before a world is made (ADR 0010, F, G4).

A world takes a few minutes; the land alone, the same land model run on the same canvas with
the same seed, takes seconds. So the generator can roll several seeds, draw each one's land
and sea as a small picture, and let the player pick the continent they like and only then make the
world. The sketch is the land stage of the world and nothing else: no cells, relief, biomes or
peoples, and the coast of the finished world can move by the few pixels its cells' borders wobble.

The sketches are made beside each other, as many at once as the cores and the free memory allow;
each is the same whatever runs beside it. With a cache folder each sketch's land stage is kept
there (``rnw.landcache``), and the world made from a sketch starts from it.

This reads the installed game (the map and the canvas), so it is game-side.
"""

# NumPy stubs type array shapes and arithmetic as Any.
# pyright: reportAny=false

from __future__ import annotations

import secrets
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import landcache, tagfont
from rnw.eu5_map import load_map
from rnw.messages import say
from rnw.newworld import land_stage
from rnw.parallel import worker_count
from rnw.progress import checkpoint, run_stage, running

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

    from rnw.eu5_canvas import Canvas
    from rnw.settings import Settings

STEP: Final[int] = 8
SEA: Final[tuple[int, int, int]] = (30, 58, 110)
LAKE: Final[tuple[int, int, int]] = (70, 120, 190)
LAND: Final[tuple[int, int, int]] = (110, 160, 80)
OUTSIDE: Final[tuple[int, int, int]] = (14, 20, 30)
LABEL: Final[tuple[int, int, int]] = (250, 250, 250)
MAX_COUNT: Final[int] = 12
# Peak working memory of one land stage per canvas pixel, with headroom (measured 2026-11-07
# on the continents canvas of EU5 1.4.7).
STAGE_BYTES_PER_PIXEL: Final[int] = 40


class CandidateError(ValueError):
    pass


def check_count(count: int) -> None:
    if not 1 <= count <= MAX_COUNT:
        message = say("candidates.count", count=MAX_COUNT)
        raise CandidateError(message)


@dataclass(frozen=True, slots=True, eq=False)
class Candidate:
    """One rolled continent: its seed, its picture and how much of the area is land."""

    seed: int
    picture: NDArray[np.uint8]
    land_permille: int


def roll(count: int) -> list[int]:
    """``count`` fresh seeds, from the system's secure source."""
    check_count(count)
    return [secrets.randbits(64) for _ in range(count)]


def sketch(
    game_dir: Path, settings: Settings, seeds: list[int], *, cache: Path | None = None
) -> list[Candidate]:
    """The land of each seed on the canvas of ``settings``, drawn at an eighth of the map.

    Needs the game's map; a cancel is felt within a stage of the land model. With ``cache``
    (the land cache of ``rnw.app.service``) each sketch's land stage is kept for its world.
    """
    check_count(len(seeds))
    if settings.mask.id:
        message = say("candidates.drawn")
        raise CandidateError(message)
    shape = settings.new_world
    domain = _canvas(game_dir, settings, cache).mask
    with running("candidates"):
        digest = None if cache is None else landcache.domain_digest(domain)

        def one(seed: int) -> Candidate:
            checkpoint()
            # The relief is let go at once: a sketch keeps only its masks.
            land, ocean, lakes = land_stage(domain.copy(), seed, shape)[:3]
            if cache is not None and digest is not None:
                key = landcache.stage_key(digest, seed, shape)
                landcache.keep_stage(cache, key, (land, ocean, lakes))
            return _draw(seed, domain, land, lakes)

        workers = worker_count(len(seeds), bytes_each=STAGE_BYTES_PER_PIXEL * domain.size)
        if workers == 1:
            found = [one(seed) for seed in seeds]
        else:
            pool = ThreadPoolExecutor(max_workers=workers)
            try:
                found = [job.result() for job in [pool.submit(one, seed) for seed in seeds]]
            finally:
                pool.shutdown(wait=True, cancel_futures=True)
    if cache is not None:
        landcache.prune(cache)
    return found


def _canvas(game_dir: Path, settings: Settings, cache: Path | None) -> Canvas:
    """The canvas of ``settings`` on the installed map; the map is let go on return."""
    game_map = run_stage("load map", lambda: load_map(game_dir))
    shape = settings.new_world
    return run_stage(
        "select canvas",
        lambda: landcache.get_canvas(
            cache,
            game_map,
            shape.ocean_band_px,
            expanded=bool(shape.expand_oceans or shape.landform),
        ),
    )


def _draw(
    seed: int, domain: NDArray[np.bool_], land: NDArray[np.bool_], lakes: NDArray[np.bool_]
) -> Candidate:
    inside, solid, water = domain[::STEP, ::STEP], land[::STEP, ::STEP], lakes[::STEP, ::STEP]
    picture = np.empty((*inside.shape, 3), dtype=np.uint8)
    picture[:] = OUTSIDE
    picture[inside] = SEA
    picture[water] = LAKE
    picture[solid] = LAND
    share = int(np.count_nonzero(land & domain)) * 1000 // max(1, int(np.count_nonzero(domain)))
    return Candidate(seed, picture, share)


def contact_sheet(found: list[Candidate], columns: int = 3) -> NDArray[np.uint8]:
    """The candidates side by side, each marked with its number (from 1) in the corner."""
    if not found or columns < 1:
        message = "There is nothing to put on a sheet"
        raise CandidateError(message)
    height, width, _ = found[0].picture.shape
    gap = 6
    rows = -(-len(found) // columns)
    sheet = np.zeros(
        (rows * (height + gap) + gap, columns * (width + gap) + gap, 3), dtype=np.uint8
    )
    for number, item in enumerate(found, start=1):
        row, column = divmod(number - 1, columns)
        top, left = gap + row * (height + gap), gap + column * (width + gap)
        tile = item.picture.copy()
        _number(tile, number)
        sheet[top : top + height, left : left + width] = tile
    return sheet


def _number(tile: NDArray[np.uint8], number: int) -> None:
    """Stamp ``number`` large in the top-left corner of a tile, in the sheet's label colour."""
    ink = tagfont.text_mask(str(number))
    height, width = tile.shape[:2]
    scale = max(1, min(6, (height - 16) // ink.shape[0], (width - 16) // ink.shape[1]))
    big = np.repeat(np.repeat(ink, scale, axis=0), scale, axis=1)
    rows, columns = min(big.shape[0], height - 8), min(big.shape[1], width - 8)
    if min(rows, columns) <= 0:
        return
    big = big[:rows, :columns]
    tile[8 : 8 + rows, 8 : 8 + columns][big] = LABEL
