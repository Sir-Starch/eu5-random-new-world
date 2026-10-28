"""EU5 river drawing domains and lossless palette encoding.

The native river walker does not provide a verified cylindrical network contract.
The first and last world columns stay outside channel domains, as in vanilla.
Drainage is generated independently on each side before encoding; serialization
never cuts a channel, invents a source or changes a physical river.
"""

# NumPy stubs type scalar indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw.progress import checkpoint
from rnw.rivers import JOIN, NONE, SOURCE, STRIP_ROWS

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.rivers import Rivers


class RiverRasterError(ValueError):
    """A logical river cannot be represented by the supported raster contract."""


def watershed_spans(columns: int, seam: int) -> tuple[tuple[int, int], ...]:
    """Closed, independent channel domains; neither world-edge column is a mouth.

    ``seam`` is the crop column placed at world x=0. Excluding the two world-edge
    samples is a planning constraint only: land, real water and relief are unchanged.
    The divide may coincide with either end of the crop, or lie outside it.
    """
    if not 0 <= seam <= columns:
        return ((0, columns),)
    return tuple(
        (left, right) for left, right in ((0, seam - 1), (seam + 1, columns)) if left < right
    )


def encode_rivers(
    rivers: Rivers,
    classes: NDArray[np.int8],
    widths: tuple[int, ...],
    *,
    seam: int,
) -> tuple[NDArray[np.uint8], dict[str, int]]:
    """Encode the planned network exactly; reject a forbidden edge channel loudly."""
    if rivers.role.shape != classes.shape:
        message = "River roles and width classes must have the same shape"
        raise RiverRasterError(message)
    for column in (seam - 1, seam):
        if 0 <= column < classes.shape[1] and np.any(rivers.role[:, column] != NONE):
            message = "River occupies a closed watershed boundary; generate its basin independently"
            raise RiverRasterError(message)
    codes = np.empty(rivers.role.shape, dtype=np.uint8)
    table = np.array(widths, dtype=np.uint8)
    for first in range(0, codes.shape[0], STRIP_ROWS):
        checkpoint()
        last = min(first + STRIP_ROWS, codes.shape[0])
        block, role = classes[first:last], rivers.role[first:last]
        if np.any((block >= 0) != (role != NONE)) or np.any(block >= len(widths)):
            message = "River width classes must cover exactly the planned channel pixels"
            raise RiverRasterError(message)
        encoded = np.where(block >= 0, table[np.maximum(block, 0)], 255)
        encoded[role == SOURCE] = SOURCE
        encoded[role == JOIN] = JOIN
        codes[first:last] = encoded
    return codes, {"cut_networks": 0, "fragments": 0, "isolated_points": 0, "boundary_pixels": 0}
