"""Minimal, span-based rewrites of EU5 text files for a replaced New World.

Each function receives vanilla text and returns edited text: entries that mention a
removed identifier are cut out (whole lines where they stand alone), generated entries
are inserted, and every other byte is kept as it was.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from rnw.pdx import Block, Edits, Entry, parse

if TYPE_CHECKING:
    from collections.abc import Iterable

WORD: Final[re.Pattern[str]] = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
CLASS_LIST_NAMES: Final[tuple[str, ...]] = (
    "sea_zones",
    "lakes",
    "impassable_mountains",
    "non_ownable",
    "volcanoes",
    "earthquakes",
)


def _line_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Widen a span to its whole line(s) when nothing else but a comment shares them."""
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    line_end = len(text) if line_end < 0 else line_end
    before = text[line_start:start]
    after = text[end:line_end].split("#", 1)[0]
    if before.strip() or after.strip():
        return start, end
    return line_start, min(len(text), line_end + 1)


def _delete(edits: Edits, text: str, entry: Entry) -> None:
    edits.deletions.append(_line_span(text, entry.start, entry.end))


def _words(value: str | Block) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return
    for entry in value.entries:
        if entry.key is not None:
            yield entry.key
        yield from _words(entry.value)


def mentions(entry: Entry, names: set[str]) -> bool:
    """Whether an entry's key or any nested word is in ``names``."""
    if entry.key in names:
        return True
    return any(word in names for word in _words(entry.value))


def _indent_before(text: str, offset: int) -> str:
    line_start = text.rfind("\n", 0, offset) + 1
    prefix = text[line_start:offset]
    return prefix if not prefix.strip() else ""


def rewrite_named_colors(text: str, removed: set[str], added: list[tuple[str, int]]) -> str:
    """Drop removed key/colour lines; append generated declarations."""
    kept = [
        line
        for line in text.splitlines(keepends=True)
        if line.partition("#")[0].split("=", 1)[0].strip() not in removed
    ]
    body = "".join(kept)
    if body and not body.endswith("\n"):
        body += "\n"
    return body + "".join(f"{key} = {color:06x}\n" for key, color in added)


@dataclass(slots=True)
class HierarchyAdditions:
    """Generated provinces per existing area, and new areas per existing region."""

    provinces: dict[str, list[tuple[str, list[str]]]] = field(default_factory=dict)
    areas: dict[str, list[tuple[str, list[tuple[str, list[str]]]]]] = field(default_factory=dict)


def _province_lines(provinces: list[tuple[str, list[str]]], indent: str) -> str:
    return "".join(f"{indent}{name} = {{ {' '.join(keys)} }}\n" for name, keys in provinces)


def _keeps(block: Block, removed: set[str]) -> bool:
    """Whether any location word below survives the removal."""
    return any(word not in removed for word in _location_words(block))


def _location_words(block: Block) -> Iterable[str]:
    for entry in block.entries:
        if isinstance(entry.value, Block):
            yield from _location_words(entry.value)
        elif entry.key is None:
            yield entry.value


def rewrite_definitions(text: str, removed: set[str], additions: HierarchyAdditions) -> str:
    """Cut removed locations (and emptied parents); insert generated hierarchy."""
    root = parse(text)
    edits = Edits()
    for continent in root.entries:
        if not isinstance(continent.value, Block):
            continue
        _rewrite_level(text, continent, removed, additions, edits, depth=0)
    return edits.apply(text)


def _has_additions(entry: Entry, additions: HierarchyAdditions, depth: int) -> bool:
    if not isinstance(entry.value, Block):
        return False
    if depth == 2:  # noqa: PLR2004 - region level
        return bool(additions.areas.get(entry.key or "")) or any(
            _has_additions(child, additions, depth + 1) for child in entry.value.entries
        )
    if depth == 3:  # noqa: PLR2004 - area level
        return bool(additions.provinces.get(entry.key or ""))
    return any(_has_additions(child, additions, depth + 1) for child in entry.value.entries)


def _rewrite_level(  # noqa: PLR0913 - recursive walk carries the shared edit state.
    text: str,
    entry: Entry,
    removed: set[str],
    additions: HierarchyAdditions,
    edits: Edits,
    *,
    depth: int,
) -> None:
    block = entry.value
    if not isinstance(block, Block):
        return
    if not _keeps(block, removed) and not _has_additions(entry, additions, depth):
        _delete(edits, text, entry)
        return
    for child in block.entries:
        if isinstance(child.value, Block) and depth < 4:  # noqa: PLR2004 - provinces are leaves
            _rewrite_level(text, child, removed, additions, edits, depth=depth + 1)
        elif child.key is None and child.value in removed:
            edits.deletions.append((child.start, child.end))
    indent = _indent_before(text, block.close) + "\t"
    name = entry.key or ""
    if depth == 3 and additions.provinces.get(name):  # noqa: PLR2004 - area level
        edits.insert(
            _line_start(text, block.close), _province_lines(additions.provinces[name], indent)
        )
    if depth == 2 and additions.areas.get(name):  # noqa: PLR2004 - region level
        chunks: list[str] = []
        for area, provinces in additions.areas[name]:
            inner = _province_lines(provinces, indent + "\t")
            chunks.append(f"{indent}{area} = {{\n{inner}{indent}}}\n")
        edits.insert(_line_start(text, block.close), "".join(chunks))


def _line_start(text: str, offset: int) -> int:
    start = text.rfind("\n", 0, offset) + 1
    return start if not text[start:offset].strip() else offset


def rewrite_class_lists(text: str, removed: set[str], additions: dict[str, list[str]]) -> str:
    """Remove location tokens from ``default.map`` lists and append generated ones."""
    root = parse(text)
    edits = Edits()
    appended: set[str] = set()
    for entry in root.entries:
        if entry.key not in CLASS_LIST_NAMES or not isinstance(entry.value, Block):
            continue
        for item in entry.value.entries:
            if item.key is None and item.value in removed:
                edits.deletions.append((item.start, item.end))
        new = additions.get(entry.key, [])
        if new and entry.key not in appended:
            appended.add(entry.key)
            edits.insert(entry.value.close, "\n\t# RNW generated\n\t" + " ".join(new) + "\n")
    return edits.apply(text)


def rewrite_templates(text: str, removed: set[str], lines: list[str]) -> str:
    """Remove removed location templates and append generated template lines."""
    root = parse(text)
    edits = Edits()
    for entry in root.entries:
        if entry.key in removed:
            _delete(edits, text, entry)
    body = edits.apply(text)
    if body and not body.endswith("\n"):
        body += "\n"
    return body + "".join(f"{line}\n" for line in lines)


def rewrite_csv(text: str, removed: set[str], key_columns: tuple[int, ...], rows: list[str]) -> str:
    """Drop rows naming removed keys; append rows; keep the header and final-newline style."""
    lines = text.split("\n")
    trailing = text.endswith("\n")
    body = [line for line in lines if line] if trailing else list(lines)
    header, data = body[0], body[1:]
    kept = [
        line
        for line in data
        if not any(
            index < len(fields) and fields[index].strip() in removed
            for fields in [line.split(";")]
            for index in key_columns
        )
    ]
    out = "\n".join([header, *kept, *rows])
    return out + "\n" if trailing else out


def rewrite_locators(text: str, removed: set[str], instances: list[str]) -> str:
    """Drop locator instances of removed locations and append generated ones."""
    root = parse(text)
    edits = Edits()
    for top in root.entries:
        if not isinstance(top.value, Block):
            continue
        holder = top.value.first("instances")
        if holder is None or not isinstance(holder.value, Block):
            continue
        for item in holder.value.entries:
            if isinstance(item.value, Block):
                ident = item.value.first("id")
                if ident is not None and ident.value in removed:
                    _delete(edits, text, item)
        if instances:
            edits.insert(_line_start(text, holder.value.close), "".join(instances))
    return edits.apply(text)


def rewrite_override_locators(text: str, removed: set[str]) -> str:
    """Drop override entries whose ``province`` is removed."""
    root = parse(text)
    edits = Edits()
    for entry in root.entries:
        if isinstance(entry.value, Block):
            province = entry.value.first("province")
            if province is not None and province.value in removed:
                _delete(edits, text, entry)
    return edits.apply(text)


@dataclass(slots=True)
class SetupResult:
    """Edited setup texts and what was cut."""

    texts: dict[str, str]
    deleted: dict[str, int]
    removed_ids: set[str]


def _record_holders(root: Block) -> Iterable[Block]:
    """Blocks whose children are independent records (managers and their lists)."""
    for top in root.entries:
        if isinstance(top.value, Block):
            yield top.value


def prune_setup(  # noqa: C901, PLR0912 - one fixed-point loop over all setup files.
    texts: dict[str, str],
    removed: set[str],
    pops_added: dict[str, list[str]],
) -> SetupResult:
    """Remove every setup record that refers to a removed identifier, to a fixed point.

    Countries are records under ``countries/countries``; members of international
    organisations are removed word by word (an organisation whose members all vanish is
    removed). Keys of deleted records (characters, dynasties, tags) join the removed set
    so dependent records disappear too. Generated locations get empty pop entries.
    """
    ids = set(removed)
    trees = {name: parse(text) for name, text in texts.items()}
    doomed: dict[str, set[tuple[int, int]]] = {name: set() for name in texts}
    words: dict[str, set[tuple[int, int]]] = {name: set() for name in texts}
    changed = True
    while changed:
        changed = False
        for name, root in trees.items():
            holders = list(_record_holders(root))
            countries = root.block("countries", "countries")
            if countries is not None:
                holders = [countries]
            for holder in holders:
                keyed = Counter(record.key for record in holder.entries if record.key)
                for record in holder.entries:
                    span = (record.start, record.end)
                    if span in doomed[name]:
                        continue
                    if name.startswith("15_") and isinstance(record.value, Block):
                        changed |= _prune_members(record, ids, words[name], doomed[name])
                        continue
                    if mentions(record, ids):
                        doomed[name].add(span)
                        unique = record.key is not None and keyed[record.key] == 1
                        if unique and isinstance(record.value, Block):
                            ids.add(record.key or "")
                        changed = True
    out: dict[str, str] = {}
    deleted: dict[str, int] = {}
    for name, text in texts.items():
        edits = Edits()
        for start, end in sorted(doomed[name]):
            edits.deletions.append(_line_span(text, start, end))
        for start, end in sorted(words[name]):
            edits.deletions.append((start, end))
        if name.startswith("06_") and pops_added:
            holder = trees[name].block("locations")
            if holder is not None:
                lines = "".join(
                    f"{key} = {{\n" + "".join(f"{line}\n" for line in pops) + "}\n"
                    for key, pops in pops_added.items()
                )
                edits.insert(_line_start(text, holder.close), lines)
        out[name] = edits.apply(text)
        deleted[name] = len(doomed[name])
    return SetupResult(out, deleted, ids)


def insert_into_block(text: str, path: tuple[str, ...], addition: str) -> str:
    """Insert ``addition`` before the closing brace of the block at ``path``."""
    block = parse(text).block(*path)
    if block is None:
        message = f"No block {'/'.join(path)}"
        raise KeyError(message)
    edits = Edits()
    edits.insert(_line_start(text, block.close), addition)
    return edits.apply(text)


def _prune_members(
    record: Entry, ids: set[str], words: set[tuple[int, int]], doomed: set[tuple[int, int]]
) -> bool:
    block = record.value
    if not isinstance(block, Block):
        return False
    members = block.first("members")
    if members is None or not isinstance(members.value, Block):
        if mentions(record, ids):
            doomed.add((record.start, record.end))
            return True
        return False
    items = list(members.value.words())
    gone = [item for item in items if item.value in ids]
    others = [entry for entry in block.entries if entry is not members]
    if (items and len(gone) == len(items)) or any(mentions(entry, ids) for entry in others):
        doomed.add((record.start, record.end))
        return True
    before = len(words)
    words.update((item.start, item.end) for item in gone)
    return len(words) != before
