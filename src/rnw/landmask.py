"""Land drawn in an image: a continent from another tool, or from a painter, to build a world on.

A player may bring a picture of land and sea (white land on black sea, any size of the right
proportions) instead of letting the generator draw the land. The rest is generated on it: the
cells, relief, climate, rivers, resources and peoples (ADR 0010, C, G4).

A code cannot hold an image, so it holds the image's **id**, 48 bits of the hash of what it draws
(``Settings.mask``); the picture itself lives in the world's folder (``land_mask.png``) and in a
world file, and a world made again from its code needs it. The id is of the land and not of the
file, so the same drawing saved by another program has the same id.

This module reads no game file. ``fit`` turns the image into the canvas the New World is made in;
the generator then keeps the land off the edge of the canvas, takes out specks and refuses a
picture that asks for what the world cannot be.
"""

# NumPy stubs type array shapes and arithmetic as Any.
# pyright: reportAny=false

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np
from PIL import Image

from rnw.fields import box_blur
from rnw.png import COLOR_GRAY, encode_png

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

MIN_SIDE: Final[int] = 64
MAX_PIXELS: Final[int] = 64_000_000
THRESHOLD: Final[int] = 128
# The share of the picture that may be land: below it there is no world, above it no sea.
MIN_LAND_PERMILLE: Final[int] = 30
MAX_LAND_PERMILLE: Final[int] = 900
# How far the picture's proportions may differ from the canvas's, in permille.
ASPECT_PERMILLE: Final[int] = 100
ID_BITS: Final[int] = 48
SMOOTH_ABOVE: Final[int] = 2
PERMILLE: Final[int] = 1000


class LandMaskError(ValueError):
    """A picture that cannot be land: unreadable, too small or large, all land or all sea,
    or the wrong shape for the New World."""


@dataclass(frozen=True, slots=True, eq=False)
class LandMask:
    """What the picture draws: land (True) and sea (False), at the picture's own size."""

    land: NDArray[np.bool_]

    @property
    def size(self) -> tuple[int, int]:
        """Height and width of the picture."""
        height, width = self.land.shape
        return int(height), int(width)

    @property
    def sha256(self) -> str:
        """The hash of the size and the land: the same on every machine and in every file format."""
        digest = hashlib.sha256()
        digest.update(f"{self.size[0]}x{self.size[1]}:".encode("ascii"))
        digest.update(np.packbits(self.land, axis=None).tobytes())
        return digest.hexdigest()

    @property
    def id(self) -> int:
        """The first ``ID_BITS`` bits of the hash: what a world code holds of the picture."""
        return int(self.sha256[: ID_BITS // 4], 16)

    @property
    def share(self) -> int:
        """Land in permille of the picture."""
        return int(np.count_nonzero(self.land)) * PERMILLE // int(self.land.size)

    def png(self) -> bytes:
        """The picture as a grey PNG (255 land, 0 sea), the form the world's folder keeps."""
        grey = np.where(self.land, 255, 0).astype(np.uint8)
        return encode_png(grey, color_type=COLOR_GRAY, compression="zlib")


def _decode(data: bytes) -> tuple[NDArray[np.uint8], NDArray[np.uint8]]:
    """The grey values and the transparency of a picture, or ``LandMaskError``."""
    try:
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            if min(width, height) < MIN_SIDE or width * height > MAX_PIXELS:
                return _refuse_size(width, height)
            rgba = image.convert("RGBA")
            return np.asarray(rgba.convert("L")), np.asarray(rgba)[..., 3]
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        message = f"The picture cannot be read: {error}"
        raise LandMaskError(message) from error


def _refuse_size(width: int, height: int) -> tuple[NDArray[np.uint8], NDArray[np.uint8]]:
    message = (
        f"The picture is {width} x {height}; it must be at least {MIN_SIDE} pixels each way "
        f"and at most {MAX_PIXELS // 1_000_000} million in all"
    )
    raise LandMaskError(message)


def from_bytes(data: bytes) -> LandMask:
    """The land a picture draws; raises ``LandMaskError`` for one that cannot be a world."""
    grey, alpha = _decode(data)
    land = (grey >= THRESHOLD) & (alpha >= THRESHOLD)
    mask = LandMask(land.astype(bool))
    if not MIN_LAND_PERMILLE <= mask.share <= MAX_LAND_PERMILLE:
        message = (
            f"The picture is {mask.share / 10:.1f} % land; a world needs between "
            f"{MIN_LAND_PERMILLE / 10:.0f} % and {MAX_LAND_PERMILLE / 10:.0f} % "
            "(white is land, black is sea)"
        )
        raise LandMaskError(message)
    return mask


def read(path: Path) -> LandMask:
    """``from_bytes`` of the file at ``path``."""
    try:
        return from_bytes(path.read_bytes())
    except OSError as error:
        message = f"{path.name} cannot be read: {error}"
        raise LandMaskError(message) from error


def fit(mask: LandMask, shape: tuple[int, int]) -> NDArray[np.bool_]:
    """The picture's land on a canvas of ``shape`` (rows, columns).

    The picture's proportions must be the canvas's, within ``ASPECT_PERMILLE``; it is stretched
    to it by whole pixels, and when it is much smaller than the canvas its blocky edges are
    smoothed (a blur and a threshold, in integers). Deterministic.
    """
    height, width = shape
    rows, columns = mask.size
    wanted = width * PERMILLE // height
    given = columns * PERMILLE // rows
    if abs(given - wanted) * PERMILLE > ASPECT_PERMILLE * wanted:
        message = (
            f"The picture is {given / 1000:.2f} times as wide as it is high; the New World's "
            f"area is {wanted / 1000:.2f}. Draw it in that proportion (for example "
            f"{round(wanted * rows / 1000)} x {rows} pixels)"
        )
        raise LandMaskError(message)
    source_rows = np.arange(height, dtype=np.int64) * rows // height
    source_columns = np.arange(width, dtype=np.int64) * columns // width
    fitted = mask.land[np.ix_(source_rows, source_columns)]
    scale = min(height // rows, width // columns)
    if scale > SMOOTH_ABOVE:
        smooth = box_blur(fitted.astype(np.int64) * PERMILLE, scale // 2)
        fitted = smooth >= PERMILLE // 2
    return fitted


def to_png_file(mask: LandMask, path: Path) -> None:
    """Write the picture's PNG form at ``path``."""
    _ = path.write_bytes(mask.png())
