"""Necessary-condition pruning preserves complete eligible choices and whole histories."""

from __future__ import annotations

# pyright: reportPrivateUsage=false
from collections import Counter
from dataclasses import replace

import pytest

from rnw import history_engine as engine
from rnw.history_context import Context
from rnw.history_engine import create, digest, simulate
from rnw.history_model import History, Tenure, TrajectoryKind

from .history_fixtures import divided_valley, valley
from .reference.history_candidates import unpruned_choices
from .test_history_plan import quiet, realized_network
from .test_history_societies import _prepared


def histories() -> tuple[History, ...]:
    mixed = _prepared(pressure=True)
    community = create(
        replace(
            mixed.geography,
            districts=tuple(
                replace(d, tenure=Tenure.COMMUNITY) if d.key == "c" else d
                for d in mixed.geography.districts
            ),
        ),
        tuple(replace(f, tenure=Tenure.COMMUNITY) if f.key == "c" else f for f in mixed.foundings),
        seed=42,
    )
    return (
        valley(),
        quiet(valley()),
        divided_valley(),
        _prepared(),
        mixed,
        community,
        realized_network(TrajectoryKind.SEA_LEAGUE),
        realized_network(TrajectoryKind.HIGHLAND_CONFEDERATION, overlap=True),
    )


def test_every_eligible_candidate_is_retained_with_the_same_multiplicity() -> None:
    for history in histories():
        reference, current = Context(history, lambda: None), Context(history, lambda: None)
        for actor in history.state.actors:
            if actor.living:
                assert Counter(engine._local_choices(current, actor)) == Counter(
                    unpruned_choices(reference, actor)
                )


@pytest.mark.parametrize("turbulence", [0, 200, 500, 800, 1000])
def test_unpruned_policy_produces_the_same_complete_rounds_and_digests(
    turbulence: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    pruned = engine._local_choices
    for original in histories():
        with monkeypatch.context() as patch:
            patch.setattr(engine, "_local_choices", unpruned_choices)
            expected = simulate(original, turbulence=turbulence)
        assert engine._local_choices is pruned
        actual = simulate(original, turbulence=turbulence)
        assert actual == expected
        assert digest(actual) == digest(expected)
