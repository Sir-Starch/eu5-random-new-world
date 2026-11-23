"""The land of Africa and Oceania drawn in an image, as America's always could be."""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw import landarea, worldfile
from rnw.app import exchange, library, service
from rnw.app.exchange import ExchangeError
from rnw.app.worldcode import decode, encode, new_code
from rnw.eu5_canvas import NEW_WORLD
from rnw.eu5_nw_export import NewWorldExportError, require_drawings
from rnw.landmask import DRAWN_FILES, LandMask
from rnw.layers import land_key
from rnw.settings import AMERICA, REGIONAL_PRESETS, SettingsError, build_settings, drawn_ids
from tests.fakes import build_game, build_world

if TYPE_CHECKING:
    from rnw.app.discovery import GameInstall


def _drawing(top: int = 24) -> LandMask:
    picture = np.zeros((96, 88), dtype=np.bool_)
    picture[top : top + 40, 22:66] = True
    return LandMask(picture)


def test_the_continents_name_their_picture_files() -> None:
    assert AMERICA == NEW_WORLD
    assert DRAWN_FILES[AMERICA] == "land_mask.png"
    assert set(DRAWN_FILES) == {AMERICA, *REGIONAL_PRESETS}
    assert len(set(DRAWN_FILES.values())) == len(DRAWN_FILES)


def test_a_continent_other_than_america_names_its_drawing_in_its_own_settings() -> None:
    mask = _drawing()
    settings = build_settings(
        "continents",
        {"mask": {"id": 5}, "continents": {"africa": {"mask": {"id": mask.id}}, "oceania": True}},
    )
    africa, oceania = settings.continents.regions
    assert (africa.mask.id, oceania.mask.id) == (mask.id, 0)
    assert drawn_ids(settings) == {AMERICA: 5, "africa": mask.id}
    document = settings.to_json_data()["continents"]
    assert document["africa"]["mask"] == {"id": mask.id}  # pyright: ignore[reportIndexIssue]
    assert "mask" not in document["oceania"]  # pyright: ignore[reportIndexIssue]
    assert build_settings("continents", {"continents": document}).continents == settings.continents
    with pytest.raises(SettingsError, match="Unknown africa drawing settings"):
        _ = build_settings("continents", {"continents": {"africa": {"mask": {"hue": 1}}}})
    assert drawn_ids(build_settings("continents", None)) == {}


def test_a_world_without_regional_drawings_is_the_same_as_before() -> None:
    plain = build_settings("continents", {"continents": {"africa": True, "oceania": True}})
    assert "mask" not in str(plain.to_json_data())
    again = build_settings(
        "continents", {"continents": {"africa": {"mask": {"id": 0}}, "oceania": True}}
    )
    assert land_key(again, 7) == land_key(plain, 7)
    drawn = build_settings(
        "continents", {"continents": {"africa": {"mask": {"id": 9}}, "oceania": True}}
    )
    assert land_key(drawn, 7) != land_key(plain, 7)
    other = build_settings(
        "continents", {"continents": {"africa": {"mask": {"id": 10}}, "oceania": True}}
    )
    assert land_key(other, 7) != land_key(drawn, 7)


def test_a_code_carries_a_regional_drawing_and_an_american_one_stays_compact() -> None:
    changes: dict[str, object] = {
        "continents": {"africa": {"mask": {"id": 12345}}, "oceania": True}
    }
    code = encode(new_code("continents", 3, changes))
    assert decode(code).settings().continents.regions[0].mask.id == 12345
    american = encode(new_code("continents", 3, {"mask": {"id": 12345}}))
    assert len(american) < len(code)
    assert decode(american).settings().mask.id == 12345


def test_the_export_wants_each_continent_to_be_given_the_image_its_settings_name() -> None:
    mask = _drawing()
    settings = build_settings(
        "continents", {"continents": {"africa": {"mask": {"id": mask.id}}, "oceania": True}}
    )
    require_drawings(settings, None, {"africa": mask})
    with pytest.raises(NewWorldExportError, match="africa that was not given"):
        require_drawings(settings, None, {})
    with pytest.raises(NewWorldExportError, match="africa is not the one"):
        require_drawings(settings, None, {"africa": _drawing(30)})
    with pytest.raises(NewWorldExportError, match="oceania is not the one"):
        require_drawings(settings, None, {"africa": mask, "oceania": mask})
    africa_only = build_settings(
        "continents",
        {"continents": {"africa": {"mask": {"id": mask.id}}}},
    )
    with pytest.raises(NewWorldExportError, match="does not make"):
        require_drawings(africa_only, None, {"africa": mask, "oceania": mask})
    with pytest.raises(NewWorldExportError, match="not given"):
        require_drawings(build_settings("continents", {"mask": {"id": mask.id}}), None, {})


def _drawn_africa(data: Path, game: GameInstall) -> tuple[library.World, LandMask]:
    mask = _drawing()
    changes: dict[str, object] = {"continents": {"africa": {"mask": {"id": mask.id}}}}
    code = encode(new_code("continents", 9, changes))
    world = build_world(data, game)
    drawn = replace(world, code=code, id=library.world_id(code, "26043558"))
    old, new = library.folder(data, world), library.folder(data, drawn)
    _ = old.rename(new)
    _ = (new / world.folder).rename(new / drawn.folder)
    library.save(data, drawn)
    _ = (new / DRAWN_FILES["africa"]).write_bytes(mask.png())
    return drawn, mask


def test_the_regional_image_is_kept_in_the_library_and_required_to_make_the_world_again(
    tmp_path: Path,
) -> None:
    game = build_game(tmp_path / "game")
    world, mask = _drawn_africa(tmp_path / "data", game)
    assert library.regional_masks(tmp_path / "data", world)["africa"].id == mask.id
    assert library.drawings(tmp_path / "data", world).keys() == {"africa"}
    assert service.required_land_mask(tmp_path / "data", world) is None
    assert service.required_regional_masks(tmp_path / "data", world)["africa"].id == mask.id
    (library.folder(tmp_path / "data", world) / DRAWN_FILES["africa"]).unlink()
    with pytest.raises(service.LandImageError):
        _ = service.required_regional_masks(tmp_path / "data", world)


def test_the_regional_image_travels_with_the_world_file(tmp_path: Path) -> None:
    game = build_game(tmp_path / "game")
    world, mask = _drawn_africa(tmp_path / "one", game)
    path = exchange.export_world(tmp_path / "one", world, tmp_path / "w.rnworld")
    assert worldfile.read(path).regional_masks == {"africa": mask.png()}
    taken = exchange.import_world(tmp_path / "two", path)
    assert library.regional_masks(tmp_path / "two", taken.world)["africa"].id == mask.id
    wrong = worldfile.write(
        tmp_path / "wrong.rnworld",
        library.document(world),
        None,
        None,
        {"africa": _drawing(30).png()},
    )
    with pytest.raises(ExchangeError, match="not the one"):
        _ = exchange.import_world(tmp_path / "three", wrong)
    # An image for a continent the code does not draw is no more welcome than a wrong one.
    stray = worldfile.write(
        tmp_path / "stray.rnworld", library.document(world), None, None, {"oceania": mask.png()}
    )
    with pytest.raises(ExchangeError, match="not the one"):
        _ = exchange.import_world(tmp_path / "three", stray)


def test_the_area_of_a_continent_in_several_follows_the_seed_and_its_own_shore() -> None:
    settings = build_settings(
        "continents",
        {"continents": {"africa": {"new_world": {"ocean_band_px": 300}}, "oceania": True}},
    )
    game = Path("game")
    first = landarea.area_inputs(game, settings, "africa", 1)
    assert first.plan is not None
    assert [shape[0] for shape in first.plan.shapes] == ["america", "africa", "oceania"]
    assert landarea.area_inputs(game, settings, "africa", 1) == first
    assert landarea.area_inputs(game, settings, "africa", 2) != first
    assert landarea.area_inputs(game, settings, "oceania", 1) != first
    # What does not move the area does not name it: the land's share, the peoples.
    plain = build_settings(
        "continents",
        {
            "new_world": {"land_permille": 400},
            "natives": {"population_permille": 800},
            "continents": {
                "africa": {"new_world": {"ocean_band_px": 300, "land_permille": 150}},
                "oceania": True,
            },
        },
    )
    assert landarea.area_inputs(game, plain, "africa", 1) == first
    narrow = build_settings(
        "continents",
        {"continents": {"africa": {"new_world": {"ocean_band_px": 400}}, "oceania": True}},
    )
    assert landarea.area_inputs(game, narrow, "africa", 1) != first
    asia = build_settings(
        "continents",
        {
            "continents": {
                "africa": {"new_world": {"ocean_band_px": 300}, "require_asia_connection": True},
                "oceania": True,
            }
        },
    )
    assert landarea.area_inputs(game, asia, "africa", 1) != first
    banded = build_settings(
        "continents",
        {"continents": {"africa": {"new_world": {"ocean_band_px": 300}}, "oceania": True}},
    )
    iberia = build_settings(
        "continents",
        {
            "continents": {
                "africa": {"new_world": {"ocean_band_px": 300}, "iberia_connection": "required"},
                "oceania": True,
            }
        },
    )
    assert landarea.area_inputs(game, iberia, "africa", 1) != landarea.area_inputs(
        game, banded, "africa", 1
    )
    # America alone has one area for every seed.
    alone = build_settings("continents", None)
    assert landarea.area_inputs(game, alone, "america", 1) == landarea.area_inputs(
        game, alone, "america", 2
    )
    assert landarea.area_inputs(game, alone, "america", 1).plan is None
