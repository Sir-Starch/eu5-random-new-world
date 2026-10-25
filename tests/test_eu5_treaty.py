"""The treaty keeps one west/east order when a continent crosses the raster seam."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from rnw.eu5_canvas import Canvas
from rnw.eu5_newworld import Plan, PlannedCell, VanillaGeometry
from rnw.eu5_treaty import (
    LOCATION,
    PROVINCE,
    Longitudes,
    TreatyError,
    coordinates,
    metadata,
    replace_comparisons,
    replace_distribution,
)
from rnw.model import CellClass
from rnw.pdx import Block, parse
from rnw.wording import reference

if TYPE_CHECKING:
    from rnw.eu5_map import Eu5Map
    from rnw.newworld import NewWorld


def _decoded(axis: Longitudes, name: str, kind: str) -> dict[str, int]:
    files = metadata(axis)
    geography = parse(files["in_game/common/scripted_geography/rnw_treaty_longitudes.txt"].decode())
    values = parse(files["in_game/common/script_values/rnw_treaty_longitudes.txt"].decode())
    value = values.block(name)
    assert value is not None
    result = dict.fromkeys(axis.locations if kind == "location" else axis.provinces, 0)
    for addition in value.find("if"):
        assert isinstance(addition.value, Block)
        condition = addition.value.block("limit")
        assert condition is not None
        target = condition.first("is_in_scripted_geography")
        assert target is not None
        assert isinstance(target.value, str)
        group = geography.block(target.value.removeprefix("scripted_geography:"), kind)
        assert group is not None
        amount = addition.value.first("add")
        assert amount is not None
        assert isinstance(amount.value, str)
        for entry in group.words():
            assert isinstance(entry.value, str)
            result[entry.value] += int(amount.value)
    return result


def test_continuous_order_including_a_meridian_moved_across_the_seam() -> None:
    # World width 100, Pacific cut 80: the same mainland occupies 90..99,0..15.
    raster = {"western": 90, "seam": 98, "middle": 5, "eastern": 15, "old_world": 40}
    projected = {key: (column - 80) % 100 for key, column in raster.items()}
    axis = Longitudes(100, projected, {"west_province": 10, "east_province": 35})
    decoded = _decoded(axis, LOCATION, "location")
    assert raster["western"] > raster["middle"]  # Original wrong classification.
    assert decoded["western"] < decoded["middle"] < decoded["eastern"]
    assert decoded["western"] < decoded["seam"] < decoded["middle"]
    assert decoded["old_world"] > decoded["eastern"]
    # Compare both directions and equality, including origins on either side.
    for target, target_column in projected.items():
        for current, current_column in projected.items():
            assert (decoded[current] > decoded[target]) == (current_column > target_column)
    assert _decoded(axis, PROVINCE, "province_definition") == axis.provinces


def test_all_coordinate_bits_round_trip_without_province_bits_leaking_into_locations() -> None:
    axis = Longitudes(257, {f"l{i}": i for i in range(257)}, {"p": 256, "other": 0})
    assert _decoded(axis, LOCATION, "location") == axis.locations
    assert _decoded(axis, PROVINCE, "province_definition") == axis.provinces
    files = metadata(axis)
    values = files["in_game/common/script_values/rnw_treaty_longitudes.txt"].decode()
    assert "set_variable" not in values
    assert "on_game_start" not in "".join(files)


@pytest.mark.parametrize(
    ("width", "locations", "provinces"),
    [
        (1, {"a": 0}, {"p": 0}),
        (10, {}, {"p": 0}),
        (10, {"a": -1}, {"p": 0}),
        (10, {"a": 10}, {"p": 0}),
    ],
)
def test_incomplete_or_out_of_range_geometry_fails(
    width: int, locations: dict[str, int], provinces: dict[str, int]
) -> None:
    with pytest.raises(TreatyError):
        _ = Longitudes(width, locations, provinces)


def test_physical_aliases_are_weighted_before_provinces_and_retained_points_share_the_axis() -> (
    None
):
    game_map = cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(keys=("old", "water"), classes=(CellClass.LAND, CellClass.SEA)),
        ),
    )
    world = cast(
        "NewWorld",
        cast(
            "object",
            SimpleNamespace(
                pixels=np.array([2, 6, 4]), centroids=np.array([[0, 0], [0, 4], [0, 10]])
            ),
        ),
    )
    canvas = Canvas(
        7,
        8,
        np.ones((1, 12), dtype=bool),
        (1, 20),
        np.zeros(2, dtype=bool),
        np.zeros(2, dtype=bool),
    )
    plan = Plan(
        [
            PlannedCell(key, reference(key), 1, CellClass.LAND, "p", "a", "r", "s", "c")
            for key in ("alias", "alias", "new")
        ]
    )
    geometry = VanillaGeometry(np.array([0, 0]), np.array([5, 3]), ("a", "a"), np.array([3, 4]))
    defs = "c={s={r={a={p={alias new} retained={old} ocean={water}}}}}"
    axis = coordinates(
        game_map, canvas=canvas, world=world, plan=plan, geometry=geometry, definitions=defs
    )
    assert axis.locations == {"alias": 3, "new": 10, "old": 17}
    assert axis.provinces == {"p": 5, "retained": 17}
    with pytest.raises(TreatyError, match="unknown location class"):
        _ = coordinates(
            game_map,
            canvas=canvas,
            world=world,
            plan=plan,
            geometry=geometry,
            definitions=defs.replace("old}", "old unknown}"),
        )


def test_only_predicates_are_replaced_and_a_changed_contract_fails() -> None:
    text = """# is_east_of = location:comment
x={ text="is_east_of = quoted" NOT={is_east_of=scope:line} }"""
    result = replace_comparisons(text, 1)
    assert "# is_east_of = location:comment" in result
    assert 'text="is_east_of = quoted"' in result
    assert "NOT={rnw_treaty_is_east_of = { target = scope:line }}" in result
    with pytest.raises(TreatyError, match="Expected 2"):
        _ = replace_comparisons(text, 2)
    with pytest.raises(TreatyError, match="changed shape"):
        _ = replace_comparisons("is_east_of={ unexpected=yes }", 1)


def test_final_distribution_changes_the_selection_and_preserves_claim_rules_and_effects() -> None:
    line = "var:var_line_location.province_definition"
    land = "any_location_in_province_definition={ is_land=yes }"
    gates = f"limit={{ {land} NOR={{ has_colonial_claim=yes }} }}"
    text = (
        f"before={{keep=yes}}\ndistribute_world={{ situation:treaty_of_tordesillas={{ {line}={{ "
        + " ".join(
            f"every_{side}_of_province_definition={{ {gates} claim_{side}=yes }}"
            for side in ("east", "west")
        )
        + " } } }\nafter={keep=yes}"
    )
    result = replace_distribution(text)
    assert result.startswith("before={keep=yes}")
    assert result.endswith("after={keep=yes}")
    assert result.count("every_province_definition =") == 2
    assert f"{PROVINCE} >" in result
    assert f"{PROVINCE} <" in result
    assert result.count("NOR={ has_colonial_claim=yes }") == 2
    assert "claim_east=yes" in result
    assert "claim_west=yes" in result
    assert "every_east_of_province_definition" not in result
    with pytest.raises(TreatyError, match="changed shape"):
        _ = replace_distribution(text.replace("every_west_of_province_definition", "new_iterator"))
    with pytest.raises(TreatyError, match="anchor"):
        _ = replace_distribution("unrelated={keep=yes}")
