"""The main window, driven offscreen: widgets follow the controller and the buttons act."""

# NumPy and Qt stubs type signals and widgets loosely.
# pyright: reportAny=false

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

import pytest

from rnw.app.discovery import Environment, GameInstall
from rnw.app.service import Request, Result
from rnw.app.worldcode import encode, new_code
from rnw.gui.controller import Controller, Generator, Phase

try:  # the window needs PySide6 and the system's graphics libraries
    from PySide6.QtWidgets import QApplication

    from rnw.gui.window import MainWindow
except ImportError:
    pytest.skip("PySide6 is not available", allow_module_level=True)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

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


def quick(request: Request, progress: Progress | None = None) -> Result:
    """A generator that reports two stages and returns."""
    assert progress is not None
    progress.begin("generate world")
    progress.finish("generate world")
    return Result(encode(request.code), request.data, None, 2.4, {})


def hang(request: Request, progress: Progress | None = None) -> Result:
    """A generator that runs until it is cancelled."""
    del request
    assert progress is not None
    progress.begin("generate world")
    while True:
        progress.checkpoint()
        _ = threading.Event().wait(0.005)


def _window(tmp_path: Path, generator: Generator) -> MainWindow:
    game = tmp_path / "game"
    (game / "game" / "in_game" / "map_data").mkdir(parents=True)
    controller = Controller(
        data=tmp_path / "data",
        environment=Environment(system="linux", home=tmp_path / "home", variables={}),
        generator=generator,
    )
    controller.game = GameInstall(game, None, "26043558")
    controller.install = False
    return MainWindow(controller)


def test_the_window_shows_the_world_and_enables_generate_only_when_it_can(
    application: QApplication, tmp_path: Path
) -> None:
    """Seed and code come from the controller; without a game Generate is off."""
    del application
    window = _window(tmp_path, quick)
    controller = window.controller
    assert window.seed_edit.text() == str(controller.seed)
    assert window.code_edit.text() == controller.code
    assert window.generate_button.isEnabled()
    assert not window.cancel_button.isEnabled()
    assert window.stage_list.count() > 10
    controller.game = None
    window.refresh()
    assert not window.generate_button.isEnabled()
    assert window.game_problem.text() != ""


def test_typing_a_seed_or_pasting_a_code_changes_the_world(
    application: QApplication, tmp_path: Path
) -> None:
    """A typed seed, a pasted code and a bad entry all go through the controller's checks."""
    window = _window(tmp_path, quick)
    window.seed_edit.setText("2468")
    window.seed_edit.editingFinished.emit()
    assert window.controller.seed == 2468
    window.seed_edit.setText("not a number")
    window.seed_edit.editingFinished.emit()
    assert window.controller.seed == 2468
    assert window.notice.text() != ""
    assert window.seed_edit.text() == "2468"
    QApplication.clipboard().setText(encode(new_code("archipelago", 99)))
    window.paste_button.click()
    assert (window.controller.preset, window.controller.seed) == ("archipelago", 99)
    assert window.preset_choice.currentData() == "archipelago"
    window.copy_button.click()
    assert QApplication.clipboard().text() == window.controller.code
    window.random_button.click()
    assert window.controller.seed != 99
    del application


def test_generate_runs_to_the_end_and_fills_the_history(
    application: QApplication, tmp_path: Path
) -> None:
    """The bar fills, the status says done, and Generate is available again."""
    del application
    window = _window(tmp_path, quick)
    window.generate_button.click()
    pump(lambda: window.controller.phase is Phase.FINISHED)
    pump(lambda: window.bar.value() == window.bar.maximum())
    assert "Done in 2 s" in window.status.text()
    assert window.generate_button.isEnabled()
    items = [window.stage_list.item(row).text() for row in range(window.stage_list.count())]
    assert any(item.startswith("✓") and "Generating continents" in item for item in items)


def test_cancel_shows_cancelling_and_then_cancelled(
    application: QApplication, tmp_path: Path
) -> None:
    """While the generator runs the controls are locked and Cancel is the one live button."""
    del application
    window = _window(tmp_path, hang)
    window.generate_button.click()
    pump(lambda: window.controller.phase is Phase.RUNNING and window.cancel_button.isEnabled())
    assert not window.generate_button.isEnabled()
    assert not window.seed_edit.isEnabled()
    window.cancel_button.click()
    pump(lambda: window.controller.phase is Phase.CANCELLED)
    pump(lambda: "Cancelled" in window.status.text())
    assert window.seed_edit.isEnabled()
    _ = window.close()
