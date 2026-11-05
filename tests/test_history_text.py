"""Causal, bounded prose and voluntary EU5 history output, using synthetic worlds."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from rnw import eu5_history_text, game_texts, history_text
from rnw.eu5_history_plan import project_start
from rnw.history_engine import advance, create
from rnw.history_model import (
    Action,
    Authority,
    Cohort,
    Exchange,
    HistoryError,
    Movement,
    Outcome,
    Proposal,
    TrajectoryKind,
)
from rnw.history_output_checks import verify_text
from rnw.loc_keys import KeySpace, key_hashes
from rnw.pdx import Block, parse
from rnw.translations import catalog_languages

from .history_fixtures import divided_valley
from .test_history import _line  # pyright: ignore[reportPrivateUsage]
from .test_history_plan import inputs_for, quiet, realized_network
from .test_history_societies import _neighbours, _prepared  # pyright: ignore[reportPrivateUsage]

if TYPE_CHECKING:
    from rnw.eu5_start import FinalStartPlan


@pytest.fixture
def plan() -> FinalStartPlan:
    return project_start(inputs_for(divided_valley()))


def write(plan: FinalStartPlan) -> eu5_history_text.WrittenHistory:
    written = eu5_history_text.build(plan, KeySpace(key_hashes(plan.names)))
    verify_text(plan, written)
    return written


def scalar(block: Block, key: str) -> str:
    entry = block.first(key)
    assert entry is not None
    assert isinstance(entry.value, str)
    return entry.value


def test_written_biases_match_causal_setup_records(plan: FinalStartPlan) -> None:
    written = write(plan)
    biases = parse(written.files[eu5_history_text.BIAS_FILE].decode("utf-8-sig"))
    assert {entry.key for entry in biases.entries} == {o.key for o in plan.historical_opinions}
    assert plan.historical_opinions
    assert plan.history is not None
    for opinion in plan.historical_opinions:
        block = biases.block(opinion.key)
        assert block is not None
        assert len(block.entries) == 2
        assert scalar(block, "value") == str(opinion.value)
        assert scalar(block, "yearly_decay") == str(opinion.yearly_decay)
        english = game_texts.localize({opinion.key: written.texts[opinion.key]}, "english")
        assert str(opinion.year) in english[opinion.key]
        if opinion.place:
            assert str(plan.names[opinion.place]) in english[opinion.key]


def test_decision_is_repeatable_free_voluntary_and_generated_only(plan: FinalStartPlan) -> None:
    written = write(plan)
    decision = parse(written.files[eu5_history_text.DECISION_FILE].decode("utf-8-sig"))
    block = decision.block(eu5_history_text.DECISION)
    assert block is not None
    assert len(decision.entries) == 1
    assert block.first("only_once") is None
    ai = block.block("ai_will_do")
    assert ai is not None
    assert scalar(ai, "value") == "0"
    potential = block.block("potential")
    assert potential is not None
    assert scalar(potential, eu5_history_text.TRIGGER) == "yes"
    effect = block.block("option", "effect")
    assert effect is not None
    assert len(effect.entries) == 1
    assert scalar(effect, "trigger_event_non_silently") == eu5_history_text.EVENT
    trigger = parse(written.files[eu5_history_text.TRIGGER_FILE].decode("utf-8-sig"))
    countries = trigger.block(eu5_history_text.TRIGGER, "OR")
    assert countries is not None
    assert {entry.value for entry in countries.entries if isinstance(entry.value, str)} == {
        c.tag for c in plan.countries
    }
    assert all(entry.key == "tag" for entry in countries.entries)
    assert not any("on_action" in path or "setup" in path for path in written.files)


def test_one_event_selects_every_living_country_without_dead_scopes(plan: FinalStartPlan) -> None:
    written = write(plan)
    event = parse(written.files[eu5_history_text.EVENT_FILE].decode("utf-8-sig"))
    assert {entry.key for entry in event.entries} == {"namespace", eu5_history_text.EVENT}
    descriptions = event.block(eu5_history_text.EVENT, "desc", "first_valid")
    assert descriptions is not None
    selected: dict[str, str] = {}
    for entry in descriptions.entries:
        assert entry.key == "triggered_desc"
        assert isinstance(entry.value, Block)
        gate = entry.value.block("trigger")
        assert gate is not None
        selected[scalar(gate, "tag")] = scalar(entry.value, "desc")
    assert selected == written.chronicles
    assert set(selected) == {country.tag for country in plan.countries}
    for key in selected.values():
        assert key in written.texts


def test_chronicles_select_real_events_and_include_extinct_predecessors(
    plan: FinalStartPlan,
) -> None:
    assert plan.history is not None
    events = {event.key: event for event in plan.history.events}
    chronicles = history_text.chronicles(plan)
    assert set(chronicles) == {c.tag for c in plan.countries}
    assert any(
        row.family is Action.UNION for chronicle in chronicles.values() for row in chronicle.rows
    )
    for chronicle in chronicles.values():
        assert 1 <= len(chronicle.rows) <= 8
        assert len({row.event for row in chronicle.rows}) == len(chronicle.rows)
        assert list(chronicle.rows) == sorted(chronicle.rows, key=lambda row: (row.year, row.event))
        for row in chronicle.rows:
            event = events[row.event]
            assert event.outcome is not Outcome.REFUSED
            assert row.family is event.kind
            assert row.year == event.year
            assert row.family is not Action.TRAJECTORY
            assert 1 <= len(row.actors) <= 3


def test_quiet_history_does_not_invent_events_or_a_foundation_date(plan: FinalStartPlan) -> None:
    assert plan.history is not None
    history = plan.history
    quiet_plan = project_start(
        inputs_for(quiet(create(history.geography, history.foundings, seed=history.seed)))
    )
    chronicles = history_text.chronicles(quiet_plan)
    assert all(len(chronicle.rows) == 1 for chronicle in chronicles.values())
    english = game_texts.localize(dict(chronicles), "english")
    assert all("1037" in text and "record" in text for text in english.values())
    assert all("found" not in text.lower() for text in english.values())


@pytest.mark.parametrize("language", catalog_languages())
def test_all_world_history_text_renders_without_tokens(plan: FinalStartPlan, language: str) -> None:
    written = write(plan)
    texts = game_texts.localize(written.texts, language)
    assert all(text and "{" not in text and "}" not in text for text in texts.values())
    assert all('"' not in text and "\n" not in text for text in texts.values())
    assert all("\\n\\n" in texts[written.chronicles[c.tag]] for c in plan.countries)
    if language != "english":
        assert texts[eu5_history_text.DECISION] != "Our History"


def test_all_family_variants_render_with_names_in_every_language() -> None:
    for family, variants in history_text.TEMPLATES.items():
        for variant, _ in enumerate(variants):
            source = f"rnw_history_{family}_{variant}"
            for language in catalog_languages():
                sentence = history_text.Sentence(
                    source,
                    (("year", 1282), ("first", "Kaira"), ("second", "Tlaco"), ("third", "Yara")),
                )
                text = game_texts.localize({"row": sentence}, language)["row"]
                assert "1282" in text
                assert "{" not in text


def test_cause_text_rejects_another_event(plan: FinalStartPlan) -> None:
    assert plan.history is not None
    with pytest.raises(HistoryError, match="differs from its cause"):
        _ = history_text.opinion_text(
            plan.historical_opinions[0], plan.names, plan.history.events[0]
        )


def test_localization_and_output_do_not_depend_on_input_order(plan: FinalStartPlan) -> None:
    assert plan.history is not None
    other = replace(
        plan,
        countries=tuple(reversed(plan.countries)),
        history_tags=dict(reversed(tuple(plan.history_tags.items()))),
        history=replace(plan.history, events=tuple(reversed(plan.history.events))),
    )
    first, second = write(plan), write(other)
    assert first.files == second.files
    assert first.texts == second.texts
    assert game_texts.localize(first.texts, "russian") == game_texts.localize(
        second.texts, "russian"
    )


def test_empty_world_has_no_empty_or_trigger_or_unreachable_decision(plan: FinalStartPlan) -> None:
    assert plan.history is not None
    empty = project_start(
        inputs_for(
            quiet(create(replace(plan.history.geography, districts=(), routes=()), (), seed=3))
        )
    )
    written = write(empty)
    assert set(written.files) == {eu5_history_text.BIAS_FILE}
    assert not written.texts


def test_population_tribes_get_their_own_chronicles() -> None:
    plan = project_start(
        inputs_for(realized_network(TrajectoryKind.HIGHLAND_CONFEDERATION, chance=0))
    )
    assert any(country.kind == "tribe" and not country.landed for country in plan.countries)
    written = write(plan)
    assert set(written.chronicles) == {country.tag for country in plan.countries}


def test_guarantee_setup_keeps_provider_direction() -> None:
    text = "diplomacy_manager = {\n" + eu5_history_text.guarantee_lines((("AAA", "BBB"),)) + "}"
    relation = parse(text).block("diplomacy_manager", "scripted_oneway")
    assert relation is not None
    assert (scalar(relation, "first"), scalar(relation, "second"), scalar(relation, "type")) == (
        "AAA",
        "BBB",
        "guarantee",
    )


def test_new_chronicle_keys_skip_taken_localization_hashes(plan: FinalStartPlan) -> None:
    keys = KeySpace(key_hashes(("rnw_chronicle_1", "rnw_chronicle_2")))
    written = eu5_history_text.build(plan, keys)
    assert not set(written.chronicles.values()) & {"rnw_chronicle_1", "rnw_chronicle_2"}
    with pytest.raises(HistoryError, match="interface keys collide"):
        _ = eu5_history_text.build(plan, KeySpace(key_hashes(("rnw_our_history",))))


def test_repulsed_attack_never_claims_an_annexation() -> None:
    root = _line(count=2)
    places = tuple(
        replace(place, defence=100_000 if place.key == "0" else 1000)
        for place in root.geography.districts
    )
    history = create(replace(root.geography, districts=places), root.foundings, seed=42)
    history = advance(history, (Proposal(Action.CONTACT, "a0", "a1"),))
    history = advance(history, (Proposal(Action.CONFLICT, "a1", "a0", ("0",)),))
    event = history.events[-1]
    assert event.outcome is Outcome.FAILED
    plan = project_start(inputs_for(quiet(history)))
    rows = [row for chronicle in history_text.chronicles(plan).values() for row in chronicle.rows]
    failed = [row for row in rows if row.event == event.key]
    assert failed
    assert all(row.text.source.startswith("rnw_history_repelled_") for row in failed)
    text = game_texts.localize({"row": failed[0].text}, "english")["row"]
    assert "attack" in text
    assert "annex" not in text
    assert "conquer" not in text


def test_migration_keeps_source_and_destination_order() -> None:
    history = advance(_neighbours(), (Proposal(Action.CONTACT, "a", "b"),))
    history = advance(
        history,
        (
            Proposal(
                Action.MIGRATION,
                "a",
                "b",
                movement=Movement("a", "b", Cohort("a", "faith_a", 100, 50)),
            ),
        ),
    )
    event = history.events[-1]
    assert event.outcome is Outcome.ACCEPTED
    plan = project_start(inputs_for(quiet(history)))
    row = next(
        row
        for chronicle in history_text.chronicles(plan).values()
        for row in chronicle.rows
        if row.event == event.key
    )
    fields = dict(row.text.fields)
    assert fields["first"] == plan.names["a"]
    assert fields["second"] == plan.names["b"]


def test_resisted_reform_is_not_described_as_a_change() -> None:
    history = _prepared(seed=3, tradition=1000)
    profile = history.state.actors[0].society
    history = advance(
        history,
        (Proposal(Action.REFORM, "a", reform=replace(profile, exchange=Exchange.COASTAL)),),
    )
    event = history.events[-1]
    assert event.outcome is Outcome.FAILED
    plan = project_start(inputs_for(quiet(history)))
    rows = [row for chronicle in history_text.chronicles(plan).values() for row in chronicle.rows]
    # D27: an attempt that changed nothing stays in the record, not in the chronicle.
    assert not [row for row in rows if row.event == event.key]
    assert all(not row.text.source.startswith("rnw_history_reform_") for row in rows)


def test_only_a_change_of_authority_enters_the_chronicle() -> None:
    history = _prepared(seed=0, pressure=True)
    profile = history.state.actors[0].society
    changed = advance(
        history,
        (Proposal(Action.REFORM, "a", reform=replace(profile, authority=Authority.RULER)),),
    )
    event = changed.events[-1]
    assert event.outcome is Outcome.ACCEPTED
    plan = project_start(inputs_for(quiet(changed)))
    rows = [row for chronicle in history_text.chronicles(plan).values() for row in chronicle.rows]
    assert any(
        row.event == event.key and row.text.source.startswith("rnw_history_reform_") for row in rows
    )


def test_refused_proposal_has_no_chronicle_entry() -> None:
    history = _neighbours()
    profile = history.state.actors[0].society
    history = advance(
        history,
        (Proposal(Action.REFORM, "a", reform=replace(profile, authority=Authority.COUNCIL)),),
    )
    event = history.events[-1]
    assert event.outcome is Outcome.REFUSED
    plan = project_start(inputs_for(quiet(history)))
    assert all(
        row.event != event.key
        for chronicle in history_text.chronicles(plan).values()
        for row in chronicle.rows
    )


@pytest.mark.parametrize(
    ("path", "before", "after"),
    [
        (eu5_history_text.BIAS_FILE, "yearly_decay =", "yearly_decay >"),
        (eu5_history_text.BIAS_FILE, "value =", "unplanned_value ="),
        (eu5_history_text.DECISION_FILE, "value = 0", "value = 100"),
        (
            eu5_history_text.DECISION_FILE,
            "decision_category =",
            "only_once = yes\n decision_category =",
        ),
        (eu5_history_text.DECISION_FILE, "effect = {", "effect = { add_gold = 10"),
        (eu5_history_text.DECISION_FILE, "allow = { always = yes }", "allow = { always = no }"),
        (eu5_history_text.EVENT_FILE, "type = country_event", "type = location_event"),
        (eu5_history_text.EVENT_FILE, "desc = rnw_chronicle_", "desc = unbound_chronicle_"),
        (eu5_history_text.TRIGGER_FILE, "tag =", "old_tag ="),
        (eu5_history_text.EVENT_FILE, "option = {", "immediate = { add_gold = 10 } option = {"),
    ],
)
def test_written_output_check_rejects_changed_scopes_effects_or_values(
    plan: FinalStartPlan, path: str, before: str, after: str
) -> None:
    written = write(plan)
    original = written.files[path].decode("utf-8-sig")
    changed = original.replace(before, after, 1)
    assert changed != original
    files = {**written.files, path: changed.encode("utf-8-sig")}
    with pytest.raises(HistoryError):
        verify_text(plan, replace(written, files=files))


def test_written_output_check_rejects_startup_hooks_and_missing_translation_keys(
    plan: FinalStartPlan,
) -> None:
    written = write(plan)
    with pytest.raises(HistoryError, match="startup hooks"):
        verify_text(
            plan,
            replace(written, files={**written.files, "in_game/common/on_action/start.txt": b""}),
        )
    texts = dict(written.texts)
    del texts[next(iter(written.chronicles.values()))]
    with pytest.raises(HistoryError, match="localization"):
        verify_text(plan, replace(written, texts=texts))
