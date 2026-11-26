"""The land editor of the classic window, driven offscreen: it cuts the area, draws with the
pointer, asks the generator what it makes of the drawing and gives the land to the world."""

# Qt stubs type signals and widgets loosely.
# pyright: reportAny=false

from __future__ import annotations

import time
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from rnw.app import service
from rnw.app.discovery import Environment, GameInstall, Profile
from rnw.gui.controller import Controller, Phase
from rnw.gui.land_pictures import Drafts, say_report, thumbnail
from rnw.gui.text import text
from rnw.landmask import LAKE, LAND, MOUNTAINS, SEA
from tests.test_studio import _full_area  # pyright: ignore[reportPrivateUsage]

try:  # the window needs PySide6 and the system's graphics libraries
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QMessageBox

    from rnw.gui import land_editor
    from rnw.gui.land_editor import LandEditorDialog, resized
    from rnw.gui.window import MainWindow
except ImportError:
    pytest.skip("PySide6 is not available", allow_module_level=True)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from numpy.typing import NDArray

    from rnw.app.service import Exporter
    from rnw.landarea import LandArea


@pytest.fixture(scope="module")
def application() -> QApplication:
    """One QApplication for the module (Qt allows a single one per process)."""
    existing = QApplication.instance()
    return existing if isinstance(existing, QApplication) else QApplication([])


def pump(condition: Callable[[], bool], timeout: float = 15.0) -> None:
    """Run the event loop until ``condition`` holds."""
    deadline = time.monotonic() + timeout
    app = QApplication.instance()
    while not condition():
        assert time.monotonic() < deadline, "the window did not reach the state in time"
        if app is not None:
            app.processEvents()
        time.sleep(0.01)


def _controller(tmp_path: Path, export: Exporter) -> Controller:
    def generator(request: service.Request, progress: object = None) -> service.Result:
        return service.generate(request, cast("None", progress), export)

    environment = Environment(system="linux", home=tmp_path / "home", variables={})
    controller = Controller(data=tmp_path / "data", environment=environment, generator=generator)
    (tmp_path / "game" / "game" / "in_game" / "map_data").mkdir(parents=True)
    controller.game = GameInstall(tmp_path / "game", None, "26043558")
    (tmp_path / "profile" / "mod").mkdir(parents=True)
    controller.profile = Profile(tmp_path / "profile", "linux", has_mods=True)
    return controller


@pytest.fixture
def cut(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """The game's area stood in for by the synthetic one; counts how often it is cut."""
    count: list[int] = []

    def land_area(*_arguments: object, **_keywords: object) -> LandArea:
        count.append(1)
        return _full_area()

    monkeypatch.setattr(service, "land_area", land_area)
    return count


def _opened(controller: Controller, continent: str = "america") -> LandEditorDialog:
    dialog = LandEditorDialog(None, controller, continent)
    dialog.resize(1200, 760)
    dialog.show()
    pump(lambda: dialog.stage in {"ready", "failed"})
    return dialog


def _at(dialog: LandEditorDialog, x: int, y: int) -> QPoint:
    """The point of the canvas over the middle of a pixel of the sheet."""
    canvas = dialog.canvas
    return QPoint(
        round(canvas.offset.x() + (x + 0.5) * canvas.scale),
        round(canvas.offset.y() + (y + 0.5) * canvas.scale),
    )


def _drag(dialog: LandEditorDialog, start: tuple[int, int], end: tuple[int, int]) -> None:
    canvas = dialog.canvas
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=_at(dialog, *start))
    QTest.mouseMove(canvas, _at(dialog, *end))
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=_at(dialog, *end))


def _sheet(dialog: LandEditorDialog) -> NDArray[np.uint8]:
    assert dialog.sheet is not None
    return dialog.sheet.kinds


@pytest.mark.usefixtures("application")
def test_the_editor_cuts_the_area_and_opens_an_empty_sheet(
    tmp_path: Path, fake_export: Exporter, cut: list[int]
) -> None:
    controller = _controller(tmp_path, fake_export)
    dialog = _opened(controller)
    try:
        assert dialog.stage == "ready"
        assert len(cut) == 1
        assert dialog.sheet is not None
        assert (dialog.sheet.width, dialog.sheet.height) == (300, 240)
        assert dialog.sheet.empty
        assert not dialog.use_button.isEnabled()  # no land yet
        pump(lambda: dialog.report is not None)
        assert dialog.report is not None
        assert dialog.report["refusal"] == "share"
        assert "share" in dialog.lines[0].key
        assert dialog.canvas.scale > 0
        assert dialog.size_label.text() == "300 × 240"
    finally:
        dialog.reject()


@pytest.mark.usefixtures("application")
def test_the_pointer_draws_with_the_tools_and_the_keys_choose_them(
    tmp_path: Path, fake_export: Exporter, cut: list[int]
) -> None:
    _ = cut
    dialog = _opened(_controller(tmp_path, fake_export))
    try:
        _drag(dialog, (60, 60), (200, 60))
        kinds = _sheet(dialog)
        assert (kinds[60, 60:201] == LAND).all()
        assert dialog.undo_button.isEnabled()
        # a key chooses a kind; a lake is painted over the land, not mountains over the sea
        QTest.keyClick(dialog, Qt.Key.Key_6)
        assert dialog.canvas.kind == LAKE
        _drag(dialog, (100, 60), (120, 60))
        assert (_sheet(dialog)[60, 100:121] == LAKE).all()
        QTest.keyClick(dialog, Qt.Key.Key_3)
        _drag(dialog, (100, 100), (120, 100))
        assert (_sheet(dialog)[100, 100:121] == SEA).all()
        _drag(dialog, (62, 60), (64, 60))
        assert _sheet(dialog)[60, 63] == MOUNTAINS
        # the tools
        QTest.keyClick(dialog, Qt.Key.Key_R)
        assert dialog.canvas.tool == "rectangle"
        QTest.keyClick(dialog, Qt.Key.Key_2)
        _drag(dialog, (30, 150), (80, 190))
        assert (_sheet(dialog)[150:191, 30:81] == LAND).all()
        QTest.keyClick(dialog, Qt.Key.Key_G)
        QTest.keyClick(dialog, Qt.Key.Key_6)
        QTest.mouseClick(dialog.canvas, Qt.MouseButton.LeftButton, pos=_at(dialog, 40, 160))
        assert _sheet(dialog)[160, 40] == LAKE
        # undo and redo, by key
        QTest.keyClick(dialog, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        assert _sheet(dialog)[160, 40] == LAND
        QTest.keyClick(
            dialog,
            Qt.Key.Key_Z,
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier,
        )
        assert _sheet(dialog)[160, 40] == LAKE
        # the right button takes the kind under the pointer
        QTest.mouseClick(dialog.canvas, Qt.MouseButton.RightButton, pos=_at(dialog, 150, 60))
        assert dialog.canvas.kind == LAND
        assert dialog.kind_buttons[LAND].isChecked()
        before = dialog.canvas.brush
        QTest.keyClick(dialog, Qt.Key.Key_BracketRight)
        assert dialog.canvas.brush > before
        assert dialog.size_value.text() == str(dialog.canvas.brush)
    finally:
        dialog.reject()


@pytest.mark.usefixtures("application")
def test_a_ready_land_is_laid_checked_and_used_for_the_world(
    tmp_path: Path, fake_export: Exporter, cut: list[int]
) -> None:
    _ = cut
    controller = _controller(tmp_path, fake_export)
    dialog = _opened(controller)
    try:
        gallery = dialog.galleries["ready"]
        pump(lambda: gallery.count() > 0 and gallery.item(0).flags() != Qt.ItemFlag.NoItemFlags)
        dialog._start_clicked(gallery.item(0))  # pyright: ignore[reportPrivateUsage]
        assert not dialog.sheet.empty  # pyright: ignore[reportOptionalMemberAccess]
        pump(lambda: not dialog.checking and dialog.use_button.isEnabled())
        assert dialog.lines[-1].level == "ok"
        assert (
            text("editor.check.land", share=dialog.lines[-1].values["share"])
            in dialog.report_label.text()
        )
        # terrain is added to the plain land on a worker
        dialog.decorate_button.click()
        pump(lambda: not dialog.working)
        assert dialog.sheet.counts()[MOUNTAINS] > 0  # pyright: ignore[reportOptionalMemberAccess]
        pump(lambda: not dialog.checking)
        dialog.use_button.click()
        assert dialog.result() == 1
        assert controller.land_mask is not None
        assert controller.drawings()["america"].id == controller.land_mask.id
        assert dialog.used
    finally:
        dialog.reject()


@pytest.mark.usefixtures("application")
def test_a_picture_that_is_no_world_cannot_be_used_and_a_draft_is_kept(
    tmp_path: Path, fake_export: Exporter, cut: list[int], monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = cut
    controller = _controller(tmp_path, fake_export)
    dialog = _opened(controller)
    _drag(dialog, (40, 40), (60, 40))
    pump(lambda: not dialog.checking)
    assert not dialog.use_button.isEnabled()
    assert dialog.report is not None
    assert dialog.report["refusal"] == "share"
    warnings: list[str] = []

    def warn(*arguments: object) -> None:
        warnings.append(str(arguments[-1]))

    monkeypatch.setattr(QMessageBox, "warning", warn)
    dialog._use()  # pyright: ignore[reportPrivateUsage]
    assert controller.land_mask is None
    drawn = _sheet(dialog).copy()
    dialog.reject()  # closing keeps what was drawn
    again = _opened(controller)
    try:
        assert np.array_equal(_sheet(again), drawn)
        assert Drafts(controller.data).load("america", (240, 300)) is not None
    finally:
        again.reject()


@pytest.mark.usefixtures("application")
def test_the_editor_says_why_the_area_could_not_be_cut(
    tmp_path: Path, fake_export: Exporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*_arguments: object, **_keywords: object) -> LandArea:
        message = "the game's map could not be read"
        raise OSError(message)

    monkeypatch.setattr(service, "land_area", broken)
    controller = _controller(tmp_path, fake_export)
    dialog = _opened(controller)
    try:
        assert dialog.stage == "failed"
        assert controller.phase is Phase.FAILED
        assert "could not be read" in dialog.failure.text()
    finally:
        dialog.reject()
    controller.game = None
    refused = LandEditorDialog(None, controller, "america")
    try:
        assert refused.stage == "failed"
        assert refused.failure.text() == text("ready_no_game")
    finally:
        refused.reject()


@pytest.mark.usefixtures("application")
def test_each_continent_of_the_world_has_its_own_sheet_and_land(
    tmp_path: Path, fake_export: Exporter, cut: list[int]
) -> None:
    _ = cut
    controller = _controller(tmp_path, fake_export)
    controller.set_continent("africa", enabled=True)
    assert controller.drawable_continents() == ["america", "africa"]
    dialog = _opened(controller)
    try:
        assert set(dialog.continent_buttons) == {"america", "africa"}
        assert dialog.continent_box.isVisible()
        _drag(dialog, (60, 60), (200, 60))
        assert dialog.version == 1
        dialog.continent_buttons["africa"].click()
        assert dialog.continent == "africa"
        pump(lambda: dialog.stage == "ready" and dialog.continent == "africa")
        assert dialog.sheet is not None
        assert dialog.sheet.empty  # another continent's sheet, not America's drawing
        assert dialog.drafts.load("america", (240, 300)) is not None
        gallery = dialog.galleries["ready"]
        pump(lambda: gallery.count() > 0 and gallery.item(0).flags() != Qt.ItemFlag.NoItemFlags)
        dialog._start_clicked(gallery.item(0))  # pyright: ignore[reportPrivateUsage]
        pump(lambda: not dialog.checking and dialog.use_button.isEnabled())
        dialog.use_button.click()
        assert "africa" in controller.drawings()
        assert "america" not in controller.drawings()
    finally:
        dialog.reject()


@pytest.mark.usefixtures("application")
def test_the_land_tools_of_the_window_follow_the_continents_and_open_the_editor(
    tmp_path: Path, fake_export: Exporter, cut: list[int], monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = cut
    controller = _controller(tmp_path, fake_export)
    window = MainWindow(controller)
    window.show()
    opened: list[str] = []

    def exec_(dialog: LandEditorDialog) -> int:
        opened.append(dialog.continent)
        dialog.reject()
        return 0

    monkeypatch.setattr(LandEditorDialog, "exec", exec_)
    try:
        tools = window.land_tools
        assert tools.rows["america"].isVisible()
        assert not tools.rows["africa"].isVisible()
        assert tools.editor_button.isEnabled()
        tools.editor_button.click()
        assert opened == ["america"]
        controller.set_continent("africa", enabled=True)
        pump(
            lambda: (
                tools.rows["africa"].isVisible() and tools.rows["africa"].edit_button.isEnabled()
            )
        )
        tools.rows["africa"].edit_button.click()
        assert opened == ["america", "africa"]
        assert tools.rows["america"].name.isVisible()  # several continents are named
        # a drawing of Africa shows in its row and goes back to generated land
        picture = tmp_path / "africa.png"
        _ = picture.write_bytes(_square_picture())
        assert controller.choose_land_image(picture, "africa") is None
        pump(
            lambda: (
                tools.rows["africa"].clear_button.isVisible()
                and tools.rows["africa"].clear_button.isEnabled()
            )
        )
        assert "Africa" in tools.rows["africa"].state.text()
        tools.rows["africa"].clear_button.click()
        pump(lambda: not tools.rows["africa"].clear_button.isVisible())
        assert "africa" not in controller.drawings()
        controller.set_continent("africa", enabled=False)
        controller.set_continent("america", enabled=False)
        pump(lambda: not tools.isVisible())
        assert not tools.editor_button.isEnabled()
    finally:
        _ = window.close()


def _square_picture() -> bytes:
    from rnw.png import COLOR_GRAY, encode_png  # noqa: PLC0415 - one test needs it

    picture = np.zeros((300, 400), dtype=np.uint8)
    picture[80:220, 100:300] = 255
    return encode_png(picture, color_type=COLOR_GRAY, compression="zlib")


def test_the_reports_are_told_worst_first_in_the_players_words() -> None:
    base: dict[str, object] = {
        "land": 321,
        "kept": 100,
        "specks": 0,
        "islands": 0,
        "open_lakes": [],
        "low": 50,
        "high": 125,
        "refusal": "",
    }
    good = say_report(base)
    assert [line.level for line in good] == ["ok"]
    assert good[0].says() == text("editor.check.land", share="32.1")
    refused = say_report({**base, "land": 10, "refusal": "share"})
    assert [(line.level, line.key) for line in refused] == [("error", "editor.check.share")]
    assert "5 %" in refused[0].says()
    assert "12.5 %" in refused[0].says()
    messy = say_report({**base, "kept": 80, "specks": 3, "islands": 2})
    assert [line.key for line in messy] == [
        "editor.check.dropped",
        "editor.check.specks",
        "editor.check.islands",
        "editor.check.land",
    ]
    assert messy[0].values == {"dropped": "20"}
    lake = say_report({**base, "refusal": "lake_open", "open_lakes": [[1, 2], [3, 4]]})
    assert lake[0].values == {"count": "2"}
    assert say_report({**base, "refusal": "outside"})[0].level == "error"


def test_the_brush_changes_by_a_pixel_when_small_and_by_a_quarter_when_large() -> None:
    assert resized(5, larger=True) == 6
    assert resized(5, larger=False) == 4
    assert resized(1, larger=False) == 1
    assert resized(8, larger=True) == 10
    assert resized(10, larger=False) == 8
    assert resized(64, larger=True) == 64
    assert land_editor.MAX_SIZE == 64  # pyright: ignore[reportPrivateLocalImportUsage]


@pytest.mark.usefixtures("application")
def test_a_ready_land_is_shown_small_on_the_area() -> None:
    area = _full_area().at(4)
    kinds = np.zeros(area.picture_shape, dtype=np.uint8)
    kinds[40:80, 60:120] = LAND
    pixmap = thumbnail(kinds, area.area)
    assert pixmap.width() == -(-area.picture_shape[1] // 4)
    assert pixmap.height() == -(-area.picture_shape[0] // 4)
