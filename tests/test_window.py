"""The main window, driven offscreen: widgets follow the controller and the buttons act."""

# Qt stubs type signals and widgets loosely.
# pyright: reportAny=false

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest

from rnw.app import service
from rnw.app.discovery import Environment, GameInstall, Profile
from rnw.gui.controller import NEW, Controller, Phase
from rnw.gui.text import text

try:  # the window needs PySide6 and the system's graphics libraries
    from PySide6.QtWidgets import QApplication, QMessageBox

    from rnw.gui.window import MainWindow, SettingsDialog
except ImportError:
    pytest.skip("PySide6 is not available", allow_module_level=True)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

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
def test_the_new_world_page_shows_types_and_needs_a_game(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """Every world type is offered; without a game, Generate is off and says why."""
    window = _window(tmp_path, fake_export, game=False)
    assert window.stack.currentWidget() is window.new_page
    assert len(window.type_buttons.buttons()) == 5
    assert not window.generate_button.isEnabled()
    assert window.problem_line.text() == text("game_missing")
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
def test_a_made_world_opens_hidden_and_shows_on_request(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """After Generate the world is listed and shown with its New World covered until asked."""
    window = _window(tmp_path, fake_export)
    controller = window.controller
    window.generate_button.click()
    pump(lambda: controller.phase is Phase.FINISHED and bool(controller.worlds))
    pump(lambda: window.stack.currentWidget() is window.world_page)
    assert window.world_list.count() == 2
    assert not window.reveal_button.isChecked()
    assert window.preview_caption.text().startswith(text("preview_hidden"))
    window.reveal_button.click()
    pump(lambda: controller.revealed)
    assert window.preview_caption.text().startswith(text("preview_shown"))
    assert window.remove_button.isVisible() or not window.isVisible()
    window.world_list.setCurrentRow(0)
    pump(lambda: controller.selection == NEW)
    assert not controller.revealed
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
def test_the_settings_dialog_remembers_the_picture_choice(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """The box for the mod-list pictures starts off and its choice is kept."""
    window = _window(tmp_path, fake_export)
    dialog = SettingsDialog(window)
    assert not dialog.reveal.isChecked()
    dialog.reveal.setChecked(True)
    assert window.controller.preferences.reveal_thumbnails
    _ = dialog.close()
    _ = window.close()
