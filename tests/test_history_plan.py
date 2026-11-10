"""Historical outcomes become one causally checked EU5 start plan."""

# NumPy scalar conversion is typed as Any in its stubs.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw.eu5_empires import EmpireCalibration
from rnw.eu5_history import HistoryBootstrap, canonical_population
from rnw.eu5_history_plan import ProjectionInputs, project_start
from rnw.eu5_history_values import position_ranges, profile_positions
from rnw.eu5_natives import (
    ADVANCED_STATE,
    DEFAULT_CITY,
    DEFAULT_STATE,
    DEFAULT_TOWN,
    DEFAULT_TRIBE,
    Culture,
    VanillaNatives,
    country_records,
)
from rnw.eu5_nw_export import _ai_diplomacy  # pyright: ignore[reportPrivateUsage]
from rnw.eu5_start import HistoricalOpinion, PopCohort
from rnw.history_context import Context
from rnw.history_diplomacy import select_opinions
from rnw.history_engine import advance, create, simulate
from rnw.history_model import (
    Action,
    Authority,
    Cohort,
    District,
    Exchange,
    Factor,
    Founding,
    Geography,
    Hearth,
    History,
    HistoryError,
    Military,
    Proposal,
    Route,
    Society,
    Tenure,
    TrajectoryKind,
)
from rnw.history_plan_checks import validate_projection
from rnw.history_values import (
    AXES,
    CENTRAL,
    EXCHANGE,
    MYSTICISM,
    POSTURE,
    QUALITY,
    SPIRITUAL,
    TRADITION,
)
from rnw.loc_keys import KeySpace
from rnw.pdx import parse
from rnw.societies import LandGraph, Polity, Societies, StateFloor

from .history_fixtures import divided_valley, valley, valley_policy
from .test_archetype_world import CALIBRATION
from .test_history_societies import _trajectory_world  # pyright: ignore[reportPrivateUsage]
from .test_laws import LAW_BOOK

if TYPE_CHECKING:
    from rnw.eu5_start import FinalStartPlan


RANGES = {
    AXES[0]: (60, 100),
    AXES[1]: (-90, -70),
    AXES[2]: (-90, -60),
    AXES[4]: (-50, 50),
    AXES[5]: (30, 100),
    AXES[6]: (-75, 10),
    AXES[7]: (-90, 60),
}


def quiet(history: History) -> History:
    return simulate(history, policy=lambda _: ())


def inputs_for(history: History) -> ProjectionInputs:
    root = create(
        history.geography,
        history.foundings,
        seed=history.seed,
        empire_permille=history.empire_permille,
        turbulence=history.turbulence,
    )
    places = tuple(sorted(root.geography.districts, key=lambda place: place.key))
    keys = tuple(place.key for place in places)
    nodes = {key: node for node, key in enumerate(keys)}
    pops = {
        place.key: tuple(
            pop
            for cohort in place.cohorts
            for pop in (
                PopCohort("peasants", cohort.peasants, cohort.culture, cohort.religion),
                PopCohort(
                    "tribesmen",
                    cohort.population - cohort.peasants,
                    cohort.culture,
                    cohort.religion,
                ),
            )
            if pop.amount
        )
        for place in places
        if place.cohorts
    }
    cultures = sorted({pop.culture for rows in pops.values() for pop in rows})
    faiths = sorted({pop.religion for rows in pops.values() for pop in rows})
    zero = np.zeros(len(keys), dtype=np.int64)
    populations = np.array([place.population for place in places], dtype=np.int64)
    societies = Societies(
        np.array([place.complexity for place in places], dtype=np.int64),
        populations,
        np.array([place.peasants for place in places], dtype=np.int64),
        zero,
        zero,
        tuple(nodes[hearth.centre] for hearth in root.geography.hearths),
        tuple(
            Polity(
                "state" if founding.tenure is Tenure.LAND else "tribe",
                tuple(nodes[key] for key in founding.districts),
                nodes[founding.seat],
                0,
            )
            for founding in root.foundings
            if founding.tenure is not Tenure.COMMUNITY
        ),
        {},
        (),
    )
    graph = LandGraph(
        populations.copy(),
        np.full(len(keys), 800, dtype=np.int64),
        np.array([place.defence for place in places], dtype=np.int64),
        np.array(
            [(nodes[r.first], nodes[r.second]) for r in root.geography.routes if not r.sea_steps],
            dtype=np.int64,
        ).reshape(-1, 2),
        np.array(
            [(nodes[r.first], nodes[r.second]) for r in root.geography.routes if r.sea_steps],
            dtype=np.int64,
        ).reshape(-1, 2),
        coastal=np.array([place.coastal for place in places], dtype=np.bool_),
    )
    governments = {
        DEFAULT_STATE: (("type", "monarchy"), ("heir_selection", "cognatic_primogeniture")),
        ADVANCED_STATE: (("type", "monarchy"), ("heir_selection", "cognatic_primogeniture")),
        DEFAULT_TRIBE: (("type", "tribe"), ("heir_selection", "tribal_oldest_male")),
        CALIBRATION.republic_include: CALIBRATION.republic_government,
    }
    vanilla = VanillaNatives(
        {},
        1000,
        {
            culture: Culture(
                faiths[0], (), 1000, DEFAULT_STATE, DEFAULT_TRIBE, DEFAULT_CITY, DEFAULT_TOWN
            )
            for culture in cultures
        },
        dict.fromkeys(faiths, ((), 1000)),
        frozenset(governments),
        frozenset(),
        (),
        governments=governments,
        levels={
            DEFAULT_STATE: 0,
            ADVANCED_STATE: 2,
            DEFAULT_TRIBE: next(
                (f.technology for f in root.foundings if f.tenure is Tenure.TRIBE), 0
            ),
            CALIBRATION.republic_include: 2,
        },
        state_levels=(0, 1, 2),
        overlord_level=2,
        empire=EmpireCalibration(3, "rank_duchy", 1000, ()),
        archetypes=replace(CALIBRATION, confederate_density=1),
        state_floor=StateFloor(
            root.geography.rules.minimum_peasants, root.geography.rules.minimum_share
        ),
        law_book=LAW_BOOK,
    )
    return ProjectionInputs(
        HistoryBootstrap(root, canonical_population(pops), int(populations.sum()), 0),
        history,
        graph,
        societies,
        keys,
        {key: f"area_{key}" for key in keys},
        {key: f"Seat{key}" for key in keys},
        vanilla,
        RANGES,
        KeySpace(set()),
        {f"original_{p.key}": p.key for p in places if p.sacred},
    )


def check(plan: FinalStartPlan, inputs: ProjectionInputs) -> None:
    validate_projection(
        plan, vanilla=inputs.vanilla, positions=inputs.positions, areas=inputs.areas
    )


def test_surviving_ownership_seats_and_population_have_one_source() -> None:
    history = divided_valley()
    inputs = inputs_for(history)
    plan = project_start(inputs)
    assert len(plan.countries) == 3
    assert len(plan.history_tags) == 3
    assert all(actor.living for actor in history.state.actors if actor.key in plan.history_tags)
    assert len(history.state.actors) > len(plan.history_tags)
    owners = {key: country.history_actor for country in plan.countries for key in country.members}
    assert owners == {h.district: h.actor for h in history.state.holdings}
    assert sum(plan.population.values()) == 13_000
    assert plan.history is history
    assert not any(country.rank for country in plan.countries)
    assert any(opinion.factor is Factor.GRIEVANCE for opinion in plan.historical_opinions)
    assert all(
        opinion.cause in {e.key for e in history.events} for opinion in plan.historical_opinions
    )
    records = parse("countries = { countries = {" + country_records(plan.countries) + "} }")
    for country in plan.countries:
        block = records.block("countries", "countries", country.tag)
        assert block is not None
        assert block.first("capital").value == country.capital  # pyright: ignore[reportOptionalMemberAccess]
    check(plan, inputs)


@pytest.mark.parametrize(
    ("authority", "level", "wanted"),
    [
        (Authority.RULER, 1, "monarchy"),
        (Authority.COUNCIL, 2, "republic"),
        (Authority.COUNCIL, 0, "monarchy"),
        (Authority.SACRED, 1, "theocracy"),
        (Authority.CUSTOMARY, 0, "monarchy"),
    ],
)
def test_authority_selects_a_usable_calibrated_government(
    authority: Authority, level: int, wanted: str
) -> None:
    original = valley()
    roots = tuple(
        replace(f, authority=authority, technology=level, society=Society(authority=authority))
        for f in original.foundings
    )
    history = quiet(create(original.geography, roots, seed=42, empire_permille=0))
    inputs = inputs_for(history)
    plan = project_start(inputs)
    assert all(dict(country.government)["type"] == wanted for country in plan.countries)
    assert all(country.level == level for country in plan.countries)
    if wanted == "theocracy":
        assert all(not country.include for country in plan.countries)
        # The vanilla precedents' laws come first; ``eu5_laws`` completes the rest.
        assert all(
            country.laws[:2] == CALIBRATION.theocracy_institutions.laws
            and dict(country.laws)["theocratic_leadership"] == "clerical_state"
            for country in plan.countries
        )


def test_vassal_lord_retains_the_proven_template_prerequisite() -> None:
    geography = Geography(
        (
            District("a", "r", Tenure.LAND, (Cohort("c", "r", 1000, 500),)),
            District("a2", "r", Tenure.LAND, (Cohort("c", "r", 120, 60),)),
            District("b", "r", Tenure.LAND, (Cohort("c", "r", 10_000, 5000),)),
            District("c", "r", Tenure.LAND, (Cohort("c", "r", 400, 340),)),
        ),
        (Route("a", "b"), Route("a", "a2"), Route("a2", "b"), Route("b", "c")),
    )
    history = create(
        geography,
        (
            Founding("client", Tenure.LAND, ("a", "a2"), "a", technology=1),
            Founding("lord", Tenure.LAND, ("b", "c"), "b", Authority.SACRED, 2),
        ),
        seed=42,
        empire_permille=0,
    )
    history = advance(history, (Proposal(Action.CONTACT, "client", "lord"),))
    # D25: the client submits after a recorded defeat by a lord of real scale.
    history = advance(history, (Proposal(Action.CONFLICT, "lord", "client", ("a2",)),))
    history = advance(history, (Proposal(Action.DEPENDENCY, "client", "lord"),))
    inputs = inputs_for(quiet(history))
    plan = project_start(inputs)
    assert plan.vassals == ((plan.history_tags["lord"], plan.history_tags["client"]),)
    lord = next(country for country in plan.countries if country.history_actor == "lord")
    assert lord.include == ADVANCED_STATE
    assert dict(lord.government)["type"] == "monarchy"
    assert inputs.areas["a"] in lord.areas
    assert inputs.areas["b"] in next(c for c in plan.countries if c.history_actor == "client").areas


def test_same_history_and_fresh_keyspace_produce_identical_plans() -> None:
    history = divided_valley()
    first = project_start(inputs_for(history))
    second = project_start(inputs_for(history))
    assert first.countries == second.countries
    assert first.historical_opinions == second.historical_opinions
    assert first.roads == second.roads
    assert first.stats == second.stats


def test_1037_and_a_different_bootstrap_cannot_be_projected() -> None:
    with pytest.raises(HistoryError, match="unfinished"):
        _ = project_start(inputs_for(valley()))
    inputs = inputs_for(divided_valley())
    with pytest.raises(HistoryError, match="different bootstrap"):
        _ = project_start(
            replace(
                inputs,
                bootstrap=replace(
                    inputs.bootstrap, history=replace(inputs.bootstrap.history, seed=77)
                ),
            )
        )


def test_profiles_are_interpolated_only_inside_observed_ungated_ranges() -> None:
    templates = {
        "low": "government = { "
        + " ".join(f"{axis} = {lo}" for axis, (lo, _) in RANGES.items())
        + " }",
        "high": "government = { "
        + " ".join(f"{axis} = {hi}" for axis, (_, hi) in RANGES.items())
        + " }",
    }
    definitions = [
        " ".join(f"{axis} = {{ {'age = discovery' if axis == EXCHANGE else ''} }}" for axis in AXES)
    ]
    ranges = position_ranges(templates, {"low", "high"}, definitions)
    assert EXCHANGE not in ranges
    assert MYSTICISM not in ranges
    values = dict(
        profile_positions(
            Society(
                centralization=1000,
                tradition=0,
                religious_authority=1000,
                military=Military.DEFENSIVE,
                exchange=Exchange.COASTAL,
            ),
            ranges,
        )
    )
    assert values[CENTRAL] == 60
    assert values[TRADITION] == -70
    assert values[SPIRITUAL] == -90
    assert values[POSTURE] == 50
    assert values[QUALITY] == -75
    assert all(lo <= values[axis] <= hi for axis, (lo, hi) in ranges.items())


@pytest.mark.parametrize("defect", ["definition", "repeated", "template", "noninteger", "bounds"])
def test_invalid_position_calibration_fails_explicitly(defect: str) -> None:
    definitions = " ".join(f"{axis} = {{}}" for axis in AXES)
    templates = {"used": f"government = {{ {CENTRAL} = 60 }}"}
    if defect == "definition":
        definitions = ""
    elif defect == "repeated":
        definitions += f" {CENTRAL} = {{}}"
    elif defect == "template":
        templates = {}
    elif defect == "noninteger":
        templates["used"] = f"government = {{ {CENTRAL} = nonsense }}"
    else:
        templates["used"] = f"government = {{ {CENTRAL} = 101 }}"
    with pytest.raises(HistoryError):
        _ = position_ranges(templates, {"used"}, [definitions])


def opinion(first: str, second: str, value: int, cause: str) -> HistoricalOpinion:
    return HistoricalOpinion(
        "",
        first,
        second,
        Factor.TRUST if value > 0 else Factor.GRIEVANCE,
        value,
        1,
        cause,
        1300,
        Action.CONFLICT,
    )


def test_named_memory_limits_keep_alliance_bundles_together() -> None:
    candidates = [
        opinion("A", "B", 20, "trust"),
        opinion("A", "B", -15, "loss"),
        opinion("A", "B", -40, "older_loss"),
        opinion("B", "A", -10, "suspicion"),
    ]
    candidates.extend(opinion(f"pair_{n}", "Z", 1, str(m)) for n in range(600) for m in range(6))
    selected = select_opinions(candidates, (("A", "B"),), KeySpace(set()))
    assert len(selected) <= 2000
    assert len({item.key for item in selected}) == len(selected)
    assert any(item.cause == "loss" for item in selected)
    assert not any(item.cause in {"older_loss", "suspicion"} for item in selected)
    counts: dict[tuple[str, str], int] = {}
    for item in selected:
        counts[item.first, item.second] = counts.get((item.first, item.second), 0) + 1
    assert max(counts.values()) <= 4
    assert sum(item.value for item in selected if (item.first, item.second) == ("A", "B")) >= 0
    assert select_opinions(tuple(reversed(candidates)), (("A", "B"),), KeySpace(set())) == selected


@pytest.mark.parametrize(
    "defect",
    ["ownership", "population", "axis", "opinion", "discovery", "rank", "extra_actor", "road"],
)
def test_final_plan_verifier_rejects_mismatches(defect: str) -> None:
    inputs = inputs_for(divided_valley())
    plan = project_start(inputs)
    country, *rest = plan.countries
    if defect == "ownership":
        plan = replace(plan, countries=(replace(country, members=(country.capital,)), *rest))
    elif defect == "population":
        plan = replace(plan, population={**plan.population, country.capital: 1})
    elif defect == "axis":
        plan = replace(
            plan,
            countries=(
                replace(
                    country,
                    government=tuple(
                        (k, "-100") if k == CENTRAL else (k, v) for k, v in country.government
                    ),
                ),
                *rest,
            ),
        )
    elif defect == "opinion":
        item, *others = plan.historical_opinions
        plan = replace(plan, historical_opinions=(replace(item, cause="invented"), *others))
    elif defect == "discovery":
        plan = replace(plan, countries=tuple(replace(c, areas=()) for c in plan.countries))
    elif defect == "rank":
        plan = replace(plan, countries=(replace(country, rank="rank_duchy"), *rest))
    elif defect == "extra_actor":
        plan = replace(plan, history_tags={**plan.history_tags, "extinct": "OLD"})
    else:
        plan = replace(plan, roads=((country.capital, "not_a_place"),))
    with pytest.raises(HistoryError):
        check(plan, inputs)


def realized_network(kind: TrajectoryKind, *, overlap: bool = False, chance: int = 1000) -> History:
    original = _trajectory_world(kind)
    sea = kind is TrajectoryKind.SEA_LEAGUE
    places, routes, roots = (
        list(original.geography.districts),
        list(original.geography.routes),
        list(original.foundings),
    )
    for key in ("0", "1", "2"):
        if sea:
            border = f"border_{key}"
            places.append(District(border, "plain", Tenure.LAND, (Cohort("c", "r", 100, 50),)))
            routes.extend((Route(key, border), Route(border, "threat")))
            roots = [
                replace(f, districts=(*f.districts, border)) if f.key == key else f for f in roots
            ]
        else:
            routes.append(Route(key, "threat"))
    places.append(District("threat", "plain", Tenure.LAND, (Cohort("other", "r", 20_000, 10_000),)))
    roots.append(
        Founding(
            "threat",
            Tenure.LAND,
            ("threat",),
            "threat",
            Authority.RULER,
            2,
            society=Society(
                authority=Authority.RULER, military=Military.OFFENSIVE, integration=800
            ),
        )
    )
    history = create(
        replace(
            original.geography,
            districts=tuple(places),
            routes=tuple(routes),
            hearths=(
                *original.geography.hearths,
                replace(original.geography.hearths[0], key="other_hearth"),
            )
            if overlap
            else original.geography.hearths,
        ),
        roots,
        seed=42,
        empire_permille=chance,
    )
    while history.state.year < 1267:
        history = advance(history, ())
    for key in ("0", "1", "2"):
        history = advance(history, (Proposal(Action.CONTACT, "threat", key),))
        history = advance(
            history,
            (
                Proposal(
                    Action.CONFLICT if sea else Action.PRESSURE,
                    "threat",
                    key,
                    (f"border_{key}" if sea else key,),
                ),
            ),
        )
    history = advance(
        history, (Proposal(Action.CONTACT, "0", "1"), Proposal(Action.CONTACT, "0", "2"))
    )
    if sea:
        history = advance(
            history, (Proposal(Action.EXCHANGE, "0", "1"), Proposal(Action.EXCHANGE, "0", "2"))
        )
    history = advance(
        history,
        (
            Proposal(Action.PACT, "0", "1", threat="threat"),
            Proposal(Action.PACT, "0", "2", threat="threat"),
        ),
    )
    return quiet(history)


@pytest.mark.parametrize("kind", [TrajectoryKind.SEA_LEAGUE, TrajectoryKind.HIGHLAND_CONFEDERATION])
def test_realized_network_uses_actual_pacts_and_discovered_partner_capitals(
    kind: TrajectoryKind,
) -> None:
    history = realized_network(kind)
    inputs = inputs_for(history)
    plan = project_start(inputs)
    (group,) = plan.historical_groups
    assert group.kind == kind
    assert len(group.members) == 3
    assert len(plan.alliances) == 2  # An actual star, not a newly invented third pact.
    assert all(o.first != o.second for o in plan.historical_opinions)
    assert any(o.factor is Factor.FEAR for o in plan.historical_opinions)
    for first, second in plan.alliances:
        assert (
            sum(o.value for o in plan.historical_opinions if (o.first, o.second) == (first, second))
            >= 0
        )
        assert (
            sum(o.value for o in plan.historical_opinions if (o.first, o.second) == (second, first))
            >= 0
        )
    if kind is TrajectoryKind.SEA_LEAGUE:
        assert not plan.confederations
        assert all(
            dict(c.government)["type"] == "republic"
            for c in plan.countries
            if c.tag in group.members
        )
        assert len(plan.exchanges) == 2
        assert not plan.roads  # The star's water passages cannot become land roads.
        # An exchange is an opinion and a road, never a market or a town: 1.2.0 made every
        # partner a market centre of its own, so each country of the New World traded alone.
        assert plan.markets == ("threat",)
        assert {rank for rank, _ in plan.ranks.values()} == {"city"}
    else:
        assert len(plan.confederations) == 1
        assert all(c.landed and c.level is None for c in plan.countries if c.tag in group.members)
    check(plan, inputs)
    without_display_biases = replace(plan, historical_opinions=(), opinions=())
    tags = {c.tag for c in plan.countries if c.kind == "state" or c.landed}
    ai = _ai_diplomacy(without_display_biases, tags)
    threat = plan.history_tags["threat"]
    assert all(threat in ai.threatened_by[plan.history_tags[key]] for key in ("0", "1", "2"))


def test_only_a_realized_expansion_gets_the_empire_level_rank_and_royal_roads() -> None:
    original = _trajectory_world(TrajectoryKind.GREAT_EMPIRE)
    anchor = original.state.trajectories[0].anchor
    context = Context(original, lambda: None)
    owner = context.index.owner[anchor]
    homeland = context.index.members[owner]
    geography = replace(
        original.geography,
        districts=tuple(
            replace(p, cohorts=(Cohort("c", "r", 20_000, 10_000),)) if p.key in homeland else p
            for p in original.geography.districts
        ),
    )
    roots = tuple(
        replace(f, society=Society(integration=900)) if f.key == owner else f
        for f in original.foundings
    )
    history = create(geography, roots, seed=42, empire_permille=1000)
    before = project_start(inputs_for(quiet(history)))
    assert not any(c.great or c.rank for c in before.countries)
    for _ in range(2):
        context = Context(history, lambda: None)
        target = min(context.near[owner])
        members = tuple(context.index.members[target])
        history = advance(history, (Proposal(Action.CONTACT, owner, target),))
        history = advance(history, (Proposal(Action.CONFLICT, owner, target, members),))
        for _ in range(5):
            history = advance(history, ())
    inputs = inputs_for(quiet(history))
    plan = project_start(inputs)
    (country,) = plan.countries
    assert country.great
    assert country.rank == "rank_duchy"
    assert country.level == 3
    assert len(country.members) == 12
    assert plan.roads
    assert set(plan.history_tags) == {owner}
    check(plan, inputs)


def test_sacred_host_and_visitors_have_explicit_distinct_roles() -> None:
    history = _trajectory_world(TrajectoryKind.SACRED_CENTRE)
    history = advance(
        history, (Proposal(Action.CONTACT, "1", "0"), Proposal(Action.CONTACT, "2", "0"))
    )
    history = advance(
        history,
        (Proposal(Action.ACCESS, "1", "0", ("0",)), Proposal(Action.ACCESS, "2", "0", ("0",))),
    )
    plan = project_start(inputs_for(quiet(history)))
    (group,) = plan.historical_groups
    assert group.kind == TrajectoryKind.SACRED_CENTRE
    assert len(group.members) == 3
    assert all(group.key in c.memberships for c in plan.countries)
    host = next(c for c in plan.countries if c.tag == group.members[0])
    assert "sacred_centre" in host.archetypes
    assert all("sacred_centre" not in c.archetypes for c in plan.countries if c.tag != host.tag)
    assert dict(host.government)["type"] == "theocracy"
    assert not plan.rivals  # A religious grouping does not invent personal antagonism.


def test_religion_or_trajectory_alone_never_assigns_diplomacy() -> None:
    plan = project_start(inputs_for(quiet(_trajectory_world(TrajectoryKind.SEA_LEAGUE))))
    assert not plan.historical_groups
    assert not plan.alliances
    assert not plan.rivals
    assert not plan.vassals
    assert not plan.protections


def test_unorganized_communities_keep_population_without_becoming_country_tags() -> None:
    original = valley()
    free = District("community", "valley", Tenure.COMMUNITY, (Cohort("c", "r", 1000, 0),))
    geography = replace(
        original.geography,
        districts=(*original.geography.districts, free),
        routes=(*original.geography.routes, Route("d1", "community")),
    )
    history = quiet(
        create(
            geography,
            (
                *original.foundings,
                Founding(
                    "unorganized", Tenure.COMMUNITY, ("community",), "community", technology=0
                ),
            ),
            seed=42,
        )
    )
    plan = project_start(inputs_for(history))
    assert "unorganized" not in plan.history_tags
    assert plan.population["community"] == 1000
    assert not any("community" in c.members for c in plan.countries)


def test_confederation_eligibility_retains_the_landed_farming_floor() -> None:
    original = _trajectory_world(TrajectoryKind.HIGHLAND_CONFEDERATION)
    geography = replace(
        original.geography,
        districts=tuple(
            replace(p, cohorts=(Cohort("c", "r", 1000, 0),)) for p in original.geography.districts
        ),
    )
    history = create(geography, original.foundings, seed=42, empire_permille=1000)
    assert not history.state.trajectories


def test_two_hearth_ambitions_do_not_put_a_tribe_in_two_engine_organizations() -> None:
    plan = project_start(
        inputs_for(realized_network(TrajectoryKind.HIGHLAND_CONFEDERATION, overlap=True))
    )
    (group,) = plan.historical_groups
    assert len(group.hearths) == 2
    assert len(plan.confederations) == 1
    assert len({tag for organization in plan.confederations for tag in organization}) == 3


def test_pop_type_defence_pacts_remain_in_history_without_assigning_land() -> None:
    inputs = inputs_for(realized_network(TrajectoryKind.HIGHLAND_CONFEDERATION, chance=0))
    plan = project_start(inputs)
    assert not plan.alliances
    assert not plan.confederations
    assert not any(c.landed for c in plan.countries)
    assert sum(b.kind is Action.PACT for b in inputs.history.state.bonds) == 2


def test_sacred_group_retains_community_participants_without_live_tags() -> None:
    original = _trajectory_world(TrajectoryKind.SACRED_CENTRE)
    geography = replace(
        original.geography,
        districts=(
            *original.geography.districts,
            District("pilgrim", "plain", Tenure.COMMUNITY, (Cohort("c", "r", 1000, 0),)),
        ),
        routes=(*original.geography.routes, Route("0", "pilgrim")),
    )
    history = create(
        geography,
        (
            *original.foundings,
            Founding("pilgrim", Tenure.COMMUNITY, ("pilgrim",), "pilgrim", technology=0),
        ),
        seed=42,
        empire_permille=1000,
    )
    history = advance(
        history, (Proposal(Action.CONTACT, "2", "0"), Proposal(Action.CONTACT, "pilgrim", "0"))
    )
    history = advance(
        history,
        (
            Proposal(Action.ACCESS, "2", "0", ("0",)),
            Proposal(Action.ACCESS, "pilgrim", "0", ("0",)),
        ),
    )
    plan = project_start(inputs_for(quiet(history)))
    (group,) = plan.historical_groups
    assert "pilgrim" in group.actors
    assert "pilgrim" not in plan.history_tags
    assert len(group.members) == 2


def test_real_fractured_lineage_and_sacred_centre_can_share_members() -> None:
    original = valley()
    geography = replace(
        original.geography,
        rules=replace(original.geography.rules, empire_locations=6),
        hearths=(Hearth("hearth", "d0", tuple(p.key for p in original.geography.districts)),),
        districts=tuple(
            replace(p, cohorts=(Cohort("valley_people", "river_faith", 3000, 1500),), sacred=True)
            if p.key == "d0"
            else replace(p, sacred=False)
            for p in original.geography.districts
        ),
    )
    roots = tuple(
        replace(
            f,
            authority=Authority.SACRED,
            society=Society(authority=Authority.SACRED, religious_authority=900),
        )
        if f.key == "downstream"
        else f
        for f in original.foundings
    )
    history = create(geography, roots, seed=3, empire_permille=1000)
    assert history.state.trajectories[0].kind is TrajectoryKind.SACRED_CENTRE
    while history.state.year < 1232:
        context = Context(history, lambda: None)
        proposals = tuple(
            replace(
                p,
                partitions=tuple(
                    replace(part, authority=Authority.SACRED) if part.seat == "d0" else part
                    for part in p.partitions
                ),
            )
            if p.kind is Action.SEPARATION
            else p
            for p in valley_policy(context)
        )
        history = advance(history, proposals)
    seats = {a.seat: a.key for a in history.state.actors if a.living}
    history = advance(
        history,
        (
            Proposal(Action.ACCESS, seats["u0"], seats["d0"], ("d0",)),
            Proposal(Action.ACCESS, seats["m0"], seats["d0"], ("d0",)),
        ),
    )
    plan = project_start(inputs_for(quiet(history)))
    assert {group.kind for group in plan.historical_groups} == {"fractured_realm", "sacred_centre"}
    host = next(country for country in plan.countries if country.capital == "d0")
    assert set(host.archetypes) == {"fractured_realm", "sacred_centre"}
    assert len(host.memberships) == 2
    assert not plan.rivals  # Neither the split nor a shrine invents present hostility.
