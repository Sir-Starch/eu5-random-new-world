"""Treaties within the diplomatic capacity the game reckons (``history_diplomacy``, C523)."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast, final

from rnw.history_diplomacy import (
    UPKEEP_BUDGET,
    _affordable,  # pyright: ignore[reportPrivateUsage]
    alliance_upkeep,
    guarantee_upkeep,
    upkeep,
)
from rnw.history_model import Action, Factor

if TYPE_CHECKING:
    from rnw.history_context import Context


@final
class _Context:
    """The three things the budget asks of the history: populations, trust and a checkpoint."""

    def __init__(self, population: dict[str, int], trust: dict[tuple[str, str], int]) -> None:
        self.people: dict[str, int] = population
        self.trust: dict[tuple[str, str], int] = trust

    def population(self, key: str) -> int:
        return self.people[key]

    def score(self, first: str, second: str, factor: Factor) -> int:
        return self.trust.get((first, second), 0) if factor is Factor.TRUST else 0

    def checkpoint(self) -> None:
        return None


def test_the_upkeep_follows_the_games_formulas() -> None:
    """Equals pay 0.5 + 2 + 0.5; a far larger partner is capped at 3, a far smaller floored at
    0.1; a guarantee costs half the relative size, at least 0.25."""
    assert alliance_upkeep(1000, 1000) == 3000
    assert alliance_upkeep(1000, 12000) == 4000
    assert alliance_upkeep(12000, 1000) == 1166
    assert alliance_upkeep(100000, 1) == 1100
    assert guarantee_upkeep(1000, 12000) == 6000
    assert guarantee_upkeep(12000, 1000) == 250
    used = upkeep({"A": 1000, "B": 1000, "C": 4000}, [("A", "B")], [("C", "A")])
    assert used == {"A": 3000, "B": 3000, "C": 250}


def test_a_league_keeps_the_most_trusted_treaties_within_the_budget() -> None:
    """Four equals in a full league can each carry two alliances: the trusted pairs come first,
    then the rest in order while both partners can pay. A guarantee its giver cannot pay on top
    stays history, as a bond from client to provider."""
    people = {"a": 1000, "b": 1000, "c": 1000, "d": 1000, "e": 100}
    context = _Context(people, {("a", "b"): 500, ("c", "d"): 400, ("a", "c"): 300})
    actors = {tag.upper(): tag for tag in people}
    alliances = {(first, second) for first in "ABCD" for second in "ABCD" if first < second}
    kept, protections, dropped = _affordable(
        cast("Context", cast("object", context)), actors, alliances, {("E", "A"), ("A", "E")}
    )
    assert kept == {("A", "B"), ("C", "D"), ("A", "C"), ("B", "D")}
    assert protections == {("E", "A")}
    assert sorted(dropped) == sorted(
        [(Action.PACT, "a", "d"), (Action.PACT, "b", "c"), (Action.PROTECTION, "e", "a")]
    )
    population = {tag: people[actor] for tag, actor in actors.items()}
    used = upkeep(population, sorted(kept), sorted(protections))
    assert max(used.values()) <= UPKEEP_BUDGET
