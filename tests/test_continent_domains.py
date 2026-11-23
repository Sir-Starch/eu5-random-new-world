"""The shared canvas preserves land ownership and resolves overlapping coastal domains."""

# NumPy stubs type array comparisons as Any.
# pyright: reportAny=false

from __future__ import annotations

from itertools import combinations
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from rnw.continent_domains import (
    CONTINENTS,
    Domain,
    _coastal_claim,  # pyright: ignore[reportPrivateUsage]
    _coastal_waters,  # pyright: ignore[reportPrivateUsage]
    _pacific_islands,  # pyright: ignore[reportPrivateUsage]
    _protected_sea,  # pyright: ignore[reportPrivateUsage]
    _rejoin_fragments,  # pyright: ignore[reportPrivateUsage]
    _released_coasts,  # pyright: ignore[reportPrivateUsage]
    _sighted,  # pyright: ignore[reportPrivateUsage]
    _without_islets,  # pyright: ignore[reportPrivateUsage]
    plan_domains,
)
from rnw.eu5_biomes import EQUATOR_ROW, block_features, climate_grid, land_features, latitude_tenths
from rnw.eu5_canvas import CanvasError, select_canvas
from rnw.model import CellClass
from rnw.settings import PRESETS
from rnw.topology import adjacency_pairs, unpack_pairs

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.eu5_map import Eu5Map
    from rnw.settings import NewWorldSettings


def test_a_water_pocket_inside_retained_land_is_outside_the_american_claim() -> None:
    marine = np.ones((9, 11), dtype=bool)
    marine[2:7, 2:7] = False
    marine[4, 4] = True
    footprint = np.zeros_like(marine)
    footprint[5, 9] = True
    claimed = marine | footprint
    protected = _coastal_claim(claimed, footprint, marine)
    assert not protected[4, 4]
    assert protected[0, 0]
    assert protected[5, 9]
    assert np.count_nonzero(claimed ^ protected) == 1


def _map() -> Eu5Map:
    labels = np.zeros((400, 800), dtype=np.int32)
    labels[40:350, 190:245] = 1
    labels[70:290, 620:724] = 2
    labels[45:70, 660:715] = 3
    labels[205:228, :42] = 4
    labels[205:228, -25:] = 4
    labels[270:325, 16:108] = 4
    labels[180:188, 695:703] = 5
    return cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                keys=("ocean", "america", "africa", "asia", "oceania", "lake"),
                labels=labels,
                continents=(
                    "pacific_ocean_continent",
                    "america",
                    "africa",
                    "asia",
                    "oceania",
                    "africa",
                ),
                classes=(CellClass.SEA, *(CellClass.LAND for _ in range(4)), CellClass.LAKE),
                ambiguous=np.array([True, False, False, False, False, False]),
            ),
        ),
    )


def _settings(names: tuple[str, ...]) -> dict[str, NewWorldSettings]:
    return {name: PRESETS[CONTINENTS[name].preset].new_world for name in names}


def _in_world(
    domain: Domain, local: NDArray[np.bool_], shape: tuple[int, int]
) -> NDArray[np.bool_]:
    result = np.zeros(shape, dtype=bool)
    for crop, original in domain.spans():
        result[domain.rows, original] = local[:, crop]
    return result


SELECTIONS = tuple(
    names for size in range(1, len(CONTINENTS) + 1) for names in combinations(CONTINENTS, size)
)


@pytest.mark.parametrize("names", SELECTIONS)
def test_all_selections_cover_their_land_once(names: tuple[str, ...]) -> None:
    game = _map()
    labels = game.labels
    domains = plan_domains(game, _settings(names[::-1]))
    assert tuple(domain.continent.key for domain in domains) == names
    owners = np.full(labels.shape, -1, dtype=np.int8)
    for index, domain in enumerate(domains):
        mask = _in_world(domain, domain.mask, labels.shape)
        footprint = _in_world(domain, domain.footprint, labels.shape)
        member = np.array([tag == domain.continent.key for tag in game.continents], dtype=bool)
        assert np.array_equal(footprint, member[labels])
        assert not np.any(footprint & ~mask)
        assert np.all(owners[mask] == -1)
        assert not np.any(mask & (labels == 3))
        if names != ("america",):
            assert not np.any(mask & ~(member[labels] | (labels == 0)))
        owners[mask] = index


def test_original_african_land_interface_and_oceanian_wrap() -> None:
    game = _map()
    africa, oceania = plan_domains(game, _settings(("africa", "oceania")))
    assert africa.land_interface is not None
    interface = _in_world(africa, africa.land_interface, game.labels.shape)
    expected = np.zeros(game.labels.shape, dtype=bool)
    expected[70, 660:715] = True
    assert np.array_equal(interface, expected)
    assert oceania.land_interface is None
    assert oceania.seam is not None
    assert oceania.first_row > 0
    rows = slice(205 - oceania.first_row, 228 - oceania.first_row)
    assert np.all(oceania.footprint[rows, oceania.seam - 1 : oceania.seam + 1])


def test_shared_southern_ocean_and_seeded_african_boundary() -> None:
    game = _map()
    selected = {member: CONTINENTS[member].geography() for member in CONTINENTS}
    america, africa, oceania = plan_domains(game, selected, seed=42, require_asia_connection=True)
    assert africa.join_asia
    assert africa.land_interface is not None
    assert africa.land_interface.any()
    assert oceania.rows.stop == game.labels.shape[0]
    assert oceania.mask[-1].any()
    assert america.shared_ocean
    assert africa.north_water_rows > 0
    plans = plan_domains(game, selected, seed=42)
    assert not plans[1].join_asia
    assert plans[1].land_interface is None


def test_three_canvases_partition_the_whole_ocean_and_share_borders() -> None:
    game = _map()
    names = tuple(CONTINENTS)
    owner = np.full(game.labels.shape, -1, dtype=np.int32)
    for number, domain in enumerate(plan_domains(game, _settings(names), seed=739)):
        mask = _in_world(domain, domain.mask, game.labels.shape)
        assert np.all(owner[mask] == -1)
        owner[mask] = number
    water = game.labels == 0
    assert np.all(owner[water] >= 0)
    ocean_owner = np.where(water, owner, -1).astype(np.int32)
    pairs = set(unpack_pairs(adjacency_pairs(ocean_owner, wrap_x=True)))
    assert {(0, 1), (0, 2), (1, 2)} <= pairs


def test_africa_claims_no_water_beyond_its_northern_limit() -> None:
    game = _map()
    africa = plan_domains(game, _settings(tuple(CONTINENTS)), seed=739)[1]
    limit = africa.first_row + africa.north_water_rows
    assert limit > 0
    mask = _in_world(africa, africa.mask, game.labels.shape)
    assert mask[limit:].any()
    assert not mask[:limit].any()


def _northern_sea_map() -> tuple[Eu5Map, int, int]:
    """Africa's own sea above its limit beside European land, and another sea to its west."""
    base = _map()
    labels = base.labels.copy()
    labels[5:40, 640:700] = 6
    labels[5:40, 700:760] = 7
    labels[100:140, 560:620] = 8
    game = _with_locations(
        base,
        labels,
        ("northern_sea", CellClass.SEA, "africa"),
        ("european_shore", CellClass.LAND, "europe"),
        ("western_sea", CellClass.SEA, "africa"),
    )
    return game, 6, 8


def test_water_africa_is_denied_above_its_limit_stays_with_the_retained_map() -> None:
    game, north, west = _northern_sea_map()
    owner = _owners(game, tuple(CONTINENTS))
    assert np.all(owner[game.labels == north] == -1)
    assert np.all(owner[game.labels == west] >= 0)


@pytest.mark.parametrize("names", [("oceania",), ("africa", "oceania")])
def test_a_partial_selection_leaves_enclosed_water_to_the_retained_map(
    names: tuple[str, ...],
) -> None:
    game, passage = _passage_map(gap=0)
    owner = _owners(game, names)
    assert np.all(owner[game.labels == passage] == -1)


def test_a_partial_african_world_claims_no_water_beyond_its_limit() -> None:
    game, north, _ = _northern_sea_map()
    owner = _owners(game, ("africa",))
    assert np.all(owner[game.labels == north] == -1)
    assert not (owner[:45] >= 0).any()


def test_vanilla_water_speck_inside_asia_stays_in_the_preserved_canvas() -> None:
    game = _map()
    game.labels[55, 680] = 0
    domains = plan_domains(game, _settings(tuple(CONTINENTS)), seed=739)
    given = [_in_world(domain, domain.mask, game.labels.shape) for domain in domains]
    assert not any(mask[55, 680] for mask in given)


def test_eurasian_canvas_keeps_native_inner_waters_and_leaves_africa_its_shore() -> None:
    game = _map()
    labels = game.labels.copy()
    labels[45:70, 655:660] = 6
    labels[120:170, 610:620] = 7
    game = cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                labels=labels,
                keys=(*game.keys, "eurasian_strait", "african_sea"),
                classes=(*game.classes, CellClass.SEA, CellClass.SEA),
                continents=(*game.continents, "asia", "africa"),
                ambiguous=np.append(game.ambiguous, (False, False)),
            ),
        ),
    )
    domains = plan_domains(game, _settings(tuple(CONTINENTS)), seed=739)
    owner = np.zeros(labels.shape, dtype=np.int8)
    for number, domain in enumerate(domains, 1):
        area = _in_world(domain, domain.mask, labels.shape)
        assert not np.any(owner[area])
        owner[area] = number
    assert np.all(owner[(labels == 3) | (labels == 6)] == 0)
    assert np.all(owner[labels == 7] == 2)
    assert np.all(owner[labels == 0] > 0)


def test_an_islet_of_a_replaced_continent_does_not_punch_a_hole_in_another_canvas() -> None:
    game = _map()
    game.labels[240, 270] = 4
    names = tuple(CONTINENTS)
    domains = plan_domains(game, _settings(names), seed=739)
    given = {
        domain.continent.key: _in_world(domain, domain.mask, game.labels.shape)
        for domain in domains
    }
    assert given["america"][240, 270]
    assert not given["oceania"][240, 270]
    assert not any(domain.groups for domain in domains)


def test_open_ocean_island_enters_placement_inside_its_canvas() -> None:
    game = _map()
    labels = game.labels.copy()
    labels[260:265, 430:435] = 6
    with_island = cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                labels=labels,
                keys=(*game.keys, "island"),
                classes=(*game.classes, CellClass.LAND),
                continents=(*game.continents, "atlantic_ocean_continent"),
                ambiguous=np.append(game.ambiguous, False),
            ),
        ),
    )
    domains = plan_domains(with_island, _settings(tuple(CONTINENTS)), seed=739)
    holder = next(domain for domain in domains if domain.groups)
    assert holder.groups[0].locations == (6,)
    points = holder.footprints[0]
    assert points.size == 25
    assert np.all(holder.mask[points.rows, points.columns])


def _with_locations(
    game: Eu5Map, labels: NDArray[np.int32], *added: tuple[str, CellClass, str]
) -> Eu5Map:
    """The test map with extra locations numbered after the existing ones."""
    return cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                labels=labels,
                keys=(*game.keys, *(key for key, _, _ in added)),
                classes=(*game.classes, *(kind for _, kind, _ in added)),
                continents=(*game.continents, *(name for _, _, name in added)),
                ambiguous=np.append(game.ambiguous, np.zeros(len(added), dtype=bool)),
            ),
        ),
    )


def _owners(game: Eu5Map, selected: tuple[str, ...]) -> NDArray[np.int8]:
    """The canvas of each pixel in order of selection, -1 where the map is retained."""
    owner = np.full(game.labels.shape, -1, dtype=np.int8)
    for number, domain in enumerate(plan_domains(game, _settings(selected), seed=739)):
        owner[_in_world(domain, domain.mask, game.labels.shape)] = number
    return owner


def _passage_map(gap: int) -> tuple[Eu5Map, int]:
    """Two European shores with an open-ocean location in the passage between them."""
    base = _map()
    labels = base.labels.copy()
    labels[330:370, 300 : 330 - gap] = 6
    labels[330:370, 380 + gap : 410] = 7
    labels[330:370, 330:380] = 8
    return (
        _with_locations(
            base,
            labels,
            ("west_shore", CellClass.LAND, "europe"),
            ("east_shore", CellClass.LAND, "europe"),
            ("passage", CellClass.SEA, "atlantic_ocean_continent"),
        ),
        8,
    )


def test_open_water_between_eurasian_shores_stays_retained() -> None:
    game, passage = _passage_map(gap=0)
    owner = _owners(game, tuple(CONTINENTS))
    assert np.all(owner[game.labels == passage] == -1)
    assert owner[310, 355] >= 0
    assert owner[390, 355] >= 0


def test_enclosed_water_detached_from_the_eurasian_map_is_regenerated() -> None:
    game, passage = _passage_map(gap=3)
    owner = _owners(game, tuple(CONTINENTS))
    assert np.all(owner[game.labels == passage] >= 0)


def test_a_sight_line_stops_at_the_land_of_a_generated_continent() -> None:
    target = np.zeros((3, 12), dtype=bool)
    blocking = np.zeros_like(target)
    target[1, 10] = True
    blocking[1, 5] = True
    seen = _sighted(target, blocking, 0, 1, 12)
    assert seen[1, 5:10].all()
    assert not seen[1, :5].any()
    assert not seen[0].any()
    assert _sighted(target, blocking, 0, -1, 12)[1, 11]


def test_a_water_speck_inside_replaced_land_belongs_to_its_canvas() -> None:
    game = _map()
    game.labels[100, 210] = 0
    america = plan_domains(game, _settings(tuple(CONTINENTS)), seed=739)[0]
    assert _in_world(america, america.mask, game.labels.shape)[100, 210]


def _stranded(
    *, solid: tuple[bool, bool, bool]
) -> tuple[NDArray[np.int32], NDArray[np.int8], NDArray[np.int8], NDArray[np.bool_]]:
    labels = np.zeros((2, 16384), dtype=np.int32)
    labels[:, :100] = 1
    labels[1, 200:205] = 2
    claimed = np.where(labels > 0, 0, -1).astype(np.int8)
    connected = claimed.copy()
    connected[0, 50] = -1
    connected[1, 200:205] = -1
    return labels, claimed, connected, np.array(solid, dtype=bool)


def test_a_small_piece_of_replaced_land_cut_off_by_retained_water_stays_out_of_the_canvas() -> None:
    labels, claimed, connected, solid = _stranded(solid=(False, True, True))
    joined = _rejoin_fragments(labels, claimed, connected, solid)
    # The piece of location 1, whose body is in the canvas, is left to the water round it.
    assert joined[0, 50] == -1
    # Location 2 lies wholly there: it is removed whole, so it stays with its canvas.
    assert (joined[1, 200:205] == 0).all()
    assert np.array_equal(joined >= 0, claimed >= 0) is False


def test_a_cut_off_piece_of_water_stays_with_its_canvas() -> None:
    labels, claimed, connected, solid = _stranded(solid=(False, False, False))
    joined = _rejoin_fragments(labels, claimed, connected, solid)
    assert joined[0, 50] == 0
    assert np.array_equal(joined >= 0, claimed >= 0)


def test_a_large_location_stranded_among_retained_waters_is_an_error() -> None:
    labels = np.zeros((2, 16384), dtype=np.int32)
    labels[:, 100:2000] = 2
    claimed = np.where(labels > 0, 1, -1).astype(np.int8)
    with pytest.raises(CanvasError, match="stranded"):
        _ = _rejoin_fragments(
            labels, claimed, np.full_like(claimed, -1), np.array([False, False, True])
        )


def _coasts() -> Eu5Map:
    # Replaced land (africa) in the middle; retained land (asia) at the right edge; sea zones
    # filed under the retained continent wash one or both.
    labels = np.zeros((4, 12), dtype=np.int32)
    labels[:, 4:6] = 1  # africa
    labels[:, 6:8] = 2  # sea that washes only africa
    labels[:, 8:10] = 3  # sea that washes africa through 2 and asia
    labels[:, 10:11] = 4  # asia, with open sea beyond it across the seam
    labels[:, 2:4] = 5  # a sea that washes only africa but is kept for its ships
    return cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                keys=("deep", "africa", "bay", "strait", "asia", "ships"),
                labels=labels,
                continents=("pacific_ocean_continent", "africa", "asia", "asia", "asia", "asia"),
                classes=(
                    CellClass.SEA,
                    CellClass.LAND,
                    CellClass.SEA,
                    CellClass.SEA,
                    CellClass.LAND,
                    CellClass.SEA,
                ),
            ),
        ),
    )


def test_a_kept_coast_that_washes_only_replaced_land_goes_to_the_canvas_that_replaces_it() -> None:
    game = _coasts()
    kept = np.array([False, False, True, True, False, True])
    released = _released_coasts(game, kept, {"africa"}, ())
    # `bay` touches africa and `strait`; `strait` touches `bay` and asia: only `bay` is released,
    # and to africa, the second of the continents.
    assert released.tolist() == [-1, -1, 1, -1, -1, 1]


def test_a_coast_kept_for_its_ships_stays() -> None:
    game = _coasts()
    kept = np.array([False, False, True, True, False, True])
    released = _released_coasts(game, kept, {"africa"}, {"ships"})
    assert released.tolist() == [-1, -1, 1, -1, -1, -1]


def test_a_coast_between_two_replaced_continents_goes_to_the_one_it_touches_most() -> None:
    # africa 1 | bay 3 | oceania 2, and a second africa location beyond the bay; then the same
    # without it, where each continent touches the bay once and the lower number wins.
    labels = np.zeros((2, 12), dtype=np.int32)
    labels[:, 1] = 1
    labels[:, 2] = 3
    labels[:, 3] = 2
    labels[0, 2] = 4
    game = cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                keys=("deep", "africa", "oceania", "bay", "more"),
                labels=labels,
                continents=("pacific_ocean_continent", "africa", "oceania", "asia", "africa"),
                classes=(
                    CellClass.SEA,
                    CellClass.LAND,
                    CellClass.LAND,
                    CellClass.SEA,
                    CellClass.LAND,
                ),
            ),
        ),
    )
    kept = np.array([False, False, False, True, False])
    both = {"africa", "oceania"}
    assert _released_coasts(game, kept, both, ())[3] == 1
    labels[0, 2] = 3
    assert _released_coasts(game, kept, both, ())[3] == 1
    labels[:, 1] = 0
    assert _released_coasts(game, kept, both, ())[3] == 2


def _released_map() -> Eu5Map:
    """The synthetic map with two coastal zones filed under asia beside africa's coast."""
    base = _map()
    labels = base.labels.copy()
    labels[100:140, 724:790] = 6  # washes only africa, and reaches far beyond its water band
    labels[250:285, 724:745] = 7  # washes africa and a retained shore
    labels[250:285, 745:760] = 3
    return cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                keys=(*base.keys, "bay", "gulf"),
                labels=labels,
                continents=(*base.continents, "asia", "asia"),
                classes=(*base.classes, CellClass.SEA, CellClass.SEA),
                ambiguous=np.array([*base.ambiguous.tolist(), False, False]),
            ),
        ),
    )


def test_africa_takes_the_whole_coastal_zone_that_washes_only_its_land() -> None:
    game = _released_map()
    (africa,) = plan_domains(game, _settings(("africa",)))
    mask = _in_world(africa, africa.mask, game.labels.shape)
    assert mask[game.labels == 6].all()
    assert not mask[game.labels == 7].any()
    assert not mask[game.labels == 3].any()


def _islets(*, site: bool = False, neighbour: bool = False) -> tuple[Eu5Map, tuple[Domain, ...]]:
    labels = np.zeros((6, 16384), dtype=np.int32)
    labels[1:5, 100:400] = 1  # the body of location 1, with a wide shelf of water
    labels[2, 9000:9004] = 1  # its stray piece among retained water
    labels[2, 12000:12020] = 2  # location 2, a small island that lies wholly there
    mask = np.zeros(labels.shape, dtype=bool)
    mask[:, 50:2000] = True
    mask[2, 9000:9004] = True
    mask[2, 12000:12020] = True
    footprint = (labels > 0) & mask
    game = cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                keys=("deep", "one", "two"),
                labels=labels,
                continents=("pacific_ocean_continent", "africa", "africa"),
                classes=(CellClass.SEA, CellClass.LAND, CellClass.LAND),
            ),
        ),
    )
    domain = Domain(
        CONTINENTS["africa"],
        0,
        16384,
        mask,
        footprint,
        island_sites=((2, 9001, 1),) if site else (),
    )
    domains = [domain]
    if neighbour:
        # Another canvas touches the small island: together they are no small piece.
        other = np.zeros(labels.shape, dtype=bool)
        other[:, 12020:15000] = True
        domains.append(Domain(CONTINENTS["oceania"], 0, 16384, other, np.zeros_like(other)))
    return game, tuple(domains)


def test_a_small_piece_of_replaced_land_among_retained_water_is_left_out_of_the_canvases() -> None:
    game, domains = _islets()
    (result,) = _without_islets(game, domains)
    assert not result.mask[2, 9000:9004].any()
    assert not result.footprint[2, 9000:9004].any()
    # The small island that lies wholly there goes too, and the main piece stays.
    assert not result.mask[2, 12000:12020].any()
    assert result.mask[:, 50:2000].all()


def test_a_small_piece_with_an_island_site_stays_in_the_canvas() -> None:
    game, domains = _islets(site=True)
    (result,) = _without_islets(game, domains)
    assert result.mask[2, 9000:9004].all()
    assert not result.mask[2, 12000:12020].any()


def test_a_piece_that_another_canvas_touches_is_not_a_small_piece() -> None:
    game, domains = _islets(neighbour=True)
    africa, oceania = _without_islets(game, domains)
    assert africa.mask[2, 12000:12020].all()
    assert oceania.mask[:, 12020:15000].all()


def test_canvases_without_small_pieces_are_not_changed() -> None:
    game, (domain,) = _islets()
    domain.mask[2, 9000:9004] = False
    domain.mask[2, 12000:12020] = False
    assert _without_islets(game, (domain,)) == (domain,)


def test_open_pacific_islands_take_compact_sites_between_the_existing_claims() -> None:
    labels = np.zeros((128, 512), dtype=np.int32)
    owners = np.full(labels.shape, -1, dtype=np.int8)
    owners[:, 40:110] = 0
    keep = owners == 0
    first = _pacific_islands(
        _map(),
        labels,
        owners,
        np.arange(128, dtype=np.int64),
        np.arange(512, dtype=np.int64),
        step=1,
        seed=17,
    )
    assert len(first) == 3
    assert all(owners[row, col] == 2 for row, col, _ in first)
    assert np.array_equal(owners == 0, keep)
    assert 0 < np.count_nonzero(owners == 2) < 500


def test_pacific_islands_keep_away_from_impassable_retained_water() -> None:
    labels = np.zeros((128, 512), dtype=np.int32)
    labels[:, 440:] = 1
    owners = np.full(labels.shape, -1, dtype=np.int8)
    owners[:, 40:110] = 0
    game = cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                keys=("ocean", "shut"),
                continents=("pacific_ocean_continent", "pacific_ocean_continent"),
            ),
        ),
    )
    rows, columns = np.arange(128, dtype=np.int64), np.arange(512, dtype=np.int64)

    def place(closed: tuple[str, ...]) -> NDArray[np.bool_]:
        claimed = owners.copy()
        sites = _pacific_islands(
            game, labels, claimed, rows, columns, step=1, seed=17, closed=closed
        )
        assert sites
        return claimed == 2

    assert place(())[:, 440:].any()
    assert not place(("shut",))[:, 440 - 9 :].any()


def test_a_partly_claimed_retained_gulf_keeps_its_whole_shore() -> None:
    labels = np.zeros((20, 24), dtype=np.int32)
    labels[5:15, 10:16] = 1
    labels[5:15, 6:10] = 2
    game = cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                keys=("ocean", "shore", "gulf"),
                labels=labels,
                continents=("indian_ocean_continent", "asia", "asia"),
                classes=(CellClass.SEA, CellClass.LAND, CellClass.SEA),
                ambiguous=np.array([True, False, False]),
            ),
        ),
    )
    claim = np.zeros(labels.shape, dtype=bool)
    claim[5:15, 9] = True
    protected = _protected_sea(game, claim, {"africa": CONTINENTS["africa"].geography()})
    assert protected.tolist() == [False, False, True]


def test_an_unselected_navigational_toll_reserves_its_sea_zone() -> None:
    game = _map()
    settings = {"africa": CONTINENTS["africa"].geography()}
    (domain,) = plan_domains(game, settings, retained_tolls={"ocean"})
    assert np.array_equal(domain.mask, domain.footprint)


def test_america_only_uses_the_current_canvas() -> None:
    game = _map()
    selected = _settings(("america",))
    (domain,) = plan_domains(game, selected)
    expected = select_canvas(game, selected["america"].ocean_band_px, expanded=True)
    assert domain.legacy_canvas is not None
    assert np.array_equal(domain.mask, expected.mask)
    assert domain.spans() == tuple(expected.spans())
    assert [(group.locations, group.zones) for group in domain.legacy_canvas.groups] == [
        (group.locations, group.zones) for group in expected.groups
    ]
    assert np.array_equal(domain.legacy_canvas.removed, expected.removed)


def test_small_islands_do_not_claim_the_full_continental_band() -> None:
    footprint = np.zeros((48, 64), dtype=bool)
    footprint[10:20, 10:20] = True
    footprint[25:27, 40:42] = True
    seas = ~footprint
    seas[23, 13] = False  # A retained location in the large landmass's band.
    coastal = _coastal_waters(footprint, seas, reach=8, island_reach=3, continental_area=64)
    assert coastal[26, 12]
    assert coastal[29, 40]
    assert not coastal[30, 40]
    assert not coastal[23, 13]
    assert not np.any(coastal & footprint)


def test_continents_resolve_their_own_presets() -> None:
    selected = {
        "america": CONTINENTS["america"].geography("wall"),
        "africa": CONTINENTS["africa"].geography("archipelago"),
        "oceania": CONTINENTS["oceania"].geography("supercontinent"),
    }
    assert selected["america"] == PRESETS["wall"].new_world
    assert selected["africa"].land_permille == PRESETS["archipelago"].new_world.land_permille
    assert selected["oceania"].land_permille == PRESETS["supercontinent"].new_world.land_permille
    assert not selected["africa"].expand_oceans
    assert not selected["oceania"].expand_oceans


@pytest.mark.parametrize("name", ["wall", "omerika"])
def test_american_landforms_cannot_be_applied_to_other_continents(name: str) -> None:
    for key in ("africa", "oceania"):
        with pytest.raises(CanvasError, match="American options"):
            _ = CONTINENTS[key].geography(name)
        with pytest.raises(CanvasError, match="American options"):
            _ = plan_domains(_map(), {key: PRESETS[name].new_world})


@pytest.mark.parametrize("names", [(), ("asia",)])
def test_rejects_empty_and_unsupported_selections(names: tuple[str, ...]) -> None:
    selected = dict.fromkeys(names, PRESETS["continents"].new_world)
    with pytest.raises(CanvasError, match="Choose at least one supported continent"):
        _ = plan_domains(_map(), selected)


def test_window_climate_and_cell_size_votes_use_global_latitude() -> None:
    land = np.zeros((64, 64), dtype=bool)
    land[3:12, 5:25] = True
    heights = np.full(land.shape, 7000, dtype=np.int32)
    row0 = EQUATOR_ROW - 256
    grid = climate_grid(~land, heights, seasonal=True, row0=row0)
    points = np.array([[7, 12]], dtype=np.int64)
    cell = land_features(grid, points, np.array([7000], dtype=np.int64))
    assert cell[0, 0] == latitude_tenths(np.array([row0 + points[0, 0]]))[0]
    regional, local = block_features(land, heights, grid)
    legacy, base = block_features(land, heights, climate_grid(~land, heights, seasonal=True))
    assert np.array_equal(regional, legacy)
    assert np.all(local[:, 0] < base[:, 0])


def _iberian_map() -> Eu5Map:
    """The test map with a European peninsula (area ``andalusia_area``) of the region
    ``iberia_region``, a strait west of Africa, an island of that region nearer to Africa than
    the peninsula is, a Portuguese location (area ``north_portugal_area``) of the same peninsula
    that lies as near to Africa, and another European location."""
    base = cast("SimpleNamespace", cast("object", _map()))
    labels = base.labels.copy()
    labels[130:200, 590:604] = 6
    labels[100:130, 560:604] = 7
    labels[140:160, 608:613] = 8
    labels[200:240, 590:604] = 9
    return cast(
        "Eu5Map",
        cast(
            "object",
            SimpleNamespace(
                keys=(*base.keys, "iberia", "france", "balearic", "portugal"),
                labels=labels,
                continents=(*base.continents, "europe", "europe", "europe", "europe"),
                classes=(*base.classes, *(CellClass.LAND,) * 4),
                ambiguous=np.array([*base.ambiguous, False, False, False, False]),
                regions=("",) * len(base.keys)
                + ("iberia_region", "france_region", "iberia_region", "iberia_region"),
                areas=("",) * len(base.keys)
                + ("andalusia_area", "paris_area", "balearics_area", "north_portugal_area"),
            ),
        ),
    )


def _africa(game: Eu5Map, *, seed: int | None = 42, mode: str = "off") -> Domain:
    selected = {"africa": CONTINENTS["africa"].geography()}
    return plan_domains(game, selected, seed=seed, iberia_connection=mode)[0]


def test_the_iberian_link_is_off_by_default_and_changes_nothing() -> None:
    game = _iberian_map()
    default, off = _africa(game), _africa(game, mode="off")
    assert not default.join_iberia
    assert default.iberia_interface is None
    assert np.array_equal(default.mask, off.mask)
    assert (default.contact_land is None) == (off.contact_land is None)
    if default.contact_land is not None and off.contact_land is not None:
        assert np.array_equal(default.contact_land, off.contact_land)


def test_a_required_iberian_link_meets_only_iberian_land_and_leaves_no_strait() -> None:
    game = _iberian_map()
    domain = _africa(game, mode="required")
    assert domain.join_iberia
    assert domain.strait is None
    assert domain.iberia_interface is not None
    assert domain.iberia_interface.any()
    interface = _in_world(domain, domain.iberia_interface, game.labels.shape)
    touched = np.zeros(game.labels.shape, dtype=bool)
    touched[1:] |= game.labels[:-1] == 6
    touched[:-1] |= game.labels[1:] == 6
    touched[:, 1:] |= game.labels[:, :-1] == 6
    touched[:, :-1] |= game.labels[:, 1:] == 6
    assert np.all(touched[interface])
    # Neither the other European location (the Seine side) nor the island of the region, which
    # lies nearer to Africa and would leave the Mediterranean open, is a contact of the link; the
    # land of the strait's coast is the only land it may meet, though Portugal stays retained land.
    assert domain.contact_land is not None
    contact = _in_world(domain, domain.contact_land, game.labels.shape)
    assert contact[game.labels == 6].all()
    assert contact[game.labels == 9].all()
    assert not contact[game.labels == 7].any()
    assert not contact[game.labels == 8].any()
    portugal = game.labels == 9
    beside = np.zeros_like(portugal)
    beside[1:] |= portugal[:-1]
    beside[:-1] |= portugal[1:]
    beside[:, 1:] |= portugal[:, :-1]
    beside[:, :-1] |= portugal[:, 1:]
    assert not np.any(interface & beside)
    islet = np.zeros(game.labels.shape, dtype=bool)
    islet[game.labels == 8] = True
    near = np.zeros_like(islet)
    near[1:] |= islet[:-1]
    near[:-1] |= islet[1:]
    near[:, 1:] |= islet[:, :-1]
    near[:, :-1] |= islet[:, 1:]
    assert not np.any(interface & near)


def test_an_allowed_iberian_link_is_drawn_per_seed_and_rules_out_the_strait() -> None:
    game = _iberian_map()
    drawn = [_africa(game, seed=seed, mode="allowed") for seed in range(60)]
    joined = [domain for domain in drawn if domain.join_iberia]
    assert 0 < len(joined) < len(drawn)
    assert all(domain.strait is None for domain in joined)
    assert all(domain.iberia_interface is not None for domain in joined)
    assert all(domain.iberia_interface is None for domain in drawn if not domain.join_iberia)
    # A seed drawn without the link keeps what it had with the option off.
    kept = next(domain for domain in drawn if not domain.join_iberia)
    seed = drawn.index(kept)
    assert np.array_equal(kept.mask, _africa(game, seed=seed, mode="off").mask)
