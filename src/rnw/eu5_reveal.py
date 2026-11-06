"""The optional reveal of the whole generated New World at the start of a campaign (W6).

A multiplayer table that wants every player to see the New World from the first day turns the
world setting ``new_world.reveal_at_start`` on. The world then writes one file that hooks the
game's own start the way the installation's ``ai_personalities_setup.txt`` does (a mod that
defines ``on_game_start`` with an ``effect`` of its own stops the game's start, C200; a
sub-on-action beside it runs, C206): every country discovers every area of the New World
through the vanilla ``discover_area`` effect. No vanilla country record is edited, and a world
made with the setting off has no such file.

The areas are read from the ``definitions.txt`` the world writes, not from the generator's own
plan: the reveal covers the areas the game will see under the New World's continent, land and
sea. The installed ``discovered_any_in_americas_trigger`` is rebound to the generated sea areas
(``eu5_content.rebind_discovery``), so once they are discovered it is true for every country on
the first day. ``exploration_monthly.38`` ("Old World discovers New World") would then fire for
the first Old World country that sends out an exploration, with a reward for it and a notice to
every human player in range. The vanilla event is gated by its own flag, so the start effect
sets that flag, ``new_world_discovered``, which the event sets itself when it fires (C499).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from rnw.eu5_canvas import NEW_WORLD
from rnw.geography import parse_locations
from rnw.pdx import Block, parse

if TYPE_CHECKING:
    from collections.abc import Sequence

REVEAL_FILE: Final[str] = "in_game/common/on_action/rnw_reveal.txt"
HOOK: Final[str] = "on_game_start"
ACTION: Final[str] = "rnw_reveal_new_world"
# The global variable the vanilla event "Old World discovers New World" tests and sets.
DISCOVERED: Final[str] = "new_world_discovered"
HEADER: Final[str] = (
    "# Written by Random New World for the setting 'Reveal the New World at the start'.\n"
    "# Every country discovers every area of the generated New World when a campaign begins.\n"
)


class RevealError(ValueError):
    """A reveal that cannot be written, or a written one that does not say what it should."""


def new_world_areas(definitions: str) -> list[str]:
    """The areas under the New World's continent in ``definitions.txt``, land and sea, sorted."""
    areas = sorted(
        {
            location.area
            for location in parse_locations(definitions)
            if location.continent == NEW_WORLD
        }
    )
    if not areas:
        message = f"definitions.txt has no area under the continent {NEW_WORLD}"
        raise RevealError(message)
    return areas


def script(areas: Sequence[str]) -> str:
    """The on_action file: the hook on the game's start and the effect it runs."""
    lines = [
        HEADER,
        f"{HOOK} = {{\n\ton_actions = {{ {ACTION} }}\n}}\n",
        f"\n{ACTION} = {{\n\teffect = {{\n",
        # The flag of the vanilla event that announces the discovery (see the module's note).
        f"\t\tset_global_variable = {DISCOVERED}\n",
        "\t\tevery_country = {\n",
        *(f"\t\t\tdiscover_area = area:{area}\n" for area in areas),
        "\t\t}\n\t}\n}\n",
    ]
    return "".join(lines)


def files(definitions: str) -> dict[str, bytes]:
    """The reveal's file for a world whose ``definitions.txt`` is ``definitions``."""
    return {REVEAL_FILE: script(new_world_areas(definitions)).encode("utf-8-sig")}


def _entries(block: Block | None) -> list[str | None]:
    return [] if block is None else [entry.key for entry in block.entries]


def verify(written: dict[str, bytes], definitions: str) -> dict[str, object]:
    """Check the reveal file as written against the written ``definitions.txt``.

    The file hooks the game's start through ``on_actions`` and never defines an ``effect`` of
    ``on_game_start`` itself, sets the vanilla flag, and has every country discover exactly the
    areas under the New World's continent, each once.
    """
    data = written.get(REVEAL_FILE)
    if data is None:
        message = f"{REVEAL_FILE} is not among the written files"
        raise RevealError(message)
    root = parse(data.decode("utf-8-sig"))
    hook = root.block(HOOK)
    if _entries(root) != [HOOK, ACTION] or _entries(hook) != ["on_actions"]:
        message = f"{REVEAL_FILE} must define {HOOK} with on_actions only, and {ACTION}"
        raise RevealError(message)
    hooked = hook.block("on_actions") if hook is not None else None
    if hooked is None or [entry.value for entry in hooked.words()] != [ACTION]:
        message = f"{REVEAL_FILE}: {HOOK} must only run the on_action {ACTION}"
        raise RevealError(message)
    action = root.block(ACTION)
    effect = action.block("effect") if action is not None else None
    if _entries(action) != ["effect"] or _entries(effect) != [
        "set_global_variable",
        "every_country",
    ]:
        message = f"{REVEAL_FILE}: {ACTION} must set {DISCOVERED} and visit every country"
        raise RevealError(message)
    assert effect is not None  # noqa: S101 - narrowed by the check above
    flag = effect.first("set_global_variable")
    countries = effect.block("every_country")
    if flag is None or flag.value != DISCOVERED or countries is None:
        message = f"{REVEAL_FILE}: the effect must set the global variable {DISCOVERED}"
        raise RevealError(message)
    if any(entry.key != "discover_area" for entry in countries.entries):
        message = f"{REVEAL_FILE}: every_country may only discover areas"
        raise RevealError(message)
    discovered = [
        entry.value.removeprefix("area:") if isinstance(entry.value, str) else ""
        for entry in countries.entries
    ]
    wanted = new_world_areas(definitions)
    if sorted(discovered) != wanted:
        missing = sorted(set(wanted) - set(discovered))
        extra = sorted(set(discovered) - set(wanted))
        message = (
            f"{REVEAL_FILE} does not discover exactly the New World's areas: "
            f"{len(missing)} missing (first {missing[:3]}), {len(extra)} extra (first {extra[:3]})"
        )
        raise RevealError(message)
    return {"reveal_areas": len(wanted)}
