"""The story graphs: every node reached, every branch ended, nothing left behind (no game)."""

from __future__ import annotations

import re

import pytest

from rnw.pdx import Block, parse
from rnw.stories import (
    AFFORD,
    CLEANUP,
    STORIES,
    Story,
    event_keys,
    outcomes,
    reachable,
    render_events,
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
            removes = {f"remove_variable = {v}" for v in (story.centre, story.path)}
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
            assert f"var:{story.centre}" in scopes, (effect, scopes)
    assert found.get("remove_location_modifier") or found.get("add_location_modifier")


def test_the_stories_name_no_tag_and_no_location() -> None:
    """The templates are the same in every world: only the start events know a place."""
    for story in STORIES:
        script = render_events(story)
        assert not re.search(r"\blocation:", script)
        assert not re.search(r"\b(tag|c:)\s*=?\s*[A-Z]{3}\b", script)


def test_the_paths_of_each_story_are_the_ones_designed() -> None:
    """The river story has three first choices, each with its own ending; so has the sacred one."""
    river, sacred = STORIES
    assert sorted(outcomes(river)) == [
        ("1a", "2a"), ("1a", "2b"), ("1b", "3a"), ("1b", "3b"), ("1c", "4a"), ("1c", "4b"),
    ]  # fmt: skip
    assert len(outcomes(sacred)) == 6
