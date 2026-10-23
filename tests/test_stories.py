"""The story graphs: every node reached, every branch ended, nothing left behind (no game)."""

from __future__ import annotations

import re

import pytest

from rnw.pdx import Block, parse
from rnw.stories import STORIES
from rnw.storymodel import (
    AFFORD,
    CLEANUP,
    LOCATION,
    PULSE_START,
    Story,
    event_keys,
    outcomes,
    pulse_action,
    reachable,
    render_events,
    render_hook,
)


@pytest.fixture(params=STORIES, ids=[story.family for story in STORIES])
def story(request: pytest.FixtureRequest) -> Story:
    """Each story in turn."""
    return request.param  # pyright: ignore[reportAny]


def test_every_node_is_reached_from_the_first_and_every_follow_exists(story: Story) -> None:
    """No orphan node, no follow-up to an event that does not exist."""
    numbers = {node.number for node in story.nodes}
    assert reachable(story) == numbers
    for node in story.nodes:
        for option in node.options:
            if option.follow is not None:
                assert option.follow.node in numbers
                assert option.follow.node > node.number  # a story only goes forward: no loop
                low, high = option.follow.months
                assert 0 < low <= high


def test_every_path_ends_and_ending_clears_the_variables(story: Story) -> None:
    """Options without a follow-up remove the story's variables; the others keep them."""
    assert outcomes(story)
    for node in story.nodes:
        for option in node.options:
            removes = {f"remove_variable = {v}" for v in story.variables()}
            ends = removes <= set(option.effects)
            assert ends == (option.follow is None), (node.number, option.key)


def test_each_branch_sets_the_path_its_next_node_requires(story: Story) -> None:
    """Following an option leads to the node whose trigger asks for the value it set."""
    by_number = {node.number: node for node in story.nodes}
    for node in story.nodes:
        for option in node.options:
            if option.follow is None:
                continue
            values = [
                int(match.group(1))
                for effect in option.effects
                if (
                    match := re.fullmatch(
                        rf"set_variable = \{{ name = {story.path} value = (\d+) \}}", effect
                    )
                )
            ]
            assert len(values) == 1
            requires = " ".join(by_number[option.follow.node].requires)
            assert f"var:{story.path} >= {values[0]}" in requires
            assert f"var:{story.path} <= {values[0]}" in requires


def test_nothing_is_offered_that_cannot_be_paid_for(story: Story) -> None:
    """Options that cost gold are offered only to a state that has some."""
    for node in story.nodes:
        for option in node.options:
            costs = any(
                re.fullmatch(r"change_gold_effect = \{ scale = -\d+ \}", effect)
                for effect in option.effects
            )
            assert costs == (option.trigger == AFFORD), (node.number, option.key)


def test_every_option_has_an_ai_weight_and_every_node_a_free_choice(story: Story) -> None:
    """The AI can always choose, and at least one option needs no gold."""
    for node in story.nodes:
        assert all(option.ai > 0 for option in node.options)
        assert any(option.trigger != AFFORD for option in node.options)
        assert len(node.options) >= 2


def test_the_script_reads_and_names_each_event_once(story: Story) -> None:
    """The generated events parse; there is one per node and the hidden cleanup."""
    root = parse(render_events(story))
    keys = [entry.key for entry in root.entries if entry.key and isinstance(entry.value, Block)]
    expected = [story.event(node.number) for node in story.nodes] + [story.event(CLEANUP)]
    if story.pulse is not None:
        expected.append(story.event(PULSE_START))
    assert keys == expected


def test_every_text_and_name_the_script_uses_is_localized(story: Story) -> None:
    """Titles, descriptions, options, modifiers and privileges all have their English text."""
    keys = event_keys(story)
    script = render_events(story)
    for node in story.nodes:
        base = story.event(node.number)
        assert f"{base}.title" in keys
        assert f"{base}.desc" in keys
        assert all(f"{base}.{option.key}" in keys for option in node.options)
    for modifier in story.modifiers:
        assert f"STATIC_MODIFIER_NAME_{modifier.name}" in keys
        assert f"STATIC_MODIFIER_DESC_{modifier.name}" in keys
    used = set(re.findall(r"modifier = (rnw_\w+)", script)) | set(
        re.findall(r"remove_(?:location|country)_modifier = (rnw_\w+)", script)
    )
    assert used <= {modifier.name for modifier in story.modifiers}
    assert {modifier.name for modifier in story.modifiers} <= used
    assert all('"' not in text for text in keys.values())


def _scopes_of(
    block: Block, scopes: tuple[str, ...], found: dict[str, list[tuple[str, ...]]]
) -> None:
    for entry in block.entries:
        if entry.key is None:
            continue
        found.setdefault(entry.key, []).append(scopes)
        if isinstance(entry.value, Block):
            _scopes_of(entry.value, (*scopes, entry.key), found)


def test_location_modifiers_are_changed_in_the_scope_of_the_centre(story: Story) -> None:
    """Events run in the country's scope, so a location modifier is added or removed inside
    ``var:<centre> ?= { }`` (the engine reported ``remove_location_modifier: Inconsistent effect
    scopes (country vs. location)`` for a bare one, EU5 1.4.4, experiment 036)."""
    found: dict[str, list[tuple[str, ...]]] = {}
    _scopes_of(parse(render_events(story)), (), found)
    for effect in ("add_location_modifier", "remove_location_modifier"):
        for scopes in found.get(effect, []):
            assert f"var:{story.centre}" in scopes or (
                story.other and f"var:{story.other}" in scopes
            ), (effect, scopes)
    if any(modifier.category == LOCATION for modifier in story.modifiers):
        assert found.get("remove_location_modifier") or found.get("add_location_modifier")
    # a country modifier on another country is applied inside the owner of the place's scope
    for scopes in found.get("add_country_modifier", []):
        assert not any(scope.startswith("var:") for scope in scopes) or "owner" in scopes, scopes


def test_the_stories_name_no_tag_and_no_location() -> None:
    """The templates are the same in every world: only the start events know a place."""
    for story in STORIES:
        script = render_events(story)
        assert not re.search(r"\blocation:", script)
        assert not re.search(r"\b(tag|c:)\s*=?\s*[A-Z]{3}\b", script)


def test_the_paths_of_each_story_are_the_ones_designed() -> None:
    """Every story has three first choices, each with its own endings."""
    by_family = {story.family: story for story in STORIES}
    river, sacred = by_family["river_centre"], by_family["sacred_centre"]
    assert sorted(outcomes(river)) == [
        ("1a", "2a"), ("1a", "2b"), ("1b", "3a"), ("1b", "3b"), ("1c", "4a"), ("1c", "4b"),
    ]  # fmt: skip
    assert len(outcomes(sacred)) == 6
    for family in (
        "harvest",
        "route_market",
        "great_alliance",
        "empire_periphery",
        "contact",
        "colony",
    ):
        assert len(outcomes(by_family[family])) == 6, family


PULSE_STORIES = [story for story in STORIES if story.pulse is not None]


def test_the_stories_that_find_their_bearers_in_play_are_contact_and_colony() -> None:
    """Two stories have no bearer at the start; each is in the New World only."""
    assert {story.family for story in PULSE_STORIES} == {"contact", "colony"}
    for story in PULSE_STORIES:
        assert story.pulse is not None
        assert "capital.continent = continent:america" in story.pulse.trigger
        assert 0 < story.pulse.chance <= 10
        assert story.pulse.quiet_years >= 30
    by_family = {story.family: story for story in PULSE_STORIES}
    colony, contact = by_family["colony"], by_family["contact"]
    assert colony.pulse is not None
    assert contact.pulse is not None
    assert "is_subject_type = colonial_nation" in colony.pulse.trigger
    # strangers meet natives that are no colony and have a port, and have met someone from abroad
    assert "NOT = { is_subject_type = colonial_nation }" in contact.pulse.trigger
    assert "culture ?= { is_culture_native_american = yes }" in contact.pulse.trigger
    assert "num_of_ports > 0" in contact.pulse.trigger
    assert any("capital_in_old_world_trigger" in line for line in contact.pulse.trigger)


@pytest.mark.parametrize("story", PULSE_STORIES, ids=[story.family for story in PULSE_STORIES])
def test_a_pulse_start_binds_the_places_and_cannot_start_a_story_twice(story: Story) -> None:
    """The hidden start stores both places, marks the country, and asks for no story under way."""
    assert story.pulse is not None
    root = parse(render_events(story))
    start = root.block(story.event(PULSE_START))
    assert start is not None
    text = render_events(story)
    section = text[text.index(f"{story.event(PULSE_START)} = {{") :]
    assert "hidden = yes" in section
    assert f"NOT = {{ has_variable = {story.path} }}" in section
    assert f"NOT = {{ has_variable = {story.quiet()} }}" in section
    assert f"set_variable = {{ name = {story.centre} value = scope:home_place }}" in section
    assert f"set_variable = {{ name = {story.other} value = scope:seat_place }}" in section
    assert (
        f"set_variable = {{ name = {story.quiet()} years = {story.pulse.quiet_years} }}" in section
    )
    # the cleanup is scheduled, and the first node is fired after the places are stored
    assert section.index("seat_place") < section.index(f"id = {story.event(story.nodes[0].number)}")
    assert f"id = {story.event(CLEANUP)}" in section
    # a pulse story has no place in a start event of the world
    assert "location:" not in text


def test_the_hook_offers_each_pulse_story_to_every_country_each_year() -> None:
    """One sub-on-action per story in the game's yearly pulse, with the story's chance."""
    hook = render_hook(STORIES)
    root = parse(hook)
    pulse = root.block("yearly_country_pulse")
    assert pulse is not None
    listed = pulse.block("on_actions")
    assert listed is not None
    assert [w.value for w in listed.words()] == [pulse_action(s) for s in PULSE_STORIES]
    for story in PULSE_STORIES:
        action = root.block(pulse_action(story))
        assert action is not None
        events = action.block("random_events")
        assert events is not None
        assert story.pulse is not None
        chance = events.first("chance_to_happen")
        assert chance is not None
        assert chance.value == str(story.pulse.chance)
        assert f"100 = {story.event(PULSE_START)}" in hook
    assert render_hook([s for s in STORIES if s.pulse is None]) == (
        "yearly_country_pulse = {\n\ton_actions = {\n\t}\n}\n"
    )
