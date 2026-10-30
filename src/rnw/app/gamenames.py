"""The game's own names of its identifiers, in one of its languages, for the window's maps.

The atlas of a world names cultures, religions, raw materials, climates, vegetation and
topography by the game's identifiers (``abipones_culture``, ``goods_gold``). When the game is
installed, the window shows the game's own name of each in the window's language, read from the
game's localization; without the game it shows the identifier made readable (``atlas.pretty``).

Russian and Polish culture names are stems that the game's texts complete (``Абипонск``,
``Achaguańs``, C272); the window completes them as an adjective of *culture* (``Абипонская``,
``Achaguańska``). Read only; nothing is written.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path

LOCALIZATION: Final[str] = "game/main_menu/localization"
ENTRY: Final[re.Pattern[str]] = re.compile(
    r'^[ \t]*([^\s:#"]+):\d*[ \t]*"(.*)"[ \t]*$', re.MULTILINE
)
# A text with scripted parts, references or formatting is not a plain name.
SCRIPTED: Final[re.Pattern[str]] = re.compile(r"[\[\]$#@]")
STEMS: Final[dict[str, tuple[tuple[str, ...], str]]] = {
    "russian": (("ск", "цк"), "ая"),
    "polish": (("ńs", "ws", "js", "ck"), "ka"),
}


def _complete(language: str, key: str, name: str) -> str:
    endings, ending = STEMS.get(language, ((), ""))
    if key.endswith("_culture") and name.endswith(endings):
        return name + ending
    return name


@lru_cache(maxsize=2)
def _read(game_dir: Path, language: str) -> dict[str, str]:
    """Read one catalogue for all worlds, rather than rereading it for each set of keys."""
    found: dict[str, str] = {}
    folder = game_dir / LOCALIZATION / language
    for path in sorted(folder.rglob(f"*_l_{language}.yml")):
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        pairs: list[tuple[str, str]] = ENTRY.findall(text)
        for key, value in pairs:
            if key not in found and value and not SCRIPTED.search(value):
                found[key] = _complete(language, key, value)
    return found


def game_names(game_dir: Path, language: str, keys: frozenset[str]) -> dict[str, str]:
    """The game's names of ``keys`` in ``language``; keys it has no plain name for are left out."""
    found = _read(game_dir, language)
    return {key: found[key] for key in keys if key in found}
