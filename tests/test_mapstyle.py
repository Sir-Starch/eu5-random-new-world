"""The maps as the classic window draws them: the same look as the Tauri window's."""

# NumPy stubs type array arithmetic as Any.
# pyright: reportAny=false

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from rnw import atlas as atlas_module
from rnw import barrens
from rnw.atlas import Country
from rnw.eu5_history_plan import project_start
from rnw.gui import mapstyle
from rnw.opinions import TREATIES
from rnw.wording import Name, english, render
from tests.fakes import synthetic_atlas
from tests.history_fixtures import divided_valley
from tests.test_history_archive import history_atlas
from tests.test_history_plan import inputs_for

STYLE = Path(__file__).resolve().parent.parent / "src" / "rnw" / "gui" / "lenses.json"
DESKTOP = Path(__file__).resolve().parent.parent / "desktop" / "src" / "lib" / "style.ts"


def _with_a_tribe() -> atlas_module.Atlas:
    """The synthetic atlas with its second land location held by a tribe."""
    found = synthetic_atlas()
    land = np.flatnonzero(found.kinds == mapstyle.LAND)
    tribe = Country("TRB", found.countries[0].name, "tribe", (0, 200, 0), int(land[-1]), 0, 0, 1)
    owner = found.owner.copy()
    owner[land[-1]] = 1
    return replace(found, countries=(*found.countries, tribe), owner=owner)


def test_both_windows_read_one_look() -> None:
    """The palettes and profiles are one file, which the Tauri window imports as well."""
    assert json.loads(STYLE.read_text(encoding="utf-8"))["profiles"].keys() == set(
        atlas_module.LAYERS
    )
    assert "src/rnw/gui/lenses.json" in DESKTOP.read_text(encoding="utf-8")
    # The light and the shelf of the physical map are numbers in that file as well, read by both.
    relief = json.loads(STYLE.read_text(encoding="utf-8"))["relief"]
    assert "STYLE.relief" in DESKTOP.read_text(encoding="utf-8")
    assert sum(share for _, share in relief["lights"]) == pytest.approx(1)
    assert tuple((float(a), float(b)) for a, b in relief["lights"]) == mapstyle.LIGHTS
    assert relief["snow"]["lines"] == mapstyle.SNOW_LINES
    assert mapstyle.profile("land").physical
    assert mapstyle.profile("resources").names == "none"


def test_the_noise_and_the_hashed_colours_are_those_of_the_tauri_window() -> None:
    """Values computed by relief.ts and lenses.ts (node, 2026-10-30)."""
    x = np.array([3, 100, 0, 999], dtype=np.int64)
    y = np.array([5, 7, 0, 1234], dtype=np.int64)
    expected = [0.530632486457618, -0.5928587777523461, -1, 0.8795757991912718]
    assert np.allclose(mapstyle._lattice(x, y), expected, atol=1e-6)  # pyright: ignore[reportPrivateUsage]
    assert mapstyle._hashed("wild_game") == mapstyle.QUALITATIVE[4]  # pyright: ignore[reportPrivateUsage]


def test_neighbours_never_share_a_colour() -> None:
    path = [{1}, {0, 2}, {1, 3}, {2}]
    colours = mapstyle.colour_classes(path, [4, 3, 2, 1])
    for k, near in enumerate(path):
        assert all(colours[n] != colours[k] for n in near)


def test_countries_show_states_and_tribes_only_when_asked() -> None:
    found = _with_a_tribe()
    tribe_cell = int(np.flatnonzero(found.owner == 1)[0])
    state_cell = int(np.flatnonzero(found.owner == 0)[0])
    states = mapstyle.style(
        found, "countries", atlas_module.ENGLISH, tribes=False, tribes_label="Tribes"
    )
    assert states.opacity[tribe_cell] == 0
    assert states.opacity[state_cell] > 0
    assert states.legend[states.classes[tribe_cell]][0] == "Tribes"
    every = mapstyle.style(
        found, "countries", atlas_module.ENGLISH, tribes=True, tribes_label="Tribes"
    )
    assert every.opacity[tribe_cell] == mapstyle.TRIBE_OPACITY
    assert "Tribes" not in {label for label, _, _ in every.legend}
    names = mapstyle.names(found, states, atlas_module.ENGLISH, tribes=False)
    assert {label.kind for label in names} == {"country"}
    capitals = mapstyle.places(found, "countries", atlas_module.ENGLISH, tribes=False)
    assert {place.cell for place in capitals if place.kind == "capital"} == {
        found.countries[0].capital
    }


def test_every_lens_draws_over_the_physical_map() -> None:
    found = synthetic_atlas()
    height, width = found.size
    for layer in atlas_module.LAYERS:
        lens = mapstyle.style(found, layer, atlas_module.ENGLISH, tribes=False, tribes_label="T")
        drawn = mapstyle.picture(found, lens, tribes=False)
        assert drawn.shape == (height, width, 3)
        assert drawn.dtype == np.uint8
    land = mapstyle.style(found, "land", atlas_module.ENGLISH, tribes=False, tribes_label="T")
    drawn = mapstyle.picture(found, land, tribes=False)
    lone = mapstyle.isolate(found, drawn, [0])
    outside = found.labels != 1
    assert (lone[outside].astype(int).sum()) < (drawn[outside].astype(int).sum())


def test_scattered_lenses_write_no_large_names_and_mark_riches() -> None:
    found = synthetic_atlas()
    resources = mapstyle.style(
        found, "resources", atlas_module.ENGLISH, tribes=False, tribes_label="T"
    )
    assert mapstyle.names(found, resources, atlas_module.ENGLISH, tribes=False) == []
    marks = mapstyle.places(found, "resources", atlas_module.ENGLISH, tribes=False)
    gold = {
        int(c)
        for c in np.flatnonzero(found.material == found.vocabulary["material"].index("goods_gold"))
    }
    land = {int(c) for c in np.flatnonzero(found.kinds == mapstyle.LAND)}
    assert {place.cell for place in marks} == gold & land
    assert all(place.kind == "riches" for place in marks)
    cell = next(iter(land))
    assert mapstyle.spot(found, "resources", cell, atlas_module.ENGLISH)


def test_game_identifiers_are_named_by_the_game() -> None:
    def bracketed(key: str) -> str:
        return f"<{key}>"

    words = replace(atlas_module.ENGLISH, key=bracketed)
    assert mapstyle.written("$chukchi_sea$", words) == "<chukchi_sea>"
    assert mapstyle.written("great_plains_region", words) == "<great_plains_region>"
    assert mapstyle.written("Great Area", words) == "Great Area"

    # A plain generated name is written as the world's localization writes it in that language.
    def in_russian(name: Name) -> str:
        return render(name, "russian")

    russian = replace(atlas_module.ENGLISH, name=in_russian)
    assert mapstyle.written("Xicochimanga", russian) == render("Xicochimanga", "russian")
    assert mapstyle.written("Xicochimanga", russian) != "Xicochimanga"
    found = synthetic_atlas()
    assert mapstyle.written(found.names[1], words) == english(found.names[1])
    assert "chukchi_sea" in mapstyle.identifiers(
        replace(found, names=(*found.names[:-1], "$chukchi_sea$"))
    )


def test_a_world_with_history_asks_the_game_for_its_treaty_opinions() -> None:
    """The Relations tab names the engine's treaty opinions as the game does (*Allied*, *Rival*),
    so their keys are among the identifiers the game is asked to name."""
    found = history_atlas(project_start(inputs_for(divided_valley())))
    assert {treaty.key for treaty in TREATIES} <= mapstyle.identifiers(found)
    assert not {treaty.key for treaty in TREATIES} & mapstyle.identifiers(synthetic_atlas())


def _mountains_with_a_lake() -> atlas_module.Atlas:
    """One mountainous land location with a lake location in the middle, no sea at all."""
    found = synthetic_atlas()
    mountains = int(np.flatnonzero((found.kinds == mapstyle.LAND) & (found.topography == 1))[0])
    lake = int(np.flatnonzero(found.kinds == mapstyle.LAKE)[0])
    labels = np.full((48, 48), mountains + 1, dtype=np.int32)
    labels[20:28, 20:28] = lake + 1
    return replace(found, labels=labels)


def test_a_lake_in_mountains_is_no_crater_on_the_physical_map() -> None:
    """Around a lake the shade is no darker or brighter than in the mountains far from it: the
    lake is not a shore whose walls the light would draw as a crater."""
    field = mapstyle.relief(_mountains_with_a_lake())
    assert np.all(field.depth[10:14, 10:14] > 0)
    shade = field.shade
    ring = np.zeros(shade.shape, dtype=bool)
    ring[7:17, 7:17] = True
    ring[10:14, 10:14] = False
    far = np.zeros(shade.shape, dtype=bool)
    far[2:6, 2:6] = True
    ring_deviation = float(np.abs(shade[ring]).mean())
    far_deviation = float(np.abs(shade[far]).mean())
    assert ring_deviation < far_deviation + 0.15


def _mountains_by_the_sea() -> atlas_module.Atlas:
    """One mountainous land location on the left half of the box and the sea on the right."""
    found = synthetic_atlas()
    mountains = int(np.flatnonzero((found.kinds == mapstyle.LAND) & (found.topography == 1))[0])
    sea = int(np.flatnonzero(found.kinds == mapstyle.SEA)[0])
    labels = np.full((48, 48), sea + 1, dtype=np.int32)
    labels[:, :24] = mountains + 1
    return replace(found, labels=labels)


def test_a_mountain_shore_is_lit_as_the_mountain_inland_is() -> None:
    """The height is smoothed over the land alone and not dragged to nothing at the shore, so
    the shore is no cliff: its shade is as mild as the mountain's far from it (the black and
    burned coasts of a forced slope) and every shade lies between full shadow and full light."""
    field = mapstyle.relief(_mountains_by_the_sea())
    land = field.depth == 0
    assert land.any()
    assert np.all(np.abs(field.shade) <= 1)
    columns = np.arange(field.shade.shape[1], dtype=np.int64)
    near = land & (np.abs(columns - 11) <= 1)[None, :]
    inland = land & (np.abs(columns - 3) <= 1)[None, :]
    rows = slice(4, -4)
    shore = float(np.abs(field.shade[rows][near[rows]]).max())
    deep = float(np.abs(field.shade[rows][inland[rows]]).max())
    assert shore <= deep + 0.1


def test_light_on_the_land_darkens_and_warms_without_burning_or_blackening() -> None:
    soil = np.array([[200.0, 160.0, 90.0]], dtype=np.float32)
    level = mapstyle.lit(soil, np.zeros(1, dtype=np.float32))
    assert np.array_equal(level, soil)
    dark = mapstyle.lit(soil, np.full(1, -1.0, dtype=np.float32))
    bright = mapstyle.lit(soil, np.full(1, 1.0, dtype=np.float32))
    # In full shadow no channel loses more than its share; in full light none passes the lamp.
    assert np.all(dark >= soil * (1 - np.array(mapstyle.SHADOW, np.float32)) - 1e-3)
    assert np.all(dark > 0)
    assert np.all(bright <= np.array(mapstyle.LAMP, np.float32) + 1e-3)
    assert np.all(bright >= soil)
    # The shadow is cooler than the light: the blue is kept better than the red.
    assert dark[0, 2] / soil[0, 2] > dark[0, 0] / soil[0, 0]


def test_the_water_darkens_smoothly_from_the_shore_to_the_open_ocean() -> None:
    """The shelf is a fall with no step: the colour moves a little at each pixel from the shore."""
    found = _mountains_by_the_sea()
    drawn = mapstyle.picture(
        found,
        mapstyle.style(found, "land", atlas_module.ENGLISH, tribes=False, tribes_label="T"),
        tribes=False,
    )
    row = drawn[24, 24:].astype(int)
    steps = np.abs(np.diff(row, axis=0)).max(axis=1)
    assert steps[2:].max() <= 6


def test_the_rules_line_names_the_game_region_only_where_the_world_names_it_otherwise() -> None:
    """A region the world renames shows the base game's name of its rules; a region the game
    names itself (an ocean) and a world made before region keys were recorded show none (W8)."""
    found = synthetic_atlas()
    game = {"alaska_region": "Alaska", "north_pacific_ocean_region": "North Pacific"}

    def named(key: str) -> str:
        return game.get(key, key)

    words = replace(atlas_module.ENGLISH, key=named)
    keys = tuple(
        "north_pacific_ocean_region" if kind == mapstyle.SEA else "alaska_region"
        for kind in found.kinds.tolist()
    )
    shown: tuple[Name, ...] = tuple(
        key if key.endswith("ocean_region") else "Ziageilra" for key in keys
    )
    renamed = replace(found, regions=shown, region_keys=keys)
    rules = mapstyle.rules(renamed, words)
    assert {
        rule for rule, kind in zip(rules, found.kinds.tolist(), strict=True) if kind == mapstyle.SEA
    } == {""}
    assert {
        rule
        for rule, kind in zip(rules, found.kinds.tolist(), strict=True)
        if kind == mapstyle.LAND
    } == {"Alaska"}
    assert {"alaska_region", "north_pacific_ocean_region"} <= mapstyle.identifiers(renamed)
    assert mapstyle.rules(replace(found, region_keys=None), words) == [""] * found.cells


def test_every_wasteland_topography_the_generator_writes_is_drawn_by_both_windows() -> None:
    """A flat wild or a dune is no mountain on the physical map: each topography of a planned
    wasteland (``rnw.barrens``) has its own relief, its colour on the terrain lens and its entry in
    the palette both windows read (``lenses.json``), and the flat ones lie lower than a mountain."""
    palette = json.loads(Path(mapstyle.__file__).with_name("lenses.json").read_text("utf-8"))[
        "palettes"
    ]["terrain"]
    for name in barrens.TOPOGRAPHY.values():
        assert name in mapstyle.TOPOGRAPHY
        assert name in atlas_module.TERRAIN_COLOURS
        assert name in palette
    heights = {name: mapstyle.TOPOGRAPHY[name]["height"] for name in barrens.TOPOGRAPHY.values()}
    for flat in ("flatland_wasteland", "dune_wasteland"):
        assert heights[flat] < heights["hills_wasteland"] < heights["mountain_wasteland"]
