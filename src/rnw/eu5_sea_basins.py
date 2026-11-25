"""Carry the installed Mediterranean into the water beside a generated Africa."""

# NumPy stubs type array indexing and tolist() as Any.
# pyright: reportAny=false
from __future__ import annotations

import heapq
from collections import Counter
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.hierarchy import pieces
from rnw.model import CellClass
from rnw.pdx import parse
from rnw.progress import checkpoint

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from pathlib import Path

    from numpy.typing import NDArray

    from rnw.eu5_canvas import Canvas
    from rnw.eu5_map import Eu5Map
    from rnw.hierarchy import ContactGraph
    from rnw.newworld import NewWorld

MEDITERRANEAN: Final[str] = "mediterranean_sea_geography"
GEOGRAPHY_FILE: Final[str] = "game/in_game/common/scripted_geography/01_europe.txt"
STRIP_ROWS: Final[int] = 256


def mediterranean_areas(game_dir: Path) -> frozenset[str]:
    """Read the areas that EU5 treats as part of the Mediterranean."""
    text = (game_dir / GEOGRAPHY_FILE).read_text(encoding="utf-8-sig")
    block = parse(text).block(MEDITERRANEAN, "area")
    areas: frozenset[str] = (
        frozenset(entry.value for entry in block.words() if isinstance(entry.value, str))
        if block is not None
        else frozenset()
    )
    if not areas:
        message = f"Missing Mediterranean sea areas in {GEOGRAPHY_FILE}"
        raise ValueError(message)
    return areas


def _marine_overlap(
    game_map: Eu5Map, canvas: Canvas, world: NewWorld, med: NDArray[np.bool_]
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Count original Mediterranean and other sea pixels under the finished sea cells."""
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes])
    generated = np.array([kind is CellClass.SEA for kind in world.classes] + [False])
    count = len(world.classes)
    inside = np.zeros(count, dtype=np.int64)
    outside = np.zeros(count, dtype=np.int64)
    for crop, original in canvas.spans():
        for top in range(0, world.labels.shape[0], STRIP_ROWS):
            checkpoint()
            rows = slice(top, top + STRIP_ROWS)
            new = world.labels[rows, crop]
            old = game_map.labels[rows, original]
            wet = generated[new]
            inside += np.bincount(new[wet & med[old]], minlength=count)
            outside += np.bincount(new[wet & sea[old] & ~med[old]], minlength=count)
    return inside, outside


def _join_basin_pockets(
    game_map: Eu5Map,
    world: NewWorld,
    graph: ContactGraph,
    contacts: Collection[tuple[int, int]],
    members: dict[int, str],
) -> None:
    """Give water supported only by the basin's new waters to their own areas."""
    if not members:
        return
    sea = CellClass.SEA
    shore = {cell for label, cell in contacts if game_map.classes[label] is sea}
    for left, right in world.edges:
        if (world.classes[left] is sea) != (world.classes[right] is sea):
            shore.add(left if world.classes[left] is sea else right)
    other = [cell for cell, kind in enumerate(world.classes) if kind is sea and cell not in members]
    for pocket in pieces(graph, other):
        if shore.intersection(pocket):
            continue
        banks = Counter(
            members[neighbor]
            for cell in pocket
            for neighbor, _ in graph.links[cell]
            if neighbor in members
        )
        if banks:
            area = min(banks, key=lambda name: (-banks[name], name))
            members.update(dict.fromkeys(pocket, area))


def mediterranean_cells(  # noqa: PLR0913 - the finished water and its retained geography.
    game_map: Eu5Map,
    canvas: Canvas,
    world: NewWorld,
    graph: ContactGraph,
    *,
    contacts: Collection[tuple[int, int]],
    original_areas: Sequence[str],
    basin_areas: Collection[str],
) -> dict[int, str]:
    """Extend retained Mediterranean areas into neighbouring generated water.

    Marine overlap separates the Mediterranean from the Atlantic and other seas at
    their mouths. Over drowned land, the nearest water source wins along the new
    sea graph. Every assigned area grows from a shared edge with its retained water.
    """
    if not basin_areas:
        return {}
    med = np.array(
        [
            kind is CellClass.SEA and area in basin_areas
            for kind, area in zip(game_map.classes, original_areas, strict=True)
        ]
    )
    shores: dict[int, Counter[str]] = {}
    foreign: set[int] = set()
    for label, cell in contacts:
        if world.classes[cell] is CellClass.SEA and game_map.classes[label] is CellClass.SEA:
            if med[label]:
                shores.setdefault(cell, Counter())[original_areas[label]] += 1
            else:
                foreign.add(cell)
    if not shores:
        return {}
    inside, outside = _marine_overlap(game_map, canvas, world, med)
    core = inside > outside
    other = (outside > 0) & ~core
    for cell in foreign:
        other[cell] |= not core[cell]
    frontier = [
        (0, min(votes, key=lambda name: (-votes[name], name)), cell)
        for cell, votes in shores.items()
        if not other[cell]
    ]
    if not frontier:
        return {}
    frontier.extend((0, "", cell) for cell in np.flatnonzero(other).tolist())
    heapq.heapify(frontier)
    assigned: dict[int, str] = {}
    while frontier:
        distance, area, cell = heapq.heappop(frontier)
        if cell in assigned:
            continue
        assigned[cell] = area
        for neighbour, length in graph.links[cell]:
            if neighbour not in assigned and (area or not core[neighbour]):
                heapq.heappush(frontier, (distance + length, area, neighbour))
    members = {cell: area for cell, area in assigned.items() if area}
    _join_basin_pockets(game_map, world, graph, contacts, members)
    return members
