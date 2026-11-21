"""The land editor's sheet: a picture of kinds (sea, land, mountains, highlands, lowlands, lake),
the tools that change it and the undo of every change.

This is the classic window's twin of ``desktop/src/lib/landEditor.ts`` and draws the same shapes
the same way. Nothing here touches Qt, so the tools are tested without a window; the editor's
canvas paints the sheet and hands it the pointer.
"""

# NumPy stubs type array arithmetic, indexing and boolean masks as Any.
# pyright: reportAny=false

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.landmask import HIGHLANDS, KINDS, LAKE, LAND, LOWLANDS, MOUNTAINS, SEA
from rnw.topology import label_components

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = [
    "HIGHLANDS",
    "KINDS",
    "LAKE",
    "LAND",
    "LOWLANDS",
    "MAX_SIZE",
    "MIN_SIZE",
    "MOUNTAINS",
    "SEA",
    "SHOWN",
    "Box",
    "Rule",
    "Sheet",
]

MIN_SIZE: Final[int] = 1
MAX_SIZE: Final[int] = 64
# How many changes can be undone, and how many changed pixels the undo keeps in all.
MAX_UNDO: Final[int] = 80
MAX_UNDO_PIXELS: Final[int] = 24_000_000

# What the editor shows for each kind (the sea lets the area under it show): red, green, blue,
# alpha. The colours of the Tauri editor.
SHOWN: Final[NDArray[np.uint8]] = np.array(
    [
        (0, 0, 0, 0),
        (118, 166, 92, 240),
        (128, 98, 78, 245),
        (214, 176, 80, 240),
        (176, 218, 150, 235),
        (64, 128, 214, 245),
    ],
    dtype=np.uint8,
)
# The kinds that are ground: terrain is painted on these, a lake or the sea over them.
GROUND: Final[NDArray[np.bool_]] = np.array([False, True, True, True, True, False])
# The kinds that mark the kind of ground, painted only on ground when asked.
TERRAIN: Final[tuple[int, ...]] = (MOUNTAINS, HIGHLANDS, LOWLANDS)


@dataclass(frozen=True, slots=True)
class Box:
    """A box of pixels, both corners inside it."""

    x0: int
    y0: int
    x1: int
    y1: int

    def union(self, other: Box) -> Box:
        return Box(
            min(self.x0, other.x0),
            min(self.y0, other.y0),
            max(self.x1, other.x1),
            max(self.y1, other.y1),
        )


@dataclass(frozen=True, slots=True)
class Rule:
    """How a stroke treats what is under it."""

    # Terrain is painted on ground only, never on sea or lakes.
    terrain_on_ground: bool = True
    # Shapes are filled, or only their outline (as thick as the brush).
    filled: bool = True


DEFAULT_RULE: Final[Rule] = Rule()


@dataclass(slots=True)
class _Change:
    """One change of the sheet: the pixels that differ, as they were and as they became."""

    at: NDArray[np.intp]
    before: NDArray[np.uint8]
    after: NDArray[np.uint8]


def _disc(size: int) -> NDArray[np.bool_]:
    """A round dab ``size`` pixels across, as a square mask of ``reach * 2 + 1`` pixels."""
    radius = (size - 1) / 2
    reach = math.ceil(radius)
    limit = (radius + 0.5) ** 2
    offsets = np.arange(-reach, reach + 1)
    return (offsets[:, np.newaxis] ** 2 + offsets[np.newaxis, :] ** 2) <= limit


class Sheet:
    """The picture on the editor's sheet, with what is needed to draw on it and take it back."""

    def __init__(self, width: int, height: int, kinds: NDArray[np.uint8] | None = None) -> None:
        if kinds is not None and kinds.shape != (height, width):
            message = "The picture is not the sheet's size"
            raise ValueError(message)
        self.width: int = width
        self.height: int = height
        self.kinds: NDArray[np.uint8] = (
            np.zeros((height, width), dtype=np.uint8) if kinds is None else kinds.copy()
        )
        self._base: NDArray[np.uint8] | None = None
        self._undone: list[_Change] = []
        self._redone: list[_Change] = []
        self._pixels: int = 0
        self._box: Box | None = None
        self._discs: dict[int, NDArray[np.bool_]] = {}

    def get(self, x: int, y: int) -> int:
        """The kind at a pixel; the sea outside the sheet."""
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return SEA
        return int(self.kinds[y, x])

    # -- what changed, for drawing ---------------------------------------------------------------

    def take_dirty(self) -> Box | None:
        """The box of pixels changed since the last call, or None."""
        box, self._box = self._box, None
        return box

    def _touch(self, box: Box) -> None:
        self._box = box if self._box is None else self._box.union(box)

    def _touch_all(self) -> None:
        self._box = Box(0, 0, self.width - 1, self.height - 1)

    # -- one change: begin, draw, then commit (or cancel) ------------------------------------------

    def begin(self) -> None:
        """Start a change; what is drawn until ``commit`` is one step of the undo."""
        self._base = self.kinds.copy()

    def restore(self) -> None:
        """Throw away what was drawn since ``begin``, to draw again from the start (a preview)."""
        if self._base is None:
            return
        differing = self.kinds != self._base
        if not differing.any():
            return
        rows, columns = np.nonzero(differing)
        self._touch(Box(int(columns.min()), int(rows.min()), int(columns.max()), int(rows.max())))
        self.kinds[...] = self._base

    def commit(self) -> bool:
        """End the change; whether the sheet is different now."""
        base, self._base = self._base, None
        if base is None:
            return False
        at = np.flatnonzero(base != self.kinds)
        if not at.size:
            return False
        flat = self.kinds.reshape(-1)
        self._undone.append(_Change(at, base.reshape(-1)[at], flat[at].copy()))
        self._pixels += int(at.size)
        self._redone = []
        while len(self._undone) > MAX_UNDO or (
            self._pixels > MAX_UNDO_PIXELS and len(self._undone) > 1
        ):
            self._pixels -= int(self._undone.pop(0).at.size)
        return True

    def cancel(self) -> None:
        """End the change and put the sheet back as it was at ``begin``."""
        self.restore()
        self._base = None

    @property
    def drawing(self) -> bool:
        return self._base is not None

    @property
    def can_undo(self) -> bool:
        return bool(self._undone)

    @property
    def can_redo(self) -> bool:
        return bool(self._redone)

    def undo(self) -> bool:
        if not self._undone:
            return False
        change = self._undone.pop()
        self._apply(change, change.before)
        self._pixels -= int(change.at.size)
        self._redone.append(change)
        return True

    def redo(self) -> bool:
        if not self._redone:
            return False
        change = self._redone.pop()
        self._apply(change, change.after)
        self._pixels += int(change.at.size)
        self._undone.append(change)
        return True

    def _apply(self, change: _Change, values: NDArray[np.uint8]) -> None:
        self.kinds.reshape(-1)[change.at] = values
        rows, columns = np.divmod(change.at, self.width)
        self._touch(Box(int(columns.min()), int(rows.min()), int(columns.max()), int(rows.max())))

    def replace(self, kinds: NDArray[np.uint8]) -> bool:
        """Put another picture on the sheet as one change; whether it differs."""
        if kinds.shape != self.kinds.shape:
            message = "The picture is not the sheet's size"
            raise ValueError(message)
        self.begin()
        self.kinds[...] = kinds
        self._touch_all()
        return self.commit()

    def clear(self) -> bool:
        return self.replace(np.zeros_like(self.kinds))

    @property
    def empty(self) -> bool:
        return not self.kinds.any()

    # -- the tools -------------------------------------------------------------------------------

    def _paint(self, x0: int, y0: int, mask: NDArray[np.bool_], kind: int, rule: Rule) -> None:
        """Paint ``kind`` where ``mask`` holds, its top left corner at (x0, y0); the part outside
        the sheet is dropped, and terrain keeps off what is not ground when the rule asks."""
        rows, columns = mask.shape
        top, left = max(0, -y0), max(0, -x0)
        bottom, right = min(rows, self.height - y0), min(columns, self.width - x0)
        if bottom <= top or right <= left:
            return
        mask = mask[top:bottom, left:right]
        window = self.kinds[y0 + top : y0 + bottom, x0 + left : x0 + right]
        chosen = mask & (window != kind)
        if kind in TERRAIN and rule.terrain_on_ground:
            chosen &= GROUND[window]
        if not chosen.any():
            return
        window[chosen] = kind
        found_rows, found_columns = np.nonzero(chosen)
        self._touch(
            Box(
                x0 + left + int(found_columns.min()),
                y0 + top + int(found_rows.min()),
                x0 + left + int(found_columns.max()),
                y0 + top + int(found_rows.max()),
            )
        )

    def stamp(self, x: int, y: int, size: int, kind: int, rule: Rule = DEFAULT_RULE) -> None:
        """A round dab of ``size`` pixels across, centred on a pixel."""
        disc = self._discs.get(size)
        if disc is None:
            disc = self._discs[size] = _disc(size)
        reach = disc.shape[0] // 2
        self._paint(x - reach, y - reach, disc, kind, rule)

    def stroke(  # noqa: PLR0913, PLR0917 - two points, a size, a kind and a rule
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        size: int,
        kind: int,
        rule: Rule = DEFAULT_RULE,
    ) -> None:
        """Dabs along the line from one pixel to another, close enough to leave no gaps."""
        steps = max(abs(x1 - x0), abs(y1 - y0))
        if not steps:
            self.stamp(x0, y0, size, kind, rule)
            return
        spacing = max(1, size // 4)
        for step in range(0, steps + 1, spacing):
            self.stamp(
                round(x0 + (x1 - x0) * step / steps),
                round(y0 + (y1 - y0) * step / steps),
                size,
                kind,
                rule,
            )
        self.stamp(x1, y1, size, kind, rule)

    def rectangle(  # noqa: PLR0913, PLR0917 - two corners, a size, a kind and a rule
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        size: int,
        kind: int,
        rule: Rule = DEFAULT_RULE,
    ) -> None:
        """The rectangle with these two corners, filled or as an outline ``size`` thick."""
        left, right = min(x0, x1), max(x0, x1)
        top, bottom = min(y0, y1), max(y0, y1)
        if rule.filled:
            whole = np.ones((bottom - top + 1, right - left + 1), dtype=np.bool_)
            self._paint(left, top, whole, kind, rule)
            return
        self.stroke(left, top, right, top, size, kind, rule)
        self.stroke(right, top, right, bottom, size, kind, rule)
        self.stroke(right, bottom, left, bottom, size, kind, rule)
        self.stroke(left, bottom, left, top, size, kind, rule)

    def ellipse(  # noqa: PLR0913, PLR0917 - two corners, a size, a kind and a rule
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        size: int,
        kind: int,
        rule: Rule = DEFAULT_RULE,
    ) -> None:
        """The ellipse inside the rectangle with these two corners, filled or as an outline."""
        left, right = min(x0, x1), max(x0, x1)
        top, bottom = min(y0, y1), max(y0, y1)
        centre_x, centre_y = (left + right) / 2, (top + bottom) / 2
        radius_x, radius_y = (right - left) / 2 + 0.5, (bottom - top) / 2 + 0.5
        across = (np.arange(left, right + 1) - centre_x)[np.newaxis, :]
        down = (np.arange(top, bottom + 1) - centre_y)[:, np.newaxis]

        def inside(shrink: float) -> NDArray[np.bool_]:
            a, b = radius_x - shrink, radius_y - shrink
            if a <= 0 or b <= 0:
                return np.zeros((down.size, across.size), dtype=np.bool_)
            return (across / a) ** 2 + (down / b) ** 2 <= 1

        mask = inside(0.0)
        if not rule.filled:
            mask &= ~inside(float(max(1, size)))
        self._paint(left, top, mask, kind, rule)

    def fill(self, x: int, y: int, kind: int, rule: Rule = DEFAULT_RULE) -> int:
        """Paint the whole stretch of equal pixels the pixel belongs to (its four neighbours join
        it); how many pixels were painted."""
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return 0
        target = int(self.kinds[y, x])
        if target == kind or (kind in TERRAIN and rule.terrain_on_ground and not GROUND[target]):
            return 0
        labels = label_components(self.kinds.astype(np.int32))
        stretch = labels == labels[y, x]
        rows, columns = np.nonzero(stretch)
        self.kinds[stretch] = kind
        self._touch(Box(int(columns.min()), int(rows.min()), int(columns.max()), int(rows.max())))
        return int(rows.size)

    def counts(self) -> list[int]:
        """How many pixels there are of each kind."""
        return np.bincount(self.kinds.reshape(-1), minlength=KINDS).tolist()
