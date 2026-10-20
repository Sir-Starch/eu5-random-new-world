"""Dynamic historical events of countries the generated New World replaces.

A ``dynamic_historical_event`` fires for the countries named by its ``tag`` entries. Once
a tag's definition is gone with its 1337 setup entry, the engine logs the event as one
"for the unknown country" [V-GAME 1.4.2, C94]. An event whose tags are all removed goes
with them; an event that also serves a kept tag only loses the removed tags' entries.
An event that only the removed ones fired (the follow-ups of a chain) would be logged as
orphaned [V-GAME 1.4.2, C97], so it goes too, and so on down the chain. The static
modifiers that only dropped events applied are logged as unused [V-GAME 1.4.2, C100] and
leave their files. Nothing else changes.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Final

from rnw.eu5_rewrite import drop_block_entries
from rnw.pdx import Block, Edits, Entry, line_span, parse

DYNAMIC: Final[str] = "dynamic_historical_event"
TAG_ENTRY: Final[re.Pattern[str]] = re.compile(r"(?<![A-Za-z0-9_])tag\s*=\s*([A-Za-z0-9_]+)")
STATIC_MODIFIERS: Final[str] = "/static_modifiers/"
DEFINITION: Final[re.Pattern[str]] = re.compile(r"^([A-Za-z0-9_]+)\s*=\s*\{", re.MULTILINE)
WORD: Final[re.Pattern[str]] = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
EVENT_ID: Final[re.Pattern[str]] = re.compile(
    r"(?<![A-Za-z0-9_.])([A-Za-z_][A-Za-z0-9_]*\.[0-9]+)(?![0-9])"
)


@dataclass(frozen=True, slots=True)
class Retired:
    """Events removed from one text and tag entries removed from events that stay."""

    text: str
    events: tuple[str, ...]
    tags: int
    removed: str = ""


def names_tag(text: str, tags: set[str]) -> bool:
    """Whether any ``tag = X`` of ``text`` names one of ``tags`` (a cheap pre-filter)."""
    return any(match.group(1) in tags for match in TAG_ENTRY.finditer(text))


def mentions(text: str) -> Counter[str]:
    """How often ``text`` names each event id (``namespace.number``)."""
    return Counter(EVENT_ID.findall(text))


def _dynamic_tags(event: Block) -> list[Entry]:
    """Every ``tag`` entry of the event's dynamic historical blocks."""
    return [
        tag
        for holder in event.find(DYNAMIC)
        if isinstance(holder.value, Block)
        for tag in holder.value.find("tag")
    ]


def retire_events(text: str, tags: set[str], elsewhere: Counter[str] | None = None) -> Retired:
    """``text`` without the dynamic historical events of ``tags`` and the chains they led.

    ``elsewhere`` counts the event ids named by the files other than ``text``; a follow-up
    event that nothing outside the dropped events names is dropped as well.
    """
    events = {
        entry.key: (entry, entry.value)
        for entry in parse(text).entries
        if entry.key is not None and isinstance(entry.value, Block)
    }
    edits = Edits()
    dropped: list[str] = []
    stripped = 0
    for key, (_, block) in events.items():
        entries = _dynamic_tags(block)
        gone = [tag for tag in entries if isinstance(tag.value, str) and tag.value in tags]
        if not gone:
            continue
        if len(gone) == len(entries):
            dropped.append(key)
        else:
            edits.deletions.extend(line_span(text, tag.start, tag.end) for tag in gone)
            stripped += len(gone)
    inside = {key: mentions(text[entry.start : entry.end]) for key, (entry, _) in events.items()}
    here = mentions(text)
    queue = list(dropped)
    while queue and elsewhere is not None:
        done = queue.pop()
        here.subtract(inside[done])
        for candidate in inside[done]:
            if candidate in events and candidate not in dropped:
                outside = elsewhere[candidate] + here[candidate] - inside[candidate][candidate]
                if outside <= 0:
                    dropped.append(candidate)
                    queue.append(candidate)
    edits.deletions.extend(
        line_span(text, events[key][0].start, events[key][0].end) for key in dropped
    )
    gone = "".join(text[events[key][0].start : events[key][0].end] for key in dropped)
    return Retired(edits.apply(text), tuple(dropped), stripped, gone)


def retire_modifiers(texts: dict[str, str], removed: str) -> tuple[dict[str, str], tuple[str, ...]]:
    """Static modifier files without the modifiers only the ``removed`` events applied.

    ``texts`` holds every script text by path as it will be written. A modifier goes if
    ``removed`` names it, a file under ``static_modifiers`` defines it, and nothing else
    names it but its own definition. Returns the changed files and the modifiers dropped.
    """
    used = set(WORD.findall(removed))
    home: dict[str, str] = {}
    for path, text in texts.items():
        if STATIC_MODIFIERS in path:
            defined: list[str] = DEFINITION.findall(text)
            home.update({name: path for name in defined if name in used})
    if not home:
        return {}, ()
    pattern = re.compile(
        r"(?<![A-Za-z0-9_])(" + "|".join(sorted(map(re.escape, home))) + r")(?![A-Za-z0-9_])"
    )
    counts: Counter[str] = Counter()
    for text in texts.values():
        counts.update(pattern.findall(text))
    gone = sorted(name for name in home if counts[name] <= 1)
    changed: dict[str, str] = {}
    for path in sorted({home[name] for name in gone}):
        changed[path] = drop_block_entries(
            texts[path], (), {name for name in gone if home[name] == path}
        )
    return changed, tuple(gone)
