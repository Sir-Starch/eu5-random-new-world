"""Valve's text KeyValues format, as far as Steam's library and app manifests use it.

``"key" "value"`` pairs and ``"key" { ... }`` sections, with ``//`` comments and the
escapes ``\\\\``, ``\\"``, ``\\n`` and ``\\t`` inside quotes. Keys are case-insensitive in
Valve's format (Steam writes ``"libraryfolders"``, the Steam stub in a Proton prefix
``"LibraryFolders"``), so they are kept in lower case. Duplicate keys keep the last value.
"""

from __future__ import annotations

import re
from typing import Final

TOKEN: Final[re.Pattern[str]] = re.compile(r'"((?:\\.|[^"\\])*)"|(\{)|(\})|//[^\n]*|\s+|(.)')
ESCAPE: Final[re.Pattern[str]] = re.compile(r"\\(.)")
ESCAPES: Final[dict[str, str]] = {"\\": "\\", '"': '"', "n": "\n", "t": "\t"}

type Section = dict[str, str | Section]


class VdfError(ValueError):
    """Text that is not KeyValues."""


def _unescape(text: str) -> str:
    return ESCAPE.sub(lambda match: ESCAPES.get(match.group(1), match.group(1)), text)


def parse(text: str) -> Section:
    """The sections and values of a KeyValues file, as nested dictionaries with lower-case keys."""
    root: Section = {}
    stack: list[Section] = [root]
    pending: str | None = None
    for match in TOKEN.finditer(text):
        quoted, opening, closing, stray = match.groups()
        if stray is not None:
            message = f"unexpected character {stray!r} at offset {match.start()}"
            raise VdfError(message)
        if quoted is not None:
            word = _unescape(quoted)
            if pending is None:
                pending = word.lower()
            else:
                stack[-1][pending] = word
                pending = None
        elif opening is not None:
            if pending is None:
                message = f"a section without a name at offset {match.start()}"
                raise VdfError(message)
            section: Section = {}
            stack[-1][pending] = section
            stack.append(section)
            pending = None
        elif closing is not None:
            if len(stack) == 1 or pending is not None:
                message = f"unbalanced closing brace at offset {match.start()}"
                raise VdfError(message)
            _ = stack.pop()
    if len(stack) != 1 or pending is not None:
        message = "unclosed section or key without a value"
        raise VdfError(message)
    return root
