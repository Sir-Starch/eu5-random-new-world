"""The barrier survives cell construction; polar land is also possible in ordinary worlds."""

# pyright: reportAny=false
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from rnw import __version__, wall
from rnw.app.worldcode import WorldCode, decode, encode
from rnw.model import CellClass
from rnw.newworld import LAND_KINDS, generate_new_world, land_stage
from rnw.settings import build_settings
from rnw.topology import label_components
from tests.test_newworld import SMALL


@pytest.mark.parametrize("seed", [7, 42, 1000])
@pytest.mark.parametrize(
    ("position", "width", "coast"), [(0, 40, 0), (700, 70, 600), (1000, 140, 1000)]
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
    centre, _ = wall.geometry(domain, settings)
    land = np.array([kind in LAND_KINDS for kind in world.classes])[world.labels]
    assert land[:, centre].all()
    assert np.all(world.labels >= 0)
    assert all(
        world.classes[i] is CellClass.WASTELAND for i in np.unique(world.labels[[0, -1], centre])
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
        centre, _ = wall.geometry(domain, settings)
        assert continuous[:, centre].all()
        assert not (land & ~continuous).any()
