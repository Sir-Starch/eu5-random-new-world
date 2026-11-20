"""Extend the retained terrain into a generated land connection."""

# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.fields import PERMILLE, box_blur, smoothstep
from rnw.relief import COAST_HEIGHT
from rnw.topology import distance_from, nearest_label

if TYPE_CHECKING:
    from numpy.typing import NDArray

REACH: Final[int] = 240
DETAIL_REACH: Final[int] = 36
MATERIAL_REACH: Final[int] = 10
# Averages are taken over this many units a pixel, so a window holding only a few retained pixels
# (a thin sliver of weight) is still exact. A scale counts once retained ground fills a few
# millionths of its window, which is little enough to reach as far as its blur does.
PRECISION: Final[int] = 1 << 30
SCALE_PRESENT: Final[tuple[int, int]] = (2, 60)
MILLIONTH: Final[int] = 1_000_000
BLUR_PASSES: Final[int] = 3
# The retained height is carried into the generated land by averages of the retained heights
# round each pixel, over wider and wider reaches the farther it lies from the seam. The nearest
# retained pixel's height, carried straight in, leaves its differences as streaks and, where two
# such pixels' reaches meet, as straight steps (the reaches of a four-step spread are squares).
# Each scale is the reach of a blur (three box passes, a smooth bell), the distance from the seam
# up to which it counts in full and the distance beyond which it counts no more. They apply from
# the widest to the narrowest, so where a narrow scale has no retained ground in reach the wider
# one is what remains.
BLUR_SCALES: Final[tuple[tuple[int, int, int], ...]] = (
    (REACH, REACH, REACH + 1),
    (96, 20, 48),
    (32, 7, 16),
    (9, 2, 5),
)
# The seam itself reproduces the real shore: the nearest retained height up to the first
# distance, fading out by the second.
SEAM_EXACT: Final[tuple[int, int]] = (1, 2)
# Conditioning fades out toward the generated coast, which keeps its own profile down to the
# water, so the retained height does not stand as a cliff at the shore far from the seam.
COAST_TAPER: Final[int] = 32
SEAM_HOLD: Final[tuple[int, int]] = (8, 48)
# A retained shore that the generated sea has cut through high ground would stand over the water
# as a wall whose edge is the staircase of the cut. Within RIM_REACH of any water the retained
# height may rise over the shoreline only as steeply as the steepest vanilla coasts do (RIM_BASE
# at the first pixel, RIM_SLOPE a pixel after it, the 90th percentile of the installed coasts);
# what is above that is compressed to a ``RIM_SOFT``-th, so the ground still reads as it was.
RIM_REACH: Final[int] = 24
RIM_BASE: Final[int] = 1200
RIM_SLOPE: Final[int] = 900
RIM_SOFT: Final[int] = 4
NO_RIM: Final[int] = 1 << 30


def contact_box(
    interface: NDArray[np.bool_],
) -> tuple[slice, slice] | None:
    """Only read installed heights within reach of a possible junction."""
    rows, columns = (np.flatnonzero(interface.any(axis=axis)) for axis in (1, 0))
    if not len(rows):
        return None
    return (
        slice(max(0, int(rows[0]) - REACH), min(len(interface), int(rows[-1]) + REACH + 1)),
        slice(
            max(0, int(columns[0]) - REACH),
            min(interface.shape[1], int(columns[-1]) + REACH + 1),
        ),
    )


@dataclass(frozen=True, slots=True, eq=False)
class ContactTerrain:
    """Installed height samples, in the regional domain's local coordinates."""

    box: tuple[slice, slice]
    height: NDArray[np.uint16]

    def blend(
        self, land: NDArray[np.bool_], outside_land: NDArray[np.bool_]
    ) -> ContactBlend | None:
        generated = land[self.box]
        retained = outside_land[self.box]
        shore = retained & (distance_from(generated, 2) == 1)
        if not shore.any():
            return None
        distance = distance_from(shore, REACH, octagonal=True)
        index = np.arange(shore.size, dtype=np.int32).reshape(tuple(map(int, shore.shape)))
        nearest = nearest_label(index, shore, 2 * REACH)
        # The retained heights are averaged over reaches that narrow toward the seam, which then
        # reproduces the real shore.
        carried = self.height.ravel()[nearest.clip(min=0)].astype(np.int64)
        target = carried
        gap = distance.astype(np.int64)
        heights = np.where(retained, self.height.astype(np.int64), 0) * PRECISION
        present = retained.astype(np.int64) * PRECISION
        for reach, held, gone in BLUR_SCALES:
            radius = max(1, reach // BLUR_PASSES)
            weight, total = present, heights
            for _ in range(BLUR_PASSES):
                weight, total = box_blur(weight, radius), box_blur(total, radius)
            average = total // np.maximum(1, weight)
            # Where no retained ground lies within the reach, this scale says nothing.
            share = smoothstep(weight * MILLIONTH // PRECISION, *SCALE_PRESENT)
            step = (PERMILLE - smoothstep(gap, held, gone)) * share // PERMILLE
            target = (target * (PERMILLE - step) + average * step) // PERMILLE
        exact = PERMILLE - smoothstep(gap, *SEAM_EXACT)
        target = (target * (PERMILLE - exact) + carried * exact) // PERMILLE
        water = ~generated & ~retained
        coast = distance_from(water, COAST_TAPER, octagonal=True).astype(np.int64)
        inland = smoothstep(coast, 0, COAST_TAPER)
        # Far from the seam the generated coast keeps its profile; at the seam, ground is ground.
        held = smoothstep(gap, *SEAM_HOLD)
        taper = PERMILLE - held * (PERMILLE - inland) // PERMILLE
        from_water = distance_from(water, RIM_REACH, octagonal=True).astype(np.int64)
        rim = np.where(
            retained & (from_water < RIM_REACH),
            COAST_HEIGHT + RIM_BASE + RIM_SLOPE * (from_water - 1),
            NO_RIM,
        )
        return ContactBlend(
            self.box, self.height, retained, generated, distance, nearest, target, taper, rim
        )


def soften_rim(heights: NDArray[np.int64], rim: NDArray[np.int64]) -> NDArray[np.int64]:
    """Retained ``heights`` with what rises over the ``rim`` limits compressed to a fraction."""
    over = heights - rim
    return np.where(over > 0, rim + over // RIM_SOFT, heights)


@dataclass(frozen=True, slots=True, eq=False)
class ContactBlend:
    box: tuple[slice, slice]
    height: NDArray[np.uint16]
    retained: NDArray[np.bool_]
    generated: NDArray[np.bool_]
    distance: NDArray[np.int32]
    nearest: NDArray[np.int32]
    target: NDArray[np.int64]
    taper: NDArray[np.int64]
    rim: NDArray[np.int64]

    def weight(self, reach: int) -> NDArray[np.int64]:
        """How much of the retained height each generated pixel takes, in permille, within
        ``reach`` of the seam: all of it at the seam, none at the reach or at a distant coast."""
        gap = PERMILLE - smoothstep(self.distance.astype(np.int64), 2, reach)
        return np.where(self.generated, gap * self.taper // PERMILLE, 0)

    def condition(self, relief: NDArray[np.int32]) -> None:
        """Set the height boundary before drainage."""
        local = relief[self.box]
        weight = self.weight(REACH)
        active = self.generated & (weight > 0)
        local[active] = (
            local[active] * (PERMILLE - weight[active]) + self.target[active] * weight[active]
        ) // PERMILLE
        local[self.retained] = self.height[self.retained]

    def keep_shore(self, relief: NDArray[np.int32]) -> None:
        """Taper fine detail so it meets the retained ground continuously."""
        local = relief[self.box]
        weight = self.weight(DETAIL_REACH)
        active = self.generated & (weight > 0)
        local[active] = (
            local[active] * (PERMILLE - weight[active]) + self.target[active] * weight[active]
        ) // PERMILLE

    def biome_votes(
        self, labels: NDArray[np.int32], installed: NDArray[np.int32], old_count: int
    ) -> dict[int, tuple[int, int]]:
        """Read the nearest retained zones into a vote fading inland from the junction."""
        weight = PERMILLE - smoothstep(self.distance.astype(np.int64), 24, 160)
        active = self.generated & (labels >= 0) & (weight > 0)
        generated = labels[active].astype(np.int64)
        foreign = installed.ravel()[self.nearest[active]]
        packed, ids = np.unique(generated * old_count + foreign, return_inverse=True)
        total = np.zeros(len(packed), dtype=np.int64)
        np.add.at(total, ids, weight[active] * np.where(self.distance[active] == 1, 32, 1))
        best: dict[int, tuple[int, int]] = {}
        strengths: dict[int, int] = {}
        for item, votes in zip(packed.tolist(), total.tolist(), strict=True):
            cell, donor = divmod(item, old_count)
            if cell not in best or votes > best[cell][1]:
                best[cell] = donor, votes
        cells, inverse = np.unique(generated, return_inverse=True)
        maximum = np.zeros(len(cells), dtype=np.int64)
        np.maximum.at(maximum, inverse, weight[active])
        strengths.update(zip(cells.tolist(), maximum.tolist(), strict=True))
        return {cell: (donor, strengths[cell]) for cell, (donor, _) in best.items()}
