"""Army crossings at useful shore gaps, with one perpendicular section per narrows.

Vanilla-width links between distinct landmasses remain eligible. Wider or same-landmass
links must cut a real water throat opening into substantial water on both sides. A short
walk around a coastal indentation is not a crossing. All geometry uses bounded windows.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import isqrt
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.model import CellClass
from rnw.progress import checkpoint
from rnw.straits import CROSSING_PX, Gap, narrow_gaps
from rnw.topology import euclidean_distance, label_components

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.newworld import NewWorld

VANILLA_PX: Final[int] = 9
# EU5's AI_CIRCULAR_STRAIT_DISTANCE_THRESHOLD is 8 locations. Do not create
# same-shore shortcuts that the game's own AI treats as an unimportant walk.
MIN_DETOUR: Final[int] = 8
MIN_BASIN_AREA: Final[int] = 128
MIN_BASIN_DEPTH: Final[int] = 4
TWO_WATERS: Final[int] = 2
NECK_RADIUS: Final[int] = 48
SEPARATION: Final[int] = 2 * CROSSING_PX
AXIS_REACH: Final[int] = isqrt(2 * (CROSSING_PX + 1) ** 2)


@dataclass(frozen=True, slots=True)
class Section:
    first: int
    second: int
    through: int
    start: tuple[int, int]
    stop: tuple[int, int]

    @property
    def squared(self) -> int:
        return sum((a - b) ** 2 for a, b in zip(self.start, self.stop, strict=True))


def pixels(start: tuple[int, int], stop: tuple[int, int]) -> tuple[tuple[int, int], ...]:
    """A supercover of the segment between pixel centres, including corner contacts."""
    row, col = start
    dr, dc = stop[0] - row, stop[1] - col
    nr, nc = abs(dr), abs(dc)
    sr, sc = (1 if dr > 0 else -1), (1 if dc > 0 else -1)
    ir = ic = 0
    found = [(row, col)]
    while ir < nr or ic < nc:
        decision = (1 + 2 * ic) * nr - (1 + 2 * ir) * nc
        if decision == 0:
            found.extend(((row + sr, col), (row, col + sc)))
            row, col, ir, ic = row + sr, col + sc, ir + 1, ic + 1
        elif decision < 0:
            col, ic = col + sc, ic + 1
        else:
            row, ir = row + sr, ir + 1
        found.append((row, col))
    return tuple(found)


def _links(world: NewWorld) -> list[set[int]]:
    links: list[set[int]] = [set() for _ in world.classes]
    for a, b in world.edges:
        links[a].add(b)
        links[b].add(a)
    return links


def _short_walk(first: int, second: int, land: NDArray[np.bool_], links: list[set[int]]) -> bool:
    seen = {first}
    queue = deque([(first, 0)])
    while queue:
        cell, distance = queue.popleft()
        if distance == MIN_DETOUR - 1:
            continue
        for other in sorted(links[cell]):
            if other == second:
                return True
            if land[other] and other not in seen:
                seen.add(other)
                queue.append((other, distance + 1))
    return False


def _landmasses(world: NewWorld, links: list[set[int]]) -> list[int]:
    dry = {CellClass.LAND, CellClass.WASTELAND, CellClass.LAKE}
    mass = [-1] * len(world.classes)
    number = 0
    for start, kind in enumerate(world.classes):
        if kind not in dry or mass[start] >= 0:
            continue
        queue = [start]
        mass[start] = number
        while queue:
            for other in sorted(links[queue.pop()]):
                if world.classes[other] in dry and mass[other] < 0:
                    mass[other] = number
                    queue.append(other)
        number += 1
    return mass


def _refine(world: NewWorld, water: NDArray[np.bool_], gap: Gap) -> Section | None:
    a, b = (
        ((gap.line, gap.start), (gap.line, gap.stop))
        if gap.axis == 0
        else ((gap.start, gap.line), (gap.stop, gap.line))
    )
    row, col = ((x + y) // 2 for x, y in zip(a, b, strict=True))
    reach = CROSSING_PX + 2
    r0, c0 = max(0, row - reach), max(0, col - reach)
    labels = world.labels[r0 : row + reach + 1, c0 : col + reach + 1]
    wet = water[r0 : row + reach + 1, c0 : col + reach + 1]
    shores = label_components((~wet).astype(np.int32))
    one, two = int(shores[a[0] - r0, a[1] - c0]), int(shores[b[0] - r0, b[1] - c0])
    if one == two:
        return None
    coast = np.zeros(wet.shape, dtype=bool)
    coast[1:] |= wet[:-1]
    coast[:-1] |= wet[1:]
    coast[:, 1:] |= wet[:, :-1]
    coast[:, :-1] |= wet[:, 1:]
    passable = np.array([kind is CellClass.LAND for kind in world.classes] + [False])[labels]
    first = np.argwhere(coast & passable & (shores == one))
    second = np.argwhere(coast & passable & (shores == two))
    if not len(first) or not len(second):
        return None
    delta = first[:, None, :] - second[None, :, :]
    distances = np.sum(delta * delta, axis=2)
    for flat in np.argsort(distances, axis=None, kind="stable").tolist():
        i, j = divmod(flat, len(second))
        if int(distances[i, j]) > (CROSSING_PX + 1) ** 2:
            break
        ar, ac = first[i].tolist()
        br, bc = second[j].tolist()
        start, stop = (int(ar), int(ac)), (int(br), int(bc))
        line = pixels(start, stop)
        # Shortest coastal points may graze a third shore or cross a sea-cell boundary.
        # Require one unambiguous water cell for the entire actual water section.
        at = [int(labels[p]) for p in line[1:-1]]
        if not at or any(not wet[p] for p in line[1:-1]) or len(set(at)) != 1:
            continue
        first_cell, second_cell = int(labels[start]), int(labels[stop])
        if first_cell == second_cell:
            continue
        item = Section(
            first_cell,
            second_cell,
            at[0],
            (start[0] + r0, start[1] + c0),
            (stop[0] + r0, stop[1] + c0),
        )
        return (
            item
            if first_cell < second_cell
            else Section(second_cell, first_cell, item.through, item.stop, item.start)
        )
    return None


def _throat(water: NDArray[np.bool_], section: Section) -> bool:
    width = max(1, isqrt(section.squared) - 1)
    reach = max(NECK_RADIUS, 4 * (width + 1))
    row, col = ((a + b) // 2 for a, b in zip(section.start, section.stop, strict=True))
    r0, c0 = max(0, row - reach), max(0, col - reach)
    wet = water[r0 : row + reach + 1, c0 : col + reach + 1].copy()
    line = [(r - r0, c - c0) for r, c in pixels(section.start, section.stop)[1:-1]]
    depth = euclidean_distance(~wet, 8 * (reach + 1))
    for point in line:
        wet[point] = False
    pieces = label_components(wet.astype(np.int32))
    adjacent = {
        int(pieces[r + dr, c + dc])
        for r, c in line
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
        if 0 <= r + dr < len(wet) and 0 <= c + dc < wet.shape[1] and wet[r + dr, c + dc]
    }
    wide = 0
    for piece in sorted(adjacent):
        mask = (pieces == piece) & wet
        if int(np.count_nonzero(mask)) >= max(MIN_BASIN_AREA, 2 * width * width) and int(
            depth[mask].max(initial=0)
        ) >= 8 * max(MIN_BASIN_DEPTH, width):
            wide += 1
    return wide == TWO_WATERS


def sections(world: NewWorld) -> list[Section]:
    """Useful crossings, shortest true water sections, and one section per nearby throat."""
    land = np.array([kind is CellClass.LAND for kind in world.classes], dtype=bool)
    sea = np.array([kind is CellClass.SEA for kind in world.classes] + [False], dtype=bool)
    water = sea[world.labels]
    links = _links(world)
    mass = _landmasses(world, links)
    candidates: list[Section] = []
    throats: dict[Section, bool] = {}
    seen: set[Section] = set()
    for gap in narrow_gaps(world.labels, water, land, AXIS_REACH).values():
        checkpoint()
        section = _refine(world, water, gap)
        if section is None or section in seen:
            continue
        seen.add(section)
        if _short_walk(section.first, section.second, land, links):
            continue
        different = mass[section.first] != mass[section.second]
        throat = _throat(water, section)
        if not throat and not (different and section.squared <= (VANILLA_PX + 1) ** 2):
            continue
        candidates.append(section)
        throats[section] = throat
    found: list[Section] = []
    for section in sorted(
        candidates, key=lambda s: (not throats[s], s.squared, s.first, s.second, s.start, s.stop)
    ):
        pair = sorted((mass[section.first], mass[section.second]))
        centre = tuple(a + b for a, b in zip(section.start, section.stop, strict=True))
        if any(
            sorted((mass[known.first], mass[known.second])) == pair
            and (
                not throats[section]
                or sum(
                    (x - a - b) ** 2
                    for x, a, b in zip(centre, known.start, known.stop, strict=True)
                )
                <= (2 * SEPARATION) ** 2
            )
            for known in found
        ):
            continue
        found.append(section)
    return sorted(found, key=lambda s: (s.first, s.second))
