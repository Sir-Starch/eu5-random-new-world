"""Move land-sea pixel boundaries between existing cells without changing topology.

A pixel may switch from its cell A to a 4-neighbour cell B of the opposite land/sea
class only when its whole 3x3 neighbourhood consists of A and B, B touches it by an
edge, and the remaining A neighbours stay 4-connected around the ring. Consequently:

* every cell stays 4-connected and nonempty (a size floor is enforced);
* no pair of cells gains or loses contact (4- or 8-neighbour), so the cell graph,
  sea-route reachability and port/adjacency partners are unchanged;
* only the land-sea boundary between eligible cells moves.

Pixels are processed on a 3x3 sub-lattice per phase, so simultaneous switches never
share a neighbourhood; a pixel may only move if it was on a boundary when the pass
began, which bounds displacement by the pass count. A signed noise field decides
direction: positive grows land, negative grows sea, stronger values move further.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.noise import NOISE_SCALE

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.settings import CoastSettings

PERMILLE: Final[int] = 1000
RING: Final[tuple[tuple[int, int], ...]] = (
    (-1, 0),
    (-1, 1),
    (0, 1),
    (1, 1),
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, -1),
)
EDGE_POSITIONS: Final[tuple[int, ...]] = (0, 2, 4, 6)
SENTINEL: Final[int] = -1


def _ring_lut() -> NDArray[np.bool_]:
    """Ring masks whose edge-touching A neighbours form exactly one cyclic arc."""
    table = np.zeros(256, dtype=bool)
    for mask in range(256):
        bits = [(mask >> position) & 1 for position in range(8)]
        if all(bits):
            table[mask] = True
            continue
        start = bits.index(0)
        arcs = 0
        touching = False
        for step in range(1, 9):
            position = (start + step) % 8
            if bits[position]:
                touching = touching or position in EDGE_POSITIONS
            else:
                arcs += int(touching)
                touching = False
        table[mask] = arcs == 1
    return table


RING_OK: Final[NDArray[np.bool_]] = _ring_lut()


@dataclass(frozen=True, slots=True, eq=False)
class CoastResult:
    """Moved labels and the pixels that changed class."""

    labels: NDArray[np.int32]
    to_land: NDArray[np.bool_]
    to_sea: NDArray[np.bool_]
    moved_by_pass: tuple[int, ...]


class _Lattice:
    """Strided views of one 3x3 phase inside a 1-pixel padded array."""

    def __init__(self, shape: tuple[int, int], phase_y: int, phase_x: int) -> None:
        height, width = shape
        self.rows: int = len(range(phase_y, height, 3))
        self.columns: int = len(range(phase_x, width, 3))
        self.y: int = phase_y
        self.x: int = phase_x

    def view[T: np.generic](self, padded: NDArray[T], dy: int = 0, dx: int = 0) -> NDArray[T]:
        top = self.y + 1 + dy
        left = self.x + 1 + dx
        return padded[
            top : top + 3 * (self.rows - 1) + 1 : 3,
            left : left + 3 * (self.columns - 1) + 1 : 3,
        ]


def _boundary(padded: NDArray[np.int32]) -> NDArray[np.bool_]:
    """Pixels (padded coordinates) with a 4-neighbour of another label."""
    center = padded[1:-1, 1:-1]
    found = np.zeros(padded.shape, dtype=bool)
    found[1:-1, 1:-1] = (
        (padded[:-2, 1:-1] != center)
        | (padded[2:, 1:-1] != center)
        | (padded[1:-1, :-2] != center)
        | (padded[1:-1, 2:] != center)
    )
    return found


def move_coast(  # noqa: PLR0913 - inputs are independent invariants of one edit.
    labels: NDArray[np.int32],
    *,
    land_ok: NDArray[np.bool_],
    sea_ok: NDArray[np.bool_],
    frozen: NDArray[np.bool_],
    field: NDArray[np.int64],
    settings: CoastSettings,
) -> CoastResult:
    """Return labels with eligible coastlines moved according to ``field``.

    ``land_ok`` and ``sea_ok`` are per-label tables of cells allowed to change; a label
    must never be in both. ``frozen`` marks pixels that must not change. The outer
    ``settings.border_px`` pixels are always frozen.
    """
    if np.any(land_ok & sea_ok):
        message = "A cell cannot be both editable land and editable sea"
        raise ValueError(message)
    count = int(land_ok.size)
    border = settings.border_px
    locked = frozen.copy()
    locked[:border] = True
    locked[-border:] = True
    locked[:, :border] = True
    locked[:, -border:] = True
    padded = np.pad(labels.astype(np.int32), 1, constant_values=SENTINEL)
    locked_padded = np.pad(locked, 1, constant_values=True)
    field_padded = np.pad(field, 1, constant_values=0)
    original = np.bincount(labels.ravel(), minlength=count).astype(np.int64)
    sizes = original.copy()
    floor = (original * settings.min_keep_permille + PERMILLE - 1) // PERMILLE
    cap = original * settings.max_growth_permille // PERMILLE
    lattices = [_Lattice(labels.shape, py, px) for py in range(3) for px in range(3)]
    moved: list[int] = []
    for step in range(settings.passes):
        permille = settings.threshold_base_permille + step * settings.threshold_step_permille
        threshold = NOISE_SCALE * permille // PERMILLE
        on_boundary = _boundary(padded)
        total = 0
        for lattice in lattices:
            total += _phase(
                lattice,
                padded=padded,
                locked=locked_padded,
                field=field_padded,
                on_boundary=on_boundary,
                threshold=threshold,
                tables=(land_ok, sea_ok, sizes, floor, cap),
            )
        moved.append(total)
    result = padded[1:-1, 1:-1].copy()
    land_table = np.zeros(count + 1, dtype=bool)
    sea_table = np.zeros(count + 1, dtype=bool)
    land_table[:count] = land_ok
    sea_table[:count] = sea_ok
    changed = result != labels
    return CoastResult(
        labels=result,
        to_land=changed & land_table[result],
        to_sea=changed & sea_table[result],
        moved_by_pass=tuple(moved),
    )


def _phase(  # noqa: PLR0913 - one phase consumes the shared mutable pass state.
    lattice: _Lattice,
    *,
    padded: NDArray[np.int32],
    locked: NDArray[np.bool_],
    field: NDArray[np.int64],
    on_boundary: NDArray[np.bool_],
    threshold: int,
    tables: tuple[
        NDArray[np.bool_],
        NDArray[np.bool_],
        NDArray[np.int64],
        NDArray[np.int64],
        NDArray[np.int64],
    ],
) -> int:
    land_ok, sea_ok, sizes, floor, cap = tables
    if lattice.rows == 0 or lattice.columns == 0:
        return 0
    center = lattice.view(padded)
    ring = [lattice.view(padded, dy, dx) for dy, dx in RING]
    north, east, south, west = (ring[position] for position in EDGE_POSITIONS)
    other = np.where(
        north != center,
        north,
        np.where(east != center, east, np.where(south != center, south, west)),
    )
    ready = (
        ~lattice.view(locked)
        & lattice.view(on_boundary)
        & (other != center)
        & (other != SENTINEL)
        & (center != SENTINEL)
    )
    for neighbour in ring:
        ready &= (neighbour == center) | (neighbour == other)
    a = np.where(ready, center, 0)
    b = np.where(ready, other, 0)
    values = lattice.view(field)
    to_sea = land_ok[a] & sea_ok[b] & (values < -threshold)
    to_land = sea_ok[a] & land_ok[b] & (values > threshold)
    bits = np.zeros(center.shape, dtype=np.int64)
    for position, neighbour in enumerate(ring):
        bits |= (neighbour == center).astype(np.int64) << position
    ready &= (to_sea | to_land) & RING_OK[bits]
    loss = np.bincount(a[ready], minlength=sizes.size).astype(np.int64)
    gain = np.bincount(b[ready], minlength=sizes.size).astype(np.int64)
    allowed = (sizes - loss >= floor) & (sizes + gain <= cap)
    ready &= allowed[a] & allowed[b]
    loss = np.bincount(a[ready], minlength=sizes.size).astype(np.int64)
    gain = np.bincount(b[ready], minlength=sizes.size).astype(np.int64)
    center[ready] = other[ready]
    sizes -= loss
    sizes += gain
    return int(np.count_nonzero(ready))
