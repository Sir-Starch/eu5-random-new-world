"""Uncropped band construction: reference for trimming work outside the written mask."""

# pyright: reportAny=false, reportPrivateUsage=false
from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING

import numpy as np

from rnw.eu5_mountains import CAP, FULL, LOW
from rnw.eu5_slots import NO_MATERIAL, synthesize
from rnw.eu5_terrain import (
    TerrainRangeError,
    _band_window,
    _lay_stamp_slots,
    _write_where,
    coast_codes,
    decal_heights,
)
from rnw.topology import distance_from

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.eu5_slots import SlotTables
    from rnw.eu5_terrain import Decal, TerrainInputs


def rebuild_band(  # noqa: PLR0913 - a band reads the decal, its rows, the inputs and the images.
    decal: Decal,
    *,
    first: int,
    last: int,
    inputs: TerrainInputs,
    tables: SlotTables,
    seed: int,
    images: tuple[NDArray[np.uint16], NDArray[np.uint8]],
) -> None:
    """Heights and material slots of rows ``first`` to ``last`` of a decal, into ``images``."""
    codes = inputs.codes
    window = _band_window(decal, (int(codes.shape[0]), int(codes.shape[1])), first, last)
    rows = slice(window.row0, window.row1)
    width = int(codes.shape[1])
    columns = np.arange(window.column0, window.column1, dtype=np.int64) % width
    local_water = inputs.vanilla_water[rows][:, columns]
    local_codes = coast_codes(codes[rows][:, columns], local_water)
    relief = inputs.relief(rows, slice(window.column0, window.column1))
    labels = np.repeat(np.repeat(inputs.labels[rows][:, columns], 2, axis=0), 2, axis=1)
    rivers = np.repeat(np.repeat(inputs.rivers[rows][:, columns], 2, axis=0), 2, axis=1)
    river_reach = (
        distance_from(rivers, 12, octagonal=True) if inputs.mountains is not None else None
    )
    # The noise lives in the same rolled coordinates as the land. Its cut is at
    # the canvas's outside edge, not the world seam. Split a decal at that cut so
    # neither a sampling window nor a noise origin restarts at the world wrap.
    cut = (-inputs.noise_roll) % width
    breaks = [0, decal.columns]
    breaks.extend(
        cut + shift - decal.column0
        for shift in (-width, 0, width)
        if decal.column0 < cut + shift < decal.column0 + decal.columns
    )
    breaks.sort()
    for left, right in pairwise(breaks):
        core = (
            slice(window.inner_row, window.inner_row + (last - first) * 2),
            slice(window.inner_column + left * 2, window.inner_column + right * 2),
        )
        origin = (
            ((decal.column0 + left + inputs.noise_roll) % width) * 2
            - (window.inner_column + left * 2),
            window.row0 * 2,
        )
        land, inside, heights = decal_heights(
            local_codes, local_water, relief, seed=seed, origin=origin, core=core
        )
        stamped = None
        if inputs.mountains is not None and river_reach is not None:
            window_origin = (origin[0] + core[1].start, origin[1] + core[0].start)
            detail, laid = inputs.mountains.stamp(window_origin, heights.shape)
            # The stamps' own slots show where their heights do: on the mountains.
            stamped = np.where(inside & (heights >= LOW), laid, NO_MATERIAL)
            gain = np.clip((heights - LOW) * 1000 // (FULL - LOW), 0, 1000)
            raised = heights + np.where(inside, detail * gain // 1000 * river_reach[core] // 12, 0)
            heights = np.minimum(raised, np.maximum(heights, CAP))
            if np.any(heights > np.iinfo(np.uint16).max):
                message = "Mountain detail exceeds the terrain height range"
                raise TerrainRangeError(message)
        target = (slice(first * 2, last * 2), slice(left * 2, right * 2))
        height_image, material_image = images
        _write_where(height_image[target], heights, inside)
        del heights
        slots = synthesize(labels, land, rivers, tables, seed=seed, origin=origin, core=core)
        if stamped is not None:
            slots = _lay_stamp_slots(slots, stamped, labels[core], tables)
        _write_where(material_image[target], slots, inside)
