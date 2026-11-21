"""What the land editor in the window asks of the generator, as JSON the window reads.

The window draws and the generator knows the rest (``rnw.landeditor``): which ready lands there
are, what the picture on the sheet will become, how a file or a sketched continent is laid on
the sheet. A picture travels as a PNG data URL in the colours of ``KIND_COLORS``; the area the
picture is drawn on travels once, as the grey picture ``LandArea.png`` makes, and the window
reads the four greys back with the numbers ``classes`` names.
"""

from __future__ import annotations

import base64
import binascii
from typing import TYPE_CHECKING, Final, cast

import numpy as np

from rnw import knownlands, landeditor, landmask
from rnw.app import candidates as sketches
from rnw.gui import view
from rnw.gui.text import explain
from rnw.landarea import (
    AMERICAS_GREY,
    AREA_GREY,
    EDITOR_STEP,
    ISLANDS_GREY,
    OUTSIDE_GREY,
    WORLD_STEP,
)
from rnw.landmask import KIND_COLORS, LandMask, LandMaskError
from rnw.png import COLOR_GRAY, COLOR_RGB, encode_png

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from pathlib import Path

    from numpy.typing import NDArray

    from rnw.landarea import LandArea
    from rnw.settings import NewWorldSettings

PNG_URL: Final[str] = "data:image/png;base64,"
PNG_SIGNATURE: Final[bytes] = b"\x89PNG\r\n\x1a\n"
PALETTE: Final[NDArray[np.uint8]] = np.array(KIND_COLORS, dtype=np.uint8)
UNPREPARED: Final[str] = "The area is not ready"
WRONG_SHEET: Final[str] = "The picture is not the editor's sheet"
NOT_PNG: Final[str] = "The picture is not a PNG data URL"
NO_SKETCH: Final[str] = "There is no such sketched continent"


class StudioError(ValueError):
    """A request the editor cannot answer: the window sent something it should not have."""


# The area the drawing fills, on the editor's view of the world: the game's land there is
# replaced, so it is shown neither as kept land nor as sea.
SHEET_AREA: Final[tuple[int, int, int]] = (104, 110, 124)


def kinds_url(kinds: NDArray[np.uint8]) -> str:
    """A picture of kinds as the PNG data URL the window paints from."""
    return view.data_url(encode_png(PALETTE[kinds], color_type=COLOR_RGB, compression="zlib"))


def png_of(url: str) -> bytes:
    """The bytes of a PNG data URL."""
    try:
        raw = base64.b64decode(url.removeprefix(PNG_URL), validate=True)
    except binascii.Error as error:
        raise StudioError(NOT_PNG) from error
    if not url.startswith(PNG_URL) or not raw.startswith(PNG_SIGNATURE):
        raise StudioError(NOT_PNG)
    return raw


def kinds_of(url: str, area: LandArea) -> NDArray[np.uint8]:
    """The kinds of a picture the window sent, which must be the size of the sheet ``area``."""
    try:
        kinds = landmask.decode_kinds(png_of(url))
    except LandMaskError as error:
        raise StudioError(explain(error)) from error
    if kinds.shape != area.picture_shape:
        raise StudioError(WRONG_SHEET)
    return kinds


def opening(
    area: LandArea,
    drawn: LandMask | None,
    found: Sequence[sketches.Candidate],
    settings: NewWorldSettings,
    chosen: sketches.Candidate | None = None,
) -> dict[str, object]:
    """What the window needs to open the editor on the sheet ``area`` (the area at
    ``EDITOR_STEP``): the sheet, the picture chosen now (laid on it, with how it was laid), the
    ready lands, the sketched continents and the sheet's place in the world (``world_view``)."""
    height, width = area.picture_shape
    image, fit = ("", "") if drawn is None else _lay(drawn, area)
    return {
        "width": width,
        "height": height,
        "step": EDITOR_STEP,
        "backdrop": view.data_url(area.png()),
        "margin": view.data_url(_grey(landeditor.shore_of(area, settings) & area.area)),
        "classes": {
            "outside": OUTSIDE_GREY,
            "area": AREA_GREY,
            "islands": ISLANDS_GREY,
            "americas": AMERICAS_GREY,
        },
        "palette": [list(color) for color in KIND_COLORS],
        "image": image,
        "fit": fit,
        "presets": list(landeditor.PRESETS),
        "lands": list(knownlands.land_ids()),
        "sketches": [
            index for index, one in enumerate(found) if one.picture.shape[:2] == area.picture_shape
        ],
        "world": world_view(area, chosen),
    }


def world_view(
    area: LandArea, chosen: sketches.Candidate | None, step: int = EDITOR_STEP
) -> dict[str, object] | None:
    """The whole map with the sheet's frame on it, as fractions of the picture (its left edge,
    top, width and height): the chosen sketch of the world's several continents when there is
    one, else the game's own map in a sketch's darker colours with the area the drawing fills
    (``area`` cut every ``step``th pixel) in ``SHEET_AREA``, since the game's land there is
    replaced. The map wraps east to west, so it is turned to put the frame in its middle, in one
    piece. None when the area does not know where it lies."""
    if area.origin is None or area.world is None:
        return None
    row, column, height, width = area.origin
    rows, columns = area.shape
    picture: NDArray[np.uint8]
    if chosen is not None and chosen.composed:
        picture = np.ascontiguousarray(chosen.picture[::2, ::2])
    else:
        picture = np.where(
            area.world[..., np.newaxis],
            np.array(sketches.KEPT_LAND, dtype=np.uint8),
            np.array(sketches.KEPT_SEA, dtype=np.uint8),
        ).astype(np.uint8)
        picture[_drawn_area(area, area.origin, area.world, step)] = SHEET_AREA
    # Turn the map so that the frame's middle is the picture's.
    picture_width = int(cast("tuple[int, int, int]", picture.shape)[1])
    shift = round((0.5 - (column + columns / 2) / width) * picture_width)
    picture = np.ascontiguousarray(np.roll(picture, shift, axis=1))
    left = (column / width + shift / picture_width) % 1.0
    return {
        "picture": view.data_url(encode_png(picture, color_type=COLOR_RGB, compression="zlib")),
        "frame": [left, row / height, min(columns / width, 1.0), rows / height],
        "sketch": chosen is not None and chosen.composed,
    }


def _drawn_area(
    area: LandArea,
    origin: tuple[int, int, int, int],
    world: NDArray[np.bool_],
    step: int,
) -> NDArray[np.bool_]:
    """The pixels of ``world`` (the map every ``WORLD_STEP``th pixel) that fall in the area the
    drawing fills: the sheet ``area`` cut every ``step``th pixel from ``origin``."""
    row, column, _height, width = origin
    sheet_rows, sheet_columns = area.picture_shape
    world_rows, world_columns = cast("tuple[int, int]", world.shape)
    down = np.arange(world_rows) * WORLD_STEP - row
    across = (np.arange(world_columns) * WORLD_STEP - column) % width
    inside_rows = (down >= 0) & (down < sheet_rows * step)
    inside_columns = across < sheet_columns * step
    found = np.zeros((world_rows, world_columns), dtype=np.bool_)
    picked = np.ix_(np.flatnonzero(inside_rows), np.flatnonzero(inside_columns))
    found[picked] = area.area[np.ix_(down[inside_rows] // step, across[inside_columns] // step)]
    return found


def _grey(mask: NDArray[np.bool_]) -> bytes:
    """A mask as a grey PNG: white where it holds."""
    grey = np.where(mask, 255, 0).astype(np.uint8)
    return encode_png(grey, color_type=COLOR_GRAY, compression="zlib")


def _lay(drawn: LandMask, area: LandArea) -> tuple[str, str]:
    kinds, how = landeditor.to_editor(drawn, area.picture_shape)
    return kinds_url(kinds), how


def preset(area: LandArea, name: str, seed: int, settings: NewWorldSettings) -> str:
    """A ready land on the area, off the coast margin the settings keep."""
    try:
        margin = landeditor.margin_for(settings)
        return kinds_url(landeditor.make_preset(name, area, seed, margin=margin))
    except ValueError as error:
        raise StudioError(str(error)) from error


def known(area: LandArea, name: str, settings: NewWorldSettings) -> str:
    """A known land (``rnw.knownlands``) laid on the area, off the coast margin the settings keep,
    without the pieces the generator would remove."""
    try:
        return kinds_url(
            knownlands.known_land(
                name,
                area,
                margin=landeditor.margin_for(settings),
                speck=max(1, settings.min_island_px // EDITOR_STEP**2),
            )
        )
    except ValueError as error:
        raise StudioError(str(error)) from error


def real_americas(area: LandArea) -> str:
    """The game's own Americas as the land to start from."""
    return kinds_url(landeditor.americas(area))


def sketch(area: LandArea, found: Sequence[sketches.Candidate], index: int) -> str:
    """A continent the generator sketched, as the land to start from."""
    if not 0 <= index < len(found):
        raise StudioError(NO_SKETCH)
    picture = found[index].picture
    if picture.shape[:2] != area.picture_shape:
        raise StudioError(WRONG_SHEET)
    return kinds_url(landeditor.from_sketch(picture, lake=sketches.LAKE, land=sketches.LAND))


DECORATIONS: Final[tuple[str, ...]] = ("mountains", "highlands", "lowlands", "lakes")


def decorate(area: LandArea, url: str, seed: int, parts: Collection[str]) -> str:
    """The picture with some of ``DECORATIONS`` added to its plain land."""
    unknown = set(parts) - set(DECORATIONS)
    if unknown:
        message = f"Nothing to add called {min(unknown)!r}"
        raise StudioError(message)
    done = landeditor.decorate(
        kinds_of(url, area),
        seed,
        mountains="mountains" in parts,
        highlands="highlands" in parts,
        lowlands="lowlands" in parts,
        lakes="lakes" in parts,
    )
    return kinds_url(done)


def imported(area: LandArea, path: Path) -> dict[str, str]:
    """A picture from a file, laid on the sheet: ``{"image", "fit"}``."""
    try:
        data = path.read_bytes()
    except OSError as error:
        raise StudioError(explain(error)) from error
    try:
        mask = landmask.from_kinds(landmask.decode_kinds(data))
    except LandMaskError as error:
        raise StudioError(explain(error)) from error
    image, fit = _lay(mask, area)
    return {"image": image, "fit": fit}


def report(area: LandArea, url: str, settings: NewWorldSettings) -> dict[str, object]:
    """What the generator will do with the picture: numbers the window turns into sentences."""
    found = landeditor.check(kinds_of(url, area), area, settings)
    return {
        "land": found.land_permille,
        "mountains": found.mountains,
        "highlands": found.highlands,
        "lowlands": found.lowlands,
        "lakes": found.lakes,
        "outside": found.outside_permille,
        "kept": found.kept_percent,
        "specks": found.specks,
        "open_lakes": [list(place) for place in found.open_lakes],
        "islands": found.islands_touched,
        "low": landmask.MIN_LAND_PERMILLE,
        "high": landmask.MAX_LAND_PERMILLE,
        "refusal": found.refusal,
    }
