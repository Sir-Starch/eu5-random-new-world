"""Which polities form a sea league, a confederation, a fractured realm or a sacred centre."""

from __future__ import annotations

from typing import cast

import pytest

from rnw.archetypes import (
    FRACTURED_REALM,
    HIGHLAND_CONFEDERATION,
    KINDS,
    SACRED_CENTRE,
    SEA_LEAGUE,
    Group,
    Rules,
    Structure,
    alliance_pairs,
    fractured_realms,
    highland_confederations,
    options,
    plan_archetypes,
    rival_pairs,
    sacred_centres,
    sea_leagues,
)

RULES = Rules(level=2, density=0)


def _structure(count: int, **changes: object) -> Structure:
    """``count`` free level-2 states of one religion that touch nobody, in one domain."""
    fields: dict[str, object] = {
        "state": [True] * count,
        "free": [True] * count,
        "level": [2] * count,
        "population": [1000 - number for number in range(count)],
        "locations": [5] * count,
        "near": [set[int]() for _ in range(count)],
        "religion": [0] * count,
        "complexity": [800] * count,
        "highland": [0] * count,
        "ports": [dict[int, int]() for _ in range(count)],
        "domain": [0] * count,
        "domains": 1,
        "cradle": frozenset[int](),
    }
    fields.update(changes)
    return Structure(**fields)  # pyright: ignore[reportArgumentType]


def _touch(structure: Structure, *pairs: tuple[int, int]) -> None:
    near = cast("list[set[int]]", structure.near)
    for first, second in pairs:
        near[first].add(second)
        near[second].add(first)


def _chain(structure: Structure, nodes: range) -> None:
    _touch(structure, *zip(nodes, list(nodes)[1:], strict=False))


def test_a_sea_league_is_three_states_of_one_sea_that_the_land_does_not_join() -> None:
    structure = _structure(5, ports=[{7: 10 + n} for n in range(4)] + [{9: 99}])
    _touch(structure, (0, 1))
    found = sea_leagues(structure, 2)
    assert [(g.kind, g.members, g.zone, g.ports) for g in found] == [
        (SEA_LEAGUE, (0, 1, 2, 3), 7, (10, 11, 12, 13))
    ]
    assert found[0].hub == 0


def test_states_all_in_land_contact_are_no_league_and_neither_are_two() -> None:
    ports = [{7: n} for n in range(3)]
    assert sea_leagues(_structure(3, ports=ports), 2)[0].members == (0, 1, 2)
    joined = _structure(3, ports=ports)
    _touch(joined, (0, 1), (0, 2), (1, 2))
    assert sea_leagues(joined, 2) == []
    assert sea_leagues(_structure(2, ports=[{7: 0}, {7: 1}]), 2) == []


@pytest.mark.parametrize("field", ["free", "state", "level"])
def test_a_league_takes_only_free_states_of_the_republics_level(field: str) -> None:
    values: dict[str, list[object]] = {
        "free": [True, True, False],
        "state": [True, True, False],
        "level": [2, 2, 1],
    }
    structure = _structure(3, ports=[{7: n} for n in range(3)], **{field: values[field]})
    assert sea_leagues(structure, 2) == []


def test_a_league_has_at_most_five_members_the_most_populous() -> None:
    structure = _structure(7, ports=[{7: n} for n in range(7)], population=[1, 9, 2, 8, 3, 7, 4])
    assert sea_leagues(structure, 2)[0].members == (1, 3, 5, 6, 4)


def _highland(count: int, **changes: object) -> Structure:
    fields: dict[str, object] = {
        "state": [False] * count,
        "highland": [900] * count,
        "level": [-1] * count,
    }
    fields.update(changes)
    structure = _structure(count, **fields)
    _chain(structure, range(count))
    return structure


def test_touching_highland_tribes_of_one_religion_form_a_confederation() -> None:
    structure = _highland(4)
    found = highland_confederations(structure, 0)
    assert [(g.kind, g.members) for g in found] == [(HIGHLAND_CONFEDERATION, (0, 1, 2, 3))]


@pytest.mark.parametrize(
    "changes",
    [
        {"highland": [900, 900, 500, 900]},
        {"religion": [0, 0, 1, 0]},
        {"free": [True, True, False, True]},
        {"state": [False, False, True, False]},
    ],
)
def test_a_tribe_off_the_hills_of_another_faith_or_a_state_breaks_the_chain(
    changes: dict[str, list[object]],
) -> None:
    assert highland_confederations(_highland(4, **changes), 0) == []


def test_two_tribes_are_no_confederation_and_a_big_chain_is_cut_to_six_connected_ones() -> None:
    assert highland_confederations(_highland(2), 0) == []
    structure = _highland(9, population=[1, 2, 3, 4, 5, 6, 7, 8, 9])
    (group,) = highland_confederations(structure, 0)
    assert len(group.members) == 6
    assert group.hub == 8
    assert set(group.members) == {8, 7, 6, 5, 4, 3}


def test_a_confederation_needs_the_density_of_the_calibration() -> None:
    structure = _highland(4)
    density = sum(structure.population) // sum(structure.locations)
    assert len(highland_confederations(structure, density)) == 1
    assert highland_confederations(structure, density + 1) == []


def test_a_fractured_realm_holds_together_the_land_of_an_empire() -> None:
    assert fractured_realms(_realm(locations=[3, 3, 3, 3])) != []
    assert fractured_realms(_realm(locations=[3, 3, 3, 2])) == []


def test_a_sacred_centre_is_among_the_most_populous_quarter_of_the_states() -> None:
    structure = _structure(
        8, cradle=frozenset({0}), population=[100, 900, 800, 700, 600, 500, 400, 300]
    )
    _touch(structure, (0, 1), (0, 2))
    assert sacred_centres(structure) == []
    structure = _structure(
        8, cradle=frozenset({0}), population=[800, 900, 100, 700, 600, 500, 400, 300]
    )
    _touch(structure, (0, 1), (0, 2))
    assert [g.members for g in sacred_centres(structure)] == [(0, 1, 2)]


def _realm(count: int = 4, **changes: object) -> Structure:
    structure = _structure(count, **changes)
    _touch(structure, *((0, other) for other in range(1, count)))
    return structure


def test_touching_states_of_one_faith_and_complex_capitals_are_a_fractured_realm() -> None:
    (group, *_) = fractured_realms(_realm())
    assert (group.kind, group.members) == (FRACTURED_REALM, (0, 1, 2, 3))


def test_a_dominant_state_a_simple_capital_or_another_faith_keep_a_state_out() -> None:
    assert fractured_realms(_realm(population=[900, 100, 100, 100])) == []
    assert fractured_realms(_realm(complexity=[800, 800, 400, 800]))[0].members == (0, 1, 3)
    assert fractured_realms(_realm(religion=[0, 0, 1, 0]))[0].members == (0, 1, 3)
    assert fractured_realms(_realm(complexity=[800, 800, 400, 400])) == []


def test_a_fractured_realm_has_at_most_four_centres() -> None:
    assert fractured_realms(_realm(6))[0].members == (0, 1, 2, 3)


def test_the_cradle_state_with_competitors_of_its_faith_is_a_sacred_centre() -> None:
    structure = _structure(
        5, cradle=frozenset({2}), religion=[0, 0, 0, 0, 1], population=[900, 800, 1000, 700, 600]
    )
    _touch(structure, (2, 0), (2, 1), (2, 4))
    (group,) = sacred_centres(structure)
    assert (group.kind, group.hub, group.members) == (SACRED_CENTRE, 2, (2, 0, 1))


def test_a_centre_needs_two_competitors_and_takes_at_most_three() -> None:
    structure = _structure(3, cradle=frozenset({0}))
    _touch(structure, (0, 1))
    assert sacred_centres(structure) == []
    many = _structure(6, cradle=frozenset({0}))
    _touch(many, *((0, other) for other in range(1, 6)))
    assert sacred_centres(many)[0].members == (0, 1, 2, 3)
    bound = _structure(4, cradle=frozenset({0}), free=[False, True, True, True])
    _touch(bound, (0, 1), (0, 2), (0, 3))
    assert sacred_centres(bound) == []


def _world() -> Structure:
    """Two domains: a sea league and a sacred centre in the first, tribes in the second."""
    structure = _structure(
        12,
        state=[True] * 6 + [False] * 6,
        level=[2] * 6 + [-1] * 6,
        ports=[{7: n} for n in range(3)] + [{} for _ in range(9)],
        domain=[0] * 6 + [1] * 6,
        domains=3,
        cradle=frozenset({3}),
        population=[900, 800, 700, 1000, 600, 500] + [100 * n for n in range(1, 7)],
        highland=[0] * 6 + [900] * 6,
        religion=[0] * 12,
    )
    _touch(structure, (3, 4), (3, 5))
    _chain(structure, range(6, 12))
    return structure


def test_options_list_every_group_by_kind() -> None:
    found = options(_world(), RULES)
    assert set(found) == set(KINDS)
    assert [len(found[kind]) for kind in KINDS] == [1, 1, 1, 1]


def test_a_chance_of_nothing_chooses_nothing_and_a_sure_one_chooses_a_group_for_each_domain() -> (
    None
):
    structure = _world()
    assert plan_archetypes(structure, RULES, chance=0, seed=1) == ()
    chosen = plan_archetypes(structure, RULES, chance=1000, seed=1)
    assert sorted(group.domain for group in chosen) == [0, 1]
    assert {group.kind for group in chosen if group.domain == 1} == {HIGHLAND_CONFEDERATION}


def test_the_choice_is_the_same_each_time_and_depends_on_the_seed() -> None:
    structure = _world()
    first = plan_archetypes(structure, RULES, chance=1000, seed=5)
    assert plan_archetypes(structure, RULES, chance=1000, seed=5) == first
    kinds = {
        group.kind
        for seed in range(30)
        for group in plan_archetypes(structure, RULES, chance=1000, seed=seed)
        if group.domain == 0
    }
    assert kinds == {SEA_LEAGUE, FRACTURED_REALM, SACRED_CENTRE}


def test_a_higher_chance_chooses_in_the_same_domains_and_more() -> None:
    structure = _world()
    for seed in range(20):
        low = {g.domain: g for g in plan_archetypes(structure, RULES, chance=400, seed=seed)}
        high = {g.domain: g for g in plan_archetypes(structure, RULES, chance=1000, seed=seed)}
        assert low.items() <= high.items()


def test_a_group_never_takes_a_polity_an_earlier_group_holds() -> None:
    structure = _structure(
        8,
        ports=[{7: n} for n in range(3)] + [{} for _ in range(5)],
        population=[500, 900, 800, 700, 600, 400, 300, 200],
        domain=[0, 1, 1, 0, 0, 1, 1, 1],
        domains=2,
        cradle=frozenset({0}),
    )
    _touch(structure, (0, 3), (0, 4))
    for seed in range(40):
        chosen = plan_archetypes(structure, RULES, chance=1000, seed=seed)
        # Every group of the first domain holds polity 0, the one group of the second needs it.
        assert [group.domain for group in chosen] == [0]


def _group(kind: str, members: tuple[int, ...]) -> Group:
    return Group(kind, members[0], members, 0)


@pytest.mark.parametrize("count", [3, 4, 5])
def test_a_ring_gives_every_member_two_alliances(count: int) -> None:
    pairs = alliance_pairs(_group(SEA_LEAGUE, tuple(range(count))))
    assert len(pairs) == count == len(set(pairs))
    holds = [sum(1 for pair in pairs if member in pair) for member in range(count)]
    assert holds == [2] * count


def test_only_a_league_has_alliances() -> None:
    for kind in KINDS[1:]:
        assert alliance_pairs(_group(kind, (0, 1, 2))) == ()


def test_rivals_are_returned_pairs_of_touching_centres_or_of_the_centre_and_its_competitors() -> (
    None
):
    near = [{1, 2}, {0}, {0}, set[int]()]
    realm = rival_pairs(_group(FRACTURED_REALM, (0, 1, 2)), near)
    assert realm == ((0, 1), (0, 2), (1, 0), (2, 0))
    centre = rival_pairs(_group(SACRED_CENTRE, (3, 0, 1)), near)
    assert centre == ((0, 3), (1, 3), (3, 0), (3, 1))
    assert rival_pairs(_group(SEA_LEAGUE, (0, 1, 2)), near) == ()
    assert rival_pairs(_group(HIGHLAND_CONFEDERATION, (0, 1, 2)), near) == ()
