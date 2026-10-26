"""A historical urban template must fit a generated settlement's native capacity."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.eu5_towns import TOWNS, TownError, guild_capacity, plan_towns
from rnw.pdx import parse

if TYPE_CHECKING:
    from pathlib import Path

CAPACITY = """guild_max_level={
 add={desc="BASE_TOOLTIP" value=1} add={value=development multiply=0.1}
 add={value=population multiply=0.05}
 if={limit={location_rank ?= location_rank:city} add={value=5}}
 if={limit={location_rank ?= location_rank:megalopolis} add={value=10}}
 if={limit={location_rank ?= location_rank:rural_settlement has_variable=extra} add={value=2}}
 if={limit={market_access < 0.75} multiply={value=market_access add=0.25}}
 min=1
}
cloth_max={add=guild_max_level
 if={limit={modifier:cloth_bonus > 0} add={value=modifier:cloth_bonus}}}
market_max={add={value=1}}
"""


def _game(root: Path) -> Path:
    common = root / "game/in_game/common"
    for folder in ("town_setups", "building_types", "script_values"):
        (common / folder).mkdir(parents=True)
    _ = (common / "town_setups/default.txt").write_text(
        "highland_town={temple=1 granary=2 cloth=2 market=1}"
    )
    _ = (common / "building_types/default.txt").write_text(
        """temple={max_levels=1} granary={max_levels=guild_max_level}
        cloth={max_levels=cloth_max} market={max_levels=market_max}
        unused={max_levels={value=1 if={limit={always=yes} add=1}}}"""
    )
    _ = (common / "script_values/building_caps.txt").write_text(CAPACITY)
    return root


def test_capacity_is_legal_even_at_the_worst_initial_market_access() -> None:
    rule = guild_capacity(CAPACITY)
    assert rule.guaranteed("town", 8000, 2000) == 1
    assert rule.guaranteed("city", 20000, 100000) == 3
    # Independent native equation, across market access and every urban rank.
    for rank, bonus in (("town", 0), ("city", 5), ("megalopolis", 10)):
        for development in (0, 8, 20, 55):
            for population in (0, 2, 20, 100):
                safe = rule.guaranteed(rank, development * 1000, population * 1000)
                for access in (0, 0.1, 0.5, 0.74, 0.75, 1):
                    actual = 1 + development / 10 + population / 20 + bonus
                    if access < 0.75:
                        actual *= access + 0.25
                    assert safe <= int(max(1, actual))


def test_setup_uses_native_capacity_without_inflating_the_generated_settlement(
    tmp_path: Path,
) -> None:
    game = _game(tmp_path)
    ranks = {"small": ("town", "highland_town"), "large": ("city", "highland_town")}
    planned = plan_towns(
        game, ranks, {"small": 8000, "large": 20000}, {"small": 2000, "large": 100000}
    )
    assert planned.ranks["large"] == ranks["large"]
    assert planned.ranks["small"][0] == "town"
    assert ranks["small"] == ("town", "highland_town")
    assert planned.adjusted_locations == 1
    text = planned.files()[TOWNS]
    assert text.startswith(b"\xef\xbb\xbf")
    town = parse(text.decode("utf-8-sig")).block(planned.ranks["small"][1])
    assert town is not None
    assert {e.key: e.value for e in town.entries} == {
        "temple": "1",
        "granary": "1",
        "cloth": "1",
        "market": "1",
    }
    assert (
        plan_towns(game, ranks, {"small": 8000, "large": 20000}, {"small": 2000, "large": 100000})
        == planned
    )


def test_capacity_drift_and_missing_templates_fail_loudly(tmp_path: Path) -> None:
    with pytest.raises(TownError, match="formula changed"):
        _ = guild_capacity(CAPACITY.replace("min=1", "min=1 add=2"))
    with pytest.raises(TownError, match="Unknown native urban setup"):
        _ = plan_towns(_game(tmp_path), {"a": ("town", "missing")}, {"a": 0}, {"a": 0})


def test_unrecognised_guild_alias_is_refused_instead_of_preserving_excess_levels(
    tmp_path: Path,
) -> None:
    game = _game(tmp_path)
    values = game / "game/in_game/common/script_values/building_caps.txt"
    _ = values.write_text(CAPACITY.replace("add={value=modifier:cloth_bonus}", "multiply=0.5"))
    with pytest.raises(TownError, match="alias changed"):
        _ = plan_towns(game, {"a": ("town", "highland_town")}, {"a": 0}, {"a": 0})
