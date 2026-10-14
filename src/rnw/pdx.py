"""Span-preserving reader for Paradox script text.

The parser keeps byte offsets for every entry so callers can delete or insert text
without reformatting the rest of a vanilla file: comments, spacing, BOM and line endings
outside edited spans survive untouched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from itertools import pairwise
from typing import TYPE_CHECKING, Final, override

if TYPE_CHECKING:
    from collections.abc import Iterator

LEXICON: Final[str] = (
    r'(?P<comment>#[^\n]*)|(?P<string>"(?:\\.|[^"\\])*")|(?P<op><=|>=|!=|\?=|==|[=<>])'
    r"|(?P<open>\{)|(?P<close>\})|(?P<word>[^\s{}=<>!?#\"]+)|(?P<space>\s+)|(?P<bad>.)"
)
TOKEN: Final[re.Pattern[str]] = re.compile(LEXICON)


@dataclass(frozen=True, slots=True)
class PdxSyntaxError(ValueError):
    """Text that this reader cannot parse unambiguously."""

    reason: str
    offset: int

    @override
    def __str__(self) -> str:
        return f"Paradox script syntax error at offset {self.offset}: {self.reason}"


@dataclass(slots=True)
class Block:
    """A braced list of entries, with the offsets of its braces."""

    entries: list[Entry] = field(default_factory=list)
    open: int = -1
    close: int = -1

    def find(self, key: str) -> Iterator[Entry]:
        """Entries assigned with ``key``, in order."""
        return (entry for entry in self.entries if entry.key == key)

    def first(self, key: str) -> Entry | None:
        """The first entry with ``key``."""
        return next(self.find(key), None)

    def block(self, *path: str) -> Block | None:
        """Follow nested keys to a block."""
        current: Block | None = self
        for key in path:
            entry = current.first(key) if current is not None else None
            current = entry.value if entry is not None and isinstance(entry.value, Block) else None
        return current

    def words(self) -> Iterator[Entry]:
        """Bare scalar entries such as items of a location list."""
        return (
            entry for entry in self.entries if entry.key is None and isinstance(entry.value, str)
        )


@dataclass(slots=True)
class Entry:
    """``key op value``, or a bare value when ``key`` is None; ``start``/``end`` span it."""

    key: str | None
    op: str | None
    value: str | Block
    start: int
    end: int


def parse(text: str) -> Block:
    """Parse a whole file into its root block (offsets index ``text``)."""
    tokens = [
        (match.lastgroup or "", match.group(), match.start(), match.end())
        for match in TOKEN.finditer(text)
        if match.lastgroup not in {"comment", "space"}
    ]
    for kind, value, start, _ in tokens:
        if kind == "bad":
            reason = f"unexpected character {value!r}"
            raise PdxSyntaxError(reason, start)
    root, index = _block(tokens, 0, root=True)
    if index != len(tokens):
        reason = "unbalanced closing brace"
        raise PdxSyntaxError(reason, tokens[index][2])
    root.open, root.close = -1, len(text)
    return root


def _value(tokens: list[tuple[str, str, int, int]], index: int) -> tuple[str | Block, int, int]:
    kind, value, start, end = tokens[index]
    if kind == "open":
        block, after = _block(tokens, index + 1, root=False)
        block.open = start
        return block, block.close + 1, after
    if kind in {"word", "string"}:
        return value, end, index + 1
    reason = f"expected a value, found {value!r}"
    raise PdxSyntaxError(reason, start)


def _block(tokens: list[tuple[str, str, int, int]], index: int, *, root: bool) -> tuple[Block, int]:
    block = Block()
    while index < len(tokens):
        kind, value, start, _ = tokens[index]
        if kind == "close":
            if root:
                return block, index
            block.close = start
            return block, index + 1
        if kind == "op":
            reason = "operator without a key"
            raise PdxSyntaxError(reason, start)
        following = tokens[index + 1] if index + 1 < len(tokens) else None
        if kind in {"word", "string"} and following is not None and following[0] == "op":
            if index + 2 >= len(tokens):
                reason = "assignment without a value"
                raise PdxSyntaxError(reason, following[2])
            parsed, end, index = _value(tokens, index + 2)
            block.entries.append(Entry(value, following[1], parsed, start, end))
            continue
        parsed, end, index = _value(tokens, index)
        block.entries.append(Entry(None, None, parsed, start, end))
    if not root:
        reason = "unclosed block"
        raise PdxSyntaxError(reason, tokens[-1][2] if tokens else 0)
    return block, index


@dataclass(slots=True)
class Edits:
    """Non-overlapping deletions and insertions applied to the original text at once."""

    deletions: list[tuple[int, int]] = field(default_factory=list)
    insertions: list[tuple[int, str]] = field(default_factory=list)

    def delete(self, entry: Entry) -> None:
        """Remove one entry's span."""
        self.deletions.append((entry.start, entry.end))

    def insert(self, offset: int, text: str) -> None:
        """Insert text before ``offset``."""
        self.insertions.append((offset, text))

    def apply(self, text: str) -> str:
        """Return the edited text; overlapping deletions are an error."""
        deletions = sorted(set(self.deletions))
        for (_, first_end), (second_start, _) in pairwise(deletions):
            if second_start < first_end:
                message = "overlapping deletions"
                raise ValueError(message)
        events: list[tuple[int, int, int, str]] = [(start, 1, end, "") for start, end in deletions]
        events += [(offset, 0, offset, inserted) for offset, inserted in self.insertions]
        events.sort(key=lambda item: (item[0], item[1]))
        parts: list[str] = []
        cursor = 0
        for offset, kind, end, inserted in events:
            if offset < cursor:
                message = "edit inside a deleted span"
                raise ValueError(message)
            parts.append(text[cursor:offset])
            if kind == 0:
                parts.append(inserted)
                cursor = offset
            else:
                cursor = end
        parts.append(text[cursor:])
        return "".join(parts)
