"""Construct native town setups within the installed game's building capacity.

Historical town templates describe historical populations and development. Their
guild levels are not portable to a newly generated settlement. Read the native
capacity formula and derive only those templates whose initial levels need a
different capacity. No building rule or running campaign is modified.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING

from rnw.pdx import Block, parse

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

TOWNS = "in_game/common/town_setups/rnw_starting_towns.txt"


class TownError(ValueError):
    """A town template or its capacity contract cannot be established."""


def _scalar(block: Block, key: str) -> str:
    entry = block.first(key)
    if entry is None or not isinstance(entry.value, str):
        message = f"Missing scalar {key} in the town capacity contract"
        raise TownError(message)
    return entry.value


def _keys(block: Block) -> list[str | None]:
    """Descriptions affect the tooltip, not the arithmetic being verified."""
    return [entry.key for entry in block.entries if entry.key != "desc"]


@dataclass(frozen=True)
class GuildCapacity:
    base: Fraction
    development: Fraction
    population: Fraction
    ranks: Mapping[str, Fraction]
    market_minimum: Fraction
    minimum: Fraction

    def guaranteed(self, rank: str, development: int, population: int) -> int:
        """A legal level for any initial market access, with exact rational arithmetic."""
        value = (
            self.base
            + self.development * development / 1000
            + self.population * population / 1000
            + self.ranks.get(rank, Fraction(0))
        )
        return int(max(self.minimum, value * min(Fraction(1), self.market_minimum)))


def _guild_terms(root: Block) -> dict[str, Fraction]:
    terms: dict[str, Fraction] = {}
    for entry in root.find("add"):
        if not isinstance(entry.value, Block):
            message = "A guild capacity term changed"
            raise TownError(message)
        term = _scalar(entry.value, "value")
        factor = entry.value.first("multiply")
        if _keys(entry.value) != (["value", "multiply"] if factor is not None else ["value"]) or (
            factor is not None and not isinstance(factor.value, str)
        ):
            message = "The installed guild capacity operations changed"
            raise TownError(message)
        terms[term] = Fraction(str(factor.value)) if factor is not None else Fraction(1)
    if set(terms) != {"1", "development", "population"} or any(v < 0 for v in terms.values()):
        message = "The installed guild base terms changed"
        raise TownError(message)
    return terms


def guild_capacity(text: str) -> GuildCapacity:
    """Read the known native formula, refusing a changed or additional operation."""
    root = parse(text).block("guild_max_level")
    if root is None or [e.key for e in root.entries] != [
        "add",
        "add",
        "add",
        "if",
        "if",
        "if",
        "if",
        "min",
    ]:
        message = "The installed guild capacity formula changed"
        raise TownError(message)
    terms = _guild_terms(root)
    ranks: dict[str, Fraction] = {}
    market_minimum: Fraction | None = None
    for entry in root.find("if"):
        if not isinstance(entry.value, Block) or (limit := entry.value.block("limit")) is None:
            message = "A guild capacity condition changed"
            raise TownError(message)
        rank = limit.first("location_rank")
        if rank is not None and isinstance(rank.value, str):
            name = rank.value.removeprefix("location_rank:")
            if name == "rural_settlement":
                continue  # Generated town setups are applied only to urban ranks.
            add = entry.value.block("add")
            if (
                name not in {"city", "megalopolis"}
                or len(limit.entries) != 1
                or add is None
                or _keys(entry.value) != ["limit", "add"]
                or _keys(add) != ["value"]
            ):
                message = "The urban guild capacity bonuses changed"
                raise TownError(message)
            ranks[name] = Fraction(_scalar(add, "value"))
        else:
            access = limit.first("market_access")
            multiply = entry.value.block("multiply")
            if (
                access is None
                or access.op != "<"
                or len(limit.entries) != 1
                or multiply is None
                or _scalar(multiply, "value") != "market_access"
                or _keys(entry.value) != ["limit", "multiply"]
                or _keys(multiply) != ["value", "add"]
                or not isinstance(access.value, str)
                or Fraction(access.value) <= 0
            ):
                message = "The guild market-access capacity rule changed"
                raise TownError(message)
            market_minimum = Fraction(_scalar(multiply, "add"))
    if market_minimum is None or market_minimum < 0 or any(v < 0 for v in ranks.values()):
        message = "No nonnegative guild market-access lower bound"
        raise TownError(message)
    return GuildCapacity(
        terms["1"],
        terms["development"],
        terms["population"],
        ranks,
        market_minimum,
        Fraction(_scalar(root, "min")),
    )


def _guild_alias(root: Block, key: str) -> bool:
    """The native aliases only add a modifier guarded to be positive."""
    if key == "guild_max_level":
        return True
    block = root.block(key)
    add_guild = block.first("add") if block is not None else None
    if (
        block is None
        or add_guild is None
        or add_guild.value != "guild_max_level"
        or block.entries[0] is not add_guild
    ):
        return False
    for entry in block.entries[1:]:
        if entry.key != "if" or not isinstance(entry.value, Block):
            return False
        limit = entry.value.block("limit")
        add = entry.value.block("add")
        if (
            limit is None
            or len(limit.entries) != 1
            or add is None
            or _keys(entry.value) != ["limit", "add"]
            or _keys(add) != ["value"]
        ):
            return False
        condition = limit.entries[0]
        if condition.op != ">" or condition.value != "0" or condition.key != _scalar(add, "value"):
            return False
    return True


@dataclass(frozen=True)
class TownPlan:
    ranks: dict[str, tuple[str, str]]
    definitions: dict[str, dict[str, int]]
    adjusted_locations: int

    def files(self) -> dict[str, bytes]:
        if not self.definitions:
            return {}
        text = "\n".join(
            f"{key} = {{\n"
            + "".join(f"\t{building} = {level}\n" for building, level in levels.items())
            + "}\n"
            for key, levels in self.definitions.items()
        )
        return {TOWNS: text.encode("utf-8-sig")}


def _levels(
    template: Block, caps: Mapping[str, str | Block], values: Block, limit: int
) -> tuple[dict[str, int], dict[str, int]]:
    original: dict[str, int] = {}
    levels: dict[str, int] = {}
    for entry in template.entries:
        if entry.key is None or entry.key not in caps or not isinstance(entry.value, str):
            message = "Unsupported native town building"
            raise TownError(message)
        amount = int(entry.value)
        if amount < 1:
            message = "Nonpositive native town building"
            raise TownError(message)
        cap = caps[entry.key]
        if not isinstance(cap, str):
            message = f"Unsupported native starting-building capacity: {entry.key}"
            raise TownError(message)
        original[entry.key] = amount
        if cap.replace(".", "", 1).isdigit():
            amount = min(amount, int(Fraction(cap)))
        elif _guild_alias(values, cap):
            amount = min(amount, limit)
        else:
            formula = values.block(cap)
            if formula is not None and any(e.value == "guild_max_level" for e in formula.entries):
                message = f"The installed guild capacity alias changed: {cap}"
                raise TownError(message)
        if amount < 1:
            message = "A native town building has no guaranteed starting capacity"
            raise TownError(message)
        levels[entry.key] = amount
    return original, levels


def plan_towns(
    game_dir: Path,
    ranks: Mapping[str, tuple[str, str]],
    development: Mapping[str, int],
    population: Mapping[str, int],
) -> TownPlan:
    """Derive compatible setups once, before any initial buildings are written."""
    if not ranks:
        return TownPlan({}, {}, 0)
    common = game_dir / "game/in_game/common"
    templates: dict[str, Block] = {}
    for path in sorted((common / "town_setups").glob("*.txt")):
        templates.update(
            {
                str(e.key): e.value
                for e in parse(path.read_text(encoding="utf-8-sig")).entries
                if isinstance(e.value, Block)
            }
        )
    caps: dict[str, str | Block] = {}
    for path in sorted((common / "building_types").glob("*.txt")):
        for entry in parse(path.read_text(encoding="utf-8-sig")).entries:
            if isinstance(entry.value, Block) and (cap := entry.value.first("max_levels")):
                caps[str(entry.key)] = cap.value
    values = (common / "script_values/building_caps.txt").read_text(encoding="utf-8-sig")
    capacity, value_root = guild_capacity(values), parse(values)
    definitions: dict[str, dict[str, int]] = {}
    planned: dict[str, tuple[str, str]] = {}
    adjusted = 0
    for location, (rank, template) in ranks.items():
        name = template
        if rank not in {"town", "city", "megalopolis"} or name not in templates:
            message = f"Unknown native urban setup {rank}/{name}"
            raise TownError(message)
        limit = capacity.guaranteed(rank, development[location], population[location])
        original, levels = _levels(templates[name], caps, value_root, limit)
        if levels != original:
            digest = hashlib.sha256(repr(sorted(levels.items())).encode()).hexdigest()[:12]
            key = f"rnw_{name}_{digest}"
            if key in templates or (key in definitions and definitions[key] != levels):
                message = "A generated town setup identifier collides"
                raise TownError(message)
            definitions[key] = levels
            name = key
            adjusted += 1
        planned[location] = (rank, name)
    return TownPlan(planned, definitions, adjusted)
