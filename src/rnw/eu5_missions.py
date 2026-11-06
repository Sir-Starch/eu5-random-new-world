"""Missions on the road to a formable (history plan §22.4): hold its seat, gather its land, form it.

Vanilla offers a country missions from ``common/missions`` (``____Info.txt``: a mission with
``visible``, ``enabled``, ``abort`` and ``chance``, and tasks with ``requires``, ``enabled``,
``final`` and ``on_completion``); ``generic_conquer_province`` is the model. A world offers one
mission for each formable smaller than the continent, *Road to X*, visible to a country that could
form it with its capital in the territory: hold the seat (a realm's throne), then half of the
places the formation asks for (``any_location_in_scripted_geography`` with ``count``, over the
formation's own scripted geography), then proclaim it. Someone else proclaiming it aborts the
mission. The rewards are vanilla values. How often the game draws these missions among its own is
[UNKNOWN].
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.eu5_formation import geography, potential
from rnw.formations import BY_FAMILY, ROAD
from rnw.game_texts import Described, Text

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from rnw.content import Formation
    from rnw.eu5_formation import Identity
    from rnw.game_texts import Entry
    from rnw.loc_keys import KeySpace
    from rnw.wording import Phrase

MISSIONS_FILE: Final[str] = "in_game/common/missions/rnw_roads.txt"
ILLUSTRATION: Final[str] = "generic_conquer_province"
ICONS: Final[dict[str, str]] = {
    "seat": "expansionism",
    "land": "offensive_army",
    "proclaim": "a_magnanimous_empire",
}
CHANCE: Final[int] = 2000


ILLUSTRATIONS_DIR: Final[str] = "game/main_menu/gfx/interface/illustrations/missions"
ICONS_DIR: Final[str] = "game/main_menu/gfx/interface/advance"


class MissionError(ValueError):
    """A picture that the missions lean on is gone from the installation."""


def check_installation(game_dir: Path) -> None:
    """Raise unless the mission's illustration and the tasks' icons are in the installation."""
    pictures = [
        game_dir / ILLUSTRATIONS_DIR / f"{ILLUSTRATION}.dds",
        *(game_dir / ICONS_DIR / f"{icon}.dds" for icon in ICONS.values()),
    ]
    for picture in pictures:
        if not picture.is_file():
            message = f"The picture {picture.name} of the missions is gone from the installation"
            raise MissionError(message)


@dataclass(frozen=True, slots=True)
class Road:
    """The mission of one formation: its number, the formable's tag and name, its seat and the
    places a founder must hold to be half way."""

    base: str
    formation: Formation
    tag: str
    name: Phrase
    half: int


def offered(formation: Formation) -> bool:
    """A mission for each formable smaller than the continent."""
    return not formation.continent


# The keys of a mission besides its own: its description and its tasks with theirs.
SUFFIXES: Final[tuple[str, ...]] = tuple(
    f"{part}{end}" for part in ("", "_seat", "_land", "_proclaim") for end in ("", "_desc")
)


def roads(
    formations: Sequence[Formation],
    identities: Sequence[Identity],
    keys: KeySpace | None = None,
) -> list[Road]:
    """The missions of a world, in the order of its formations.

    ``keys`` hands out each mission's keys together, so that none shares the engine's hash
    with another; without it they are numbered in order.
    """
    found: list[Road] = []
    for formation, identity in zip(formations, identities, strict=True):
        if not offered(formation):
            continue
        base = f"{ROAD}_{len(found) + 1}" if keys is None else keys.group(f"{ROAD}_", SUFFIXES)
        need = float(BY_FAMILY[formation.family].fraction) * len(formation.places)
        found.append(
            Road(base, formation, identity.tag, identity.name, max(1, math.ceil(need / 2)))
        )
    return found


def key(road: Road) -> str:
    return road.base


def _lines(lines: Sequence[str], depth: int) -> str:
    return "".join("\t" * depth + line + "\n" for line in lines)


def _task(  # noqa: PLR0913 - a task is its mission, its part, its order, its goal and reward.
    road: Road, part: str, requires: str, enabled: str, reward: str, *, final: bool
) -> list[str]:
    return [
        f"{key(road)}_{part} = {{",
        f"\ticon = {ICONS[part]}",
        *([f"\trequires = {{ {key(road)}_{requires} }}"] if requires else []),
        *(["\tfinal = yes"] if final else []),
        f"\tenabled = {{ {enabled} }}",
        "\tduration = 0",
        f"\ton_completion = {{ {reward} }}",
        "}",
    ]


def missions(found: Sequence[Road]) -> str:
    """The script of the missions."""
    out: list[str] = []
    for road in found:
        formation, tag = road.formation, road.tag
        territory = f"scripted_geography:{geography(formation)}"
        seat = formation.throne or formation.seat
        gathered = (
            f"{territory} = {{ any_location_in_scripted_geography = "
            f"{{ count >= {road.half} owner ?= root }} }}"
        )
        lines = [
            f"{key(road)} = {{",
            f"\ticon = {ILLUSTRATION}",
            "\trepeatable = no",
            "\tplayer_playstyle = military",
            "\tvisible = {",
            "\t\tgame_has_missions_enabled = yes",
            f"\t\tcapital ?= {{ is_in_scripted_geography = {territory} }}",
            *(f"\t\t{line}" for line in potential(formation)),
            "\t}",
            "\tenabled = { }",
            f"\tabort = {{ country_exists = c:{tag} NOT = {{ tag = {tag} }} }}",
            f"\tchance = {CHANCE}",
            "",
            *(
                f"\t{line}"
                for line in _task(
                    road,
                    "seat",
                    "",
                    f"owns = location:{seat}",
                    "add_prestige = prestige_weak_bonus",
                    final=False,
                )
            ),
            *(
                f"\t{line}"
                for line in _task(
                    road,
                    "land",
                    "seat",
                    gathered,
                    "add_stability = stability_weak_bonus",
                    final=False,
                )
            ),
            *(
                f"\t{line}"
                for line in _task(
                    road,
                    "proclaim",
                    "land",
                    f"tag = {tag}",
                    "add_prestige = prestige_weak_bonus",
                    final=True,
                )
            ),
            "}",
        ]
        out.append(_lines(lines, 0))
    return "\n".join(out)


def texts(found: Sequence[Road]) -> dict[str, Entry]:
    """The missions' and tasks' names and descriptions, the formable's name filled in."""
    entries: dict[str, Entry] = {}
    for road in found:
        name = road.name
        mission = key(road)
        entries[mission] = _described("name", name)
        entries[f"{mission}_desc"] = _described("desc", name)
        for part in ("seat", "land"):
            entries[f"{mission}_{part}"] = Text(f"{ROAD}.{part}")
            entries[f"{mission}_{part}_desc"] = Text(f"{ROAD}.{part}_desc")
        entries[f"{mission}_proclaim"] = Text(f"{ROAD}.proclaim")
        entries[f"{mission}_proclaim_desc"] = _described("proclaim_desc", name)
    return entries


def _described(part: str, name: Phrase) -> Entry:
    return Described(f"{ROAD}.{part}", name)
