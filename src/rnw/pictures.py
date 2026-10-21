"""Pictures of a world for the generator's window and the game's mod list, without spoilers.

The export draws the whole map with the generated New World in it (``preview.png``) and the
same map with the New World covered as terra incognita (``preview_hidden.png``). What it
covers is the canvas, which the game build and the preset decide, never the seed, so the
covered picture tells nothing about a world. The game's mod list shows the mod's
``.metadata/thumbnail.png``: a square of the map around the New World, cut from the covered
picture unless the player asks for the uncovered one. Every step is integer arithmetic, so
a picture is the same bytes on every machine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, cast

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

TERRA_INCOGNITA: Final[tuple[int, int, int]] = (58, 52, 44)
BACKGROUND: Final[tuple[int, int, int]] = (14, 26, 46)
SIZE: Final[int] = 512


def cover(
    preview: NDArray[np.uint8], rows: NDArray[np.integer], columns: NDArray[np.integer]
) -> NDArray[np.uint8]:
    """``preview`` with the pixels at ``rows`` and ``columns`` painted as terra incognita."""
    covered = preview.copy()
    covered[rows, columns] = TERRA_INCOGNITA
    return covered


def center_column(hidden: NDArray[np.uint8]) -> int:
    """The column the covered New World centres on (its median covered column)."""
    covered = np.all(np.equal(hidden, np.array(TERRA_INCOGNITA, dtype=np.uint8)), axis=2)
    columns = np.nonzero(covered)[1]
    width = cast("int", hidden.shape[1])
    return int(np.median(columns)) if columns.size else width // 2


def thumbnail(picture: NDArray[np.uint8], center: int) -> NDArray[np.uint8]:
    """A ``SIZE`` square of the map around ``center``, shrunk by whole blocks.

    The map wraps east to west, so the square is cut from the map rolled to ``center``.
    """
    height, width, _ = cast("tuple[int, int, int]", picture.shape)
    side = min(height, width)
    rolled = np.roll(picture, width // 2 - center, axis=1)
    left = width // 2 - side // 2
    window = rolled[:side, left : left + side]
    factor = max(1, -(-side // SIZE))
    cells = side // factor
    blocks = window[: cells * factor, : cells * factor].astype(np.uint32)
    blocks = blocks.reshape(cells, factor, cells, factor, 3).sum(axis=(1, 3))
    area = factor * factor
    small = ((blocks + area // 2) // area).astype(np.uint8)
    square = np.empty((SIZE, SIZE, 3), dtype=np.uint8)
    square[:] = BACKGROUND
    top = (SIZE - cells) // 2
    square[top : top + cells, top : top + cells] = small
    return square
