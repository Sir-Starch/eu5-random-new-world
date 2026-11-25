"""What surrounds a world's generated lands on the game's map, for the map viewer.

The atlas (``rnw.atlas``) holds only what the world generated, so its box shows the lands the
world keeps from the game as open sea: a world of several continents looks like islands adrift,
with nothing to say which is Africa and where Europe would be. Here the viewer gets, for the box,

- which of its pixels are land the world keeps from the game, read from the world's own picture
  (``preview.png``: the map at an eighth with the kept lands in their darker colours, written by
  ``rnw.eu5_nw_export._previews``), and
- the continent of each generated location (America, Africa, Oceania), from its region in the
  installed game's hierarchy (``definitions.txt``).

Both are read on this machine when a world is shown and go nowhere else: nothing of the game's map
enters the atlas or a world file. The box's place on the map is the atlas's ``origin``; a world
made before it was recorded is placed by matching its atlas to its picture, which must agree
exactly where both show generated land and sea, or the world is shown without its surroundings.
"""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.atlas import KINDS

if TYPE_CHECKING:
    from collections.abc import Mapping

    from numpy.typing import NDArray

    from rnw.atlas import Atlas

# The world's picture is the map at an eighth, in these colours (``eu5_nw_export._previews``).
PREVIEW_STEP: Final[int] = 8
KEPT_LAND: Final[tuple[int, int, int]] = (70, 110, 60)
GENERATED_DRY: Final[tuple[tuple[int, int, int], ...]] = ((96, 160, 72), (140, 140, 140))
GENERATED_WET: Final[tuple[tuple[int, int, int], ...]] = ((40, 75, 160), (90, 150, 220))
# The continents a world generates, by the game's key of the continent their regions belong to.
CONTINENTS: Final[tuple[str, ...]] = ("america", "africa", "oceania")
# A placement found by matching may disagree with the picture at this share of the atlas's
# generated pixels (none is expected); the next best placement must disagree at least at
# ``AMBIGUOUS`` times as many, or the match is not trusted.
TOLERANCE: Final[float] = 0.002
AMBIGUOUS: Final[int] = 5


@dataclass(frozen=True, slots=True, eq=False)
class Surroundings:
    """``kept``: the box's pixels that are land the world keeps from the game (box-shaped).
    ``continent``: each location's index in ``CONTINENTS``, -1 for none (a sea, or land of
    another continent)."""

    kept: NDArray[np.bool_] | None
    continent: NDArray[np.int8]


def surroundings(
    atlas: Atlas, preview: NDArray[np.uint8] | None, regions: Mapping[str, str]
) -> Surroundings:
    """The surroundings of ``atlas``: its kept lands from ``preview`` (the world's picture, or
    None), its continents from ``regions`` (the game's continent of each region)."""
    origin = None if preview is None else placed(atlas, preview)
    kept = None if origin is None or preview is None else kept_land(atlas, origin, preview)
    return Surroundings(kept, continents_of(atlas, regions))


def placed(atlas: Atlas, preview: NDArray[np.uint8]) -> tuple[int, int, int, int] | None:
    """Use the recorded origin when it agrees with the full map size of the preview."""
    if atlas.origin is not None:
        _, _, height, width = atlas.origin
        if (-(-height // PREVIEW_STEP), -(-width // PREVIEW_STEP)) == preview.shape[:2]:
            return atlas.origin
    # Early atlases could store the crop width and wrap their column against it.
    return match_origin(atlas, preview)


def match_origin(atlas: Atlas, preview: NDArray[np.uint8]) -> tuple[int, int, int, int] | None:
    """The box's place on the map found from the world's picture: the offset at which every
    generated pixel of the atlas (land or water) meets the same in the picture.

    The picture samples the map's rows and columns at multiples of ``PREVIEW_STEP``, the atlas at
    multiples of its scale from where its box was cut, so one of the four interleaved quarters
    of the box (by row and column parity, for an atlas at half the picture's step) samples the
    same pixels as the picture and agrees with it exactly. Columns wrap around the map.
    """
    if atlas.scale * 2 != PREVIEW_STEP:
        return None
    rows, columns = preview.shape[:2]
    dry_p = _any_colour(preview, GENERATED_DRY)
    wet_p = _any_colour(preview, GENERATED_WET)
    kinds = np.concatenate([np.array([255], dtype=np.uint8), atlas.kinds])[atlas.labels]
    dry_a = (kinds == KINDS.index("land")) | (kinds == KINDS.index("wasteland"))
    wet_a = (kinds == KINDS.index("sea")) | (kinds == KINDS.index("lake"))
    # Per quarter: disagreements at its best offset and at its next best, the offset, the quarter.
    found: list[tuple[int, int, int, int, int, int, int]] = []
    for row_parity in (0, 1):
        for column_parity in (0, 1):
            dry = dry_a[row_parity::2, column_parity::2]
            wet = wet_a[row_parity::2, column_parity::2]
            total = int(np.count_nonzero(dry) + np.count_nonzero(wet))
            if not total or dry.shape[0] > rows or dry.shape[1] > columns:
                continue
            # Rows do not wrap: the box must lie inside the map's height.
            matched = (_correlate(dry, dry_p) + _correlate(wet, wet_p))[: rows - dry.shape[0] + 1]
            order = np.argsort(matched, axis=None)
            dy, dx = divmod(int(order[-1]), matched.shape[1])
            misses = total - round(float(matched.flat[int(order[-1])]))
            runner_up = (
                total - round(float(matched.flat[int(order[-2])])) if order.size > 1 else total
            )
            found.append((misses, runner_up, total, dy, dx, row_parity, column_parity))
    if not found:
        return None
    misses, runner_up, total, dy, dx, row_parity, column_parity = min(found)
    # Another offset of the same quarter must disagree clearly more; a neighbouring quarter of
    # the same place agrees almost as well and gives the same answer.
    if misses > max(2, int(total * TOLERANCE)) or runner_up < AMBIGUOUS * max(misses, 1):
        return None
    height, width = rows * PREVIEW_STEP, columns * PREVIEW_STEP
    half = PREVIEW_STEP // 2
    row = dy * PREVIEW_STEP - row_parity * half
    column = (dx * PREVIEW_STEP - column_parity * half) % width
    return (max(row, 0), column, height, width)


def kept_land(
    atlas: Atlas, origin: tuple[int, int, int, int], preview: NDArray[np.uint8]
) -> NDArray[np.bool_]:
    """The box's pixels that the world's picture shows as land kept from the game."""
    row, column, _height, width = origin
    rows, columns = preview.shape[:2]
    box_rows, box_columns = atlas.size
    picture_rows = np.clip((row + np.arange(box_rows) * atlas.scale) // PREVIEW_STEP, 0, rows - 1)
    picture_columns = (
        ((column + np.arange(box_columns) * atlas.scale) % width) // PREVIEW_STEP
    ).clip(0, columns - 1)
    kept = _any_colour(preview, (KEPT_LAND,))
    return kept[np.ix_(picture_rows, picture_columns)]


def continents_of(atlas: Atlas, regions: Mapping[str, str]) -> NDArray[np.int8]:
    """Each location's index in ``CONTINENTS`` by its region's continent, -1 for a sea or a
    location of another continent. A world made before region keys were recorded names its
    regions by their keys."""
    keys = atlas.region_keys if atlas.region_keys is not None else atlas.regions
    index = {name: number for number, name in enumerate(CONTINENTS)}
    land = {KINDS.index("land"), KINDS.index("wasteland")}
    return np.array(
        [
            index.get(regions.get(key, ""), -1) if isinstance(key, str) and kind in land else -1
            for key, kind in zip(keys, atlas.kinds.tolist(), strict=True)
        ],
        dtype=np.int8,
    )


def _any_colour(
    picture: NDArray[np.uint8], colours: tuple[tuple[int, int, int], ...]
) -> NDArray[np.bool_]:
    rgb = picture[..., :3]
    found = np.zeros(rgb.shape[:2], dtype=np.bool_)
    for colour in colours:
        found |= np.all(rgb == np.array(colour, dtype=np.uint8), axis=-1)
    return found


def _correlate(pattern: NDArray[np.bool_], picture: NDArray[np.bool_]) -> NDArray[np.float64]:
    """For every offset (dy, dx), how many pixels of ``pattern`` meet a pixel of ``picture``:
    columns wrap around the picture's width, rows do not (the picture is padded below)."""
    rows = picture.shape[0] + pattern.shape[0]
    columns = picture.shape[1]
    shape = (rows, columns)
    spectrum = np.fft.rfft2(picture.astype(np.float64), s=shape)
    kernel = np.fft.rfft2(pattern.astype(np.float64), s=shape)
    return np.fft.irfft2(spectrum * np.conj(kernel), s=shape)
