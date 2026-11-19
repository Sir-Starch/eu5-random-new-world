"""Regional rasters share one world and remain continuous at its longitude wrap."""

# NumPy stubs type array operations as Any.
# pyright: reportAny=false
from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import numpy as np

from rnw.continent_domains import CONTINENTS, Domain
from rnw.continent_world import WorldRegion, compose_regions
from rnw.eu5_biomes import CellBiomes
from rnw.eu5_newworld import outside_contacts, regional_geometry
from rnw.eu5_nw_export import (
    _replacement_water_links,  # pyright: ignore[reportPrivateUsage]
    settled_biomes,
)
from rnw.eu5_seas import Coast
from rnw.model import CellClass
from rnw.newworld import derive_world
from rnw.ports import ForeignCoast, pair_lengths, relabel

if TYPE_CHECKING:
    from rnw.eu5_map import Eu5Map


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
