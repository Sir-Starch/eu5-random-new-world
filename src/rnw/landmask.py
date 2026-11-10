"""Land drawn in an image: a continent from another tool, or from a painter, to build a world on.

A player may bring a picture of land and sea (white land on black sea, any size of the right
proportions) instead of letting the generator draw the land. The rest is generated on it: the
cells, relief, climate, rivers, resources and peoples (ADR 0010, C, G4).

Colours say more than land and sea. A picture may mark **mountains**, **highlands**, **lowlands**
and **lakes** (``KIND_COLORS``): the relief is raised or kept flat there and the lakes stay lakes.
A picture of greys is read as it always was, white land on black sea, and has the id it always
had; colours are read only where a pixel is clearly one of the four (``CHROMA_MIN``,
``COLOR_TOLERANCE``), so a stroke blurred at its edge or a JPEG's noise falls back to land or sea.

A code cannot hold an image, so it holds the image's **id**, 48 bits of the hash of what it draws
(``Settings.mask``); the picture itself lives in the world's folder (``land_mask.png``) and in a
world file, and a world made again from its code needs it. The id is of the drawing and not of
the file, so the same drawing saved by another program has the same id.

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
from rnw.messages import say
from rnw.png import COLOR_GRAY, COLOR_RGB, encode_png
from rnw.relief import FLANK_BLUR, HINT_BLUR, HINT_STEP, ReliefHints

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
# A drawing is smoothed before it is stretched: a binomial blur of 8 (a standard deviation of
# 1.4 picture pixels, in whole numbers adding up to ``BLUR_UNIT`` along an axis) takes the
# staircase of a stroke's pixels out of a coast and leaves what is a few pixels across. The blur
# is then kept to ``VALUE_UNIT`` levels, so that the stretch below stays in 32 bits.
BLUR_TAPS: Final[tuple[int, ...]] = (1, 8, 28, 56, 70, 56, 28, 8, 1)
BLUR_UNIT: Final[int] = sum(BLUR_TAPS)
VALUE_UNIT: Final[int] = 256
# The cubic B-spline's weights are whole numbers adding up to this, so the arithmetic is exact.
TAP_UNIT: Final[int] = 1 << 10
PERMILLE: Final[int] = 1000

# What a pixel of a drawing is. A kind is its index in ``KIND_COLORS``.
SEA: Final[int] = 0
LAND: Final[int] = 1
MOUNTAINS: Final[int] = 2
HIGHLANDS: Final[int] = 3
LOWLANDS: Final[int] = 4
LAKE: Final[int] = 5
KINDS: Final[int] = 6
KIND_COLORS: Final[tuple[tuple[int, int, int], ...]] = (
    (0, 0, 0),
    (255, 255, 255),
    (160, 82, 45),
    (218, 165, 32),
    (124, 205, 124),
    (30, 144, 255),
)
# Which kinds are land: a lake is water, everything else with a ground is land.
IS_LAND: Final[tuple[bool, ...]] = (False, True, True, True, True, False)
# A pixel is taken for a colour only when it is coloured (the largest channel exceeds the
# smallest by ``CHROMA_MIN``) and within ``COLOR_TOLERANCE`` of it in RGB; grey is land or sea.
CHROMA_MIN: Final[int] = 40
COLOR_TOLERANCE: Final[int] = 70
STRIP_ROWS: Final[int] = 256


class LandMaskError(ValueError):
    """A picture that cannot be land: unreadable, too small or large, all land or all sea,
    or the wrong shape for the New World."""


@dataclass(frozen=True, slots=True, eq=False)
class LandMask:
    """What the picture draws, at the picture's own size: land (True) and sea (False), and when
    the picture marks mountains, highlands, lowlands or lakes, the ``kinds`` of every pixel.

    A mask of land and sea alone has ``kinds`` None, whatever it was read from; ``land`` always
    agrees with ``kinds``.
    """

    land: NDArray[np.bool_]
    kinds: NDArray[np.uint8] | None = None

    @property
    def size(self) -> tuple[int, int]:
        """Height and width of the picture."""
        height, width = self.land.shape
        return int(height), int(width)

    @property
    def sha256(self) -> str:
        """The hash of the size and the drawing: the same on every machine and in every file
        format. Land and sea alone hash as they always did; marked ground adds its kinds."""
        digest = hashlib.sha256()
        digest.update(f"{self.size[0]}x{self.size[1]}:".encode("ascii"))
        digest.update(np.packbits(self.land, axis=None).tobytes())
        if self.kinds is not None:
            digest.update(b"|kinds:")
            digest.update(self.kinds.tobytes())
        return digest.hexdigest()

    @property
    def id(self) -> int:
        """The first ``ID_BITS`` bits of the hash: what a world code holds of the picture."""
        return int(self.sha256[: ID_BITS // 4], 16)

    @property
    def share(self) -> int:
        """Land in permille of the picture."""
        return int(np.count_nonzero(self.land)) * PERMILLE // int(self.land.size)

    def count(self, kind: int) -> int:
        """Pixels of one kind (``LAND`` and ``SEA`` too)."""
        if self.kinds is not None:
            return int(np.count_nonzero(self.kinds == kind))
        if kind == LAND:
            return int(np.count_nonzero(self.land))
        return int(np.count_nonzero(~self.land)) if kind == SEA else 0

    def png(self) -> bytes:
        """The picture as a PNG, the form the world's folder keeps: grey (255 land, 0 sea) for
        land and sea alone, in the colours of ``KIND_COLORS`` when ground is marked."""
        if self.kinds is None:
            grey = np.where(self.land, 255, 0).astype(np.uint8)
            return encode_png(grey, color_type=COLOR_GRAY, compression="zlib")
        palette = np.array(KIND_COLORS, dtype=np.uint8)
        return encode_png(palette[self.kinds], color_type=COLOR_RGB, compression="zlib")


def decode_kinds(data: bytes) -> NDArray[np.uint8]:
    """The kind of every pixel of a picture, or ``LandMaskError``; nothing about its land is
    checked, so a drawing that is not yet a world (an empty sheet) reads."""
    try:
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            if min(width, height) < MIN_SIDE or width * height > MAX_PIXELS:
                return _refuse_size(width, height)
            _ = image.load()
            kinds = np.empty((height, width), dtype=np.uint8)
            for top in range(0, height, STRIP_ROWS):
                bottom = min(height, top + STRIP_ROWS)
                rgba = image.crop((0, top, width, bottom)).convert("RGBA")
                kinds[top:bottom] = _kinds_of(np.asarray(rgba), np.asarray(rgba.convert("L")))
            return kinds
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        message = say("mask.unreadable", error=error)
        raise LandMaskError(message) from error


def _kinds_of(rgba: NDArray[np.uint8], grey: NDArray[np.uint8]) -> NDArray[np.uint8]:
    """The kinds of a strip of pixels: bright and opaque is land, the rest is sea, and a pixel
    that is clearly one of the marked colours is that kind (a lake is water, the others land)."""
    opaque = rgba[..., 3] >= THRESHOLD
    kinds = np.where((grey >= THRESHOLD) & opaque, LAND, SEA).astype(np.uint8)
    rgb = rgba[..., :3].astype(np.int32)
    coloured = opaque & (rgb.max(axis=2) - rgb.min(axis=2) >= CHROMA_MIN)
    if not coloured.any():
        return kinds
    pixels = rgb[coloured]
    palette = np.array(KIND_COLORS[MOUNTAINS:], dtype=np.int32)
    distance = ((pixels[:, np.newaxis, :] - palette[np.newaxis, :, :]) ** 2).sum(axis=2)
    nearest = distance.argmin(axis=1)
    close = distance[np.arange(len(pixels)), nearest] <= COLOR_TOLERANCE**2
    kinds[coloured] = np.where(close, MOUNTAINS + nearest, kinds[coloured]).astype(np.uint8)
    return kinds


def _refuse_size(width: int, height: int) -> NDArray[np.uint8]:
    message = say(
        "mask.size", width=width, height=height, side=MIN_SIDE, millions=MAX_PIXELS // 1_000_000
    )
    raise LandMaskError(message)


def from_kinds(kinds: NDArray[np.uint8]) -> LandMask:
    """The mask of a picture of kinds (no check of its size or share): land and sea alone are
    kept as such, so the same land has the same id however it was drawn."""
    if kinds.max(initial=0) >= KINDS:
        message = f"A pixel of kind {int(kinds.max())} is none of the {KINDS} kinds"
        raise ValueError(message)
    land = np.array(IS_LAND, dtype=np.bool_)[kinds]
    marked = bool(np.any(kinds >= MOUNTAINS))
    return LandMask(land, kinds if marked else None)


def from_bytes(data: bytes) -> LandMask:
    """The drawing of a picture; raises ``LandMaskError`` for one that cannot be a world."""
    mask = from_kinds(decode_kinds(data))
    if not MIN_LAND_PERMILLE <= mask.share <= MAX_LAND_PERMILLE:
        message = say(
            "mask.share",
            share=f"{mask.share / 10:.1f}",
            low=f"{MIN_LAND_PERMILLE / 10:.0f}",
            high=f"{MAX_LAND_PERMILLE / 10:.0f}",
        )
        raise LandMaskError(message)
    return mask


def read(path: Path) -> LandMask:
    """``from_bytes`` of the file at ``path``."""
    try:
        return from_bytes(path.read_bytes())
    except OSError as error:
        message = say("mask.file", name=path.name, error=error)
        raise LandMaskError(message) from error


class _Taps:
    """How the four source pixels round a canvas pixel add up along one axis.

    A canvas pixel's centre lies at ``position = (2 c + 1) * source / (2 * canvas) - 1 / 2`` in
    source pixels; ``first`` is the pixel at or before it and ``weights`` the cubic B-spline's
    four weights of ``first - 1 .. first + 2`` (``TAP_UNIT`` in all). Both come from exact integer
    arithmetic, so the same drawing gives the same land on every machine. Indices past the picture
    take its edge pixel.
    """

    first: NDArray[np.int64]
    weights: NDArray[np.int32]

    def __init__(self, source: int, canvas: int) -> None:
        # Position c lies at ``(2 c + 1) * source - canvas`` over ``2 * canvas``.
        whole = 2 * canvas
        if 12 * whole**3 * TAP_UNIT >= 1 << 63:
            message = f"A canvas {canvas} pixels across is too large for the exact stretch"
            raise ValueError(message)
        top = (2 * np.arange(canvas, dtype=np.int64) + 1) * source - canvas
        self.first = top // whole
        a = top - self.first * whole  # the fraction past ``first``, over ``whole``
        cube, unit = whole**3, TAP_UNIT
        # The spline's weights times 6 * whole**3; the four add up to exactly that.
        parts = (
            (whole - a) ** 3,
            3 * a**3 - 6 * a**2 * whole + 4 * cube,
            -3 * a**3 + 3 * a**2 * whole + 3 * a * whole**2 + cube,
            a**3,
        )
        scaled = np.stack([(2 * part * unit + 6 * cube) // (12 * cube) for part in parts])
        # Rounding may leave the sum a unit or two off ``TAP_UNIT``: the centre pixels take it.
        scaled[1] += unit - scaled.sum(axis=0)
        self.weights = scaled.astype(np.int32)

    def index(self, tap: int, limit: int) -> NDArray[np.int64]:
        """The source pixel of tap ``tap`` (0 to 3) of every canvas pixel."""
        return np.clip(self.first + tap - 1, 0, limit - 1)


def _blurred(indicator: NDArray[np.bool_]) -> NDArray[np.int32]:
    """``indicator`` blurred by ``BLUR_TAPS`` along both axes, in ``VALUE_UNIT`` levels (rounded),
    with the picture's edge pixels carried on past its edge."""
    reach = len(BLUR_TAPS) // 2
    blurred = indicator.astype(np.int32)
    for axis in (0, 1):
        along = np.arange(int(blurred.shape[axis]), dtype=np.int64)
        total = np.zeros_like(blurred)
        for tap, weight in enumerate(BLUR_TAPS):
            total += weight * blurred.take(along + tap - reach, axis=axis, mode="clip")
        blurred = total
    step = BLUR_UNIT**2 // VALUE_UNIT
    return (blurred + step // 2) // step


def _stretch(indicator: NDArray[np.bool_], shape: tuple[int, int]) -> NDArray[np.bool_]:
    """``indicator`` on a canvas of ``shape``.

    A picture the canvas does not outgrow is read pixel by pixel. A smaller one is stretched
    smoothly: the picture is blurred, each pixel of the canvas takes the blur round it
    through a cubic B-spline (smooth in itself) and is land where that reaches half. A straight
    coast stays where it was drawn, and the steps of the drawing's pixels, which a stretch by
    whole pixels leaves as a staircase on the shore, become curves; a feature a pixel or two wide
    goes. Done in strips of canvas rows and in integers: the same on every machine.
    """
    height, width = shape
    rows, columns = indicator.shape
    if height <= rows or width <= columns:
        source_rows = np.arange(height, dtype=np.int64) * rows // height
        source_columns = np.arange(width, dtype=np.int64) * columns // width
        return indicator[np.ix_(source_rows, source_columns)]
    across = _Taps(columns, width)
    down = _Taps(rows, height)
    across_index = [across.index(tap, columns) for tap in range(4)]
    values = _blurred(indicator)
    fitted = np.empty((height, width), dtype=np.bool_)
    for top in range(0, height, STRIP_ROWS):
        strip = slice(top, min(height, top + STRIP_ROWS))
        wanted = [down.index(tap, rows)[strip] for tap in range(4)]
        first = int(min(index.min() for index in wanted))
        last = int(max(index.max() for index in wanted))
        # The picture's rows this strip reads, already stretched across.
        flat = np.zeros((last - first + 1, width), dtype=np.int32)
        for tap in range(4):
            flat += values[first : last + 1][:, across_index[tap]] * across.weights[tap]
        total = np.zeros((strip.stop - top, width), dtype=np.int32)
        for tap in range(4):
            total += flat[wanted[tap] - first] * down.weights[tap, strip, np.newaxis]
        fitted[strip] = total >= TAP_UNIT**2 * VALUE_UNIT // 2
    return fitted


def fit(mask: LandMask, shape: tuple[int, int]) -> NDArray[np.bool_]:
    """The picture's land on a canvas of ``shape`` (rows, columns).

    The picture's proportions must be the canvas's, within ``ASPECT_PERMILLE``. A picture the
    canvas does not outgrow is read pixel by pixel; a smaller one is stretched smoothly, so that
    its coasts are curves and not a staircase of its pixels (``_stretch``). Deterministic.
    """
    height, width = shape
    rows, columns = mask.size
    wanted = width * PERMILLE // height
    given = columns * PERMILLE // rows
    if abs(given - wanted) * PERMILLE > ASPECT_PERMILLE * wanted:
        message = say(
            "mask.aspect",
            given=f"{given / 1000:.2f}",
            wanted=f"{wanted / 1000:.2f}",
            width=round(wanted * rows / 1000),
            height=rows,
        )
        raise LandMaskError(message)
    return _stretch(mask.land, shape)


@dataclass(frozen=True, slots=True, eq=False)
class Fitted:
    """A drawing on a canvas: its land, the lakes it marks and the relief it asks for.

    ``lakes`` and ``hints`` are None for a drawing of land and sea alone, which is built on
    exactly as it always was.
    """

    land: NDArray[np.bool_]
    lakes: NDArray[np.bool_] | None
    hints: ReliefHints | None


def _coverage(indicator: NDArray[np.bool_], rows: int, columns: int) -> NDArray[np.int64]:
    """The share of each of ``rows`` by ``columns`` blocks of the picture that the indicator
    covers, in permille: the mean of the pixels in a block (a picture smaller than the grid
    gives each pixel to every block it spans)."""
    height, width = indicator.shape
    row_edges = np.arange(rows + 1, dtype=np.int64) * height // rows
    column_starts = np.minimum(np.arange(columns, dtype=np.int64) * width // columns, width - 1)
    spans = np.maximum(1, np.diff(np.append(column_starts, width)))
    covered = np.empty((rows, columns), dtype=np.int64)
    for row in range(rows):
        first = min(int(row_edges[row]), height - 1)
        last = max(int(row_edges[row + 1]), first + 1)
        counts = indicator[first:last].sum(axis=0, dtype=np.int64)
        sums = np.add.reduceat(counts, column_starts)
        covered[row] = sums * PERMILLE // ((last - first) * spans)
    return covered


def _hint_grid(
    indicator: NDArray[np.bool_], shape: tuple[int, int], blur: int = HINT_BLUR
) -> NDArray[np.int32]:
    """The coverage of one kind on the grid of ``ReliefHints``, smoothed over ``blur`` cells."""
    rows, columns = -(-shape[0] // HINT_STEP), -(-shape[1] // HINT_STEP)
    smooth = box_blur(_coverage(indicator, rows, columns), blur)
    return np.pad(smooth, ((0, 1), (0, 1)), mode="edge").astype(np.int32)


def fit_drawing(mask: LandMask, shape: tuple[int, int]) -> Fitted:
    """The drawing on a canvas of ``shape``: ``fit``'s land, less the lakes the drawing marks
    (a lake is cut out of the land, and wins where the smoothed edges meet), and the relief
    hints of its mountains, highlands and lowlands. Deterministic."""
    land = fit(mask, shape)
    kinds = mask.kinds
    if kinds is None:
        return Fitted(land, None, None)
    lakes = _stretch(kinds == LAKE, shape) if np.any(kinds == LAKE) else None
    if lakes is not None:
        land &= ~lakes
    marked = [kinds == kind for kind in (MOUNTAINS, HIGHLANDS, LOWLANDS)]
    hints = (
        ReliefHints(
            mountains=_hint_grid(marked[0], shape),
            highlands=_hint_grid(marked[1], shape),
            lowlands=_hint_grid(marked[2], shape),
            flanks=_hint_grid(marked[0], shape, FLANK_BLUR),
        )
        if any(found.any() for found in marked)
        else None
    )
    return Fitted(land, lakes, hints)


def to_png_file(mask: LandMask, path: Path) -> None:
    """Write the picture's PNG form at ``path``."""
    _ = path.write_bytes(mask.png())
