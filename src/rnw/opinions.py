"""Opinions on the game's scale: historical memories as vanilla opinions, and treaties' opinions.

EU5 counts opinion in tens and hundreds. Its event opinions are named biases with a ``value``
and a ``yearly_decay`` (``in_game/common/biases/03_opinion_from_events.txt``), and the engine
adds its own for the relations a start writes (``00_opinion_hardcoded.txt``,
``02_opinion_subject_types.txt``). A surviving historical memory is written as the vanilla
opinion of its kind: the analogue's decay, and its value in proportion to how much of the
memory survives to 1337, so a fresh memory takes the analogue's full value. The analogue's own
name is not used; the opinion keeps its historical name.

The treaties' opinions are what the engine gives for an alliance, a rivalry, a subject
relationship and a guarantee that the start writes; the window shows them beside the historical
ones, under the game's names. That the engine gives each to the side named here is [INFERRED]
from the biases' names (``vassal_subject_opinion`` is *Our Liege*, ``opinion_rival`` *Rival*).

``check`` refuses an installation whose values differ, so a game patch that rescales them stops
the export instead of leaving the world off the game's scale. Pure: it reads texts, not files.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.history_model import Factor
from rnw.pdx import Block, parse

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class Analogue:
    """A vanilla opinion: its key, its value and how much of it fades each year."""

    key: str
    value: int
    yearly_decay: int


# The vanilla opinion of each kind of memory (history plan §10): kept agreements are good
# relations, shared experience pleases, a loss is a recent conflict lost, a shown threat and
# overlapping aims are border aggression, and the burden of dependence is outrageous demands.
ANALOGUES: Final[dict[Factor, Analogue]] = {
    Factor.TRUST: Analogue("opinion_good_relations", 50, 1),
    Factor.AFFINITY: Analogue("opinion_pleased", 20, 1),
    Factor.GRIEVANCE: Analogue("recent_conflict_lost", -40, 3),
    Factor.FEAR: Analogue("border_aggression", -25, 1),
    Factor.COMPETITION: Analogue("border_aggression", -25, 1),
    Factor.DEPENDENCE: Analogue("outrageous_demands", -25, 1),
}
# The largest weight a memory of each factor has when history makes it (``history_actions``,
# ``history_societies``): a conquest's grievance, a repelled or successful attack's fear, the
# aggressor's competition, a pact's trust (60, tradition up to 40, sacred access up to 20),
# a host's affinity and a dependency. ``tests/test_opinions.py`` checks every made memory.
FULL: Final[dict[Factor, int]] = {
    Factor.TRUST: 120,
    Factor.AFFINITY: 40,
    Factor.GRIEVANCE: 220,
    Factor.FEAR: 120,
    Factor.COMPETITION: 60,
    Factor.DEPENDENCE: 100,
}
POSITIVE: Final[frozenset[Factor]] = frozenset(
    factor for factor, analogue in ANALOGUES.items() if analogue.value > 0
)


@dataclass(frozen=True, slots=True)
class Treaty:
    """The opinion the engine gives one side of a written relation of the other."""

    kind: str
    first: bool
    key: str
    value: int


# ``vassal`` pairs are (overlord, subject), ``guarantee`` pairs (guarantor, protected) and
# ``rival`` pairs (the country that rivals, its rival); ``first`` is the side that holds the
# opinion. A relation without a line here (an exchange of goods) gives the engine no opinion.
TREATIES: Final[tuple[Treaty, ...]] = (
    Treaty("alliance", first=True, key="opinion_alliance", value=50),
    Treaty("alliance", first=False, key="opinion_alliance", value=50),
    Treaty("vassal", first=True, key="vassal_overlord_opinion", value=100),
    Treaty("vassal", first=False, key="vassal_subject_opinion", value=50),
    Treaty("guarantee", first=True, key="opinion_giving_guarantee", value=5),
    Treaty("guarantee", first=False, key="opinion_receiving_guarantee", value=10),
    Treaty("rival", first=True, key="opinion_rival", value=-100),
)


class OpinionScaleError(ValueError):
    """The installed game defines an opinion differently from the scale the world copies."""


def opinion_value(factor: Factor, amount: int) -> int:
    """A surviving memory's opinion: its analogue's value in proportion to ``amount`` of the
    factor's full weight, rounded away from zero and never beyond the analogue."""
    analogue = ANALOGUES[factor]
    size = abs(analogue.value)
    magnitude = min(size, -(-min(max(amount, 0), FULL[factor]) * size // FULL[factor]))
    return magnitude if analogue.value > 0 else -magnitude


def treaty_opinions(kind: str, *, first: bool) -> tuple[Treaty, ...]:
    """The engine's opinions of one side of a relation of ``kind``."""
    return tuple(line for line in TREATIES if line.kind == kind and line.first == first)


def _number(block: Block, key: str) -> float | None:
    entry = block.first(key)
    if entry is None or isinstance(entry.value, Block):
        return None
    try:
        return float(entry.value)
    except ValueError:
        return None


def check(bias_texts: Sequence[str]) -> None:
    """Raise unless every analogue and treaty opinion has, in the game, the value copied here."""
    found: dict[str, Block] = {}
    for text in bias_texts:
        for entry in parse(text).entries:
            if entry.key is not None and isinstance(entry.value, Block):
                found[entry.key] = entry.value
    expected: list[tuple[str, int, int | None]] = [
        *((a.key, a.value, a.yearly_decay) for a in ANALOGUES.values()),
        *((t.key, t.value, None) for t in TREATIES),
    ]
    for key, value, decay in expected:
        block = found.get(key)
        if block is None:
            message = f"The opinion {key} that the world's opinions copy is gone from the game"
            raise OpinionScaleError(message)
        if _number(block, "value") != value or (
            decay is not None and _number(block, "yearly_decay") != decay
        ):
            message = f"The game's opinion {key} no longer has the value or decay the world copies"
            raise OpinionScaleError(message)
