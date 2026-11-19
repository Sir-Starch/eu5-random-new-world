"""The final native start plan, shared by writers, checks, content, AI and atlas.

Construction owns the facts here. Serialization belongs to the EU5 adapters; readers
must not recover population or identity by parsing generated script (history plan H1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rnw.history_model import Action, Factor, History
    from rnw.wording import Name


@dataclass(frozen=True, slots=True)
class Country:
    """One generated native country."""

    tag: str
    name: str
    kind: str
    members: tuple[str, ...]
    capital: str
    culture: str
    religion: str
    include: str
    areas: tuple[str, ...]
    color: tuple[int, int, int]
    color2: tuple[int, int, int]
    government: tuple[tuple[str, str], ...] = ()
    level: int | None = None
    great: bool = False
    rank: str = ""
    landed: bool = False
    currency: tuple[tuple[str, int], ...] = ()
    archetype: str = ""
    laws: tuple[tuple[str, str], ...] = ()
    parliament: str = ""
    history_actor: str = ""
    memberships: tuple[str, ...] = ()
    archetypes: tuple[str, ...] = ()
    # Where the country stands on each societal value at the start, its template's included
    # (``eu5_laws.positions``); the window shows them as the game does.
    positions: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True, slots=True)
class PopCohort:
    """One pop's type, milli-population and identities, before script serialization."""

    kind: str
    amount: int
    culture: str
    religion: str


@dataclass(frozen=True, slots=True)
class HistoricalOpinion:
    """A bounded directed bias with its actual historical cause, before localization."""

    key: str
    first: str
    second: str
    factor: Factor
    value: int
    yearly_decay: int
    cause: str
    year: int
    action: Action
    place: str = ""


@dataclass(frozen=True, slots=True)
class HistoricalGroup:
    """An actual structure, with explicit membership and backward causal references."""

    key: str
    kind: str
    members: tuple[str, ...]
    causes: tuple[str, ...]
    hearths: tuple[str, ...] = ()
    actors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class FinalStartPlan:
    """The complete historical start state shared by all output consumers.

    The normal H4 path conserves the post-diaspora population and stores its exact
    current totals in ``population``. Legacy static diagnostics retain H1's
    calibrated-only population totals; their ``pops`` also include diaspora.
    """

    pops: dict[str, tuple[PopCohort, ...]]
    countries: tuple[Country, ...]
    ranks: dict[str, tuple[str, str]]
    markets: tuple[str, ...]
    holy_sites: dict[str, str]
    names: dict[str, Name]
    vassals: tuple[tuple[str, str], ...]
    complexity: dict[str, int]
    population: dict[str, int]
    stats: dict[str, object]
    technology: dict[str, object] = field(default_factory=dict)
    roads: tuple[tuple[str, str], ...] = ()
    opinions: tuple[tuple[str, str, str], ...] = ()
    extraordinary: dict[str, object] = field(default_factory=dict)
    alliances: tuple[tuple[str, str], ...] = ()
    rivals: tuple[tuple[str, str], ...] = ()
    confederations: tuple[tuple[str, ...], ...] = ()
    confederation_date: str = ""
    archetypes: dict[str, object] = field(default_factory=dict)
    protections: tuple[tuple[str, str], ...] = ()
    exchanges: tuple[tuple[str, str], ...] = ()
    historical_opinions: tuple[HistoricalOpinion, ...] = ()
    historical_groups: tuple[HistoricalGroup, ...] = ()
    history: History | None = None
    history_tags: dict[str, str] = field(default_factory=dict)


def _merge_records[T](records: Sequence[dict[str, T]]) -> dict[str, T]:
    combined: dict[str, T] = {}
    for record in records:
        if overlap := combined.keys() & record.keys():
            message = f"Regional starts assign {min(overlap)} more than once"
            raise ValueError(message)
        combined.update(record)
    return combined


def combine_starts(plans: Sequence[FinalStartPlan]) -> FinalStartPlan:
    """Assemble the world's setup while each chronicle keeps its own historical causes."""
    countries = tuple(country for plan in plans for country in plan.countries)
    tags = {country.tag for country in countries}
    owners = [location for country in countries for location in country.members]
    if len(tags) != len(countries) or len(owners) != len(set(owners)):
        message = "Combined regional starts have shared country tags or owned locations"
        raise ValueError(message)
    confederations = [plan for plan in plans if plan.confederations]
    dates = {plan.confederation_date for plan in confederations}
    if len(dates) > 1:
        message = "Regional confederations disagree about the shared start date"
        raise ValueError(message)
    return FinalStartPlan(
        pops=_merge_records([plan.pops for plan in plans]),
        countries=countries,
        ranks=_merge_records([plan.ranks for plan in plans]),
        markets=tuple(place for plan in plans for place in plan.markets),
        holy_sites=_merge_records([plan.holy_sites for plan in plans]),
        names=_merge_records([plan.names for plan in plans]),
        vassals=tuple(pair for plan in plans for pair in plan.vassals),
        complexity=_merge_records([plan.complexity for plan in plans]),
        population=_merge_records([plan.population for plan in plans]),
        stats={"continents": [plan.stats for plan in plans]},
        roads=tuple(edge for plan in plans for edge in plan.roads),
        opinions=tuple(opinion for plan in plans for opinion in plan.opinions),
        alliances=tuple(pair for plan in plans for pair in plan.alliances),
        rivals=tuple(pair for plan in plans for pair in plan.rivals),
        confederations=tuple(group for plan in confederations for group in plan.confederations),
        confederation_date=next(iter(dates), ""),
        protections=tuple(pair for plan in plans for pair in plan.protections),
        exchanges=tuple(pair for plan in plans for pair in plan.exchanges),
        historical_opinions=tuple(
            opinion for plan in plans for opinion in plan.historical_opinions
        ),
        historical_groups=tuple(group for plan in plans for group in plan.historical_groups),
    )
