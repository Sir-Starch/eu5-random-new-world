"""Project conservative history movements back into exact EU5 typed populations.

History groups non-farming people by identity. At this boundary the original
non-farmer types travel proportionally, with deterministic largest-remainder
rounding. No person, identity, farmer or elite type is created by projection.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Final

from rnw.eu5_history import canonical_population, identity_cohorts
from rnw.eu5_start import PopCohort
from rnw.history_checks import require
from rnw.history_model import Action, Cohort, Outcome

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from rnw.eu5_history import HistoryBootstrap
    from rnw.history_model import Event, History

MOVEMENT_ENDPOINTS: Final[int] = 2


def _checkpoint() -> None:
    """Optional generator cancellation callback."""


def _apportion(amount: int, counts: Mapping[str, int]) -> dict[str, int]:
    total = sum(counts.values())
    require(0 <= amount <= total, "Migration exceeds its typed source population")
    if not amount:
        return {}
    taken = {kind: amount * count // total for kind, count in counts.items()}
    order = sorted(counts, key=lambda kind: (-(amount * counts[kind] % total), kind))
    for kind in order[: amount - sum(taken.values())]:
        taken[kind] += 1
    return taken


def _take(rows: Sequence[PopCohort], move: Cohort) -> tuple[PopCohort, ...]:
    matching = [
        pop
        for pop in rows
        if (pop.culture, pop.religion)
        == (
            move.culture,
            move.religion,
        )
    ]
    farmers = sum(pop.amount for pop in matching if pop.kind == "peasants")
    require(0 <= move.peasants <= min(farmers, move.population), "Invalid farmer migration")
    nonfarmers: Counter[str] = Counter()
    for pop in matching:
        if pop.kind != "peasants":
            nonfarmers[pop.kind] += pop.amount
    amounts = _apportion(move.population - move.peasants, nonfarmers)
    if move.peasants:
        amounts["peasants"] = move.peasants
    return tuple(
        PopCohort(kind, amount, move.culture, move.religion)
        for kind, amount in sorted(amounts.items())
        if amount
    )


def _movement(
    event: Event,
    current: Mapping[str, tuple[PopCohort, ...]],
) -> tuple[str, str, Cohort]:
    changes: list[tuple[str, str, str, int, int]] = []
    require(len(event.effects.settlements) == MOVEMENT_ENDPOINTS, "Migration needs two settlements")
    require(
        len({place.district for place in event.effects.settlements}) == MOVEMENT_ENDPOINTS,
        "Migration repeats a settlement",
    )
    for place in event.effects.settlements:
        require(place.cause == event.key, "Migration settlement has a different cause")
        before = {
            (pop.culture, pop.religion): pop for pop in identity_cohorts(current[place.district])
        }
        after = {(pop.culture, pop.religion): pop for pop in place.cohorts}
        require(len(after) == len(place.cohorts), "Migration repeats a cohort identity")
        for culture, religion in sorted(before.keys() | after.keys()):
            empty = Cohort(culture, religion, 0, 0)
            old, new = before.get((culture, religion), empty), after.get((culture, religion), empty)
            people, farmers = new.population - old.population, new.peasants - old.peasants
            if people or farmers:
                changes.append((place.district, culture, religion, people, farmers))
    require(len(changes) == MOVEMENT_ENDPOINTS, "Migration changes more than one identity")
    source, destination = sorted(changes, key=lambda change: change[3])
    require(
        source[3] < 0 < destination[3]
        and source[1:3] == destination[1:3]
        and (source[3], source[4]) == (-destination[3], -destination[4]),
        "Migration does not conserve population and farmers",
    )
    return (
        source[0],
        destination[0],
        Cohort(
            destination[1],
            destination[2],
            destination[3],
            destination[4],
        ),
    )


def project_population(
    bootstrap: HistoryBootstrap,
    history: History,
    *,
    checkpoint: Callable[[], None] = _checkpoint,
) -> dict[str, tuple[PopCohort, ...]]:
    """Exact typed population of a history rooted in this post-diaspora bootstrap.

    The history engine owns causal validation. This projection independently checks
    the demographic effects it consumes, its final agreement, and all typed budgets.
    Conquest, unions and changes of government never assimilate or retype a pop.
    """
    root = bootstrap.history
    require(
        history.geography == root.geography
        and history.foundings == root.foundings
        and history.seed == root.seed
        and history.empire_permille == root.empire_permille
        and history.turbulence == root.turbulence,
        "Population projection belongs to a different bootstrap",
    )
    current = dict(bootstrap.pops)
    for event in history.events:
        checkpoint()
        if event.kind is Action.FOUNDATION:
            continue
        if event.kind is not Action.MIGRATION or event.outcome is not Outcome.ACCEPTED:
            require(not event.effects.settlements, "A non-migration changed population")
            continue
        require(
            all(place.district in current for place in event.effects.settlements),
            "Migration names an uninhabited location",
        )
        source, destination, move = _movement(event, current)
        taken = _take(current[source], move)
        amounts = {(pop.kind, pop.culture, pop.religion): pop.amount for pop in current[source]}
        for pop in taken:
            amounts[pop.kind, pop.culture, pop.religion] -= pop.amount
        current[source] = tuple(
            PopCohort(kind, amount, culture, religion)
            for (kind, culture, religion), amount in sorted(amounts.items())
            if amount
        )
        current[destination] = dict(
            canonical_population(
                {
                    destination: (*current[destination], *taken),
                }
            )
        )[destination]
        for place in event.effects.settlements:
            require(
                identity_cohorts(current[place.district]) == place.cohorts,
                "Typed migration differs from history",
            )
    actual = {place.district: place.cohorts for place in history.state.settlements}
    require(
        {key: identity_cohorts(rows) for key, rows in current.items()} == actual,
        "Projected population differs from the final history",
    )

    def budget(pops: Mapping[str, Sequence[PopCohort]]) -> Counter[tuple[str, str, str]]:
        counts: Counter[tuple[str, str, str]] = Counter()
        for rows in pops.values():
            for pop in rows:
                counts[pop.kind, pop.culture, pop.religion] += pop.amount
        return counts

    require(budget(current) == budget(dict(bootstrap.pops)), "Typed population budget changed")
    return current
