"""How a world is called: in the game's mod list, in the generator's window and on its picture.

One function builds each name, so the window and the game agree (ADR 0010). A world is
``<Type> <TAG>`` (Total Chaos for a draw, Custom world for manual settings) unless the player
names it; the game's list shows it behind ``RNW: ``, at most
``MAX_TITLE`` characters, and a covered world carries its tag in the middle of its picture, since
every covered New World looks alike (``rnw.pictures``). The tag is four characters of the world's
id, so the same world has the same tag on every machine.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final

from rnw.settings import PRESETS, TITLES

if TYPE_CHECKING:
    from rnw.settings import Settings

GAME_PREFIX: Final[str] = "RNW: "
MAX_TITLE: Final[int] = 30
MAX_NAME: Final[int] = MAX_TITLE - len(GAME_PREFIX)
TAG_LENGTH: Final[int] = 4


@dataclass(frozen=True, slots=True)
class Label:
    """What the game's mod list shows of a world: the title, and the tag for a covered picture."""

    title: str
    tag: str


def tag_of(world_id: str) -> str:
    """The tag of a world: the first characters of its id, in capitals."""
    return world_id[:TAG_LENGTH].upper()


def fallback_tag(source: str) -> str:
    """A tag for an export made without the library (the command line): from ``source``'s hash."""
    digest = hashlib.sha256(source.encode("utf-8")).digest()
    return base64.b32encode(digest).decode("ascii")[:TAG_LENGTH]


def clean_name(name: str) -> str:
    """The player's name as it is kept: one line, spaces collapsed, cut to ``MAX_NAME``."""
    return " ".join(name.split())[:MAX_NAME].rstrip()


def display_name(
    preset: str, tag: str, name: str = "", *, settings: Settings | None = None, origin: str = ""
) -> str:
    """The player's name, else the preset or Custom world and the tag.

    A preset describes its own geography, not the arbitrary settings Total Chaos or the
    player can put over it. Peoples, resources and visibility do not change that description.
    Metadata titles stay English (localization §2.9).
    """
    title = TITLES.get(preset, preset)
    if origin == "chaos":
        title = "Total Chaos"
    elif origin in {"custom", "chaos_custom"}:
        title = "Custom world"
    elif settings is not None and preset in PRESETS:
        base = PRESETS[preset].new_world
        shape = replace(
            settings.new_world,
            precious_permille=base.precious_permille,
            reveal_at_start=base.reveal_at_start,
        )
        if settings.mask.id or shape != base:
            title = "Custom world"
    return clean_name(name) or f"{title} {tag}"


def label(
    preset: str, tag: str, name: str = "", *, settings: Settings | None = None, origin: str = ""
) -> Label:
    """The title the game's list shows, and the tag, for a world."""
    return Label(
        f"{GAME_PREFIX}{display_name(preset, tag, name, settings=settings, origin=origin)}", tag
    )
