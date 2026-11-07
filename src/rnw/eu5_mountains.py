"""Vanilla mountain height detail, sampled into the initial primary height sources.

The installed mountain stamps supply eroded crests: a dendritic web of valleys falling from
a bright crest line. Vanilla places each by hand along a range, at its own size, stretch and
strength (scales 0.015--1.3, strengths 0.01--0.8). Here a stamp follows the continuous relief
instead of location identities: it is turned so that its crest runs along the local axis of
the range (the direction of least slope in the smoothed relief), and sized and strengthened
by the height there, so the highest massifs carry the strongest stamps, at vanilla's density,
size and strength. Baking
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

from rnw import _native
from rnw.eu5_slots import NO_MATERIAL
from rnw.fields import block_mean, box_blur
from rnw.rng import derive_seed, hash_point

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.terrain_tiles import LayerFormat

NAMES: Final[tuple[str, ...]] = ("mountain_01", "mountain_02", "mountain_03")
STEP: Final[int] = (
    48  # location pixels between candidate stamps; vanilla overlaps its mountains about once
)
JITTER: Final[int] = 12
PLACE: Final[int] = 9000  # smoothed relief from which a stamp may be placed
LOW: Final[int] = 9000  # decal height at which the stamps begin to show
FULL: Final[int] = 14000
CAP: Final[int] = 62000  # no stamp raises a sample past this height; the layer holds 65,535
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
# A candidate cell gets a stamp with a chance (permille) that rises with the square of the height
# above ``PLACE`` from ``CHANCE_LOW`` to ``CHANCE_HIGH`` over ``REACH`` units: foothills seldom
# carry one, the high ranges nearly always.
REACH: Final[int] = 14000
CHANCE_LOW: Final[int] = 200
CHANCE_HIGH: Final[int] = 800
# Vanilla's 3,706 stamps: scale 0.1 / 0.2 / 0.4 at the 10th, 50th and 90th percentile (26, 51
# and 102 location pixels across), so a draw ``u`` in [0, 1] gives ``26 + 100 u u`` pixels. Their
# strength is 0.15 / 0.23 / 0.35; ours is ``0.2 + 0.4 u u``, the strength at which the local
# relief and slope of each height class, with the stamps summed, equal those of vanilla's primary
# heightmaps with its stamps added [V-EXEC 2026-10-31]. The stamp's stretch along its crest is
# drawn within ``STRETCH_MIN``--``STRETCH_MAX`` percent of its width.
ACROSS_MIN: Final[int] = 26
ACROSS_RANGE: Final[int] = 100
STRENGTH_MIN: Final[int] = 200
STRENGTH_RANGE: Final[int] = 400
STRETCH_MIN: Final[int] = 70
STRETCH_MAX: Final[int] = 150
# Strength rises with the height there, from 0.85 to 1.15 of its draw.
RISE_LOW: Final[int] = 850
RISE_RANGE: Final[int] = 300
DRAWS: Final[int] = 1000


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
    # The sources, the materials and the placements as the native kernel reads them.
    _stacked: NDArray[np.uint16] = field(init=False, repr=False)
    _slots: NDArray[np.uint8] = field(init=False, repr=False)
    _table: NDArray[np.int64] = field(init=False, repr=False)

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
        if (
            len({source.shape for source in self.sources}) > 1
            or len({slots.shape for slots in self.materials}) > 1
        ):
            message = "The mountain stamps' sources must share one size, and their materials one"
            raise ValueError(message)
        stacked = (
            np.stack([np.asarray(source, dtype=np.uint16) for source in self.sources])
            if self.sources
            else np.zeros((0, 2, 2), dtype=np.uint16)
        )
        slots = (
            np.stack([np.asarray(layer, dtype=np.uint8) for layer in self.materials])
            if self.materials
            else np.zeros((0, 1, 1), dtype=np.uint8)
        )
        table = np.array(
            [
                (m.row, m.column, m.along, m.across, m.source, m.rotation, m.strength)
                for m in self.placements
            ],
            dtype=np.int64,
        ).reshape(-1, 7)
        object.__setattr__(self, "_stacked", stacked)
        object.__setattr__(self, "_slots", slots)
        object.__setattr__(self, "_table", table)

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
        """Additive height and material slot of a decal window (``origin`` is column, row).

        Heights add, as the engine's ``add`` blend does, and the stamp that is highest at a
        pixel decides its slot, the lower slot on a tie. Vanilla lets the lowest slot win, but
        that turns every dense massif into the first variation. Slots are indices, so they are
        taken from the nearest source pixel; the pattern then follows the stamp's own valleys.
        Each stamp is sampled bilinearly from its source, which it covers turned and stretched,
        with a small fade at the source's edge. The kernel is Rust (ADR 0005); its NumPy
        specification is ``tests/reference/mountains.py``.
        """
        return _native.mountain_stamp(
            self._stacked,
            self._slots,
            self._table,
            self.bounds,
            list(ROTATIONS),
            (int(origin[0]), int(origin[1])),
            (int(shape[0]), int(shape[1])),
            UNIT,
            NO_MATERIAL,
        )


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
            chance = CHANCE_LOW + (CHANCE_HIGH - CHANCE_LOW) * rise * rise // 1_000_000
            if int(picks % DRAWS) >= chance:
                continue
            picks //= DRAWS
            source = int(picks % len(sources))
            axis = int(axes[cell]) if int(coherence[cell]) >= COHERENCE else int(picks // 3 % AXES)
            turn = DIRECTIONS // 2 * int(picks // 3 // AXES % 2)
            picks //= 3 * AXES * 2
            size, stretch_draw, force = (int(picks // DRAWS**n % DRAWS) for n in range(3))
            stretch = STRETCH_MIN + stretch_draw * (STRETCH_MAX - STRETCH_MIN) // DRAWS
            across = ACROSS_MIN + ACROSS_RANGE * size * size // DRAWS**2
            strength = (
                (STRENGTH_MIN + STRENGTH_RANGE * force * force // DRAWS**2)
                * (RISE_LOW + RISE_RANGE * rise // 1000)
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
