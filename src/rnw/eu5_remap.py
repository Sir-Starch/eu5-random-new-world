"""Point script references at removed New World locations to generated ones.

Removing vanilla locations leaves holy sites, scripted geographies, formables,
expedition routes and events pointing at nothing; EU5 1.4.1 crashed while setting up a
holy site whose location was removed [V-GAME]. Each removed location is mapped to the
nearest generated cell of the same family, and only syntactic location references are
rewritten: ``location:KEY`` scopes, ``location``/``connected_location`` values and the
items of ``location``/``locations``/``waypoints`` and ``province_definition``/
``provinces`` lists (repeats dropped). Removed provinces map to the province of their
first location's replacement. A removed location in a ``map_id`` list is dropped, since
the object it names needs a locator of its own. The files of the base game and of every
DLC are rewritten alike; a mod file replaces the DLC file at the same path. The same
pass drops the dynamic historical events of removed country tags (``eu5_events``).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.eu5_events import EVENT_ID, mentions, names_tag, retire_events, retire_modifiers
from rnw.model import CellClass
from rnw.pdx import Block, Edits, PdxSyntaxError, line_span, parse
from rnw.progress import checkpoint

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

    from rnw.eu5_newworld import Plan

SCRIPT_ROOTS: Final[tuple[str, ...]] = (
    "game/in_game/common",
    "game/in_game/events",
    "game/main_menu/common",
    "game/in_game/gfx/map/canal_gfx",
    "game/in_game/gfx/map/city_data",
)
SCRIPT_FILES: Final[tuple[str, ...]] = (
    "game/in_game/gfx/map/map_objects/dynamic_game_objects.txt",
)
VALUE_KEYS: Final[frozenset[str]] = frozenset(
    {"location", "connected_location", "only_in_location"}
)
LIST_KEYS: Final[frozenset[str]] = frozenset(
    {"location", "locations", "waypoints", "province_definition", "provinces", "map_id"}
)
DROP_KEYS: Final[frozenset[str]] = frozenset({"map_id"})
WORD: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9_]+")
SCOPE: Final[re.Pattern[str]] = re.compile(
    r"(?<![A-Za-z0-9_])(location|province):([A-Za-z_][A-Za-z0-9_]*)"
)
FAMILY: Final[dict[CellClass, frozenset[CellClass]]] = {
    CellClass.LAND: frozenset({CellClass.LAND}),
    CellClass.NON_OWNABLE: frozenset({CellClass.LAND}),
    CellClass.WASTELAND: frozenset({CellClass.WASTELAND, CellClass.LAND}),
    CellClass.SEA: frozenset({CellClass.SEA}),
    CellClass.LAKE: frozenset({CellClass.LAKE, CellClass.SEA}),
}


def build_remap(
    removed: list[tuple[str, CellClass, int, int]],
    plan: Plan,
    centres: NDArray[np.int64],
    provinces: dict[str, list[str]],
) -> dict[str, str]:
    """Map removed location (and province) keys to generated keys.

    ``removed`` holds (key, class, row, column) in the same coordinates as ``centres``,
    which gives each generated cell's centre. ``provinces`` lists each removed province's
    locations in definition order.
    """
    remap: dict[str, str] = {}
    by_family: dict[frozenset[CellClass], NDArray[np.int64]] = {}
    for family in set(FAMILY.values()):
        members = [i for i, cell in enumerate(plan.cells) if cell.kind in family]
        by_family[family] = np.array(members, dtype=np.int64)
    for key, kind, row, column in removed:
        pool = by_family[FAMILY[kind]]
        if not pool.size:
            pool = by_family[FAMILY[CellClass.LAND]]
        delta = centres[pool] - np.array([row, column], dtype=np.int64)
        best = int(pool[int(np.argmin((delta * delta).sum(axis=1)))])
        remap[key] = plan.cells[best].key
    province_of = {cell.key: cell.province for cell in plan.cells}
    for province, keys in provinces.items():
        for key in keys:
            if key in remap:
                remap[province] = province_of[remap[key]]
                break
    return remap


def _list_edits(block: Block, remap: dict[str, str], edits: Edits, text: str, *, drop: bool) -> int:
    count = 0
    seen = {word.value for word in block.words() if isinstance(word.value, str)} - remap.keys()
    for entry in block.entries:
        if entry.key is None and isinstance(entry.value, str) and entry.value in remap:
            target = remap[entry.value]
            if drop or target in seen:
                edits.deletions.append(line_span(text, entry.start, entry.end))
            else:
                edits.deletions.append((entry.start, entry.end))
                edits.insert(entry.start, target)
                seen.add(target)
            count += 1
    return count


def _walk(block: Block, remap: dict[str, str], edits: Edits, text: str) -> int:
    count = 0
    for entry in block.entries:
        value = entry.value
        if isinstance(value, Block):
            if entry.key in LIST_KEYS:
                count += _list_edits(value, remap, edits, text, drop=entry.key in DROP_KEYS)
            count += _walk(value, remap, edits, text)
        elif entry.key in VALUE_KEYS:
            bare = value.strip('"')
            if bare in remap and ":" not in value:
                start = entry.end - len(value)
                edits.deletions.append((start, entry.end))
                quote = '"' if value.startswith('"') else ""
                edits.insert(start, f"{quote}{remap[bare]}{quote}")
                count += 1
    return count


def remap_text(text: str, remap: dict[str, str]) -> tuple[str, int]:
    """Rewrite location references in one script text; returns (text, replacements)."""
    if remap.keys().isdisjoint(WORD.findall(text)):
        return text, 0  # no reference can change, so the text need not be parsed
    count = 0
    try:
        root = parse(text)
    except PdxSyntaxError:
        root = None
    edits = Edits()
    if root is not None:
        count += _walk(root, remap, edits, text)
    covered = sorted(edits.deletions)
    for match in SCOPE.finditer(text):
        key = match.group(2)
        if key in remap and not any(start <= match.start(2) < end for start, end in covered):
            edits.deletions.append((match.start(2), match.end(2)))
            edits.insert(match.start(2), remap[key])
            count += 1
    return (edits.apply(text) if count else text), count


class RemapError(ValueError):
    """Script files that cannot be rewritten as one set."""


@dataclass(frozen=True, slots=True)
class ScriptRewrite:
    """Mod copies of rewritten script files with what changed in each."""

    outputs: dict[str, bytes]
    remapped: dict[str, int]
    retired: dict[str, tuple[str, ...]]
    modifiers: tuple[str, ...] = ()


def script_files(game_dir: Path) -> dict[str, Path]:
    """Script files by mod path: the base game's and every DLC's, none twice."""
    game = game_dir / "game"
    files: dict[str, Path] = {}
    for base in (game, *sorted((game / "dlc").glob("*"))):
        paths = [
            path
            for root in SCRIPT_ROOTS
            if (base / root.removeprefix("game/")).is_dir()
            for path in sorted((base / root.removeprefix("game/")).rglob("*.txt"))
        ]
        paths += [base / name.removeprefix("game/") for name in SCRIPT_FILES]
        for path in paths:
            if not path.is_file():
                continue
            relative = path.relative_to(base).as_posix()
            if relative in files:
                message = f"{relative} exists in the base game and in {base.name}"
                raise RemapError(message)
            files[relative] = path
    return files


def remap_scripts(game_dir: Path, remap: dict[str, str], retired_tags: set[str]) -> ScriptRewrite:
    """Mod copies of every script file whose location or tag references changed."""
    files: dict[str, tuple[bytes, str]] = {}
    named: Counter[str] = Counter()
    for relative, path in script_files(game_dir).items():
        raw = path.read_bytes()
        files[relative] = (raw, raw.decode("utf-8-sig", errors="strict"))
        named.update(EVENT_ID.findall(files[relative][1]))
    texts = {relative: text for relative, (_, text) in files.items()}
    retired: dict[str, tuple[str, ...]] = {}
    removed: list[str] = []
    for relative, text in list(texts.items()):
        if "/events/" in relative and names_tag(text, retired_tags):
            elsewhere = named.copy()
            elsewhere.subtract(mentions(text))
            result = retire_events(text, retired_tags, elsewhere)
            if result.text != text:
                texts[relative] = result.text
                retired[relative] = result.events
                removed.append(result.removed)
    changed, modifiers = retire_modifiers(texts, "".join(removed))
    texts.update(changed)
    outputs: dict[str, bytes] = {}
    counts: dict[str, int] = {}
    for relative, (raw, original) in files.items():
        checkpoint()
        new, count = remap_text(texts[relative], remap)
        if count or texts[relative] != original:
            bom = "\ufeff" if raw.startswith(b"\xef\xbb\xbf") else ""
            outputs[relative] = (bom + new).encode("utf-8")
            counts[relative] = count
    return ScriptRewrite(outputs, counts, retired, modifiers)
