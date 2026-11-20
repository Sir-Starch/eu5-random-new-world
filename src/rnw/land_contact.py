"""Extend the retained terrain into a generated land connection."""

# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.fields import PERMILLE, box_blur, smoothstep
from rnw.topology import distance_from, nearest_label

if TYPE_CHECKING:
    from numpy.typing import NDArray

REACH: Final[int] = 240
DETAIL_REACH: Final[int] = 36
MATERIAL_REACH: Final[int] = 10


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
        extended = self.height.ravel()[nearest.clip(min=0)].astype(np.int64)
        # The immediate seam reproduces the real shore. Farther in, soften the
        # lines between nearest shore samples before the continent takes over.
        valid = nearest >= 0
        density = box_blur(valid.astype(np.int64) * PERMILLE, 12)
        broad = box_blur(np.where(valid, extended, 0) * PERMILLE, 12)
        smooth = broad // np.maximum(1, density)
        softness = smoothstep(distance.astype(np.int64), 2, 32)
        target = (extended * (PERMILLE - softness) + smooth * softness) // PERMILLE
        return ContactBlend(self.box, self.height, retained, generated, distance, nearest, target)


@dataclass(frozen=True, slots=True, eq=False)
class ContactBlend:
    box: tuple[slice, slice]
    height: NDArray[np.uint16]
    retained: NDArray[np.bool_]
    generated: NDArray[np.bool_]
    distance: NDArray[np.int32]
    nearest: NDArray[np.int32]
    target: NDArray[np.int64]

    def condition(self, relief: NDArray[np.int32]) -> None:
        """Set the height boundary before drainage."""
        local = relief[self.box]
        weight = PERMILLE - smoothstep(self.distance.astype(np.int64), 2, REACH)
        active = self.generated & (weight > 0)
        local[active] = (
            local[active] * (PERMILLE - weight[active]) + self.target[active] * weight[active]
        ) // PERMILLE
        local[self.retained] = self.height[self.retained]

    def keep_shore(self, relief: NDArray[np.int32]) -> None:
        """Taper fine detail so it meets the retained ground continuously."""
        local = relief[self.box]
        weight = PERMILLE - smoothstep(self.distance.astype(np.int64), 2, DETAIL_REACH)
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
