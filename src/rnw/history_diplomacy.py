"""Project surviving historical bargains and directed memory onto EU5 prerequisites."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final

from rnw.eu5_start import HistoricalOpinion
from rnw.history_checks import require
from rnw.history_model import Action, Factor

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from rnw.eu5_start import Country
    from rnw.history_context import Context
    from rnw.loc_keys import KeySpace

PAIR_LIMIT: Final[int] = 4
WORLD_LIMIT: Final[int] = 2000
VALUE_LIMIT: Final[int] = 50
MEMORY_SCALE: Final[int] = 20
RIVAL_MEMORY: Final[int] = 150
POSITIVE: Final[frozenset[Factor]] = frozenset({Factor.TRUST, Factor.AFFINITY})
DECAY: Final[dict[Factor, int]] = {
    Factor.TRUST: 1,
    Factor.AFFINITY: 1,
    Factor.GRIEVANCE: 3,
    Factor.FEAR: 2,
    Factor.DEPENDENCE: 1,
    Factor.COMPETITION: 2,
}


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
        magnitude = min(VALUE_LIMIT, (amount + MEMORY_SCALE - 1) // MEMORY_SCALE)
        candidates.append(
            HistoricalOpinion(
                "",
                countries[first].tag,
                countries[second].tag,
                factor,
                magnitude if factor in POSITIVE else -magnitude,
                DECAY[factor],
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
