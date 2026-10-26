"""Generated AI personalities follow country strength, ties and strategic archetypes."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from rnw.eu5_ai import (
    AiPersonalityError,
    CountryContext,
    assignments,
    decide,
    lines,
    vanilla_profiles,
    verify,
)
from rnw.eu5_rewrite import insert_into_block

if TYPE_CHECKING:
    from pathlib import Path


PROFILES = (
    "ai_aggressive",
    "ai_balanced",
    "ai_cautious",
    "ai_defensive",
    "ai_expansionist",
    "ai_friendly",
    "ai_isolationist",
    "ai_opportunistic",
)


def _game_files(root: Path, setup: str, definitions: str) -> None:
    setup_path = root / "game/main_menu/setup/1337/26_ai_personalities.txt"
    definitions_path = root / "game/in_game/common/ai_personalities/00_profiles.txt"
    _ = setup_path.parent.mkdir(parents=True)
    _ = definitions_path.parent.mkdir(parents=True)
    _ = setup_path.write_text(setup, encoding="utf-8")
    _ = definitions_path.write_text(definitions, encoding="utf-8")


def _context(
    tag: str,
    power: int = 100,
    *,
    landed: bool = True,
    **changes: object,
) -> CountryContext:
    return replace(
        CountryContext(
            tag=tag,
            landed=landed,
            great=False,
            archetype="",
            level=1,
            population=power,
            power=power,
            coastal=False,
            market=False,
        ),
        **changes,
    )


def test_vanilla_profiles_are_read_from_setup_and_require_definitions(tmp_path: Path) -> None:
    setup = "countries = { countries = { AAA = { ai_personality = ai_aggressive } } }"
    _game_files(
        tmp_path,
        setup,
        "ai_balanced = { default = yes }\nai_aggressive = { }",
    )

    assert vanilla_profiles(tmp_path) == ("ai_aggressive", "ai_balanced")


def test_vanilla_profiles_reject_an_undefined_personality(tmp_path: Path) -> None:
    _game_files(
        tmp_path,
        "countries = { countries = { AAA = { ai_personality = ai_missing } } }",
        "ai_balanced = { default = yes }",
    )

    with pytest.raises(AiPersonalityError, match="undefined AI personality"):
        _ = vanilla_profiles(tmp_path)


def test_balanced_is_the_baseline_and_strong_signals_override_it() -> None:
    contexts = (
        _context("EMPR", 300, great=True, neighbors=("WEAK",), prey_targets=("WEAK",)),
        _context("WEAK", 100, neighbors=("EMPR",), threatened_by=("EMPR",)),
        _context("SIEG", 100, threatened_by=("EMPR", "RICH")),
        _context("RICH", 300, neighbors=("RIVAL",), rivals=("RIVAL",)),
        _context("RIVAL", 215, neighbors=("RICH",), rivals=("RICH",)),
        _context("SEA", 100, archetype="sea_league"),
        _context("HIGH", 100, archetype="highland_confederation", confederated=True),
        _context("SACR", 100, archetype="sacred_centre"),
        _context("ALLY", 100, neighbors=("MATE",), allies=("MATE",)),
        _context("MATE", 300, neighbors=("ALLY",), allies=("ALLY",)),
        _context("PROT", 100, allies=("MATE",), threatened_by=("MATE",)),
        _context("LONE", 100),
        _context("PORT", 100, coastal=True, market=True),
        _context("COAST", 100, coastal=True),
        _context("OVER", 100, neighbors=("EMPR",)),
        _context("BORD", 100, neighbors=("PEER",)),
        _context("PEER", 100, neighbors=("BORD",)),
        _context("POP", 500, landed=False),
    )

    first = decide(contexts, PROFILES)
    second = decide(tuple(reversed(contexts)), PROFILES)

    assert first == second
    by_tag = {decision.tag: decision for decision in first}
    assert len(by_tag) == len(contexts) - 1
    assert by_tag["EMPR"].profile == "ai_expansionist"
    assert by_tag["WEAK"].profile == "ai_defensive"
    assert by_tag["SIEG"].profile == "ai_cautious"
    assert by_tag["RICH"].profile == "ai_aggressive"
    assert by_tag["RIVAL"].profile == "ai_defensive"
    assert by_tag["SEA"].profile == "ai_opportunistic"
    assert by_tag["HIGH"].profile == "ai_friendly"
    assert by_tag["SACR"].profile == "ai_defensive"
    assert by_tag["ALLY"].profile == "ai_friendly"
    assert by_tag["PROT"].profile == "ai_friendly"
    assert by_tag["LONE"].profile == "ai_balanced"
    assert by_tag["PORT"].profile == "ai_opportunistic"
    assert by_tag["COAST"].profile == "ai_balanced"
    assert by_tag["OVER"].profile == "ai_balanced"
    assert by_tag["BORD"].profile == "ai_balanced"
    assert by_tag["BORD"].reason == (
        "no strong strategic signal; keep the vanilla Balanced baseline"
    )


def test_missing_required_profile_fails_loudly() -> None:
    error = "needs unavailable AI personality ai_expansionist"
    with pytest.raises(AiPersonalityError, match=error):
        _ = decide(
            (
                _context("EMPR", 300, great=True, neighbors=("WEAK",), prey_targets=("WEAK",)),
                _context("WEAK", 100, neighbors=("EMPR",)),
            ),
            ("ai_balanced",),
        )


def test_unknown_rival_and_nonpositive_power_fail_loudly() -> None:
    with pytest.raises(AiPersonalityError, match="unknown generated country"):
        _ = decide((_context("AAA", rivals=("MISSING",)),), PROFILES)
    with pytest.raises(AiPersonalityError, match="must be positive"):
        _ = decide((_context("AAA", 0),), PROFILES)


def test_rendered_assignments_survive_the_merged_setup() -> None:
    setup = "countries = {\n\tcountries = {\n\t\tVAN = { ai_personality = ai_aggressive }\n\t}\n}\n"
    decisions = decide(
        (_context("RNW", allies=("RNY",)), _context("RNY", allies=("RNW",))), PROFILES
    )
    records = assignments(decisions)
    with pytest.raises(AiPersonalityError, match="setup mismatch"):
        verify(setup, records)

    merged = insert_into_block(setup, ("countries", "countries"), lines(records))

    verify(merged, records)

    with pytest.raises(AiPersonalityError, match="setup mismatch"):
        verify(merged.replace("ai_friendly", "ai_aggressive"), records)
