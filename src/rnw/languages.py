"""The game's official languages, read from the installation (owner, 2026-10-23).

The mod and the generator use exactly the languages the game ships localization for, never a
fixed list: a language that a patch adds is picked up, and one it removes is dropped. The
languages are the folders of ``main_menu/localization`` that hold localization files named for
them (``*_l_<language>.yml``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path

LOCALIZATION: Final[str] = "game/main_menu/localization"
# The language authored text is written in; the others carry it until they are translated.
SOURCE: Final[str] = "english"


class LanguageError(ValueError):
    """An installation whose languages cannot be read."""


def official_languages(game_dir: Path) -> tuple[str, ...]:
    """The languages of the installation in name order; English must be among them."""
    root = game_dir / LOCALIZATION
    if not root.is_dir():
        message = f"No localization folder at {root}"
        raise LanguageError(message)
    languages = tuple(
        folder.name
        for folder in sorted(root.iterdir())
        if folder.is_dir() and next(folder.rglob(f"*_l_{folder.name}.yml"), None) is not None
    )
    if SOURCE not in languages:
        message = f"The installation has no {SOURCE} localization (found: {', '.join(languages)})"
        raise LanguageError(message)
    return languages
