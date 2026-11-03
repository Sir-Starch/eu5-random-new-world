"""Bounded physical routes from the generated cell graph, without sea-zone labels.

This H4 adapter deliberately takes no resources, donor identities or game scripts.
Only actual SEA cells provide maritime contact; lakes cannot bridge ocean coasts.
"""

# NumPy scalar conversion is typed as Any in its stubs.
# pyright: reportAny=false

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import numpy as np

from rnw.history_checks import require, unique
from rnw.history_model import PERMILLE, Route
from rnw.model import CellClass

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from rnw.societies import LandGraph


def _checkpoint() -> None:
    """Optional generator cancellation callback."""


@dataclass(frozen=True, slots=True)
class PhysicalMap:
    """Land names/costs in graph order; cells/edges in the generated world's order."""

    keys: tuple[str, ...]
    cells: tuple[int, ...]
    costs: tuple[int, ...]
    classes: Sequence[CellClass]
    edges: Sequence[tuple[int, int]]


def physical_routes(
    physical: PhysicalMap,
    *,
    max_sea_steps: int = 4,
    checkpoint: Callable[[], None] = _checkpoint,
) -> tuple[Route, ...]:
    """Land contacts and shortest coast-to-coast paths through at most N wet cells.

    A single wet cell is one sea step, even if it belongs to a huge named sea zone.
    Reversing edges or cell traversal cannot change a route or its cost. Land costs
    are the mean of the two terrain costs; a sea passage adds 1000 per wet cell and
    2000 for departure/arrival. All routes are undirected, as in the history core.
    """
    unique(physical.keys, "physical land key")
    require(
        len(physical.keys) == len(physical.cells) == len(physical.costs)
        and len(set(physical.cells)) == len(physical.cells)
        and max_sea_steps >= 0,
        "Invalid physical map dimensions",
    )
    require(
        all(
            0 <= cell < len(physical.classes) and physical.classes[cell] is CellClass.LAND
            for cell in physical.cells
        )
        and all(cost > 0 for cost in physical.costs),
        "Invalid physical land cell/cost",
    )
    land = dict(zip(physical.cells, physical.keys, strict=True))
    require(
        set(land) == {i for i, kind in enumerate(physical.classes) if kind is CellClass.LAND},
        "Physical map omits a land cell",
    )
    costs = dict(zip(physical.keys, physical.costs, strict=True))
    shores: dict[int, set[str]] = defaultdict(set)
    water: dict[int, set[int]] = defaultdict(set)
    found: dict[tuple[str, str], Route] = {}
    for number, (first, second) in enumerate(physical.edges):
        if number % 128 == 0:
            checkpoint()
        require(
            0 <= first < len(physical.classes)
            and 0 <= second < len(physical.classes)
            and first != second,
            "Invalid physical cell edge",
        )
        if first in land and second in land:
            a, b = sorted((land[first], land[second]))
            found[a, b] = Route(a, b, (costs[a] + costs[b]) // 2)
        for wet, dry in ((first, second), (second, first)):
            if physical.classes[wet] is CellClass.SEA:
                if dry in land:
                    shores[wet].add(land[dry])
                elif physical.classes[dry] is CellClass.SEA:
                    water[wet].add(dry)
    if max_sea_steps:
        _sea_routes(found, shores, water, costs, limit=max_sea_steps, checkpoint=checkpoint)
    return tuple(found[pair] for pair in sorted(found))


def _sea_routes(  # noqa: PLR0913 - physical shores, passages and costs with a bounded traversal.
    found: dict[tuple[str, str], Route],
    shores: dict[int, set[str]],
    water: dict[int, set[int]],
    costs: dict[str, int],
    *,
    limit: int,
    checkpoint: Callable[[], None],
) -> None:
    for start in sorted(shores):
        checkpoint()
        pending = deque([(start, 1)])
        seen = {start}
        while pending:
            wet, steps = pending.popleft()
            for first in sorted(shores[start]):
                for second in sorted(shores.get(wet, ())):
                    if first == second:
                        continue
                    a, b = sorted((first, second))
                    prior = found.get((a, b))
                    if prior is None or (prior.sea_steps and steps < prior.sea_steps):
                        found[a, b] = Route(
                            a,
                            b,
                            (costs[a] + costs[b]) // 2 + (steps + 2) * PERMILLE,
                            sea_steps=steps,
                        )
            if steps < limit:
                for other in sorted(water.get(wet, ())):
                    if other not in seen:
                        seen.add(other)
                        pending.append((other, steps + 1))


def routed_graph(graph: LandGraph, keys: Sequence[str], routes: Sequence[Route]) -> LandGraph:
    """Use these physical contacts for the ordinary society bootstrap too.

    Existing shared-water links are replaced before construction, never after a
    country has formed. Society travel uses its existing conservative link cost;
    history itself uses each passage's measured length and cost.
    """
    unique(keys, "routed graph key")
    require(len(keys) == len(graph.capacity), "Routed graph dimensions differ")
    index = {key: number for number, key in enumerate(keys)}
    require(
        all(route.first in index and route.second in index for route in routes),
        "Physical route names an unknown land key",
    )
    land = sorted(
        (min(index[r.first], index[r.second]), max(index[r.first], index[r.second]))
        for r in routes
        if not r.sea_steps
    )
    require(
        set(land) == {tuple(sorted((int(a), int(b)))) for a, b in graph.edges},
        "Physical land routes differ from the society graph",
    )
    links = sorted(
        (min(index[r.first], index[r.second]), max(index[r.first], index[r.second]))
        for r in routes
        if r.sea_steps
    )
    coastal = {key for route in routes if route.sea_steps for key in (route.first, route.second)}
    require(
        not coastal
        or (graph.coastal is not None and all(bool(graph.coastal[index[key]]) for key in coastal)),
        "Physical passage does not end on society coasts",
    )
    return replace(graph, links=np.array(links, dtype=np.int64).reshape(-1, 2))
