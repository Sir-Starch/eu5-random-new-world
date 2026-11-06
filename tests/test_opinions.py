"""Historical opinions on the game's scale: analogues, full weights and the install check."""

from __future__ import annotations

import pytest

from rnw.eu5_history_plan import project_start
from rnw.history_model import Factor
from rnw.opinions import (
    ANALOGUES,
    FULL,
    POSITIVE,
    TREATIES,
    OpinionScaleError,
    check,
    opinion_value,
    treaty_opinions,
)

from .history_fixtures import divided_valley
from .test_history_plan import inputs_for

VANILLA = """
opinion_good_relations = { value = 50 yearly_decay = 1 }
opinion_pleased = { value = 20 yearly_decay = 1 }
recent_conflict_lost = { value = -40 yearly_decay = 3 }
border_aggression = { value = -25 yearly_decay = 1 }
outrageous_demands = { value = -25 yearly_decay = 1 }
opinion_alliance = { value = 50 }
vassal_overlord_opinion = { value = 100 }
vassal_subject_opinion = { value = 50 }
opinion_giving_guarantee = { value = 5 }
opinion_receiving_guarantee = { value = 10 }
opinion_rival = { value = -100 }
"""


def test_a_fresh_memory_takes_its_analogue_and_an_old_one_a_share() -> None:
    """Rounded away from zero, so a surviving memory is never written as nothing."""
    for factor, analogue in ANALOGUES.items():
        assert opinion_value(factor, FULL[factor]) == analogue.value
        assert opinion_value(factor, 10 * FULL[factor]) == analogue.value
        assert abs(opinion_value(factor, 1)) == 1
        assert (opinion_value(factor, FULL[factor] // 2) > 0) == (factor in POSITIVE)
    assert opinion_value(Factor.GRIEVANCE, 110) == -20
    assert opinion_value(Factor.TRUST, 61) == 26


def test_the_band_is_the_vanilla_band_of_event_opinions() -> None:
    """Every analogue lies within the values and decays vanilla gives its event opinions."""
    for analogue in ANALOGUES.values():
        assert 20 <= abs(analogue.value) <= 50
        assert 1 <= analogue.yearly_decay <= 3
    assert {Factor.TRUST, Factor.AFFINITY} == POSITIVE


def test_no_memory_is_made_heavier_than_its_full_weight() -> None:
    """The full weights are the largest a memory is made with, so a fresh one is the analogue."""
    history = project_start(inputs_for(divided_valley())).history
    assert history is not None
    made = [memory for event in history.events for memory in event.effects.memories]
    assert made
    assert all(memory.weight <= FULL[memory.factor] for memory in made)


def test_treaties_name_each_side_once() -> None:
    assert [line.key for line in treaty_opinions("vassal", first=False)] == [
        "vassal_subject_opinion"
    ]
    assert treaty_opinions("rival", first=False) == ()
    assert treaty_opinions("exchange", first=True) == ()
    assert len({(line.kind, line.first) for line in TREATIES}) == len(TREATIES)


def test_the_installation_must_define_every_copied_opinion_as_copied() -> None:
    check([VANILLA])
    with pytest.raises(OpinionScaleError, match="recent_conflict_lost"):
        check([VANILLA.replace("value = -40", "value = -30")])
    with pytest.raises(OpinionScaleError, match="opinion_rival"):
        check([VANILLA.replace("opinion_rival", "opinion_other")])
    with pytest.raises(OpinionScaleError, match="opinion_pleased"):
        check([VANILLA.replace("value = 20 yearly_decay = 1", "value = 20 yearly_decay = 2")])
