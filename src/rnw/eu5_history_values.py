"""Project society profiles only onto installed, ungated American value ranges."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from rnw.history_checks import require
from rnw.history_model import PERMILLE, Exchange, Military
from rnw.history_values import (
    AXES,
    BELLIGERENCE,
    BOUND,
    CENTRAL,
    EXCHANGE,
    MYSTICISM,
    POSTURE,
    QUALITY,
    SPIRITUAL,
    TRADITION,
)
from rnw.pdx import Block, parse

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from rnw.history_model import Society

INTEGER: Final[re.Pattern[str]] = re.compile(r"-?\d+")


def position_ranges(
    templates: Mapping[str, str],
    used: Collection[str],
    value_texts: Sequence[str],
) -> dict[str, tuple[int, int]]:
    """Read the range; an age gate or absence of American values means summary only.

    Missing definitions, missing used templates, duplicate definitions and malformed
    positions fail explicitly. No inferred default extends the American range.
    """
    definitions: dict[str, Block] = {}
    for text in value_texts:
        for entry in parse(text).entries:
            if entry.key in AXES and isinstance(entry.value, Block):
                require(entry.key not in definitions, f"Repeated societal value {entry.key}")
                definitions[entry.key] = entry.value
    require(set(AXES) <= definitions.keys(), "Missing history societal-value definition")
    require(set(used) <= templates.keys(), "Missing American history template")
    governments = [parse(templates[name]).block("government") for name in sorted(used)]
    ranges: dict[str, tuple[int, int]] = {}
    for axis in AXES:
        values: list[int] = []
        for government in governments:
            entries = list(government.find(axis)) if government is not None else []
            require(len(entries) <= 1, f"Repeated American position on {axis}")
            for entry in entries:
                require(
                    isinstance(entry.value, str) and INTEGER.fullmatch(entry.value) is not None,
                    f"Noninteger American position on {axis}",
                )
                value = int(str(entry.value))
                require(abs(value) <= BOUND, f"American position on {axis} is out of range")
                values.append(value)
        if definitions[axis].first("age") is None and values:
            ranges[axis] = min(values), max(values)
    return ranges


def profile_positions(
    profile: Society,
    ranges: Mapping[str, tuple[int, int]],
) -> tuple[tuple[str, int], ...]:
    """Independent orientations within observed ranges; no flat institutional bonus."""
    military = {
        Military.OFFENSIVE: 0,
        Military.BALANCED: PERMILLE // 2,
        Military.DEFENSIVE: PERMILLE,
    }[profile.military]
    scores = {
        CENTRAL: PERMILLE - profile.centralization,
        TRADITION: PERMILLE - profile.tradition,
        SPIRITUAL: PERMILLE - profile.religious_authority,
        MYSTICISM: PERMILLE - profile.religious_authority,
        POSTURE: military,
        BELLIGERENCE: military,
        QUALITY: PERMILLE - military,
        EXCHANGE: {
            Exchange.OVERLAND: 0,
            Exchange.INWARD: PERMILLE // 2,
            Exchange.COASTAL: PERMILLE,
        }[profile.exchange],
    }
    written: list[tuple[str, int]] = []
    for axis, score in sorted(scores.items()):
        if axis in ranges:
            low, high = ranges[axis]
            require(-BOUND <= low <= high <= BOUND, f"Invalid history range for {axis}")
            require(0 <= score <= PERMILLE, "Invalid history profile position")
            written.append((axis, low + (high - low) * score // PERMILLE))
    return tuple(written)
