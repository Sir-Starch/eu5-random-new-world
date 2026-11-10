"""The work of the window's land editor that is not drawing (ADR 0010, G4).

The editor paints a picture of kinds (``rnw.landmask``: sea, land, mountains, highlands,
lowlands, lakes) on the area that the New World can fill (``rnw.landarea``), every eighth pixel
of the canvas. Everything it needs from the generator lives here, so that the two windows and
the tests share it and the window only draws:

* ``make_preset`` draws a ready land to start from (a supercontinent, two continents, an
  archipelago, a ring of land round a sea, ...), fitted to the area and to the seed;
* ``decorate`` adds mountain chains, highlands, lowlands and lakes to land that has none;
* ``check`` says what the generator will make of the picture before the world is begun: what
  it will drop, what it will refuse and which island groups it will move;
* ``to_editor`` brings a picture from a file onto the editor's sheet.

Nothing here reads a game file; the area is given. A picture is an array of kinds, ``uint8``.
"""

# NumPy stubs type array shapes and arithmetic as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np
from numpy.typing import NDArray

from rnw.fields import warped_noise
from rnw.landarea import EDITOR_STEP
from rnw.landmask import (
    ASPECT_PERMILLE,
    HIGHLANDS,
    IS_LAND,
    KINDS,
    LAKE,
    LAND,
    LOWLANDS,
    MAX_LAND_PERMILLE,
    MIN_LAND_PERMILLE,
    MOUNTAINS,
    PERMILLE,
    SEA,
)
from rnw.newworld import MIN_KEPT_PERCENT
from rnw.noise import NOISE_SCALE
from rnw.rng import derive_seed
from rnw.topology import distance_from, label_components

if TYPE_CHECKING:
    from rnw.landarea import LandArea
    from rnw.landmask import LandMask
    from rnw.settings import NewWorldSettings

Floats = NDArray[np.float64]
Kinds = NDArray[np.uint8]
Mask = NDArray[np.bool_]

# The ways to start: a layout of the land over the area, and the share of the usable area it fills.
SUPERCONTINENT: Final[str] = "supercontinent"
TWO_CONTINENTS: Final[str] = "two_continents"
THREE_CONTINENTS: Final[str] = "three_continents"
ARCHIPELAGO: Final[str] = "archipelago"
ISLAND_CHAIN: Final[str] = "island_chain"
RING: Final[str] = "ring"
CRESCENT: Final[str] = "crescent"
SCATTERED: Final[str] = "scattered"
PRESETS: Final[tuple[str, ...]] = (
    SUPERCONTINENT,
    TWO_CONTINENTS,
    THREE_CONTINENTS,
    ARCHIPELAGO,
    ISLAND_CHAIN,
    RING,
    CRESCENT,
    SCATTERED,
)
# Permille of the usable area that is land.
SHARES: Final[dict[str, int]] = {
    SUPERCONTINENT: 300,
    TWO_CONTINENTS: 270,
    THREE_CONTINENTS: 280,
    ARCHIPELAGO: 130,
    ISLAND_CHAIN: 90,
    RING: 220,
    CRESCENT: 200,
    SCATTERED: 220,
}
# Land pieces under this many pixels of the sheet are specks of a preset and are taken out,
# and so are the pits of water that small in its land.
SPECK: Final[int] = 24
PIT: Final[int] = 10
OFFSHORE: Final[int] = 3  # sheet pixels of sea that a lake keeps between it and the open water
LAKES_MAX: Final[int] = 10
LAND_PER_LAKE: Final[int] = 14000
OPEN_LAKES_SHOWN: Final[int] = 8
# How ``decorate`` chooses: a chain lies where a smooth noise is within ``CHAIN_BAND`` of zero,
# is broken where another is under ``CHAIN_BREAK``, and stays ``CHAIN_INLAND`` pixels off the
# shore; highlands fill ``FLANK_REACH`` pixels round a chain wherever a noise is over
# ``FLANK_FLOOR``; lowlands lie low where a noise is over ``LOW_FLOOR``, between ``LOW_NEAR`` and
# ``LOW_FAR`` pixels from the sea and ``LOW_CLEAR`` from a chain; a lake sits ``LAKE_INLAND``
# pixels inside the land and is where its bump is over ``LAKE_LEVEL``.
CHAIN_BAND: Final[float] = 0.1
CHAIN_BREAK: Final[float] = -0.45
CHAIN_INLAND: Final[int] = 5
CHAIN_CORE_INLAND: Final[int] = 7
FLANK_REACH: Final[int] = 8
FLANK_FLOOR: Final[float] = -0.15
FLANK_INLAND: Final[int] = 3
LOW_FLOOR: Final[float] = 0.12
LOW_NEAR: Final[int] = 3
LOW_FAR: Final[int] = 34
LOW_CLEAR: Final[int] = 14
LAKE_INLAND: Final[int] = 14
LAKE_LEVEL: Final[float] = 0.4
INLAND_LIMIT: Final[int] = 48


# The sheet's usual height, to which the periods of the noises are given.
REFERENCE_SIDE: Final[int] = 1024
MIN_PERIOD: Final[int] = 8


def _unit(seed: int, name: str, shape: tuple[int, int], period: int, octaves: int = 3) -> Floats:
    """Smooth noise of the sheet's size in about [-1, 1]; ``period`` is in pixels of a sheet
    ``REFERENCE_SIDE`` high and is scaled to the sheet given."""
    period = max(MIN_PERIOD, period * min(shape) // REFERENCE_SIDE)
    field = warped_noise(
        derive_seed(seed, name),
        shape,
        step=EDITOR_STEP,
        period=period,
        octaves=octaves,
        warp_px=max(1, period // 3),
    )
    return field.astype(np.float64) / NOISE_SCALE


def usable_area(area: Mask, margin: int) -> Mask:
    """Where land may be drawn: the area, a coast margin in from what lies outside it and from
    the picture's edge (the generator keeps land off them)."""
    outside = ~area
    outside[:, [0, -1]] = True
    outside[[0, -1], :] = True
    return distance_from(outside, margin, octagonal=True) >= margin


def _grid(shape: tuple[int, int]) -> tuple[Floats, Floats]:
    rows, columns = np.mgrid[0 : shape[0], 0 : shape[1]]
    return rows.astype(np.float64), columns.astype(np.float64)


@dataclass(frozen=True, slots=True)
class _Frame:
    """The usable area's box, in which a layout is given in fractions."""

    top: float
    left: float
    height: float
    width: float

    def at(self, down: float, across: float) -> tuple[float, float]:
        return self.top + down * self.height, self.left + across * self.width


def _frame(usable: Mask) -> _Frame:
    rows, columns = np.nonzero(usable)
    if not rows.size:
        message = "No area is left to draw on"
        raise ValueError(message)
    top, bottom, left, right = rows.min(), rows.max(), columns.min(), columns.max()
    return _Frame(float(top), float(left), float(bottom - top + 1), float(right - left + 1))


def _blob(
    grid: tuple[Floats, Floats],
    centre: tuple[float, float],
    radii: tuple[float, float],
    turn: float,
    weight: float = 1.0,
) -> Floats:
    """An elongated bump: weight at its centre, falling away over its radii."""
    rows, columns = grid
    down, across = rows - centre[0], columns - centre[1]
    along = down * np.cos(turn) + across * np.sin(turn)
    athwart = across * np.cos(turn) - down * np.sin(turn)
    distance = (along / radii[0]) ** 2 + (athwart / radii[1]) ** 2
    return weight * np.exp(-1.6 * distance)


def _jitter(rng: np.random.Generator, spread: float) -> float:
    return float(rng.uniform(-spread, spread))


def _continents(
    frame: _Frame,
    grid: tuple[Floats, Floats],
    rng: np.random.Generator,
    layout: tuple[tuple[float, float, float, float, float], ...],
) -> Floats:
    """The bumps of a layout of ``(down, across, tall, wide, weight)`` in fractions of the frame,
    each moved, sized and turned a little by the generator."""
    total = np.zeros(grid[0].shape, dtype=np.float64)
    for down, across, tall, wide, weight in layout:
        centre = frame.at(down + _jitter(rng, 0.04), across + _jitter(rng, 0.04))
        scale = 1 + _jitter(rng, 0.18)
        radii = (tall * frame.height * scale, wide * frame.width * (2 - scale))
        total += _blob(grid, centre, radii, float(rng.uniform(0, np.pi)), weight)
    return total


def _chain(frame: _Frame, grid: tuple[Floats, Floats], rng: np.random.Generator) -> Floats:
    """A string of islands along a bending line, larger in the middle."""
    total = np.zeros(grid[0].shape, dtype=np.float64)
    phase, bend = float(rng.uniform(0, 2 * np.pi)), float(rng.uniform(0.8, 1.6))
    count = 18
    for step in range(count):
        along = 0.08 + 0.84 * step / (count - 1)
        down = 0.5 + 0.26 * np.sin(2 * np.pi * bend * along + phase)
        size = 0.016 + 0.03 * np.sin(np.pi * along) * float(rng.uniform(0.4, 1.2))
        centre = frame.at(down + _jitter(rng, 0.03), along)
        radii = (size * frame.height * 1.4, size * frame.width * 1.1)
        total += _blob(grid, centre, radii, float(rng.uniform(0, np.pi)))
    return total


def _ring(
    frame: _Frame, grid: tuple[Floats, Floats], rng: np.random.Generator, *, arc: bool
) -> Floats:
    """A ring of land round a sea, or a crescent: the part of it that faces one way."""
    centre = frame.at(0.5 + _jitter(rng, 0.05), 0.5 + _jitter(rng, 0.05))
    radius = 0.30 * min(frame.height, frame.width)
    rows, columns = grid
    down, across = rows - centre[0], columns - centre[1]
    distance = np.hypot(down, across)
    ring = np.exp(-(((distance - radius) / (0.2 * radius)) ** 2))
    if not arc:
        return ring
    facing = float(rng.uniform(0, 2 * np.pi))
    gate = np.cos(np.arctan2(down, across) - facing)
    return ring * np.clip(gate + 0.35, 0.0, 1.0)


def _layout(
    preset: str,
    frame: _Frame,
    grid: tuple[Floats, Floats],
    rng: np.random.Generator,
    seed: int,
) -> Floats:
    shape = grid[0].shape
    rough = _unit(seed, "preset_rough", shape, 70, 3)
    if preset == SUPERCONTINENT:
        bumps = _continents(
            frame,
            grid,
            rng,
            (
                (0.5, 0.5, 0.36, 0.30, 1.0),
                (0.3, 0.36, 0.20, 0.16, 0.8),
                (0.68, 0.62, 0.18, 0.20, 0.8),
                (0.5, 0.78, 0.14, 0.12, 0.6),
            ),
        )
    elif preset == TWO_CONTINENTS:
        bumps = _continents(
            frame,
            grid,
            rng,
            ((0.5, 0.25, 0.34, 0.15, 1.0), (0.5, 0.76, 0.28, 0.15, 0.95)),
        )
    elif preset == THREE_CONTINENTS:
        bumps = _continents(
            frame,
            grid,
            rng,
            (
                (0.35, 0.2, 0.22, 0.13, 1.0),
                (0.65, 0.5, 0.25, 0.15, 1.0),
                (0.38, 0.82, 0.20, 0.13, 0.9),
            ),
        )
    elif preset == ARCHIPELAGO:
        return _unit(seed, "preset_islands", shape, 85, 3) + 0.35 * _unit(
            seed, "preset_swell", shape, 260, 2
        )
    elif preset == ISLAND_CHAIN:
        bumps = _chain(frame, grid, rng)
    elif preset == RING:
        bumps = _ring(frame, grid, rng, arc=False)
    elif preset == CRESCENT:
        bumps = _ring(frame, grid, rng, arc=True)
    else:
        bumps = _continents(frame, grid, rng, ((0.5, 0.45, 0.30, 0.22, 1.1),)) + 0.5 * (
            _unit(seed, "preset_islands", shape, 85, 3) + 1.0
        )
    return bumps + 0.22 * rough + 0.08 * _unit(seed, "preset_fine", shape, 28, 2)


def _tidy(land: Mask, usable: Mask) -> Mask:
    """Take out specks of land and pits of water: a preset has no dust to clean."""
    pieces = label_components(land.astype(np.int32))
    sizes = np.bincount(pieces.ravel())
    land = land & (sizes >= SPECK)[pieces]
    pits = label_components((~land).astype(np.int32))
    water = np.bincount(pits.ravel())
    small = ~land & usable & (water < PIT)[pits]
    return land | small


def make_preset(preset: str, area: LandArea, seed: int, *, margin: int = 6) -> Kinds:
    """A land to start from: the layout ``preset`` on ``area`` (at the editor's step), different
    for each seed, filling the share of the usable area that ``SHARES`` gives it.

    The land keeps ``margin`` pixels off what lies outside the area. Raises ``ValueError`` for an
    unknown preset or an area with nothing usable.
    """
    if preset not in SHARES:
        message = f"There is no preset {preset!r}"
        raise ValueError(message)
    shape = area.picture_shape
    usable = usable_area(area.area.copy(), margin)
    frame, grid = _frame(usable), _grid(shape)
    rng = np.random.default_rng(derive_seed(seed, f"preset_{preset}") & 0xFFFF_FFFF_FFFF)
    potential = _layout(preset, frame, grid, rng, seed)
    inside = potential[usable]
    keep = max(1, int(inside.size * SHARES[preset] // PERMILLE))
    threshold = float(np.partition(inside, inside.size - keep)[inside.size - keep])
    land = _tidy(usable & (potential >= threshold), usable) & usable
    return np.where(land, LAND, SEA).astype(np.uint8)


def americas(area: LandArea) -> Kinds:
    """The installed game's own Americas on the sheet, as land."""
    return np.where(area.americas & area.area, LAND, SEA).astype(np.uint8)


def _dilate(mask: Mask, radius: int) -> Mask:
    """The pixels within ``radius`` (octagonal steps) of ``mask``."""
    return distance_from(mask, radius + 1, octagonal=True) <= radius


def decorate(  # noqa: PLR0913 - what to add is a choice for each kind.
    kinds: Kinds,
    seed: int,
    *,
    mountains: bool = True,
    highlands: bool = True,
    lowlands: bool = False,
    lakes: bool = True,
) -> Kinds:
    """``kinds`` with mountain chains, highlands, lowlands and lakes added to its plain land.

    Only ``LAND`` pixels change, so what was painted stays. Chains follow the zero lines of a
    smooth noise inland (as the generator's own do), highlands flank them, lowlands lie low by the
    coasts and lakes sit well inside the land with a shore of land all round. The same picture
    and seed give the same result.
    """
    out = kinds.copy()
    shape = kinds.shape
    land = np.array(IS_LAND, dtype=np.bool_)[kinds]
    if not land.any():
        return out
    plain = kinds == LAND
    inland = distance_from(~land, INLAND_LIMIT, octagonal=True)
    chain = np.zeros(shape, dtype=np.bool_)
    if mountains:
        line = np.abs(_unit(seed, "deco_chain", shape, 220, 2)) < CHAIN_BAND
        broken = _unit(seed, "deco_breaks", shape, 120, 2) > CHAIN_BREAK
        chain = _dilate(line & broken & (inland >= CHAIN_CORE_INLAND), 2) & plain
        chain &= inland >= CHAIN_INLAND
        out[chain] = MOUNTAINS
    if highlands:
        flank = np.zeros(shape, dtype=np.bool_)
        if chain.any():
            flank = _dilate(chain, FLANK_REACH) & ~chain
        spread = _unit(seed, "deco_flank", shape, 60, 2) > FLANK_FLOOR
        out[flank & spread & plain & (inland >= FLANK_INLAND)] = HIGHLANDS
    if lowlands:
        low = _unit(seed, "deco_low", shape, 110, 2) > LOW_FLOOR
        far = ~_dilate(chain, LOW_CLEAR) if chain.any() else np.ones(shape, dtype=np.bool_)
        out[low & far & plain & (inland >= LOW_NEAR) & (inland <= LOW_FAR)] = LOWLANDS
    if lakes:
        _add_lakes(out, seed, inland)
    return out


def _add_lakes(kinds: Kinds, seed: int, inland: NDArray[np.int32]) -> None:
    """Round lakes of plain land that has ``OFFSHORE`` pixels of land round them."""
    rng = np.random.default_rng(derive_seed(seed, "deco_lakes") & 0xFFFF_FFFF_FFFF)
    rows, columns = _grid(kinds.shape)
    free = (kinds == LAND) & (inland >= LAKE_INLAND)
    count = min(LAKES_MAX, max(1, int(np.count_nonzero(kinds == LAND)) // LAND_PER_LAKE))
    for _ in range(count * 6):
        candidates = np.flatnonzero(free)
        if not candidates.size or count <= 0:
            return
        spot = int(candidates[int(rng.integers(candidates.size))])
        centre = (spot // kinds.shape[1], spot % kinds.shape[1])
        reach = int(rng.integers(3, 9))
        wobble = _blob(
            (rows, columns),
            (float(centre[0]), float(centre[1])),
            (reach * float(rng.uniform(0.8, 1.6)), reach * float(rng.uniform(0.8, 1.6))),
            float(rng.uniform(0, np.pi)),
        )
        water = wobble > LAKE_LEVEL
        shore = _dilate(water, OFFSHORE)
        if (kinds[shore & ~water] != LAND).any() or (kinds[water] != LAND).any():
            continue
        kinds[water] = LAKE
        free &= ~_dilate(water, 10)
        count -= 1


@dataclass(frozen=True, slots=True)
class Check:
    """What the generator will make of a picture drawn on an area, before the world is begun."""

    land_permille: int
    mountains: int
    highlands: int
    lowlands: int
    lakes: int
    outside_permille: int
    kept_percent: int
    specks: int
    open_lakes: tuple[tuple[int, int], ...]
    islands_touched: int
    refusal: str


# What would make the generator refuse the picture (or the window refuse to use it).
NO_LAND: Final[str] = "share"
OUTSIDE: Final[str] = "outside"
OPEN_LAKE: Final[str] = "lake_open"
NOTHING: Final[str] = ""


def margin_for(settings: NewWorldSettings) -> int:
    """The sheet pixels of coast margin the generator keeps free of land, at least one."""
    return max(1, -(-settings.coast_margin_px // EDITOR_STEP))


def check(kinds: Kinds, area: LandArea, settings: NewWorldSettings) -> Check:
    """What would happen to ``kinds`` drawn on ``area`` (at the editor's step), by the generator's
    own rules at the sheet's resolution: land outside the area or in its coast margin is dropped,
    land pieces under the smallest island are taken out, a world needs between a thirtieth and
    nine tenths of the picture to be land, and a lake must be enclosed.

    Sizes the settings give in canvas pixels are divided by the sheet's pixel (``EDITOR_STEP``).
    """
    if kinds.max(initial=0) >= KINDS:
        message = f"A pixel of kind {int(kinds.max())} is none of the {KINDS} kinds"
        raise ValueError(message)
    land = np.array(IS_LAND, dtype=np.bool_)[kinds]
    margin = margin_for(settings)
    domain = area.area
    guard = ~domain
    guard[:, [0, -1]] = True
    shore = distance_from(guard, margin, octagonal=True) < margin
    asked = land & domain
    kept = asked & ~shore
    asked_px, kept_px, total = (int(np.count_nonzero(x)) for x in (asked, kept, land))
    percent = 100 if not asked_px else kept_px * 100 // asked_px
    smallest = max(1, settings.min_island_px // EDITOR_STEP**2)
    pieces = label_components(kept.astype(np.int32))
    sizes = np.bincount(pieces.ravel())
    specks = int(np.count_nonzero(sizes[np.unique(pieces[kept])] < smallest))
    keepers = kept & (sizes >= smallest)[pieces]
    marked = kinds == LAKE
    opened = _open_lakes(domain, keepers, shore, marked)
    refusal = NOTHING
    share = total * PERMILLE // kinds.size
    if not MIN_LAND_PERMILLE <= share <= MAX_LAND_PERMILLE:
        refusal = NO_LAND
    elif not asked_px or kept_px * 100 < asked_px * MIN_KEPT_PERCENT:
        refusal = OUTSIDE
    elif opened:
        refusal = OPEN_LAKE
    return Check(
        land_permille=share,
        mountains=int(np.count_nonzero(kinds == MOUNTAINS)),
        highlands=int(np.count_nonzero(kinds == HIGHLANDS)),
        lowlands=int(np.count_nonzero(kinds == LOWLANDS)),
        lakes=int(np.count_nonzero(marked)),
        outside_permille=0 if not total else (total - asked_px) * PERMILLE // total,
        kept_percent=percent,
        specks=specks,
        open_lakes=tuple(opened[:OPEN_LAKES_SHOWN]),
        islands_touched=_islands_touched(area.islands & domain, kept),
        refusal=refusal,
    )


def _open_lakes(domain: Mask, land: Mask, shore: Mask, marked: Mask) -> list[tuple[int, int]]:
    """Where, as (column, row) of the sheet, the marked lakes lie in water that reaches the shore
    (``rnw.newworld._ocean``): a lake that land does not enclose."""
    if not marked.any():
        return []
    coded = np.where(domain, land.astype(np.int32), 2).astype(np.int32)
    parts = label_components(coded)
    water = domain & ~land
    reaching = np.zeros(int(parts.max()) + 1, dtype=np.bool_)
    reaching[np.unique(parts[water & shore])] = True
    leaking = marked & domain & reaching[parts]
    found: list[tuple[int, int]] = []
    for part in np.unique(parts[leaking]).tolist():
        rows, columns = np.nonzero(leaking & (parts == part))
        found.append((int(columns.mean()), int(rows.mean())))
    return found


def _islands_touched(islands: Mask, land: Mask) -> int:
    """Island groups (4-connected stretches of the area's island layer) that land reaches."""
    if not islands.any() or not land.any():
        return 0
    parts = label_components(islands.astype(np.int32))
    return int(np.unique(parts[islands & land]).size)


def to_editor(mask: LandMask, shape: tuple[int, int]) -> tuple[Kinds, str]:
    """A picture on the editor's sheet of ``shape``, and how it was laid on it: ``exact`` when it
    is the sheet's size, ``stretched`` when its proportions are the sheet's within the tolerance
    the generator allows, else ``centered`` at its own proportions with sea round it.
    """
    height, width = shape
    source = (
        mask.kinds if mask.kinds is not None else np.where(mask.land, LAND, SEA).astype(np.uint8)
    )
    rows, columns = source.shape
    if (rows, columns) == (height, width):
        return source.copy(), "exact"
    wanted, given = width * PERMILLE // height, columns * PERMILLE // rows
    if abs(given - wanted) * PERMILLE <= ASPECT_PERMILLE * wanted:
        take_rows = np.arange(height, dtype=np.int64) * rows // height
        take_columns = np.arange(width, dtype=np.int64) * columns // width
        return source[np.ix_(take_rows, take_columns)], "stretched"
    scale = min(height / rows, width / columns)
    new_rows, new_columns = max(1, round(rows * scale)), max(1, round(columns * scale))
    take_rows = np.arange(new_rows, dtype=np.int64) * rows // new_rows
    take_columns = np.arange(new_columns, dtype=np.int64) * columns // new_columns
    out = np.zeros(shape, dtype=np.uint8)
    top, left = (height - new_rows) // 2, (width - new_columns) // 2
    out[top : top + new_rows, left : left + new_columns] = source[np.ix_(take_rows, take_columns)]
    return out, "centered"


def from_sketch(
    picture: NDArray[np.uint8], *, lake: tuple[int, int, int], land: tuple[int, int, int]
) -> Kinds:
    """The kinds of a continent sketch (``rnw.app.candidates``): its land and its lakes are the
    two colours given, and the rest is sea."""
    kinds = np.full(picture.shape[:2], SEA, dtype=np.uint8)
    kinds[np.all(picture == np.array(lake, dtype=np.uint8), axis=2)] = LAKE
    kinds[np.all(picture == np.array(land, dtype=np.uint8), axis=2)] = LAND
    return kinds
