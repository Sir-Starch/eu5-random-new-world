"""The atlas of a world: built from the export's data, written, read, drawn, asked and searched."""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import json
from dataclasses import replace
from typing import cast

import numpy as np
import pytest

from rnw import atlas
from rnw.atlas import AtlasError
from rnw.eu5_atlas import build_atlas, grown_mask
from rnw.newworld import NewWorld
from rnw.wording import Phrase, render
from tests.fakes import synthetic_atlas, synthetic_world


def test_the_box_keeps_the_land_and_its_coasts_and_drops_the_far_sea() -> None:
    """Sea farther than the margin from any land is cut, and the box is trimmed to what is left."""
    world, plan, biomes, natives, mask = synthetic_world()
    labels = np.zeros((24, 72), dtype=np.int32)
    labels[:, 30:42] = 1
    lone = replace(world, labels=labels)
    for margin in (3, 10):
        built = build_atlas(
            world=lone, plan=plan, biomes=biomes, natives=natives, mask=mask, step=1, margin=margin
        )
        assert built.size == (24, 12 + 2 * margin)
        present = {int(cell) - 1 for cell in np.unique(built.labels) if cell}
        assert present == {0, 1}
    everything = synthetic_atlas(margin=100)
    assert everything.size == (24, 70)


def test_every_location_has_what_the_export_knew_of_it() -> None:
    """Owner, culture, religion, material, biome, settlement, population and names."""
    built = synthetic_atlas()
    land = built.keys.index("rnw_loc_1")
    facts = atlas.describe(built, land)
    assert facts is not None
    assert (facts.name, facts.kind, facts.area) == ("Alandia", "land", "Great Area")
    assert facts.country is not None
    assert facts.country.tag == "AAA"
    assert (facts.culture, facts.religion, facts.material) == ("a_culture", "a_faith", "goods_gold")
    assert (facts.climate, facts.vegetation, facts.topography) == (
        "tropical",
        "jungle",
        "mountains",
    )
    assert (facts.settlement, facts.population, facts.complexity) == ("city", 5000, 900)
    other = atlas.describe(built, built.keys.index("rnw_loc_2"))
    assert other is not None
    assert other.country is None
    assert other.culture == "b_culture"
    sea = atlas.describe(built, 0)
    assert sea is not None
    assert (sea.kind, sea.culture, sea.material) == ("sea", "", "")
    assert atlas.describe(built, -1) is None
    assert atlas.describe(built, 99) is None


def test_the_atlas_survives_its_two_files_and_refuses_damaged_ones() -> None:
    """Written and read back it is the same; a damaged or oversized one raises AtlasError."""
    built = synthetic_atlas()
    document, picture = atlas.to_files(built)
    again = atlas.from_files(document, picture)
    assert np.array_equal(again.labels, built.labels)
    assert again.keys == built.keys
    assert again.countries == built.countries
    assert again.vocabulary == built.vocabulary
    assert np.array_equal(again.population, built.population)
    assert np.array_equal(atlas.render(again, "countries"), atlas.render(built, "countries"))
    assert atlas.to_files(again) == (document, picture)
    with pytest.raises(AtlasError, match="damaged"):
        _ = atlas.from_files(b"{", picture)
    with pytest.raises(AtlasError, match="damaged"):
        _ = atlas.from_files(document, b"not a png")
    wrong = json.loads(document)
    wrong["format"] = 99
    with pytest.raises(AtlasError, match="format"):
        _ = atlas.from_files(json.dumps(wrong).encode(), picture)
    short = json.loads(document)
    short["locations"]["name"] = short["locations"]["name"][:-1]
    with pytest.raises(AtlasError, match="differ in length"):
        _ = atlas.from_files(json.dumps(short).encode(), picture)
    few = json.loads(document)
    for column in few["locations"].values():
        del column[1:]
    with pytest.raises(AtlasError, match="does not have"):
        _ = atlas.from_files(json.dumps(few).encode(), picture)


def test_every_layer_is_a_picture_of_the_box_with_a_legend() -> None:
    """Each layer paints the box deterministically; the legend counts the locations by colour."""
    built = synthetic_atlas()
    for layer in atlas.LAYERS:
        picture = atlas.render(built, layer)
        assert picture.shape == (*built.size, 3)
        assert picture.dtype == np.uint8
        assert np.array_equal(picture, atlas.render(built, layer))
        entries = atlas.legend(built, layer)
        assert entries
        assert all(count >= 0 for _label, _colour, count in entries)
    countries = atlas.render(built, "countries")
    cell = built.keys.index("rnw_loc_1")
    row, column = (int(value) for value in built.centre[cell])
    assert tuple(countries[row, column - 4]) == (200, 30, 30)
    assert any(label == "Aland" for label, _colour, _count in atlas.legend(built, "countries"))
    assert any(label == "Gold" for label, _colour, _count in atlas.legend(built, "resources"))
    with pytest.raises(AtlasError, match="Unknown layer"):
        _ = atlas.render(built, "weather")


def test_a_search_finds_countries_cultures_materials_and_places_and_outlines_them() -> None:
    """A name finds what it covers; the outline paints only those locations' edges."""
    built = synthetic_atlas()
    kinds = {match.kind for match in atlas.find(built, "a")}
    assert {"country", "culture", "religion", "material", "place"} <= kinds
    [country] = [m for m in atlas.find(built, "aland") if m.kind == "country"]
    assert country.cells == (built.keys.index("rnw_loc_1"),)
    assert atlas.find(built, "  ") == []
    assert atlas.find(built, "no such thing") == []
    plain = atlas.render(built, "land")
    marked = atlas.render(built, "land", highlight=country.cells)
    changed = np.any(plain != marked, axis=2)
    assert changed.any()
    assert tuple(marked[changed][0]) == atlas.HIGHLIGHT
    assert changed.sum() < plain.shape[0] * plain.shape[1] // 3


def test_a_pixel_gives_its_location_and_the_outside_gives_none() -> None:
    """Rows and columns map to locations; outside the box or the New World is -1."""
    built = synthetic_atlas()
    assert atlas.cell_at(built, 0, 0) >= -1
    assert atlas.cell_at(built, -1, 0) == -1
    assert atlas.cell_at(built, 0, built.size[1]) == -1
    cell = built.keys.index("rnw_loc_2")
    row, column = (int(value) for value in built.centre[cell])
    assert atlas.cell_at(built, row, column) == cell


def test_the_palettes_are_stable_and_the_ramp_is_a_ramp() -> None:
    """A key always has the same colour; the ramp runs from its first colour to its last."""
    assert atlas.colour_of("maize") == atlas.colour_of("maize")
    assert atlas.colour_of("maize") != atlas.colour_of("potato")
    assert atlas.ramp(0) == atlas.RAMP[0]
    assert atlas.ramp(1000) == atlas.RAMP[-1]
    assert atlas.pretty("goods_gold") == "Gold"
    assert atlas.pretty("wild_game") == "Wild Game"


def test_the_growth_of_a_mask_reaches_exactly_the_radius() -> None:
    """Doubling steps cover a square of the radius and no more."""
    mask = np.zeros((41, 41), dtype=bool)
    mask[20, 20] = True
    for radius in (1, 2, 5, 9):
        grown = grown_mask(mask, radius)
        assert grown.sum() == (2 * radius + 1) ** 2
        assert grown[20 - radius, 20 - radius]
        assert not grown[20 - radius - 1, 20]


def test_a_builder_given_labels_of_the_wrong_shape_refuses() -> None:
    """The labels and the canvas must share a shape."""
    world, plan, biomes, natives, mask = synthetic_world()
    with pytest.raises(ValueError, match="differ in shape"):
        _ = build_atlas(world=world, plan=plan, biomes=biomes, natives=natives, mask=mask[:, :-1])
    assert isinstance(cast("object", world), NewWorld)


def test_names_are_phrases_that_a_viewer_writes_in_its_own_language() -> None:
    """Format 2 keeps names as phrases; format 1, English text, is still read."""
    built = synthetic_atlas()
    gulf = Phrase("gulf", "Akaira", ("north",))
    named = replace(built, names=(gulf, *built.names[1:]))
    document, picture = atlas.to_files(named)
    again = atlas.from_files(document, picture)
    assert again.names[0] == gulf
    assert again.names[1:] == built.names[1:]
    old = cast("dict[str, object]", json.loads(document))
    old["format"] = 1
    columns = cast("dict[str, list[object]]", old["locations"])
    columns["name"] = ["Northern Gulf of Akaira", *columns["name"][1:]]
    first = atlas.from_files(json.dumps(old).encode(), picture)
    assert first.names[0] == "Northern Gulf of Akaira"
    words = atlas.Words(
        label=lambda key: f"<{key}>",
        key=lambda key: key.upper(),
        name=lambda name: render(name, "russian"),
    )
    labels = [label for label, _, _ in atlas.legend(again, "cultures", words)]
    assert "<sea>" in labels
    assert "A_CULTURE" in labels
    found = atlas.find(again, "Аланд", words=words)
    assert "place" in [match.kind for match in found]


def test_a_lens_names_each_locations_legend_entry_and_keeps_the_legacy_pictures() -> None:
    """Every location's class is its legend entry; ramps leave land unclassed; the classic
    layers draw what ``render`` drew before lenses (their legend is the lens's)."""
    built = synthetic_atlas()
    for layer in atlas.LAYERS:
        lens = atlas.lens(built, layer)
        assert lens.colours.shape == (built.cells, 3)
        assert lens.legend == tuple(atlas.legend(built, layer))
        for cell in range(built.cells):
            entry = int(lens.classes[cell])
            if entry >= 0 and layer != "land":
                assert tuple(int(v) for v in lens.colours[cell]) == lens.legend[entry][1]
        assert bool(lens.ramp) == (layer in atlas.RAMPS)
    land = np.flatnonzero(built.kinds == atlas.KINDS.index("land"))
    population = atlas.lens(built, "population")
    inhabited = [cell for cell in land if built.population[cell] > 0]
    assert all(population.classes[cell] == -1 for cell in inhabited)
    areas = atlas.lens(built, "areas")
    assert len({int(areas.values[cell]) for cell in land}) == len({built.areas[c] for c in land})
