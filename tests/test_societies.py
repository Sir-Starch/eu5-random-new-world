"""Native societies on synthetic land graphs."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import hashlib
from dataclasses import replace
from statistics import median

import numpy as np
import pytest

from rnw.eu5_natives import _pop_cohorts, pop_lines  # pyright: ignore[reportPrivateUsage]
from rnw.rng import SplitMix64
from rnw.settings import NATIVES
from rnw.societies import (
    CITY,
    EMPIRE_FLOOR,
    STATE,
    STEP_COST,
    TOWN,
    TRIBE,
    LandGraph,
    Polity,
    Societies,
    StateFloor,
    _Graph,  # pyright: ignore[reportPrivateUsage]
    _Identity,  # pyright: ignore[reportPrivateUsage]
    _states,  # pyright: ignore[reportPrivateUsage]
    generate_societies,
    hearth_domains,
    land_routes,
    regional_markets,
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


def _fragmented_grid() -> LandGraph:
    """The same land count in six separated blocks and a small detached island."""
    graph = _grid()
    edges = [
        (int(first), int(second))
        for first, second in graph.edges.tolist()
        if first < ROWS * COLUMNS
        and second < ROWS * COLUMNS
        and (first // COLUMNS) // 10 == (second // COLUMNS) // 10
        and (first % COLUMNS) // 15 == (second % COLUMNS) // 15
    ]
    base = ROWS * COLUMNS
    edges.extend((base + index, base + index + 1) for index in range(ISLAND - 1))
    potential = np.full(len(graph.capacity), 550, dtype=np.int64)
    potential[base:] = 100
    return LandGraph(
        capacity=graph.capacity.copy(),
        potential=potential,
        cost=graph.cost.copy(),
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


def _written_country_shares(societies: Societies) -> list[tuple[int, int]]:
    """Read the serialized pop types and return peasants / total for each landed country."""
    keys = [f"loc_{node}" for node in range(len(societies.population))]
    religions = ["test_religion"] * (int(societies.religion.max()) + 1)
    cultures = ["test_culture"] * (int(societies.culture.max()) + 1)
    written = pop_lines(_pop_cohorts(societies, keys, religions, cultures))
    amounts: list[dict[str, int]] = [{} for _ in keys]
    for node, key in enumerate(keys):
        found: dict[str, int] = {}
        for line in written.get(key, []):
            parts = line.split()
            kind = parts[parts.index("type") + 2]
            whole, _, fraction = parts[parts.index("size") + 2].partition(".")
            found[kind] = int(whole) * 1000 + int(fraction)
        amounts[node] = found
    shares: list[tuple[int, int]] = []
    for polity in societies.polities:
        if polity.kind != STATE:
            continue
        actual = sum(sum(amounts[node].values()) for node in polity.members)
        expected = int(societies.population[list(polity.members)].sum())
        assert actual == expected
        shares.append(
            (
                sum(amounts[node].get("peasants", 0) for node in polity.members),
                actual,
            )
        )
    return shares


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


@pytest.mark.parametrize("empire_chance", [0, 1000], ids=["ordinary", "extraordinary"])
def test_peasant_mix_changes_written_country_shares_without_changing_population(
    empire_chance: int,
) -> None:
    """The control changes serialized country pop shares, while support and totals still hold."""
    graph = _grid()
    floor = StateFloor(peasants=338, share=122)
    by_peak: dict[int, Societies] = {}
    actual_shares: dict[int, list[tuple[int, int]]] = {}
    for peak in (300, 800):
        settings = replace(
            SETTINGS,
            empire_permille=empire_chance,
            peasant_peak_permille=peak,
        )
        societies = generate_societies(graph, settings, seed=4, target=4_000_000, state_floor=floor)
        by_peak[peak] = societies
        actual_shares[peak] = _written_country_shares(societies)
        states = [polity for polity in societies.polities if polity.kind == STATE]
        assert states
        assert all(
            floor.supports(
                int(societies.population[list(polity.members)].sum()),
                int(societies.peasants[list(polity.members)].sum()),
            )
            for polity in states
        )
        assert all(
            peasants >= 338 and peasants * 1000 >= total * 122
            for peasants, total in actual_shares[peak]
        )
    lower, higher = by_peak[300], by_peak[800]
    assert np.array_equal(lower.population, higher.population)
    assert np.array_equal(lower.complexity, higher.complexity)
    assert int(lower.population.sum()) == int(higher.population.sum())
    assert np.all(higher.peasants >= lower.peasants)
    assert np.any(higher.peasants > lower.peasants)
    for peak in (300, 800):
        assert actual_shares[peak]
    lower_peasants = sum(peasants for peasants, _ in actual_shares[300])
    lower_population = sum(total for _, total in actual_shares[300])
    higher_peasants = sum(peasants for peasants, _ in actual_shares[800])
    higher_population = sum(total for _, total in actual_shares[800])
    assert higher_peasants * lower_population > lower_peasants * higher_population
    if empire_chance:
        assert any(polity.great for polity in higher.polities)


@pytest.mark.parametrize("shape", ["continents", "poor", "fragmented"])
def test_higher_state_targets_measure_coverage_without_bypassing_support(shape: str) -> None:
    """Coverage stress results stay reproducible while eligibility and population remain bounded."""
    graph = _grid() if shape != "fragmented" else _fragmented_grid()
    if shape == "poor":
        graph.potential[:] = 260
    floor = StateFloor(peasants=338, share=122)
    expected = {
        "continents": {
            110: (11.0, 10.6, 11.0),
            300: (20.9, 16.0, 22.4),
            450: (20.9, 16.0, 22.4),
            600: (20.9, 16.0, 22.4),
        },
        "poor": {
            110: (11.0, 11.0, 11.0),
            300: (22.2, 15.9, 23.5),
            450: (22.2, 15.9, 23.9),
            600: (22.2, 15.9, 23.9),
        },
        "fragmented": {
            110: (11.0, 11.0, 11.0),
            300: (25.6, 19.1, 27.1),
            450: (27.6, 21.4, 29.3),
            600: (28.5, 21.6, 29.8),
        },
    }
    for share in (110, 300, 450, 600):
        coverage: list[float] = []
        for seed in (3, 4, 7, 42, 77, 1000):
            settings = replace(
                SETTINGS,
                state_share_permille=share,
                state_spread_permille=150,
                empire_permille=0,
            )
            societies = generate_societies(
                graph, settings, seed=seed, target=4_000_000, state_floor=floor
            )
            inhabited = int(np.count_nonzero(societies.population))
            held = [
                member
                for polity in societies.polities
                if polity.kind == STATE
                for member in polity.members
            ]
            assert 0 < len(held) <= inhabited * share // 1000
            coverage.append(100 * len(held) / inhabited)
            assert 4_000_000 - len(graph.capacity) <= int(societies.population.sum()) <= 4_000_000
            assert np.all(societies.peasants <= societies.population)
            assert all(
                floor.supports(
                    int(societies.population[list(polity.members)].sum()),
                    int(societies.peasants[list(polity.members)].sum()),
                )
                for polity in societies.polities
                if polity.kind == STATE
            )
        assert (
            round(median(coverage), 1),
            round(min(coverage), 1),
            round(max(coverage), 1),
        ) == expected[shape][share]


def test_state_share_control_boundaries_generate_deterministically() -> None:
    """The lowest and highest window values keep seeded society output reproducible."""
    graph = _grid()
    floor = StateFloor(peasants=338, share=122)
    for share in (30, 600):
        settings = replace(SETTINGS, state_share_permille=share)
        first = generate_societies(graph, settings, seed=42, target=4_000_000, state_floor=floor)
        again = generate_societies(graph, settings, seed=42, target=4_000_000, state_floor=floor)
        assert first.polities == again.polities
        assert np.array_equal(first.population, again.population)
        assert np.array_equal(first.peasants, again.peasants)


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


@pytest.mark.parametrize("seed", [3, 4, 77])
@pytest.mark.parametrize("chance", [0, 1000])
def test_remote_states_have_farming_support_before_population_is_allocated(
    seed: int, chance: int
) -> None:
    graph = _grid()
    floor = StateFloor(peasants=338, share=122)
    societies = generate_societies(
        graph,
        replace(SETTINGS, state_spread_permille=600, empire_permille=chance),
        seed=seed,
        target=4_000_000,
        state_floor=floor,
    )
    states = [p for p in societies.polities if p.kind == STATE]
    assert states
    costs = [travel_from(graph, hearth) for hearth in societies.hearths]
    remote = [
        p
        for p in states
        if all(
            d[p.capital] < 0 or d[p.capital] >= SETTINGS.hearth_reach_steps * STEP_COST
            for d in costs
        )
    ]
    assert remote
    assert all(societies.complexity[p.capital] > 0 for p in remote)
    assert all(
        floor.supports(
            int(societies.population[list(p.members)].sum()),
            int(societies.peasants[list(p.members)].sum()),
        )
        for p in states
    )
    assert all(_connected(set(p.members), graph.edges) for p in societies.polities)
    assert int(societies.population.sum()) <= 4_000_000
    assert np.all(societies.peasants <= societies.population)


def test_poor_islands_do_not_become_empty_states_and_population_is_not_granted() -> None:
    graph = _grid()
    graph.potential[ROWS * COLUMNS :] = 0
    societies = generate_societies(
        graph,
        replace(
            SETTINGS,
            state_spread_permille=600,
            organized_permille=1000,
            peasant_peak_permille=800,
        ),
        seed=3,
        target=4_000_000,
        state_floor=StateFloor(peasants=338, share=122),
    )
    island = set(range(ROWS * COLUMNS, len(graph.capacity)))
    assert any(island & set(p.members) for p in societies.polities if p.kind == TRIBE)
    assert not any(island & set(p.members) for p in societies.polities if p.kind == STATE)
    assert np.all(societies.complexity[sorted(island)] == 0)
    assert 4_000_000 - len(graph.capacity) <= societies.population.sum() <= 4_000_000


def test_insufficient_population_remains_tribal_even_on_fertile_land() -> None:
    societies = generate_societies(
        _grid(),
        replace(SETTINGS, organized_permille=1000, empire_permille=1000),
        seed=3,
        target=40_000,
        state_floor=StateFloor(peasants=338, share=122),
    )
    assert not any(p.kind == STATE for p in societies.polities)
    assert any(p.kind == TRIBE for p in societies.polities)


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


# Epoch 60: identity-aware capitals and habitat growth, without empires.
NO_EMPIRES: dict[int, str] = {
    3: "b4965a25422110339daa33cd8152117704f837b8be1c0668ae5b6ae643a53366",
    4: "af399e538f5f3093c707dae837e83ffa8a1b203f2ea2f4e29383af6c3e6b86be",
    77: "34014ee4a6f1cf6b1a186969a0dc5a2c276752221183386849e5414f3cddfb41",
}


def test_without_great_empires_the_societies_match_the_reference() -> None:
    """Pin the complete society output for the current algorithm epoch."""
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
    assert any(societies.ranks.get(empire.capital) == CITY for empire in empires)


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


def test_identity_growth_keeps_foreign_passages_and_accumulated_cost() -> None:
    """Foreign land is traversable; crossing it never disconnects a matching enclave."""
    graph = _roads(4, [(0, 1), (1, 2)], links=[(2, 3)])
    identity = _Identity([0, 1, 0, 0], [0, 1, 0, 0])
    cost, owner = _Graph(graph).grow([0], identity=identity)
    assert cost.tolist() == [0, 6000, 7000, 12000]
    assert owner.tolist() == [0, 0, 0, 0]


def test_capital_selection_prefers_a_supported_identity_interior() -> None:
    """A slightly larger boundary town loses to the substantial neighbouring core."""
    graph = _Graph(_roads(7, [(n, n + 1) for n in range(6)]))
    population = np.array([50, 50, 110, 100, 100, 100, 100], dtype=np.int64)
    identity = _Identity([0, 0, 1, 1, 1, 1, 1], [0, 0, 1, 1, 1, 1, 1])
    eligible = np.ones(7, dtype=bool)
    eligible[:3] = False
    eligible[2] = True
    states = _states(
        graph,
        np.ones(7, dtype=bool),
        population,
        locations=7,
        rng=SplitMix64(3),
        eligible=eligible,
        identity=identity,
    )
    assert len(states) == 1
    capital, members = states[0]
    assert capital >= 3
    assert members == list(range(7))


def test_identity_cores_across_seeds_keep_minorities_and_agrarian_support() -> None:
    """Compare the pre-issue baseline matrix; shares weight residents, not locations.

    Six seeds, two disconnected-land shapes, state sizes 3/10 and 30-location faith
    zones stress identity boundaries. The measured baseline ordinary-large medians
    were .554 culture / .835 faith; empires .517 / .653 (docs/natives.md).
    """
    shares: dict[str, list[tuple[float, float]]] = {"large": [], "empire": []}
    tiny = 0
    floor = StateFloor(338, 122)
    for graph in (_grid(), _fragmented_grid()):
        for size in (3, 10):
            for seed in (3, 4, 7, 42, 77, 1000):
                settings = replace(
                    SETTINGS, state_locations=size, religion_locations=30, empire_permille=1000
                )
                societies = generate_societies(
                    graph, settings, seed=seed, target=4_000_000, state_floor=floor
                )
                for polity in societies.polities:
                    assert _connected(set(polity.members), graph.edges)
                    if polity.kind != STATE:
                        continue
                    members = list(polity.members)
                    population = societies.population[members]
                    total = int(population.sum())
                    assert floor.supports(total, int(societies.peasants[members].sum()))
                    culture = (
                        float(population[societies.culture[members] == polity.culture].sum())
                        / total
                    )
                    faith = (
                        float(
                            population[
                                societies.religion[members] == societies.religion[polity.capital]
                            ].sum()
                        )
                        / total
                    )
                    if polity.great:
                        shares["empire"].append((culture, faith))
                    elif len(members) > 5:
                        shares["large"].append((culture, faith))
                        tiny += culture < 0.25
    assert tiny < 14  # Baseline countries below 25% primary culture.
    for group in shares.values():
        assert median(c for c, _ in group) > 0.65
        assert median(r for _, r in group) > 0.90
        assert sum(c < 1 for c, _ in group) > len(group) // 2


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


@pytest.mark.parametrize("linked", [False, True])
def test_remote_state_groups_have_trading_towns_and_share_existing_markets(*, linked: bool) -> None:
    graph = _roads(5, [(0, 1), (2, 3)], links=[(1, 2)] if linked else [])
    zero = np.zeros(5, dtype=np.int64)
    before = Societies(
        complexity=zero,
        population=np.full(5, 3000, dtype=np.int64),
        peasants=zero,
        religion=zero,
        culture=zero,
        hearths=(),
        polities=(
            Polity(STATE, (0, 1), 0, 0),
            Polity(STATE, (2, 3), 2, 0),
            Polity(TRIBE, (4,), 4, 0),
        ),
        ranks={0: CITY},
        markets=(0,),
    )
    result = regional_markets(graph, before)
    assert result.markets == ((0,) if linked else (0, 2))
    assert result.ranks == ({0: CITY} if linked else {0: CITY, 2: TOWN})
    assert result.population is before.population
    assert result.polities == before.polities
    assert regional_markets(graph, result).markets == result.markets
    landed = replace(
        before, polities=(*before.polities[:2], replace(before.polities[2], landed=True))
    )
    assert 4 in regional_markets(graph, landed).markets
