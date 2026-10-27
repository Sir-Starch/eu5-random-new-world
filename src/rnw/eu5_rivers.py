"""Serialize continuous rivers into EU5's planar, palette-indexed river raster.

The physical network lives in the rolled geography. The engine discovers its raster
components without wrapping, but its line walker normalizes an out-of-bounds neighbour
to column zero, including the neighbour after the last column. Drawing into the last
column can therefore join separately discovered fragments. Construct drawing endpoints
before that column; the physical network and carved valley remain continuous.
"""

# NumPy stubs type scalar indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

import numpy as np

from rnw.progress import checkpoint
from rnw.rivers import JOIN, NEIGHBOURS4, NONE, SOURCE

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.rivers import Rivers

Pixel = tuple[int, int]


class RiverRasterError(ValueError):
    """A logical river cannot be represented by the supported raster contract."""


def _neighbours(role: NDArray[np.int8], pixel: Pixel, cut: int | None) -> list[Pixel]:
    rows, columns = role.shape
    r, c = pixel
    return [
        (r + dr, c + dc)
        for dr, dc in NEIGHBOURS4
        if 0 <= r + dr < rows
        and 0 <= c + dc < columns
        and c + dc != cut
        and role[r + dr, c + dc] != NONE
    ]


def _distances(role: NDArray[np.int8], start: Pixel, cut: int | None) -> dict[Pixel, int]:
    """Only visit river pixels reachable from a seam contact, never the whole map."""
    distances = {start: 0}
    queue = deque([start])
    while queue:
        pixel = queue.popleft()
        if len(distances) % 4096 == 0:
            checkpoint()
        for other in _neighbours(role, pixel, cut):
            if other not in distances:
                distances[other] = distances[pixel] + 1
                queue.append(other)
    return distances


def _fragment(
    codes: NDArray[np.uint8],
    rivers: Rivers,
    pixels: dict[Pixel, int],
    from_mouth: dict[Pixel, int],
    cut: int,
) -> None:
    """Give a planar tree a leaf start and one tributary marker per confluence."""
    neighbours = {p: _neighbours(rivers.role, p, cut) for p in pixels}
    if sum(map(len, neighbours.values())) != 2 * (len(pixels) - 1):
        message = "a boundary river fragment is not a tree"
        raise RiverRasterError(message)
    leaves = [p for p in pixels if len(neighbours[p]) == 1]
    if not leaves:
        message = "a boundary river fragment has no drawing endpoint"
        raise RiverRasterError(message)
    # Keep the original drawing head when it belongs to this piece; otherwise
    # choose the endpoint furthest upstream in the original, uncut tree. This is a
    # drawing start, not a new geographical spring or an extra drainage basin.
    leaves.sort(key=lambda p: (rivers.role[p] != SOURCE, -from_mouth[p], p))
    # A cut can put two short arms at the far end of a fork. Starting at the
    # old head makes neither arm long enough for a join marker; another leaf
    # can orient the very same tree without adding or removing river pixels.
    root: Pixel | None = None
    for leaf in leaves:
        checkpoint()
        if _drawable_root(leaf, neighbours):
            root = leaf
            break
    if root is None:
        message = "a boundary confluence has no room for its join marker"
        raise RiverRasterError(message)
    codes[root] = SOURCE
    stack = [(root, root)]
    while stack:
        pixel, parent = stack.pop()
        children = [p for p in neighbours[pixel] if p != parent]
        if len(children) > 2:  # noqa: PLR2004
            message = "a boundary river has a non-binary confluence"
            raise RiverRasterError(message)
        if len(children) == 2:  # noqa: PLR2004
            candidates = [p for p in children if len(neighbours[p]) == 2]  # noqa: PLR2004
            if not candidates:
                message = "a boundary confluence has no room for its join marker"
                raise RiverRasterError(message)
            branch = min(
                candidates,
                key=lambda p: (rivers.role[p] != JOIN, int(rivers.flow[p]), p),
            )
            codes[branch] = JOIN
        stack.extend((p, pixel) for p in children)
    if any(
        (codes[p] == SOURCE and len(adjacent) != 1)
        or (codes[p] == JOIN and len(adjacent) != 2)  # noqa: PLR2004
        or (len(adjacent) == 3 and sum(codes[q] == JOIN for q in adjacent) != 1)  # noqa: PLR2004
        for p, adjacent in neighbours.items()
    ):
        message = "serialized boundary river has invalid starts or joins"
        raise RiverRasterError(message)


def _drawable_root(root: Pixel, neighbours: dict[Pixel, list[Pixel]]) -> bool:
    """Whether orienting this unchanged tree from a leaf permits every join marker."""
    stack = [(root, root)]
    while stack:
        pixel, parent = stack.pop()
        children = [p for p in neighbours[pixel] if p != parent]
        if len(children) > 2:  # noqa: PLR2004
            return False
        if len(children) == 2 and not any(len(neighbours[p]) == 2 for p in children):  # noqa: PLR2004
            return False
        stack.extend((p, pixel) for p in children)
    return True


def _mouth(role: NDArray[np.int8], source: Pixel) -> Pixel:
    """Follow the original main line, whose tributary entrances are marked JOIN."""
    pixel, parent = source, source
    visited: set[Pixel] = set()
    while pixel not in visited:
        visited.add(pixel)
        following = [p for p in _neighbours(role, pixel, None) if p != parent and role[p] != JOIN]
        if not following:
            return pixel
        if len(following) != 1:
            message = "a continuous boundary river has an ambiguous main line"
            raise RiverRasterError(message)
        parent, pixel = pixel, following[0]
    message = "a continuous boundary river contains a loop"
    raise RiverRasterError(message)


def encode_rivers(
    rivers: Rivers,
    classes: NDArray[np.int8],
    widths: tuple[int, ...],
    *,
    seam: int,
) -> tuple[NDArray[np.uint8], dict[str, int]]:
    """Write final palette codes within the native walker's bounded drawing domain.

    Uncut networks retain their exact bytes. Only networks with a horizontal edge
    touching the final raster column are visited. Its channel pixels are not line
    primitives in this domain and are explicitly counted. Every other fragment of
    two or more pixels keeps its channel pixels and widths. An isolated point has
    no line to draw and is also counted explicitly; physical fields keep both.
    Input network validation belongs to the caller; invalid fragment topology fails
    loudly, rather than dropping a river or trying another geographical layout.
    """
    codes = np.full(rivers.role.shape, 255, dtype=np.uint8)
    table = np.array(widths, dtype=np.uint8)
    for first in range(0, codes.shape[0], 1024):
        checkpoint()
        last = min(first + 1024, codes.shape[0])
        block = classes[first:last]
        codes[first:last] = np.where(block >= 0, table[np.maximum(block, 0)], 255)
    codes[rivers.role == SOURCE] = SOURCE
    codes[rivers.role == JOIN] = JOIN
    stats = {"cut_networks": 0, "fragments": 0, "isolated_points": 0, "boundary_pixels": 0}
    if not 0 < seam < codes.shape[1]:
        return codes, stats
    cut = seam - 1
    contacts = np.flatnonzero(rivers.role[:, cut] != NONE)
    visited: set[Pixel] = set()
    for row in contacts.tolist():
        checkpoint()
        start = (row, cut)
        if start in visited:
            continue
        network = _distances(rivers.role, start, None)
        visited.update(network)
        sources = [p for p in network if rivers.role[p] == SOURCE]
        if len(sources) != 1:
            message = "a continuous boundary river must have exactly one source"
            raise RiverRasterError(message)
        from_mouth = _distances(rivers.role, _mouth(rivers.role, sources[0]), None)
        for r, c in network:
            codes[r, c] = 255 if c == cut else widths[int(classes[r, c])]
        remaining = {p for p in network if p[1] != cut}
        stats["boundary_pixels"] += len(network) - len(remaining)
        while remaining:
            piece = _distances(rivers.role, min(remaining), cut)
            remaining.difference_update(piece)
            if len(piece) == 1:
                codes[next(iter(piece))] = 255
                stats["isolated_points"] += 1
                continue
            _fragment(codes, rivers, piece, from_mouth, cut)
            stats["fragments"] += 1
        stats["cut_networks"] += 1
    return codes, stats
