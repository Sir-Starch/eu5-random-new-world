"""Inventory of the vanilla script objects that name the New World the generator replaces.

The generator replaces the American continent, so every script object that names an
American tag, location, province, area, region or subcontinent is a *consumer* of the
replaced content. Each consumer is one top-level entry of a script file under the remap
roots (an event, a formable, an advance, a scripted trigger and so on), identified by its
category and its vanilla identifier. ``content_decisions`` gives each one exactly one
decision; the export stops on a consumer without one (content plan, N0).

The scan reads only the installation and keeps no game text: a consumer is its
identifiers. Words are matched structurally, never as substrings: a word that is the key of
an assignment (``circle = {``) is not a reference, a word after a scope prefix
(``area:granada_area``) is, and so is a bare value or list item.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.eu5_canvas import NEW_WORLD
from rnw.eu5_natives import COUNTRY_DIR
from rnw.eu5_remap import script_files
from rnw.eu5_rewrite import prune_setup
from rnw.geography import read_locations
from rnw.pdx import Block, parse
from rnw.progress import checkpoint

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from collections.abc import Set as AbstractSet
    from pathlib import Path

GEOGRAPHY: Final[tuple[str, ...]] = ("location", "province", "area", "region", "subcontinent")
# What a consumer can name: a retired tag, an American key, or state only retired objects set.
KINDS: Final[tuple[str, ...]] = ("tag", *GEOGRAPHY, "state")
SETUP_DIR: Final[str] = "game/main_menu/setup/1337"
DEFINITIONS: Final[str] = "game/in_game/map_data/definitions.txt"
COMMENT: Final[re.Pattern[str]] = re.compile(r"#[^\n]*")
# An optional scope prefix, the word, and the operator that would make the word a key.
NAME: Final[str] = r"[A-Za-z_][A-Za-z0-9_]*"
WORD: Final[re.Pattern[str]] = re.compile(
    rf"(?<![A-Za-z0-9_.])(?:({NAME}):)?({NAME})(?![A-Za-z0-9_])(\s*(?:[=<>]|[!?]=))?"
)
# A statement that sets a variable or a flag: ``set_variable = { name = x`` or ``set_x_flag = x``.
STATE_VERB: Final[str] = (
    r"\b(?:set|change|add_to|remove_from|clamp)_(?:[a-z]+_)?(?:variable|flag)\w*"
)
STATE_SET: Final[re.Pattern[str]] = re.compile(
    rf'{STATE_VERB}\s*=\s*(?:\{{\s*name\s*=\s*)?"?({NAME}(?:\.{NAME})*)'
)
WORDS: Final[re.Pattern[str]] = re.compile(NAME)
# Scope prefixes that make the word after them a map key or a country tag.
SCOPES: Final[frozenset[str]] = frozenset(
    (
        "location",
        "province",
        "province_definition",
        "area",
        "region",
        "sub_continent",
        "c",
        "country",
    )
)


@dataclass(frozen=True, slots=True)
class Footprint:
    """What the generator replaces: American keys by kind and the tags that go with them."""

    keys: Mapping[str, frozenset[str]]
    tags: frozenset[str]

    def kinds_of(self, word: str) -> tuple[str, ...]:
        """The geography kinds in which ``word`` is an American key."""
        return tuple(kind for kind in GEOGRAPHY if word in self.keys[kind])


@dataclass(frozen=True, slots=True)
class Consumer:
    """One top-level script object that names replaced content.

    ``retired`` is set for an object the exporter removes today (the events of retired
    tags, the modifiers only they applied, the historical base values of removed
    locations), whether or not it names a key itself.
    """

    category: str
    ident: str
    files: tuple[str, ...]
    refs: Mapping[str, tuple[str, ...]]
    retired: bool = False

    @property
    def key(self) -> str:
        """The consumer's identifier in the decision table."""
        return f"{self.category}:{self.ident}"


def read_footprint(game_dir: Path) -> Footprint:
    """American keys by kind, and the tags whose 1337 setup records go with them.

    The tags are found as the exporter finds them: a setup record that names a removed
    location or province is removed, a removed record's key joins the removed identifiers
    and so on to a fixed point, and every tag defined by a country file that is among them
    is retired. Here every American location and province is removed.
    """
    locations = [
        item for item in read_locations(game_dir / DEFINITIONS) if item.continent == NEW_WORLD
    ]
    keys = {
        "location": frozenset(item.key for item in locations),
        "province": frozenset(item.province for item in locations),
        "area": frozenset(item.area for item in locations),
        "region": frozenset(item.region for item in locations),
        "subcontinent": frozenset(item.subcontinent for item in locations),
    }
    setup = {
        path.name: path.read_text(encoding="utf-8-sig")
        for path in sorted((game_dir / SETUP_DIR).glob("*.txt"))
    }
    result = prune_setup(setup, set(keys["location"]) | set(keys["province"]), {})
    defined: set[str] = set()
    for path in sorted((game_dir / COUNTRY_DIR).glob("*.txt")):
        text = path.read_text(encoding="utf-8-sig")
        defined |= {entry.key for entry in parse(text).entries if entry.key}
    return Footprint(keys, frozenset(result.removed_ids & defined))


def category_of(relative: str) -> str:
    """The kind of script object a file under the remap roots holds."""
    parts = relative.split("/")
    if parts[:2] == ["in_game", "common"]:
        return f"common/{parts[2]}"
    if parts[:2] == ["main_menu", "common"]:
        return f"menu/{parts[2]}"
    if parts[:2] == ["in_game", "events"]:
        return "events"
    return "/".join(parts[1:3])


def references(text: str, footprint: Footprint, keywords: frozenset[str]) -> dict[str, set[str]]:
    """The American keys and retired tags ``text`` names, by kind.

    A map key that is also a key somewhere in the scripts (``keywords``) counts only after
    a scope prefix: ``circle`` is both an American location and a script word.
    """
    found: defaultdict[str, set[str]] = defaultdict(set)
    for match in WORD.finditer(COMMENT.sub("", text)):
        prefix, word, operator = match.groups()
        if prefix is not None and prefix not in SCOPES:
            continue
        if operator and prefix is None:
            continue  # the key of an assignment, not a value
        if word in footprint.tags:
            found["tag"].add(word)
        if prefix is not None or word not in keywords:
            for kind in footprint.kinds_of(word):
                found[kind].add(word)
    return dict(found)


def _keys(block: Block) -> set[str]:
    keys: set[str] = set()
    for entry in block.entries:
        if entry.key is not None:
            keys.add(entry.key)
        if isinstance(entry.value, Block):
            keys |= _keys(entry.value)
    return keys


def lost_states(objects: Mapping[str, str], retired: Iterable[str]) -> dict[str, set[str]]:
    """State that only retired objects set, by the objects that remain and read it.

    ``objects`` maps decision keys to their script text. A variable or flag set by retired
    objects alone is never set again, so a remaining object that reads it can no longer
    be reached (the privilege that needs a variable only a retired event sets).
    """
    gone = set(retired)
    setters: defaultdict[str, set[bool]] = defaultdict(set)
    for key, text in objects.items():
        for match in STATE_SET.finditer(COMMENT.sub("", text)):
            setters[match.group(1)].add(key in gone)
    orphaned = {name for name, flags in setters.items() if flags == {True}}
    found: dict[str, set[str]] = {}
    for key, text in objects.items():
        if key in gone:
            continue
        names = orphaned & set(WORDS.findall(COMMENT.sub("", text)))
        if names:
            found[key] = names
    return found


def scan(
    game_dir: Path, footprint: Footprint, retired: Mapping[str, Iterable[str]] | None = None
) -> dict[str, Consumer]:
    """Every top-level script object that names replaced content, by decision key.

    ``retired`` lists, by category, the objects the exporter removes today; each one is a
    consumer even where it names no key. An object that reads state only a retired object
    sets is a consumer of kind ``state``.
    """
    parsed: dict[str, tuple[str, Block]] = {}
    keywords: set[str] = set()
    for relative, path in script_files(game_dir).items():
        checkpoint()
        text = path.read_text(encoding="utf-8-sig")
        parsed[relative] = (text, parse(text))
        keywords |= _keys(parsed[relative][1])
    words = frozenset(keywords)
    merged: dict[str, tuple[set[str], dict[str, set[str]]]] = {}
    sources: dict[str, str] = {}
    where: dict[str, str] = {}
    for relative, (text, root) in parsed.items():
        category = category_of(relative)
        for entry in root.entries:
            if entry.key is None or not isinstance(entry.value, Block):
                continue
            key = f"{category}:{entry.key}"
            body = text[entry.start : entry.end]
            _ = sources.setdefault(key, "")
            sources[key] += body
            _ = where.setdefault(key, relative)
            found = references(body, footprint, words)
            owned = entry.key in footprint.tags
            if not found and not owned:
                continue
            files, refs = merged.setdefault(key, (set(), {}))
            files.add(relative)
            for kind, names in found.items():
                refs.setdefault(kind, set()).update(names)
            if owned:
                refs.setdefault("tag", set()).add(entry.key)
    gone = {
        f"{category}:{ident}" for category, idents in (retired or {}).items() for ident in idents
    }
    for key in gone:
        _ = merged.setdefault(key, (set(), {}))
    for key, names in lost_states(sources, gone).items():
        _, refs = merged.setdefault(key, (set(), {}))
        refs.setdefault("state", set()).update(names)
    return {
        key: Consumer(
            key.split(":", 1)[0],
            key.split(":", 1)[1],
            tuple(sorted(files or ({where[key]} if key in where else set()))),
            {kind: tuple(sorted(names)) for kind, names in sorted(refs.items())},
            key in gone,
        )
        for key, (files, refs) in sorted(merged.items())
    }


def residuals(
    texts: Mapping[str, str], footprint: Footprint, present: Mapping[str, AbstractSet[str]]
) -> dict[str, dict[str, tuple[str, ...]]]:
    """The objects of ``texts`` that still name a key the generated world does not have.

    ``texts`` are script texts by mod path as the world will carry them; ``present`` lists, by
    kind, the keys the generated world defines. What is found is what ``scan`` finds in the
    vanilla files, minus what the remap and the decisions took away: a name of an American
    location, province, area, region or subcontinent that is gone, by decision key.
    """
    parsed = {relative: (text, parse(text)) for relative, text in texts.items()}
    keywords: set[str] = set()
    for _, root in parsed.values():
        keywords |= _keys(root)
    words = frozenset(keywords)
    found: dict[str, dict[str, set[str]]] = {}
    for relative, (text, root) in parsed.items():
        category = category_of(relative)
        for entry in root.entries:
            if entry.key is None or not isinstance(entry.value, Block):
                continue
            refs = references(text[entry.start : entry.end], footprint, words)
            for kind in GEOGRAPHY:
                lost = refs.get(kind, set()) - present.get(kind, frozenset())
                if lost:
                    found.setdefault(f"{category}:{entry.key}", {}).setdefault(kind, set()).update(
                        lost
                    )
    return {
        key: {kind: tuple(sorted(names)) for kind, names in sorted(kinds.items())}
        for key, kinds in sorted(found.items())
    }


def objects(text: str) -> frozenset[str]:
    """The identifiers of the top-level script objects of ``text``."""
    return frozenset(
        entry.key
        for entry in parse(text).entries
        if entry.key is not None and isinstance(entry.value, Block)
    )


def summarize(consumers: Iterable[Consumer]) -> dict[str, dict[str, int]]:
    """How many consumers each category has, and how many name each kind of key."""
    totals: dict[str, dict[str, int]] = {}
    for consumer in consumers:
        row = totals.setdefault(consumer.category, {"consumers": 0})
        row["consumers"] += 1
        for kind in consumer.refs:
            row[kind] = row.get(kind, 0) + 1
    return dict(sorted(totals.items()))
