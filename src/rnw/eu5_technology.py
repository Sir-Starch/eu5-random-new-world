"""Technology and regional families of the generated native states (R7b).

NOT GAME VALIDATED. In EU5 1.4.3 an age-of-traditions advance whose
``starting_technology_level`` is higher than the country's own starts unresearched, so a
higher level starts a country with more of them [V-LOCAL C155; INFERRED]. Vanilla gives its
American states level 2 in 86% of the cases and the generator wrote no level at all, so a
state took the level of its culture's template [V-EXEC C156]. A state now takes its level from
the complexity of its capital, on the vanilla distribution (the rule of the harbours in
``eu5_development``), and its template follows the level, as in vanilla.

The regional advance trees and units of the Americas are gated by two scripted triggers on the
capital's region or area [V-LOCAL C157]. A culture belongs to the family of the land it
lives on, so ``families`` reads the triggers and the homeland vector of a culture or a zone
gains the shares of the three families.

Pure functions on texts and lists, like ``eu5_development``; all arithmetic is integer.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.pdx import Block, parse

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping, Sequence


PERMILLE: Final[int] = 1000
MESOAMERICA: Final[str] = "mesoamerica"
SOUTH_AMERICA: Final[str] = "south_america"
NORTH_AMERICA: Final[str] = "north_america"
FAMILIES: Final[tuple[str, ...]] = (MESOAMERICA, SOUTH_AMERICA, NORTH_AMERICA)
# The scripted triggers that select a family from the capital; a capital that neither matches
# is North American [V-LOCAL C157].
FAMILY_TRIGGERS: Final[tuple[tuple[str, str], ...]] = (
    ("is_capital_mesoamerica", MESOAMERICA),
    ("is_capital_in_south_america_or_carribean", SOUTH_AMERICA),
)
TRIGGER_FILE: Final[str] = "game/in_game/common/scripted_triggers/location_triggers.txt"
# The family shares of a homeland count twice, like its climate [INFERRED design]. The one
# free constant of R7b: it decides how much a culture follows the land it lives on.
FAMILY_WEIGHT: Final[int] = 2
NO_LEVEL: Final[str] = "none"


class TechnologyError(ValueError):
    """Vanilla technology or family data is missing or inconsistent."""


@dataclass(frozen=True, slots=True, eq=False)
class Families:
    """The regional family of the vanilla regions and areas the triggers list."""

    by_region: dict[str, str]
    by_area: dict[str, str]

    def of(self, region: str, area: str) -> str:
        """Family of a location in ``region`` and ``area``: an area or region the first
        trigger lists makes it Mesoamerican, one the second lists South American."""
        found = {self.by_area.get(area), self.by_region.get(region)}
        return next((name for _, name in FAMILY_TRIGGERS if name in found), NORTH_AMERICA)


def _listed(block: Block, key: str, prefix: str) -> list[str]:
    """Every ``<key> = <prefix><name>`` in ``block`` and the blocks nested in it."""
    found: list[str] = []
    for entry in block.entries:
        if isinstance(entry.value, Block):
            found += _listed(entry.value, key, prefix)
        elif entry.key == key and entry.value.startswith(prefix):
            found.append(entry.value.removeprefix(prefix))
    return found


def families(text: str, regions: Collection[str], areas: Collection[str]) -> Families:
    """Read the family triggers; ``regions`` and ``areas`` are those of the vanilla Americas.

    Fails if a trigger is missing, lists nothing, or lists a key that is no American region
    or area.
    """
    root = parse(text)
    by_region: dict[str, str] = {}
    by_area: dict[str, str] = {}
    for trigger, family in FAMILY_TRIGGERS:
        block = root.block(trigger)
        if block is None:
            message = f"Scripted trigger {trigger} is missing"
            raise TechnologyError(message)
        listed_regions = _listed(block, "region", "region:")
        listed_areas = _listed(block, "area", "area:")
        if not listed_regions and not listed_areas:
            message = f"Scripted trigger {trigger} lists no region or area"
            raise TechnologyError(message)
        unknown = sorted(set(listed_regions) - set(regions)) + sorted(
            set(listed_areas) - set(areas)
        )
        if unknown:
            message = (
                f"Scripted trigger {trigger} lists {unknown[0]}, no region or area of the Americas"
            )
            raise TechnologyError(message)
        for name in listed_regions:
            _ = by_region.setdefault(name, family)
        for name in listed_areas:
            _ = by_area.setdefault(name, family)
    return Families(by_region=by_region, by_area=by_area)


def family_shares(members: Sequence[str], weights: Sequence[int]) -> list[int]:
    """Permille of ``weights`` in each family of ``FAMILIES``, times ``FAMILY_WEIGHT``."""
    total = max(1, sum(weights))
    sums = Counter[str]()
    for family, weight in zip(members, weights, strict=True):
        sums[family] += weight
    return [FAMILY_WEIGHT * sums[family] * PERMILLE // total for family in FAMILIES]


def plain(vector: Sequence[int]) -> tuple[int, ...]:
    """A homeland vector without its family entries."""
    return tuple(vector[: -len(FAMILIES)])


def without_families(vector: Sequence[int]) -> tuple[int, ...]:
    """A homeland vector with its family entries at zero: the same as a family weight of 0."""
    return (*plain(vector), *(0 for _ in FAMILIES))


def majority(members: Sequence[str], weights: Sequence[int]) -> str:
    """The family with the most weight, ties by name."""
    sums = Counter[str]()
    for family, weight in zip(members, weights, strict=True):
        sums[family] += weight
    return min(sums, key=lambda name: (-sums[name], name)) if sums else ""


def _own_level(block: Block, levels: Mapping[str, int]) -> int | None:
    own = block.first("starting_technology_level")
    if own is not None and isinstance(own.value, str) and own.value.isdigit():
        return int(own.value)
    known = [
        levels[name]
        for include in block.find("include")
        if isinstance(include.value, str)
        if (name := include.value.strip('"')) in levels
    ]
    return max(known) if known else None


def vanilla_state_levels(
    setup_text: str, levels: Mapping[str, int], american: Collection[str]
) -> tuple[int, ...]:
    """Sorted starting technology levels of the vanilla American landed countries.

    A country takes the level its entry writes, else the highest level among its includes
    (``levels``, the templates with theirs). A country with neither is left out, and so is
    every country that is not landed or holds a location outside ``american``.
    """
    holder = parse(setup_text).block("countries", "countries")
    found: list[int] = []
    for entry in holder.entries if holder is not None else []:
        if entry.key is None or not isinstance(entry.value, Block) or _is_pop(entry.value):
            continue
        held = _held(entry.value)
        if not held or not set(held) <= set(american):
            continue
        level = _own_level(entry.value, levels)
        if level is not None:
            found.append(level)
    if not found:
        message = "No vanilla American landed country has a starting technology level"
        raise TechnologyError(message)
    return tuple(sorted(found))


def _is_pop(block: Block) -> bool:
    kind = block.first("type")
    return kind is not None and kind.value == "pop"


def _held(block: Block) -> list[str]:
    held: list[str] = []
    for key in ("own_control_core", "own_control_integrated"):
        locations = block.block(key)
        if locations is not None:
            held += [word.value for word in locations.words() if isinstance(word.value, str)]
    return held


def quantile_levels(count: int, vanilla: Sequence[int]) -> list[int]:
    """Levels of ``count`` states in the order of rising complexity.

    The state of 0-based rank ``i`` takes the vanilla level at index ``(2i + 1) m // (2n)``
    of the ``m`` sorted levels, so the vanilla distribution is reproduced on any world
    [INFERRED design, the rule of the harbours].
    """
    if count and not vanilla:
        message = "No vanilla levels to take quantiles of"
        raise TechnologyError(message)
    return [vanilla[(2 * rank + 1) * len(vanilla) // (2 * count)] for rank in range(count)]


def state_levels(order: Sequence[tuple[int, int, str]], vanilla: Sequence[int]) -> list[int]:
    """Level of each state given as (capital complexity, capital population, tag).

    The states rise by complexity, then population, then tag; the result is in the order of
    ``order``.
    """
    ranked = sorted(range(len(order)), key=lambda number: order[number])
    out = [0] * len(order)
    for number, level in zip(ranked, quantile_levels(len(order), vanilla), strict=True):
        out[number] = level
    return out


def template_for_level(
    own: str, level: int, levels: Mapping[str, int], *, advanced: str, default: str
) -> str:
    """The state template of a level.

    A culture's own vanilla template stays within one level of it, as vanilla pairs them: a
    written level is the template's or one more. Otherwise the advanced template serves a
    level it reaches and the default one the rest. A template without a level counts as 0.
    """
    if own:
        base = levels.get(own, 0)
        if base <= level <= base + 1:
            return own
    return advanced if level >= levels.get(advanced, 0) else default


def histogram(values: Iterable[int | None]) -> dict[str, int]:
    """Count of each value, sorted, ``none`` for a country without a level."""
    counts = Counter(NO_LEVEL if value is None else str(value) for value in values)
    return dict(sorted(counts.items()))


def agreement_permille(agree: int, total: int) -> int:
    """Permille of ``total`` that agree."""
    return agree * PERMILLE // total if total else 0


def homeland_distance(
    zones: Sequence[tuple[tuple[int, ...], int]],
    chosen: Sequence[str],
    homelands: Mapping[str, tuple[int, ...]],
) -> int:
    """Population-weighted mean L1 distance, family entries left out, of zones to their culture."""
    total = sum(people for _, people in zones)
    near = sum(
        people * sum(abs(a - b) for a, b in zip(plain(vector), plain(homelands[name]), strict=True))
        for (vector, people), name in zip(zones, chosen, strict=True)
    )
    return near // max(1, total)


def written_records(text: str, tags: Collection[str]) -> dict[str, tuple[list[str], list[str]]]:
    """Includes and written technology levels of the country records of ``tags``."""
    holder = parse(text).block("countries", "countries")
    out: dict[str, tuple[list[str], list[str]]] = {}
    for entry in holder.entries if holder is not None else []:
        if entry.key is not None and entry.key in tags and isinstance(entry.value, Block):
            includes = [
                include.value.strip('"')
                for include in entry.value.find("include")
                if isinstance(include.value, str)
            ]
            written = [
                level.value
                for level in entry.value.find("starting_technology_level")
                if isinstance(level.value, str)
            ]
            out[entry.key] = (includes, written)
    return out


def technology_report(  # noqa: PLR0913 - the report names each of its numbers.
    *,
    states: Sequence[tuple[str, int]],
    vanilla: Sequence[int],
    tribes: Iterable[int | None],
    replaced: int,
    agreement: Mapping[str, int],
    distance: Mapping[str, int],
    vassals: int,
) -> dict[str, object]:
    """The ``technology`` section of ``report.json``."""
    at: dict[str, list[str]] = {}
    for tag, level in sorted(states):
        at.setdefault(str(level), []).append(tag)
    return {
        "state_levels": histogram(level for _, level in states),
        "vanilla_state_levels": histogram(vanilla),
        "tags_at_level": dict(sorted(at.items())),
        "tribe_template_levels": histogram(tribes),
        "templates_replaced": replaced,
        "family_agreement_permille": dict(agreement),
        "homeland_distance": dict(distance),
        "vassals": vassals,
    }
