"""How a world is called: in the game's mod list, in the generator's window and on its picture.

One function builds each name, so the window and the game agree (ADR 0010). A world is
``<Type> <TAG>`` unless the player names it; the game's list shows it behind ``RNW: ``, at most
``MAX_TITLE`` characters, and a covered world carries its tag in the middle of its picture, since
every covered New World looks alike (``rnw.pictures``). The tag is four characters of the world's
id, so the same world has the same tag on every machine.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from typing import Final

from rnw.settings import TITLES

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


def display_name(preset: str, tag: str, name: str = "") -> str:
    """The name the window shows: the player's, else the type and the tag."""
    return clean_name(name) or f"{TITLES.get(preset, preset)} {tag}"


def label(preset: str, tag: str, name: str = "") -> Label:
    """The title the game's list shows, and the tag, for a world."""
    return Label(f"{GAME_PREFIX}{display_name(preset, tag, name)}", tag)
