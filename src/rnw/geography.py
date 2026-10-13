"""Read the location hierarchy without storing or copying game assets."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, override

if TYPE_CHECKING:
    from pathlib import Path

TOKEN: Final[re.Pattern[str]] = re.compile(r'#[^\n]*|"(?:\\.|[^"\\])*"|[{}=]|[^\s{}=#]+')
COLOR_PAIR: Final[re.Pattern[str]] = re.compile(
    r"^([a-z][a-z0-9_]*)\s*=\s*([0-9a-f]{1,6})\s*$", re.MULTILINE
)
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


def read_locations(path: Path) -> tuple[Location, ...]:
    """Parse five hierarchy levels and the location keys inside provinces."""
    content = path.read_text(encoding="utf-8-sig")
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
        elif index + 2 < len(words) and words[index + 1 : index + 3] == ["=", "{"]:
            if len(stack) >= len(LEVELS):
                raise NestedProvinceError(word)
            stack.append(word)
            index += 2
        elif index + 1 < len(words) and words[index + 1] == "=":
            index += 2  # A scalar attribute, not a location key.
        elif len(stack) == len(LEVELS):
            if word in seen:
                raise DuplicateLocationError(word)
            seen.add(word)
            locations.append(Location(word, *stack))
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


def color_summary(path: Path) -> dict[str, int]:
    """Check the named location to RGB mapping without reading the raster."""
    pairs = [match.groups() for match in COLOR_PAIR.finditer(path.read_text(encoding="utf-8-sig"))]
    colors = Counter(value.zfill(6) for _, value in pairs)
    names = Counter(key for key, _ in pairs)
    return {
        "named_locations": len(pairs),
        "duplicate_names": sum(count - 1 for count in names.values()),
        "duplicate_colors": sum(count - 1 for count in colors.values()),
    }
