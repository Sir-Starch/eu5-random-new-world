"""Known lands: the outlines of famous fantasy and science-fiction lands as ready lands (G4).

``src/rnw/lands`` keeps one small picture of kinds per land (sea, land, lakes), cut out of a map
picture of it by ``experiments/070-known-lands``; ``lands.toml`` names each and where its map is.
Only the outline is kept: no name, drawing or colour of the map. ``known_land`` lays one on the
editor's sheet: scaled to fill its share of the area, put where most of it lies inside what may be
drawn on, and cleaned of what the check would drop. Where a map is cut and its continent runs on
(the north of Westeros), the land is laid so that it runs to the edge of what may be
drawn on there and the area clips it, so that no coast is made where the map has none. Nothing
here reads a game file.
"""

# NumPy stubs type array shapes and arithmetic as Any.
# pyright: reportAny=false

from __future__ import annotations

import io
import tomllib
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import TYPE_CHECKING, Final

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from rnw import landeditor
from rnw.landmask import IS_LAND, KINDS, LAKE, LAND, SEA
from rnw.topology import distance_from, label_components

if TYPE_CHECKING:
    from rnw.landarea import LandArea

Kinds = NDArray[np.uint8]
Mask = NDArray[np.bool_]

PERMILLE: Final[int] = 1000
# A land is first scaled to fill its share of the usable area, at most this much of its box.
BOX_FILL: Final[float] = 0.97
# Scales tried in turn (fractions of the first) until the land lies inside the usable area.
SHRINKS: Final[tuple[float, ...]] = (1.0, 0.93, 0.86, 0.79, 0.72, 0.65, 0.58, 0.5, 0.42, 0.35)
# A place is good when this share of the land is inside the usable area.
INSIDE_ENOUGH: Final[float] = 0.985
# What an island group of the Old World under the land costs, against a pixel of land outside the
# usable area costing one (groups move to open water, so this only breaks ties between places).
ISLAND_WEIGHT: Final[float] = 0.5
# Gains are rounded to this fraction of a pixel (equal places must tie despite FFT noise).
ROUNDING: Final[int] = 100
# A pixel is next to the sea when its step distance to it is under this.
NEXT_TO: Final[int] = 2
# The sides of a picture, as letters (north, east, south, west).
SIDES: Final[str] = "nesw"
# On a side where the map is cut and the land runs on, this much of the box (counted from that
# edge) may lie outside the usable area: the area clips it.
OPEN_BAND: Final[float] = 0.25
# With an open side, places within this share of the best count of land inside are equally good,
# and the one whose land reaches the edge of the usable area is taken.
OPEN_SLACK: Final[float] = 0.03


@dataclass(frozen=True, slots=True)
class KnownLand:
    """A land of the library: its id, the share (permille) of the usable area it fills, where its
    map is and the sides (letters of ``SIDES``) on which the map is cut and the land runs on."""

    id: str
    share: int
    source: str
    open: str = ""


@cache
def known_lands() -> tuple[KnownLand, ...]:
    """The lands of the library, in the order of ``lands.toml``."""
    text = (resources.files("rnw") / "lands" / "lands.toml").read_text(encoding="utf-8")
    lands = tuple(
        KnownLand(str(row["id"]), int(row["share"]), str(row["source"]), str(row.get("open", "")))
        for row in tomllib.loads(text)["land"]
    )
    for land in lands:
        if not set(land.open) <= set(SIDES):
            message = f"The open sides of {land.id!r} are not letters of {SIDES!r}"
            raise ValueError(message)
    return lands


def land_ids() -> tuple[str, ...]:
    """The ids of the known lands."""
    return tuple(land.id for land in known_lands())


@cache
def source_kinds(land_id: str) -> Kinds:
    """The picture of kinds of a known land, cropped to its box. Raises ``ValueError`` for an id
    that is none of the library's, or a picture with a pixel of no kind."""
    if land_id not in land_ids():
        message = f"There is no known land {land_id!r}"
        raise ValueError(message)
    raw = (resources.files("rnw") / "lands" / f"{land_id}.png").read_bytes()
    with Image.open(io.BytesIO(raw)) as picture:
        kinds = np.asarray(picture.convert("L"), dtype=np.uint8).copy()
    if kinds.max(initial=0) >= KINDS:
        message = f"The picture of {land_id!r} has a pixel of no kind"
        raise ValueError(message)
    kinds.setflags(write=False)
    return kinds


def _resize(kinds: Kinds, scale: float) -> Kinds:
    """``kinds`` at ``scale`` by the nearest pixel."""
    rows, columns = kinds.shape
    new_rows, new_columns = max(1, round(rows * scale)), max(1, round(columns * scale))
    take_rows = np.minimum(np.arange(new_rows, dtype=np.int64) * rows // new_rows, rows - 1)
    take_columns = np.minimum(
        np.arange(new_columns, dtype=np.int64) * columns // new_columns, columns - 1
    )
    return kinds[np.ix_(take_rows, take_columns)]


def _core(land: Mask, open_sides: str) -> Mask:
    """``land`` but what lies within ``OPEN_BAND`` of the box on an open side: the part that has to
    lie inside the usable area."""
    core = land.copy()
    rows, columns = land.shape
    band_rows, band_columns = round(OPEN_BAND * rows), round(OPEN_BAND * columns)
    if "n" in open_sides:
        core[:band_rows] = False
    if "s" in open_sides:
        core[rows - band_rows :] = False
    if "w" in open_sides:
        core[:, :band_columns] = False
    if "e" in open_sides:
        core[:, columns - band_columns :] = False
    return core


def _limits(size: int, box: int, span: tuple[int, int], runs: tuple[bool, bool]) -> tuple[int, int]:
    """The first and last offset of a box of ``box`` pixels on an axis of ``size``, whose usable
    part spans ``span`` (first and last pixel): any with the box on the sheet, and where the land
    runs on past a side (``runs``: low, high), as far past the usable edge as ``OPEN_BAND`` of the
    box, or, if it can cover the whole usable part from both sides, only the offsets that do."""
    low, high = span
    first, last = 0, size - box
    band = round(OPEN_BAND * box)
    if runs[0]:
        first = low - band
    if runs[1]:
        last = high + 1 - box + band
    if all(runs) and box >= high - low + 1:
        first, last = high + 1 - box, low
    return first, last


def _best_offset(
    core: Mask,
    usable: Mask,
    islands: Mask,
    limits: tuple[tuple[int, int], tuple[int, int]],
    open_sides: str,
) -> tuple[int, int] | None:
    """Where ``core`` (a small box) lies most inside ``usable``, and off the island groups of the
    Old World where it can: its top-left (row, column) on the sheet, within ``limits`` (the box may
    reach past the sheet where its land runs on), or ``None`` if no offset is allowed. Equally good
    places give the one whose land reaches the usable area on the open sides, then the one nearest
    the middle of the usable area."""
    height, width = usable.shape
    rows, columns = core.shape
    (first_row, last_row), (first_column, last_column) = limits
    if first_row > last_row or first_column > last_column:
        return None
    pad_top, pad_left = max(0, -first_row), max(0, -first_column)
    pad_bottom, pad_right = max(0, last_row + rows - height), max(0, last_column + columns - width)
    weight = np.zeros(
        (height + pad_top + pad_bottom, width + pad_left + pad_right), dtype=np.float64
    )
    weight[pad_top : pad_top + height, pad_left : pad_left + width] = usable.astype(
        np.float64
    ) - ISLAND_WEIGHT * (islands & usable)
    sheet = np.zeros_like(weight)
    sheet[:rows, :columns] = core
    gain = np.rint(
        np.fft.irfft2(np.fft.rfft2(weight) * np.conj(np.fft.rfft2(sheet)), s=weight.shape)
        * ROUNDING
    )
    window = gain[
        first_row + pad_top : last_row + pad_top + 1,
        first_column + pad_left : last_column + pad_left + 1,
    ]
    slack = OPEN_SLACK * ROUNDING * np.count_nonzero(core) if open_sides else 0
    candidates = np.argwhere(window >= window.max() - slack) + np.array([first_row, first_column])
    around_rows, around_columns = np.nonzero(usable)
    low_row, high_row = int(around_rows.min()), int(around_rows.max()) + 1
    low_column, high_column = int(around_columns.min()), int(around_columns.max()) + 1
    gap = np.zeros(len(candidates), dtype=np.int64)
    if "n" in open_sides:
        gap += np.maximum(0, candidates[:, 0] - low_row)
    if "s" in open_sides:
        gap += np.maximum(0, high_row - (candidates[:, 0] + rows))
    if "w" in open_sides:
        gap += np.maximum(0, candidates[:, 1] - low_column)
    if "e" in open_sides:
        gap += np.maximum(0, high_column - (candidates[:, 1] + columns))
    centre = (around_rows.mean() - rows / 2, around_columns.mean() - columns / 2)
    far = (candidates[:, 0] - centre[0]) ** 2 + (candidates[:, 1] - centre[1]) ** 2
    row, column = (int(x) for x in candidates[int(np.lexsort((far, gap))[0])])
    return row, column


def _lay(box: Kinds, row: int, column: int, shape: tuple[int, int]) -> Kinds:
    """``box`` put on a sheet of ``shape``, its top-left at (row, column), clipped to the sheet."""
    sheet = np.zeros(shape, dtype=np.uint8)
    top, left = max(0, row), max(0, column)
    bottom, right = min(shape[0], row + box.shape[0]), min(shape[1], column + box.shape[1])
    if bottom > top and right > left:
        sheet[top:bottom, left:right] = box[
            top - row : bottom - row, left - column : right - column
        ]
    return sheet


def close_lakes(kinds: Kinds) -> Kinds:
    """Lakes that touch the sea (the scaling or the clipping opened them) become sea: a lake must
    be enclosed by land."""
    lake = kinds == LAKE
    if not lake.any():
        return kinds
    sea = kinds == SEA
    parts = label_components(lake.astype(np.int32))
    touching = np.unique(parts[lake & (distance_from(sea, NEXT_TO) < NEXT_TO)])
    opened = np.isin(parts, touching[touching > 0]) & lake
    out = kinds.copy()
    out[opened] = SEA
    return out


def _run_on(
    box: Kinds, row: int, column: int, shape: tuple[int, int], open_sides: str
) -> tuple[Kinds, int, int]:
    """``box`` at (row, column) with its open sides carried on to the edge of the sheet by mirroring
    the map across each cut (a coast that meets the cut goes on as its own reflection), so that the
    land does not end in a cut where its map does not. Returns the carried-on box and its new
    top-left."""
    north = max(0, row) if "n" in open_sides else 0
    south = max(0, shape[0] - (row + box.shape[0])) if "s" in open_sides else 0
    west = max(0, column) if "w" in open_sides else 0
    east = max(0, shape[1] - (column + box.shape[1])) if "e" in open_sides else 0
    if not (north or south or west or east):
        return box, row, column
    return np.pad(box, ((north, south), (west, east)), mode="symmetric"), row - north, column - west


def place(  # noqa: PLR0913
    source: Kinds, area: LandArea, share: int, *, margin: int, speck: int, open_sides: str = ""
) -> Kinds:
    """``source`` laid on the sheet of ``area`` (the editor's step): scaled so that its land fills
    ``share`` permille of the usable area (the area but a coast margin of ``margin`` pixels), and
    put where most of it lies inside; land outside, pieces under ``speck`` pixels and lakes that
    the sea reaches are taken out. On ``open_sides`` (letters of ``SIDES``) the map is cut and the
    land runs on: it is put to reach the edge of the usable area there, is made big enough to
    cover the usable area between two open opposite sides, and the area clips what runs past.
    Raises ``ValueError`` if no usable area is left."""
    usable = landeditor.usable_area(area.area.copy(), margin)
    if not usable.any():
        message = "No area is left to draw on"
        raise ValueError(message)
    is_land = np.array(IS_LAND, dtype=np.bool_)
    rows, columns = np.nonzero(is_land[source])
    box = source[rows.min() : rows.max() + 1, columns.min() : columns.max() + 1]
    land_px = int(np.count_nonzero(is_land[box]))
    used_rows, used_columns = np.nonzero(usable)
    low = (int(used_rows.min()), int(used_columns.min()))
    high = (int(used_rows.max()), int(used_columns.max()))
    room = (high[0] - low[0] + 1, high[1] - low[1] + 1)
    runs = (("n" in open_sides, "s" in open_sides), ("w" in open_sides, "e" in open_sides))
    by_share = (share / PERMILLE * usable.sum() / land_px) ** 0.5
    # An axis with a side that runs on may be longer than the room; one with none must fit it.
    by_box = min(
        (BOX_FILL * room[axis] / box.shape[axis] for axis in (0, 1) if not any(runs[axis])),
        default=by_share,
    )
    covers = [(room[axis] + 2) / box.shape[axis] for axis in (0, 1) if all(runs[axis])]
    first = max([min(by_share, by_box), *covers])
    chosen: tuple[Kinds, Mask, tuple[int, int]] | None = None
    for shrink in SHRINKS:
        scaled = _resize(box, first * shrink)
        land = is_land[scaled]
        core = _core(land, open_sides)
        limits = (
            _limits(usable.shape[0], scaled.shape[0], (low[0], high[0]), runs[0]),
            _limits(usable.shape[1], scaled.shape[1], (low[1], high[1]), runs[1]),
        )
        found = _best_offset(core, usable, area.islands & area.area, limits, open_sides)
        if found is None:
            continue
        chosen = (scaled, core, found)
        inside = np.count_nonzero(
            _lay(core.astype(np.uint8), *found, usable.shape).astype(np.bool_) & usable
        )
        if inside >= INSIDE_ENOUGH * np.count_nonzero(core):
            break
    if chosen is None:
        message = "The land does not fit the sheet"
        raise ValueError(message)
    scaled, _, (row, column) = chosen
    scaled, row, column = _run_on(scaled, row, column, usable.shape, open_sides)
    kinds = _lay(scaled, row, column, usable.shape)
    kinds[~usable] = SEA
    cleaned = landeditor.tidy(is_land[kinds], usable) & usable
    pieces = label_components(cleaned.astype(np.int32))
    sizes = np.bincount(pieces.ravel())
    cleaned &= (sizes >= max(1, speck))[pieces]
    ground = np.where(is_land[kinds], kinds, LAND)
    lakes = (kinds == LAKE) & usable
    out = np.where(cleaned, ground, np.where(lakes, LAKE, SEA)).astype(np.uint8)
    return close_lakes(out)


def known_land(land_id: str, area: LandArea, *, margin: int, speck: int) -> Kinds:
    """The known land ``land_id`` laid on the sheet of ``area`` (see ``place``), running on where
    its map is cut."""
    source = source_kinds(land_id)
    land = next(land for land in known_lands() if land.id == land_id)
    return place(source, area, land.share, margin=margin, speck=speck, open_sides=land.open)
