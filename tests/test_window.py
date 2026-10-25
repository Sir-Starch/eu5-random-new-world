"""The main window, driven offscreen: widgets follow the controller and the buttons act."""

# Qt stubs type signals and widgets loosely.
# pyright: reportAny=false

from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import TYPE_CHECKING

import pytest

from rnw.app import library, service
from rnw.app.discovery import Environment, GameInstall, Profile
from rnw.app.worldcode import decode, encode, new_code
from rnw.bundle import COVER_COPY
from rnw.gui.controller import NEW, Controller, Phase, Task
from rnw.gui.text import LANGUAGE_NAMES, set_language, text
from rnw.record import Verdict

try:  # the window needs PySide6 and the system's graphics libraries
    from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
    from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont, QImage, QMouseEvent, QWheelEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import (
        QApplication,
        QFileDialog,
        QLabel,
        QMessageBox,
        QPushButton,
        QWidget,
    )

    from rnw.gui.maps import CompareDialog
    from rnw.gui.preview import PreviewView
    from rnw.gui.text import TITLE
    from rnw.gui.window import AboutDialog, MainWindow, SettingsDialog
except ImportError:
    pytest.skip("PySide6 is not available", allow_module_level=True)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from rnw.app.library import World
    from rnw.app.service import Exporter
    from rnw.progress import Progress


@pytest.fixture(scope="module")
def application() -> QApplication:
    """One QApplication for the module (Qt allows a single one per process)."""
    existing = QApplication.instance()
    return existing if isinstance(existing, QApplication) else QApplication([])


def pump(condition: Callable[[], bool], timeout: float = 10.0) -> None:
    """Run the event loop until ``condition`` holds, so queued signals are delivered."""
    deadline = time.monotonic() + timeout
    while not condition():
        QApplication.processEvents()
        if time.monotonic() > deadline:
            message = "the window did not reach the expected state"
            raise AssertionError(message)
        time.sleep(0.005)


def _window(tmp_path: Path, export: Exporter, *, game: bool = True) -> MainWindow:
    def generator(request: service.Request, progress: Progress | None = None) -> service.Result:
        return service.generate(request, progress, export)

    controller = Controller(
        data=tmp_path / "data",
        environment=Environment(system="linux", home=tmp_path / "home", variables={}),
        generator=generator,
    )
    if game:
        (tmp_path / "game" / "game" / "in_game" / "map_data").mkdir(parents=True)
        controller.game = GameInstall(tmp_path / "game", None, "26043558")
    (tmp_path / "profile" / "mod").mkdir(parents=True)
    controller.profile = Profile(tmp_path / "profile", "linux", has_mods=True)
    return MainWindow(controller)


@pytest.mark.usefixtures("application")
def test_the_queue_buttons_generate_the_snapshots_the_player_added(
    tmp_path: Path,
    fake_export: Exporter,
) -> None:
    window = _window(tmp_path, fake_export)
    window.install_box.setChecked(False)
    _ = window.controller.set_seed("11")
    window.enqueue_button.click()
    _ = window.controller.set_seed("22")
    window.enqueue_button.click()
    window.run_queue_button.click()
    pump(lambda: window.controller.phase is Phase.FINISHED)
    assert {world.seed for world in window.controller.worlds} == {11, 22}
    assert not window.controller.queue
    _ = window.close()


@pytest.mark.usefixtures("application")
def test_a_world_file_destination_disables_install_and_saves_without_a_profile(
    tmp_path: Path,
    fake_export: Exporter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window = _window(tmp_path, fake_export)
    window.controller.profile = None
    output = tmp_path / "mine.rnworld"

    def choose(
        _parent: MainWindow,
        _title: str,
        _suggested: str,
        _filter: str,
    ) -> tuple[str, str]:
        return str(output), ""

    monkeypatch.setattr(QFileDialog, "getSaveFileName", choose)
    window.destination.setCurrentIndex(2)
    assert not window.install_box.isChecked()
    assert not window.generate_button.isEnabled()
    window.destination_button.click()
    assert window.generate_button.isEnabled()
    window.generate_button.click()
    pump(lambda: window.controller.phase is Phase.FINISHED)
    assert output.is_file()
    assert window.controller.result is not None
    assert window.controller.result.installed is None
    _ = window.close()


@pytest.mark.usefixtures("application")
def test_notes_and_favourite_are_saved_from_the_world_page(
    tmp_path: Path,
    fake_export: Exporter,
) -> None:
    window = _window(tmp_path, fake_export)
    window.generate_button.click()
    pump(lambda: window.controller.selected_world() is not None)
    window.world_tabs.setCurrentIndex(2)
    window.notes_edit.setPlainText("Try this one with friends")
    window.user_tag_edit.setText("multiplayer")
    window.starred_box.setChecked(True)
    window.save_notes_button.click()
    world = window.controller.selected_world()
    assert world is not None
    assert (world.notes, world.user_tag, world.starred) == (
        "Try this one with friends",
        "multiplayer",
        True,
    )
    _ = window.close()


@pytest.mark.usefixtures("application")
@pytest.mark.parametrize(("width", "height"), [(1080, 760), (1440, 900)])
def test_the_library_and_world_page_fit_the_supported_window_size(
    tmp_path: Path,
    fake_export: Exporter,
    width: int,
    height: int,
) -> None:
    window = _window(tmp_path, fake_export)
    window.resize(width, height)
    window.show()
    QApplication.processEvents()
    assert (window.width(), window.height()) == (width, height)
    assert not window.show_new_world.visibleRegion().isEmpty()
    assert not window.progress_box.isVisible()
    for button in window.new_page.findChildren(QPushButton):
        if button.isVisibleTo(window):
            assert button.height() >= max(32, button.fontMetrics().height() + 14)
            assert button.width() >= button.minimumSizeHint().width()
    window.generate_button.click()
    pump(lambda: window.controller.selected_world() is not None)
    QApplication.processEvents()
    assert (window.width(), window.height()) == (width, height)
    assert not window.world_visibility.visibleRegion().isEmpty()
    _ = window.close()


@pytest.mark.usefixtures("application")
def test_progress_height_and_percent_display_stay_in_sync(
    tmp_path: Path,
    fake_export: Exporter,
) -> None:
    window = _window(tmp_path, fake_export)
    window.resize(1080, 760)
    window.show()
    window.controller.task = Task.GENERATE
    window.controller.phase = Phase.RUNNING
    window.controller.fraction = 0.975
    window.controller.running = ("water textures",)
    window.refresh()
    QApplication.processEvents()
    height = window.height()
    status_height = window.status.height()

    window.controller.running = (
        "water textures",
        "biomes and rivers",
        "identities",
        "script remap",
        "spline network",
    )
    window.refresh()
    QApplication.processEvents()

    assert window.height() == height
    assert window.status.height() == status_height
    assert not window.status.wordWrap()
    assert window.bar.value() == 98
    assert window.bar.text() == "98%"
    assert "98 %" in window.world_list.item(0).text()

    window.controller.phase = Phase.IDLE
    window.controller.task = None
    _ = window.close()


@pytest.mark.usefixtures("application")
@pytest.mark.parametrize("language", sorted(LANGUAGE_NAMES))
def test_every_language_fits_the_smallest_supported_window(
    tmp_path: Path, fake_export: Exporter, language: str
) -> None:
    """Translations run longer than English; none may widen the window or cut a button (L1)."""
    set_language(language)
    try:
        window = _window(tmp_path, fake_export)
        window.resize(1080, 760)
        window.show()
        QApplication.processEvents()
        assert (window.width(), window.height()) == (1080, 760)
        for button in window.new_page.findChildren(QPushButton):
            if button.isVisibleTo(window):
                assert button.width() >= button.minimumSizeHint().width(), button.text()
        window.generate_button.click()
        pump(lambda: window.controller.selected_world() is not None)
        QApplication.processEvents()
        assert (window.width(), window.height()) == (1080, 760)
        _ = window.close()
    finally:
        set_language("english")


@pytest.mark.usefixtures("application")
def test_the_library_panel_leaves_its_width_to_the_splitter(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """A wide font or an error naming a Windows path wraps or clips; it never widens the window."""
    window = _window(tmp_path, fake_export)
    window.setFont(QFont("Sans Serif", 12))
    window.resize(1080, 760)
    window.show()
    path = r"C:\Users\runneradmin\AppData\Local\rnw\worlds\6rf2nzt4dv\mod\map_data\locations.png"
    window.library_status.setText(
        text(
            "batch_delete_failed", name="Small continents", done=2, message=f"Access denied: {path}"
        )
    )
    window.library_status.show()
    QApplication.processEvents()
    panel = window.world_list.parent()
    assert isinstance(panel, QWidget)
    assert panel.minimumSizeHint().width() == window.world_list.minimumWidth()
    assert (window.width(), window.height()) == (1080, 760)
    _ = window.close()


@pytest.mark.usefixtures("application")
def test_the_new_world_page_shows_types_and_needs_a_game(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """Every world type is offered; without a game, Generate is off and says why."""
    window = _window(tmp_path, fake_export, game=False)
    assert window.stack.currentWidget() is window.new_page
    assert window.type_choice.count() == 7
    window.type_choice.setCurrentIndex(5)
    assert window.controller.preset == "archipelago"
    assert window.controller.mode is None
    assert not window.generate_button.isEnabled()
    assert window.problem_line.text() == text("game_missing")
    window.type_choice.setCurrentIndex(1)
    assert window.controller.mode == "chaos"
    assert window.type_choice.currentData() == "chaos"
    assert window.type_about.text() == text("type.chaos.about")
    window.type_choice.setCurrentIndex(0)
    assert window.controller.mode == "random"
    assert window.type_about.text() == text("type.random.about")
    _ = window.close()


@pytest.mark.usefixtures("application")
def test_a_slider_changes_the_world_and_its_code(tmp_path: Path, fake_export: Exporter) -> None:
    """Moving a control changes the value, marks it, and the code carries it."""
    window = _window(tmp_path, fake_export)
    controller = window.controller
    before = controller.code
    window.customize_button.setChecked(True)
    row = next(r for r in window.rows if r.control.key == "natives.state_spread_permille")
    row.slider.setValue(row.control.position(400))
    pump(lambda: "natives.state_spread_permille" in controller.changes)
    assert controller.value("natives.state_spread_permille") == row.control.value_at(
        row.control.position(400)
    )
    assert controller.code != before
    assert window.code_edit.text() == controller.code
    assert row.reset.isEnabled()
    row.reset.click()
    pump(lambda: not controller.changes)
    _ = window.close()


@pytest.mark.usefixtures("application")
def test_quick_buttons_set_the_controls_and_follow_the_sliders(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """A button sets its answer, the sliders move with it and a moved slider reads as custom."""
    window = _window(tmp_path, fake_export)
    controller = window.controller
    rows = {row.quick.name: row for row in window.quick_rows}
    assert set(rows) == {"land", "peoples", "states", "empires", "wealth"}
    assert rows["empires"].buttons["seldom"].isChecked()
    assert not rows["empires"].custom.isVisibleTo(window)
    rows["empires"].buttons["often"].click()
    pump(lambda: controller.value("natives.empire_permille") == 800)
    assert rows["empires"].buttons["often"].isChecked()
    assert not rows["empires"].buttons["seldom"].isChecked()
    row = next(r for r in window.rows if r.control.key == "natives.empire_permille")
    assert row.number.value() == 80.0
    row.number.setValue(33.0)
    pump(lambda: controller.quick_level("empires") is None)
    assert not any(button.isChecked() for button in rows["empires"].buttons.values())
    assert rows["empires"].custom.isVisibleTo(window)
    rows["empires"].buttons["never"].click()
    pump(lambda: controller.value("natives.empire_permille") == 0)
    _ = window.close()


@pytest.mark.usefixtures("application")
def test_a_made_world_opens_hidden_and_shows_when_the_setting_says_so(
    tmp_path: Path, fake_export: Exporter
) -> None:
    window = _window(tmp_path, fake_export)
    controller = window.controller
    window.generate_button.click()
    pump(lambda: controller.phase is Phase.FINISHED and bool(controller.worlds))
    pump(lambda: window.stack.currentWidget() is window.world_page)
    assert window.world_list.count() == 2
    assert window.preview_caption.text().startswith(text("preview_hidden"))
    window.world_visibility.setChecked(True)
    pump(lambda: window.preview_caption.text().startswith(text("preview_shown")))
    assert window.remove_button.isVisible() or not window.isVisible()
    window.world_list.setCurrentRow(0)
    pump(lambda: controller.selection == NEW)
    _ = window.close()


@pytest.mark.usefixtures("application")
def test_new_world_visibility_is_a_default_and_leaves_the_existing_world_hidden(
    tmp_path: Path, fake_export: Exporter
) -> None:
    window = _window(tmp_path, fake_export)
    window.generate_button.click()
    pump(lambda: window.controller.phase is Phase.FINISHED)
    [first] = window.controller.worlds
    window.controller.select(NEW)
    pump(lambda: window.stack.currentWidget() is window.new_page)
    window.show_new_world.setChecked(True)
    assert window.controller.preferences.show_new_world
    assert not window.controller.shown(first)
    window.controller.randomize()
    window.generate_button.click()
    pump(lambda: window.controller.phase is Phase.FINISHED)
    second = window.controller.selected_world()
    assert second is not None
    assert window.controller.shown(second)
    assert not window.controller.shown(first)
    _ = window.close()


@pytest.mark.usefixtures("application")
def test_a_missing_cover_keeps_the_visibility_checkbox_and_reports_the_problem(
    tmp_path: Path, fake_export: Exporter
) -> None:
    window = _window(tmp_path, fake_export)
    window.generate_button.click()
    pump(lambda: window.controller.phase is Phase.FINISHED)
    pump(window.world_visibility.isEnabled)
    world = window.controller.selected_world()
    assert world is not None
    cover = library.folder(window.controller.data, world) / COVER_COPY
    for path in cover.rglob("*"):
        if path.is_file():
            path.unlink()
    window.world_visibility.click()
    assert not window.world_visibility.isChecked()
    assert "cover" in window.world_notice.text()
    assert "missing" in window.world_notice.text()
    assert window.controller.task is Task.GENERATE
    assert window.controller.phase is Phase.FINISHED
    _ = window.close()


@pytest.mark.usefixtures("application")
def test_delete_asks_first(
    tmp_path: Path, fake_export: Exporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Delete does nothing when the player says no and removes the world on yes."""
    window = _window(tmp_path, fake_export)
    controller = window.controller
    _ = controller.start()
    controller.wait(10)
    pump(lambda: bool(controller.worlds))
    answers = [QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes]

    def answer(*_args: object, **_kwargs: object) -> QMessageBox.StandardButton:
        return answers.pop(0)

    monkeypatch.setattr(QMessageBox, "question", answer)
    window.delete_button.click()
    assert controller.worlds
    window.delete_button.click()
    controller.wait(10)
    pump(lambda: not controller.worlds)
    _ = window.close()


@pytest.mark.usefixtures("application")
def test_multiple_worlds_can_be_selected_and_removed_from_the_library_panel(
    tmp_path: Path, fake_export: Exporter
) -> None:
    window = _window(tmp_path, fake_export)
    controller = window.controller
    for seed in (11, 22, 33):
        _ = controller.set_seed(str(seed))
        assert controller.start() is None
        controller.wait(10)
        assert controller.phase is Phase.FINISHED
    window.resize(1080, 760)
    window.show()
    window.refresh()
    QApplication.processEvents()
    listing = window.world_list
    first = listing.visualItemRect(listing.item(1)).center()
    second = listing.visualItemRect(listing.item(2)).center()
    third = listing.visualItemRect(listing.item(3)).center()
    QTest.mouseClick(listing.viewport(), Qt.MouseButton.LeftButton, pos=first)
    QTest.mouseClick(
        listing.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier, second
    )
    selected = set(window.selected_entries())
    assert len(selected) == 2
    window.refresh()
    assert set(window.selected_entries()) == selected
    # Changing a row's label rebuilds the list and must still preserve the selection.
    world = next(world for world in controller.worlds if world.id in selected)
    assert controller.rename(world, "Renamed") is None
    window.refresh()
    assert set(window.selected_entries()) == selected
    QTest.mouseClick(listing.viewport(), Qt.MouseButton.LeftButton, pos=first)
    QTest.mouseClick(
        listing.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, third
    )
    assert len(window.selected_entries()) == 3
    window.select_all_button.click()
    assert len(listing.selectedItems()) == 3
    assert NEW not in window.selected_entries()
    assert window.library_remove.isEnabled()
    controller.game = None
    window.refresh()
    window.library_remove.click()
    controller.wait(10)
    assert controller.phase is Phase.FINISHED, controller.message
    window.refresh()
    assert len(controller.worlds) == 3
    assert all(
        controller.placement(world) is library.Placement.CODE_ONLY for world in controller.worlds
    )
    assert not window.library_remove.isEnabled()
    assert window.library_delete.isEnabled()
    assert len(window.selected_entries()) == 3
    assert window.library_status.text() == text("batch_removed")
    _ = window.close()


@pytest.mark.usefixtures("application")
def test_bulk_delete_confirms_the_selected_names_once_and_keeps_the_other_world(
    tmp_path: Path, fake_export: Exporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = _window(tmp_path, fake_export)
    controller = window.controller
    for seed in (11, 22, 33):
        _ = controller.set_seed(str(seed))
        assert controller.start() is None
        controller.wait(10)
    window.refresh()
    listing = window.world_list
    listing.setCurrentRow(1)
    listing.item(2).setSelected(True)
    selected = set(window.selected_entries())
    assert len(selected) == 2
    kept = next(world for world in controller.worlds if world.id not in selected)
    answers = [QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes]
    questions: list[str] = []

    def answer(
        _parent: MainWindow, _title: str, question: str, *_args: object
    ) -> QMessageBox.StandardButton:
        questions.append(question)
        return answers.pop(0)

    monkeypatch.setattr(QMessageBox, "question", answer)
    window.library_delete.click()
    assert len(controller.worlds) == 3
    window.library_delete.click()
    controller.wait(10)
    window.refresh()
    assert len(questions) == 2
    assert questions[0] == questions[1]
    assert controller.worlds == [kept]
    assert controller.placement(kept) is library.Placement.IN_GAME
    assert window.library_status.text() == text("batch_deleted")
    assert not window.selected_entries()
    assert not window.library_delete.isEnabled()
    _ = window.close()


@pytest.mark.usefixtures("application")
def test_the_settings_dialog_does_not_compress_path_controls(
    tmp_path: Path, fake_export: Exporter
) -> None:
    window = _window(tmp_path, fake_export)
    controller = window.controller
    controller.games = [GameInstall(tmp_path / ("long game path " * 8), None, "26043558")]
    controller.profiles = [Profile(tmp_path / ("long profile path " * 8), "linux", has_mods=True)]
    dialog = SettingsDialog(window)
    dialog.show()
    QApplication.processEvents()
    for choice in (dialog.game_choice, dialog.profile_choice):
        assert choice.height() >= choice.sizeHint().height()
    assert dialog.width() <= 800
    _ = dialog.close()
    _ = window.close()


def test_gui_self_test_does_not_migrate_the_players_library(tmp_path: Path) -> None:
    data = tmp_path / "players-library"
    world = library.World("legacy", "code", "continents", 42, "0.9.23", "26043558", 0, 0.0)
    library.save(data, world)
    record = library.folder(data, world) / library.RECORD
    before = record.read_bytes()
    result = subprocess.run(
        [sys.executable, "-m", "rnw.gui", "--self-test"],
        env={**os.environ, "RNW_DATA": str(data), "QT_QPA_PLATFORM": "offscreen"},
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert record.read_bytes() == before


@pytest.mark.usefixtures("application")
def test_a_world_page_says_whether_it_comes_out_the_same_and_checks_on_request(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """The record's sentence is on the page; Check runs and its answer replaces the sentence."""
    window = _window(tmp_path, fake_export)
    controller = window.controller

    def checker(
        world: World, *, game: GameInstall, data: Path, progress: Progress | None = None
    ) -> service.Check:
        del world, game, data, progress
        return service.Check(Verdict.IDENTICAL, True, [], [], 1.0)  # noqa: FBT003

    controller.checker = checker
    window.generate_button.click()
    pump(lambda: controller.phase is Phase.FINISHED and bool(controller.worlds))
    pump(lambda: window.stack.currentWidget() is window.world_page)
    assert "byte for byte" in window.details["reproduce"].text()
    pump(window.check_button.isEnabled)
    window.check_button.click()
    pump(lambda: controller.phase is Phase.FINISHED and controller.task is Task.CHECK)
    pump(lambda: "files are the same" in window.details["reproduce"].text())
    controller.game = None
    controller.refresh_library()
    pump(lambda: not window.check_button.isEnabled())
    _ = window.close()


@pytest.mark.usefixtures("application")
def test_the_buttons_make_a_version_of_the_world_and_the_list_shows_it_below(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """New peoples makes a version on the same land; it is listed indented, with a way back."""
    window = _window(tmp_path, fake_export)
    controller = window.controller
    window.generate_button.click()
    pump(lambda: controller.phase is Phase.FINISHED and bool(controller.worlds))
    pump(lambda: window.stack.currentWidget() is window.world_page)
    window.peoples_button.click()
    pump(lambda: controller.phase is Phase.FINISHED and len(controller.worlds) == 2)
    pump(lambda: window.world_list.count() == 3)
    assert window.world_list.item(2).text().startswith("↳ ")
    assert text("part.peoples") in window.world_list.item(2).text()
    pump(lambda: window.parent_button.isVisible() or not window.isVisible())
    window.parent_button.click()
    pump(lambda: not getattr(controller.selected_world(), "parent", "x"))
    window.edit_button.click()
    pump(lambda: controller.selection == NEW)
    _ = window.close()


@pytest.mark.usefixtures("application")
def test_the_maps_tab_is_covered_until_revealed_and_then_draws_layers_and_answers(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """Covered by default; Reveal draws the map; layers, hover, search and saving work."""
    window = _window(tmp_path, fake_export)
    controller = window.controller
    window.generate_button.click()
    pump(lambda: controller.phase is Phase.FINISHED and bool(controller.worlds))
    pump(lambda: window.stack.currentWidget() is window.world_page)
    maps = window.maps
    assert maps.pages.currentIndex() == 0
    assert maps.reveal_button.isVisibleTo(maps)
    assert maps.picture() is None
    maps.reveal_button.click()
    pump(lambda: maps.pages.currentIndex() == 1)
    assert maps.picture() is not None
    assert "countries" in maps.summary.text()
    for layer in ("countries", "cultures", "religions", "resources", "development", "land"):
        maps.select_layer(layer)
        assert maps.layer == layer
        assert maps.legend_list.count() > 0
    first = maps.picture()
    maps.search.setText("aland")
    pump(lambda: maps.results.count() > 0)
    maps.results.setCurrentRow(0)
    marked = maps.picture()
    assert first is not None
    assert marked is not None
    assert not (first == marked).all()
    maps.search.setText("")
    pump(lambda: maps.results.count() == 0)
    maps.show_facts_at(5, 5)
    assert maps.facts.text()
    maps.clear_facts()
    assert maps.facts.text() == text("facts_hint")
    _ = window.close()


@pytest.mark.usefixtures("application")
def test_pictures_are_saved_and_two_worlds_are_compared(
    tmp_path: Path, fake_export: Exporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Save picture writes the chosen file; Compare needs two revealed worlds and then opens."""
    window = _window(tmp_path, fake_export)
    controller = window.controller
    window.generate_button.click()
    pump(lambda: controller.phase is Phase.FINISHED and bool(controller.worlds))
    pump(lambda: window.stack.currentWidget() is window.world_page)
    target = tmp_path / "saved.png"

    def chosen(*_arguments: object, **_keywords: object) -> tuple[str, str]:
        return str(target), "PNG (*.png)"

    monkeypatch.setattr(QFileDialog, "getSaveFileName", chosen)
    window.save_button.click()
    assert target.is_file()
    assert "saved.png" in window.world_notice.text()
    window.compare_button.click()
    assert text("compare_need_two") in window.world_notice.text()
    controller.set_show_new_world(True)
    [only] = controller.worlds
    entries = [("one", controller.atlas(only)), ("two", controller.atlas(only))]
    assert all(found is not None for _name, found in entries)
    dialog = CompareDialog(window, [(name, found) for name, found in entries if found], "land")
    dialog.layer_buttons.button(1).click()
    assert len(dialog.views) == 2
    dialog.choices[1].setCurrentIndex(0)
    _ = dialog.close()
    _ = window.close()


@pytest.mark.usefixtures("application")
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_world_files_are_written_opened_and_dropped_on_the_window(
    tmp_path: Path, fake_export: Exporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Save world file writes it; Open takes it into a second library; a drop does the same."""
    first = _window(tmp_path / "one", fake_export)
    first.generate_button.click()
    pump(lambda: first.controller.phase is Phase.FINISHED and bool(first.controller.worlds))
    pump(lambda: first.stack.currentWidget() is first.world_page)
    target = tmp_path / "w.rnworld"
    answer = {"path": str(target)}

    def chosen(*_arguments: object, **_keywords: object) -> tuple[str, str]:
        return answer["path"], ""

    monkeypatch.setattr(QFileDialog, "getSaveFileName", chosen)
    first.export_button.click()
    assert target.is_file()
    assert "w.rnworld" in first.world_notice.text()
    second = _window(tmp_path / "two", fake_export)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", chosen)
    second.open_file_button.click()
    pump(lambda: bool(second.controller.worlds))
    assert second.world_notice.text() == text("imported")
    bad = tmp_path / "bad.rnworld"
    _ = bad.write_bytes(b"x")
    warned: list[str] = []

    def warn(_parent: object, _title: str, message: str) -> QMessageBox.StandardButton:
        warned.append(message)
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "warning", warn)
    answer["path"] = str(bad)
    second.open_file_button.click()
    assert warned
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(target))])
    third = _window(tmp_path / "three", fake_export)
    event = QDragEnterEvent(
        QPoint(5, 5),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    third.dragEnterEvent(event)
    assert event.isAccepted()
    drop = QDropEvent(
        QPointF(5, 5),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    third.dropEvent(drop)
    pump(lambda: bool(third.controller.worlds))
    text_mime = QMimeData()
    text_mime.setText("RNW1-0426C-SYW6B-MW73Y-C004H-0037F-87G")
    code_event = QDragEnterEvent(
        QPoint(5, 5),
        Qt.DropAction.CopyAction,
        text_mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    third.dragEnterEvent(code_event)
    assert code_event.isAccepted()
    other_mime = QMimeData()
    other_mime.setText("hello")
    plain = QDragEnterEvent(
        QPoint(5, 5),
        Qt.DropAction.CopyAction,
        other_mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    third.dragEnterEvent(plain)
    assert not plain.isAccepted()
    for window in (first, second, third):
        _ = window.close()


@pytest.mark.usefixtures("application")
def test_ocean_checkbox_is_in_the_world_code_and_follows_pasted_codes(
    tmp_path: Path,
    fake_export: Exporter,
) -> None:
    window = _window(tmp_path, fake_export)
    assert window.expand_oceans.isChecked()
    window.expand_oceans.click()
    assert decode(window.controller.code).settings().new_world.expand_oceans == 0
    code = encode(new_code("continents", 123))
    assert window.controller.use_code(code) is None
    assert window.expand_oceans.isChecked()
    assert decode(window.controller.code).settings().new_world.expand_oceans == 1
    _ = window.close()


@pytest.mark.usefixtures("application")
def test_about_dialog_and_header_button(tmp_path: Path, fake_export: Exporter) -> None:
    window = _window(tmp_path, fake_export)
    assert window.about_button.text() == text("about")
    assert window.about_button.toolTip() == text("about_tip")
    dialog = AboutDialog(window)
    dialog.show()
    QApplication.processEvents()
    assert TITLE in dialog.windowTitle()
    labels = dialog.findChildren(QLabel)
    texts = " ".join(lbl.text() for lbl in labels)
    assert "https://github.com/Sir-Starch/eu5-random-new-world" in texts
    assert "https://github.com/Sir-Starch/eu5-random-new-world/issues" in texts
    assert "CHANGELOG.md" in texts
    assert "docs" in texts
    _ = dialog.close()
    _ = window.close()


@pytest.mark.usefixtures("application")
def test_preview_view_zooms_drags_and_fits(application: QApplication) -> None:
    view = PreviewView()
    view.resize(800, 280)
    image = QImage(2048, 1024, QImage.Format.Format_RGB32)
    image.fill(0xFF0000)
    view.show_image(image, "test_preview")
    initial_scale = view.transform().m11()
    assert initial_scale > 0

    # Zoom in via wheel
    wheel = QWheelEvent(
        QPoint(100, 100),
        view.mapToGlobal(QPoint(100, 100)),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,  # noqa: FBT003
    )
    view.wheelEvent(wheel)
    zoomed_scale = view.transform().m11()
    assert zoomed_scale > initial_scale

    # Zoom in more to enable scrollbars for dragging
    for _ in range(3):
        view.wheelEvent(wheel)

    hbar = view.horizontalScrollBar()
    vbar = view.verticalScrollBar()
    assert hbar.maximum() > 0
    assert vbar.maximum() > 0
    h_before, v_before = hbar.value(), vbar.value()

    pos1 = QPoint(200, 200)
    pos2 = QPoint(150, 150)
    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        pos1,
        view.viewport().mapToGlobal(pos1),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    _ = application.sendEvent(view.viewport(), press)
    move = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        pos2,
        view.viewport().mapToGlobal(pos2),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    _ = application.sendEvent(view.viewport(), move)
    release = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        pos2,
        view.viewport().mapToGlobal(pos2),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    _ = application.sendEvent(view.viewport(), release)
    assert (hbar.value(), vbar.value()) != (h_before, v_before)

    # Double click resets fit
    dbl = QMouseEvent(
        QMouseEvent.Type.MouseButtonDblClick,
        pos1,
        view.mapToGlobal(pos1),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    view.mouseDoubleClickEvent(dbl)
    reset_scale = view.transform().m11()
    assert abs(reset_scale - initial_scale) < 1e-4
