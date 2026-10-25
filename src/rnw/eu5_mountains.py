"""Vanilla mountain height detail, sampled into the initial primary height sources.

The installed mountain stamps supply eroded crests at vanilla sizes and strengths.
Placements follow the continuous relief, independently of location identities. Baking
their additive contribution into each source band also supplies the same mountains
in the opposite edge's periodic padding, without outside-only instances.
"""

# pyright: reportAny=false
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Protocol

import numpy as np

from rnw.rng import derive_seed, hash_point

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.terrain_tiles import LayerFormat

NAMES: Final[tuple[str, ...]] = ("mountain_01", "mountain_02", "mountain_03")
STEP: Final[int] = 32  # location pixels; stamps overlap along the mountain belt
LOW: Final[int] = 14000
FULL: Final[int] = 20000
UNIT: Final[int] = 1024
# Cosine and sine for eight directions; integers keep Windows and Linux identical.
ROTATIONS: Final[tuple[tuple[int, int], ...]] = (
    (1024, 0), (724, 724), (0, 1024), (-724, 724),
    (-1024, 0), (-724, -724), (0, -1024), (724, -724),
)  # fmt: skip


class HeightSources(Protocol):
    """The installed height layers needed for mountain detail."""

    def layer(
        self, decal: str, kind: str
    ) -> tuple[LayerFormat, NDArray[np.uint16] | NDArray[np.uint8]]: ...


@dataclass(frozen=True, slots=True)
class Mountain:
    """Centre and diameter in decal pixels, with an installed source and rotation."""

    row: int
    column: int
    diameter: int
    source: int
    rotation: int


@dataclass(frozen=True, slots=True, eq=False)
class MountainRelief:
    """Read-only placements and local source images; sampled by terrain bands."""

    sources: tuple[NDArray[np.uint16], ...]
    placements: tuple[Mountain, ...]

    def sample(self, origin: tuple[int, int], shape: tuple[int, int]) -> NDArray[np.int64]:
        """Additive height at a decal window in continuous generation coordinates."""
        column0, row0 = origin
        rows, columns = shape
        out = np.zeros(shape, dtype=np.int64)
        for stamp in self.placements:
            # A rotated square's half-diagonal, rounded up, bounds its support.
            radius = (stamp.diameter * 725 + UNIT - 1) // UNIT
            top, bottom = max(row0, stamp.row - radius), min(row0 + rows, stamp.row + radius + 1)
            left = max(column0, stamp.column - radius)
            right = min(column0 + columns, stamp.column + radius + 1)
            if top >= bottom or left >= right:
                continue
            yy = np.arange(top, bottom, dtype=np.int64)[:, None] - stamp.row
            xx = np.arange(left, right, dtype=np.int64)[None, :] - stamp.column
            cosine, sine = ROTATIONS[stamp.rotation]
            source = self.sources[stamp.source]
            height, width = source.shape
            # Source coordinates in 1/1024 pixels, bilinearly sampled with zero
            # outside. A small edge fade removes the source's nonzero boundary.
            u = (xx * cosine + yy * sine) * width // stamp.diameter + width * UNIT // 2
            v = (yy * cosine - xx * sine) * height // stamp.diameter + height * UNIT // 2
            ix, iy = u // UNIT, v // UNIT
            valid = (ix >= 0) & (ix < width - 1) & (iy >= 0) & (iy < height - 1)
            x, y = np.clip(ix, 0, width - 2), np.clip(iy, 0, height - 2)
            fx, fy = u % UNIT, v % UNIT
            a = source[y, x].astype(np.int64) * (UNIT - fx) + source[y, x + 1] * fx
            b = source[y + 1, x].astype(np.int64) * (UNIT - fx) + source[y + 1, x + 1] * fx
            value = (a * (UNIT - fy) + b * fy) // (UNIT * UNIT)
            edge = np.minimum(
                np.minimum(u, (width - 1) * UNIT - u), np.minimum(v, (height - 1) * UNIT - v)
            )
            fade = np.clip(edge * 32000 // (max(width, height) * UNIT), 0, 1000)
            # Vanilla median strengths are 0.20--0.24. Overlap uses the highest
            # crest instead of summing many stamps into an artificial plateau.
            value = np.where(valid, value * fade // 5000, 0)
            target = out[top - row0 : bottom - row0, left - column0 : right - column0]
            _ = np.maximum(target, value, out=target)
        return out


def mountain_relief(
    store: HeightSources, elevation: NDArray[np.int32], *, seed: int, column0: int
) -> MountainRelief:
    """Plan an overlapping chain on elevated land, before building any height files."""
    sources = tuple(store.layer(name, "height")[1].astype(np.uint16) for name in NAMES)
    if any(source.shape != (UNIT, UNIT) for source in sources):
        message = "Installed mountain height sources must be 1024 by 1024"
        raise ValueError(message)
    key = derive_seed(seed, "mountain_detail")
    placements: list[Mountain] = []
    rows, columns = elevation.shape
    for row in range(STEP // 2, rows, STEP):
        for column in range(STEP // 2, columns, STEP):
            draw = hash_point(key, column, row)
            rr = min(rows - 1, row + int(draw % 9) - 4)
            cc = min(columns - 1, column + int(draw // 9 % 9) - 4)
            if elevation[rr, cc] < LOW:
                continue
            placements.append(
                Mountain(
                    rr * 2,
                    (cc + column0) * 2,
                    112 + int(draw // 81 % 33),
                    int(draw // 2673 % len(sources)),
                    int(draw // 8019 % len(ROTATIONS)),
                )
            )
    return MountainRelief(sources, tuple(placements))
