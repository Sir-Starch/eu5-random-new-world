"""Read the location hierarchy without storing or copying game assets."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, override

if TYPE_CHECKING:
    from pathlib import Path

TOKEN: Final[re.Pattern[str]] = re.compile(r'#[^\n]*|"(?:\\.|[^"\\])*"|[{}=]|[^\s{}=#]+')
COLOR_PAIR: Final[re.Pattern[str]] = re.compile(r"([A-Za-z][A-Za-z0-9_]*)\s*=\s*([0-9a-fA-F]{1,6})")
LEVELS: Final[tuple[str, ...]] = ("continent", "subcontinent", "region", "area", "province")


@dataclass(frozen=True, slots=True)
class Location:
    """A named map cell and its five geographic parents."""

    key: str
    continent: str
    subcontinent: str
    region: str
    area: str
    province: str


class GeographyError(Exception):
    """A malformed or ambiguous hierarchy that should not be exported."""


class UnexpectedCloseError(GeographyError):
    """A closing brace has no matching open brace."""

    @override
    def __str__(self) -> str:
        return "Unexpected closing brace in definitions"


class UnnamedBlockError(GeographyError):
    """A block has no key."""

    @override
    def __str__(self) -> str:
        return "Unnamed block in definitions"


@dataclass(frozen=True, slots=True)
class NestedProvinceError(GeographyError):
    """A province unexpectedly contains a nested block."""

    key: str

    @override
    def __str__(self) -> str:
        return f"Nested block inside province: {self.key}"


@dataclass(frozen=True, slots=True)
class DuplicateLocationError(GeographyError):
    """A location belongs to more than one province."""

    key: str

    @override
    def __str__(self) -> str:
        return f"Location has multiple parents: {self.key}"


class UnclosedBlockError(GeographyError):
    """The file ends before a block closes."""

    @override
    def __str__(self) -> str:
        return "Unclosed block in definitions"


@dataclass(frozen=True, slots=True)
class MalformedAssignmentError(GeographyError):
    """An assignment has no valid value."""

    key: str

    @override
    def __str__(self) -> str:
        return f"Malformed assignment in definitions: {self.key}"


@dataclass(frozen=True, slots=True)
class UnexpectedTokenError(GeographyError):
    """A token appears outside a province list or assignment."""

    token: str

    @override
    def __str__(self) -> str:
        return f"Unexpected token in definitions: {self.token}"


@dataclass(frozen=True, slots=True)
class MalformedColorEntryError(GeographyError):
    """A non-comment color line does not match the observed format."""

    line_number: int

    @override
    def __str__(self) -> str:
        return f"Malformed named color entry at line {self.line_number}"


def _consume_assignment(words: list[str], index: int, stack: list[str]) -> int:
    key = words[index]
    if index + 2 >= len(words) or words[index + 2] in {"}", "="}:
        raise MalformedAssignmentError(key)
    if words[index + 2] == "{":
        if len(stack) >= len(LEVELS):
            raise NestedProvinceError(key)
        stack.append(key)
    return index + 2


def read_locations(path: Path) -> tuple[Location, ...]:
    """Parse five hierarchy levels and the location keys inside provinces."""
    return parse_locations(path.read_text(encoding="utf-8-sig"))


def parse_locations(content: str) -> tuple[Location, ...]:
    """Parse hierarchy text (already decoded) into locations with their parents."""
    words = [
        match.group() for match in TOKEN.finditer(content) if not match.group().startswith("#")
    ]
    stack: list[str] = []
    locations: list[Location] = []
    seen: set[str] = set()
    index = 0
    while index < len(words):
        word = words[index]
        if word == "}":
            if not stack:
                raise UnexpectedCloseError
            _ = stack.pop()
        elif word == "{":
            raise UnnamedBlockError
        elif index + 1 < len(words) and words[index + 1] == "=":
            index = _consume_assignment(words, index, stack)
        elif len(stack) == len(LEVELS):
            if word == "=":
                raise UnexpectedTokenError(word)
            if word in seen:
                raise DuplicateLocationError(word)
            seen.add(word)
            locations.append(Location(word, *stack))
        else:
            raise UnexpectedTokenError(word)
        index += 1
    if stack:
        raise UnclosedBlockError
    return tuple(locations)


def summary(locations: tuple[Location, ...]) -> dict[str, int]:
    """Count each hierarchy level and the American cell count."""
    counts = {level: len({getattr(item, level) for item in locations}) for level in LEVELS}
    counts["location"] = len(locations)
    counts["american_location"] = sum(item.continent == "america" for item in locations)
    return counts


def read_named_colors(path: Path) -> tuple[tuple[str, int], ...]:
    """Read all observed named-color declarations, including inline comments."""
    pairs: list[tuple[str, int]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        bare = line.partition("#")[0].strip()
        if not bare:
            continue
        match = COLOR_PAIR.fullmatch(bare)
        if match is None:
            raise MalformedColorEntryError(line_number)
        pairs.append((match.group(1), int(match.group(2), 16)))
    return tuple(pairs)


def color_summary(locations: tuple[Location, ...], path: Path) -> dict[str, int]:
    """Compare hierarchy keys with color declarations without reading the raster."""
    pairs = read_named_colors(path)
    colors = Counter(value for _, value in pairs)
    names = Counter(key for key, _ in pairs)
    hierarchy_keys = {item.key for item in locations}
    color_keys = set(names)
    return {
        "named_locations": len(pairs),
        "duplicate_names": sum(count - 1 for count in names.values()),
        "duplicate_colors": sum(count - 1 for count in colors.values()),
        "hierarchy_keys_without_color": len(hierarchy_keys - color_keys),
        "color_keys_outside_hierarchy": len(color_keys - hierarchy_keys),
    }
