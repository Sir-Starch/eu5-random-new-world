"""Physical key assignment on synthetic templates and compact contact graphs (N5)."""

from __future__ import annotations

from dataclasses import replace
from itertools import permutations
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw.eu5_biomes import CellBiomes
from rnw.eu5_map import DEFINITIONS, load_map
from rnw.eu5_regionkeys import (
    KeyMatcher,
    RegionKeyError,
    Trait,
    distance,
    minimum_assignment,
    physical_keys,
    profile,
)
from rnw.geography import read_locations
from rnw.model import CellClass
from rnw.newworld import derive_world
from rnw.topology import adjacency_pairs, unpack_pairs
from tests.fixtures_eu5 import make_install

if TYPE_CHECKING:
    from pathlib import Path

COLD = Trait("arctic", "mountains", 100, coastal=False)
WARM = Trait("tropical", "flatland", 100, coastal=True)


def test_physical_matching_moves_keys_to_comparable_land() -> None:
    matcher = KeyMatcher({"cold": profile([COLD]), "warm": profile([WARM])}, {0: WARM, 1: COLD})
    parts = [[0], [1]]
    assert matcher.pair(parts, ["cold", "warm"], [0, 1]) == [1, 0]
    assert parts == [[0], [1]]  # assignment cannot change connected boundaries
    assert all(row["cost"] == 0 and row["moved"] for row in matcher.assignments)
    assert all(row["positional_cost"] == 9000 for row in matcher.assignments)


def test_extra_areas_take_no_vanilla_key_and_all_keys_are_used_once() -> None:
    matcher = KeyMatcher({"cold": profile([COLD])}, {0: WARM, 1: COLD, 2: WARM})
    assert matcher.pair([[0], [1], [2]], ["cold"], [0, -1, -1]) == [-1, 0, -1]
    assert len(matcher.assignments) == 1


def test_physical_ties_keep_positional_keys_and_are_repeatable() -> None:
    for _ in range(3):
        matcher = KeyMatcher(
            {"a": profile([COLD]), "b": profile([COLD])}, dict.fromkeys(range(3), COLD)
        )
        assert matcher.pair([[0], [1], [2]], ["a", "b"], [1, -1, 0]) == [1, -1, 0]


def test_profiles_are_pixel_weighted_and_normalize_relief() -> None:
    traits = [Trait("arctic", "mountain_wasteland", 300, coastal=False), WARM]
    result = profile(traits)
    assert result == profile(reversed(traits))
    assert result.climate == {"arctic": 750, "tropical": 250}
    assert result.topography == {"flatland": 250, "mountains": 750}
    assert result.coast == 250
    assert result.pixels == 400
    assert distance(result, result, (400, 400)) == (0, 0, 0, 0)
    assert distance(profile([COLD]), profile([COLD]), (100, 200)) == (0, 0, 0, 500)


@pytest.mark.parametrize("dimension", ["climate", "topography", "coast", "size"])
def test_each_dimension_can_decide_an_assignment(dimension: str) -> None:
    first, second = {
        "climate": (
            Trait("arctic", "hills", 100, coastal=False),
            Trait("tropical", "hills", 100, coastal=False),
        ),
        "topography": (COLD, Trait("arctic", "flatland", 100, coastal=False)),
        "coast": (COLD, Trait("arctic", "mountains", 100, coastal=True)),
        "size": (COLD, Trait("arctic", "mountains", 900, coastal=False)),
    }[dimension]
    matcher = KeyMatcher({"a": profile([first]), "b": profile([second])}, {0: second, 1: first})
    assert matcher.pair([[0], [1]], ["a", "b"], [0, 1]) == [1, 0]


def test_region_assignment_reserves_room_for_child_areas() -> None:
    matcher = KeyMatcher(
        {"large": profile([COLD]), "small": profile([WARM])}, {0: COLD, 1: WARM, 2: WARM}
    )
    assert matcher.pair(
        [[0], [1, 2]], ["large", "small"], [0, 1], minimum={"large": 2, "small": 1}
    ) == [1, 0]
    with pytest.raises(RegionKeyError, match="child areas"):
        _ = matcher.pair(
            [[0], [1, 2]], ["large", "small"], [0, 1], minimum={"large": 2, "small": 2}
        )


@pytest.mark.parametrize("bad", [[], [[1], [2]], [[1, 2], [3]]])
def test_impossible_or_ragged_matrix_fails(bad: list[list[int]]) -> None:
    if not bad:
        assert minimum_assignment(bad) == []
    else:
        with pytest.raises(RegionKeyError, match="rectangular"):
            _ = minimum_assignment(bad)


def test_assignment_is_global_not_greedy_and_accepts_negative_costs() -> None:
    # Greedy takes column 0 for row 0, forcing a cost of 100 on row 1.
    assert minimum_assignment([[1, 2], [2, 100]]) == [1, 0]
    assert minimum_assignment([[-1, 2], [-2, 100]]) == [1, 0]


def test_solver_matches_exhaustive_optimum_on_rectangular_matrices() -> None:
    for rows, columns in ((1, 4), (2, 3), (3, 3), (3, 5), (4, 5)):
        for seed in range(16):
            costs = [
                [(seed * (r + 3) + c * 7 + r * c * 11) % 23 for c in range(columns)]
                for r in range(rows)
            ]
            chosen = minimum_assignment(costs)
            actual = sum(costs[row][col] for row, col in enumerate(chosen))
            expected = min(
                sum(costs[row][col] for row, col in enumerate(candidate))
                for candidate in permutations(range(columns), rows)
            )
            assert actual == expected
            assert len(set(chosen)) == rows
            assert chosen == minimum_assignment(costs)


def test_missing_data_and_incomplete_comparisons_fail_loudly() -> None:
    with pytest.raises(RegionKeyError, match="empty"):
        _ = profile([])
    with pytest.raises(RegionKeyError, match="Incomplete"):
        _ = Trait("", "hills", 100, coastal=False)
    matcher = KeyMatcher({"a": profile([COLD])}, {0: WARM, 1: COLD})
    with pytest.raises(RegionKeyError, match="No physical template"):
        _ = matcher.pair([[0], [1]], ["missing"], [0, -1])
    with pytest.raises(RegionKeyError, match="exactly once"):
        _ = matcher.pair([[0], [1]], ["a"], [0, 0])
    with pytest.raises(RegionKeyError, match="unique"):
        _ = matcher.pair([[0], [1]], ["a", "a"], [0, 1])


def test_adapter_uses_physics_only_and_excludes_old_world(tmp_path: Path) -> None:
    _ = make_install(tmp_path)
    game = load_map(tmp_path)
    hierarchy = {p.key: p for p in read_locations(tmp_path / DEFINITIONS)}
    attributes = {
        key: {"climate": "tropical", "topography": "hills", "raw_material": "maize"}
        for key, location in hierarchy.items()
        if location.continent == "america"
    }
    labels = np.tile(np.arange(4, dtype=np.int32), (5, 1))
    kinds = (CellClass.SEA, CellClass.LAND, CellClass.LAKE, CellClass.WASTELAND)
    world = derive_world(labels, kinds, np.zeros(labels.shape, dtype=np.int32))
    biomes = CellBiomes(
        ("tropical",) * 4, ("",) * 4, ("", "hills", "", "hills_wasteland"), ("maize",) * 4
    )
    pairs = unpack_pairs(adjacency_pairs(game.labels))
    pixels = np.bincount(game.labels.ravel(), minlength=len(game.keys)).tolist()
    model = physical_keys(
        game, hierarchy, attributes, pairs, world=world, biomes=biomes, pixels=pixels
    )
    assert set(model.generated) == {1, 2, 3}
    assert model.generated[1].coastal
    assert not model.generated[3].coastal  # a lake is not sea
    assert model.generated[2].topography == "lakes"
    assert all("old" not in key for key in model.vanilla)
    changed = {key: {**values, "raw_material": "silver"} for key, values in attributes.items()}
    other = physical_keys(
        game,
        hierarchy,
        changed,
        pairs,
        world=world,
        biomes=replace(biomes, raw_material=("silver",) * 4),
        pixels=pixels,
    )
    assert model == other
    selected = next(
        key for key in attributes if game.classes[game.keys.index(key)] is CellClass.LAND
    )
    del attributes[selected]["climate"]
    with pytest.raises(RegionKeyError, match="has no climate"):
        _ = physical_keys(
            game, hierarchy, attributes, pairs, world=world, biomes=biomes, pixels=pixels
        )
