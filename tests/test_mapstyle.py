"""The maps as the classic window draws them: the same look as the Tauri window's."""

# NumPy stubs type array arithmetic as Any.
# pyright: reportAny=false

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from rnw import atlas as atlas_module
from rnw.atlas import Country
from rnw.gui import mapstyle
from rnw.wording import english
from tests.fakes import synthetic_atlas

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
    found = synthetic_atlas()
    assert mapstyle.written(found.names[1], words) == english(found.names[1])
    assert "chukchi_sea" in mapstyle.identifiers(
        replace(found, names=(*found.names[:-1], "$chukchi_sea$"))
    )


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
    lake is not a shore whose walls the light would draw as a crater (0.70 against 0.17)."""
    field = mapstyle.relief(_mountains_with_a_lake())
    assert np.all(field.depth[10:14, 10:14] > 0)
    shade = field.shade
    ring = np.zeros(shade.shape, dtype=bool)
    ring[7:17, 7:17] = True
    ring[10:14, 10:14] = False
    far = np.zeros(shade.shape, dtype=bool)
    far[2:6, 2:6] = True
    ring_deviation = float(np.abs(shade[ring] - 1).mean())
    far_deviation = float(np.abs(shade[far] - 1).mean())
    assert ring_deviation < far_deviation + 0.15
