"""One final EU5 start plan from the surviving historical facts.

The normal exporter uses this H4 adapter after simulation. Static selectors never
add a second set of relations.
"""

# NumPy stubs type scalar/list conversion as Any.
# pyright: reportAny=false

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, final

import numpy as np

from rnw.eu5_archetypes import government_fields
from rnw.eu5_empires import empire_roads, extraordinary_report, road_targets
from rnw.eu5_history_values import profile_positions
from rnw.eu5_laws import complete, positions
from rnw.eu5_natives import (
    DEFAULT_CITY,
    DEFAULT_TOWN,
    PlaceNamer,
    map_colors,
    new_tags,
    state_economy,
)
from rnw.eu5_natives import (
    _include as country_template,  # pyright: ignore[reportPrivateUsage]
)
from rnw.eu5_start import Country, FinalStartPlan, HistoricalGroup
from rnw.history_checks import require, unique
from rnw.history_context import Context
from rnw.history_diplomacy import project_diplomacy
from rnw.history_engine import digest, validate_history
from rnw.history_model import END, START, Action, Authority, HistoryError, Tenure, TrajectoryKind
from rnw.history_plan_checks import validate_projection
from rnw.history_population import project_population
from rnw.history_routes import routed_graph
from rnw.history_trajectories import realizations, report
from rnw.societies import (
    CITY,
    STATE,
    STEP_COST,
    TRIBE,
    Polity,
    settlement_centres,
    trunk_roads,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from rnw.eu5_history import HistoryBootstrap
    from rnw.eu5_natives import VanillaNatives
    from rnw.history_diplomacy import DiplomacyProjection
    from rnw.history_model import Actor, History
    from rnw.loc_keys import KeySpace
    from rnw.societies import LandGraph, Societies
    from rnw.wording import Name


def _checkpoint() -> None:
    """Optional generator cancellation callback."""


@dataclass(frozen=True, slots=True, eq=False)
class ProjectionInputs:
    bootstrap: HistoryBootstrap
    history: History
    graph: LandGraph
    societies: Societies
    keys: tuple[str, ...]
    areas: Mapping[str, str]
    names: Mapping[str, Name]
    vanilla: VanillaNatives
    positions: Mapping[str, tuple[int, int]]
    loc_keys: KeySpace
    holy_sites: Mapping[str, str]
    reach_steps: int = 16
    coastal_areas: Mapping[str, tuple[str, ...]] | None = None


@dataclass(frozen=True, slots=True)
class _Government:
    include: str
    level: int | None
    fields: tuple[tuple[str, str], ...]
    laws: tuple[tuple[str, str], ...]
    parliament: str
    positions: tuple[tuple[str, int], ...] = ()


@final
class _Projection:
    def __init__(self, inputs: ProjectionInputs, checkpoint: Callable[[], None]) -> None:
        self.inputs = inputs
        self.checkpoint = checkpoint
        require(inputs.history.state.year == END, "Cannot project an unfinished history")
        validate_history(inputs.history, checkpoint=checkpoint)
        self.context = Context(inputs.history, checkpoint)
        unique(inputs.keys, "projection location")
        self.nodes = {key: number for number, key in enumerate(inputs.keys)}
        require(
            set(inputs.keys) == set(self.context.index.places)
            and len(inputs.graph.capacity) == len(inputs.keys)
            and set(inputs.areas) == set(inputs.keys)
            and set(inputs.keys) <= inputs.names.keys()
            and set(inputs.holy_sites.values()) <= set(inputs.keys),
            "Projection geography differs from history",
        )
        routed = routed_graph(inputs.graph, inputs.keys, inputs.history.geography.routes)
        require(
            {tuple(sorted((int(a), int(b)))) for a, b in inputs.graph.links}
            == {tuple(sorted((int(a), int(b)))) for a, b in routed.links},
            "Projection passages differ from history",
        )
        self.pops = project_population(inputs.bootstrap, inputs.history, checkpoint=checkpoint)
        self.actors = tuple(
            actor
            for actor in inputs.history.state.actors
            if actor.living and actor.tenure is not Tenure.COMMUNITY
        )
        self.actor_number = {actor.key: number for number, actor in enumerate(self.actors)}
        tags = new_tags(
            len(self.actors), inputs.vanilla.reserved_tags, inputs.history.seed, inputs.loc_keys
        )
        self.tags = dict(zip((actor.key for actor in self.actors), tags, strict=True))
        self.groups = self._groups()
        self.great = {
            key
            for group in self.groups
            if group.kind == TrajectoryKind.GREAT_EMPIRE
            for key in group.members
        }
        self.confederates = {
            key
            for group in self.groups
            if group.kind == TrajectoryKind.HIGHLAND_CONFEDERATION
            for key in group.members
        }

    def _groups(self) -> tuple[HistoricalGroup, ...]:
        combined: dict[tuple[str, tuple[str, ...]], set[str]] = defaultdict(set)
        hearths: dict[tuple[str, tuple[str, ...]], set[str]] = defaultdict(set)
        actors: dict[tuple[str, tuple[str, ...]], set[str]] = defaultdict(set)
        for found in realizations(self.context):
            members = tuple(self.tags[key] for key in found.members if key in self.tags)
            require(bool(members), "A realized structure has no country projection")
            combined[found.kind, members].update(found.causes)
            actors[found.kind, members].update(found.members)
            if found.hearth:
                hearths[found.kind, members].add(found.hearth)
        return tuple(
            HistoricalGroup(
                f"history_group_{number}",
                kind,
                members,
                tuple(sorted(causes)),
                tuple(sorted(hearths[kind, members])),
                tuple(sorted(actors[kind, members])),
            )
            for number, ((kind, members), causes) in enumerate(sorted(combined.items()), start=1)
        )

    def identity(self, place: str) -> tuple[str, str]:
        cultures: Counter[str] = Counter()
        faiths: Counter[str] = Counter()
        for pop in self.pops[place]:
            cultures[pop.culture] += pop.amount
            faiths[pop.religion] += pop.amount
        return (
            min(cultures, key=lambda key: (-cultures[key], key)),
            min(faiths, key=lambda key: (-faiths[key], key)),
        )

    def government(self, actor: Actor, culture: str, religion: str) -> _Government:
        vanilla = self.inputs.vanilla
        calibration = vanilla.archetypes
        if calibration is None:
            message = "Missing history government calibration"
            raise HistoryError(message)
        tag = self.tags[actor.key]
        level = actor.technology if actor.tenure is Tenure.LAND else None
        if tag in self.great:
            require(vanilla.empire is not None, "Missing realized empire calibration")
            if vanilla.empire is not None:
                level = vanilla.empire.level
        lord = any(
            bond.kind is Action.DEPENDENCY and bond.second == actor.key
            for bond in self.context.state.bonds
        )
        coast = any(
            self.context.index.places[key].coastal for key in self.context.index.members[actor.key]
        )
        include = country_template(
            vanilla, culture, level=level, coastal=coast, empire=tag in self.great or lord
        )
        require(
            include in vanilla.templates and include in vanilla.governments,
            f"Missing usable history template {include}",
        )
        governments = vanilla.history_governments or vanilla.governments
        fields = governments[include]
        laws: tuple[tuple[str, str], ...] = ()
        parliament = ""
        if actor.tenure is Tenure.LAND:
            institutions = calibration.theocracy_institutions
            if (
                actor.authority is Authority.SACRED
                and not lord
                and religion not in institutions.excluded_religions
            ):
                include, fields = "", calibration.theocracy
                laws, parliament = institutions.laws, institutions.parliament
            elif (
                actor.authority is Authority.COUNCIL
                and level is not None
                and level >= calibration.republic_level
            ):
                include, fields = calibration.republic_include, calibration.republic_government
                require(include in vanilla.templates, "Missing history republic template")
            elif dict(fields).get("type") != "monarchy":
                # Institutional choice precedes donor style. A donor's republic is
                # not an advantage or an instruction to change a ruler's authority.
                include = country_template(vanilla, "", level=level, coastal=coast, empire=lord)
                require(include in vanilla.governments, "Missing history monarchy template")
                fields = governments[include]
            if lord:
                require(
                    level is not None
                    and level >= vanilla.overlord_level
                    and vanilla.levels.get(include, -1) >= vanilla.overlord_level,
                    "Historical lord lacks the installed technology/template prerequisite",
                )
        else:
            require(dict(fields).get("type") == "tribe", "A pop tribe has a nontribal government")
            require(
                vanilla.levels.get(include, 0) == actor.technology,
                "Historical tribal technology differs from its installed template",
            )
        written = government_fields(
            fields, (), profile_positions(actor.society, self.inputs.positions)
        )
        if actor.tenure is Tenure.LAND and level is not None:
            # Every law the state sees at the start holds a policy (``eu5_laws``).
            require(vanilla.law_book is not None, "Missing installed law calibration")
            if vanilla.law_book is not None:
                laws = complete(
                    vanilla.law_book,
                    include=include,
                    fields=written,
                    laws=laws,
                    level=level,
                    religion=religion,
                    culture=culture,
                )
        standing = (
            positions(vanilla.law_book, include=include, fields=written)
            if vanilla.law_book is not None
            else {}
        )
        return _Government(include, level, written, laws, parliament, tuple(standing.items()))

    def countries(self) -> tuple[Country, ...]:
        vanilla = self.inputs.vanilla
        near = [
            {
                self.actor_number[key]
                for key in self.context.land_near.get(actor.key, ())
                if key in self.actor_number
            }
            for actor in self.actors
        ]
        colors = map_colors(near, self.inputs.history.seed, vanilla.colors)
        namer = PlaceNamer(vanilla, self.inputs.history.seed)
        namer.reserve([name for name in self.inputs.names.values() if isinstance(name, str)])
        countries: list[Country] = []
        for number, actor in enumerate(self.actors):
            self.checkpoint()
            tag = self.tags[actor.key]
            culture, religion = self.identity(actor.seat)
            require(
                culture in vanilla.cultures and religion in vanilla.religions,
                "A historical identity is absent from the installed calibration",
            )
            members = tuple(sorted(self.context.index.members[actor.key]))
            is_state = actor.tenure is Tenure.LAND
            name = self.inputs.names[actor.seat] if is_state else namer.name(culture)
            if not isinstance(name, str):
                message = "A historical country seat has no proper name"
                raise HistoryError(message)
            known = {self.inputs.areas[place] for place in members}
            for place in members:
                known.update((self.inputs.coastal_areas or {}).get(place, ()))
            memberships = tuple(group.key for group in self.groups if tag in group.members)
            roles = tuple(
                sorted(
                    {
                        group.kind
                        for group in self.groups
                        if tag in group.members
                        and (group.kind != TrajectoryKind.SACRED_CENTRE or group.members[0] == tag)
                    }
                )
            )
            fields = self.government(actor, culture, religion)
            # Explicit fields keep this boundary strictly typed; no script is parsed back.
            countries.append(
                Country(
                    tag,
                    name,
                    STATE if is_state else TRIBE,
                    members,
                    actor.seat,
                    culture,
                    religion,
                    fields.include,
                    tuple(sorted(known)),
                    colors[number][0],
                    colors[number][1],
                    government=fields.fields,
                    level=fields.level,
                    great=tag in self.great,
                    rank=vanilla.empire.rank if tag in self.great and vanilla.empire else "",
                    landed=tag in self.confederates,
                    currency=vanilla.archetypes.cohesion
                    if tag in self.confederates and vanilla.archetypes
                    else (),
                    laws=fields.laws,
                    parliament=fields.parliament,
                    history_actor=actor.key,
                    memberships=memberships,
                    archetypes=roles,
                    positions=fields.positions,
                )
            )
        return tuple(countries)

    def societies(self, countries: Sequence[Country]) -> Societies:
        old = self.inputs.societies
        require(
            len(old.population) == len(self.inputs.keys)
            and int(old.population.sum()) == self.inputs.bootstrap.calibrated_population,
            "Projection's calibrated population differs from the bootstrap",
        )
        settled = replace(
            old,
            population=np.array(
                [sum(pop.amount for pop in self.pops.get(key, ())) for key in self.inputs.keys],
                dtype=np.int64,
            ),
            peasants=np.array(
                [
                    sum(pop.amount for pop in self.pops.get(key, ()) if pop.kind == "peasants")
                    for key in self.inputs.keys
                ],
                dtype=np.int64,
            ),
            polities=tuple(
                Polity(
                    country.kind,
                    tuple(self.nodes[key] for key in country.members),
                    self.nodes[country.capital],
                    int(old.culture[self.nodes[country.capital]]),
                    country.great,
                    country.landed,
                )
                for country in countries
            ),
            ranks={},
            markets=(),
        )
        return settlement_centres(
            self.inputs.graph, settled, reach=self.inputs.reach_steps * STEP_COST
        )


def _confederations(groups: Sequence[HistoricalGroup]) -> tuple[tuple[str, ...], ...]:
    # The installed join trigger allows one tribal confederation per country.
    # Overlapping historical groups share an actual pact network and project to
    # its connected organization; other kinds retain their independent memberships.
    components: list[set[str]] = []
    for group in groups:
        if group.kind != TrajectoryKind.HIGHLAND_CONFEDERATION:
            continue
        joined = set(group.members)
        rest: list[set[str]] = []
        for component in components:
            if component & joined:
                joined |= component
            else:
                rest.append(component)
        components = [*rest, joined]
    return tuple(sorted(tuple(sorted(component)) for component in components))


def _discovered(
    projection: _Projection,
    countries: Sequence[Country],
    diplomacy: DiplomacyProjection,
    confederations: Sequence[Sequence[str]],
) -> tuple[Country, ...]:
    area_of = {country.tag: projection.inputs.areas[country.capital] for country in countries}
    known: dict[str, set[str]] = defaultdict(set)
    for relation in projection.context.state.knowledge:
        if relation.first in projection.tags and relation.second in projection.tags:
            known[projection.tags[relation.first]].add(area_of[projection.tags[relation.second]])
    mutual = (
        *diplomacy.alliances,
        *diplomacy.vassals,
        *diplomacy.protections,
        *diplomacy.exchanges,
    )
    pairs = [(a, b) for pair in mutual for a, b in (pair, tuple(reversed(pair)))]
    pairs.extend(diplomacy.rivals)
    pairs.extend((opinion.first, opinion.second) for opinion in diplomacy.opinions)
    for group in confederations:
        pairs.extend((a, b) for a in group for b in group if a != b)
    for first, second in pairs:
        known[first].add(area_of[second])
    return tuple(
        replace(country, areas=tuple(sorted({*country.areas, *known[country.tag]})))
        for country in countries
    )


def _centres(
    projection: _Projection, societies: Societies
) -> tuple[dict[str, tuple[str, str]], tuple[str, ...]]:
    """Ranks with the culture's town setup and the market centres of the surviving countries.

    The calibrated centres of ``settlement_centres`` are all there is: an exchange agreement
    adds a road and an opinion, never a market. The vanilla Americas have 12 market centres for
    223 landed countries; a market of every partner made each country trade alone (1.2.0).
    """
    setups: dict[str, tuple[str, str]] = {}
    for node, rank in sorted(societies.ranks.items()):
        key = projection.inputs.keys[node]
        culture, _ = projection.identity(key)
        info = projection.inputs.vanilla.cultures[culture]
        setup = (
            (info.city_setup or DEFAULT_CITY) if rank == CITY else (info.town_setup or DEFAULT_TOWN)
        )
        setups[key] = rank, setup
    return setups, tuple(projection.inputs.keys[node] for node in sorted(societies.markets))


def _roads(  # noqa: PLR0913 - existing road targets require centres and current population.
    projection: _Projection,
    countries: Sequence[Country],
    diplomacy: DiplomacyProjection,
    *,
    ranks: Mapping[str, tuple[str, str]],
    markets: Sequence[str],
    population: Mapping[str, int],
) -> tuple[tuple[str, str], ...]:
    by_tag = {country.tag: country for country in countries}
    inputs, nodes = projection.inputs, projection.nodes
    roads: set[tuple[int, int]] = set()
    for first, second in diplomacy.exchanges:
        projection.checkpoint()
        a, b = by_tag[first], by_tag[second]
        roads.update(
            trunk_roads(
                inputs.graph,
                {nodes[key] for key in (*a.members, *b.members)},
                nodes[a.capital],
                (nodes[b.capital],),
            )
        )
    for country in countries:
        if not country.great:
            continue
        projection.checkpoint()
        subjects = [by_tag[subject] for lord, subject in diplomacy.vassals if lord == country.tag]
        members = tuple(nodes[key] for key in country.members)
        targets = road_targets(
            capital=nodes[country.capital],
            vassal_capitals=[nodes[c.capital] for c in subjects],
            members=members,
            ranked=[nodes[key] for key in ranks],
            markets=[nodes[key] for key in markets],
            areas=[inputs.areas[key] for key in inputs.keys],
            population=[population[key] for key in inputs.keys],
            keys=inputs.keys,
        )
        roads.update(
            empire_roads(
                inputs.graph,
                capital=nodes[country.capital],
                members=members,
                vassal_members=[nodes[key] for c in subjects for key in c.members],
                targets=targets,
            )
        )
    return tuple(
        sorted(
            (min(inputs.keys[a], inputs.keys[b]), max(inputs.keys[a], inputs.keys[b]))
            for a, b in roads
        )
    )


def project_start(
    inputs: ProjectionInputs,
    *,
    checkpoint: Callable[[], None] = _checkpoint,
) -> FinalStartPlan:
    """Project every surviving fact once; serializers and consumers share this result."""
    projection = _Projection(inputs, checkpoint)
    countries = projection.countries()
    diplomacy = project_diplomacy(
        projection.context,
        {country.history_actor: country for country in countries},
        inputs.loc_keys,
    )
    confederations = _confederations(projection.groups)
    countries = _discovered(projection, countries, diplomacy, confederations)
    societies = projection.societies(countries)
    ranks, markets = _centres(projection, societies)
    population = dict(zip(inputs.keys, societies.population.tolist(), strict=True))
    roads = _roads(
        projection, countries, diplomacy, ranks=ranks, markets=markets, population=population
    )
    near = [
        {
            projection.actor_number[key]
            for key in projection.context.land_near.get(actor.key, ())
            if key in projection.actor_number
        }
        for actor in projection.actors
    ]
    statistics: dict[str, object] = {
        "land_locations": len(inputs.keys),
        "population_milli": sum(population.values()),
        "calibrated_population_milli": inputs.bootstrap.calibrated_population,
        "diaspora_population_milli": inputs.bootstrap.diaspora_population,
        "inhabited_locations": len(projection.pops),
        "hearths": len(societies.hearths),
        "state_locations": sum(len(c.members) for c in countries if c.kind == STATE),
        "states": sum(c.kind == STATE for c in countries),
        "great_empires": [len(c.members) for c in countries if c.great],
        "largest_ordinary_state": max(
            (len(c.members) for c in countries if c.kind == STATE and not c.great), default=0
        ),
        "tribes": sum(c.kind == TRIBE for c in countries),
        "tribe_locations": sum(len(c.members) for c in countries if c.kind == TRIBE),
        "religion_zones": int(societies.religion.max()) + 1 if inputs.keys else 0,
        "culture_zones": int(societies.culture.max()) + 1 if inputs.keys else 0,
        "religions": len({pop.religion for rows in projection.pops.values() for pop in rows}),
        "cultures": len({pop.culture for rows in projection.pops.values() for pop in rows}),
        "peasants_milli": int(societies.peasants.sum()),
        "ranks": dict(Counter(rank for rank, _ in ranks.values())),
        "markets": len(markets),
        "holy_sites_placed": len(inputs.holy_sites),
        "names_in_local_languages": len(inputs.names),
        "vassals": len(diplomacy.vassals),
        "extraordinary_societies": dict(Counter(group.kind for group in projection.groups)),
        "state_economy": state_economy(societies, near, inputs.vanilla.state_floor),
        "history": {
            "start": START,
            "end": END,
            "rounds": len(inputs.history.rounds),
            "events": len(inputs.history.events),
            "digest": digest(inputs.history, checkpoint=checkpoint),
            "trajectories": report(projection.context),
            "memory_candidates": diplomacy.memory_candidates,
            "named_opinions": len(diplomacy.opinions),
            "bonds_in_chronicle_only": len(diplomacy.unprojected_bonds),
        },
    }
    empires = [{"tag": c.tag, "locations": len(c.members)} for c in countries if c.great]
    result = FinalStartPlan(
        projection.pops,
        countries,
        ranks,
        markets,
        dict(inputs.holy_sites),
        dict(inputs.names),
        diplomacy.vassals,
        {p.key: p.complexity for p in inputs.history.geography.districts},
        population,
        statistics,
        technology={
            "state_levels": dict(Counter(str(c.level) for c in countries if c.kind == STATE)),
            "source": "historical lineage and realized empires",
        },
        roads=roads,
        opinions=tuple((o.first, o.second, o.key) for o in diplomacy.opinions),
        extraordinary=extraordinary_report(inputs.vanilla.empire, empires)
        if inputs.vanilla.empire
        else {},
        alliances=diplomacy.alliances,
        rivals=diplomacy.rivals,
        confederations=confederations,
        confederation_date=inputs.vanilla.archetypes.confederation_date
        if inputs.vanilla.archetypes
        else "",
        archetypes={
            "groups": [
                {
                    "key": g.key,
                    "kind": g.kind,
                    "tags": list(g.members),
                    "hub": g.members[0],
                    "causes": list(g.causes),
                }
                for g in projection.groups
            ]
        },
        protections=diplomacy.protections,
        exchanges=diplomacy.exchanges,
        historical_opinions=diplomacy.opinions,
        historical_groups=projection.groups,
        history=inputs.history,
        history_tags=projection.tags,
    )
    validate_projection(
        result, vanilla=inputs.vanilla, positions=inputs.positions, areas=inputs.areas
    )
    return result
