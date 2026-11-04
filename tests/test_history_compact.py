"""Compact state and causal frontiers preserve the historical computation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from typing import TYPE_CHECKING

import pytest

from rnw.history_context import Context
from rnw.history_engine import advance, digest, propose, simulate, validate_history
from rnw.history_model import END, Action, Outcome, Proposal, TrajectoryKind
from rnw.history_societies import _reforms, reforms  # pyright: ignore[reportPrivateUsage]

from .history_fixtures import divided_valley, valley
from .test_history_plan import realized_network
from .test_history_societies import _prepared  # pyright: ignore[reportPrivateUsage]

if TYPE_CHECKING:
    from collections.abc import Callable

    from rnw.history_model import History


def all_fact_causes(context: Context, proposal: Proposal) -> tuple[str, ...]:
    """The pre-compaction reference: explicitly cite every current participant fact."""
    actors = {key for key in (proposal.actor, proposal.target, proposal.threat) if key}
    causes = {context.index.actors[key].origin for key in actors}
    for key in actors:
        causes.update(context.causes_by_actor[key])
    if proposal.kind is Action.REFORM:
        causes.update(
            event.key
            for event in context.experiences[proposal.actor]
            if event.year >= context.state.year - 75 and event.outcome is not Outcome.REFUSED
        )
    if proposal.kind is Action.SEPARATION:
        seats = {part.seat for part in proposal.partitions}
        causes.update(
            context.index.actors[root.key].society_cause
            for root in context.history.foundings
            if seats & set(root.districts)
        )
    return tuple(sorted(causes))


def closure(history: History) -> dict[str, frozenset[str]]:
    found: dict[str, frozenset[str]] = {}
    for event in history.events:
        found[event.key] = frozenset(event.causes).union(*(found[key] for key in event.causes))
    return found


@pytest.mark.parametrize("case", ["valley", "autonomous", "sea", "confederates"])
def test_frontiers_preserve_every_outcome_and_the_complete_ancestor_closure(
    monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    builders: dict[str, Callable[[], History]] = {
        "valley": divided_valley,
        "autonomous": lambda: simulate(valley(), turbulence=800),
        "sea": lambda: realized_network(TrajectoryKind.SEA_LEAGUE),
        "confederates": lambda: realized_network(
            TrajectoryKind.HIGHLAND_CONFEDERATION, overlap=True
        ),
    }
    compact = builders[case]()
    validate_history(compact)
    monkeypatch.setattr(Context, "causes", all_fact_causes)
    reference = builders[case]()
    assert compact.state == reference.state
    assert compact.rounds == reference.rounds
    assert tuple(replace(event, causes=()) for event in compact.events) == tuple(
        replace(event, causes=()) for event in reference.events
    )
    assert closure(compact) == closure(reference)
    assert sum(len(event.causes) for event in compact.events) <= sum(
        len(event.causes) for event in reference.events
    )


@pytest.mark.parametrize("turbulence", [0, 500, 1000])
def test_reusing_the_proposal_snapshot_matches_fresh_contexts(turbulence: int) -> None:
    actual = simulate(valley(), turbulence=turbulence)
    reference = valley()
    while reference.state.year < END:
        proposals = propose(Context(reference, lambda: None), turbulence=turbulence)
        reference = advance(reference, proposals)
    assert actual == reference
    assert all(memory.at(END) > 0 for memory in actual.state.memories)


def test_canonical_digest_matches_recursive_asdict_reference() -> None:
    history = divided_valley()
    payload = json.dumps(asdict(history), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    assert digest(history) == hashlib.sha256(payload.encode("ascii")).hexdigest()


def test_reform_cache_matches_uncached_candidates_and_checks_actor_identity() -> None:
    history = _prepared()
    context = Context(history, lambda: None)
    actor = context.index.actors["a"]
    assert reforms(context, actor) == _reforms(context, actor)
    assert reforms(context, actor) == reforms(context, actor)
    changed = replace(actor, society=replace(actor.society, centralization=0))
    assert reforms(context, changed) == _reforms(context, changed)
    assert reforms(context, actor) == _reforms(context, actor)
