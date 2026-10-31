"""Climate and vegetation stay consistent through spatial regularization (synthetic data).

``assign_biomes`` smooths the calibration's nearest-neighbour votes over the location graph.
Whatever it smooths, a generated cell must end with a (climate, vegetation) pair that the
calibration holds, taken from votes its own climate supports (issue #4). Every calibration
and map here is synthetic; none needs the game.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw.eu5_biomes import (
    EQUATOR_ROW,
    NEIGHBOURS,
    CellBiomes,
    ClimateGrid,
    Generated,
    VanillaLocations,
    assign_biomes,
    regularize_votes,
    smooth_scores,
)
from rnw.model import CellClass

if TYPE_CHECKING:
    from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class Site:
    """A location's features: raster row (latitude), rainfall index, mean height, sea distance."""

    row: int = 0
    rain: int = 0
    height: int = 6000
    coast: int = 200


Calibration = list[tuple[str, str, Site]]

# Raster rows of latitudes near 30 and 60 degrees (``LATITUDE_ANCHORS``).
SUBTROPICS = EQUATOR_ROW - 1689
SUBARCTIC = EQUATOR_ROW - 3622
DRY = Site(rain=0)
WET = Site(rain=1000)


def _group(climate: str, vegetation: str, site: Site) -> Calibration:
    """One full vote of calibration locations of one pair at one place in feature space."""
    return [(climate, vegetation, site)] * NEIGHBOURS


def _chain(count: int) -> tuple[tuple[int, int], ...]:
    return tuple((i, i + 1) for i in range(count - 1))


def _points(sites: list[Site]) -> NDArray[np.int64]:
    return np.array([[site.row, 4 * i] for i, site in enumerate(sites)], dtype=np.int64)


def _grid(sites: list[Site]) -> ClimateGrid:
    def row(values: list[int]) -> NDArray[np.int64]:
        return np.array([values], dtype=np.int64)

    return ClimateGrid(
        rain=row([site.rain for site in sites]),
        coast=row([site.coast for site in sites]),
        shore=row([0] * len(sites)),
    )


def _classify(
    calibration: Calibration, cells: list[Site], edges: tuple[tuple[int, int], ...]
) -> CellBiomes:
    """Climate and vegetation of ``cells`` joined by ``edges``, calibrated on ``calibration``.

    One New World donor location lets the raw materials, which this module does not test,
    be drawn.
    """
    keys = tuple(f"source_{i}" for i in range(len(calibration) + 1))
    game = SimpleNamespace(
        keys=keys,
        classes=(CellClass.LAND,) * len(keys),
        continents=("europe",) * len(calibration) + ("america",),
    )
    templates = {
        key: {
            "climate": climate,
            "vegetation": vegetation,
            "topography": "flatland",
            "raw_material": "stone",
        }
        for key, (climate, vegetation, _) in zip(keys, [*calibration, calibration[0]], strict=True)
    }
    sites = [site for _, _, site in calibration] + [Site()]
    vanilla = VanillaLocations(
        points=_points(sites),
        mean_height=np.array([site.height for site in sites], dtype=np.int64),
        pairs=np.empty(0, dtype=np.int64),
    )
    generated = Generated(
        kinds=(CellClass.LAND,) * len(cells),
        points=_points(cells),
        mean_height=np.array([site.height for site in cells], dtype=np.int64),
        spread=np.zeros(len(cells), dtype=np.int64),
        edges=edges,
        coastal=np.zeros(len(cells), dtype=bool),
    )
    biomes, _ = assign_biomes(
        game_map=game,  # pyright: ignore[reportArgumentType] - only keys, classes, continents
        templates=templates,
        vanilla=vanilla,
        vanilla_grid=_grid(sites),
        final_grid=_grid(cells),
        cells=generated,
        seed=1,
    )
    return biomes


def _pairs(biomes: CellBiomes) -> set[tuple[str, str]]:
    return set(zip(biomes.climate, biomes.vegetation, strict=True))


def _calibrated(calibration: Calibration) -> set[tuple[str, str]]:
    return {(climate, vegetation) for climate, vegetation, _ in calibration}


def test_a_dry_centre_among_wet_neighbours_stays_desert() -> None:
    """Issue #4: forest reached an arid centre through three wet neighbours; it has no pair."""
    calibration = _group("arid", "desert", DRY) + _group("tropical", "forest", WET)
    # The centre touches three wet cells; each of those touches three more dry ones.
    edges = tuple(
        [(0, i) for i in range(1, 4)]
        + [(i, 4 + (i - 1) * 3 + j) for i in range(1, 4) for j in range(3)]
    )
    cells = [DRY, *[WET] * 3, *[DRY] * 9]
    biomes = _classify(calibration, cells, edges)
    assert set(biomes.climate) == {"arid"}
    assert set(biomes.vegetation) == {"desert"}


def test_a_wet_cell_in_a_dry_climate_takes_the_vegetation_of_that_climate() -> None:
    """The cell's own votes are all tropical; its climate comes out arid, so none of them count."""
    calibration = _group("arid", "desert", DRY) + _group("tropical", "forest", WET)
    biomes = _classify(calibration, [WET, *[DRY] * 8], _chain(9))
    assert set(biomes.climate) == {"arid"}
    assert set(biomes.vegetation) == {"desert"}


def test_both_climates_keep_their_own_vegetation_across_their_border() -> None:
    """A border between two calibrated pairs gives each side its pair, never a mixture."""
    calibration = _group("arid", "desert", DRY) + _group("tropical", "forest", WET)
    biomes = _classify(calibration, [WET] * 4 + [DRY] * 4, _chain(8))
    assert biomes.climate == ("tropical",) * 4 + ("arid",) * 4
    assert biomes.vegetation == ("forest",) * 4 + ("desert",) * 4


@pytest.mark.parametrize("seed", range(12))
def test_random_maps_carry_only_calibrated_pairs(seed: int) -> None:
    """Cells of mixed latitudes and moisture never get a pair the calibration lacks."""
    zones = {"tropical": EQUATOR_ROW, "arid": SUBTROPICS, "continental": EQUATOR_ROW - 3029}
    calibration: Calibration = []
    for climate, vegetation, rain in (
        ("tropical", "forest", 1000),
        ("tropical", "grasslands", 600),
        ("arid", "desert", 0),
        ("arid", "grasslands", 250),
        ("continental", "forest", 400),
        ("continental", "grasslands", 150),
    ):
        calibration += _group(climate, vegetation, Site(row=zones[climate], rain=rain))
    side = 6
    edges = tuple(
        [(r * side + c, r * side + c + 1) for r in range(side) for c in range(side - 1)]
        + [(r * side + c, (r + 1) * side + c) for r in range(side - 1) for c in range(side)]
    )
    rng = np.random.default_rng(seed)
    rows = list(zones.values())
    cells = [
        Site(row=rows[int(rng.integers(0, len(rows)))], rain=int(rng.integers(0, 1001)))
        for _ in range(side * side)
    ]
    biomes = _classify(calibration, cells, edges)
    assert _pairs(biomes) <= _calibrated(calibration)
    assert _classify(calibration, cells, edges) == biomes


def test_a_climate_without_local_votes_widens_the_neighbourhood() -> None:
    """Cell 0 votes for climate 1 only, as do its neighbour's; climate 0 reaches it in round 2."""
    # Joint classes: (climate 0, vegetation 0), (climate 1, vegetation 1).
    scores = np.array([[0, 1], [0, 1], [1000, 0], [1000, 0], [1000, 0], [1000, 0]], dtype=np.int64)
    edges = np.array(_chain(6), dtype=np.int64)
    joint = np.array([0, 1], dtype=np.int64)
    assert smooth_scores(scores, edges, 1)[0, 0] == 0  # one round leaves it without a vote
    climate, vegetation = regularize_votes(scores, joint, joint, edges, 2)
    assert climate.tolist() == [0] * 6
    assert vegetation.tolist() == [0] * 6  # never vegetation 1, which only climate 1 holds


def test_a_cell_without_any_vote_is_refused() -> None:
    """No vote in any neighbourhood is an error, not an arbitrary pair."""
    joint = np.array([0, 1], dtype=np.int64)
    with pytest.raises(ValueError, match="no climate or vegetation vote"):
        _ = regularize_votes(
            np.zeros((2, 2), dtype=np.int64), joint, joint, np.empty((0, 2), np.int64), 2
        )


def test_vegetation_follows_moisture_from_the_coast_inland() -> None:
    """Forest, grassland and desert follow falling rainfall and rising distance from the sea."""
    calibration = (
        _group("oceanic", "forest", Site(rain=1000, coast=0))
        + _group("continental", "grasslands", Site(rain=500, coast=100))
        + _group("arid", "desert", Site(rain=0, coast=200))
    )
    cells = [Site(rain=1000 - 125 * i, coast=25 * i) for i in range(9)]
    biomes = _classify(calibration, cells, _chain(9))
    wetness = {"desert": 0, "grasslands": 1, "forest": 2}
    levels = [wetness[name] for name in biomes.vegetation]
    assert levels == sorted(levels, reverse=True)
    assert biomes.vegetation[0] == "forest"
    assert biomes.vegetation[4] == "grasslands"
    assert biomes.vegetation[-1] == "desert"
    assert (biomes.climate[0], biomes.climate[-1]) == ("oceanic", "arid")
    assert _pairs(biomes) <= _calibrated(calibration)


def test_a_rain_shadow_does_not_inherit_the_windward_forest() -> None:
    """Behind a range the lee side stays dry; the forest ends on the windward slope."""
    calibration = (
        _group("oceanic", "forest", Site(rain=1000, height=6000, coast=0))
        + _group("alpine", "sparse", Site(rain=600, height=20000, coast=100))
        + _group("arid", "desert", Site(rain=0, height=6000, coast=200))
    )
    windward = Site(rain=1000, height=6000, coast=0)
    summit = Site(rain=600, height=20000, coast=100)
    leeward = Site(rain=0, height=6000, coast=200)
    cells = [windward] * 3 + [summit] * 2 + [leeward] * 3
    biomes = _classify(calibration, cells, _chain(8))
    assert biomes.vegetation[0] == "forest"
    assert biomes.vegetation[3:5] == ("sparse", "sparse")
    assert "forest" not in biomes.vegetation[3:]
    assert (biomes.climate[-1], biomes.vegetation[-1]) == ("arid", "desert")
    assert _pairs(biomes) <= _calibrated(calibration)


def test_cold_climates_keep_forests_at_a_rainfall_that_is_desert_elsewhere() -> None:
    """Forest is no wet-climate privilege: calibrated subarctic forest survives a dry index."""
    calibration = (
        _group("subarctic", "forest", Site(row=SUBARCTIC, rain=60))
        + _group("arid", "desert", Site(row=SUBTROPICS, rain=150))
        + _group("tropical", "forest", Site(row=EQUATOR_ROW, rain=1000))
    )
    cells = [Site(row=SUBARCTIC, rain=60)] * 3 + [Site(row=SUBTROPICS, rain=150)] * 3
    biomes = _classify(calibration, cells, _chain(6))
    assert biomes.climate == ("subarctic",) * 3 + ("arid",) * 3
    assert biomes.vegetation == ("forest",) * 3 + ("desert",) * 3
