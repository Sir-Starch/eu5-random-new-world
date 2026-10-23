"""Exceptional resource places: where they stand, what they copy, how they read (synthetic)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.eu5_places import (
    BASE_VALUES,
    SPECS,
    Cells,
    PlacesError,
    Spec,
    choose,
    modifiers_file,
    payloads,
    texts,
)
from rnw.pdx import parse

if TYPE_CHECKING:
    from pathlib import Path

COUNT = 400


def _cells() -> Cells:
    materials = [
        "silver" if index % 4 == 0 else "fish" if index % 5 == 0 else "maize"
        for index in range(COUNT)
    ]
    topography = [
        "mountains" if index % 8 == 0 else "hills" if index % 3 == 0 else "flatland"
        for index in range(COUNT)
    ]
    return Cells(
        land=[index % 50 != 49 for index in range(COUNT)],
        material=materials,
        topography=topography,
        coastal=[index % 2 == 0 for index in range(COUNT)],
    )


def test_each_kind_takes_a_suitable_cell_and_no_cell_holds_two() -> None:
    """Silver is mined where silver lies, a fishery stands on a coast, and kinds do not overlap."""
    cells = _cells()
    found = choose(cells, 7)
    assert len(set(found)) == len(found)
    for index, spec in found.items():
        assert cells.land[index]
        assert cells.material[index] == spec.material
        assert cells.coastal[index] or not spec.coastal
    great = next(index for index, spec in found.items() if spec.modifier == "rnw_great_silver_lode")
    assert cells.topography[great] == "mountains"
    assert {spec.modifier for spec in found.values()} <= {spec.modifier for spec in SPECS}


def test_the_choice_is_stable_and_follows_the_seed() -> None:
    """The same seed makes the same places; another seed moves them."""
    cells = _cells()
    assert choose(cells, 7) == choose(cells, 7)
    assert choose(cells, 7) != choose(cells, 8)


def test_adding_a_kind_does_not_move_the_others() -> None:
    """Each kind draws from a stream of its own, so the first kinds stay where they were."""
    cells = _cells()
    extra = Spec("rnw_extra", "x", "silver", (), coastal=False, name="E", description="E")
    before = choose(cells, 7)
    after = choose(cells, 7, (*SPECS, extra))
    assert {index: spec for index, spec in after.items() if spec is not extra} == before


def test_a_kind_without_a_candidate_is_left_out() -> None:
    """A world with no silver has no silver place, and says nothing else about it."""
    cells = _cells()
    cells = Cells(cells.land, ["maize"] * COUNT, cells.topography, cells.coastal)
    assert choose(cells, 7) == {}


BASE = """potosi_base = {
\tgame_data = {
\t\tcategory = location
\t}
\tlocal_silver_output_modifier = 2.5
}
zacatecas_base = {
\tgame_data = { category = location }
\tlocal_silver_output_modifier = 1.5
}
guanajuato_base = { local_silver_output_modifier = 1 }
huancavelica_base = { local_mercury_output_modifier = 2.5 }
newfoundland_fishing_grounds_base = { local_fish_output_modifier = 2 }
"""


def _install(root: Path, text: str = BASE) -> None:
    path = root / BASE_VALUES
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def test_the_effects_are_copied_from_the_installation(tmp_path: Path) -> None:
    """Each bonus is the size of the vanilla one, read at generation time, under the mod's name."""
    _install(tmp_path)
    effects = payloads(tmp_path)
    assert effects["rnw_great_silver_lode"] == "\tlocal_silver_output_modifier = 2.5"
    assert effects["rnw_rich_fishery"] == "\tlocal_fish_output_modifier = 2"
    used = SPECS[:2]
    file = modifiers_file(used, effects).decode("utf-8-sig")
    blocks = {entry.key: entry.value for entry in parse(file).entries}
    assert set(blocks) == {"rnw_great_silver_lode", "rnw_rich_silver_vein"}
    assert "local_silver_output_modifier = 1.5" in file
    assert "category = location" in file
    assert "potosi" not in file.lower()


def test_a_base_value_that_is_gone_stops_the_export(tmp_path: Path) -> None:
    """A patch that removes or empties a historical base value is refused, not worked around."""
    _install(tmp_path, BASE.replace("potosi_base", "elsewhere_base"))
    with pytest.raises(PlacesError, match="potosi_base is gone"):
        _ = payloads(tmp_path)
    _install(tmp_path, BASE.replace("\tlocal_silver_output_modifier = 2.5\n", ""))
    with pytest.raises(PlacesError, match="no longer has an effect"):
        _ = payloads(tmp_path)


def test_a_place_has_a_name_and_a_description_of_its_own() -> None:
    """The texts are the mod's, never the vanilla names of the mines."""
    found = texts(SPECS)
    assert len(found) == 2 * len(SPECS)
    assert found["STATIC_MODIFIER_NAME_rnw_great_silver_lode"] == "Great Silver Lode"
    assert not any("Potos" in text or "Zacatecas" in text for text in found.values())
