"""Native societies on synthetic land graphs."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import hashlib
from dataclasses import replace

import numpy as np
import pytest

from rnw.settings import NATIVES
from rnw.societies import (
    CITY,
    EMPIRE_FLOOR,
    STATE,
    STEP_COST,
    TRIBE,
    LandGraph,
    Societies,
    generate_societies,
    hearth_domains,
    land_routes,
    travel_from,
    trunk_roads,
)

ROWS, COLUMNS, ISLAND = 30, 40, 12
SETTINGS = replace(
    NATIVES,
    hearths_per_10k=20,
    hearth_reach_steps=10,
    culture_locations=10,
    religion_locations=150,
    tribe_locations=5,
    organized_permille=600,
    empire_permille=0,
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


def _state_groups(graph: LandGraph, societies: Societies) -> list[int]:
    """Locations of each group of touching state land, largest first."""
    land = {
        member for polity in societies.polities if polity.kind == STATE for member in polity.members
    }
    neighbours: dict[int, set[int]] = {node: set() for node in land}
    for first, second in graph.edges.tolist():
        if first in land and second in land:
            neighbours[first].add(second)
            neighbours[second].add(first)
    sizes: list[int] = []
    seen: set[int] = set()
    for start in land:
        if start in seen:
            continue
        group, stack = {start}, [start]
        while stack:
            for other in neighbours[stack.pop()] - group:
                group.add(other)
                stack.append(other)
        seen |= group
        sizes.append(len(group))
    return sorted(sizes, reverse=True)


def test_lone_states_spread_state_land_into_small_groups() -> None:
    """With a spread, part of the state land lies in small groups apart from the core.

    Without one the states form one block around the hearths, as before; the share of state
    land stays as set either way.
    """
    graph = _grid()
    clustered = generate_societies(
        graph, replace(SETTINGS, state_spread_permille=0), seed=3, target=4_000_000
    )
    spread = generate_societies(
        graph, replace(SETTINGS, state_spread_permille=400), seed=3, target=4_000_000
    )
    one, many = _state_groups(graph, clustered), _state_groups(graph, spread)
    assert len(many) > len(one)
    assert sum(many[1:]) > sum(one[1:])
    assert abs(sum(many) - sum(one)) <= max(2, sum(one) // 10)


def _digest(societies: Societies) -> str:
    """Everything a world is made of, as one hash."""
    digest = hashlib.sha256()
    for name in ("complexity", "population", "peasants", "religion", "culture"):
        digest.update(getattr(societies, name).tobytes())
    polities = [(p.kind, p.members, p.capital, p.culture) for p in societies.polities]
    digest.update(repr(polities).encode())
    digest.update(
        repr((societies.hearths, sorted(societies.ranks.items()), societies.markets)).encode()
    )
    return digest.hexdigest()


# Taken from 0.9.14, before great empires existed: with none, the societies are those bytes.
NO_EMPIRES: dict[int, str] = {
    3: "8918da688fcbf1b52ccd3ef3f7ada1b5732a338ec7cb35e7a73c4c1f5c6ebeeb",
    4: "b14448be80550c2c17aa917a3c9f4595ae05727bdecc1781e3ab255011609865",
    77: "6c86f55e823202a4eefc711ad66395101cd47c893c4cb19f818639deae0deb43",
}


def test_without_great_empires_the_societies_are_those_of_before() -> None:
    """A chance of 0 draws nothing from the world's own stream: the bytes do not move."""
    graph = _grid()
    for seed, digest in NO_EMPIRES.items():
        societies = generate_societies(graph, SETTINGS, seed=seed, target=4_000_000)
        assert _digest(societies) == digest
        assert not any(polity.great for polity in societies.polities)


def test_great_empires_are_large_connected_states_apart_from_the_rest() -> None:
    """Each hearth may raise a connected state of at least the floor, among disjoint polities."""
    graph = _grid()
    societies = generate_societies(
        graph, replace(SETTINGS, empire_permille=1000), seed=4, target=4_000_000
    )
    empires = [polity for polity in societies.polities if polity.great]
    assert empires
    ordinary = max(len(p.members) for p in societies.polities if p.kind == STATE and not p.great)
    held: set[int] = set()
    for polity in societies.polities:
        members = set(polity.members)
        assert not members & held
        assert _connected(members, graph.edges)
        assert polity.capital in members
        held |= members
    for empire in empires:
        assert empire.kind == STATE
        assert len(empire.members) >= EMPIRE_FLOOR
        assert len(empire.members) > ordinary
        assert all(societies.population[node] > 0 for node in empire.members)
    assert societies.ranks[empires[0].capital] == CITY


def test_a_higher_chance_raises_more_empires() -> None:
    """The draws do not depend on the chance, so the count only grows with it."""
    graph = _grid()
    counts: list[int] = []
    for chance in (0, 400, 700, 1000):
        societies = generate_societies(
            graph, replace(SETTINGS, empire_permille=chance), seed=4, target=4_000_000
        )
        counts.append(sum(1 for polity in societies.polities if polity.great))
    assert counts == sorted(counts)
    assert counts[0] == 0
    assert counts[-1] > counts[1] > 0


def _roads(
    count: int,
    edges: list[tuple[int, int]],
    costs: list[int] | None = None,
    links: list[tuple[int, int]] | None = None,
) -> LandGraph:
    zero = np.zeros(count, dtype=np.int64)
    return LandGraph(
        capacity=zero,
        potential=zero,
        cost=np.array(costs or [STEP_COST] * count, dtype=np.int64),
        edges=np.array(edges, dtype=np.int64).reshape(-1, 2),
        links=np.array(links or [], dtype=np.int64).reshape(-1, 2),
    )


def test_trunk_roads_follow_a_line_to_each_target() -> None:
    """A line graph gives the path to the farthest target and its prefix for a nearer one."""
    line = _roads(4, [(0, 1), (1, 2), (2, 3)])
    assert trunk_roads(line, {0, 1, 2, 3}, 0, [3]) == ((0, 1), (1, 2), (2, 3))
    assert trunk_roads(line, {0, 1, 2, 3}, 0, [2]) == ((0, 1), (1, 2))
    assert trunk_roads(line, {0, 1, 2, 3}, 3, [0]) == ((0, 1), (1, 2), (2, 3))
    assert trunk_roads(line, {0, 1, 2, 3}, 0, []) == ()


def test_trunk_roads_of_equal_cost_take_the_lower_indices() -> None:
    """Of two routes of equal cost the one through the lower index wins, whatever the edge order."""
    diamond = _roads(4, [(2, 3), (0, 2), (1, 3), (0, 1)])
    assert trunk_roads(diamond, {0, 1, 2, 3}, 0, [3]) == ((0, 1), (1, 3))
    assert land_routes(diamond, {0, 1, 2, 3}, 0)[1].tolist() == [-1, 0, 0, 1]


def test_trunk_roads_take_the_cheaper_route() -> None:
    """The cost of the location entered decides before the index does."""
    diamond = _roads(4, [(0, 1), (0, 2), (1, 3), (2, 3)], costs=[1000, 5000, 1000, 1000])
    assert trunk_roads(diamond, {0, 1, 2, 3}, 0, [3]) == ((0, 2), (2, 3))
    cost, _ = land_routes(diamond, {0, 1, 2, 3}, 0)
    assert cost.tolist() == [0, 5000, 1000, 2000]


def test_trunk_roads_stay_inside_the_allowed_land_and_off_the_sea() -> None:
    """An island, a location outside ``allowed`` and a sea link all leave a target unlinked."""
    graph = _roads(5, [(0, 1), (1, 2), (3, 4)], links=[(2, 3)])
    assert trunk_roads(graph, {0, 1, 2, 3, 4}, 0, [4, 3]) == ()
    assert trunk_roads(graph, {0, 1, 3}, 0, [2]) == ()
    assert trunk_roads(graph, {0, 1, 2}, 0, [2, 4]) == ((0, 1), (1, 2))
    cost, before = land_routes(graph, {0, 1, 2, 3, 4}, 0)
    assert cost.tolist() == [0, 1000, 2000, -1, -1]
    assert before.tolist() == [-1, 0, 1, -1, -1]


def test_trunk_roads_are_unique_sorted_pairs_with_the_lower_index_first() -> None:
    """Targets that share a prefix add its pairs once."""
    tree = _roads(6, [(5, 4), (4, 3), (3, 0), (4, 2), (2, 1)])
    pairs = trunk_roads(tree, {0, 1, 2, 3, 4, 5}, 5, [0, 1, 2])
    assert pairs == tuple(sorted(set(pairs)))
    assert all(a < b for a, b in pairs)
    assert pairs == ((0, 3), (1, 2), (2, 4), (3, 4), (4, 5))


def test_a_route_needs_an_allowed_source() -> None:
    """The capital must be inside the allowed land."""
    with pytest.raises(ValueError, match="allowed"):
        _ = trunk_roads(_roads(2, [(0, 1)]), {1}, 0, [1])


def test_a_location_belongs_to_the_nearest_hearth_and_an_unreached_one_to_none() -> None:
    graph = _grid()
    last = ROWS * COLUMNS - 1
    domains = hearth_domains(graph, (0, last))
    assert domains[0] == 0
    assert domains[last] == 1
    assert set(domains[:last].tolist()) == {0, 1}
    assert domains[10] == 0
    assert domains[last - 9] == 1
    assert domains[ROWS * COLUMNS :].tolist() == [-1] * ISLAND
    assert hearth_domains(graph, ()).tolist() == [-1] * len(graph.capacity)


def test_travel_costs_run_over_land_and_sea_links_and_miss_what_neither_reaches() -> None:
    graph = _grid()
    cost = travel_from(graph, 0)
    assert cost[0] == 0
    assert cost[1] == STEP_COST
    assert cost[COLUMNS] == STEP_COST
    assert cost[ROWS * COLUMNS] == -1
    linked = replace(graph, links=np.array([[0, ROWS * COLUMNS]], dtype=np.int64))
    assert travel_from(linked, 0)[ROWS * COLUMNS] == graph.link_cost + STEP_COST
