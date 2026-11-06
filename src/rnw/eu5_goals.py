"""The AI's goals: the formables a country may form become its wars' targets (history plan §22, N8).

Vanilla weighs the wars its AI considers through ``ai_scripted_expansion_target`` (which adds the
countries a script lists to the candidates) and ``ai_scripted_expansion_score`` (which multiplies
the score of a target a trigger picks); ``attack_neighbors`` and ``castile_spares_christian_iberia``
are its precedents. For every formable of level 3 and above that the game shows by default and
that is smaller than the continent, a country that could form it, its capital in the territory,
at peace for five years and no isolationist, considers every neighbour holding land of the
territory, scored as half of ``attack_neighbors``, and weighs such a neighbour half again as high
as it would. A realm waits for
the age of discovery, the others for the second age. The territory is the formation's own
``scripted_geography`` (``eu5_formation.geography``).

Declaring war on an ally is not an AI choice the engine offers, so allies need no ``never_attack``
[INFERRED]; how far the AI pursues these goals over a campaign is [UNKNOWN] and not observed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from rnw.content import REGIONAL_REALM
from rnw.eu5_formation import geography, key_of, potential
from rnw.formations import BY_FAMILY

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from rnw.content import Formation

TARGET_FILE: Final[str] = "in_game/common/ai_scripted_expansion_target/rnw_formations.txt"
SCORE_FILE: Final[str] = "in_game/common/ai_scripted_expansion_score/rnw_formations.txt"
AGES_DIR: Final[str] = "game/in_game/common/age"
PERSONALITIES_DIR: Final[str] = "game/in_game/common/ai_personalities"
LOWEST_LEVEL: Final[int] = 3
PEACE_MONTHS: Final[int] = 60
# Half of ``attack_neighbors`` (``multiply = 10``) for the added candidates; half again for every
# holder of the territory the AI weighs anyway.
SCORE: Final[int] = 5
MULTIPLIER: Final[str] = "1.5"
SECOND_AGE: Final[str] = "age_2_renaissance"
AGES: Final[dict[str, str]] = {REGIONAL_REALM: "age_3_discovery"}
ISOLATIONIST: Final[str] = "ai_isolationist"


class GoalError(ValueError):
    """An age or an AI personality that the goals lean on is gone from the installation."""


def check_installation(game_dir: Path) -> None:
    """Raise unless the ages and the AI personality the goals name are defined."""
    defined = {
        line.split("=")[0].strip()
        for directory in (AGES_DIR, PERSONALITIES_DIR)
        for path in sorted((game_dir / directory).glob("*.txt"))
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if "=" in line and not line.startswith(("\t", " "))
    }
    for needed in (SECOND_AGE, *AGES.values(), ISOLATIONIST):
        if needed not in defined:
            message = f"The {needed} that the AI's goals lean on is gone from the game"
            raise GoalError(message)


def pursued(formation: Formation) -> bool:
    """Whether the AI pursues a formation: level 3 and above, shown by the default game rule, and
    smaller than a continent (a goal over the whole continent would weigh every neighbour)."""
    spec = BY_FAMILY[formation.family]
    return spec.level >= LOWEST_LEVEL and spec.rule == "plausible" and not formation.continent


def goal(formation: Formation) -> str:
    """The key of a formation's AI entries."""
    return f"rnw_goal_{key_of(formation)}"


def _lines(lines: Sequence[str], depth: int) -> str:
    return "".join("\t" * depth + line + "\n" for line in lines)


def _attacker(formation: Formation) -> str:
    """Who pursues the formation: whoever could form it, at peace and no isolationist."""
    age = AGES.get(formation.family, SECOND_AGE)
    lines = [
        f"current_age_or_later = {{ age = {age} }}",
        f"ai_personality != ai_personality:{ISOLATIONIST}",
        f"months_since_war >= {PEACE_MONTHS}",
        f"capital ?= {{ is_in_scripted_geography = scripted_geography:{geography(formation)} }}",
        *potential(formation),
    ]
    return f"\tattacker_potential = {{\n{_lines(lines, 2)}\t}}\n"


def _holds(formation: Formation) -> str:
    return f"owns_or_has_subject_in = scripted_geography:{geography(formation)}"


def targets(formations: Sequence[Formation]) -> str:
    """The neighbours that hold land of a formation's territory, as targets of its pursuer."""
    out: list[str] = []
    for formation in formations:
        if not pursued(formation):
            continue
        body = [
            "candidate_list = {",
            "\tevery_neighbor_country = {",
            f"\t\tlimit = {{ {_holds(formation)} }}",
            "\t\tadd_to_list = source",
            "\t}",
            "}",
            "score = {",
            "\tadd = scope:target.country_tax_base",
            '\tdivide = "scope:target.capital.distance_to(scope:attacker.capital)"',
            f"\tmultiply = {SCORE}",
            "}",
        ]
        out.append(f"{goal(formation)} = {{\n{_attacker(formation)}{_lines(body, 1)}}}\n")
    return "\n".join(out)


def scores(formations: Sequence[Formation]) -> str:
    """Every holder of a formation's territory weighs higher as a target of its pursuer."""
    out: list[str] = []
    for formation in formations:
        if not pursued(formation):
            continue
        body = ["target_trigger = {", f"\t{_holds(formation)}", "}", f"multiplier = {MULTIPLIER}"]
        out.append(f"{goal(formation)} = {{\n{_attacker(formation)}{_lines(body, 1)}}}\n")
    return "\n".join(out)


def files(formations: Sequence[Formation]) -> dict[str, str]:
    """The AI's goal files, if any formation is pursued."""
    if not any(pursued(formation) for formation in formations):
        return {}
    return {TARGET_FILE: targets(formations), SCORE_FILE: scores(formations)}
