"""The natural wasteland plan: budget, coast, barrier, reachability, biomes, determinism.

Every land, climate and calibration here is made up; none of it needs the game.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from collections import deque
from dataclasses import replace
from fractions import Fraction
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from rnw import epoch, wording
from rnw.barrens import (
    FLAT_SPREAD,
    GROUND_KINDS,
    KINDS,
    MOUNTAIN_FLOOR,
    TOPOGRAPHY,
    Calibration,
    Terrain,
    WastelandPlan,
    WastelandSettings,
    _allocate,  # pyright: ignore[reportPrivateUsage]
    calibrate,
    legacy_topography,
    plan_wastelands,
)
from rnw.eu5_biomes import (
    BIOME_DEFINITIONS,
    TERRAIN_MATERIALS,
    biome_rules,
    climate_groups,
    wasteland_settings,
)
from rnw.eu5_newworld import _land_name  # pyright: ignore[reportPrivateUsage]
from rnw.eu5_nw_export import (
    NewWorldExportError,
    _land_count,  # pyright: ignore[reportPrivateUsage]
    _wasteland_settings,  # pyright: ignore[reportPrivateUsage]
)
from rnw.model import CellClass
from rnw.newworld import derive_world
from rnw.settings import build_settings
from rnw.wording import Phrase

if TYPE_CHECKING:
    from pathlib import Path

    from rnw.newworld import NewWorld

WIDTH, HEIGHT = 20, 14
CELL_PX = 4000
GROUPS = {"tropical": "tropical", "arid": "arid"}
ALL_LAND = frozenset({CellClass.LAND, CellClass.WASTELAND})


def _dune_needs_desert(_climate: str, vegetation: str, topography: str) -> bool:
    return not (topography == TOPOGRAPHY["dune"] and vegetation != "desert")


def _grid(
    *, wasteland: set[int] | None = None, barrier: set[int] | None = None
) -> tuple[Terrain, WastelandSettings]:
    """A land of ``WIDTH`` by ``HEIGHT`` cells: jungle in the west, desert in the east, a ridge
    between, hills at the east and the rest low and smooth. Its outer ring touches the sea and
    its top and bottom rows are polar (wasteland); ``barrier`` are cells the Wall runs through."""
    count = WIDTH * HEIGHT
    xs = np.arange(count) % WIDTH
    ys = np.arange(count) // WIDTH
    coastal = (xs == 0) | (xs == WIDTH - 1) | (ys == 0) | (ys == HEIGHT - 1)
    polar = (ys == 0) | (ys == HEIGHT - 1)
    height = np.full(count, 7000, dtype=np.int64) + (xs * 37 + ys * 91) % 1500
    spread = np.full(count, 400, dtype=np.int64) + (xs * 53 + ys * 29) % 300
    ridge = (xs >= 9) & (xs <= 10) & (ys > 2) & (ys < HEIGHT - 3)
    height[ridge] = MOUNTAIN_FLOOR + 1500
    spread[ridge] = FLAT_SPREAD + 300
    hills = (xs >= 14) & (xs <= 16)
    spread[hills] = FLAT_SPREAD + 200
    west = xs < 10
    wall = np.zeros(count, dtype=bool)
    wall[sorted(barrier or set())] = True
    kinds = [CellClass.LAND] * count
    for cell in range(count):
        if polar[cell] or cell in (wasteland or set()) or cell in (barrier or set()):
            kinds[cell] = CellClass.WASTELAND
    edges = [
        (cell, other)
        for cell in range(count)
        for other in (cell + 1 if xs[cell] < WIDTH - 1 else -1, cell + WIDTH)
        if 0 <= other < count
    ]
    terrain = Terrain(
        kinds=tuple(kinds),
        climate=tuple("tropical" if flag else "arid" for flag in west),
        vegetation=tuple("jungle" if flag else "desert" for flag in west),
        ground=tuple(
            "mountain" if ridge[cell] else "hills" if hills[cell] else "flat"
            for cell in range(count)
        ),
        height=height,
        spread=spread,
        pixels=np.full(count, CELL_PX, dtype=np.int64),
        rain=xs * 50,
        latitude=np.abs(ys - HEIGHT // 2) * 60,
        coastal=coastal,
        polar=polar,
        barrier=wall,
        edges=np.array(edges, dtype=np.int64),
    )
    return terrain, WastelandSettings(0, polar, wall, GROUPS, _dune_needs_desert)


CALIBRATION = Calibration(
    rates={
        ("tropical", "jungle", "flat"): 200_000,
        ("tropical", "jungle", "hills"): 50_000,
        ("tropical", "jungle", "mountain"): 100_000,
        ("arid", "desert", "dune"): 300_000,
        ("arid", "desert", "hills"): 80_000,
        ("arid", "desert", "mountain"): 80_000,
    },
    sizes={
        "flat": (8000, 8000, 16000),
        "dune": (8000, 12000, 24000),
        "hills": (4000, 8000),
        "mountain": (4000, 4000, 8000),
    },
)


def _plan(
    budget: int,
    seed: int = 1,
    *,
    wasteland: set[int] | None = None,
    barrier: set[int] | None = None,
) -> tuple[Terrain, WastelandPlan]:
    terrain, settings = _grid(wasteland=wasteland, barrier=barrier)
    return terrain, plan_wastelands(
        terrain, CALIBRATION, replace(settings, budget=budget), seed=seed
    )


def _reaches_coast(terrain: Terrain, kinds: tuple[CellClass, ...]) -> bool:
    passable = {cell for cell, kind in enumerate(kinds) if kind is CellClass.LAND}
    sinks = [cell for cell in passable if terrain.coastal[cell]]
    around: dict[int, list[int]] = {cell: [] for cell in passable}
    for first, second in terrain.edges.tolist():
        if first in passable and second in passable:
            around[first].append(second)
            around[second].append(first)
    seen = set(sinks)
    queue = deque(sinks)
    while queue:
        for other in around[queue.popleft()]:
            if other not in seen:
                seen.add(other)
                queue.append(other)
    return seen == passable


def test_every_voted_ground_allows_a_kind() -> None:
    """Each ground the game's locations vote allows one kind; dunes ask for flat ground."""
    assert set(GROUND_KINDS) == {"mountains", "plateau", "hills", "flatland", "wetlands"}
    assert set(GROUND_KINDS.values()) == set(KINDS) - {"dune"}


def test_epoch_63_topography_rule_is_kept() -> None:
    """The cells the plan does not choose keep the topography the highest cells had."""
    assert legacy_topography(MOUNTAIN_FLOOR, 5000) == "mountain_wasteland"
    assert legacy_topography(MOUNTAIN_FLOOR - 1, FLAT_SPREAD - 1) == "plateau_wasteland"
    assert legacy_topography(MOUNTAIN_FLOOR - 1, FLAT_SPREAD) == "hills_wasteland"


def test_the_budget_is_met_and_the_polar_cells_come_on_top() -> None:
    terrain, plan = _plan(70)
    waste = sum(1 for kind in plan.kinds if kind is CellClass.WASTELAND)
    assert plan.stats["shortfall"] == 0
    assert plan.stats["barrier"] == 0
    assert plan.stats["polar"] == int(terrain.polar.sum())
    assert plan.stats["planned"] == 70
    assert waste == 70 + int(terrain.polar.sum())


def test_the_barrier_counts_in_the_budget_and_stays_wasteland() -> None:
    barrier = {WIDTH * row + 9 for row in range(2, HEIGHT - 2)}
    terrain, plan = _plan(70, barrier=barrier)
    assert plan.stats["barrier"] == len(barrier)
    assert plan.stats["planned"] == 70 - len(barrier)
    for cell in barrier:
        assert plan.kinds[cell] is CellClass.WASTELAND
        assert plan.topography[cell] == legacy_topography(
            int(terrain.height[cell]), int(terrain.spread[cell])
        )
    waste = sum(1 for kind in plan.kinds if kind is CellClass.WASTELAND)
    assert waste == 70 + int(terrain.polar.sum())
    assert _reaches_coast(terrain, plan.kinds)


def test_a_wall_world_plans_the_land_beside_its_barrier() -> None:
    """The land on either side of the barrier gets natural wastelands of several kinds."""
    barrier = {WIDTH * row + 9 for row in range(2, HEIGHT - 2)}
    terrain, plan = _plan(70, barrier=barrier)
    planned = {
        cell: name
        for cell, name in plan.topography.items()
        if not terrain.polar[cell] and cell not in barrier
    }
    assert planned
    assert any(cell % WIDTH < 9 for cell in planned)
    assert any(cell % WIDTH > 9 for cell in planned)
    assert len(set(planned.values())) >= 3


def test_the_plan_gives_several_kinds_under_both_vegetations() -> None:
    terrain, plan = _plan(70)
    chosen = {cell: name for cell, name in plan.topography.items() if not terrain.polar[cell]}
    assert len(set(chosen.values())) >= 3
    assert {terrain.vegetation[cell] for cell in chosen} == {"jungle", "desert"}
    by_kind = cast("dict[str, int]", plan.stats["by_kind"])
    assert sum(by_kind.values()) == plan.stats["planned"]


def test_every_wasteland_is_drawn_by_a_biome_of_its_own() -> None:
    terrain, plan = _plan(70)
    for cell, name in plan.topography.items():
        if terrain.polar[cell]:
            continue
        assert plan.kinds[cell] is CellClass.WASTELAND
        assert name in TOPOGRAPHY.values()
        assert _dune_needs_desert(terrain.climate[cell], terrain.vegetation[cell], name)


def test_a_kind_stands_only_on_ground_that_allows_it() -> None:
    terrain, plan = _plan(70)
    for cell, name in plan.topography.items():
        if terrain.polar[cell]:
            continue
        ground = terrain.ground[cell]
        assert name in {TOPOGRAPHY[ground], TOPOGRAPHY["dune"]}
        if name == TOPOGRAPHY["dune"]:
            assert ground == "flat"


def test_cells_at_the_sea_can_be_wasteland_and_the_poles_always_are() -> None:
    terrain, plan = _plan(150)
    assert all(plan.kinds[cell] is CellClass.WASTELAND for cell in np.flatnonzero(terrain.polar))
    at_sea = [
        cell
        for cell in np.flatnonzero(terrain.coastal & ~terrain.polar).tolist()
        if plan.kinds[cell] is CellClass.WASTELAND
    ]
    assert at_sea
    assert _reaches_coast(terrain, plan.kinds)


def test_a_kind_the_game_puts_at_the_sea_is_planned_there_as_often() -> None:
    """The share of a class's cells at the sea follows the factor read from the game."""
    inland = replace(CALIBRATION, shore=dict.fromkeys(KINDS, 0))
    neutral = replace(CALIBRATION, shore=dict.fromkeys(KINDS, 1000))
    shore = replace(CALIBRATION, shore=dict.fromkeys(KINDS, 4000))
    terrain, settings = _grid()
    settings = replace(settings, budget=50)

    def at_sea(calibration: Calibration) -> int:
        plan = plan_wastelands(terrain, calibration, settings, seed=3)
        return sum(
            1
            for cell in np.flatnonzero(terrain.coastal & ~terrain.polar).tolist()
            if plan.kinds[cell] is CellClass.WASTELAND
        )

    assert at_sea(inland) < at_sea(neutral) < at_sea(shore)


def test_every_passable_cell_still_reaches_a_coast() -> None:
    for budget in (30, 90, 150):
        terrain, plan = _plan(budget)
        assert _reaches_coast(terrain, plan.kinds)


def test_the_plan_is_the_same_for_the_same_seed_and_another_for_another() -> None:
    _, first = _plan(60, seed=7)
    _, again = _plan(60, seed=7)
    _, other = _plan(60, seed=8)
    assert first.kinds == again.kinds
    assert first.topography == again.topography
    assert first.kinds != other.kinds


def test_no_budget_leaves_no_wasteland_that_the_plan_did_not_keep() -> None:
    """The highest cells of an earlier plan are not kept: the plan starts afresh, at the sea too."""
    inside = {WIDTH * 4 + 3, WIDTH * 4 + 4, WIDTH * 7 + 12, WIDTH * 5 + WIDTH - 1}
    terrain, plan = _plan(0, wasteland=inside)
    assert all(kind is CellClass.LAND for cell, kind in enumerate(plan.kinds) if cell in inside)
    assert plan.stats["planned"] == 0
    assert sum(1 for kind in plan.kinds if kind is CellClass.WASTELAND) == int(terrain.polar.sum())


def test_land_that_cannot_reach_a_coast_is_sealed_with_the_old_topography() -> None:
    """A pocket the barrier encloses cannot be passable: it is wasteland as before."""
    ring = {
        cell
        for cell in range(WIDTH * HEIGHT)
        if cell % WIDTH in (4, 14) and 2 <= cell // WIDTH <= HEIGHT - 3
    } | {
        cell
        for cell in range(WIDTH * HEIGHT)
        if cell // WIDTH in (2, HEIGHT - 3) and 4 <= cell % WIDTH <= 14
    }
    terrain, plan = _plan(0, barrier=ring)
    inner = [
        cell
        for cell in range(WIDTH * HEIGHT)
        if 4 < cell % WIDTH < 14 and 2 < cell // WIDTH < HEIGHT - 3
    ]
    assert plan.stats["unreachable_forced"] == len(inner)
    for cell in inner:
        assert plan.kinds[cell] is CellClass.WASTELAND
        assert plan.topography[cell] == legacy_topography(
            int(terrain.height[cell]), int(terrain.spread[cell])
        )


def test_no_two_units_of_one_attribute_set_touch() -> None:
    """Touching wastelands of identical attributes are one location in the game, so the plan
    never lets two of its units touch: the connected pieces of one attribute set are its units."""
    terrain, plan = _plan(80)
    triples = {
        cell: (terrain.climate[cell], terrain.vegetation[cell], name)
        for cell, name in plan.topography.items()
        if not terrain.polar[cell]
    }
    around: dict[int, list[int]] = {cell: [] for cell in triples}
    for first, second in terrain.edges.tolist():
        if first in triples and second in triples and triples[first] == triples[second]:
            around[first].append(second)
            around[second].append(first)
    seen: set[int] = set()
    sizes: list[int] = []
    for start in triples:
        if start in seen:
            continue
        seen.add(start)
        queue, size = deque([start]), 0
        while queue:
            size += 1
            for other in around[queue.popleft()]:
                if other not in seen:
                    seen.add(other)
                    queue.append(other)
        sizes.append(size)
    assert len(sizes) == plan.stats["units"]
    assert sorted(sizes, reverse=True)[:8] == plan.stats["largest_units"]


def test_allocation_sums_to_the_total_and_respects_every_capacity() -> None:
    classes = [("a", "x", "flat"), ("a", "y", "flat"), ("b", "x", "dune")]
    weights = dict(zip(classes, (100, 300, 600), strict=True))
    capacity = dict(zip(classes, (20, 500, 500), strict=True))
    for numerator in range(10):
        got = _allocate(weights, capacity, 400, Fraction(numerator, 10))
        assert sum(got.values()) == 400
        assert all(got.get(key, 0) <= capacity[key] for key in classes)
    # the smallest class is bound by its capacity and the rest is divided again by weight
    capped = _allocate(weights, capacity, 400, Fraction(0))
    assert capped[classes[0]] == 20
    assert capped[classes[1]] in {126, 127}
    assert capped[classes[2]] in {253, 254}


def test_calibration_reads_rates_by_area_and_sizes_by_kind() -> None:
    classes = (
        CellClass.LAND,
        CellClass.WASTELAND,
        CellClass.WASTELAND,
        CellClass.LAND,
        CellClass.WASTELAND,
        CellClass.WASTELAND,
    )
    found = calibrate(
        classes=classes,
        climate=("arctic", "oceanic", "arctic", "arctic", "arid", "arctic"),
        vegetation=("forest", "forest", "forest", "forest", "desert", "forest"),
        topography=(
            "flatland",
            "flatland_wasteland",
            "mountain_wasteland",
            "mountains",
            "dune_wasteland",
            "hills_wasteland",
        ),
        coastal=np.array([False, True, False, False, False, False]),
        pixels=np.array([100_000, 50_000, 50_000, 100_000, 10_000, 90_000], dtype=np.int64),
        include=np.array([True, True, True, True, True, False]),
        groups={"arctic": "arctic", "oceanic": "arctic"},
    )
    # oceanic and arctic are one group, so the patch is 300,000 px and each kind covers a sixth
    assert found.rates[("arctic", "forest", "flat")] == 166_666
    assert found.rates[("arctic", "forest", "mountain")] == 166_666
    assert ("arctic", "forest", "hills") not in found.rates  # not included
    assert ("arid", "desert", "dune") not in found.rates  # a patch too small for a rate
    assert found.sizes["dune"] == (10_000,)
    assert found.sizes["flat"] == (50_000,)
    assert "hills" not in found.sizes
    # a sixth of the patch's area touches the sea: its flat wasteland does, so it is six times as
    # likely to as the patch, its mountain wasteland does not; a kind with no coast in its patch
    # to compare has no factor
    assert found.shore["flat"] == 6000
    assert found.shore["mountain"] == 0
    assert "dune" not in found.shore


BIOMES = """\
000 =
{
	biome = default_biome
}
001 =
{
	topography = dune_wasteland
	biome = desert_rock_wasteland
}
002 =
{
	climate = tropical
	climate = subtropical
	vegetation = jungle
	topography = flatland_wasteland
	biome = jungle_waste_biome
}
003 =
{
	climate = arid
	vegetation = desert
	topography = hills_wasteland
	biome = bare_biome
}
"""
MATERIALS = """\
{
	name = desert_rock_wasteland
	materials = { sand sand rock }
}
{
	name = jungle_waste_biome
	materials = { moss moss mud }
}
"""


def test_the_game_files_say_which_wastelands_can_be_drawn() -> None:
    rules = biome_rules(BIOMES)
    got = wasteland_settings(
        rules,
        {"desert_rock_wasteland": 3, "jungle_waste_biome": 3, "bare_biome": 0},
        budget=5,
        polar=np.zeros(3, dtype=bool),
        barrier=np.zeros(3, dtype=bool),
    )
    assert got.groups["subtropical"] == got.groups["tropical"] == "subtropical"
    assert got.biome_ok("arid", "desert", TOPOGRAPHY["dune"])
    assert got.biome_ok("tropical", "jungle", TOPOGRAPHY["flat"])
    # a biome without materials, and one only default_biome would draw, are no candidates
    assert not got.biome_ok("arid", "desert", TOPOGRAPHY["hills"])
    assert not got.biome_ok("arid", "sparse", TOPOGRAPHY["mountain"])
    assert climate_groups(rules)["arid"] == "arid"


def _game(tmp_path: Path) -> Path:
    for relative, text in ((BIOME_DEFINITIONS, BIOMES), (TERRAIN_MATERIALS, MATERIALS)):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_text(text, encoding="utf-8")
    return tmp_path


def _world() -> NewWorld:
    labels = np.arange(12, dtype=np.int32).reshape(3, 4)
    kinds = (CellClass.LAND,) * 10 + (CellClass.WASTELAND, CellClass.SEA)
    return derive_world(labels, kinds, np.full(labels.shape, 9000, dtype=np.int32))


def test_the_plan_reads_the_land_cells_the_world_numbers_first(tmp_path: Path) -> None:
    game, world = _game(tmp_path), _world()
    settings = build_settings("continents")
    settings = replace(settings, new_world=replace(settings.new_world, wasteland_permille=500))
    assert settings.algorithm == epoch.NATURAL_WASTELANDS
    assert _land_count(world) == 11
    got = _wasteland_settings(game, world, settings)
    # the budget counts every land cell (here 11) by the share of the settings
    assert got.budget == 5
    assert got.polar.tolist() == [True] * 4 + [False] * 4 + [True] * 3
    assert not got.barrier.any()
    # the Wall's barrier is read from the world
    walled = replace(world, barrier=np.array([5, 6], dtype=np.int64))
    assert _wasteland_settings(game, walled, settings).barrier.nonzero()[0].tolist() == [5, 6]


def test_water_before_land_is_no_world_the_plan_can_read() -> None:
    world = _world()
    swapped = replace(world, classes=(CellClass.SEA, *world.classes[:-1]))
    with pytest.raises(NewWorldExportError, match="land cells"):
        _ = _land_count(swapped)


def test_the_wasteland_plan_is_gated_by_its_own_epoch() -> None:
    assert epoch.SWITCHES["NATURAL_WASTELANDS"] == epoch.NATURAL_WASTELANDS
    assert epoch.NATURAL_WASTELANDS > epoch.OLDEST_SELECTABLE
    assert epoch.NATURAL_WASTELANDS <= epoch.CURRENT
    assert epoch.first_release(epoch.NATURAL_WASTELANDS) == "1.3.0"


@pytest.mark.parametrize("kind", KINDS)
def test_every_kind_has_a_topography_of_the_game(kind: str) -> None:
    assert TOPOGRAPHY[kind].endswith("_wasteland")


def test_a_wasteland_is_named_for_its_terrain_from_the_new_epoch() -> None:
    new, old = epoch.NATURAL_WASTELANDS, epoch.NATURAL_WASTELANDS - 1
    terms = {
        "flatland_wasteland": wording.WILDS,
        "dune_wasteland": wording.DESERT,
        "hills_wasteland": wording.HIGHLANDS,
        "plateau_wasteland": wording.HIGHLANDS,
        "mountain_wasteland": wording.HIGHLANDS,
    }
    for topography, term in terms.items():
        assert _land_name("Kaira", CellClass.WASTELAND, topography, new) == Phrase(term, "Kaira")
        # before epoch 64 every wasteland, whatever its topography, was a highland
        assert _land_name("Kaira", CellClass.WASTELAND, topography, old) == Phrase(
            wording.HIGHLANDS, "Kaira"
        )
    assert _land_name("Kaira", CellClass.LAND, "flatland", new) == "Kaira"
    assert _land_name("Kaira", CellClass.LAKE, "", new) == Phrase(wording.LAKE, "Kaira")
