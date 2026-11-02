"""Synthetic closed seas with actual flared mouths and a long land route around them."""

# pyright: reportAny=false

from __future__ import annotations

import numpy as np

from rnw.model import CellClass
from rnw.newworld import NewWorld, derive_world


def hourglass(width: int = 8, centres: tuple[int, ...] = (120,), *, height: int = 240) -> NewWorld:
    rows, cols = np.indices((height, 240))
    labels = ((rows // 30) * 8 + cols // 30).astype(np.int32)
    count = int(labels.max()) + 1
    along = np.minimum.reduce([abs(rows - centre) for centre in centres])
    widths = np.minimum(100, width + 2 * along)
    left = 120 - widths // 2
    water = (cols >= left) & (cols < left + widths) & (rows >= 20) & (rows < height - 20)
    labels[water] = count
    return derive_world(labels, (CellClass.LAND,) * count + (CellClass.SEA,), np.zeros_like(labels))
