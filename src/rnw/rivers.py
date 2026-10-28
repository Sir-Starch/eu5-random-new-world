"""Rivers from relief and rainfall: drainage, river network and its pixel paths (V1b).

Game-independent. A priority flood from every water cell on a coarse grid gives each land
cell a downstream neighbour, so all land drains to the sea or a lake and depressions are
crossed instead of trapping water (Barnes, Lehman and Mulla 2014); routing adds fractal
noise to the relief so flow converges into valleys. The square root of rainfall
accumulates down that tree, and cells whose catchment exceeds a threshold, chosen for a
target river density, form the network. Streams split at confluences (the larger branch
continues). Each is drawn at full resolution from its head down a smoothed, gently
meandering centre line until it reaches water (a mouth, a few pixels into the water) or
comes next to a river drawn before (a confluence). Every river is a one-pixel,
4-connected line: interior pixels have two river neighbours and a tributary meets its
river at exactly one pixel. Ties are broken by hashed noise. Arithmetic is integer except
square roots of exact integers, which IEEE arithmetic rounds the same everywhere.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import _native
from rnw.fields import PERMILLE, block_mean, smoothstep, value_noise_at, warped_noise
from rnw.noise import NOISE_SCALE
from rnw.progress import checkpoint
from rnw.rng import MASK64, derive_seed, hash_grid
from rnw.topology import euclidean_distance, label_components, nearest_label

if TYPE_CHECKING:
    from numpy.typing import NDArray

STEP: Final[int] = 4
# Rows per strip of the whole-raster passes; a multiple of STEP.
STRIP_ROWS: Final[int] = 1024
SUBPIXEL: Final[int] = 16
NONE: Final[int] = -1
SOURCE: Final[int] = 0
JOIN: Final[int] = 1
BODY: Final[int] = 2
# Drawn river pixels per 1000 land pixels; the vanilla Old World has 15.7 [V-EXEC C59].
RIVER_PERMILLE: Final[int] = 16
# Coarse river cells drawn per 1000 land pixels for the density target (calibrated: a
# coarse step becomes about 1.25 * STEP pixels of 4-connected line, minus pruning).
CELL_PIXELS_X100: Final[int] = 560
MIN_STREAM_CELLS: Final[int] = 5
# Routing adds fractal noise (period in coarse cells, amplitude in height units) to the
# relief, so flow on smooth slopes converges into valleys instead of running parallel.
VALLEY_PERIOD: Final[int] = 24
VALLEY_HEIGHT: Final[int] = 1600
# Rivers reaching the sea need this many coarse cells, so coasts are not lined with
# short parallel streams; catchments weigh the square root of rainfall, so dry plains
# keep some rivers while wet slopes do not fill with streams.
MIN_MAIN_CELLS: Final[int] = 12
RAIN_UNIT: Final[int] = 1024
MIN_STREAM_PX: Final[int] = 16
MOUTH_PX: Final[int] = 3
JITTER_PX: Final[int] = 1
MEANDER_PX: Final[int] = 2
MEANDER_PERIOD: Final[int] = 14
NEIGHBOURS4: Final[tuple[tuple[int, int], ...]] = ((-1, 0), (1, 0), (0, -1), (0, 1))
CORNERS: Final[tuple[tuple[int, int], ...]] = ((-1, -1), (-1, 1), (1, -1), (1, 1))


@dataclass(frozen=True, slots=True, eq=False)
class Rivers:
    """River pixels of a raster: role (NONE, SOURCE, JOIN, BODY) and catchment flow."""

    role: NDArray[np.int8]
    flow: NDArray[np.int64]
    stats: dict[str, int]


@dataclass(frozen=True, slots=True, eq=False)
class Drainage:
    """Coarse drainage tree in raster order: downstream cell (-1 for water) and catchment."""

    parent: NDArray[np.int64]
    flow: NDArray[np.int64]


class RiverGenerationError(ValueError):
    """A river domain cannot drain to genuine water."""


def drainage(
    land: NDArray[np.bool_], height: NDArray[np.int64], rain: NDArray[np.int64], key: int
) -> Drainage:
    """Priority flood from all water over 8-neighbours; rain accumulated downstream.

    ``land``, ``height`` and ``rain`` are coarse grids. Equal filled heights are taken
    in hashed-noise order, so drainage across flats wanders instead of running straight.
    """
    parent, flow = _native.drainage(
        np.ascontiguousarray(land, dtype=np.bool_),
        np.ascontiguousarray(height, dtype=np.int64),
        np.ascontiguousarray(rain, dtype=np.int64),
        key & MASK64,
    )
    return Drainage(parent=parent, flow=flow)


@dataclass(frozen=True, slots=True)
class Stream:
    """Coarse cells of one stream from its downstream end to its head."""

    cells: tuple[int, ...]
    outlet: int
    parent: int


def streams(tree: Drainage, threshold: int, min_cells: int) -> list[Stream]:
    """River streams, largest catchment first; tributaries name the stream they join.

    At each confluence the branch with the larger catchment continues the stream.
    Streams shorter than ``min_cells`` are dropped with everything upstream of them.
    """
    river = (tree.flow >= threshold) & (tree.parent >= 0)
    children: dict[int, list[int]] = {}
    for cell in np.flatnonzero(river).tolist():
        children.setdefault(int(tree.parent[cell]), []).append(cell)
    flow = tree.flow.tolist()
    heap = [
        (-flow[cell], cell, int(tree.parent[cell]), -1)
        for cell in np.flatnonzero(river).tolist()
        if not river[tree.parent[cell]]
    ]
    heapq.heapify(heap)
    out: list[Stream] = []
    while heap:
        _, start, outlet, parent_stream = heapq.heappop(heap)
        path = [start]
        branches: list[int] = []
        while path[-1] in children:
            options = sorted(children[path[-1]], key=lambda cell: (-flow[cell], cell))
            path.append(options[0])
            branches.extend(options[1:])
        if len(path) < (min_cells if parent_stream >= 0 else max(min_cells, MIN_MAIN_CELLS)):
            continue
        number = len(out)
        out.append(Stream(cells=tuple(path), outlet=outlet, parent=parent_stream))
        for branch in branches:
            heapq.heappush(heap, (-flow[branch], branch, int(tree.parent[branch]), number))
    return out


def river_threshold(tree: Drainage, land_pixels: int) -> int:
    """Catchment above which a land cell carries a river, for the density target."""
    flows = tree.flow[tree.parent >= 0]
    wanted = land_pixels * RIVER_PERMILLE * 100 // (1000 * CELL_PIXELS_X100)
    if flows.size == 0 or wanted <= 0:
        return 1 << 62
    wanted = min(wanted, flows.size)
    return max(1, int(np.partition(flows, flows.size - wanted)[flows.size - wanted]))


def _centres(cells: list[int], columns: int, key: int) -> list[tuple[int, int]]:
    """Jittered centres of coarse cells in subpixels (row, column)."""
    array = np.array(cells, dtype=np.int64)
    r, c = np.divmod(array, columns)
    span = np.uint64(2 * JITTER_PX * SUBPIXEL + 1)
    jitter_r = (hash_grid(key, c, r) >> np.uint64(32)) % span
    jitter_c = (hash_grid(key ^ 0x5A5A, c, r) >> np.uint64(32)) % span
    half = STEP * SUBPIXEL // 2 - JITTER_PX * SUBPIXEL
    rows = r * STEP * SUBPIXEL + half + jitter_r.astype(np.int64)
    cols = c * STEP * SUBPIXEL + half + jitter_c.astype(np.int64)
    return list(zip(rows.tolist(), cols.tolist(), strict=True))


def _smooth(
    points: list[tuple[int, int]], flows: list[int], rounds: int
) -> tuple[list[tuple[int, int]], list[int]]:
    """Chaikin corner cutting; the end points stay and each point keeps a flow."""
    for _ in range(rounds):
        if len(points) < 3:  # noqa: PLR2004 - a corner needs three points
            break
        out = [points[0]]
        out_flows = [flows[0]]
        for index in range(len(points) - 1):
            (r0, c0), (r1, c1) = points[index], points[index + 1]
            out.extend((((3 * r0 + r1) // 4, (3 * c0 + c1) // 4),
                        ((r0 + 3 * r1) // 4, (c0 + 3 * c1) // 4)))  # fmt: skip
            out_flows.extend((flows[index], flows[index + 1]))
        out.append(points[-1])
        out_flows.append(flows[-1])
        points, flows = out, out_flows
    return points, flows


def _meander(points: list[tuple[int, int]], key: int) -> list[tuple[int, int]]:
    """Shift interior points sideways by smooth noise along the line."""
    count = len(points)
    if count < 3:  # noqa: PLR2004 - ends stay fixed
        return points
    phase = np.arange(count, dtype=np.int64) * SUBPIXEL
    wave = value_noise_at(key, phase, np.zeros(count, dtype=np.int64), MEANDER_PERIOD * SUBPIXEL)
    out = [points[0]]
    for index in range(1, count - 1):
        (r0, c0), (r1, c1) = points[index - 1], points[index + 1]
        dr, dc = r1 - r0, c1 - c0
        norm = max(1, math.isqrt(dr * dr + dc * dc))
        shift = int(wave[index]) * MEANDER_PX * SUBPIXEL // NOISE_SCALE
        r, c = points[index]
        out.append((r - dc * shift // norm, c + dr * shift // norm))
    out.append(points[-1])
    return out


def _pixels(points: list[tuple[int, int]], flows: list[int]) -> list[tuple[int, int, int]]:
    """4-connected pixel line (row, column, flow) through subpixel points."""
    out: list[tuple[int, int, int]] = []
    for (r_sub, c_sub), value in zip(points, flows, strict=True):
        target = (r_sub // SUBPIXEL, c_sub // SUBPIXEL)
        if not out:
            out.append((*target, value))
            continue
        r, c, _ = out[-1]
        while (r, c) != target:
            dr, dc = target[0] - r, target[1] - c
            if abs(dr) > abs(dc) or (abs(dr) == abs(dc) and (r + c) % 2 == 0):
                r += 1 if dr > 0 else -1
            else:
                c += 1 if dc > 0 else -1
            out.append((r, c, value))
    return out


@dataclass(slots=True, eq=False)
class _Canvas:
    """Drawing state on the full-resolution raster."""

    land: NDArray[np.bool_]
    role: NDArray[np.int8]
    flow: NDArray[np.int64]
    owner: NDArray[np.int32]

    def free_land(self, r: int, c: int) -> bool:
        rows, columns = self.land.shape
        return 0 <= r < rows and 0 <= c < columns and bool(self.land[r, c]) and self.empty(r, c)

    def inside(self, r: int, c: int) -> bool:
        return 0 <= r < self.land.shape[0] and 0 <= c < self.land.shape[1]

    def empty(self, r: int, c: int) -> bool:
        return int(self.owner[r, c]) < 0

    def rivers_near(
        self, r: int, c: int, steps: tuple[tuple[int, int], ...]
    ) -> list[tuple[int, int]]:
        return [
            (r + dr, c + dc)
            for dr, dc in steps
            if self.inside(r + dr, c + dc) and not self.empty(r + dr, c + dc)
        ]

    def degree(self, r: int, c: int) -> int:
        return len(self.rivers_near(r, c, NEIGHBOURS4))


def _red_ok(canvas: _Canvas, r: int, c: int) -> bool:
    """Whether a free land pixel can be a JOIN pixel: it touches exactly one river pixel.

    That pixel must be a land BODY pixel with two river neighbours, and no other
    junction may lie within one pixel, so every confluence stays readable.
    """
    if not canvas.free_land(r, c):
        return False
    touching = canvas.rivers_near(r, c, NEIGHBOURS4)
    if len(touching) != 1:
        return False
    jr, jc = touching[0]
    if int(canvas.role[jr, jc]) != BODY or not canvas.land[jr, jc] or canvas.degree(jr, jc) != 2:  # noqa: PLR2004
        return False
    if any(int(canvas.role[q]) != BODY for q in canvas.rivers_near(jr, jc, NEIGHBOURS4)):
        return False
    around = canvas.rivers_near(r, c, NEIGHBOURS4 + CORNERS)
    return not any(int(canvas.role[q]) == JOIN or canvas.degree(*q) != 2 for q in around)  # noqa: PLR2004


def _clear(canvas: _Canvas, r: int, c: int, mine: dict[tuple[int, int], int], last: int) -> bool:
    """A free land pixel that touches no river and no own pixel except ``last``'s."""
    if not canvas.free_land(r, c) or canvas.rivers_near(r, c, NEIGHBOURS4 + CORNERS):
        return False
    return all(mine.get((r + dr, c + dc), last) == last for dr, dc in NEIGHBOURS4)


def _reach_river(
    canvas: _Canvas, out: list[tuple[int, int, int]], mine: dict[tuple[int, int], int]
) -> list[tuple[int, int, int]] | None:
    """Shortest free path from the line's end to a valid JOIN pixel nearby (BFS).

    Path pixels touch no river along an edge and no own pixel except the line's end.
    """
    if not out:
        return None
    start = (out[-1][0], out[-1][1])
    value = out[-1][2]
    radius = 2 * STEP
    previous: dict[tuple[int, int], tuple[int, int]] = {start: start}
    frontier = [start]
    while frontier:
        following: list[tuple[int, int]] = []
        for here in frontier:
            for dr, dc in NEIGHBOURS4:
                q = (here[0] + dr, here[1] + dc)
                if q in previous or q in mine:
                    continue
                if abs(q[0] - start[0]) > radius or abs(q[1] - start[1]) > radius:
                    continue
                own = [(q[0] + a, q[1] + b) for a, b in NEIGHBOURS4 if (q[0] + a, q[1] + b) in mine]
                if own != ([start] if here == start else []):
                    continue
                if _red_ok(canvas, *q):
                    path = [q]
                    node = here
                    while node != start:
                        path.append(node)
                        node = previous[node]
                    path.reverse()
                    return [(r, c, value) for r, c in path]
                if not canvas.free_land(*q) or canvas.rivers_near(*q, NEIGHBOURS4):
                    continue
                previous[q] = here
                following.append(q)
        frontier = following
    return None


def _descend(
    canvas: _Canvas, line: list[tuple[int, int, int]]
) -> tuple[list[tuple[int, int, int]], bool] | None:
    """Pixels of a stream drawn from its head down to a mouth or a confluence.

    Returns the pixels (head first) and whether the stream reached water; ``None`` if
    it can reach neither.
    """
    out: list[tuple[int, int, int]] = []
    mine: dict[tuple[int, int], int] = {}
    for index, (r, c, value) in enumerate(line):
        if out and (r, c) == (out[-1][0], out[-1][1]):
            continue
        if not out:
            if _clear(canvas, r, c, mine, -1):
                out.append((r, c, value))
                mine[(r, c)] = 0
            continue
        if canvas.inside(r, c) and not canvas.land[r, c] and canvas.empty(r, c):
            return _mouth(canvas, out, mine, line[index:]), True
        if (r, c) in mine:
            for pr, pc, _ in out[mine[(r, c)] + 1 :]:
                del mine[(pr, pc)]
            out = out[: mine[(r, c)] + 1]
            continue
        own = [mine[q] for q in ((r + dr, c + dc) for dr, dc in NEIGHBOURS4) if q in mine]
        loop = min(own) if own else len(out) - 1
        if loop < len(out) - 1:
            for pr, pc, _ in out[loop + 1 :]:
                del mine[(pr, pc)]
            out = out[: loop + 1]
        if _clear(canvas, r, c, mine, len(out) - 1):
            mine[(r, c)] = len(out)
            out.append((r, c, value))
            continue
        bridge = _reach_river(canvas, out, mine)
        return None if bridge is None else (out + bridge, False)
    return None


def _mouth(
    canvas: _Canvas,
    out: list[tuple[int, int, int]],
    mine: dict[tuple[int, int], int],
    rest: list[tuple[int, int, int]],
) -> list[tuple[int, int, int]]:
    """Extend a line that reached water by up to MOUTH_PX free water pixels."""
    added = 0
    for r, c, value in rest:
        if added >= MOUTH_PX or not canvas.inside(r, c) or canvas.land[r, c]:
            break
        if (r, c) == (out[-1][0], out[-1][1]):
            continue
        if not canvas.empty(r, c) or canvas.rivers_near(r, c, NEIGHBOURS4 + CORNERS):
            break
        if any(mine.get((r + dr, c + dc), len(out) - 1) != len(out) - 1 for dr, dc in NEIGHBOURS4):
            break
        mine[(r, c)] = len(out)
        out.append((r, c, value))
        added += 1
    return out


def mix_key(key: int, value: int) -> int:
    """A per-stream noise key."""
    return derive_seed(key, f"stream_{value}")


def _downstream(tree: Drainage, start: int, limit: int) -> list[int]:
    """Cells below ``start`` along the drainage tree, ending with the water cell."""
    out: list[int] = []
    cell = start
    while len(out) < limit:
        down = int(tree.parent[cell])
        if down < 0:
            break
        out.append(down)
        cell = down
        if tree.parent[cell] < 0:
            break
    return out


def draw_rivers(  # noqa: PLR0913 - explicit coarse grid and optional shared raster buffers.
    land: NDArray[np.bool_],
    tree: Drainage,
    found: list[Stream],
    *,
    columns: int,
    seed: int,
    output: Rivers | None = None,
) -> Rivers:
    """Draw streams at full resolution, largest catchment first, each from its head down.

    ``columns`` is the coarse grid width. A stream follows its centre line until it
    meets water (a mouth: its head becomes the SOURCE) or comes next to a river drawn
    before (a confluence: a JOIN pixel beside a river pixel, the head stays a free end).
    Streams that reach neither, or have fewer than MIN_STREAM_PX land pixels, are
    dropped. ``output`` supplies reusable role/flow views; both are initialized here.
    """
    role = np.empty(land.shape, dtype=np.int8) if output is None else output.role
    flow = np.empty(land.shape, dtype=np.int64) if output is None else output.flow
    if role.shape != land.shape or flow.shape != land.shape:
        message = "River output buffers must match the drawing domain"
        raise RiverGenerationError(message)
    role.fill(NONE)
    flow.fill(0)
    canvas = _Canvas(
        land=land,
        role=role,
        flow=flow,
        owner=np.full(land.shape, -1, dtype=np.int32),
    )
    stats = {"streams": len(found), "mouths": 0, "joins": 0, "dropped": 0}
    key = derive_seed(seed, "river_lines")
    whole = 1 << 30
    for number, stream in enumerate(found):
        checkpoint()
        below = _downstream(tree, stream.cells[0], whole)
        cells = [*reversed(below), *stream.cells]
        flows = [int(tree.flow[cell]) for cell in cells]
        points, flows = _smooth(_centres(cells, columns, key), flows, 2)
        line = _pixels(_meander(points, mix_key(key, stream.cells[0])), flows)
        line.reverse()
        drawn = _descend(canvas, line)
        if drawn is None:
            stats["dropped"] += 1
            continue
        pixels, mouth = drawn
        if sum(1 for r, c, _ in pixels if land[r, c]) < MIN_STREAM_PX:
            stats["dropped"] += 1
            continue
        for r, c, value in pixels:
            canvas.owner[r, c] = number
            canvas.role[r, c] = BODY
            canvas.flow[r, c] = value
        if mouth:
            canvas.role[pixels[0][0], pixels[0][1]] = SOURCE
            stats["mouths"] += 1
        else:
            canvas.role[pixels[-1][0], pixels[-1][1]] = JOIN
            stats["joins"] += 1
    stats["pixels"] = int(np.count_nonzero(canvas.role != NONE))
    return Rivers(role=canvas.role, flow=canvas.flow, stats=stats)


def _coarse_land_and_height(
    land: NDArray[np.bool_], height: NDArray[np.int32] | NDArray[np.int64], strip: int
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Land share (permille) and mean land height of every STEP x STEP block.

    Computed in strips of ``strip`` rows (a multiple of ``STEP``), so no whole-raster
    eight-byte copy is made; the blocks, and with them the result, are the same.
    """
    rows, columns = (int(size) for size in land.shape)
    shape = (-(-rows // STEP), -(-columns // STEP))
    share = np.empty(shape, dtype=np.int64)
    weight = np.empty(shape, dtype=np.int64)
    for first in range(0, rows, strip):
        window = slice(first, min(rows, first + strip))
        block = slice(first // STEP, -(-window.stop // STEP))
        on_land = land[window]
        share[block] = block_mean(on_land.astype(np.int64) * PERMILLE, STEP)
        weight[block] = block_mean(np.where(on_land, height[window], 0).astype(np.int64), STEP)
    return share, weight


def generate_rivers(
    land: NDArray[np.bool_],
    height: NDArray[np.int32] | NDArray[np.int64],
    rain: NDArray[np.int64],
    *,
    seed: int,
    output: Rivers | None = None,
) -> Rivers:
    """Rivers for a raster: ``land`` and ``height`` at full resolution, ``rain`` coarse.

    ``rain`` has one value per STEP x STEP block (blocks may be partial at the edges).
    """
    shape = (-(-land.shape[0] // STEP), -(-land.shape[1] // STEP))
    count, weight = _coarse_land_and_height(land, height, STRIP_ROWS)
    coarse_land = count >= PERMILLE // 2
    if np.all(coarse_land):
        message = "River domain has no water outlet; its closed boundary is not a mouth"
        raise RiverGenerationError(message)
    coarse_height = weight * PERMILLE // np.maximum(1, count)
    valleys = warped_noise(
        derive_seed(seed, "river_valleys"),
        shape,
        step=2,
        period=VALLEY_PERIOD,
        octaves=4,
        warp_px=VALLEY_PERIOD // 3,
    )
    routing = coarse_height + valleys * VALLEY_HEIGHT // NOISE_SCALE
    wet = np.maximum(np.where(coarse_land, rain, 0), 0) * RAIN_UNIT
    weight = np.floor(np.sqrt(wet.astype(np.float64))).astype(np.int64)
    tree = drainage(coarse_land, routing, weight, derive_seed(seed, "drainage"))
    threshold = river_threshold(tree, int(np.count_nonzero(land)))
    found = streams(tree, threshold, MIN_STREAM_CELLS)
    rivers = draw_rivers(land, tree, found, columns=shape[1], seed=seed, output=output)
    rivers.stats["threshold"] = threshold
    return rivers


def flow_classes(rivers: Rivers, shares_permille: tuple[int, ...]) -> NDArray[np.int8]:
    """Size class per river pixel (-1 elsewhere): flow quantiles, smallest first.

    Class ``k`` takes the next ``shares_permille[k]`` of river pixels by flow, so a
    stream's class never falls downstream.
    """
    out = np.full(rivers.role.shape, -1, dtype=np.int8)
    river = rivers.role != NONE
    flows = np.sort(rivers.flow[river])
    if flows.size == 0:
        return out
    bounds: list[int] = []
    total = 0
    for share in shares_permille[:-1]:
        total += share
        bounds.append(int(flows[min(flows.size - 1, flows.size * total // PERMILLE)]))
    out[river] = np.searchsorted(np.array(bounds, dtype=np.int64), rivers.flow[river], side="right")
    return out


def carve_valleys(
    relief: NDArray[np.int32] | NDArray[np.int64],
    classes: NDArray[np.int8],
    *,
    depths: tuple[int, ...],
    radius_px: int,
    floor: int,
) -> NDArray[np.int32]:
    """Lower ``relief`` around river pixels: ``depths[class]`` at the river, easing to
    nothing at ``radius_px``; land never drops below ``floor``. Water (0) is kept.

    Rows are carved in strips, each in a window that reaches ``radius_px + 1`` rows past it
    (the reach of the distance and of the nearest river class), so the result does not
    depend on the strip height.
    """
    rows = int(relief.shape[0])
    out = np.empty(relief.shape, dtype=np.int32)
    table = np.array(depths, dtype=np.int64)
    for first in range(0, rows, STRIP_ROWS):
        checkpoint()
        last = min(rows, first + STRIP_ROWS)
        start, stop = max(0, first - radius_px - 1), min(rows, last + radius_px + 1)
        window_classes = classes[start:stop]
        river = window_classes >= 0
        core = slice(first - start, last - start)
        values = relief[first:last].astype(np.int64)
        if not np.any(river):
            out[first:last] = values
            continue
        distance = euclidean_distance(river, radius_px)[core]
        nearest = nearest_label(window_classes.astype(np.int32), river, radius_px + 1)[core]
        depth = table[np.maximum(nearest, 0)]
        ease = PERMILLE - smoothstep(distance, 0, radius_px * 8)
        carve = np.where(nearest >= 0, depth * ease // PERMILLE, 0)
        out[first:last] = np.where(
            values > 0, np.maximum(values - carve, np.minimum(values, floor)), values
        )
    return out


def network_problems(role: NDArray[np.int8], water: NDArray[np.bool_]) -> dict[str, int]:
    """Violations of the river raster rules (all zero for a valid network).

    Sources have one river neighbour, joins two, other pixels two (or one at a free
    end, or three beside exactly one join); no 2x2 blocks; each connected network has
    exactly one source and at least one end at or in water.
    """
    river = role != NONE
    padded = np.pad(river, 1)
    degree = (
        padded[:-2, 1:-1].astype(np.uint8) + padded[2:, 1:-1] + padded[1:-1, :-2] + padded[1:-1, 2:]
    )
    join = np.pad(role == JOIN, 1)
    joins = join[:-2, 1:-1].astype(np.uint8) + join[2:, 1:-1] + join[1:-1, :-2] + join[1:-1, 2:]
    wet = np.pad(water, 1)
    near_water = wet[:-2, 1:-1] | wet[2:, 1:-1] | wet[1:-1, :-2] | wet[1:-1, 2:] | water
    body = role == BODY
    ends = body & (degree == 1)
    components = label_components(np.where(river, 1, 0).astype(np.int32))
    size = int(components.max()) + 1
    networks = np.unique(components[river])
    sources = np.bincount(components[role == SOURCE], minlength=size)[networks]
    mouths = np.bincount(components[ends & near_water], minlength=size)[networks]
    return {
        "bad_sources": int(np.count_nonzero((role == SOURCE) & (degree != 1))),
        "bad_joins": int(np.count_nonzero((role == JOIN) & (degree != 2))),  # noqa: PLR2004
        "bad_body": int(np.count_nonzero(body & ((degree == 0) | (degree > 3)))),  # noqa: PLR2004
        "bad_confluences": int(np.count_nonzero(body & (degree == 3) & (joins != 1))),  # noqa: PLR2004
        "blocks": int(
            np.count_nonzero(river[:-1, :-1] & river[1:, :-1] & river[:-1, 1:] & river[1:, 1:])
        ),
        "networks_without_one_source": int(np.count_nonzero(sources != 1)),
        "networks_without_mouth": int(np.count_nonzero(mouths == 0)),
    }


def _main_outlet(role: NDArray[np.int8], start: tuple[int, int]) -> tuple[int, int] | None:
    """Follow the main line downstream; JOIN neighbours enter from upstream."""
    pixel, parent = start, start
    visited: set[tuple[int, int]] = set()
    rows, columns = role.shape
    while pixel not in visited:
        visited.add(pixel)
        r, c = pixel
        following = [
            (r + dr, c + dc)
            for dr, dc in NEIGHBOURS4
            if 0 <= r + dr < rows
            and 0 <= c + dc < columns
            and (r + dr, c + dc) != parent
            and role[r + dr, c + dc] not in (NONE, JOIN)
        ]
        if not following:
            return pixel
        if len(following) != 1:
            return None
        parent, pixel = pixel, following[0]
    return None


def outlet_problems(role: NDArray[np.int8], water: NDArray[np.bool_]) -> dict[str, int]:
    """Each main line must end in or beside actual water within its own domain.

    A wet tributary elsewhere in the component cannot excuse a dry main-line end.
    Raster borders are closed boundaries, never implicit water. Scan starts in strips
    and visit only main-line pixels; no whole-map component or neighbour arrays.
    """
    problems = {"ambiguous_outlets": 0, "inland_mouths": 0}
    rows, columns = role.shape
    for first in range(0, rows, STRIP_ROWS):
        checkpoint()
        rr, cc = np.where(role[first : first + STRIP_ROWS] == SOURCE)
        for row, column in zip(rr.tolist(), cc.tolist(), strict=True):
            end = _main_outlet(role, (row + first, column))
            if end is None:
                problems["ambiguous_outlets"] += 1
                continue
            r, c = end
            wet = any(
                water[r + dr, c + dc]
                for dr, dc in ((0, 0), *NEIGHBOURS4)
                if 0 <= r + dr < rows and 0 <= c + dc < columns
            )
            if role[end] != BODY or not wet:
                problems["inland_mouths"] += 1
    return problems
