"""Regional rasters share one world and remain continuous at its longitude wrap."""

# NumPy stubs type array operations as Any.
# pyright: reportAny=false
from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from rnw.continent_domains import CONTINENTS, Domain
from rnw.continent_world import (
    WorldRegion,
    absorb_land_fragments,
    absorb_ocean_specks,
    compose_regions,
    relocated_canvas,
)
from rnw.eu5_biomes import CellBiomes
from rnw.eu5_canvas import Canvas, CanvasError, OceanRemainder
from rnw.eu5_map import Eu5Map
from rnw.eu5_newworld import outside_contacts, regional_geometry
from rnw.eu5_nw_export import (
    _replacement_water_links,  # pyright: ignore[reportPrivateUsage]
    _wasteland_shore,  # pyright: ignore[reportPrivateUsage]
    settled_biomes,
)
from rnw.eu5_seas import Coast, mediterranean_crossing
from rnw.model import CellClass
from rnw.newworld import derive_world
from rnw.ports import ForeignCoast, pair_lengths, relabel

if TYPE_CHECKING:
    from rnw.eu5_newworld import Plan
    from rnw.eu5_seas import Water


def _game() -> Eu5Map:
    labels = np.tile(np.array([1, 1, 1, 1, 1, 1, 1, 0], dtype=np.int32), (5, 1))
    labels[1:3, 7] = 2
    labels[1:3, 0] = 2
    return cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                labels=labels,
                keys=("old", "sea", "isle"),
                classes=(CellClass.LAND, CellClass.SEA, CellClass.LAND),
                ambiguous=np.zeros(3, dtype=bool),
                continents=("europe", "africa", "oceania"),
            ),
        ),
    )


def _region(name: str, first: int, values: list[int]) -> WorldRegion:
    labels = np.tile(np.array(values, dtype=np.int32), (2, 1))
    domain = Domain(CONTINENTS[name], first, 8, labels >= 0, labels == 0, first_row=1)
    kinds = (CellClass.LAND, CellClass.SEA) if name == "oceania" else (CellClass.LAND,)
    return WorldRegion(domain, derive_world(labels, kinds, np.ones_like(labels)))


def test_a_wrapped_location_keeps_one_identity_and_a_local_centre() -> None:
    game = _game()
    africa = _region("africa", 2, [0, 0])
    oceania = _region("oceania", 7, [0, 0, 1])
    out = compose_regions(game, (africa, oceania))
    assert out.world.wrap_x
    assert out.world.classes == (CellClass.LAND, CellClass.LAND, CellClass.SEA)
    assert out.cell_ids["africa"].tolist() == [0]
    assert out.cell_ids["oceania"].tolist() == [1, 2]
    assert out.world.labels[1].tolist() == [1, 2, 0, 0, -1, -1, -1, 1]
    assert out.world.labels[0].tolist() == [-1] * 8
    assert out.world.centroids[1].tolist() == [1, 7]
    assert out.canvas.removed.tolist() == [False, False, True]
    contacts = outside_contacts(game, out.canvas, out.world, offset=len(game.keys))
    assert all(old != 2 for old, _ in contacts)
    # A shared pass sees both landmasses on the same sea location.
    assert pair_lengths(out.world) == {(0, 2): 2, (1, 2): 2}
    local = regional_geometry(game, oceania.domain, {})
    assert local.pixels[2] == 4
    assert local.columns[2] == 0


def test_southern_passage_grows_water_cells_only_in_closed_ocean() -> None:
    game = _game()
    game.labels[-2:, :] = 1
    game.labels[-1, 0] = 0
    game.ambiguous[1] = True
    region = _region("africa", 2, [0])
    combined = compose_regions(game, (region,), southern_passage=1, seed=17)
    assert combined.world.labels[-1, 0] == -1
    assert np.all(combined.world.labels[-1, 1:] >= 1)
    assert np.all(combined.world.labels[-2, 3:] == -1)
    assert all(kind is CellClass.SEA for kind in combined.world.classes[1:])


def test_distinct_labels_across_the_wrap_share_a_real_border() -> None:
    data = np.array([[0, -1, 1], [0, 2, 1]], dtype=np.int32)
    world = derive_world(data, (CellClass.LAND,) * 3, np.zeros_like(data), wrap_x=True)
    assert (0, 1) in world.edges
    assert pair_lengths(world)[0, 1] == 2


def test_biome_tables_follow_the_final_cell_numbers_after_coastal_folds() -> None:
    labels = np.array([[0, 1, 2, 2, 3]], dtype=np.int32)
    world = derive_world(
        labels, (CellClass.LAND, CellClass.SEA, CellClass.SEA, CellClass.LAKE), labels
    )
    final, translated = relabel(world, {2: 1})
    coast = Coast(
        final, ForeignCoast(), {}, {}, frozenset(), frozenset(), 1, source_cells=translated
    )
    biomes = CellBiomes(
        ("temperate", "cold", "arid", "tropical"),
        ("woods", "", "", ""),
        ("flatland", "", "", ""),
        ("wool", "", "", ""),
    )
    result = settled_biomes(biomes, world, coast)
    assert result.climate == ("temperate", "arid", "tropical")
    assert result.vegetation == ("woods", "", "")
    assert result.topography == ("flatland", "", "")
    assert result.raw_material == ("wool", "", "")


def test_cut_retained_sea_records_each_connected_remainder() -> None:
    labels = np.zeros((3, 7), dtype=np.int32)
    game = cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                labels=labels,
                keys=("open_sea",),
                classes=(CellClass.SEA,),
                ambiguous=np.array([False]),
            ),
        ),
    )
    stripe = np.zeros((3, 1), dtype=np.int32)
    world = derive_world(stripe, (CellClass.LAND,), stripe)
    regions = [
        WorldRegion(Domain(CONTINENTS[name], col, 7, stripe == 0, stripe == 0), world)
        for name, col in (("africa", 1), ("oceania", 4))
    ]
    shared = compose_regions(game, regions)
    assert shared.canvas.trimmed.tolist() == [True]
    assert [part.pixels for part in shared.canvas.ocean_parts] == [9, 6]
    assert all(part.source == 0 for part in shared.canvas.ocean_parts)


def test_an_enclosed_closed_ocean_speck_follows_its_actual_land_location() -> None:
    labels = np.zeros((5, 1024), dtype=np.int32)
    labels[2, 100] = 1
    labels[2, 200:220] = 1
    rgb = np.zeros((*labels.shape, 3), dtype=np.uint8)
    game = Eu5Map(
        ("land", "ocean"),
        np.array([0x123456, 0], dtype=np.int64),
        (CellClass.LAND, CellClass.SEA),
        np.array([False, True]),
        ("asia", "pacific_ocean_continent"),
        rgb,
        labels,
        rgb,
        (),
        (),
        (),
        (),
    )
    canvas = Canvas(
        0,
        0,
        labels == 0,
        labels.shape,
        np.zeros(2, dtype=bool),
        np.array([False, True]),
        (OceanRemainder(1, np.array([[2, 100, 101]], dtype=np.int64), 1),),
    )
    result, fixed = absorb_ocean_specks(game, canvas)
    assert result.labels[2, 100] == 0
    assert result.rgb[2, 100].tolist() == [0x12, 0x34, 0x56]
    assert np.all(result.labels[2, 200:220] == 1)
    assert game.labels[2, 100] == 1
    assert fixed.enclosed_ocean == ((canvas.ocean_parts[0], 0x123456),)


def _islet_map() -> tuple[Eu5Map, Canvas]:
    # Replaced land (location 1) with a stray piece inside a retained sea zone (location 2).
    labels = np.full((8, 16384), 2, dtype=np.int32)
    labels[:, :100] = 0
    labels[2:6, 100:140] = 1
    labels[3, 500:503] = 1
    labels[4, 500] = 1
    rgb = np.zeros((*labels.shape, 3), dtype=np.uint8)
    game = Eu5Map(
        ("shore", "islet", "bay"),
        np.array([0x111111, 0x222222, 0x336699], dtype=np.int64),
        (CellClass.LAND, CellClass.LAND, CellClass.SEA),
        np.array([False, False, False]),
        ("asia", "africa", "asia"),
        rgb,
        labels,
        rgb,
        (),
        (),
        (),
        (),
    )
    mask = labels == 1
    mask[3, 500:503] = False
    mask[4, 500] = False
    canvas = Canvas(0, 0, mask, labels.shape, np.zeros(3, dtype=bool), np.zeros(3, dtype=bool))
    return game, canvas


def test_a_stray_piece_of_replaced_land_takes_the_colour_of_the_retained_water_round_it() -> None:
    game, canvas = _islet_map()
    result, fixed = absorb_land_fragments(game, canvas, {"africa"})
    assert (result.labels[3, 500:503] == 2).all()
    assert result.labels[4, 500] == 2
    assert result.rgb[3, 501].tolist() == [0x33, 0x66, 0x99]
    # The islet's body is untouched, the original map is not edited in place.
    assert (result.labels[2:6, 100:140] == 1).all()
    assert game.labels[3, 500] == 1
    ((part, colour),) = fixed.enclosed_ocean
    assert colour == 0x336699
    assert part.source == 2
    assert part.pixels == 4
    assert sorted(part.runs.tolist()) == [[3, 500, 503], [4, 500, 501]]


def test_an_islet_left_out_of_every_canvas_whole_is_drowned_and_counted_as_removed() -> None:
    game, canvas = _islet_map()
    nothing = Canvas(0, 0, game.labels == 9, game.labels.shape, canvas.removed, canvas.trimmed)
    result, fixed = absorb_land_fragments(game, nothing, {"africa"})
    assert (result.labels == 1).sum() == 0
    assert fixed.drowned is not None
    assert fixed.drowned.tolist() == [False, True, False]
    # A location with no pixel left is removed from the map, with no canvas of its own.
    counted = relocated_canvas(result, fixed)
    assert counted.removed.tolist() == [False, True, False]
    assert not counted.trimmed.any()


def test_a_canvas_that_leaves_no_replaced_land_out_is_not_changed() -> None:
    game, canvas = _islet_map()
    whole = Canvas(0, 0, game.labels == 1, game.labels.shape, canvas.removed, canvas.trimmed)
    result, fixed = absorb_land_fragments(game, whole, {"africa"})
    assert result is game
    assert fixed is whole


def test_a_large_piece_of_replaced_land_left_out_of_every_canvas_is_an_error() -> None:
    game, canvas = _islet_map()
    labels = game.labels.copy()
    labels[:, 1000:3000] = 1
    with pytest.raises(CanvasError, match="too large"):
        _ = absorb_land_fragments(
            replace(game, labels=labels),
            Canvas(0, 0, labels == 0, labels.shape, canvas.removed, canvas.trimmed),
            {"africa"},
        )


def test_cut_coastal_route_needs_a_new_navigable_connection() -> None:
    game = cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                keys=("coast", "sea"),
                classes=(CellClass.SEA, CellClass.SEA),
                ambiguous=np.zeros(2, dtype=bool),
                continents=("europe", "africa"),
            ),
        ),
    )
    links = {0: [2], 2: [0, 3], 3: [2, 1], 1: [3]}
    lost = [(0, 1)]
    assert _replacement_water_links(game, lost, links, frozenset({"africa"}), ()) == {(0, 1)}
    assert not _replacement_water_links(game, lost, links, frozenset({"africa"}), (1,))
    assert not _replacement_water_links(game, lost, links, frozenset({"oceania"}), ())


def test_only_a_wasteland_and_its_sea_carry_no_contact() -> None:
    game = cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                classes=(CellClass.WASTELAND, CellClass.SEA, CellClass.LAND, CellClass.WASTELAND)
            ),
        ),
    )
    assert _wasteland_shore(game, (0, 1))
    assert not _wasteland_shore(game, (1, 2))
    assert not _wasteland_shore(game, (0, 3))


def test_mediterranean_crossing_uses_the_retained_and_generated_shores() -> None:
    installed = np.ones((100, 164), dtype=np.int32)
    installed[:, :74] = 0
    generated = np.full(installed.shape, -1, dtype=np.int32)
    generated[:, 74:81] = 0
    generated[:, 81:] = 1
    world = derive_world(generated, (CellClass.SEA, CellClass.LAND), np.zeros_like(generated))
    game = cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                labels=installed,
                keys=("european", "old_sea"),
                continents=("europe", "africa"),
                classes=(CellClass.LAND, CellClass.SEA),
            ),
        ),
    )
    plan = cast(
        "Plan",
        cast(
            "object",
            SimpleNamespace(
                cells=[
                    SimpleNamespace(key="new_sea", continent="africa"),
                    SimpleNamespace(key="new_coast", continent="africa"),
                ]
            ),
        ),
    )
    water = cast(
        "Water", cast("object", SimpleNamespace(coast=SimpleNamespace(world=world), zones=set()))
    )
    result = mediterranean_crossing(game, water, plan, (50, 81))
    assert result is not None
    assert result.row(100).startswith("european;new_coast;sea;new_sea;")
    assert result.start[1] == 73
    assert result.stop[1] == 81
