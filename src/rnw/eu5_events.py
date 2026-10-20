"""Dynamic historical events of countries the generated New World replaces.

A ``dynamic_historical_event`` fires for the countries named by its ``tag`` entries. Once
a tag's definition is gone with its 1337 setup entry, the engine logs the event as one
"for the unknown country" [V-GAME 1.4.2, C94]. An event whose tags are all removed goes
with them; an event that also serves a kept tag only loses the removed tags' entries.
Nothing else in the file changes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from rnw.pdx import Block, Edits, line_span, parse

DYNAMIC: Final[str] = "dynamic_historical_event"
TAG_ENTRY: Final[re.Pattern[str]] = re.compile(r"(?<![A-Za-z0-9_])tag\s*=\s*([A-Za-z0-9_]+)")


@dataclass(frozen=True, slots=True)
class Retired:
    """Events removed from one text and tag entries removed from events that stay."""

    text: str
    events: tuple[str, ...]
    tags: int


def names_tag(text: str, tags: set[str]) -> bool:
    """Whether any ``tag = X`` of ``text`` names one of ``tags`` (a cheap pre-filter)."""
    return any(match.group(1) in tags for match in TAG_ENTRY.finditer(text))


def retire_events(text: str, tags: set[str]) -> Retired:
    """``text`` without the dynamic historical events of ``tags``."""
    edits = Edits()
    dropped: list[str] = []
    stripped = 0
    for event in parse(text).entries:
        if event.key is None or not isinstance(event.value, Block):
            continue
        entries = [
            tag
            for holder in event.value.find(DYNAMIC)
            if isinstance(holder.value, Block)
            for tag in holder.value.find("tag")
        ]
        gone = [tag for tag in entries if isinstance(tag.value, str) and tag.value in tags]
        if not gone:
            continue
        if len(gone) == len(entries):
            edits.deletions.append(line_span(text, event.start, event.end))
            dropped.append(event.key)
        else:
            edits.deletions.extend(line_span(text, tag.start, tag.end) for tag in gone)
            stripped += len(gone)
    return Retired(edits.apply(text), tuple(dropped), stripped)
