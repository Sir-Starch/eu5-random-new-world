"""Installed startup and material inputs stay scoped to their source continents."""

# NumPy stubs type array operations as Any.
# pyright: reportAny=false

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from rnw.eu5_biomes import (
    Generated,
    MaterialRegion,
    VanillaLocations,
    _regional_materials,  # pyright: ignore[reportPrivateUsage]
    material_frequencies,
)
from rnw.eu5_natives import (
    COUNTRY_DIR,
    CULTURE_DIR,
    LANGUAGE_DIR,
    LOCATION_NAMES,
    SETUP,
    regional_populations,
)
from rnw.model import CellClass
from rnw.settings import SettingsError
from rnw.topology import adjacency_pairs

if TYPE_CHECKING:
    from pathlib import Path

    from rnw.eu5_map import Eu5Map


def _map() -> tuple[Eu5Map, VanillaLocations]:
    # Africa's west coast touches the sea across the wrapped edge.
    labels = np.array([[1, 2, 3, 4, 0]], dtype=np.int32)
    game = cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                keys=("sea", "west", "inland", "asia", "isle"),
                continents=("pacific_ocean_continent", "africa", "africa", "asia", "oceania"),
                classes=(CellClass.SEA, *(CellClass.LAND for _ in range(4))),
            ),
        ),
    )
    return game, VanillaLocations(
        points=np.zeros((5, 2), dtype=np.int64),
        mean_height=np.zeros(5, dtype=np.int64),
        pairs=adjacency_pairs(labels, wrap_x=True),
        pixels=np.full(5, 100, dtype=np.int64),
    )


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(content, encoding="utf-8")


def test_regional_profiles_use_local_cohorts_and_mixed_ownership(tmp_path: Path) -> None:
    game, geometry = _map()
    _write(
        tmp_path,
        f"{SETUP}/06_pops.txt",
        """locations = {
          west = { define_pop = { type = peasants size = 3 culture = a religion = faith_a } }
          inland = {
            define_pop = { type = peasants size = 1 culture = a religion = faith_b }
            define_pop = { type = burghers size = 1 culture = a religion = faith_b }
          }
          asia = { define_pop = { type = peasants size = 30 culture = a religion = faith_x } }
          isle = { define_pop = { type = tribesmen size = 2 culture = b religion = faith_b } }
        }""",
    )
    _write(
        tmp_path,
        f"{SETUP}/10_countries.txt",
        """countries = { countries = {
          AAC = { own_control_conquered = { west } own_control_core = { asia } include = s_a }
          BBT = { type = pop add_pops_from_locations = { isle } include = t_b }
        } }""",
    )
    _write(
        tmp_path,
        f"{SETUP}/07_cities_and_buildings.txt",
        "locations = { west = { rank = city town_setup = c_a } }",
    )
    _write(
        tmp_path,
        f"{COUNTRY_DIR}/local.txt",
        "AAC = { culture_definition = a }\nBBT = { culture_definition = b }",
    )
    _write(tmp_path, f"{CULTURE_DIR}/local.txt", "a = { language = l_a } b = { language = l_b }")
    _write(tmp_path, f"{LANGUAGE_DIR}/local.txt", "l_a = { family = f_a } l_b = { family = f_b }")
    _write(tmp_path, f"{LOCATION_NAMES}/local.yml", ' west: "West"\n isle: "Isle"')
    profiles = regional_populations(
        tmp_path,
        game,
        geometry,
        {
            "west": {"climate": "tropical"},
            "inland": {"climate": "arid"},
            "isle": {"climate": "tropical"},
        },
        ("oceania", "africa"),
    )
    africa = profiles["africa"]
    assert africa.land_locations == 2
    assert africa.owned_locations == 1
    assert africa.population_per_location == 2500
    assert africa.density == {"tropical": 30_000, "arid": 20_000}
    assert set(africa.cultures) == {"a"}
    assert africa.cultures["a"].religion == "faith_a"
    assert africa.cultures["a"].state_include == "s_a"
    assert africa.cultures["a"].city_setup == "c_a"
    assert africa.places == (("West", "a"),)
    assert africa.languages == {"a": ("l_a", "f_a")}
    oceania = profiles["oceania"]
    assert oceania.population == 2000
    assert oceania.owned_locations == 0
    assert oceania.cultures["b"].tribe_include == "t_b"
    assert set(oceania.religions) == {"faith_b"}
    assert oceania.places == (("Isle", "b"),)


def test_resources_use_the_selected_continent_and_shared_wrapped_coast() -> None:
    game, geometry = _map()
    templates = {
        key: {"raw_material": name}
        for key, name in zip(game.keys[1:], ("ivory", "millet", "tea", "fish"), strict=True)
    }
    assert material_frequencies(game, templates, geometry, "africa") == {
        "coast": Counter(ivory=1),
        "inland": Counter(millet=1),
    }
    assert material_frequencies(game, templates, geometry, "oceania") == {"coast": Counter(fish=1)}


@pytest.mark.parametrize("pooled", [False, True])
def test_two_continents_can_weight_the_same_material_independently(*, pooled: bool) -> None:
    game, geometry = _map()
    geometry = replace(geometry, pairs=np.array([1, 2, 4], dtype=np.int64))
    count = 4
    cells = Generated(
        kinds=(CellClass.LAND, CellClass.LAND, CellClass.LAND, CellClass.SEA),
        points=np.zeros((count, 2), dtype=np.int64),
        mean_height=np.zeros(count, dtype=np.int64),
        spread=np.zeros(count, dtype=np.int64),
        edges=(),
        coastal=np.array([True, True, True, False]),
    )
    attributes: list[dict[str, str]] = [
        {},
        {"raw_material": "ivory"},
        {"raw_material": "rice"},
        {"raw_material": "tea"},
        {"raw_material": "rice"},
    ]
    fields = (["tropical"] * count, ["forest"] * count, ["flatland"] * count)
    regions = {
        "africa": MaterialRegion(range(2), 17, {"rice": 0}),
        "oceania": MaterialRegion(range(2, 4), 42, {"rice": 1000}),
    }
    assert _regional_materials(
        game,
        attributes=attributes,
        vanilla=geometry,
        cells=cells,
        fields=fields,
        regions=regions,
        pooled=pooled,
    ) == ("ivory", "ivory", "rice", "")
    regions["oceania"] = MaterialRegion(range(2, 4), 42, {"tea": 0})
    with pytest.raises(SettingsError, match="Unknown ordinary resources in oceania: tea"):
        _ = _regional_materials(
            game,
            attributes=attributes,
            vanilla=geometry,
            cells=cells,
            fields=fields,
            regions=regions,
            pooled=pooled,
        )
