"""Moved-layer copying before factoring the four subpixel scans."""

# pyright: reportAny=false
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override

from rnw.eu5_terrain import DecalStore

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

    from rnw.eu5_islands import Moved
    from rnw.eu5_terrain import Decal
    from rnw.terrain_tiles import LayerFormat


@dataclass(eq=False)
class ShiftedStore(DecalStore):
    """A decal store whose layers show the moved island groups where they now stand.

    The height and material pixels of a moved group are copied to its new place, two decal
    pixels to each location pixel; the old place keeps what it had, because it lies inside
    the canvas and is generated over.
    """

    moved: Moved | None = None

    @override
    def layer(
        self, decal: str, kind: str
    ) -> tuple[LayerFormat, NDArray[np.uint16] | NDArray[np.uint8]]:
        """Vanilla layer ``kind`` of a decal, with the moved groups' pixels at their new places."""
        layer, image = super().layer(decal, kind)
        if self.moved is None:
            return layer, image
        placed = next((item for item in self.decals if item.name == decal), None)
        if placed is None:
            return layer, image
        moved = self.moved
        rows, columns = moved.new_rows, moved.new_columns
        here = (
            (rows >= placed.row0)
            & (rows < placed.row0 + placed.rows)
            & (columns >= placed.column0)
            & (columns < placed.column0 + placed.columns)
        )
        if not here.any():
            return layer, image
        sources: dict[str, NDArray[np.uint16] | NDArray[np.uint8]] = {}
        for sub_row in range(2):
            for sub_column in range(2):
                self._copy(
                    image,
                    placed,
                    kind,
                    (rows[here], columns[here]),
                    (moved.rows[here], moved.columns[here]),
                    (sub_row, sub_column),
                    sources,
                )
        return layer, image

    def _copy(  # noqa: PLR0913, PLR0917 - a copy names the image, both places and the sub-pixel.
        self,
        image: NDArray[np.uint16] | NDArray[np.uint8],
        placed: Decal,
        kind: str,
        target: tuple[NDArray[np.int64], NDArray[np.int64]],
        source: tuple[NDArray[np.int64], NDArray[np.int64]],
        sub: tuple[int, int],
        cache: dict[str, NDArray[np.uint16] | NDArray[np.uint8]],
    ) -> None:
        for origin in self.decals:
            inside = (
                (source[0] >= origin.row0)
                & (source[0] < origin.row0 + origin.rows)
                & (source[1] >= origin.column0)
                & (source[1] < origin.column0 + origin.columns)
            )
            if not inside.any():
                continue
            if origin.name not in cache:
                cache[origin.name] = DecalStore.layer(self, origin.name, kind)[1]
            values = cache[origin.name][
                2 * (source[0][inside] - origin.row0) + sub[0],
                2 * (source[1][inside] - origin.column0) + sub[1],
            ]
            image[
                2 * (target[0][inside] - placed.row0) + sub[0],
                2 * (target[1][inside] - placed.column0) + sub[1],
            ] = values
