"""RGO weights change relative placement, preserving vanilla habitat pools and defaults."""

# NumPy's array constructors and comparisons are typed as Any.
# pyright: reportAny=false
# pyright: reportPrivateUsage=false

from __future__ import annotations

from collections import Counter
from dataclasses import replace

import numpy as np
import pytest

from rnw.app import controls, worldcode
from rnw.eu5_biomes import Generated, VanillaLocations, _raw_materials, _weighted
from rnw.eu5_map import Eu5Map
from rnw.layers import land_key
from rnw.model import CellClass
from rnw.settings import RESOURCE_FIELDS, RESOURCES, ResourceSettings, SettingsError, build_settings


@pytest.mark.parametrize("bad", [-1, 5001, True, 1.5, "1000"])
def test_resource_settings_validate_values_and_unknown_names(bad: object) -> None:
    with pytest.raises(SettingsError):
        _ = build_settings("continents", {"resources": {"maize": bad}})
    with pytest.raises(SettingsError, match="Unknown resources"):
        _ = build_settings("continents", {"resources": {"imaginary": 1000}})


def test_defaults_preserve_documents_and_nondefaults_survive_codes_and_land_grouping() -> None:
    base = build_settings("continents")
    assert "resources" not in base.to_json_data()
    assert build_settings("continents", {"resources": dict.fromkeys(RESOURCE_FIELDS, 1000)}) == base
    changes: dict[str, object] = {"resources": {"maize": 3000, "fish": 0, "iron": 250}}
    code = worldcode.new_code("continents", 42, changes)
    encoded = worldcode.encode(code)
    assert worldcode.format_of(encoded) == 2
    again = worldcode.decode(encoded)
    settings = again.settings()
    assert (settings.resources.maize, settings.resources.fish, settings.resources.iron) == (
        3000,
        0,
        250,
    )
    assert build_settings("continents", settings.to_json_data()) == settings
    assert controls.flat(changes) == (
        {"resources.maize": 3000, "resources.fish": 0, "resources.iron": 250},
        {},
    )
    assert land_key(settings, 42) == land_key(base, 42)
    assert worldcode.rolled(again, "resources").settings().resources == settings.resources
    assert worldcode.with_new_seed(again, 43).settings().resources == settings.resources
    for name in RESOURCE_FIELDS:
        control = controls.BY_KEY[f"resources.{name}"]
        assert control.group == "resources"
        assert (control.low, control.high, control.default("continents")) == (0, 3000, 1000)


def test_integer_weights_keep_defaults_exact_and_scale_each_resource_independently() -> None:
    counts = Counter(maize=4, copper=2, silver=1)
    assert _weighted(counts, 1000) is counts
    assert _weighted(counts, 2000) == Counter(maize=4000, copper=2000, silver=2000)
    assert _weighted(counts, 2000, replace(RESOURCES, maize=3000, copper=0)) == Counter(
        maize=12000, silver=2000
    )
    assert counts == Counter(maize=4, copper=2, silver=1)


def _draw(
    rows: list[tuple[str, str, str, bool]],
    *,
    resources: ResourceSettings = RESOURCES,
    precious: int = 1000,
    coast: bool = False,
    count: int = 6000,
) -> tuple[str, ...]:
    # A tiny installed world: each row is one New World land location and its RGO,
    # vegetation, topography and coast; a last Old World rice donor must never be used.
    size = len(rows) + 2
    kinds = (CellClass.SEA, *(CellClass.LAND for _ in range(size - 1)))
    game = Eu5Map(
        keys=tuple(f"loc_{i}" for i in range(size)),
        colors=np.zeros((size, 3), dtype=np.int64),
        classes=kinds,
        ambiguous=np.zeros(size, dtype=bool),
        continents=("", *("america" for _ in rows), "asia"),
        rgb=np.zeros((1, size, 3), dtype=np.uint8),
        labels=np.arange(size, dtype=np.int32)[None, :],
        rivers=np.zeros((1, size), dtype=np.uint8),
        locations_chunks=(),
        rivers_chunks=(),
        points=(),
        inputs=(),
    )
    attributes: list[dict[str, str]] = (
        [dict[str, str]()]
        + [
            {
                "raw_material": material,
                "climate": "temperate",
                "vegetation": vegetation,
                "topography": topography,
            }
            for material, vegetation, topography, _ in rows
        ]
        + [
            {
                "raw_material": "rice",
                "climate": "temperate",
                "vegetation": "grasslands",
                "topography": "flatland",
            }
        ]
    )
    vanilla = VanillaLocations(
        points=np.zeros((size, 2), dtype=np.int64),
        mean_height=np.zeros(size, dtype=np.int64),
        pairs=np.array([i for i, row in enumerate(rows, 1) if row[3]], dtype=np.int64),
    )
    cells = Generated(
        kinds=(
            *(CellClass.LAND for _ in range(count)),
            CellClass.SEA,
            CellClass.LAKE,
            CellClass.WASTELAND,
        ),
        points=np.zeros((count + 3, 2), dtype=np.int64),
        mean_height=np.zeros(count + 3, dtype=np.int64),
        spread=np.zeros(count + 3, dtype=np.int64),
        edges=(),
        coastal=np.full(count + 3, coast, dtype=bool),
    )
    return _raw_materials(
        game,
        attributes=attributes,
        vanilla=vanilla,
        source=np.array([False, *(True for _ in rows), False]),
        cells=cells,
        fields=(
            ["temperate"] * (count + 3),
            ["grasslands"] * (count + 3),
            ["flatland"] * (count + 3),
        ),
        seed=42,
        precious_permille=precious,
        resources=resources,
    )


def test_sliders_change_relative_frequency_deterministically_without_creating_foreign_rgos() -> (
    None
):
    rows = [("maize", "grasslands", "flatland", False), ("copper", "grasslands", "flatland", False)]
    default = _draw(rows)
    rich = _draw(rows, resources=replace(RESOURCES, maize=3000))
    assert rich == _draw(rows, resources=replace(RESOURCES, maize=3000))
    assert default == _draw(rows, resources=ResourceSettings())
    assert 2800 < default.count("maize") < 3200
    assert 4300 < rich.count("maize") < 4700
    assert set(default) == set(rich) == {"maize", "copper", ""}
    assert default[-3:] == rich[-3:] == ("", "", "")
    assert set(_draw(rows, resources=replace(RESOURCES, maize=0))) == {"copper", ""}


def test_zero_weights_use_coarser_habitats_but_never_cross_the_coast_or_restore_stone() -> None:
    rows = [
        ("maize", "grasslands", "flatland", False),
        ("copper", "grasslands", "hills", False),
        ("fish", "grasslands", "flatland", True),
    ]
    assert set(_draw(rows, resources=replace(RESOURCES, maize=0))) == {"copper", ""}
    assert set(_draw(rows, coast=True)) == {"fish", ""}
    with pytest.raises(SettingsError, match="No enabled raw materials for inland"):
        _ = _draw(rows, resources=replace(RESOURCES, maize=0, copper=0, stone=0))
    with pytest.raises(SettingsError, match="No enabled raw materials for coast"):
        _ = _draw(rows, coast=True, resources=replace(RESOURCES, fish=0))


def test_all_resources_can_be_disabled_in_settings_but_generation_fails_explicitly() -> None:
    settings = build_settings(
        "continents",
        {"new_world": {"precious_permille": 0}, "resources": dict.fromkeys(RESOURCE_FIELDS, 0)},
    )
    with pytest.raises(SettingsError, match="No enabled raw materials"):
        _ = _draw(
            [("stone", "grasslands", "flatland", False)], resources=settings.resources, precious=0
        )
