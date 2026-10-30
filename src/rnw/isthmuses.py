"""Isthmuses: narrow land that joins two landmasses a strait apart.

Game-independent. Thresholded noise leaves landmasses either well apart or joined by land as
thick as the noise happens to be, and ``straits.pinch`` brings near ones to a five-pixel
channel. The Americas, Suez, the Kra isthmus and Perekop are another kind of place: two
landmasses, or a peninsula and its mainland, joined by a neck of land far narrower than
either. Here a land corridor is raised across the water between two landmasses a moderate
distance apart, narrowest in the middle and flaring at both ends, from the pixels whose
distances to the two landmasses add up to little more than the distance between them.

A bridge is only built if it touches no third landmass, keeps off the protected edge, and
leaves no new piece of water that cannot reach the open sea. Everything is integer
arithmetic on named SplitMix64 streams, so equal inputs give equal bridges everywhere.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.fields import SUBPIXEL, fractal_at
from rnw.noise import NOISE_SCALE
from rnw.progress import checkpoint
from rnw.rng import SplitMix64, derive_seed, mix64
from rnw.straits import NEAR_PX, Gap, narrow_gaps
from rnw.topology import euclidean_distance, label_components

if TYPE_CHECKING:
    from numpy.typing import NDArray

PERMILLE: Final[int] = 1000
EIGHTHS: Final[int] = 8
# Landmasses at most this far apart (permille of the scale length) may be joined, and each
# narrow place between a pair is joined with this chance, so a seed leaves most straits open.
REACH_PERMILLE: Final[int] = 200
BRIDGE_PERMILLE: Final[int] = 450
# Landmasses smaller than this share of the scale length squared are no landmass to join.
MIN_LAND_PERMILLE: Final[int] = 8
# Half-width of the neck at its middle, as permille of the scale length, and at least this
# share of the strait it crosses: a long causeway a few pixels wide is no isthmus.
LENGTH_SHARE_PERMILLE: Final[int] = 125
HALF_WIDTH_MIN_PERMILLE: Final[int] = 4
HALF_WIDTH_MAX_PERMILLE: Final[int] = 13
# How far the land widens towards each end, per distance from that end.
FLARE_PERMILLE: Final[int] = 450
CLEARANCE_PX: Final[int] = 3
# Where two coasts face each other along their whole length every pixel between is as near to
# both as the narrowest place, so the neck is also held within this many half-widths of the
# crossing, a few times its own width, rather than closing the strait from end to end.
BAND_HALF_WIDTHS: Final[int] = 3


@dataclass(slots=True, eq=False)
class _Rasters:
    """The land being joined: landmass labels, land, open-sea water, where land may be added,
    and the pixels raised so far."""

    labels: NDArray[np.int32]
    land: NDArray[np.bool_]
    ocean: NDArray[np.bool_]
    allowed: NDArray[np.bool_]
    raised: NDArray[np.bool_]


def raise_isthmuses(
    land: NDArray[np.bool_],
    ocean: NDArray[np.bool_],
    allowed: NDArray[np.bool_],
    seed: int,
    *,
    scale_px: int,
) -> NDArray[np.bool_]:
    """The water pixels that become isthmus land, for a land mask; nothing else changes.

    ``ocean`` is the water that reaches the open sea; ``allowed`` the pixels where land may
    be added. Bridges are raised one at a time, each seeing the land the earlier ones left.
    """
    land, ocean = land.copy(), ocean.copy()
    parts = label_components(land.astype(np.int32))
    sizes = np.bincount(parts.ravel())
    labels = np.where(land, parts, np.int32(-1))
    del parts
    state = _Rasters(labels, land, ocean, allowed, np.zeros(land.shape, dtype=bool))
    big = sizes >= max(1, scale_px * scale_px * MIN_LAND_PERMILLE // PERMILLE)
    reach = max(NEAR_PX + 2, scale_px * REACH_PERMILLE // PERMILLE)
    gaps = narrow_gaps(labels, ocean, big, reach)
    key = derive_seed(seed, "isthmuses")
    for gap in sorted(gaps.values(), key=lambda item: (item.length, item.first, item.second)):
        checkpoint()
        stream = SplitMix64(mix64(key ^ (gap.first << 32) ^ gap.second))
        chance, drawn = stream.below(PERMILLE), stream.below(PERMILLE)
        if gap.length <= NEAR_PX or chance >= BRIDGE_PERMILLE:
            continue
        half_width = max(
            3,
            scale_px
            * (
                HALF_WIDTH_MIN_PERMILLE
                + drawn * (HALF_WIDTH_MAX_PERMILLE - HALF_WIDTH_MIN_PERMILLE) // PERMILLE
            )
            // PERMILLE,
        )
        half_width = max(half_width, gap.length * LENGTH_SHARE_PERMILLE // PERMILLE)
        _bridge(state, gap, half_width, mix64(stream.next_u64()))
    return state.raised


def _bridge(state: _Rasters, gap: Gap, half_width: int, key: int) -> None:
    """Raise the neck across ``gap`` if it is safe; the rasters are unchanged otherwise."""
    middle = (gap.start + gap.stop) // 2
    row, column = (gap.line, middle) if gap.axis == 0 else (middle, gap.line)
    rows, columns = (int(size) for size in state.land.shape)
    span = 2 * gap.length + 4 * half_width + 12
    window = (
        slice(max(0, row - span), min(rows, row + span + 1)),
        slice(max(0, column - span), min(columns, column + span + 1)),
    )
    names = state.labels[window]
    first, second = names == gap.first, names == gap.second
    others = state.land[window] & ~first & ~second
    water = state.ocean[window]
    limit = 2 * span
    from_first, from_second = euclidean_distance(first, limit), euclidean_distance(second, limit)
    total = from_first + from_second
    shortest = int(total[water].min(initial=EIGHTHS * limit * 2))
    length = max(1, shortest // EIGHTHS)
    ys, xs = np.mgrid[window].astype(np.int64)
    wiggle = fractal_at(
        key,
        xs * SUBPIXEL,
        ys * SUBPIXEL,
        period=max(8, length // 2),
        octaves=2,
        persistence_permille=500,
    )
    slack = 2 * EIGHTHS * half_width * half_width // length + (
        np.minimum(from_first, from_second) * FLARE_PERMILLE // PERMILLE
    )
    slack = np.maximum(slack // 3, slack * (PERMILLE + 500 * wiggle // NOISE_SCALE) // PERMILLE)
    across = np.abs((ys - row) if gap.axis == 0 else (xs - column))
    bridge = (
        water
        & state.allowed[window]
        & (total <= shortest + slack)
        & (across <= BAND_HALF_WIDTHS * half_width)
    )
    near_others = euclidean_distance(others, CLEARANCE_PX + 1) <= EIGHTHS * CLEARANCE_PX
    if not bridge.any() or bool((bridge & near_others).any()):
        return
    # Only a neck that really joins the two landmasses is raised; stray corridor pixels are not.
    joined = label_components((first | second | bridge).astype(np.int32))
    if joined[first][0] != joined[second][0]:
        return
    bridge &= joined == joined[first][0]
    if _closed_water(water & ~bridge) > _closed_water(water):
        return
    state.land[window] |= bridge
    state.ocean[window] &= ~bridge
    state.raised[window] |= bridge
    side = np.where(from_first <= from_second, gap.first, gap.second)
    names[bridge] = side[bridge]


def _closed_water(water: NDArray[np.bool_]) -> int:
    """How many pieces of water do not reach the edge of the window."""
    parts = label_components(water.astype(np.int32))
    edge = np.zeros(parts.shape, dtype=bool)
    edge[[0, -1], :] = True
    edge[:, [0, -1]] = True
    reaching = np.unique(parts[edge & water])
    pieces = np.unique(parts[water])
    return int(np.count_nonzero(~np.isin(pieces, reaching)))
