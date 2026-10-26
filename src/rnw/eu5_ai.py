"""Contextual, explainable EU5 AI-personality choices from generated societies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.pdx import Block, parse

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

AI_SETUP: Final[str] = "game/main_menu/setup/1337/26_ai_personalities.txt"
AI_DEFINITIONS: Final[str] = "game/in_game/common/ai_personalities"
PERSONALITIES: Final[str] = "26_ai_personalities.txt"

Assignments = tuple[tuple[str, str], ...]
THREAT_MARGIN: Final[int] = 120
AGGRESSION_MARGIN: Final[int] = 135
MAJOR_THREAT_MARGIN: Final[int] = 150
MULTIPLE_THREATS: Final[int] = 2


class AiPersonalityError(ValueError):
    """The installed AI-personality data cannot safely drive a generated setup."""


@dataclass(frozen=True, slots=True)
class CountryContext:
    """Generated facts that can justify one country's strategic AI bias.

    ``power`` is a comparative proxy formed from generated population and technology level,
    not an estimate of the game's full military strength.
    """

    tag: str
    landed: bool
    great: bool
    archetype: str
    level: int
    population: int
    power: int
    coastal: bool
    market: bool
    neighbors: tuple[str, ...] = ()
    allies: tuple[str, ...] = ()
    rivals: tuple[str, ...] = ()
    threatened_by: tuple[str, ...] = ()
    prey_targets: tuple[str, ...] = ()
    subjects: tuple[str, ...] = ()
    overlord: str = ""
    confederated: bool = False


@dataclass(frozen=True, slots=True)
class AiDecision:
    """The selected profile and the rule that explains it."""

    tag: str
    profile: str
    reason: str
    context: CountryContext


def vanilla_profiles(game_dir: Path) -> tuple[str, ...]:
    """Read installed assignments and include the profile marked as the vanilla default."""
    setup = (game_dir / AI_SETUP).read_text(encoding="utf-8-sig")
    files = sorted((game_dir / AI_DEFINITIONS).glob("*.txt"))
    if not files:
        message = f"No AI-personality definitions under {AI_DEFINITIONS}"
        raise AiPersonalityError(message)
    definitions = {
        entry.key: entry.value
        for path in files
        for entry in parse(path.read_text(encoding="utf-8-sig")).entries
        if entry.key is not None and isinstance(entry.value, Block)
    }
    root = parse(setup).block("countries", "countries")
    if root is None:
        message = f"{AI_SETUP} has no countries/countries block"
        raise AiPersonalityError(message)

    profiles: set[str] = set()
    for entry in root.entries:
        if not isinstance(entry.value, Block):
            continue
        value = entry.value.first("ai_personality")
        if value is None:
            continue
        if not isinstance(value.value, str) or value.value not in definitions:
            profile = value.value if isinstance(value.value, str) else "<non-text>"
            message = f"{AI_SETUP}: {entry.key} names undefined AI personality {profile}"
            raise AiPersonalityError(message)
        profiles.add(value.value)

    defaults = {
        name
        for name, definition in definitions.items()
        if (default := definition.first("default")) is not None and default.value == "yes"
    }
    if len(defaults) > 1:
        message = f"{AI_DEFINITIONS} defines multiple default AI personalities"
        raise AiPersonalityError(message)
    profiles.update(defaults)
    if not profiles:
        message = f"{AI_SETUP} contains no explicit AI-personality assignments"
        raise AiPersonalityError(message)
    return tuple(sorted(profiles))


def _relative_power(own: int, other: int, *, margin: int = THREAT_MARGIN) -> bool:
    """Whether ``own`` is at least ``margin`` percent of the compared country's proxy."""
    return own * 100 >= other * margin


def _power_of(powers: Mapping[str, int], tag: str) -> int:
    try:
        return powers[tag]
    except KeyError as error:
        message = f"AI-personality context refers to unknown generated country {tag}"
        raise AiPersonalityError(message) from error


def _threat_choice(context: CountryContext) -> tuple[str, str] | None:
    protected = set(context.allies) | set(context.subjects)
    if context.overlord:
        protected.add(context.overlord)
    threats = set(context.threatened_by) - protected
    if len(threats) >= MULTIPLE_THREATS:
        return "ai_cautious", "several countries explicitly target this state"
    if threats:
        return "ai_defensive", "a great empire explicitly targets this neighboring state"
    return None


def _empire_choice(
    context: CountryContext, powers: Mapping[str, int], independent: set[str]
) -> tuple[str, str] | None:
    if not context.great:
        return None
    prey = set(context.prey_targets) & independent
    if prey and any(_relative_power(context.power, _power_of(powers, target)) for target in prey):
        return "ai_expansionist", "great empire with a weaker designated prey"
    return None


def _rival_choice(context: CountryContext, powers: Mapping[str, int]) -> tuple[str, str] | None:
    rival_strengths = [_power_of(powers, rival) for rival in context.rivals]
    if not rival_strengths:
        return None
    strongest = max(rival_strengths)
    if _relative_power(context.power, strongest, margin=AGGRESSION_MARGIN):
        return "ai_aggressive", "stronger than a declared rival"
    if not _relative_power(context.power, strongest):
        if strongest * 100 >= context.power * MAJOR_THREAT_MARGIN:
            return "ai_cautious", "a declared rival is much stronger"
        return "ai_defensive", "a declared rival is stronger"
    return "ai_opportunistic", "rival power is close enough to favor maneuver"


def _archetype_choice(context: CountryContext) -> tuple[str, str] | None:
    if context.archetype == "sea_league":
        return "ai_opportunistic", "sea league with maritime or market interests"
    if context.archetype == "highland_confederation":
        return (
            ("ai_friendly", "highland confederation with internal bonds")
            if context.confederated
            else ("ai_defensive", "highland confederation built around defensible terrain")
        )
    if context.archetype == "sacred_centre":
        return (
            ("ai_friendly", "sacred centre supported by diplomatic ties")
            if context.allies or context.confederated
            else ("ai_defensive", "sacred centre prioritizing stability and cohesion")
        )
    return {
        "fractured_realm": (
            "ai_defensive",
            "fractured realm without a stronger rival to challenge",
        )
    }.get(context.archetype)


def _general_choice(
    context: CountryContext, powers: Mapping[str, int], independent: set[str]
) -> tuple[str, str]:
    targets = set(context.prey_targets) & independent
    if targets and any(
        _relative_power(context.power, _power_of(powers, target), margin=AGGRESSION_MARGIN)
        for target in targets
    ):
        return "ai_expansionist", "stronger than a designated conquest target"
    if context.allies or context.confederated:
        return "ai_friendly", "formal alliances or confederation ties"
    if context.overlord:
        return "ai_cautious", "subject country with a stronger overlord"
    if context.market and context.coastal:
        return "ai_opportunistic", "a coastal state with an established market"
    return "ai_balanced", "no strong strategic signal; keep the vanilla Balanced baseline"


def _choose(context: CountryContext, powers: Mapping[str, int]) -> tuple[str, str]:
    """Use Balanced as the baseline; override it only for a clear strategic signal."""
    linked = set(context.allies)
    independent = set(context.neighbors) - linked - set(context.subjects)
    if context.overlord:
        independent.discard(context.overlord)

    if (choice := _threat_choice(context)) is not None:
        return choice
    if (choice := _empire_choice(context, powers, independent)) is not None:
        return choice
    if (choice := _rival_choice(context, powers)) is not None:
        return choice
    if (choice := _archetype_choice(context)) is not None:
        return choice

    return _general_choice(context, powers, independent)


def decide(contexts: Sequence[CountryContext], profiles: Sequence[str]) -> tuple[AiDecision, ...]:
    """Classify landed countries from shared world context and explain every selection."""
    available = set(profiles)
    tags = [context.tag for context in contexts if context.landed]
    if len(set(tags)) != len(tags):
        message = "Generated AI-country tags are not unique"
        raise AiPersonalityError(message)

    by_tag = {context.tag: context for context in contexts if context.landed}
    if any(context.power < 1 for context in by_tag.values()):
        message = "Generated AI-country power proxies must be positive"
        raise AiPersonalityError(message)
    powers = {tag: max(1, context.power) for tag, context in by_tag.items()}
    for context in by_tag.values():
        related = (
            *context.neighbors,
            *context.allies,
            *context.rivals,
            *context.threatened_by,
            *context.prey_targets,
            *context.subjects,
            *((context.overlord,) if context.overlord else ()),
        )
        for tag in related:
            _ = _power_of(powers, tag)
    decisions: list[AiDecision] = []
    for context in sorted(by_tag.values(), key=lambda item: item.tag):
        profile, reason = _choose(context, powers)
        if profile not in available:
            message = f"Generated country {context.tag} needs unavailable AI personality {profile}"
            raise AiPersonalityError(message)
        decisions.append(AiDecision(context.tag, profile, reason, context))
    return tuple(decisions)


def assignments(decisions: Sequence[AiDecision]) -> Assignments:
    """Drop the audit explanation when rendering the game's setup records."""
    return tuple((decision.tag, decision.profile) for decision in decisions)


def lines(assignments: Assignments) -> str:
    """Render records for the vanilla ``countries/countries`` setup block."""
    if not assignments:
        return ""
    output = ["\n\t\t# RNW generated New World AI personalities\n"]
    output.extend(f"\t\t{tag} = {{ ai_personality = {profile} }}\n" for tag, profile in assignments)
    return "".join(output)


def verify(text: str, assignments: Assignments) -> None:
    """Fail if the final merged setup does not retain every generated assignment."""
    root = parse(text).block("countries", "countries")
    if root is None:
        message = f"{AI_SETUP} has no countries/countries block after export"
        raise AiPersonalityError(message)
    expected = dict(assignments)
    seen: dict[str, str] = {}
    for entry in root.entries:
        if entry.key not in expected:
            continue
        if entry.key in seen:
            message = f"{AI_SETUP}: generated country {entry.key} has duplicate assignments"
            raise AiPersonalityError(message)
        if not isinstance(entry.value, Block):
            seen[entry.key] = "<missing>"
            continue
        value = entry.value.first("ai_personality")
        seen[entry.key] = (
            value.value if value is not None and isinstance(value.value, str) else "<missing>"
        )
    if seen != expected:
        missing = sorted(set(expected) - set(seen))
        wrong = sorted(tag for tag in seen.keys() & expected.keys() if seen[tag] != expected[tag])
        message = f"AI-personality setup mismatch (missing={missing}, wrong={wrong})"
        raise AiPersonalityError(message)
