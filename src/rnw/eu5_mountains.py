"""Vanilla mountain height detail, sampled into the initial primary height sources.

The installed mountain stamps supply eroded crests: a dendritic web of valleys falling from
a bright crest line. Vanilla places each by hand along a range, at its own size, stretch and
strength (scales 0.015--1.3, strengths 0.01--0.8). Here a stamp follows the continuous relief
instead of location identities: it is turned so that its crest runs along the local axis of
the range (the direction of least slope in the smoothed relief), and sized and strengthened
by the height there, so the highest massifs carry the largest and strongest stamps. Baking
their additive contribution into each source band also supplies the same mountains in the
opposite edge's periodic padding, without outside-only instances. Each stamp has a material
layer too, slots 10--12 in the pattern of its valleys, which vanilla blends into the terrain's
slots; ``MountainRelief.stamp`` returns both.
"""

# pyright: reportAny=false
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final, Protocol

import numpy as np

from rnw.eu5_slots import NO_MATERIAL
from rnw.fields import block_mean, box_blur
from rnw.rng import derive_seed, hash_point

if TYPE_CHECKING:
    from collections.abc import Iterator

    from numpy.typing import NDArray

    from rnw.terrain_tiles import LayerFormat

NAMES: Final[tuple[str, ...]] = ("mountain_01", "mountain_02", "mountain_03")
STEP: Final[int] = 30  # location pixels; stamps overlap along and across a range
JITTER: Final[int] = 8
PLACE: Final[int] = 10500  # smoothed relief from which a stamp may be placed
LOW: Final[int] = 11000  # decal height at which the stamps begin to show
FULL: Final[int] = 17000
CAP: Final[int] = 52000  # no stamp raises a sample past this height
UNIT: Final[int] = 1024
# Cosine and sine for 32 directions; integers keep Windows and Linux identical.
ROTATIONS: Final[tuple[tuple[int, int], ...]] = (
    (1024, 0), (1004, 200), (946, 392), (851, 569), (724, 724), (569, 851), (392, 946),
    (200, 1004), (0, 1024), (-200, 1004), (-392, 946), (-569, 851), (-724, 724),
    (-851, 569), (-946, 392), (-1004, 200), (-1024, 0), (-1004, -200), (-946, -392),
    (-851, -569), (-724, -724), (-569, -851), (-392, -946), (-200, -1004), (0, -1024),
    (200, -1004), (392, -946), (569, -851), (724, -724), (851, -569), (946, -392),
    (1004, -200),
)  # fmt: skip
DIRECTIONS: Final[int] = len(ROTATIONS)
# Crest axes repeat after half a turn.
AXES: Final[int] = DIRECTIONS // 2
CREST_SHARE: Final[int] = 45  # percent of a source's peak that counts as its crest
# Orientation field: cells of this many location pixels, the relief smoothed twice over
# ``SMOOTH`` cells and the slope's outer products over ``TENSOR`` cells.
CELL: Final[int] = 8
SMOOTH: Final[int] = 3
TENSOR: Final[int] = 4
# Below this share (permille) of slope energy along one direction the ground has no range
# axis (a massif or a plateau), and the stamp is turned at random.
COHERENCE: Final[int] = 250
# Sizes in location pixels across the crest, strengths in permille of the source, and the
# stretch along the crest in percent; each rises from its minimum to its maximum over this
# many height units above ``PLACE`` and is drawn within 0.7--1.3 of that.
REACH: Final[int] = 16000
ACROSS_MIN: Final[int] = 44
ACROSS_MAX: Final[int] = 106
STRENGTH_MIN: Final[int] = 40
STRENGTH_MAX: Final[int] = 150
STRETCH_MIN: Final[int] = 100
STRETCH_MAX: Final[int] = 170
SPREAD_LOW: Final[int] = 700
SPREAD_RANGE: Final[int] = 600


class HeightSources(Protocol):
    """The installed height layers needed for mountain detail."""

    def layer(
        self, decal: str, kind: str
    ) -> tuple[LayerFormat, NDArray[np.uint16] | NDArray[np.uint8]]: ...


@dataclass(frozen=True, slots=True)
class Mountain:
    """Centre and extents in decal pixels, with an installed source, rotation and strength.

    ``along`` is the extent of the source along its crest and ``across`` the extent across it;
    ``rotation`` indexes ``ROTATIONS`` and ``strength`` is in permille of the source's height.
    """

    row: int
    column: int
    along: int
    across: int
    source: int
    rotation: int
    strength: int


@dataclass(frozen=True, slots=True, eq=False)
class MountainRelief:
    """Read-only placements and local source images; sampled by terrain bands.

    ``materials`` are the stamps' own material layers, one per source (empty: none), which
    vanilla blends into the terrain's slots with the lower slot winning.
    """

    sources: tuple[NDArray[np.uint16], ...]
    placements: tuple[Mountain, ...]
    materials: tuple[NDArray[np.uint8], ...] = ()
    # Bounding rows and columns (top, bottom, left, right; inclusive) of each placement.
    bounds: NDArray[np.int64] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Bound each placement's support, a rotated rectangle's half-diagonal rounded up."""
        radii = [(max(m.along, m.across) * 725 + UNIT - 1) // UNIT for m in self.placements]
        rows = [m.row for m in self.placements]
        columns = [m.column for m in self.placements]
        bounds = np.array(
            [
                [row - radius, row + radius, column - radius, column + radius]
                for row, column, radius in zip(rows, columns, radii, strict=True)
            ],
            dtype=np.int64,
        ).reshape(-1, 4)
        object.__setattr__(self, "bounds", bounds)

    def _footprints(
        self, origin: tuple[int, int], shape: tuple[int, int]
    ) -> Iterator[tuple[Mountain, tuple[slice, slice], NDArray[np.int64], NDArray[np.int64]]]:
        """Each stamp that reaches a decal window: its placement, the slices of the window it
        covers and the coordinates in its source there (1/1024 pixels, as ``u`` and ``v``).
        """
        column0, row0 = origin
        rows, columns = shape
        bounds = self.bounds
        near = np.nonzero(
            (bounds[:, 0] < row0 + rows)
            & (bounds[:, 1] >= row0)
            & (bounds[:, 2] < column0 + columns)
            & (bounds[:, 3] >= column0)
        )[0]
        for index in near.tolist():
            stamp = self.placements[index]
            top = max(row0, int(bounds[index, 0]))
            bottom = min(row0 + rows, int(bounds[index, 1]) + 1)
            left = max(column0, int(bounds[index, 2]))
            right = min(column0 + columns, int(bounds[index, 3]) + 1)
            yy = np.arange(top, bottom, dtype=np.int64)[:, None] - stamp.row
            xx = np.arange(left, right, dtype=np.int64)[None, :] - stamp.column
            cosine, sine = ROTATIONS[stamp.rotation]
            height, width = self.sources[stamp.source].shape
            u = (xx * cosine + yy * sine) * width // stamp.along + width * UNIT // 2
            v = (yy * cosine - xx * sine) * height // stamp.across + height * UNIT // 2
            window = (slice(top - row0, bottom - row0), slice(left - column0, right - column0))
            yield stamp, window, u, v

    def sample(self, origin: tuple[int, int], shape: tuple[int, int]) -> NDArray[np.int64]:
        """Additive height at a decal window in continuous generation coordinates."""
        return self.stamp(origin, shape)[0]

    def sample_materials(
        self, origin: tuple[int, int], shape: tuple[int, int]
    ) -> NDArray[np.uint8]:
        """The slots the stamps lay over a decal window, ``NO_MATERIAL`` where none does."""
        return self.stamp(origin, shape)[1]

    def stamp(
        self, origin: tuple[int, int], shape: tuple[int, int]
    ) -> tuple[NDArray[np.int64], NDArray[np.uint8]]:
        """Additive height and material slot of a decal window.

        Overlapping stamps give the highest crest, not the sum, and their slot: where one
        covers a pixel with a slot, the stamp that is highest there decides, the lower slot on
        a tie. Vanilla lets the lowest slot win, but its stamps overlap far less, and here that
        would turn every dense massif into the first variation. Slots are indices, so they are
        taken from the nearest source pixel; the pattern then follows the stamp's own valleys.
        """
        out = np.zeros(shape, dtype=np.int64)
        # Height times 256 plus the complement of the slot; negative where no slot is laid.
        best = np.full(shape, -1, dtype=np.int64)
        for stamp, window, u, v in self._footprints(origin, shape):
            source = self.sources[stamp.source]
            height, width = source.shape
            # Source coordinates in 1/1024 pixels, bilinearly sampled with zero
            # outside. A small edge fade removes the source's nonzero boundary.
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
            value = np.where(valid, value * fade // 1000 * stamp.strength // 1000, 0)
            if self.materials:
                slots = self.materials[stamp.source]
                slot = slots[np.clip(iy, 0, slots.shape[0] - 1), np.clip(ix, 0, slots.shape[1] - 1)]
                laid = (ix >= 0) & (ix < slots.shape[1]) & (iy >= 0) & (iy < slots.shape[0])
                key = np.where(laid & (slot != NO_MATERIAL), value * 256 + 255 - slot, -1)
                target = best[window]
                _ = np.maximum(target, key, out=target)
            target = out[window]
            _ = np.maximum(target, value, out=target)
        return out, np.where(best >= 0, 255 - best % 256, NO_MATERIAL).astype(np.uint8)


def crest_axes(sources: tuple[NDArray[np.uint16], ...]) -> tuple[int, ...]:
    """Direction index (below ``AXES``) of each source's crest: where its top pixels spread most."""
    found: list[int] = []
    for source in sources:
        image = source.astype(np.int64)
        rows, columns = np.nonzero(image >= int(image.max()) * CREST_SHARE // 100)
        rows, columns = rows - int(rows.mean()), columns - int(columns.mean())
        xx, yy, xy = (
            int((columns * columns).sum()),
            int((rows * rows).sum()),
            int((columns * rows).sum()),
        )

        def spread(index: int, xx: int = xx, yy: int = yy, xy: int = xy) -> tuple[int, int]:
            cosine, sine = ROTATIONS[index]
            return cosine * cosine * xx + 2 * cosine * sine * xy + sine * sine * yy, -index

        found.append(max(range(AXES), key=spread))
    return tuple(found)


def _orientation(
    elevation: NDArray[np.int32],
) -> tuple[NDArray[np.int64], NDArray[np.int64], NDArray[np.int64]]:
    """Smoothed relief per cell, its range axis (direction index) and how clear that axis is.

    The axis is the direction of least slope energy: the slope's outer products, averaged
    over a neighbourhood, give the energy along each direction, and along a range's crest
    it is lowest. Coherence is the spread of the energy, in permille.
    """
    smooth = box_blur(box_blur(block_mean(elevation.astype(np.int64), CELL), SMOOTH), SMOOTH)
    padded = np.pad(smooth, 1, mode="edge")
    dx = padded[1:-1, 2:] - padded[1:-1, :-2]
    dy = padded[2:, 1:-1] - padded[:-2, 1:-1]
    xx, yy, xy = (box_blur(values, TENSOR) for values in (dx * dx, dy * dy, dx * dy))
    energy = np.stack(
        [
            cosine * cosine * xx + 2 * cosine * sine * xy + sine * sine * yy
            for cosine, sine in ROTATIONS[:AXES]
        ]
    )
    low, high = energy.min(axis=0), energy.max(axis=0)
    coherence = (high - low) * 1000 // np.maximum(high + low, 1)
    return smooth, energy.argmin(axis=0), coherence


def mountain_relief(
    store: HeightSources, elevation: NDArray[np.int32], *, seed: int, column0: int
) -> MountainRelief:
    """Plan stamps along the ranges of elevated land, before building any height files."""
    sources = tuple(store.layer(name, "height")[1].astype(np.uint16) for name in NAMES)
    materials = tuple(store.layer(name, "materials")[1].astype(np.uint8) for name in NAMES)
    if any(source.shape != (UNIT, UNIT) for source in (*sources, *materials)):
        message = "Installed mountain height and material sources must be 1024 by 1024"
        raise ValueError(message)
    crests = crest_axes(sources)
    smooth, axes, coherence = _orientation(elevation)
    key = derive_seed(seed, "mountain_detail")
    placements: list[Mountain] = []
    rows, columns = elevation.shape
    cells = (int(smooth.shape[0]), int(smooth.shape[1]))
    for row in range(STEP // 2, rows, STEP):
        for column in range(STEP // 2, columns, STEP):
            draw = hash_point(key, column + column0, row)
            span = 2 * JITTER + 1
            rr = min(rows - 1, max(0, row + int(draw % span) - JITTER))
            cc = min(columns - 1, max(0, column + int(draw // span % span) - JITTER))
            cell = (min(cells[0] - 1, rr // CELL), min(cells[1] - 1, cc // CELL))
            height = int(smooth[cell])
            if height < PLACE:
                continue
            rise = min(1000, (height - PLACE) * 1000 // REACH)
            picks = draw // (span * span)
            source = int(picks % len(sources))
            axis = int(axes[cell]) if int(coherence[cell]) >= COHERENCE else int(picks // 3 % AXES)
            turn = DIRECTIONS // 2 * int(picks // 3 // AXES % 2)
            spread = SPREAD_LOW + int(picks // 96 % 1000) * SPREAD_RANGE // 1000
            stretch = STRETCH_MIN + int(picks // 96000 % 1000) * (STRETCH_MAX - STRETCH_MIN) // 1000
            across = (ACROSS_MIN + (ACROSS_MAX - ACROSS_MIN) * rise // 1000) * spread // 1000
            strength = (
                (STRENGTH_MIN + (STRENGTH_MAX - STRENGTH_MIN) * rise // 1000)
                * (SPREAD_LOW + int(picks // 96000000 % 1000) * SPREAD_RANGE // 1000)
                // 1000
            )
            placements.append(
                Mountain(
                    rr * 2,
                    (cc + column0) * 2,
                    across * stretch // 100 * 2,
                    across * 2,
                    source,
                    (axis - crests[source] + turn) % DIRECTIONS,
                    strength,
                )
            )
    return MountainRelief(sources, tuple(placements), materials)
