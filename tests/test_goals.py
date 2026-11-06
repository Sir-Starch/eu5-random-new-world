"""The AI's goals of the formables (history plan §22, N8): who pursues what, and N-C4."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.content import (
    CULTURAL_UNION,
    GREAT_LAW,
    HIGHLAND_CONFEDERATION,
    NEW_WORLD_EMPIRE,
    REGIONAL_REALM,
    RESTORATION,
    RIVER_UNION,
    TWO_WORLDS,
    Formation,
)
from rnw.eu5_formation import geographies, geography
from rnw.eu5_goals import (
    SCORE_FILE,
    TARGET_FILE,
    GoalError,
    check_installation,
    files,
    goal,
    pursued,
)
from rnw.pdx import parse

if TYPE_CHECKING:
    from pathlib import Path

FORMATIONS = (
    Formation(HIGHLAND_CONFEDERATION, 0, ("a", "b"), ("a",), ("ABC",), "a"),
    Formation(RIVER_UNION, 0, ("a", "b"), ("a",), ("ABC", "DEF"), "a"),
    Formation(CULTURAL_UNION, 0, ("c", "d"), ("c",), ("ABC",), "c", basis="tupi_group"),
    Formation(REGIONAL_REALM, 0, ("a", "b"), ("a",), ("ABC",), "a", region="r", throne="a"),
    Formation(NEW_WORLD_EMPIRE, 0, ("a", "b"), (), (), "a", continent="america"),
    Formation(RESTORATION, 0, ("a", "b"), ("a",), ("ABC", "DEF"), "a", "old"),
    Formation(TWO_WORLDS, 0, ("a", "b"), (), (), "a", continent="america"),
    Formation(GREAT_LAW, 0, ("a", "b"), (), ("ABC", "DEF", "GHI"), "a"),
)


def test_the_ai_pursues_the_goals_of_level_three_shown_by_default() -> None:
    """Not a duchy-level league or confederation, nor the fantasy empire, nor a goal over the
    whole continent such as the crown of two worlds."""
    assert [f.family for f in FORMATIONS if pursued(f)] == [
        RIVER_UNION,
        CULTURAL_UNION,
        REGIONAL_REALM,
        RESTORATION,
        GREAT_LAW,
    ]
    assert files(FORMATIONS[:1]) == {}


def test_every_goal_names_only_written_territories_and_the_formables_own_rules() -> None:
    """N-C4: each entry asks its formable's own potential, a written geography and an age; the
    target list and the weighting read the same territory."""
    written = files(FORMATIONS)
    territories = parse(geographies(FORMATIONS))
    for path in (TARGET_FILE, SCORE_FILE):
        root = parse(written[path])
        keys = [entry.key for entry in root.entries]
        assert keys == [goal(f) for f in FORMATIONS if pursued(f)]
        for formation in (f for f in FORMATIONS if pursued(f)):
            entry = root.block(goal(formation))
            assert entry is not None
            assert territories.block(geography(formation)) is not None
            text = written[path]
            assert f"scripted_geography:{geography(formation)}" in text
            attacker = entry.block("attacker_potential")
            assert attacker is not None
            age = attacker.block("current_age_or_later")
            assert age is not None
            first = age.first("age")
            assert first is not None
            expected = (
                "age_3_discovery" if formation.family == REGIONAL_REALM else "age_2_renaissance"
            )
            assert first.value == expected
    targets = parse(written[TARGET_FILE]).block(goal(FORMATIONS[2]))
    assert targets is not None
    assert "culture_group:tupi_group" in written[TARGET_FILE]
    heirs = parse(written[SCORE_FILE]).block(goal(FORMATIONS[5]), "attacker_potential", "OR")
    assert heirs is not None
    assert [item.value for item in heirs.find("has_or_had_tag")] == ["ABC", "DEF"]
    multiplier = parse(written[SCORE_FILE]).block(goal(FORMATIONS[1]))
    assert multiplier is not None
    found = multiplier.first("multiplier")
    assert found is not None
    assert float(found.value) > 1 if isinstance(found.value, str) else False


def test_an_age_or_personality_the_game_lacks_stops_the_export(tmp_path: Path) -> None:
    """The ages and the isolationist personality are checked against the installation."""
    ages = tmp_path / "game/in_game/common/age/00_default.txt"
    ages.parent.mkdir(parents=True)
    _ = ages.write_text("age_2_renaissance = {\n}\nage_3_discovery = {\n}\n", encoding="utf-8")
    personalities = tmp_path / "game/in_game/common/ai_personalities/00_default.txt"
    personalities.parent.mkdir(parents=True)
    _ = personalities.write_text("ai_isolationist = {\n}\n", encoding="utf-8")
    check_installation(tmp_path)
    _ = ages.write_text("age_2_renaissance = {\n}\n", encoding="utf-8")
    with pytest.raises(GoalError, match="age_3_discovery"):
        check_installation(tmp_path)
