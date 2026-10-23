"""The content model: eligible bearers, absences, independence of the draws (synthetic worlds)."""

from __future__ import annotations

import random

from rnw.content import (
    CENTRE_RANKS,
    EARLIEST_OFFSET,
    FAMILIES,
    FORMABLE_FAMILIES,
    LATEST_OFFSET,
    MAX_CHAINS,
    MAX_RIVER_CENTRES,
    MAX_UNION_STATES,
    MAX_UNIONS,
    MIN_UNION_PLACES,
    RIVER_CENTRE,
    RIVER_UNION,
    SACRED_CENTRE,
    START_YEAR,
    STORY_FAMILIES,
    UNION_TERRITORY,
    WINDOW_YEARS,
    ContentPlan,
    Facts,
    Formation,
    Place,
    State,
    plan_content,
)

SEED = 12345


def _world(
    *,
    count: int = 36,
    river: int = 1,
    states: int = 3,
    holy: tuple[int, ...] = (),
    breaks: tuple[int, ...] = (),
) -> Facts:
    """A chain of places along one river, split among ``states`` states."""
    per_state = count // states
    places: dict[str, Place] = {}
    owners: dict[str, str] = {}
    for index in range(count):
        owner = f"S{min(index // per_state, states - 1)}"
        key = f"p{index:03d}"
        owners[key] = owner
        rank = "city" if index % 9 == 4 else ""
        places[key] = Place(key, 100 + (index % 7) * 10, river, rank, f"faith_{owner}", owner)
    state_table = {
        f"S{n}": State(f"S{n}", f"p{n * per_state:03d}", f"faith_S{n}") for n in range(states)
    }
    links = frozenset((f"p{i:03d}", f"p{i + 1:03d}") for i in range(count - 1) if i not in breaks)
    return Facts(places, state_table, frozenset(f"p{i:03d}" for i in holy), links)


def _unions(plan: ContentPlan) -> list[Formation]:
    return [formation for formation in plan.formations if formation.family == RIVER_UNION]


def test_a_river_world_offers_the_river_families() -> None:
    """A long river under three states gives a centre, a sacred centre and a union."""
    plan = plan_content(_world(holy=(2, 20)), SEED)
    counts = plan.count()
    assert counts[RIVER_CENTRE] >= 1
    assert counts[SACRED_CENTRE] >= 1
    assert counts[RIVER_UNION] == 1
    held = {RIVER_CENTRE, SACRED_CENTRE, RIVER_UNION}
    assert {absence.family for absence in plan.absences} <= set(FAMILIES) - held
    union = _unions(plan)[0]
    assert len(union.states) == 3
    assert len(union.centres) >= 3


def test_every_bearer_stands_where_the_family_requires() -> None:
    """Bearers own their centre; centres lie on a river; a sacred one is held by its faith."""
    facts = _world(holy=(2, 20, 30))
    plan = plan_content(facts, SEED)
    seen: set[str] = set()
    for opportunity in plan.opportunities:
        place = facts.places[opportunity.centre]
        assert place.owner == opportunity.bearer
        assert opportunity.centre not in seen
        seen.add(opportunity.centre)
        if opportunity.family == RIVER_CENTRE:
            assert place.river >= 1
        else:
            assert opportunity.centre in facts.holy
            assert place.religion == facts.states[place.owner].religion
    bearers = [o.bearer for o in plan.opportunities]
    assert all(bearers.count(tag) <= MAX_CHAINS for tag in set(bearers))
    assert len([o for o in plan.opportunities if o.family == RIVER_CENTRE]) <= MAX_RIVER_CENTRES


def test_starts_are_spread_over_the_early_decades_and_never_at_1337() -> None:
    """Each story begins some years after the start of the game, in its own window."""
    plan = plan_content(_world(holy=(2, 20)), SEED)
    for opportunity in plan.opportunities:
        start = opportunity.start
        assert START_YEAR + EARLIEST_OFFSET <= start.year <= START_YEAR + LATEST_OFFSET
        assert start.until - start.year == WINDOW_YEARS
        assert 1 <= start.chance <= 10


def test_a_world_without_a_river_has_no_river_family_and_says_why() -> None:
    """An island or a highland: no centre and no union, and the reasons are recorded."""
    plan = plan_content(_world(river=0, holy=(2,)), SEED)
    reasons = {absence.family: absence.reason for absence in plan.absences}
    assert RIVER_CENTRE in reasons
    assert RIVER_UNION in reasons
    assert plan.count()[RIVER_CENTRE] == 0
    assert plan.count()[SACRED_CENTRE] >= 1  # the sacred centre needs no river


def test_basins_cut_into_small_pieces_make_no_union() -> None:
    """Disconnected stretches below the minimum size join nothing."""
    cut = tuple(range(MIN_UNION_PLACES - 2, 36, MIN_UNION_PLACES - 1))
    plan = plan_content(_world(breaks=cut), SEED)
    assert plan.count()[RIVER_UNION] == 0
    assert any(absence.family == RIVER_UNION for absence in plan.absences)


def test_a_basin_under_one_state_is_no_union() -> None:
    """A union needs more than one state to consolidate."""
    plan = plan_content(_world(states=1), SEED)
    assert plan.count()[RIVER_UNION] == 0
    reason = next(a.reason for a in plan.absences if a.family == RIVER_UNION)
    assert "more than one state" in reason


def test_holy_places_in_foreign_faiths_give_no_sacred_centre() -> None:
    """A holy place held by a state of another faith is not a sacred centre."""
    facts = _world(holy=(2,))
    foreign = Place("p002", 500, 1, "", "other_faith", "S0")
    places = {**facts.places, "p002": foreign}
    plan = plan_content(Facts(places, facts.states, facts.holy, facts.links), SEED)
    assert plan.count()[SACRED_CENTRE] == 0
    assert any(a.family == SACRED_CENTRE for a in plan.absences)


def test_the_plan_does_not_depend_on_the_order_of_the_facts() -> None:
    """Shuffled places, states and links give the same plan."""
    facts = _world(holy=(2, 20))
    shuffled = random.Random(7)  # noqa: S311 - a test shuffle, not a secret
    keys = list(facts.places)
    shuffled.shuffle(keys)
    links = list(facts.links)
    shuffled.shuffle(links)
    other = Facts(
        {key: facts.places[key] for key in keys},
        dict(reversed(list(facts.states.items()))),
        facts.holy,
        frozenset(links),
    )
    assert plan_content(other, SEED) == plan_content(facts, SEED)


def test_the_families_draw_from_streams_of_their_own() -> None:
    """Holy places add sacred centres and change nothing in the river centres or the union."""
    with_holy = plan_content(_world(holy=(2, 20)), SEED)
    without = plan_content(_world(), SEED)
    assert [o for o in with_holy.opportunities if o.family == RIVER_CENTRE] == [
        o for o in without.opportunities if o.family == RIVER_CENTRE
    ]
    assert with_holy.formations == without.formations
    assert without.count()[SACRED_CENTRE] == 0


def test_another_seed_makes_another_plan_and_the_same_seed_the_same() -> None:
    """Plans follow the peoples seed and nothing else."""
    facts = _world(holy=(2, 20))
    assert plan_content(facts, SEED) == plan_content(facts, SEED)
    assert plan_content(facts, SEED) != plan_content(facts, SEED + 1)


def test_unions_do_not_overlap_and_stay_within_the_limit() -> None:
    """Two basins far apart give two unions; each keeps its own territory."""
    facts = _world(count=80, states=4, breaks=(39,))
    plan = plan_content(facts, SEED)
    unions = _unions(plan)
    assert 1 <= len(unions) <= MAX_UNIONS
    territory = [set(union.places) for union in unions]
    for number, first in enumerate(territory):
        for second in territory[number + 1 :]:
            assert not first & second
    assert unions[0].index == 0


def test_the_centre_ranks_are_the_ranked_places() -> None:
    """The ranks that make a centre are cities and towns."""
    assert {"city", "town"} == CENTRE_RANKS
    assert set(STORY_FAMILIES) | set(FORMABLE_FAMILIES) == set(FAMILIES)
    assert len(FAMILIES) == len(set(FAMILIES)) == 11


def test_a_union_is_a_connected_stretch_of_the_river_under_a_few_states() -> None:
    """A long river gives a union of at most the territory limit, joined, under its neighbours."""
    facts = _world(count=120, states=12)
    plan = plan_content(facts, SEED)
    assert _unions(plan)
    for union in _unions(plan):
        assert MIN_UNION_PLACES <= len(union.places) <= UNION_TERRITORY
        assert len(union.states) <= MAX_UNION_STATES
        members = set(union.places)
        reached = {union.seat}
        frontier = [union.seat]
        while frontier:
            here = frontier.pop()
            for first, second in facts.links:
                for a, b in ((first, second), (second, first)):
                    if a == here and b in members and b not in reached:
                        reached.add(b)
                        frontier.append(b)
        assert reached == members
        assert union.seat in members


def test_a_state_begins_at_most_one_story_a_year() -> None:
    """When a state bears two chains their starts fall in different years."""
    facts = _world(count=12, states=1, holy=(4,))
    for seed in range(40):
        plan = plan_content(facts, seed)
        for tag in {o.bearer for o in plan.opportunities}:
            years = [o.start.year for o in plan.opportunities if o.bearer == tag]
            assert len(years) == len(set(years))
