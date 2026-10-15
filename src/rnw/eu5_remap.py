"""Point script references at removed New World locations to generated ones.

Removing vanilla locations leaves holy sites, scripted geographies, formables,
expedition routes and events pointing at nothing; EU5 1.4.1 crashed while setting up a
holy site whose location was removed [V-GAME]. Each removed location is mapped to the
nearest generated cell of the same family, and only syntactic location references are
rewritten: ``location:KEY`` scopes, ``location``/``connected_location`` values and the
items of ``location``/``locations``/``waypoints`` lists. Removed provinces map to the
province of their first location's replacement.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.model import CellClass
from rnw.pdx import Block, Edits, PdxSyntaxError, parse

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
VALUE_KEYS: Final[frozenset[str]] = frozenset(
    {"location", "connected_location", "only_in_location"}
)
LIST_KEYS: Final[frozenset[str]] = frozenset({"location", "locations", "waypoints"})
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


def _list_edits(block: Block, remap: dict[str, str], edits: Edits) -> int:
    count = 0
    for entry in block.entries:
        if entry.key is None and isinstance(entry.value, str) and entry.value in remap:
            edits.deletions.append((entry.start, entry.end))
            edits.insert(entry.start, remap[entry.value])
            count += 1
    return count


def _walk(block: Block, remap: dict[str, str], edits: Edits, text: str) -> int:
    count = 0
    for entry in block.entries:
        value = entry.value
        if isinstance(value, Block):
            if entry.key in LIST_KEYS:
                count += _list_edits(value, remap, edits)
            count += _walk(value, remap, edits, text)
        elif entry.key in VALUE_KEYS:
            bare = value.strip('"')
            if bare in remap and ":" not in value:
                start = entry.end - len(value)
                edits.deletions.append((start, entry.end))
                quote = '"' if value.startswith('"') else ""
                edits.insert(start, f"{quote}{remap[bare]}{quote}")
                count += 1
    _ = text
    return count


def remap_text(text: str, remap: dict[str, str]) -> tuple[str, int]:
    """Rewrite location references in one script text; returns (text, replacements)."""
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


def remap_scripts(game_dir: Path, remap: dict[str, str]) -> tuple[dict[str, bytes], dict[str, int]]:
    """Mod copies of every script file whose location references changed."""
    outputs: dict[str, bytes] = {}
    counts: dict[str, int] = {}
    for root in SCRIPT_ROOTS:
        base = game_dir / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.txt")):
            raw = path.read_bytes()
            bom = raw.startswith(b"\xef\xbb\xbf")
            text = raw.decode("utf-8-sig", errors="strict")
            new, count = remap_text(text, remap)
            if count:
                relative = path.relative_to(game_dir).as_posix().removeprefix("game/")
                outputs[relative] = (("﻿" if bom else "") + new).encode("utf-8")
                counts[relative] = count
    return outputs, counts
