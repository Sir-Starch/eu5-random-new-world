"""Native societies on synthetic land graphs."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace

import numpy as np

from rnw.settings import NATIVES
from rnw.societies import CITY, STATE, STEP_COST, TRIBE, LandGraph, Societies, generate_societies

ROWS, COLUMNS, ISLAND = 30, 40, 12
SETTINGS = replace(
    NATIVES,
    hearths_per_10k=20,
    hearth_reach_steps=10,
    culture_locations=10,
    religion_locations=150,
    tribe_locations=5,
    organized_permille=600,
)


def _grid() -> LandGraph:
    """A 30x40 grid, fertile in the north-west, plus a separate 12-location island."""
    count = ROWS * COLUMNS + ISLAND
    rows, columns = np.divmod(np.arange(ROWS * COLUMNS), COLUMNS)
    potential = np.concatenate(
        [np.clip(1000 - 25 * (rows + columns), 100, 1000), np.full(ISLAND, 500)]
    ).astype(np.int64)
    edges = [
        (r * COLUMNS + c, r * COLUMNS + c + 1) for r in range(ROWS) for c in range(COLUMNS - 1)
    ]
    edges += [
        (r * COLUMNS + c, (r + 1) * COLUMNS + c) for r in range(ROWS - 1) for c in range(COLUMNS)
    ]
    base = ROWS * COLUMNS
    edges += [(base + i, base + i + 1) for i in range(ISLAND - 1)]
    return LandGraph(
        capacity=np.full(count, 5000, dtype=np.int64),
        potential=potential,
        cost=np.full(count, STEP_COST, dtype=np.int64),
        edges=np.array(edges, dtype=np.int64),
        links=np.zeros((0, 2), dtype=np.int64),
    )


def _connected(nodes: set[int], edges: np.ndarray) -> bool:
    if not nodes:
        return True
    neighbours: dict[int, list[int]] = {node: [] for node in nodes}
    for first, second in edges.tolist():
        if first in nodes and second in nodes:
            neighbours[first].append(second)
            neighbours[second].append(first)
    start = next(iter(nodes))
    seen, stack = {start}, [start]
    while stack:
        for other in neighbours[stack.pop()]:
            if other not in seen:
                seen.add(other)
                stack.append(other)
    return seen == nodes


def _societies(seed: int = 3) -> tuple[LandGraph, Societies]:
    graph = _grid()
    return graph, generate_societies(graph, SETTINGS, seed=seed, target=4_000_000)


def test_societies_are_deterministic_and_follow_the_seed() -> None:
    """The same seed repeats exactly; another seed changes the zones."""
    _, first = _societies(3)
    _, again = _societies(3)
    _, other = _societies(4)
    for name in ("population", "peasants", "religion", "culture", "complexity"):
        assert np.array_equal(getattr(first, name), getattr(again, name))
    assert first.polities == again.polities
    assert not np.array_equal(first.culture, other.culture)


def test_population_and_states_follow_the_calibration() -> None:
    """Totals meet the target; states take the configured share around fertile hearths."""
    graph, societies = _societies()
    total = int(societies.population.sum())
    assert 4_000_000 - len(graph.capacity) <= total <= 4_000_000
    assert societies.hearths
    assert all(hearth < ROWS * COLUMNS for hearth in societies.hearths)
    hearth_rows = [hearth // COLUMNS + hearth % COLUMNS for hearth in societies.hearths]
    assert min(hearth_rows) < 15  # near the fertile corner (r + c ranges to 68)
    state_nodes = [node for p in societies.polities if p.kind == STATE for node in p.members]
    inhabited = int(np.count_nonzero(societies.population))
    assert len(state_nodes) == inhabited * SETTINGS.state_share_permille // 1000
    assert societies.peasants[state_nodes].sum() > 0
    assert np.all(societies.peasants <= societies.population)
    tribal = np.ones(len(graph.capacity), dtype=bool)
    tribal[state_nodes] = False
    density_states = societies.population[state_nodes].mean()
    assert density_states > 3 * societies.population[tribal].mean()


def test_zones_and_polities_are_connected_and_disjoint() -> None:
    """Zones nest and connect; polities hold disjoint connected land with their capital."""
    graph, societies = _societies()
    for zone in range(int(societies.religion.max()) + 1):
        members = set(np.flatnonzero(societies.religion == zone).tolist())
        assert _connected(members, graph.edges)
    island = set(range(ROWS * COLUMNS, ROWS * COLUMNS + ISLAND))
    assert {int(societies.religion[node]) for node in island}.isdisjoint(
        int(societies.religion[node]) for node in range(ROWS * COLUMNS)
    )
    for zone in range(int(societies.culture.max()) + 1):
        members = np.flatnonzero(societies.culture == zone)
        assert len({int(societies.religion[node]) for node in members}) == 1
        assert _connected(set(members.tolist()), graph.edges)
    held: set[int] = set()
    for polity in societies.polities:
        members = set(polity.members)
        assert polity.capital in members
        assert not members & held
        assert _connected(members, graph.edges)
        assert polity.kind in {STATE, TRIBE}
        if polity.kind == TRIBE:
            assert {int(societies.culture[node]) for node in members} == {polity.culture}
        held |= members
    capitals = {p.capital for p in societies.polities if p.kind == STATE}
    assert set(societies.ranks) <= capitals
    assert CITY in societies.ranks.values()
    assert set(societies.markets) <= capitals
