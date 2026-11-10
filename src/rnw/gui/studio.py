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
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import landeditor, landmask
from rnw.app import candidates as sketches
from rnw.gui import view
from rnw.gui.text import explain
from rnw.landarea import (
    AMERICAS_GREY,
    AREA_GREY,
    EDITOR_STEP,
    ISLANDS_GREY,
    OUTSIDE_GREY,
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
) -> dict[str, object]:
    """What the window needs to open the editor on the sheet ``area`` (the area at
    ``EDITOR_STEP``): the sheet, the picture chosen now (laid on it, with how it was laid), the
    ready lands and the sketched continents."""
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
        "sketches": [
            index for index, one in enumerate(found) if one.picture.shape[:2] == area.picture_shape
        ],
    }


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
