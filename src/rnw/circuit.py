"""The sea route around the world, and the least that opens it.

Game-independent. A ship can sail round the world when the passable water holds a closed
route that winds once about the map's horizontal wrap. This module finds out whether the
locations of a finished raster hold one and, when they do not, which locations to turn into
water to make one: the cheapest set, so the opening is the smallest strait or sea location that
completes the route (a polar tail of land cut through, a closed ocean zone opened), and not a
band of water drawn along an edge. Nothing here draws a random number; ties go to the lower
location.

* **Locations.** A location that straddles the wrap is two pieces, the one at the left edge
  and the one at the right, joined by the wrap itself: sailing from the right piece to the
  left one is the single step that carries a ship round the map.
* **Winding.** Every location gets a sheet number, the count of wraps a ship made reaching it.
  Two contacts that disagree on it close a route round the map.
* **Costs.** A location is passable (cost 0), can be opened at a cost, or is closed (None).
  The cheapest route crosses the wrap once; each crossing is tried and the shortest way back
  to its other side is the answer.
"""

# NumPy stubs type array shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import heapq
from collections import deque
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.topology import adjacency_pairs, unpack_pairs

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

__all__ = ["CircuitError", "cheapest_opening", "has_route"]

STRIP_ROWS: Final[int] = 1024
# A contact and the wraps a ship makes crossing it: 0 inside the map, +1 or -1 over the wrap.
Link = tuple[int, int]


class CircuitError(ValueError):
    """No set of locations the costs allow would open a route round the world."""


def _graph(labels: NDArray[np.int32]) -> tuple[dict[int, list[Link]], NDArray[np.int32]]:
    """The contacts of the locations of ``labels``, with the wraps each one carries, and the
    location (``origin``) that each piece of a location straddling the wrap belongs to."""
    height, width = labels.shape
    count = int(labels.max()) + 1
    straddling = np.intersect1d(labels[:, 0], labels[:, -1]).astype(np.int32)
    table = np.arange(count, dtype=np.int32)
    table[straddling] = count + np.arange(len(straddling), dtype=np.int32)
    half = width // 2
    links: dict[int, set[Link]] = {}

    def join(first: int, second: int, wraps: int) -> None:
        links.setdefault(first, set()).add((second, wraps))
        links.setdefault(second, set()).add((first, -wraps))

    for start in range(0, height, STRIP_ROWS):
        strip = labels[start : start + STRIP_ROWS + 1].copy()
        strip[:, half:] = table[strip[:, half:]]
        for low, high in unpack_pairs(adjacency_pairs(strip)):
            if low >= 0:
                join(low, high, 0)
        across = np.unique(np.stack((strip[:, -1], strip[:, 0]), axis=1), axis=0)
        for first, second in across.tolist():
            if first >= 0 and second >= 0 and first != second:
                join(first, second, 1)
    origin = np.concatenate((np.arange(count, dtype=np.int32), straddling))
    return {node: sorted(found) for node, found in links.items()}, origin


def _usable(costs: Sequence[int | None], origin: NDArray[np.int32]) -> list[int | None]:
    return [costs[int(label)] for label in origin.tolist()]


def _winds(links: dict[int, list[Link]], cost: Sequence[int | None]) -> bool:
    """Whether the passable locations (cost 0) hold a route that winds round the map."""
    sheet: dict[int, int] = {}
    for start in sorted(links):
        if cost[start] != 0 or start in sheet:
            continue
        sheet[start] = 0
        queue = deque([start])
        while queue:
            here = queue.popleft()
            for there, wraps in links[here]:
                if cost[there] != 0:
                    continue
                if there not in sheet:
                    sheet[there] = sheet[here] + wraps
                    queue.append(there)
                elif sheet[there] != sheet[here] + wraps:
                    return True
    return False


def has_route(labels: NDArray[np.int32], passable: Sequence[bool]) -> bool:
    """Whether the locations flagged ``passable`` hold a route winding round the wrapped map."""
    links, origin = _graph(labels)
    return _winds(links, _usable([0 if flag else None for flag in passable], origin))


def cheapest_opening(labels: NDArray[np.int32], costs: Sequence[int | None]) -> tuple[int, ...]:
    """The locations to open for a route round the world, the cheapest set, in ascending order.

    ``costs`` gives each location of ``labels`` 0 if ships can enter it, a positive cost if it
    may be turned into water, and None if it must stay as it is. Empty when a route exists.
    Raises ``CircuitError`` when no allowed set makes one.
    """
    links, origin = _graph(labels)
    cost = _usable(costs, origin)
    if _winds(links, cost):
        return ()
    best: tuple[int, int, int, dict[int, int]] | None = None
    for end in sorted(links):
        if cost[end] is None:
            continue
        for start, wraps in links[end]:
            if wraps != 1 or cost[start] is None:
                continue
            found = _shortest(links, cost, start, end)
            if found is not None and (best is None or found[0] < best[0]):
                best = (found[0], end, start, found[1])
    if best is None:
        message = "No allowed opening gives the world a sea route round it"
        raise CircuitError(message)
    _, end, start, parent = best
    path = [end]
    while path[-1] != start:
        path.append(parent[path[-1]])
    return tuple(sorted({int(origin[node]) for node in path if cost[node]}))


def _shortest(
    links: dict[int, list[Link]], cost: Sequence[int | None], start: int, end: int
) -> tuple[int, dict[int, int]] | None:
    """The cheapest way from ``start`` back to ``end`` without crossing the wrap again: the
    summed cost of the locations on it (both ends included), and each one's predecessor."""
    first = cost[start]
    if first is None:
        return None
    best = {start: first}
    parent: dict[int, int] = {}
    queue = [(first, start)]
    while queue:
        spent, here = heapq.heappop(queue)
        if spent > best[here]:
            continue
        if here == end:
            return spent, parent
        for there, wraps in links[here]:
            price = cost[there]
            if wraps != 0 or price is None:
                continue
            total = spent + price
            if total < best.get(there, total + 1):
                best[there] = total
                parent[there] = here
                heapq.heappush(queue, (total, there))
    return None
