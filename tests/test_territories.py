"""Territorial growth follows broad habitat corridors without changing identities."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from rnw.settings import NATIVES
from rnw.societies import (
    STATE,
    STEP_COST,
    LandGraph,
    StateFloor,
    _Graph,  # pyright: ignore[reportPrivateUsage]
    _Territory,  # pyright: ignore[reportPrivateUsage]
    generate_societies,
)


def _corridor() -> tuple[LandGraph, np.ndarray]:
    """A three-location-wide fertile valley bends toward the northern coast."""
    rows, columns = 15, 25
    ids = np.arange(rows * columns).reshape(rows, columns)
    edges = np.concatenate(
        (
            np.column_stack((ids[:, :-1].ravel(), ids[:, 1:].ravel())),
            np.column_stack((ids[:-1].ravel(), ids[1:].ravel())),
        )
    )
    potential = np.full((rows, columns), 100, dtype=np.int64)
    potential[6:9, :13] = 900
    potential[3:9, 11:14] = 900
    potential[2:5, 11:] = 900
    coastal = np.zeros_like(potential, dtype=bool)
    coastal[0] = True
    return LandGraph(
        capacity=np.full(ids.size, 5000, dtype=np.int64),
        potential=potential.ravel(),
        cost=np.full(ids.size, STEP_COST, dtype=np.int64),
        edges=edges,
        links=np.zeros((0, 2), dtype=np.int64),
        coastal=coastal.ravel(),
    ), ids


def _connected(graph: _Graph, members: tuple[int, ...], capital: int) -> bool:
    allowed = np.zeros(len(graph.starts) - 1, dtype=bool)
    allowed[list(members)] = True
    _, owner = graph.grow([capital], allowed=allowed)
    return set(np.flatnonzero(owner >= 0).tolist()) == set(members)


def test_farming_growth_follows_a_bend_instead_of_a_radius() -> None:
    """A valley polity reaches a broad, far fertile arm and stays connected."""
    land, ids = _corridor()
    graph = _Graph(land)
    capitals = [int(ids[7, 2]), int(ids[14, 20])]
    _, radial = graph.grow(capitals)
    territory = replace(_Territory.of(land, graph, 3), styles=[1] * ids.size)
    _, following = graph.grow(capitals, territory=territory)
    arm = ids[2:5, 20:].ravel()
    assert np.all(radial[arm] == 1)
    assert np.all(following[arm] == 0)
    for index, capital in enumerate(capitals):
        members = tuple(np.flatnonzero(following == index).tolist())
        assert capital in members
        assert _connected(graph, members, capital)


@pytest.mark.parametrize("style", [2, 3], ids=["upland", "coast"])
def test_habitat_growth_follows_a_broad_belt(style: int) -> None:
    """Coast and upland preferences extend occupation along broad belts."""
    land, ids = _corridor()
    # Two parallel habitats: a highland/coastal belt and an inland lowland.
    terrain = np.full(ids.shape, STEP_COST, dtype=np.int64)
    terrain[:3] = 3 * STEP_COST
    if style == 2:
        land = replace(land, cost=terrain.ravel())
    graph = _Graph(land)
    capitals = [int(ids[1, 2]), int(ids[10, 12])]
    _, ordinary = graph.grow(capitals)
    territory = replace(_Territory.of(land, graph, 42), styles=[style] * ids.size)
    _, following = graph.grow(capitals, territory=territory)
    belt = ids[:3, 12:].ravel()
    assert np.count_nonzero(following[belt] == 0) > np.count_nonzero(ordinary[belt] == 0)
    for index, capital in enumerate(capitals):
        members = tuple(np.flatnonzero(following == index).tolist())
        assert _connected(graph, members, capital)


def test_coastal_distance_uses_wrap_contacts_and_shared_water() -> None:
    """The seam is an ordinary contact; a coastless component gets no coastal style."""
    land = LandGraph(
        capacity=np.ones(7, dtype=np.int64),
        potential=np.full(7, 500, dtype=np.int64),
        cost=np.full(7, STEP_COST, dtype=np.int64),
        edges=np.array([(0, 1), (1, 2), (2, 3), (3, 0), (5, 6)], dtype=np.int64),
        links=np.array([(0, 4)], dtype=np.int64),
        coastal=np.array([True, False, False, False, True, False, False]),
    )
    graph = _Graph(land)
    territory = _Territory.of(land, graph, 42)
    assert territory.inland == [0, 1000, 2000, 1000, 0, 4000, 4000]
    assert territory.styles == _Territory.of(land, graph, 42).styles
    assert all(style != 3 for style in territory.styles[5:])
    _, owner = graph.grow([0], territory=territory)
    assert owner.tolist() == [0, 0, 0, 0, 0, -1, -1]
    coastless = _Territory.of(replace(land, coastal=None), graph, 42)
    assert all(style != 3 for style in coastless.styles)


@pytest.mark.parametrize("seed", [3, 42, 1000])
@pytest.mark.parametrize("chance", [0, 1000], ids=["ordinary", "extraordinary"])
def test_affinities_keep_population_identities_support_and_connected_ownership(
    monkeypatch: pytest.MonkeyPatch, seed: int, chance: int
) -> None:
    """Only political growth changes; all polities keep capitals and eligible state land."""
    land, ids = _corridor()
    # Add a normal seam contact; the shared-water island has its own regression above.
    land = replace(
        land,
        edges=np.concatenate((land.edges, np.array([(int(ids[0, 0]), int(ids[0, -1]))]))),
    )
    settings = replace(
        NATIVES,
        hearths_per_10k=80,
        hearth_reach_steps=12,
        state_locations=10,
        state_share_permille=440,
        culture_locations=40,
        religion_locations=150,
        tribe_locations=12,
        organized_permille=1000,
        empire_permille=chance,
    )
    floor = StateFloor(338, 122)
    societies = generate_societies(land, settings, seed=seed, target=4_000_000, state_floor=floor)
    again = generate_societies(land, settings, seed=seed, target=4_000_000, state_floor=floor)
    assert societies.polities == again.polities
    graph = _Graph(land)
    held: set[int] = set()
    for polity in societies.polities:
        assert polity.capital in polity.members
        assert not held.intersection(polity.members)
        assert _connected(graph, polity.members, polity.capital)
        held.update(polity.members)
        if polity.kind == STATE:
            nodes = list(polity.members)
            assert floor.supports(
                int(societies.population[nodes].sum()), int(societies.peasants[nodes].sum())
            )
            assert floor.supports(
                int(societies.population[polity.capital]), int(societies.peasants[polity.capital])
            )

    def neutral_penalty(_self: _Territory, _capital: int, _target: int) -> int:
        return 1000

    monkeypatch.setattr(_Territory, "penalty", neutral_penalty)
    neutral = generate_societies(land, settings, seed=seed, target=4_000_000, state_floor=floor)
    for name in ("population", "peasants", "complexity", "religion", "culture"):
        assert np.array_equal(getattr(societies, name), getattr(neutral, name))
    assert societies.hearths == neutral.hearths
    assert societies.polities != neutral.polities
