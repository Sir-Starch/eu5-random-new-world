"""Point script references at removed New World locations to generated ones.

Removing vanilla locations leaves holy sites, scripted geographies, formables,
expedition routes and events pointing at nothing; EU5 1.4.1 crashed while setting up a
holy site whose location was removed [V-GAME]. Each removed location is mapped to the
nearest generated cell of the same family and access role (ports and passable
water remain accessible), and only syntactic location references are
rewritten: ``location:KEY`` scopes, ``location``/``connected_location`` values and the
items of ``location``/``locations``/``waypoints`` and ``province_definition``/
``provinces`` lists (repeats dropped). Removed provinces map to the province of their
first location's replacement. A removed location in a ``map_id`` list is dropped, since
the object it names needs a locator of its own. The files of the base game and of every
DLC are rewritten alike; a mod file replaces the DLC file at the same path. The same
pass drops the dynamic historical events of removed country tags (``eu5_events``), the
illustrations of removed places (the DLC pictures that the location view shows for a monument or a
holy site) and the unique buildings of the DLC monuments that stood in them (the 3D model of the
pyramid of Teotihuacan or Cholula): a picture or a model shows its place, so it is dropped rather
than moved to a generated one.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.eu5_events import EVENT_ID, mentions, names_tag, retire_events, retire_modifiers
from rnw.model import CellClass
from rnw.pdx import Block, Edits, PdxSyntaxError, line_span, parse
from rnw.progress import checkpoint

if TYPE_CHECKING:
    from collections.abc import Set as AbstractSet
    from pathlib import Path

    from numpy.typing import NDArray

    from rnw.eu5_newworld import Plan

SCRIPT_ROOTS: Final[tuple[str, ...]] = (
    "game/in_game/common",
    "game/in_game/events",
    "game/main_menu/common",
    "game/in_game/gfx/map/canal_gfx",
    "game/in_game/gfx/map/city_data",
    "game/in_game/gfx/images",
)
SCRIPT_FILES: Final[tuple[str, ...]] = (
    "game/in_game/gfx/map/map_objects/dynamic_game_objects.txt",
)
VALUE_KEYS: Final[frozenset[str]] = frozenset(
    {"location", "connected_location", "only_in_location", "area"}
)
LIST_KEYS: Final[frozenset[str]] = frozenset(
    {
        "location",
        "locations",
        "waypoints",
        "province_definition",
        "provinces",
        "map_id",
        "areas",
        "discovered_areas",
    }
)
DROP_KEYS: Final[frozenset[str]] = frozenset({"map_id"})
WORD: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9_]+")
SCOPE: Final[re.Pattern[str]] = re.compile(
    r"(?<![A-Za-z0-9_])(location|province|province_definition|area):([A-Za-z_][A-Za-z0-9_]*)"
)
IMAGES: Final[str] = "in_game/gfx/images/"
CITY_DATA: Final[str] = "in_game/gfx/map/city_data/"
MONUMENT_PLACE: Final[str] = "only_in_location"
ILLUSTRATION: Final[str] = "illustration_image"
PLACE: Final[re.Pattern[str]] = re.compile(
    r"(?<![A-Za-z0-9_])(?:location|province|province_definition):([A-Za-z_][A-Za-z0-9_]*)"
)
FAMILY: Final[dict[CellClass, frozenset[CellClass]]] = {
    CellClass.LAND: frozenset({CellClass.LAND}),
    CellClass.NON_OWNABLE: frozenset({CellClass.LAND}),
    CellClass.WASTELAND: frozenset({CellClass.WASTELAND, CellClass.LAND}),
    CellClass.SEA: frozenset({CellClass.SEA}),
    CellClass.LAKE: frozenset({CellClass.LAKE, CellClass.SEA}),
}


@dataclass(frozen=True, slots=True)
class RemapAccess:
    """Access roles of installed places and their compatible generated destinations."""

    port_keys: frozenset[str] = frozenset()
    port_cells: frozenset[int] = frozenset()
    navigable_keys: frozenset[str] = frozenset()
    closed_seas: frozenset[int] = frozenset()


class GeographicRemap(dict[str, str]):
    """Bindings by geographic scope; vanilla can reuse a name across scopes."""

    def __init__(
        self, locations: dict[str, str], provinces: dict[str, str], areas: dict[str, str]
    ) -> None:
        super().__init__({**provinces, **areas, **locations})
        self.locations: dict[str, str] = locations
        self.provinces: dict[str, str] = provinces
        self.areas: dict[str, str] = areas

    def with_locations(self, changes: dict[str, str]) -> GeographicRemap:
        return GeographicRemap(self.locations | changes, self.provinces, self.areas)


def _scope_map(remap: dict[str, str], scope: str) -> dict[str, str]:
    if not isinstance(remap, GeographicRemap):
        return remap
    if scope in {"province", "province_definition", "provinces"}:
        return remap.provinces
    if scope in {"area", "areas", "discovered_areas"}:
        return remap.areas
    return remap.locations


def build_remap(  # noqa: PLR0913 - geographic levels share their location bindings.
    removed: list[tuple[str, CellClass, int, int]],
    plan: Plan,
    centres: NDArray[np.int64],
    provinces: dict[str, list[str]],
    *,
    access: RemapAccess,
    areas: dict[str, list[str]] | None = None,
) -> GeographicRemap:
    """Map removed location (and province) keys to generated keys.

    ``removed`` holds (key, class, row, column) in the same coordinates as ``centres``,
    which gives each generated cell's centre. ``provinces`` lists each removed province's
    locations in definition order. Removed ports require a generated port, and
    passable water requires passable water. These are geographic roles shared by
    every script reference, including expedition waypoints and their callbacks.
    """
    remap: dict[str, str] = {}
    by_family: dict[frozenset[CellClass], NDArray[np.int64]] = {}
    for family in set(FAMILY.values()):
        members = [i for i, cell in enumerate(plan.cells) if cell.kind in family]
        by_family[family] = np.array(members, dtype=np.int64)
    for key, kind, row, column in removed:
        pool = by_family[FAMILY[kind]]
        if key in access.port_keys:
            pool = np.array([i for i in pool.tolist() if i in access.port_cells], dtype=np.int64)
        elif key in access.navigable_keys:
            pool = np.array(
                [i for i in pool.tolist() if i not in access.closed_seas], dtype=np.int64
            )
        if not pool.size:
            message = f"No generated replacement preserves the geographic role of {key}"
            raise RemapError(message)
        delta = centres[pool] - np.array([row, column], dtype=np.int64)
        best = int(pool[int(np.argmin((delta * delta).sum(axis=1)))])
        remap[key] = plan.cells[best].key
    province_of = {cell.key: cell.province for cell in plan.cells}
    province_remap: dict[str, str] = {}
    for province, keys in provinces.items():
        for key in keys:
            if key in remap:
                province_remap[province] = province_of[remap[key]]
                break
    area_of = {cell.key: cell.area for cell in plan.cells}
    area_remap: dict[str, str] = {}
    for area, members in (areas or {}).items():
        destinations = Counter(area_of[remap[key]] for key in members if key in remap)
        if not destinations:
            message = f"No generated replacement for removed area {area}"
            raise RemapError(message)
        area_remap[area] = min(destinations, key=lambda name: (-destinations[name], name))
    return GeographicRemap(remap, province_remap, area_remap)


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
                scoped = _scope_map(remap, entry.key)
                count += _list_edits(value, scoped, edits, text, drop=entry.key in DROP_KEYS)
            count += _walk(value, remap, edits, text)
        elif entry.key in VALUE_KEYS:
            scoped = _scope_map(remap, entry.key)
            bare = value.strip('"')
            if bare in scoped and ":" not in value:
                start = entry.end - len(value)
                edits.deletions.append((start, entry.end))
                quote = '"' if value.startswith('"') else ""
                edits.insert(start, f"{quote}{scoped[bare]}{quote}")
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
        scoped = _scope_map(remap, match.group(1))
        if key in scoped and not any(start <= match.start(2) < end for start, end in covered):
            edits.deletions.append((match.start(2), match.end(2)))
            edits.insert(match.start(2), scoped[key])
            count += 1
    return (edits.apply(text) if count else text), count


def _with_labels(text: str, start: int) -> int:
    """``start`` moved up over the comment lines right above it, which name the entry."""
    while start > 0:
        before = text.rfind("\n", 0, start - 1) + 1
        if not text[before:start].lstrip().startswith("#"):
            break
        start = before
    return start


def _illustrations(block: Block, removed: AbstractSet[str], text: str, edits: Edits) -> int:
    count = 0
    for entry in block.entries:
        if not isinstance(entry.value, Block):
            continue
        if entry.key == ILLUSTRATION:
            if any(key in removed for key in PLACE.findall(text[entry.start : entry.end])):
                start, end = line_span(text, entry.start, entry.end)
                edits.deletions.append((_with_labels(text, start), end))
                count += 1
        else:
            count += _illustrations(entry.value, removed, text, edits)
    return count


def drop_illustrations(text: str, removed: AbstractSet[str]) -> tuple[str, int]:
    """``text`` without the illustrations whose trigger names a removed place; and how many.

    The location view asks every illustration's trigger of every location it shows; a trigger
    that compares with a location that no longer exists makes the engine log an error per
    frame (``Invalid right side during comparison 'location'``, EU5 1.4.4, experiment 036).
    """
    if removed.isdisjoint(WORD.findall(text)):
        return text, 0
    edits = Edits()
    count = _illustrations(parse(text), removed, text, edits)
    return (edits.apply(text) if count else text), count


def _monuments(block: Block, removed: AbstractSet[str], text: str, edits: Edits) -> int:
    count = 0
    for entry in block.entries:
        if not isinstance(entry.value, Block):
            continue
        place = entry.value.first(MONUMENT_PLACE)
        if (
            entry.key is not None
            and place is not None
            and isinstance(place.value, str)
            and place.value in removed
        ):
            start, end = line_span(text, entry.start, entry.end)
            edits.deletions.append((_with_labels(text, start), end))
            count += 1
        else:
            count += _monuments(entry.value, removed, text, edits)
    return count


def drop_monuments(text: str, removed: AbstractSet[str]) -> tuple[str, int]:
    """``text`` without the unique buildings bound to a removed place; and how many.

    The DLC packs of ancient monuments and sacred sites put a 3D model on one location
    (``only_in_location``): the pyramid of Teotihuacan, the pyramid of Cholula. Remapped, the model
    would stand on whichever generated location is nearest to the old one, with no tie to the
    people, the holy site or the picture of that place, so it goes with the place. Its mesh list
    stays; nothing names it.
    """
    if removed.isdisjoint(WORD.findall(text)):
        return text, 0
    edits = Edits()
    count = _monuments(parse(text), removed, text, edits)
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
    illustrations: dict[str, int] = field(default_factory=dict)
    monuments: dict[str, int] = field(default_factory=dict)


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


def _drop_places(
    texts: dict[str, str], removed: AbstractSet[str]
) -> tuple[dict[str, int], dict[str, int]]:
    """Drop the pictures and the models of removed places from ``texts``; count them by file."""
    illustrations: dict[str, int] = {}
    monuments: dict[str, int] = {}
    for relative, text in list(texts.items()):
        if relative.startswith(IMAGES):
            texts[relative], dropped = drop_illustrations(text, removed)
            if dropped:
                illustrations[relative] = dropped
        elif relative.startswith(CITY_DATA):
            texts[relative], dropped = drop_monuments(text, removed)
            if dropped:
                monuments[relative] = dropped
    return illustrations, monuments


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
    illustrations, monuments = _drop_places(texts, remap.keys())
    outputs: dict[str, bytes] = {}
    counts: dict[str, int] = {}
    for relative, (raw, original) in files.items():
        checkpoint()
        new, count = remap_text(texts[relative], remap)
        if count and relative.startswith((IMAGES, CITY_DATA)):
            message = f"{relative} names removed places outside the pictures and models it drops"
            raise RemapError(message)
        if count or texts[relative] != original:
            bom = "\ufeff" if raw.startswith(b"\xef\xbb\xbf") else ""
            outputs[relative] = (bom + new).encode("utf-8")
            counts[relative] = count
    return ScriptRewrite(outputs, counts, retired, modifiers, illustrations, monuments)
