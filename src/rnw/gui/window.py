"""The main window: draws the controller's state and forwards the buttons to it.

All rules live in ``rnw.gui.controller`` and ``rnw.app``; this module only creates widgets
and keeps them equal to the controller. The generation runs on the controller's thread;
its changes reach the window as a signal, so the window itself never waits.
"""

# Qt windows are built in helper methods; every widget exists once the constructor returns.
# pyright: reportUninitializedInstanceVariable=false

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Final, cast, override

from PySide6.QtCore import QObject, Qt, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from rnw import __version__, parallel
from rnw.gui.controller import Controller, Phase
from rnw.gui.text import TITLE, text
from rnw.settings import PRESETS

GIB: Final[float] = float(1 << 30)
PROGRESS_STEPS: Final[int] = 1000
PREVIEW_WIDTH: Final[int] = 560
MARKS: Final[dict[str, str]] = {"done": "✓", "running": "▶", "waiting": "·"}
CLOSE_WAIT: Final[float] = 15.0
MIN_PATH_CHARACTERS: Final[int] = 24
RED: Final[str] = "color: #b00020;"


class _Bridge(QObject):
    """Carries 'something changed' from the generation thread to the window's thread."""

    changed: Signal = Signal()


class MainWindow(QMainWindow):
    """The generator application's window."""

    resources: QLabel
    game_choice: QComboBox
    profile_choice: QComboBox
    game_browse: QPushButton
    profile_browse: QPushButton
    build_label: QLabel
    game_problem: QLabel
    preset_choice: QComboBox
    seed_edit: QLineEdit
    random_button: QPushButton
    code_edit: QLineEdit
    copy_button: QPushButton
    paste_button: QPushButton
    notice: QLabel
    install_box: QCheckBox
    generate_button: QPushButton
    cancel_button: QPushButton
    history_list: QListWidget
    use_button: QPushButton
    bar: QProgressBar
    status: QLabel
    stage_list: QListWidget
    preview: QLabel
    outcome: QLabel
    next_steps: QLabel
    open_button: QPushButton

    def __init__(self, controller: Controller) -> None:
        super().__init__()
        self.controller: Controller = controller
        self._bridge: _Bridge = _Bridge()
        self._building: bool = False
        self.setWindowTitle(TITLE)
        self._build()
        _ = self._bridge.changed.connect(self.refresh)
        controller.subscribe(self._bridge.changed.emit)
        self.refresh()

    # -- construction ---------------------------------------------------------------

    def _build(self) -> None:
        root = QWidget()
        columns = QHBoxLayout(root)
        left, right = QVBoxLayout(), QVBoxLayout()
        columns.addLayout(left, 5)
        columns.addLayout(right, 6)
        left.addWidget(self._game_box())
        left.addWidget(self._world_box())
        left.addLayout(self._buttons())
        left.addWidget(self._history_box(), 1)
        right.addWidget(self._progress_box(), 1)
        right.addWidget(self._result_box())
        self.setCentralWidget(root)
        self.resources = QLabel()
        status = self.statusBar()
        status.addPermanentWidget(QLabel(f"v{__version__}"))
        status.addWidget(self.resources)

    def _game_box(self) -> QGroupBox:
        box = QGroupBox(text("game"))
        grid = QGridLayout(box)
        self.game_choice = QComboBox()
        self.profile_choice = QComboBox()
        for combo in (self.game_choice, self.profile_choice):
            combo.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            combo.setMinimumContentsLength(MIN_PATH_CHARACTERS)
        self.game_browse = QPushButton(text("browse"))
        self.profile_browse = QPushButton(text("browse"))
        self.build_label = QLabel()
        self.game_problem = QLabel()
        self.game_problem.setWordWrap(True)
        self.game_problem.setStyleSheet(RED)
        grid.addWidget(QLabel(text("game")), 0, 0)
        grid.addWidget(self.game_choice, 0, 1)
        grid.addWidget(self.game_browse, 0, 2)
        grid.addWidget(self.build_label, 1, 1)
        grid.addWidget(QLabel(text("profile")), 2, 0)
        grid.addWidget(self.profile_choice, 2, 1)
        grid.addWidget(self.profile_browse, 2, 2)
        grid.addWidget(self.game_problem, 3, 0, 1, 3)
        grid.setColumnStretch(1, 1)
        _ = self.game_browse.clicked.connect(self._browse_game)
        _ = self.profile_browse.clicked.connect(self._browse_profile)
        _ = self.game_choice.activated.connect(self._pick_game)
        _ = self.profile_choice.activated.connect(self._pick_profile)
        return box

    def _world_box(self) -> QGroupBox:
        box = QGroupBox(text("world"))
        grid = QGridLayout(box)
        self.preset_choice = QComboBox()
        for name in PRESETS:
            if name in {"continents", "archipelago"}:
                self.preset_choice.addItem(text(f"preset.{name}"), name)
        self.seed_edit = QLineEdit()
        self.random_button = QPushButton(text("random"))
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText(text("code_hint"))
        self.copy_button = QPushButton(text("copy"))
        self.paste_button = QPushButton(text("paste"))
        self.notice = QLabel()
        self.notice.setWordWrap(True)
        self.notice.setStyleSheet(RED)
        self.install_box = QCheckBox(text("install"))
        grid.addWidget(QLabel(text("preset")), 0, 0)
        grid.addWidget(self.preset_choice, 0, 1, 1, 2)
        grid.addWidget(QLabel(text("seed")), 1, 0)
        grid.addWidget(self.seed_edit, 1, 1)
        grid.addWidget(self.random_button, 1, 2)
        grid.addWidget(QLabel(text("code")), 2, 0)
        grid.addWidget(self.code_edit, 2, 1, 1, 2)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.copy_button)
        buttons.addWidget(self.paste_button)
        grid.addLayout(buttons, 3, 1, 1, 2)
        grid.addWidget(self.notice, 4, 0, 1, 3)
        grid.addWidget(self.install_box, 5, 0, 1, 3)
        grid.setColumnStretch(1, 1)
        _ = self.preset_choice.activated.connect(self._pick_preset)
        _ = self.seed_edit.editingFinished.connect(self._seed_typed)
        _ = self.code_edit.editingFinished.connect(self._code_typed)
        _ = self.random_button.clicked.connect(self.controller.randomize)
        _ = self.copy_button.clicked.connect(self._copy)
        _ = self.paste_button.clicked.connect(self._paste)
        _ = self.install_box.toggled.connect(self._install_toggled)
        return box

    def _buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.generate_button = QPushButton(text("generate"))
        self.generate_button.setDefault(True)
        self.cancel_button = QPushButton(text("cancel"))
        row.addWidget(self.generate_button, 1)
        row.addWidget(self.cancel_button)
        _ = self.generate_button.clicked.connect(self._generate)
        _ = self.cancel_button.clicked.connect(self.controller.cancel)
        return row

    def _history_box(self) -> QGroupBox:
        box = QGroupBox(text("history"))
        layout = QVBoxLayout(box)
        self.history_list = QListWidget()
        self.use_button = QPushButton(text("use_code"))
        layout.addWidget(self.history_list)
        layout.addWidget(self.use_button)
        _ = self.use_button.clicked.connect(self._use_history)
        _ = self.history_list.itemDoubleClicked.connect(self._use_history_item)
        return box

    def _progress_box(self) -> QGroupBox:
        box = QGroupBox(text("progress"))
        layout = QVBoxLayout(box)
        self.bar = QProgressBar()
        self.bar.setRange(0, PROGRESS_STEPS)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.stage_list = QListWidget()
        self.stage_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(self.bar)
        layout.addWidget(self.status)
        layout.addWidget(self.stage_list, 1)
        return box

    def _result_box(self) -> QGroupBox:
        box = QGroupBox(text("preview"))
        layout = QVBoxLayout(box)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(PREVIEW_WIDTH // 2)
        self.outcome = QLabel()
        self.outcome.setWordWrap(True)
        self.next_steps = QLabel()
        self.next_steps.setWordWrap(True)
        self.open_button = QPushButton(text("open_folder"))
        layout.addWidget(self.preview)
        layout.addWidget(self.outcome)
        layout.addWidget(self.next_steps)
        layout.addWidget(self.open_button)
        _ = self.open_button.clicked.connect(self._open_folder)
        return box

    # -- the controller's state, drawn --------------------------------------------------

    def refresh(self) -> None:
        """Make every widget equal to the controller."""
        controller = self.controller
        self._building = True
        try:
            self._refresh_game()
            self._refresh_world()
            self._refresh_progress()
            self._refresh_history()
            self._refresh_result()
        finally:
            self._building = False
        busy = controller.phase in {Phase.RUNNING, Phase.CANCELLING}
        self.generate_button.setEnabled(controller.problem() is None)
        self.cancel_button.setEnabled(controller.phase is Phase.RUNNING)
        for widget in (
            self.game_choice,
            self.game_browse,
            self.profile_choice,
            self.profile_browse,
            self.preset_choice,
            self.seed_edit,
            self.random_button,
            self.code_edit,
            self.paste_button,
            self.install_box,
            self.use_button,
        ):
            widget.setEnabled(not busy)
        free = parallel.available_memory()
        threads = parallel.thread_count()
        self.resources.setText(
            text("resources_unknown", threads=threads)
            if free is None
            else text("resources", threads=threads, free=f"{free / GIB:.1f}")
        )

    def _refresh_game(self) -> None:
        controller = self.controller
        self.game_choice.clear()
        for game in controller.games:
            self.game_choice.addItem(str(game.directory), game)
        if controller.game is not None:
            self.game_choice.setCurrentIndex(max(0, self.game_choice.findData(controller.game)))
        self.build_label.setText(
            text("build", build=controller.game.build_id)
            if controller.game is not None and controller.game.build_id
            else ""
        )
        self.profile_choice.clear()
        for profile in controller.profiles:
            self.profile_choice.addItem(str(profile.directory), profile)
        if controller.profile is not None:
            self.profile_choice.setCurrentIndex(
                max(0, self.profile_choice.findData(controller.profile))
            )
        self.game_problem.setText(
            text("game_missing")
            if controller.game is None
            else text("profile_missing")
            if controller.install and controller.profile is None
            else ""
        )

    def _refresh_world(self) -> None:
        controller = self.controller
        self.preset_choice.setCurrentIndex(max(0, self.preset_choice.findData(controller.preset)))
        if not self.seed_edit.hasFocus():
            self.seed_edit.setText(str(controller.seed))
        if not self.code_edit.hasFocus():
            self.code_edit.setText(controller.code)
        self.notice.setText(controller.notice)
        self.install_box.setChecked(controller.install)

    def _refresh_progress(self) -> None:
        controller = self.controller
        self.bar.setValue(round(controller.fraction * PROGRESS_STEPS))
        self.status.setText(self._status_line())
        self.stage_list.clear()
        for label, state in controller.stage_rows():
            self.stage_list.addItem(QListWidgetItem(f"{MARKS[state]}  {label}"))

    def _status_line(self) -> str:
        controller = self.controller
        match controller.phase:
            case Phase.IDLE:
                return text("idle")
            case Phase.RUNNING:
                return text("running", stages=", ".join(controller.running) or "…")
            case Phase.CANCELLING:
                return text("cancelling")
            case Phase.FINISHED:
                seconds = round(controller.result.seconds) if controller.result else 0
                return text("finished", seconds=seconds)
            case Phase.FAILED:
                return text("failed", message=controller.message)
            case Phase.CANCELLED:
                return text("cancelled")

    def _refresh_history(self) -> None:
        self.history_list.clear()
        for entry in self.controller.history():
            when = datetime.fromtimestamp(entry.when, tz=UTC).strftime("%Y-%m-%d %H:%M")
            outcome = text(f"outcome.{entry.outcome}") if entry.outcome else ""
            item = QListWidgetItem(f"{when}  {outcome}\n{entry.code}")
            item.setData(Qt.ItemDataRole.UserRole, entry.code)
            self.history_list.addItem(item)

    def _refresh_result(self) -> None:
        result = self.controller.result
        if self.controller.phase is not Phase.FINISHED or result is None:
            self.preview.clear()
            self.outcome.setText("")
            self.next_steps.setVisible(False)
            self.open_button.setVisible(False)
            return
        picture = QPixmap(str(result.bundle / "preview.png"))
        if not picture.isNull():
            self.preview.setPixmap(
                picture.scaledToWidth(PREVIEW_WIDTH, Qt.TransformationMode.SmoothTransformation)
            )
        self.outcome.setText(
            text("result_installed", path=result.installed)
            if result.installed is not None
            else text("result_generated", path=result.bundle)
        )
        self.next_steps.setText(self.controller.advice)
        self.next_steps.setVisible(bool(self.controller.advice))
        self.open_button.setVisible(True)

    # -- what the buttons do --------------------------------------------------------------

    def _generate(self) -> None:
        _ = self.controller.start()

    def _seed_typed(self) -> None:
        if self._building:
            return
        problem = self.controller.set_seed(self.seed_edit.text())
        self.notice.setText(problem or self.controller.notice)
        if problem:
            self.seed_edit.setText(str(self.controller.seed))

    def _code_typed(self) -> None:
        if self._building or not self.code_edit.text().strip():
            return
        problem = self.controller.use_code(self.code_edit.text())
        self.notice.setText(problem or self.controller.notice)
        if problem:
            self.code_edit.setText(self.controller.code)

    def _pick_preset(self, index: int) -> None:
        name = cast("object", self.preset_choice.itemData(index))
        if isinstance(name, str):
            self.controller.set_preset(name)

    def _pick_game(self, index: int) -> None:
        if 0 <= index < len(self.controller.games):
            self.controller.game = self.controller.games[index]
            self.refresh()

    def _pick_profile(self, index: int) -> None:
        if 0 <= index < len(self.controller.profiles):
            self.controller.profile = self.controller.profiles[index]
            self.refresh()

    def _browse_game(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, text("game"))
        if folder:
            problem = self.controller.choose_game(Path(folder))
            self.game_problem.setText(problem or "")

    def _browse_profile(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, text("profile"))
        if folder:
            problem = self.controller.choose_profile(Path(folder))
            self.game_problem.setText(problem or "")

    def _install_toggled(self, checked: bool) -> None:  # noqa: FBT001 - Qt's signal argument
        if not self._building:
            self.controller.install = checked
            self.refresh()

    def _copy(self) -> None:
        QApplication.clipboard().setText(self.controller.code)

    def _paste(self) -> None:
        pasted = QApplication.clipboard().text()
        if pasted.strip():
            problem = self.controller.set_seed(pasted)
            self.notice.setText(problem or self.controller.notice)

    def _use_history_item(self, _item: QListWidgetItem) -> None:
        self._use_history()

    def _use_history(self) -> None:
        item = cast("QListWidgetItem | None", self.history_list.currentItem())
        code = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if isinstance(code, str):
            problem = self.controller.use_code(code)
            self.notice.setText(problem or self.controller.notice)

    def _open_folder(self) -> None:
        result = self.controller.result
        if result is not None:
            target = result.installed or result.bundle
            _ = QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    @override
    def closeEvent(self, event: QCloseEvent) -> None:
        """Stop a running generation before the window goes, so nothing is left half written."""
        self.controller.cancel()
        self.controller.wait(CLOSE_WAIT)
        super().closeEvent(event)
