"""Omerika: land that keeps the Americas' general shape and nothing else of them.

The generator's land is the top share of a density field (``rnw.newworld``). Omerika adds one
more term to that field, a *template* drawn from the installed game's own map: where the
vanilla Americas lie. The template is a low-frequency one. Its signed distance from the vanilla
coast (land inside, sea outside) is cut off a few hundred pixels away and made flat near the
coast, so it carries the continents' layout and the long tails of Alaska and Chile, but none of
the coast's detail. The template is bent by a smooth, seed-drawn displacement before it is used,
so no two seeds put the coast in the same place; the fractal noise the other presets use then
draws the bays, capes, straits and seas on it. Mountains, climate, rivers, resources and peoples
are made afterwards from the land, as for every world type.

A neck of land is far narrower than the continents it joins, and a low-pass field loses it. The
two great landmasses of the template are therefore joined by a *corridor*: the route between their
cores that keeps deepest in the template's land, raised above any noise. The Americas stay one
connected landmass by construction, and ``check_joined`` says so explicitly once the land is made
(no repair follows).

The vanilla Americas are read from the installed game when the canvas is selected
(``rnw.eu5_canvas.select_canvas``) and are never shipped; this module reads no game file.
Everything is integer arithmetic on named SplitMix64 streams, in row strips or on grids ``STEP``
and ``ROUTE_STEP`` pixels wide, so equal inputs give equal land everywhere.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.fields import SUBPIXEL, box_blur, fractal_at, upsample
from rnw.noise import NOISE_SCALE
from rnw.progress import checkpoint
from rnw.rng import derive_seed
from rnw.topology import euclidean_distance, label_components

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.settings import NewWorldSettings

PERMILLE: Final[int] = 1000
# The template is worked on a grid this many pixels wide, and read back by bilinear
# interpolation: it is low-frequency by design.
STEP: Final[int] = 4
STRIP_ROWS: Final[int] = 1024
# A grid cell is land when at least this share of its pixels is (a quarter keeps a narrow neck).
COVERAGE_PERMILLE: Final[int] = 250
# The signed distance is cut off here: farther from the vanilla coast than this the template says
# only "land" or "sea". This is what makes the template low-frequency: a bay or a cape smaller
# than a fraction of it hardly shows in the field.
REACH_PX: Final[int] = 600
# The template's profile from the vanilla coast out to REACH_PX: the share of the way to the
# cut-off, raised to this power. Flat near the coast and steep far from it, so the fractal noise
# draws the coast and the template decides only a good way from the vanilla shore.
PROFILE_POWER: Final[int] = 2
# A loose likeness leaves the coast to the noise; a close one holds it. The weight of a short,
# steep profile (the signed distance cut off at SHARP_REACH_PX, so that even a narrow neck or cape
# stands out of the noise) is the likeness squared: none at a loose echo, all at the closest.
SHARP_REACH_PX: Final[int] = 140
# How far the seed bends the template. The displacement is smooth noise with this period; the
# amplitude falls from WARP_MAX_PX at the weakest likeness to WARP_MIN_PX at the strongest.
WARP_PERIOD_PX: Final[int] = 1500
WARP_MAX_PX: Final[int] = 300
WARP_MIN_PX: Final[int] = 80
# The template's weight, in elevation units, at full likeness (permille 1000): twice the noise's
# own range, so that deep inside or far out at sea the template alone decides.
GAIN: Final[int] = 3 * NOISE_SCALE
BLUR_CELLS: Final[int] = 2
# The route between the two cores is found on a coarser grid, ROUTE_STEP pixels wide (a multiple
# of STEP). A route cell is land when ROUTE_COVERAGE_PERMILLE of its pixels are, and the route
# prefers depth: its cost per cell is 1 plus (ROUTE_SCALE_PX / depth) squared, in permille.
ROUTE_STEP: Final[int] = 16
ROUTE_COVERAGE_PERMILLE: Final[int] = 120
ROUTE_SCALE_PX: Final[int] = 120
# The corridor is the route, ROUTE_STEP pixels wide, widened by CORRIDOR_CELLS grid cells of STEP
# pixels each side, and raised by CORRIDOR_LIFT elevation units: enough to hold against any noise.
CORRIDOR_CELLS: Final[int] = 3
CORRIDOR_LIFT: Final[int] = 4 * NOISE_SCALE
# Below this likeness (permille) the template is a loose echo and the land keeps no promise to join
# the great landmasses: a corridor between two places that the land no longer puts there would be a
# ribbon over the sea.
JOIN_MIN_PERMILLE: Final[int] = 300
# Thin parts of the template, where no land within THIN_PX of the sea lies near (a neck, a
# peninsula, a long cape, a chain of small islands), would be lost to the noise at a depth of a few
# dozen pixels. Their centre line, the cells at least RIDGE_MIN_PX from the sea where the depth is a
# ridge, is raised by SKELETON_LIFT elevation units, widened by SKELETON_CELLS cells each side, in
# proportion to a likeness that rises from SKELETON_FROM to SKELETON_TO (permille).
THIN_PX: Final[int] = 110
THIN_WINDOW_CELLS: Final[int] = 36
RIDGE_MIN_PX: Final[int] = 16
MIN_SKELETON_CELLS: Final[int] = 10
SKELETON_CELLS: Final[int] = 3
SKELETON_LIFT: Final[int] = 3 * NOISE_SCALE
SKELETON_FROM: Final[int] = 250
SKELETON_TO: Final[int] = 650
# A core of a landmass is land at least CORE_PX from the sea, of at least MIN_CORE_CELLS route
# cells; the GREAT_CORES greatest by area are the ones the land must keep joined.
CORE_PX: Final[int] = 300
MIN_CORE_CELLS: Final[int] = 60
GREAT_CORES: Final[int] = 2
# The share of the corridor's places that must be land, in permille.
CORRIDOR_LAND_PERMILLE: Final[int] = 900
STEPS_8: Final[tuple[tuple[int, int], ...]] = (
    (-1, 0),
    (1, 0),
    (0, -1),
    (0, 1),
    (-1, -1),
    (-1, 1),
    (1, -1),
    (1, 1),
)


class OmerikaError(ValueError):
    """The template cannot be joined, or the land lost the join the template guarantees."""


@dataclass(frozen=True, slots=True, eq=False)
class Template:
    """The template as the generator uses it: its field and the cores that must stay joined.

    ``field`` is on the grid of ``STEP`` pixels, with the cells that bilinear interpolation reads
    beyond the canvas. ``route`` is the route cells that join the two great cores, in order, as
    (row, column) of the route grid, and ``joint`` the pixels (rows, columns) at their centres:
    the places the generated land must keep joined (``check_joined``). Both are empty when the
    template has fewer than two great landmasses.
    """

    field: NDArray[np.int32]
    route: tuple[tuple[int, int], ...]
    joint: tuple[NDArray[np.int64], NDArray[np.int64]]
    shape: tuple[int, int]
    # Whether the likeness is close enough for the land to promise that the great landmasses join.
    promised: bool = True


def _cell_sums(
    values: NDArray[np.bool_] | NDArray[np.int32], step: int, size: tuple[int, int]
) -> NDArray[np.int32]:
    """The sums of ``step`` x ``step`` blocks of ``values``, padded with zeros to ``size`` cells."""
    height, width = (int(item) for item in values.shape)
    columns = size[1]
    out = np.zeros(size, dtype=np.int32)
    for first in range(0, height, STRIP_ROWS):
        checkpoint()
        strip = values[first : first + STRIP_ROWS]
        padded = np.pad(strip, ((0, -len(strip) % step), (0, columns * step - width)))
        blocks = np.asarray(padded, dtype=np.int32).reshape(
            len(padded) // step, step, columns, step
        )
        out[first // step : first // step + len(padded) // step] = blocks.sum(axis=(1, 3))
    return out


def _warp(cells: NDArray[np.int32], seed: int, settings: NewWorldSettings) -> NDArray[np.int32]:
    """The coverage read through a smooth displacement that the seed draws.

    A displacement whose slope stays well under one keeps the template's topology: two
    landmasses that touch still touch, and a neck keeps a neck's width within a third.
    """
    rows, columns = (int(size) for size in cells.shape)
    likeness = settings.template_permille
    amplitude = WARP_MAX_PX - (WARP_MAX_PX - WARP_MIN_PX) * likeness // PERMILLE
    ys = (np.arange(rows, dtype=np.int64) * STEP * SUBPIXEL)[:, np.newaxis]
    xs = (np.arange(columns, dtype=np.int64) * STEP * SUBPIXEL)[np.newaxis, :]
    ys, xs = np.broadcast_arrays(ys, xs)
    shifts: list[NDArray[np.int64]] = []
    for stream in ("omerika_warp_x", "omerika_warp_y"):
        noise = fractal_at(
            derive_seed(seed, stream),
            xs,
            ys,
            period=WARP_PERIOD_PX,
            octaves=2,
            persistence_permille=500,
        )
        shifts.append(noise * amplitude // (NOISE_SCALE * STEP))
    source_y = np.clip(np.arange(rows, dtype=np.int64)[:, np.newaxis] + shifts[1], 0, rows - 1)
    source_x = np.clip(
        np.arange(columns, dtype=np.int64)[np.newaxis, :] + shifts[0], 0, columns - 1
    )
    return cells[source_y, source_x]


def _cores(
    inside: NDArray[np.int64], core_px: int
) -> list[tuple[NDArray[np.int64], NDArray[np.int64]]]:
    """The cells (rows, columns) of the ``GREAT_CORES`` greatest cores, deepest first within a core.

    A core is land at least ``core_px`` from the sea (``inside`` is the depth in eighths of a
    cell); the neck that joins the landmasses is too thin to be a core.
    """
    core = inside >= core_px * 8 // ROUTE_STEP
    parts = label_components(core.astype(np.int32))
    sizes = np.bincount(parts.ravel())
    sizes[parts[~core]] = 0
    found: list[tuple[NDArray[np.int64], NDArray[np.int64]]] = []
    for part in np.argsort(-sizes, kind="stable").tolist()[:GREAT_CORES]:
        if sizes[part] < MIN_CORE_CELLS:
            break
        rows, columns = np.nonzero(parts == part)
        order = np.lexsort((columns, rows, -inside[rows, columns]))
        found.append((rows[order].astype(np.int64), columns[order].astype(np.int64)))
    return found


def _route(
    land: NDArray[np.bool_],
    inside: NDArray[np.int64],
    start: tuple[int, int],
    goal: tuple[int, int],
) -> list[tuple[int, int]]:
    """The cheapest route of land cells from ``start`` to ``goal``, 8-connected.

    A cell costs the more the nearer it lies to the sea, so the route follows the template's
    medial axis through a neck instead of cutting its corner. Ties break by position, so the
    route is the same everywhere.
    """
    rows, columns = land.shape
    scale = ROUTE_SCALE_PX * 8 // ROUTE_STEP
    depth = inside.tolist()
    usable = land.tolist()
    best: dict[tuple[int, int], int] = {start: 0}
    before: dict[tuple[int, int], tuple[int, int]] = {}
    queue: list[tuple[int, int, int]] = [(0, start[0], start[1])]
    while queue:
        cost, row, column = heapq.heappop(queue)
        if (row, column) == goal:
            break
        if cost > best[(row, column)]:
            continue
        for down, across in STEPS_8:
            near_row, near_column = row + down, column + across
            if not (0 <= near_row < rows and 0 <= near_column < columns):
                continue
            if not usable[near_row][near_column]:
                continue
            level = depth[near_row][near_column] + 4
            length = 1414 if down and across else 1000
            step = length + length * scale * scale // (level * level)
            total = cost + step
            if total < best.get((near_row, near_column), 1 << 62):
                best[(near_row, near_column)] = total
                before[(near_row, near_column)] = (row, column)
                heapq.heappush(queue, (total, near_row, near_column))
    if goal not in best:
        message = "The Americas' template has no route of land between its great landmasses"
        raise OmerikaError(message)
    route = [goal]
    while route[-1] != start:
        route.append(before[route[-1]])
    return route[::-1]


def _deepest_near(depth: NDArray[np.int64], radius: int) -> NDArray[np.int64]:
    """The greatest ``depth`` within ``radius`` cells (a square window), by doubling shifts."""
    result = depth
    for axis in (0, 1):
        pad = [(0, 0), (0, 0)]
        pad[axis] = (radius, radius)
        window = 2 * radius + 1
        current = np.pad(result, pad, mode="edge")
        span = 1
        while span < window:
            take = min(span, window - span)
            length = current.shape[axis]
            first = [slice(None), slice(None)]
            second = [slice(None), slice(None)]
            first[axis], second[axis] = slice(0, length - take), slice(take, length)
            current = np.maximum(current[tuple(first)], current[tuple(second)])
            span += take
        result = current
    return result


def _ridge(depth: NDArray[np.int64]) -> NDArray[np.bool_]:
    """The cells whose depth is no less than that of both neighbours along some axis: the centre
    line of the land, the medial axis, with the plateaus of a depth cut off included."""
    padded = np.pad(depth, 1, mode="edge")
    up, down = padded[:-2, 1:-1], padded[2:, 1:-1]
    left, right = padded[1:-1, :-2], padded[1:-1, 2:]
    return ((depth >= up) & (depth >= down)) | ((depth >= left) & (depth >= right))


def _skeleton(land: NDArray[np.bool_], inside: NDArray[np.int64]) -> NDArray[np.bool_]:
    """The centre line of the thin parts of ``land``: a neck, a cape, a chain of small islands.

    ``inside`` is the depth in eighths of a cell. A part is thin where no land within the window
    is deeper than ``THIN_PX``; the line is the ridge of the depth there, at least ``RIDGE_MIN_PX``
    from the sea, and a stray piece of it is left out.
    """
    thin = _deepest_near(inside, THIN_WINDOW_CELLS) * STEP < THIN_PX * 8
    ridge = land & thin & _ridge(inside) & (inside * STEP >= RIDGE_MIN_PX * 8)
    return _large_parts(ridge, MIN_SKELETON_CELLS)


def _large_parts(mask: NDArray[np.bool_], minimum: int) -> NDArray[np.bool_]:
    """The cells of ``mask`` in a connected part of at least ``minimum`` cells."""
    parts = label_components(mask.astype(np.int32))
    sizes = np.bincount(parts.ravel())
    return mask & (sizes >= minimum)[parts]


def prepare(template: NDArray[np.bool_], seed: int, settings: NewWorldSettings) -> Template:
    """The field and the cores of ``template`` (the vanilla Americas on the canvas) for a seed."""
    height, width = (int(size) for size in template.shape)
    rows, columns = -(-height // STEP), -(-width // STEP)
    likeness = settings.template_permille
    cells = _warp(_cell_sums(template, STEP, (rows, columns)), seed, settings)
    land = cells.astype(np.int64) * PERMILLE >= COVERAGE_PERMILLE * STEP * STEP
    limit = REACH_PX // STEP + 1
    inside = euclidean_distance(~land, limit).astype(np.int64)
    outside = euclidean_distance(land, limit).astype(np.int64)
    # Eighths of a cell; the signed distance in pixels is (inside - outside) * STEP / 8.
    signed = (inside - outside) * STEP // 8
    del outside
    unit = np.clip(signed, -REACH_PX, REACH_PX) * PERMILLE // REACH_PX
    soft = np.sign(unit) * (np.abs(unit) ** PROFILE_POWER // PERMILLE ** (PROFILE_POWER - 1))
    sharp = np.clip(signed, -SHARP_REACH_PX, SHARP_REACH_PX) * PERMILLE // SHARP_REACH_PX
    weight = likeness * likeness // PERMILLE
    body = ((PERMILLE - weight) * soft + weight * sharp) // PERMILLE
    del unit, soft, sharp, signed
    for _ in range(2):
        body = box_blur(body, BLUR_CELLS)
    composite = body * (GAIN * likeness // PERMILLE) // PERMILLE
    del body
    ramp = int(
        np.clip((likeness - SKELETON_FROM) * PERMILLE // (SKELETON_TO - SKELETON_FROM), 0, PERMILLE)
    )
    if ramp:
        skeleton = _skeleton(land, inside)
        lift = skeleton.astype(np.int64) * PERMILLE
        for _ in range(2):
            lift = box_blur(lift, SKELETON_CELLS)
        composite += lift * (SKELETON_LIFT * ramp // PERMILLE) // PERMILLE
        del skeleton, lift
    del inside
    # The route grid: coarser cells of the same warped template.
    ratio = ROUTE_STEP // STEP
    route_rows, route_columns = -(-rows // ratio), -(-columns // ratio)
    coarse = _cell_sums(cells, ratio, (route_rows, route_columns))
    route_land = coarse.astype(np.int64) * PERMILLE >= ROUTE_COVERAGE_PERMILLE * ratio**2 * STEP**2
    route_inside = euclidean_distance(~route_land, REACH_PX // ROUTE_STEP + 1).astype(np.int64)
    cores = _cores(route_inside, CORE_PX)
    route: list[tuple[int, int]] = []
    promised = likeness >= JOIN_MIN_PERMILLE
    if promised and len(cores) >= GREAT_CORES:
        first, second = cores[0], cores[1]
        route = _route(
            route_land,
            route_inside,
            (int(first[0][0]), int(first[1][0])),
            (int(second[0][0]), int(second[1][0])),
        )
        lift = np.zeros((route_rows, route_columns), dtype=np.int64)
        for row, column in route:
            lift[row, column] = PERMILLE
        wide = np.repeat(np.repeat(lift, ratio, axis=0), ratio, axis=1)[:rows, :columns]
        for _ in range(2):
            wide = box_blur(wide, CORRIDOR_CELLS)
        composite += wide * CORRIDOR_LIFT // PERMILLE
    padded = np.pad(
        composite,
        ((0, rows + 2 - composite.shape[0]), (0, columns + 2 - composite.shape[1])),
        mode="edge",
    )
    # The land must keep the neck joined, not the heart of each continent: the stretch of the route
    # inside a core is deep land, where an inland sea or a lake may lie.
    cells_of_route = np.array(route, dtype=np.int64).reshape(-1, 2)
    if len(cells_of_route):
        shallow = (
            route_inside[cells_of_route[:, 0], cells_of_route[:, 1]] * ROUTE_STEP < CORE_PX * 8
        )
        cells_of_route = cells_of_route[shallow]
    joint = (
        np.minimum(cells_of_route[:, 0] * ROUTE_STEP + ROUTE_STEP // 2, height - 1),
        np.minimum(cells_of_route[:, 1] * ROUTE_STEP + ROUTE_STEP // 2, width - 1),
    )
    return Template(padded.astype(np.int32), tuple(route), joint, (height, width), promised)


def add_to(relief: NDArray[np.int32], template: Template) -> None:
    """Add the template's field to ``relief`` in place, in row strips."""
    height, width = relief.shape
    if (int(height), int(width)) != template.shape:
        message = "The Americas' template does not fit the canvas"
        raise ValueError(message)
    for first in range(0, height, STRIP_ROWS):
        checkpoint()
        rows = min(STRIP_ROWS, height - first)
        coarse = template.field[first // STEP : (first + rows) // STEP + 2].astype(np.int64)
        relief[first : first + rows] += upsample(coarse, STEP, (rows, width)).astype(np.int32)


def check_joined(land: NDArray[np.bool_], template: Template) -> None:
    """Fail unless the corridor between the two great landmasses is one landmass of ``land``.

    This is the preset's promise: North and South America stay joined, as they are in the
    game. The corridor is raised above any noise, so it is land by construction; land that still
    falls apart (a gulf or a lake carved across the neck) is a defect of the construction, not a
    world to play, and no repair follows. A few of the corridor's places may lie in a lake.
    """
    if not template.promised:
        return
    rows, columns = template.joint
    if not len(rows):
        message = "The Americas' template has fewer than two great landmasses to join"
        raise OmerikaError(message)
    on_land = land[rows, columns]
    if int(on_land.sum()) * PERMILLE < CORRIDOR_LAND_PERMILLE * len(rows):
        message = (
            "The corridor between the Americas' great landmasses is sea in the generated world"
        )
        raise OmerikaError(message)
    labels = label_components(land.astype(np.int32))[rows, columns][on_land]
    if (labels != labels[0]).any():
        message = "The generated land does not join the great landmasses of the Americas' template"
        raise OmerikaError(message)
