"""Independent agreement checks between historical facts and the final EU5 plan."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from rnw.eu5_history import identity_cohorts
from rnw.eu5_history_values import profile_positions
from rnw.history_checks import Index, require, unique
from rnw.history_context import Context
from rnw.history_diplomacy import PAIR_LIMIT, RIVAL_MEMORY, WORLD_LIMIT
from rnw.history_model import END, Action, Authority, Factor, Tenure, TrajectoryKind
from rnw.history_trajectories import GROUP_MIN, realizations
from rnw.opinions import ANALOGUES, POSITIVE, opinion_value

if TYPE_CHECKING:
    from collections.abc import Mapping

    from rnw.eu5_natives import VanillaNatives
    from rnw.eu5_start import Country, FinalStartPlan
    from rnw.history_model import History


def _checkpoint() -> None:
    """The caller's history has already passed full causal replay."""


def _country(
    country: Country,
    index: Index,
    vanilla: VanillaNatives,
    positions: Mapping[str, tuple[int, int]],
) -> None:
    actor = index.actors[country.history_actor]
    require(
        set(country.members) == index.members[actor.key]
        and country.capital == actor.seat
        and (country.kind == "state") == (actor.tenure is Tenure.LAND),
        "A projected country differs from its historical holdings/seat/tenure",
    )
    government = dict(country.government)
    require(len(government) == len(country.government), "Repeated projected government field")
    require(
        all(
            government.get(axis) == str(value)
            for axis, value in profile_positions(actor.society, positions)
        ),
        "A projected societal value differs from its historical profile",
    )
    if actor.tenure is Tenure.LAND:
        allowed = set(vanilla.state_levels)
        if country.great and vanilla.empire:
            allowed.add(vanilla.empire.level)
        require(country.level in allowed, "A historical state has an unsupported technology level")
        require(
            country.great or country.level == actor.technology,
            "Ordinary technology lost its lineage",
        )
        if country.include:
            template = vanilla.levels.get(country.include, 0)
            require(
                country.level is not None and template <= country.level <= template + 1,
                "A historical state's template does not fit its technology",
            )
        if actor.authority is Authority.RULER:
            require(government.get("type") == "monarchy", "Ruler authority has no usable monarchy")
    else:
        require(
            country.level is None
            and government.get("type") == "tribe"
            and vanilla.levels.get(country.include, 0) == actor.technology,
            "A historical tribe changed its calibrated representation",
        )
    calibration = vanilla.archetypes
    require(calibration is not None, "Missing history institutions")
    if calibration is not None and government.get("type") == "theocracy":
        require(
            not country.include
            and country.laws == calibration.theocracy_institutions.laws
            and country.parliament == calibration.theocracy_institutions.parliament
            and country.religion not in calibration.theocracy_institutions.excluded_religions
            and all(government.get(k) == v for k, v in calibration.theocracy),
            "Historical theocracy has incompatible institutions",
        )
    if country.landed:
        require(
            actor.tenure is Tenure.TRIBE
            and calibration is not None
            and country.currency == calibration.cohesion,
            "A landed historical tribe is not a calibrated confederate",
        )


def _opinions(plan: FinalStartPlan, history: History, index: Index) -> None:
    opinions = plan.historical_opinions
    unique((opinion.key for opinion in opinions), "historical opinion key")
    require(len(opinions) <= WORLD_LIMIT, "Too many historical opinions")
    counts = Counter((opinion.first, opinion.second) for opinion in opinions)
    require(
        all(count <= PAIR_LIMIT for count in counts.values()),
        "Too many opinions for a directed pair",
    )
    countries = {country.tag: country for country in plan.countries}
    events = {event.key: event for event in history.events}
    amounts: Counter[tuple[str, str, Factor, str]] = Counter()
    for memory in history.state.memories:
        amounts[memory.first, memory.second, memory.factor, memory.cause] += memory.at(
            history.state.year
        )
    for opinion in opinions:
        require(
            opinion.first in countries
            and opinion.second in countries
            and opinion.first != opinion.second,
            "Historical opinion has an invalid scope",
        )
        first, second = countries[opinion.first], countries[opinion.second]
        require(
            (first.kind == "state" or first.landed) and (second.kind == "state" or second.landed),
            "A startup opinion has no explicitly assigned capital",
        )
        require(opinion.cause in events, "Historical opinion has an invented cause")
        event = events[opinion.cause]
        require(
            event.year == opinion.year
            and event.kind is opinion.action
            and (not opinion.place or opinion.place in index.places),
            "Historical opinion misstates its cause",
        )
        places = {t.district for t in event.effects.transfers} | {
            s.district for s in event.effects.settlements
        }
        require(
            opinion.place in places if places else not opinion.place,
            "Historical opinion names a place outside its cause",
        )
        amount = amounts[first.history_actor, second.history_actor, opinion.factor, opinion.cause]
        analogue = ANALOGUES[opinion.factor]
        require(
            0 < abs(opinion.value) <= abs(analogue.value)
            and opinion.value == opinion_value(opinion.factor, amount)
            and opinion.yearly_decay == analogue.yearly_decay
            and (opinion.value > 0) == (opinion.factor in POSITIVE),
            "Historical opinion differs from its vanilla analogue's scale",
        )
        require(amount > 0, "Historical opinion has no surviving directed memory")
    require(
        plan.opinions == tuple((o.first, o.second, o.key) for o in opinions),
        "The plan has a second or inconsistent set of opinions",
    )
    for first, second in plan.alliances:
        for a, b in ((first, second), (second, first)):
            require(
                sum(o.value for o in opinions if (o.first, o.second) == (a, b)) >= 0,
                "Historical opinions break the alliance relations floor",
            )


def _relations(plan: FinalStartPlan, context: Context, vanilla: VanillaNatives) -> None:
    history = context.history
    countries = {country.tag: country for country in plan.countries}
    by_actor = {country.history_actor: country for country in plan.countries}
    subjects = {subject for _, subject in plan.vassals}
    expected = {
        (plan.history_tags[b.second], plan.history_tags[b.first])
        for b in history.state.bonds
        if b.kind is Action.DEPENDENCY
    }
    require(
        set(plan.vassals) == expected and len(subjects) == len(plan.vassals),
        "Projected vassalage differs from history",
    )
    for lord, _ in plan.vassals:
        country = countries[lord]
        require(
            country.level is not None
            and country.level >= vanilla.overlord_level
            and vanilla.levels.get(country.include, -1) >= vanilla.overlord_level,
            "Historical vassal lord lacks the installed prerequisite",
        )
    require(
        len({tag for group in plan.confederations for tag in group})
        == sum(len(group) for group in plan.confederations),
        "A country belongs to two tribal confederations",
    )
    require(
        all(
            len(group) >= GROUP_MIN and set(group) <= countries.keys()
            for group in plan.confederations
        ),
        "An invalid confederation entered the projection",
    )
    for kind, pairs in (
        (Action.PACT, plan.alliances),
        (Action.PROTECTION, plan.protections),
        (Action.EXCHANGE, plan.exchanges),
    ):
        require(len(set(pairs)) == len(pairs), "Repeated historical relation")
        for first, second in pairs:
            require(
                first in countries and second in countries and first != second,
                "Historical relation has an extinct or absent scope",
            )
            a, b = countries[first], countries[second]
            require(
                (a.kind == "state" or a.landed) and (b.kind == "state" or b.landed),
                "A historical treaty names a pop country",
            )
            require(
                any(
                    bond.kind is kind
                    and (
                        {bond.first, bond.second} == {a.history_actor, b.history_actor}
                        if kind in {Action.PACT, Action.EXCHANGE}
                        else (bond.second, bond.first) == (a.history_actor, b.history_actor)
                    )
                    for bond in history.state.bonds
                ),
                "A projected treaty has no historical bargain",
            )
    for first, second in plan.alliances:
        require(
            not {first, second} & subjects
            and (first, second) not in plan.rivals
            and (second, first) not in plan.rivals,
            "An alliance violates diplomacy prerequisites",
        )
    require(len(set(plan.rivals)) == len(plan.rivals), "Repeated historical rivalry")
    for first, second in plan.rivals:
        require(
            first in countries
            and second in countries
            and first != second
            and not {first, second} & subjects,
            "Invalid historical rival scope",
        )
        a, b = countries[first].history_actor, countries[second].history_actor
        require(
            (a, b) in context.known
            and not context.has(Action.PACT, a, b)
            and max(context.score(a, b, Factor.GRIEVANCE), context.score(a, b, Factor.COMPETITION))
            >= RIVAL_MEMORY,
            "A rivalry has no surviving historical hostility",
        )
    for giver, receiver in plan.protections:
        require(
            not {giver, receiver} & subjects
            and (not countries[receiver].great or countries[giver].great)
            and (giver, receiver) not in plan.rivals
            and (receiver, giver) not in plan.rivals,
            "Historical protection violates the guarantee prerequisites",
        )
    for country in plan.countries:
        require(
            by_actor[country.history_actor].tag == plan.history_tags[country.history_actor],
            "History tag mapping differs from country records",
        )


def _geography(plan: FinalStartPlan, history: History, areas: Mapping[str, str]) -> None:
    owner = {
        key: country
        for country in plan.countries
        for key in country.members
        if country.kind == "state" or country.landed
    }
    require(
        set(plan.ranks) <= owner.keys() and set(plan.markets) <= plan.ranks.keys(),
        "A historical settlement/market is not on landed inhabited territory",
    )
    require(all(plan.population[key] > 0 for key in plan.ranks), "Historical centre is uninhabited")
    contacts = {
        tuple(sorted((route.first, route.second)))
        for route in history.geography.routes
        if not route.sea_steps
    }
    require(len(set(plan.roads)) == len(plan.roads), "Repeated historical road")
    lords = {subject: lord for lord, subject in plan.vassals}
    exchanges = {frozenset(pair) for pair in plan.exchanges}
    for first, second in plan.roads:
        require(
            (first, second) in contacts and first in owner and second in owner,
            "Historical road is not a landed physical contact",
        )
        a, b = owner[first], owner[second]
        head_a, head_b = lords.get(a.tag, a.tag), lords.get(b.tag, b.tag)
        require(
            a.tag == b.tag or frozenset((a.tag, b.tag)) in exchanges or head_a == head_b,
            "Historical road has no territorial or exchange permission",
        )
    countries = {country.tag: country for country in plan.countries}
    pairs = [*plan.alliances, *plan.vassals, *plan.protections, *plan.exchanges]
    directed = [(a, b) for pair in pairs for a, b in (pair, (pair[1], pair[0]))]
    directed.extend(plan.rivals)
    directed.extend((o.first, o.second) for o in plan.historical_opinions)
    directed.extend((a, b) for group in plan.confederations for a in group for b in group if a != b)
    for first, second in directed:
        require(
            areas[countries[second].capital] in countries[first].areas,
            "A historical partner's capital area is undiscovered",
        )


def _groups(plan: FinalStartPlan, context: Context) -> None:
    found = realizations(context)
    expected = {
        (
            item.kind,
            tuple(plan.history_tags[key] for key in item.members if key in plan.history_tags),
        )
        for item in found
    }
    require(
        {(group.kind, group.members) for group in plan.historical_groups} == expected,
        "Projected extraordinary groups differ from actual structures",
    )
    unique((group.key for group in plan.historical_groups), "historical group")
    for group in plan.historical_groups:
        sources = [
            item
            for item in found
            if (
                item.kind,
                tuple(plan.history_tags[key] for key in item.members if key in plan.history_tags),
            )
            == (group.kind, group.members)
        ]
        require(
            set(group.actors) == {actor for item in sources for actor in item.members}
            and set(group.causes) == {cause for item in sources for cause in item.causes}
            and set(group.hearths) == {item.hearth for item in sources if item.hearth},
            "A historical group lost its original participants or causes",
        )
    great = {tag for kind, tags in expected if kind == TrajectoryKind.GREAT_EMPIRE for tag in tags}
    confederate_groups = [
        set(tags) for kind, tags in expected if kind == TrajectoryKind.HIGHLAND_CONFEDERATION
    ]
    landed_tribes = {tag for group in confederate_groups for tag in group}
    require(
        {c.tag for c in plan.countries if c.great} == great
        and {c.tag for c in plan.countries if c.landed} == landed_tribes,
        "An extraordinary country was assigned before its historical outcome",
    )
    organizations = [set(group) for group in plan.confederations]
    require(
        {tag for group in organizations for tag in group} == landed_tribes,
        "Confederation output differs from historical membership",
    )
    require(
        all(
            any(group <= organization for organization in organizations)
            for group in confederate_groups
        ),
        "A historical confederation was split in the game projection",
    )
    for organization in organizations:
        seen = {min(organization)}
        while True:
            joined = {tag for group in confederate_groups if group & seen for tag in group}
            if joined <= seen:
                break
            seen |= joined
        require(seen == organization, "Unrelated confederations were combined")
    for country in plan.countries:
        memberships = tuple(
            group.key for group in plan.historical_groups if country.tag in group.members
        )
        roles = tuple(
            sorted(
                {
                    group.kind
                    for group in plan.historical_groups
                    if country.tag in group.members
                    and (
                        group.kind != TrajectoryKind.SACRED_CENTRE
                        or group.members[0] == country.tag
                    )
                }
            )
        )
        require(
            country.memberships == memberships and country.archetypes == roles,
            "A country lost or invented an overlapping historical membership",
        )


def validate_projection(
    plan: FinalStartPlan,
    *,
    vanilla: VanillaNatives,
    positions: Mapping[str, tuple[int, int]],
    areas: Mapping[str, str],
) -> None:
    """Reject a changed plan instead of repairing it or trusting its own report."""
    history = plan.history
    require(history is not None, "The final plan has no history")
    if history is None:
        return
    require(history.state.year == END, "The final plan has an unfinished history")
    context = Context(history, _checkpoint)
    index = context.index
    live = {a.key for a in history.state.actors if a.living and a.tenure is not Tenure.COMMUNITY}
    unique((c.tag for c in plan.countries), "historical country tag")
    require(
        {c.history_actor for c in plan.countries} == live
        and set(plan.history_tags) == live
        and len(plan.countries) == len(live),
        "Extinct predecessors or communities entered the live country scopes",
    )
    require(
        {key: identity_cohorts(rows) for key, rows in plan.pops.items()}
        == {place.district: place.cohorts for place in history.state.settlements},
        "Final population differs from history",
    )
    require(
        plan.population
        == {
            p.key: sum(pop.amount for pop in plan.pops.get(p.key, ()))
            for p in history.geography.districts
        },
        "Final population totals differ from typed cohorts",
    )
    require(
        plan.complexity == {p.key: p.complexity for p in history.geography.districts},
        "Final complexity differs from physical bootstrap",
    )
    for country in plan.countries:
        _country(country, index, vanilla, positions)
    for group in plan.historical_groups:
        require(
            set(group.members) <= {c.tag for c in plan.countries}
            and set(group.causes) <= {e.key for e in history.events},
            "A historical group names absent members or invented causes",
        )
    require(
        all(bool(c.rank) == c.great for c in plan.countries),
        "Country rank is not reserved for realized empires",
    )
    _groups(plan, context)
    _opinions(plan, history, index)
    _relations(plan, context, vanilla)
    _geography(plan, history, areas)
