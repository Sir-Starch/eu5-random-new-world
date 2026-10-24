"""Replace map names in their installed localization files, with no duplicate definitions."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pathlib import Path

MAP_NAMES: Final[tuple[str, ...]] = (
    "area",
    "region_names",
    "location_names/location_names",
)
ENTRY: Final[re.Pattern[str]] = re.compile(
    r'(?m)^(?P<prefix>[ \t]*(?P<key>[^\s:#"]+):\d*[ \t]*)"(?:[^"\\\r\n]|\\.)*"'
)


class LocalizationError(ValueError):
    """An installed map-name file cannot supply an unambiguous replacement."""


def map_name_files(game_dir: Path, language: str, names: dict[str, str]) -> dict[str, bytes]:
    """Only requested values change; keys, other texts, BOMs and line endings stay intact.

    These files override the same paths as vanilla. An extra ``replace/`` file instead defines
    each reused key twice; EU5 1.4.4 logs duplicate-key warnings for those files (C256).
    """
    if not names:
        return {}
    found: set[str] = set()
    files: dict[str, bytes] = {}

    def replace(match: re.Match[str]) -> str:
        key = match["key"]
        if key not in names:
            return match[0]
        if key in found:
            message = f"Duplicate map-name key {key} in {language}"
            raise LocalizationError(message)
        found.add(key)
        value = names[key].replace("\\", "\\\\").replace('"', '\\"')
        return f'{match["prefix"]}"{value}"'

    for stem in MAP_NAMES:
        relative = f"main_menu/localization/{language}/{stem}_l_{language}.yml"
        path = game_dir / "game" / relative
        raw = path.read_bytes()
        source = raw.decode("utf-8-sig")
        changed = ENTRY.sub(replace, source)
        if changed != source:
            encoding = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
            files[relative] = changed.encode(encoding)
    missing = names.keys() - found
    if missing:
        message = f"Missing map-name keys in {language}: {', '.join(sorted(missing))}"
        raise LocalizationError(message)
    return files
