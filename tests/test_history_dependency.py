"""Client admissions consume real administrative capacity, including ancestor rulers."""

from __future__ import annotations

from rnw.history_context import Context
from rnw.history_engine import advance, create, validate_history
from rnw.history_model import (
    Action,
    Authority,
    Cohort,
    District,
    Founding,
    Geography,
    History,
    Outcome,
    Proposal,
    Reason,
    Route,
    Rules,
    Society,
    Tenure,
)


def _world(populations: dict[str, tuple[int, int]], profiles: dict[str, Society]) -> History:
    keys = sorted(populations)
    geography = Geography(
        tuple(
            District(key, "plain", Tenure.LAND, (Cohort("culture", "faith", *populations[key]),))
            for key in keys
        ),
        tuple(Route(first, second) for i, first in enumerate(keys) for second in keys[i + 1 :]),
        rules=Rules(minimum_peasants=338, minimum_share=122),
    )
    history = create(
        geography,
        tuple(
            Founding(
                key,
                Tenure.LAND,
                (key,),
                key,
                technology=2,
                authority=profiles[key].authority,
                society=profiles[key],
            )
            for key in keys
        ),
        seed=42,
        empire_permille=0,
    )
    contacts = tuple(
        Proposal(Action.CONTACT, first, second)
        for i, first in enumerate(keys)
        for second in keys[i + 1 :]
    )
    for start in range(0, len(contacts), 3):
        history = advance(history, contacts[start : start + 3])
    return history


def test_joint_admissions_cannot_spend_the_same_administrative_capacity_twice() -> None:
    ordinary = Society(authority=Authority.RULER)
    history = _world(
        {"a": (1000, 500), "b": (1000, 500), "lord": (10_000, 5000)},
        {
            "a": ordinary,
            "b": ordinary,
            "lord": Society(centralization=200, integration=200, authority=Authority.RULER),
        },
    )
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
    ordinary = Society(authority=Authority.RULER)
    return _world(
        {"leaf": (500, 338), "middle": (1200, 900), "root": (40_000, 20_000)},
        {
            "leaf": ordinary,
            "middle": ordinary,
            "root": ordinary
            if capable_root
            else Society(centralization=100, integration=100, authority=Authority.RULER),
        },
    )


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
    history = _world(
        {
            "b": (3000, 2000),
            "c": (3000, 2000),
            "d": (1000, 500),
            "e": (1000, 500),
            "root": (70_000, 35_000),
        },
        {
            **dict.fromkeys(("b", "c", "d", "e"), ordinary),
            "root": Society(centralization=100, integration=250, authority=Authority.RULER),
        },
    )
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
