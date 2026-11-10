"""The land editor as the window asks for it: the studio's answers, the controller's area and the
bridge's methods, on a synthetic area."""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import base64
import io
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest
from PIL import Image

from rnw import landeditor
from rnw.app import candidates, service
from rnw.app.discovery import Environment, GameInstall, Profile
from rnw.app.worldcode import decode
from rnw.gui import studio
from rnw.gui.bridge import Bridge, BridgeError
from rnw.gui.controller import EDITOR, Controller, Phase, Task
from rnw.landarea import EDITOR_STEP, TEMPLATE_STEP, LandArea
from rnw.landmask import HIGHLANDS, LAKE, LAND, MOUNTAINS, SEA
from rnw.png import COLOR_GRAY, encode_png
from rnw.settings import PRESETS

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

    from rnw.app.service import Exporter

SETTINGS = PRESETS["continents"].new_world


def _full_area() -> LandArea:
    """A canvas of 1920 by 2400 pixels: a wide area with the Americas and an island group in it."""
    area = np.zeros((480, 600), dtype=np.bool_)
    area[20:-20, 20:-20] = True
    americas = np.zeros_like(area)
    americas[180:380, 60:160] = True
    islands = np.zeros_like(area)
    islands[100:112, 300:312] = True
    return LandArea((480 * TEMPLATE_STEP, 600 * TEMPLATE_STEP), area, americas, islands)


def _sheet() -> LandArea:
    return _full_area().at(EDITOR_STEP)


def _decoded(url: str) -> NDArray[np.uint8]:
    return studio.kinds_of(url, _sheet())


def _grey(path: Path, shape: tuple[int, int]) -> Path:
    picture = np.zeros(shape, dtype=np.uint8)
    picture[shape[0] // 4 : 3 * shape[0] // 4, shape[1] // 4 : 3 * shape[1] // 4] = 255
    _ = path.write_bytes(encode_png(picture, color_type=COLOR_GRAY, compression="zlib"))
    return path


def test_a_picture_goes_to_the_window_and_comes_back_the_same() -> None:
    area = _sheet()
    kinds = np.zeros(area.picture_shape, dtype=np.uint8)
    kinds[40:80, 40:90] = LAND
    kinds[50:55, 50:55] = MOUNTAINS
    kinds[60:65, 60:70] = HIGHLANDS
    kinds[70:75, 70:80] = LAKE
    url = studio.kinds_url(kinds)
    assert url.startswith(studio.PNG_URL)
    assert np.array_equal(studio.kinds_of(url, area), kinds)
    assert studio.png_of(url).startswith(studio.PNG_SIGNATURE)


def test_what_is_not_the_sheet_or_not_a_picture_is_refused() -> None:
    area = _sheet()
    small = studio.kinds_url(np.zeros((100, 100), dtype=np.uint8))
    with pytest.raises(studio.StudioError, match="sheet"):
        _ = studio.kinds_of(small, area)
    with pytest.raises(studio.StudioError, match="PNG"):
        _ = studio.png_of("data:text/plain;base64,AAAA")
    with pytest.raises(studio.StudioError, match="PNG"):
        _ = studio.png_of(studio.PNG_URL + "!!")
    with pytest.raises(studio.StudioError, match="PNG"):
        _ = studio.png_of(studio.PNG_URL + base64.b64encode(b"not a picture").decode())


def test_the_editor_opens_on_the_sheet_with_the_picture_chosen_now() -> None:
    area = _sheet()
    bare = studio.opening(area, None, [], SETTINGS)
    assert (bare["width"], bare["height"], bare["step"]) == (300, 240, EDITOR_STEP)
    assert bare["image"] == ""
    assert bare["presets"] == list(landeditor.PRESETS)
    classes = cast("dict[str, int]", bare["classes"])
    backdrop = np.asarray(Image.open(io.BytesIO(studio.png_of(cast("str", bare["backdrop"])))))
    assert backdrop.shape == area.picture_shape
    assert backdrop[0, 0] == classes["outside"]
    assert backdrop[10, 10] == classes["area"]
    assert backdrop[100, 100] == classes["americas"] or backdrop[100, 100] == classes["area"]
    assert bare["sketches"] == []
    margin = np.asarray(Image.open(io.BytesIO(studio.png_of(cast("str", bare["margin"])))))
    assert margin.shape == area.picture_shape
    assert margin[12, 100] == 255  # in the area, within the coast margin of its edge
    assert margin[120, 150] == 0
    assert margin[0, 0] == 0  # outside the area is not margin
    from rnw.landmask import from_kinds  # noqa: PLC0415 - one test needs it

    kinds = landeditor.make_preset(landeditor.SUPERCONTINENT, area, 1)
    drawn = studio.opening(area, from_kinds(kinds), [], SETTINGS)
    assert drawn["fit"] == "exact"
    assert np.array_equal(_decoded(cast("str", drawn["image"])), kinds)


def test_sketched_continents_that_fit_the_sheet_are_offered_and_become_land() -> None:
    area = _sheet()
    picture = np.zeros((*area.picture_shape, 3), dtype=np.uint8)
    picture[:] = candidates.SEA
    picture[50:100, 60:120] = candidates.LAND
    picture[70:72, 70:72] = candidates.LAKE
    wrong = np.zeros((4, 4, 3), dtype=np.uint8)
    found = [candidates.Candidate(1, picture, 100), candidates.Candidate(2, wrong, 100)]
    assert studio.opening(area, None, found, SETTINGS)["sketches"] == [0]
    kinds = _decoded(studio.sketch(area, found, 0))
    assert kinds[60, 80] == LAND
    assert kinds[70, 70] == LAKE
    assert kinds[0, 0] == SEA
    with pytest.raises(studio.StudioError, match="sheet"):
        _ = studio.sketch(area, found, 1)
    with pytest.raises(studio.StudioError, match="no such"):
        _ = studio.sketch(area, found, 2)


def test_presets_are_made_to_the_seed_and_the_coast_margin() -> None:
    area = _sheet()
    margin = landeditor.margin_for(SETTINGS)
    assert margin == 6
    one = studio.preset(area, landeditor.ARCHIPELAGO, 5, SETTINGS)
    assert one == studio.preset(area, landeditor.ARCHIPELAGO, 5, SETTINGS)
    assert one != studio.preset(area, landeditor.ARCHIPELAGO, 6, SETTINGS)
    found = studio.report(area, one, SETTINGS)
    assert found["refusal"] == landeditor.NOTHING
    assert found["kept"] == 100
    with pytest.raises(studio.StudioError, match="no preset"):
        _ = studio.preset(area, "pangaea", 1, SETTINGS)
    americas = _decoded(studio.real_americas(area))
    assert np.array_equal(americas == LAND, area.americas & area.area)


def test_decoration_is_asked_for_by_name() -> None:
    area = _sheet()
    plain = studio.preset(area, landeditor.SUPERCONTINENT, 3, SETTINGS)
    done = _decoded(studio.decorate(area, plain, 4, ["mountains", "lakes"]))
    assert (done == MOUNTAINS).any()
    assert not (done == HIGHLANDS).any()
    nothing = _decoded(studio.decorate(area, plain, 4, []))
    assert np.array_equal(nothing, _decoded(plain))
    with pytest.raises(studio.StudioError, match="volcanoes"):
        _ = studio.decorate(area, plain, 4, ["volcanoes"])


def test_the_report_gives_the_numbers_the_window_turns_into_sentences() -> None:
    area = _sheet()
    kinds = np.zeros(area.picture_shape, dtype=np.uint8)
    kinds[60:180, 70:200] = LAND
    kinds[100:110, 60:90] = LAKE
    found = studio.report(area, studio.kinds_url(kinds), SETTINGS)
    assert found["refusal"] == landeditor.OPEN_LAKE
    (place,) = cast("list[list[int]]", found["open_lakes"])
    assert 60 <= place[0] < 90
    assert 100 <= place[1] < 110
    assert found["lakes"] == 300
    assert found["land"] == (120 * 130 - 200) * 1000 // kinds.size
    assert set(found) >= {
        "mountains",
        "highlands",
        "lowlands",
        "outside",
        "kept",
        "specks",
        "islands",
    }


def test_a_file_is_laid_on_the_sheet(tmp_path: Path) -> None:
    area = _sheet()
    same = studio.imported(area, _grey(tmp_path / "same.png", area.picture_shape))
    assert same["fit"] == "exact"
    other = studio.imported(area, _grey(tmp_path / "other.png", (480, 600)))
    assert other["fit"] == "stretched"
    square = studio.imported(area, _grey(tmp_path / "square.png", (300, 300)))
    assert square["fit"] == "centered"
    assert _decoded(square["image"]).shape == area.picture_shape
    with pytest.raises(studio.StudioError):
        _ = studio.imported(area, tmp_path / "missing.png")
    junk = tmp_path / "junk.png"
    _ = junk.write_bytes(b"junk")
    with pytest.raises(studio.StudioError, match="cannot be read"):
        _ = studio.imported(area, junk)


# -- the controller and the bridge ----------------------------------------------------------------


def _bridge(tmp_path: Path, export: Exporter) -> Bridge:
    def generator(request: service.Request, progress: object = None) -> service.Result:
        return service.generate(request, cast("None", progress), export)

    environment = Environment(system="linux", home=tmp_path / "home", variables={})
    controller = Controller(data=tmp_path / "data", environment=environment, generator=generator)
    (tmp_path / "game" / "game" / "in_game" / "map_data").mkdir(parents=True)
    controller.game = GameInstall(tmp_path / "game", None, "26043558")
    (tmp_path / "profile" / "mod").mkdir(parents=True)
    controller.profile = Profile(tmp_path / "profile", "linux", has_mods=True)
    return Bridge(controller)


@pytest.fixture
def cut(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """The game's area stood in for by the synthetic one; counts how often it is cut."""
    count: list[int] = []

    def land_area(*_arguments: object, **_keywords: object) -> LandArea:
        count.append(1)
        return _full_area()

    monkeypatch.setattr(service, "land_area", land_area)
    return count


def test_the_area_is_cut_as_a_task_once_and_again_for_another_game(
    tmp_path: Path, fake_export: Exporter, cut: list[int]
) -> None:
    bridge = _bridge(tmp_path, fake_export)
    controller = bridge.controller
    assert controller.land_sheet() is None
    assert bridge.state()["new"]["editor_ready"] is False  # pyright: ignore[reportIndexIssue]
    with pytest.raises(BridgeError, match="not ready"):
        _ = bridge.call("land_editor", {})
    assert bridge.call("prepare_land_area", {}) is None
    assert (controller.task, controller.task_target) == (Task.TEMPLATE, EDITOR)
    controller.wait(10)
    assert controller.phase is Phase.FINISHED
    assert len(cut) == 1
    sheet = controller.land_sheet()
    assert sheet is not None
    assert sheet.picture_shape == (240, 300)
    assert bridge.state()["new"]["editor_ready"] is True  # pyright: ignore[reportIndexIssue]
    assert bridge.call("prepare_land_area", {}) is None
    assert len(cut) == 1
    controller.set_preset("islands")
    assert controller.land_sheet() is not None  # every world type fills the same area
    (tmp_path / "other" / "game").mkdir(parents=True)
    controller.game = GameInstall(tmp_path / "other", None, "26043558")
    assert controller.land_sheet() is None
    assert bridge.call("prepare_land_area", {}) is None
    controller.wait(10)
    assert len(cut) == 2
    assert controller.land_sheet() is not None


def test_the_area_cannot_be_cut_without_a_game_or_while_busy(
    tmp_path: Path, fake_export: Exporter, cut: list[int]
) -> None:
    bridge = _bridge(tmp_path, fake_export)
    controller = bridge.controller
    controller.task, controller.phase = Task.GENERATE, Phase.RUNNING
    assert bridge.call("prepare_land_area", {}) is not None
    controller.phase = Phase.IDLE
    controller.game = None
    assert bridge.call("prepare_land_area", {}) is not None
    assert not cut


def test_the_editor_draws_a_world_and_its_picture_becomes_the_land(
    tmp_path: Path, fake_export: Exporter, cut: list[int]
) -> None:
    _ = cut
    bridge = _bridge(tmp_path, fake_export)
    controller = bridge.controller
    assert bridge.call("prepare_land_area", {}) is None
    controller.wait(10)
    opened = cast("dict[str, object]", bridge.call("land_editor", {}))
    assert opened["image"] == ""
    image = cast("str", bridge.call("land_preset", {"preset": "two_continents", "seed": 9}))
    image = cast(
        "str", bridge.call("land_decorate", {"image": image, "seed": 2, "parts": ["mountains"]})
    )
    report = cast("dict[str, object]", bridge.call("land_check", {"image": image}))
    assert report["refusal"] == ""
    assert bridge.call("use_land_picture", {"image": image}) is None
    assert controller.land_mask is not None
    assert controller.land_mask.kinds is not None
    assert decode(controller.code).settings().mask.id == controller.land_mask.id
    again = cast("dict[str, object]", bridge.call("land_editor", {}))
    assert again["fit"] == "exact"
    assert np.array_equal(_decoded(cast("str", again["image"])), controller.land_mask.kinds)
    empty = studio.kinds_url(np.zeros((240, 300), dtype=np.uint8))
    assert "land" in (cast("str", bridge.call("use_land_picture", {"image": empty})) or "").lower()
    with pytest.raises(BridgeError, match="PNG"):
        _ = bridge.call("use_land_picture", {"image": "nonsense"})
    with pytest.raises(BridgeError, match="no preset"):
        _ = bridge.call("land_preset", {"preset": "pangaea", "seed": 1})
    assert bridge.call("land_americas", {}) is not None


def test_known_lands_are_offered_and_laid_on_the_sheet() -> None:
    area = _sheet()
    opened = studio.opening(area, None, [], SETTINGS)
    lands = cast("list[str]", opened["lands"])
    assert "tamriel" in lands
    image = studio.known(area, "tamriel", SETTINGS)
    report = studio.report(area, image, SETTINGS)
    assert report["refusal"] == landeditor.NOTHING
    assert report["kept"] == 100
    with pytest.raises(studio.StudioError, match="no known land"):
        _ = studio.known(area, "pangaea", SETTINGS)


def test_the_bridge_lays_a_known_land(
    tmp_path: Path, fake_export: Exporter, cut: list[int]
) -> None:
    _ = cut
    bridge = _bridge(tmp_path, fake_export)
    assert bridge.call("prepare_land_area", {}) is None
    bridge.controller.wait(10)
    image = cast("str", bridge.call("land_known", {"land": "westeros"}))
    assert np.count_nonzero(_decoded(image) == LAND) > 0
    with pytest.raises(BridgeError, match="no known land"):
        _ = bridge.call("land_known", {"land": "pangaea"})
