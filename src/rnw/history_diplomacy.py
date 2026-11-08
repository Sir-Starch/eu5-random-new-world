"""Project surviving historical bargains and directed memory onto EU5 prerequisites."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final

from rnw.eu5_start import HistoricalOpinion
from rnw.history_checks import require
from rnw.history_model import Action, Factor
from rnw.opinions import ANALOGUES, opinion_value

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from rnw.eu5_start import Country
    from rnw.history_context import Context
    from rnw.loc_keys import KeySpace

PAIR_LIMIT: Final[int] = 4
WORLD_LIMIT: Final[int] = 2000
RIVAL_MEMORY: Final[int] = 150
# The diplomatic capacity a treaty uses, in thousandths, as the game reckons it ([V-LOCAL] EU5
# 1.4.7, ``in_game/common/script_values/diplomatic_values.txt``): an alliance costs each partner
# 0.5, twice the other's economic base over its own (0.1 to 3) and 0.5 less a two-hundredth of
# its opinion of the other (``alliance_upkeep_cost``); a guarantee costs the giver half the
# receiver's income over its own, at least 0.25 (``guarantee_upkeep_cost``). Population stands
# for both the economic base and the income (``ECONOMICAL_BASE_FROM_POP``); the opinion term is
# taken at a neutral opinion, and the great and regional power surcharges are left out.
ALLIANCE_BASE: Final[int] = 500
ALLIANCE_RELATIVE: Final[int] = 2000
ALLIANCE_RELATIVE_RANGE: Final[tuple[int, int]] = (100, 3000)
ALLIANCE_OPINION: Final[int] = 500
GUARANTEE_RELATIVE: Final[int] = 500
GUARANTEE_FLOOR: Final[int] = 250
# What a country's treaties may use at the start: two alliances between equals. The game's base
# capacity is [UNKNOWN] (not in the scripts or defines). In the owner's ATDT sittings (C523) the
# nine generated countries that exceeded it even with a ruler of diplomacy 100 hold treaties this
# reckoning puts at 8.3 to 37.8 (a one-location republic with five alliances and four guarantees
# at 31.0); of those at 7.4 or less none did, and one at 10.2 did not. A ruler of diplomacy 100
# doubles the capacity (``ruler_dip``), so about 8 to 10 there is 4 to 5 without the ruler.
# Vanilla's 1337 gives no country more than three alliances, most one.
UPKEEP_BUDGET: Final[int] = 6000


def alliance_upkeep(own: int, partner: int) -> int:
    """What an alliance with a country of population ``partner`` costs one of ``own``."""
    low, high = ALLIANCE_RELATIVE_RANGE
    relative = min(max(ALLIANCE_RELATIVE * partner // max(own, 1), low), high)
    return ALLIANCE_BASE + relative + ALLIANCE_OPINION


def guarantee_upkeep(own: int, receiver: int) -> int:
    """What guaranteeing a country of population ``receiver`` costs a giver of ``own``."""
    return max(GUARANTEE_RELATIVE * receiver // max(own, 1), GUARANTEE_FLOOR)


def upkeep(
    population: Mapping[str, int],
    alliances: Sequence[tuple[str, str]],
    protections: Sequence[tuple[str, str]],
) -> dict[str, int]:
    """Each country's reckoned diplomatic upkeep of its alliances and given guarantees."""
    used: dict[str, int] = defaultdict(int)
    for first, second in alliances:
        used[first] += alliance_upkeep(population[first], population[second])
        used[second] += alliance_upkeep(population[second], population[first])
    for giver, receiver in protections:
        used[giver] += guarantee_upkeep(population[giver], population[receiver])
    return dict(used)


def _affordable(
    context: Context,
    actors: Mapping[str, str],
    alliances: set[tuple[str, str]],
    protections: set[tuple[str, str]],
) -> tuple[set[tuple[str, str]], set[tuple[str, str]], list[tuple[str, str, str]]]:
    """The treaties each country can carry within ``UPKEEP_BUDGET``, the most trusted first;
    the rest stay bargains of the chronicle (``actors`` maps a tag to its history actor)."""
    population = {tag: context.population(actor) for tag, actor in actors.items()}

    def trust(first: str, second: str) -> int:
        a, b = actors[first], actors[second]
        return context.score(a, b, Factor.TRUST) + context.score(b, a, Factor.TRUST)

    used: dict[str, int] = defaultdict(int)
    kept_alliances: set[tuple[str, str]] = set()
    kept_protections: set[tuple[str, str]] = set()
    dropped: list[tuple[str, str, str]] = []
    for first, second in sorted(
        alliances,
        key=lambda pair: (
            -trust(*pair),
            alliance_upkeep(population[pair[0]], population[pair[1]])
            + alliance_upkeep(population[pair[1]], population[pair[0]]),
            pair,
        ),
    ):
        context.checkpoint()
        cost = alliance_upkeep(population[first], population[second])
        back = alliance_upkeep(population[second], population[first])
        if used[first] + cost <= UPKEEP_BUDGET and used[second] + back <= UPKEEP_BUDGET:
            used[first] += cost
            used[second] += back
            kept_alliances.add((first, second))
        else:
            dropped.append((Action.PACT, actors[first], actors[second]))
    for giver, receiver in sorted(
        protections,
        key=lambda pair: (
            -trust(*pair),
            guarantee_upkeep(population[pair[0]], population[pair[1]]),
            pair,
        ),
    ):
        context.checkpoint()
        cost = guarantee_upkeep(population[giver], population[receiver])
        if used[giver] + cost <= UPKEEP_BUDGET:
            used[giver] += cost
            kept_protections.add((giver, receiver))
        else:
            # A protection bond runs from its client to its provider.
            dropped.append((Action.PROTECTION, actors[receiver], actors[giver]))
    return kept_alliances, kept_protections, dropped


@dataclass(frozen=True, slots=True)
class DiplomacyProjection:
    vassals: tuple[tuple[str, str], ...]
    alliances: tuple[tuple[str, str], ...]
    rivals: tuple[tuple[str, str], ...]
    protections: tuple[tuple[str, str], ...]
    exchanges: tuple[tuple[str, str], ...]
    opinions: tuple[HistoricalOpinion, ...]
    memory_candidates: int
    unprojected_bonds: tuple[tuple[str, str, str], ...]


def _candidates(
    context: Context,
    countries: Mapping[str, Country],
) -> list[HistoricalOpinion]:
    events = {event.key: event for event in context.history.events}
    amounts: dict[tuple[str, str, Factor, str], int] = defaultdict(int)
    for memory in context.state.memories:
        if memory.first in countries and memory.second in countries:
            amounts[memory.first, memory.second, memory.factor, memory.cause] += memory.at(
                context.state.year,
            )
    candidates: list[HistoricalOpinion] = []
    for (first, second, factor, cause), amount in sorted(amounts.items()):
        context.checkpoint()
        if not amount:
            continue
        require(cause in events, "An opinion has no historical cause")
        event = events[cause]
        places = sorted(
            {
                *(transfer.district for transfer in event.effects.transfers),
                *(settlement.district for settlement in event.effects.settlements),
            }
        )
        candidates.append(
            HistoricalOpinion(
                "",
                countries[first].tag,
                countries[second].tag,
                factor,
                opinion_value(factor, amount),
                ANALOGUES[factor].yearly_decay,
                cause,
                event.year,
                event.kind,
                places[0] if places else "",
            )
        )
    return candidates


def _importance(opinion: HistoricalOpinion) -> tuple[int, int, str, str]:
    return -abs(opinion.value), -opinion.year, opinion.cause, opinion.factor


def select_opinions(
    candidates: Sequence[HistoricalOpinion],
    alliances: Sequence[tuple[str, str]],
    keys: KeySpace,
) -> tuple[HistoricalOpinion, ...]:
    """Construct bounded memory bundles; allied directions retain a nonnegative sum.

    Each direction is selected as one bundle, including at the world limit, so
    trimming cannot strand a grievance after dropping the trust that supported it.
    No memory's sign, cause or value is changed to satisfy an alliance.
    """
    allied = {pair for a, b in alliances for pair in ((a, b), (b, a))}
    pairs: dict[tuple[str, str], list[HistoricalOpinion]] = defaultdict(list)
    for opinion in candidates:
        pairs[opinion.first, opinion.second].append(opinion)
    bundles: list[tuple[HistoricalOpinion, ...]] = []
    for pair, memories in sorted(pairs.items()):
        selected: list[HistoricalOpinion] = []
        if pair in allied:
            order = sorted(memories, key=lambda item: (item.value < 0, *_importance(item)))
            total = 0
            for memory in order:
                if len(selected) < PAIR_LIMIT and total + memory.value >= 0:
                    selected.append(memory)
                    total += memory.value
        else:
            selected = sorted(memories, key=_importance)[:PAIR_LIMIT]
        if selected:
            bundles.append(tuple(sorted(selected, key=_importance)))
    ordered = sorted(
        bundles,
        key=lambda bundle: (
            _importance(bundle[0]),
            bundle[0].first,
            bundle[0].second,
        ),
    )
    chosen: list[HistoricalOpinion] = []
    for bundle in ordered:
        if len(chosen) + len(bundle) <= WORLD_LIMIT:
            chosen.extend(bundle)
    return tuple(
        replace(opinion, key=keys.next("rnw_hist_", 0))
        for opinion in sorted(
            chosen,
            key=lambda item: (
                item.first,
                item.second,
                item.cause,
                item.factor,
            ),
        )
    )


def project_diplomacy(
    context: Context,
    countries: Mapping[str, Country],
    keys: KeySpace,
) -> DiplomacyProjection:
    """Only living, landed countries enter engine diplomacy with a written capital.

    Pop-type tribes and communities retain their bargains and memories in the
    chronicle. Vanilla has no startup opinions for pop countries, and their setup
    cannot explicitly assign the capital that scripted opinions need to discover.
    """
    landed = {
        actor: country
        for actor, country in countries.items()
        if country.kind == "state" or country.landed
    }
    vassals: set[tuple[str, str]] = set()
    alliances: set[tuple[str, str]] = set()
    protections: set[tuple[str, str]] = set()
    exchanges: set[tuple[str, str]] = set()
    internal: list[tuple[str, str, str]] = []
    for bond in context.state.bonds:
        context.checkpoint()
        if bond.first not in landed or bond.second not in landed:
            internal.append((bond.kind, bond.first, bond.second))
            continue
        first, second = landed[bond.first].tag, landed[bond.second].tag
        if bond.kind is Action.DEPENDENCY:
            vassals.add((second, first))
        elif bond.kind is Action.PACT:
            require(
                bond.first not in context.subjects and bond.second not in context.subjects,
                "A subject has an independent defence pact",
            )
            alliances.add((min(first, second), max(first, second)))
        elif bond.kind is Action.PROTECTION:
            # The installed guarantee expires on subjecthood or lower provider
            # rank. Such a bargain remains history, rather than an invalid treaty.
            if not {bond.first, bond.second} & context.subjects and (
                not landed[bond.first].great or landed[bond.second].great
            ):
                protections.add((second, first))
            else:
                internal.append((bond.kind, bond.first, bond.second))
        elif bond.kind is Action.EXCHANGE:
            exchanges.add((min(first, second), max(first, second)))
    rivals = {
        (landed[first].tag, landed[second].tag)
        for first, second in sorted(context.known)
        if first in landed
        and second in landed
        and first not in context.subjects
        and second not in context.subjects
        and not context.has(Action.PACT, first, second)
        and max(
            context.score(first, second, Factor.GRIEVANCE),
            context.score(first, second, Factor.COMPETITION),
        )
        >= RIVAL_MEMORY
    }
    candidates = _candidates(context, landed)
    protections = {
        pair for pair in protections if pair not in rivals and tuple(reversed(pair)) not in rivals
    }
    # Treaties beyond a country's diplomatic capacity start the game with a penalty the engine
    # cannot lift (C523); such bargains remain history.
    alliances, protections, unaffordable = _affordable(
        context,
        {country.tag: actor for actor, country in landed.items()},
        alliances,
        protections,
    )
    internal.extend(unaffordable)
    return DiplomacyProjection(
        tuple(sorted(vassals)),
        tuple(sorted(alliances)),
        tuple(sorted(rivals)),
        tuple(sorted(protections)),
        tuple(sorted(exchanges)),
        select_opinions(candidates, tuple(sorted(alliances)), keys),
        len(candidates),
        tuple(sorted(internal)),
    )
