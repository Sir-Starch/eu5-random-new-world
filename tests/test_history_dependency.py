"""Client admissions consume real administrative capacity, including ancestor rulers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rnw.history_context import Context
from rnw.history_engine import advance, validate_history
from rnw.history_model import Action, Authority, Outcome, Proposal, Reason, Society

from .history_fixtures import court, defeat

if TYPE_CHECKING:
    from rnw.history_model import History


def test_joint_admissions_cannot_spend_the_same_administrative_capacity_twice() -> None:
    ordinary = Society(authority=Authority.RULER)
    history = court(
        {"a": (1000, 500, 0, True), "b": (1000, 500, 0, True), "lord": (10_000, 5000, 2, False)},
        {
            "a": ordinary,
            "b": ordinary,
            "lord": Society(centralization=200, integration=200, authority=Authority.RULER),
        },
    )
    history = defeat(defeat(history, "lord", "a"), "lord", "b")
    proposals = (Proposal(Action.DEPENDENCY, "a", "lord"), Proposal(Action.DEPENDENCY, "b", "lord"))
    result = advance(history, proposals)
    events = result.events[-2:]
    accepted = next(e for e in events if e.outcome is Outcome.ACCEPTED)
    refused = next(e for e in events if e.outcome is Outcome.REFUSED)
    assert refused.reason is Reason.COMMITTED
    assert accepted.key in refused.causes
    subject = next(key for key in ("a", "b") if key not in accepted.actors)
    result = advance(result, (Proposal(Action.DEPENDENCY, subject, "lord"),))
    assert result.events[-1].reason is Reason.CAPACITY
    assert len(result.state.bonds) == 1
    validate_history(result)
    assert advance(history, tuple(reversed(proposals))) == advance(history, proposals)


def _nested(*, capable_root: bool = False) -> History:
    """Root, middle and leaf, each lord having already defeated its future subject."""
    ordinary = Society(authority=Authority.RULER)
    history = court(
        {
            "leaf": (500, 338, 0, True),
            "middle": (1800, 1100, 1, True),
            "root": (40_000, 20_000, 5, False),
        },
        {
            "leaf": ordinary,
            "middle": ordinary,
            "root": ordinary
            if capable_root
            else Society(centralization=120, integration=125, authority=Authority.RULER),
        },
    )
    return defeat(defeat(history, "root", "middle"), "middle", "leaf")


def test_a_new_subclient_must_fit_the_ultimate_rulers_existing_obligations() -> None:
    history = advance(_nested(), (Proposal(Action.DEPENDENCY, "middle", "root"),))
    assert history.events[-1].outcome is Outcome.ACCEPTED
    result = advance(history, (Proposal(Action.DEPENDENCY, "leaf", "middle"),))
    assert result.events[-1].reason is Reason.CAPACITY
    assert len(result.state.bonds) == 1
    validate_history(result)


def test_an_incoming_lords_whole_client_realm_counts_toward_capacity() -> None:
    history = advance(_nested(), (Proposal(Action.DEPENDENCY, "leaf", "middle"),))
    assert history.events[-1].outcome is Outcome.ACCEPTED
    result = advance(history, (Proposal(Action.DEPENDENCY, "middle", "root"),))
    assert result.events[-1].reason is Reason.CAPACITY
    assert len(result.state.bonds) == 1
    validate_history(result)


def test_a_capable_ruler_can_accept_a_real_nested_realm_without_changing_ownership() -> None:
    history = _nested(capable_root=True)
    before = history.state
    history = advance(history, (Proposal(Action.DEPENDENCY, "leaf", "middle"),))
    inherited_cause = history.events[-1].key
    history = advance(history, (Proposal(Action.DEPENDENCY, "middle", "root"),))
    assert history.events[-1].outcome is Outcome.ACCEPTED
    assert inherited_cause in history.events[-1].causes
    context = Context(history, lambda: None)
    assert context.realm("root") == {"root", "middle", "leaf"}
    assert context.administrators("leaf") == ("leaf", "middle", "root")
    assert history.state.holdings == before.holdings
    assert history.state.settlements == before.settlements
    validate_history(history)


def test_two_branches_cannot_simultaneously_exhaust_the_same_ancestor() -> None:
    ordinary = Society(authority=Authority.RULER)
    history = court(
        {
            "b": (3000, 2000, 1, True),
            "c": (3000, 2000, 1, True),
            "d": (700, 400, 0, True),
            "e": (700, 400, 0, True),
            "root": (70_000, 35_000, 5, False),
        },
        {
            **dict.fromkeys(("b", "c", "d", "e"), ordinary),
            "root": Society(centralization=100, integration=280, authority=Authority.RULER),
        },
    )
    for lord, subject in (("root", "b"), ("root", "c"), ("b", "d"), ("c", "e")):
        history = defeat(history, lord, subject)
    for key in ("b", "c"):
        history = advance(history, (Proposal(Action.DEPENDENCY, key, "root"),))
        assert history.events[-1].outcome is Outcome.ACCEPTED
    history = advance(
        history, (Proposal(Action.DEPENDENCY, "d", "b"), Proposal(Action.DEPENDENCY, "e", "c"))
    )
    accepted = next(e for e in history.events[-2:] if e.outcome is Outcome.ACCEPTED)
    refused = next(e for e in history.events[-2:] if e.outcome is Outcome.REFUSED)
    assert refused.reason is Reason.COMMITTED
    assert accepted.key in refused.causes
    assert len(history.state.bonds) == 3
    validate_history(history)


def test_submission_needs_a_recorded_defeat_or_threat_and_a_lord_of_real_scale() -> None:
    ordinary = Society(authority=Authority.RULER)
    history = court(
        {
            "small": (1000, 500, 0, True),
            "peer": (1100, 600, 0, False),
            "lord": (10_000, 5000, 4, False),
        },
        dict.fromkeys(("small", "peer", "lord"), ordinary),
    )
    refused = advance(history, (Proposal(Action.DEPENDENCY, "small", "lord"),))
    assert refused.events[-1].reason is Reason.THREAT
    peer = advance(history, (Proposal(Action.DEPENDENCY, "small", "peer"),))
    assert peer.events[-1].reason is Reason.IMBALANCE
    history = defeat(history, "lord", "small")
    accepted = advance(history, (Proposal(Action.DEPENDENCY, "small", "lord"),))
    event = accepted.events[-1]
    assert event.outcome is Outcome.ACCEPTED
    conquest = next(e for e in accepted.events if e.kind is Action.CONFLICT)
    assert conquest.key in Context(history, lambda: None).actor_causes("small") or any(
        cause == conquest.key for cause in event.causes
    )
    validate_history(accepted)


def test_independence_follows_the_lords_defeat_elsewhere() -> None:
    ordinary = Society(authority=Authority.RULER)
    history = court(
        {
            "small": (1000, 500, 0, True),
            "rival": (40_000, 20_000, 3, False),
            "lord": (10_000, 5000, 2, False),
        },
        dict.fromkeys(("small", "rival", "lord"), ordinary),
    )
    history = defeat(history, "lord", "small")
    history = advance(history, (Proposal(Action.DEPENDENCY, "small", "lord"),))
    assert Context(history, lambda: None).lords == {"small": "lord"}
    loyal = advance(history, (Proposal(Action.INDEPENDENCE, "small", "lord"),))
    assert loyal.events[-1].reason is Reason.OBLIGATIONS
    # The rival takes one of the lord's own districts: a recorded setback.
    beaten = advance(history, (Proposal(Action.CONFLICT, "rival", "lord", ("lord_1",)),))
    setback = beaten.events[-1]
    assert setback.outcome is Outcome.ACCEPTED
    free = advance(beaten, (Proposal(Action.INDEPENDENCE, "small", "lord"),))
    event = free.events[-1]
    assert event.outcome is Outcome.ACCEPTED
    assert event.reason is Reason.AUTONOMY
    assert setback.key in event.causes
    assert not Context(free, lambda: None).lords
    assert event.effects.ended[0].first == "small"
    validate_history(free)
    resubmission = advance(free, (Proposal(Action.DEPENDENCY, "small", "lord"),))
    assert resubmission.events[-1].reason is Reason.THREAT
    # A fresh failed attack is a new defeat, so it can cause a later submission.
    defeated = advance(resubmission, (Proposal(Action.CONFLICT, "small", "lord", ("lord_2",)),))
    assert defeated.events[-1].outcome is Outcome.FAILED
    submitted = advance(defeated, (Proposal(Action.DEPENDENCY, "small", "lord"),))
    assert submitted.events[-1].outcome is Outcome.ACCEPTED
    validate_history(submitted)
