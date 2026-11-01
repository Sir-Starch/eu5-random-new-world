"""The barrier survives cell construction; polar land is also possible in ordinary worlds."""

# pyright: reportAny=false
from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw import __version__, newworld, wall
from rnw.app.worldcode import WorldCode, decode, encode
from rnw.model import CellClass
from rnw.newworld import LAND_KINDS, generate_new_world, land_stage
from rnw.settings import NewWorldSettings, build_settings
from rnw.topology import label_components
from tests.test_newworld import SMALL

if TYPE_CHECKING:
    from numpy.typing import NDArray


@pytest.mark.parametrize("seed", [7, 42, 1000])
@pytest.mark.parametrize(
    ("position", "width", "coast"),
    [(0, 40, 0), (700, 140, 600), (1000, 140, 1000), (500, 440, 300)],
)
def test_wall_has_no_water_passage_and_keeps_polar_end_locations_impassable(
    seed: int, position: int, width: int, coast: int
) -> None:
    settings = replace(
        SMALL,
        wall_allow_gaps=0,
        landform=1,
        wall_position_permille=position,
        wall_width_permille=width,
        wall_coast_permille=coast,
    )
    domain = np.ones((320, 480), dtype=bool)
    world = generate_new_world(domain, seed=seed, settings=settings)
    middle = wall.spine(domain, seed, settings)
    land = np.array([kind in LAND_KINDS for kind in world.classes])[world.labels]
    assert land[np.arange(len(middle)), middle].all()
    assert np.all(world.labels >= 0)
    assert all(
        world.classes[i] is CellClass.WASTELAND
        for i in np.unique(world.labels[[0, -1], middle[[0, -1]]])
    )
    parts = label_components((~land).astype(np.int32))
    west = set(parts[:, 0][~land[:, 0]].tolist())
    east = set(parts[:, -1][~land[:, -1]].tolist())
    assert west.isdisjoint(east)


def test_wall_rejects_a_canvas_without_a_polar_corridor() -> None:
    domain = np.ones((100, 240), dtype=bool)
    domain[0] = False
    with pytest.raises(ValueError, match="continuous north-south"):
        _ = land_stage(domain, 42, replace(SMALL, landform=1))


def test_ordinary_worlds_can_reach_both_poles_without_forcing_land_there() -> None:
    domain = np.ones((240, 480), dtype=bool)
    masks = [land_stage(domain, seed, SMALL)[0] for seed in range(8)]
    for row in (0, -1):
        assert any(mask[row].any() for mask in masks)
        assert any((~mask[row]).any() for mask in masks)
    assert len({mask[[0, -1]].tobytes() for mask in masks}) > 1


def test_wall_code_preserves_all_shape_controls() -> None:
    settings = build_settings(
        "wall",
        {
            "new_world": {
                "wall_width_permille": 110,
                "wall_position_permille": 300,
                "wall_coast_permille": 900,
                "wall_ridge_permille": 600,
            }
        },
    )
    code = WorldCode(
        "wall",
        42,
        __version__,
        {
            "new_world": {
                "wall_width_permille": 110,
                "wall_position_permille": 300,
                "wall_coast_permille": 900,
                "wall_ridge_permille": 600,
            }
        },
    )
    assert decode(encode(code)).settings() == settings


def test_wall_coasts_do_not_depend_on_strip_height(monkeypatch: pytest.MonkeyPatch) -> None:
    domain = np.ones((160, 320), dtype=bool)
    settings = replace(SMALL, landform=1)
    expected = wall.coast(domain, 42, settings)
    monkeypatch.setattr(wall, "STRIP_ROWS", 7)
    assert np.array_equal(wall.coast(domain, 42, settings), expected)


def test_wall_relief_control_raises_the_spine_without_changing_the_shores() -> None:
    domain = np.ones((160, 320), dtype=bool)
    settings = replace(SMALL, landform=1)
    land = wall.coast(domain, 42, settings)
    flat = np.zeros(domain.shape, dtype=np.int32)
    raised = flat.copy()
    wall.add_relief(flat, land, domain, 42, replace(settings, wall_ridge_permille=0))
    wall.add_relief(raised, land, domain, 42, settings)
    assert not flat.any()
    assert raised.max() > 10000
    assert not raised[~land].any()


def test_an_isolated_polar_basin_is_a_lake_with_no_invented_ocean_outlet() -> None:
    from rnw.newworld import _classify  # noqa: PLC0415  # pyright: ignore[reportPrivateUsage]

    domain = np.ones((80, 100), dtype=bool)
    land = domain.copy()
    land[:10, 40:50] = False
    shore = np.zeros(domain.shape, dtype=bool)
    shore[:, [0, -1]] = True
    _, ocean, lakes = _classify(domain, land, shore, SMALL)
    assert not ocean.any()
    assert lakes[:10, 40:50].all()


def test_density_field_forms_islands_and_passages_with_no_prescribed_count() -> None:
    domain = np.ones((640, 480), dtype=bool)
    settings = replace(SMALL, landform=1, land_permille=150, wall_coast_permille=1000)
    shapes = [wall.coast(domain, seed, settings) for seed in range(8)]
    assert any((~land.any(axis=1)).any() for land in shapes)
    assert len({land.tobytes() for land in shapes}) == len(shapes)
    for seed, land in enumerate(shapes):
        more = wall.coast(domain, seed, replace(settings, land_permille=450))
        assert not (land & ~more).any()
        continuous = wall.coast(domain, seed, replace(settings, wall_allow_gaps=0))
        middle = wall.spine(domain, seed, settings)
        assert continuous[np.arange(len(middle)), middle].all()
        assert not (land & ~continuous).any()


def test_seed_can_leave_a_broad_side_region_entirely_ocean() -> None:
    """A new seed changes where continents occur, beyond changing their local shores."""
    domain = np.ones((640, 960), dtype=bool)
    settings = replace(
        SMALL, landform=1, land_permille=187, wall_width_permille=140, feature_px=100
    )
    course = wall.route(domain, settings)
    centre = int(course.centre[0])
    gap = course.half + max(2 * settings.coast_margin_px, settings.sea_zone_px)
    regions = [(slice(top, top + 192), slice(60, centre - gap - 30)) for top in (64, 384)]
    counts: list[list[int]] = [[], []]
    for seed in (0, 1, 3, 5, 6):
        land, ocean, lakes, _ = land_stage(domain, seed, settings)
        assert np.array_equal(land | ocean | lakes, domain)
        for region, found in zip(regions, counts, strict=True):
            found.append(int(np.count_nonzero(land[region])))
    for region, found in zip(regions, counts, strict=True):
        # Bent coasts can trail a cape or two into an otherwise empty region.
        assert min(found) < domain[region].size // 100
        assert max(found) > domain[region].size // 4


def test_wall_secondary_land_does_not_depend_on_strip_height(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    domain = np.ones((320, 480), dtype=bool)
    domain[80:160, :100] = False
    settings = replace(SMALL, landform=1, land_permille=250)
    expected = land_stage(domain, 42, settings)
    monkeypatch.setattr(newworld, "STRIP_ROWS", 16)
    actual = land_stage(domain, 42, settings)
    assert all(np.array_equal(a, b) for a, b in zip(expected, actual, strict=True))
    assert not actual[0][~domain].any()


@pytest.mark.parametrize("seed", range(6))
def test_forced_core_is_a_broad_bent_land_route_never_a_straight_strip(seed: int) -> None:
    """The worst case for the core: little land and a very ragged coast (owner report)."""
    domain = np.ones((960, 640), dtype=bool)
    settings = replace(
        SMALL,
        landform=1,
        land_permille=100,
        wall_width_permille=140,
        wall_coast_permille=1000,
        wall_allow_gaps=0,
    )
    land = wall.coast(domain, seed, settings)
    course = wall.route(domain, settings)
    centre, half = int(course.centre[0]), course.half
    middle = wall.spine(domain, seed, settings)
    # One land component joins the first row to the last, so no ship crosses or rounds it.
    parts = label_components(land.astype(np.int32))
    assert len({int(parts[0, middle[0]]), int(parts[-1, middle[-1]])}) == 1
    # It bends: the same column is not the core's column in every row.
    assert len(np.unique(middle)) > half // 4
    assert np.abs(middle - centre).max() <= 3 * half // 10 + 1
    # It is broad everywhere, not a hairline.
    widths = land[:, centre - half : centre + half + 1].sum(axis=1)
    assert widths.min() >= half // 3
    # Its width swells and narrows too, so neither edge of the core is ruler-straight.
    reach = wall.core(len(domain), seed, course.centre, half, settings)[1]
    assert reach.max() - reach.min() > half // 10


def test_low_land_share_thins_the_side_land_and_never_the_wall() -> None:
    domain = np.ones((640, 480), dtype=bool)
    base = replace(SMALL, landform=1, land_permille=250, wall_coast_permille=1000)
    for seed in range(4):
        assert np.array_equal(
            wall.coast(domain, seed, base),
            wall.coast(domain, seed, replace(base, land_permille=120)),
        )


def test_a_wider_wall_takes_its_land_out_of_the_land_share_and_leaves_the_rest_beside_it() -> None:
    """The land share is one budget: the Wall is counted first and the continents get the rest."""
    domain = np.ones((640, 960), dtype=bool)
    settings = replace(SMALL, landform=1, land_permille=250)
    interior = int(np.count_nonzero(domain & ~newworld._off_limits(domain, settings)))  # pyright: ignore[reportPrivateUsage]
    budget = interior * settings.land_permille // 1000
    sides: list[int] = []
    for width in (40, 100, 200, 300):
        wide = replace(settings, wall_width_permille=width)
        land = land_stage(domain, 42, wide)[0]
        barrier = wall.coast(domain, 42, wide)
        assert (land & barrier).sum() == barrier.sum()
        # While the Wall fits the share, the world keeps the land amount that was asked for.
        assert abs(int(land.sum()) - budget) < budget // 20
        sides.append(int((land & ~barrier).sum()))
    assert sides == sorted(sides, reverse=True)
    assert sides[0] > 2 * sides[-1]


@pytest.mark.parametrize("width", [300, 440])
def test_the_widest_wall_takes_nearly_all_the_land_and_is_never_thinned(width: int) -> None:
    """A Wall that needs the whole share keeps its land; the continents keep only a sliver."""
    domain = np.ones((640, 960), dtype=bool)
    settings = replace(SMALL, landform=1, land_permille=150, wall_width_permille=width)
    land = land_stage(domain, 42, settings)[0]
    barrier = wall.coast(domain, 42, settings)
    assert (land & barrier).sum() == barrier.sum()
    beside = int((land & ~barrier).sum())
    assert 0 < beside < int(land.sum()) // 20
    assert not (land & ~domain).any()


@pytest.mark.parametrize("seed", range(6))
def test_no_wall_coast_is_cut_off_along_the_envelope_edge(seed: int) -> None:
    domain = np.ones((960, 640), dtype=bool)
    settings = replace(SMALL, landform=1, land_permille=700, wall_coast_permille=1000)
    land = wall.coast(domain, seed, settings)
    course = wall.route(domain, settings)
    centre, half = int(course.centre[0]), course.half
    assert land.any()
    assert not land[:, centre - half].any()
    assert not land[:, centre + half].any()


def _islands(*boxes: tuple[int, int, int, int]) -> NDArray[np.bool_]:
    """A canvas of 2048 rows and 1400 columns with protected boxes (top, bottom, left, right)."""
    domain = np.ones((2048, 1400), dtype=bool)
    for top, bottom, left, right in boxes:
        domain[top:bottom, left:right] = False
    return domain


def _wall_settings(position: int, width: int = 70) -> NewWorldSettings:
    return replace(SMALL, landform=1, wall_position_permille=position, wall_width_permille=width)


def _assert_clear(
    course: wall.Route, domain: NDArray[np.bool_], settings: NewWorldSettings
) -> None:
    """The envelope and its coast margin hold no protected pixel in any row."""
    pad = course.half + settings.coast_margin_px
    for row, column in enumerate(course.centre.tolist()):
        assert domain[row, column - pad : column + pad + 1].all()


def test_wall_route_is_a_straight_line_on_an_open_canvas() -> None:
    domain = np.ones((640, 960), dtype=bool)
    for position in (0, 300, 700, 1000):
        settings = _wall_settings(position)
        course = wall.route(domain, settings)
        pad = course.half + settings.coast_margin_px
        assert np.unique(course.centre).tolist() == [pad + (960 - 2 * pad - 1) * position // 1000]


@pytest.mark.parametrize("position", [300, 500, 700])
def test_wall_goes_around_a_protected_island_in_its_way_and_returns(position: int) -> None:
    domain = _islands((900, 1020, 600, 720))
    settings = _wall_settings(position)
    course = wall.route(domain, settings)
    straight = wall.route(np.ones_like(domain), settings).centre[0]
    _assert_clear(course, domain, settings)
    if abs(int(straight) - 660) < 200:
        # The island is in its way: it moves aside and is straight again far from the island.
        assert int(np.abs(course.centre - straight).max()) > 100
        assert course.centre[0] == straight
        assert course.centre[-1] == straight
    else:
        assert np.array_equal(course.centre, np.full(len(domain), straight))
    # Gentle: never steeper than one pixel a row.
    assert int(np.abs(np.diff(course.centre)).max()) <= 1


def test_wall_passes_a_group_of_islands_on_one_side() -> None:
    """Two islands closer together than the envelope are one obstacle: no threading between."""
    domain = _islands((900, 1000, 600, 700), (900, 1000, 760, 860))
    settings = _wall_settings(500)
    course = wall.route(domain, settings)
    _assert_clear(course, domain, settings)
    rows = slice(900, 1000)
    assert not ((course.centre[rows] > 700) & (course.centre[rows] < 760)).any()
    assert (course.centre[rows] < 600).all() or (course.centre[rows] > 860).all()


def test_wall_position_spans_the_canvas_not_only_the_corridor_free_of_islands() -> None:
    """An island once limited the position to the columns east of it."""
    domain = _islands((900, 1020, 100, 220))
    west = wall.route(domain, _wall_settings(0))
    east = wall.route(domain, _wall_settings(1000))
    pad = west.half + SMALL.coast_margin_px
    assert west.centre[0] == pad
    assert east.centre[0] == 1400 - pad - 1
    _assert_clear(west, domain, _wall_settings(0))
    assert west.centre.min() == pad


def test_wall_without_a_way_through_is_rejected() -> None:
    narrow = _islands((1000, 1001, 0, 700), (1000, 1001, 760, 1400))
    with pytest.raises(ValueError, match="continuous north-south"):
        _ = wall.route(narrow, _wall_settings(500))


def test_wall_land_stays_off_protected_pixels_and_keeps_its_core_around_islands() -> None:
    domain = _islands((900, 1020, 600, 720))
    settings = replace(_wall_settings(500), wall_allow_gaps=0)
    land = wall.coast(domain, 42, settings)
    middle = wall.spine(domain, 42, settings)
    assert not (land & ~domain).any()
    assert land[np.arange(len(middle)), middle].all()
    parts = label_components(land.astype(np.int32))
    assert len({int(parts[0, middle[0]]), int(parts[-1, middle[-1]])}) == 1


def test_wall_land_around_islands_does_not_depend_on_strip_height(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    domain = _islands((900, 1020, 600, 720))
    settings = _wall_settings(500)
    expected = wall.coast(domain, 7, settings)
    monkeypatch.setattr(wall, "STRIP_ROWS", 32)
    assert np.array_equal(wall.coast(domain, 7, settings), expected)
