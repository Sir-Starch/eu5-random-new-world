"""The main window: draws the controller's state and forwards the buttons to it.

All rules live in ``rnw.gui.controller`` and ``rnw.app``; this module only creates widgets
and keeps them equal to the controller. Work runs on the controller's thread; its changes
reach the window as a signal, so the window itself never waits. A world's picture shows the
New World covered until the player asks to see it.
"""

# Qt windows are built in helper methods; every widget exists once the constructor returns.
# pyright: reportUninitializedInstanceVariable=false

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast, override

from PySide6.QtCore import QItemSelectionModel, QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices, QFont, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from rnw import __version__, parallel, worldfile, worldname
from rnw import atlas as atlas_module
from rnw.app import controls, diagnostics, discovery, random_types
from rnw.app import quick as quick_settings
from rnw.app.library import Placement
from rnw.gui.candidates import CandidatesDialog
from rnw.gui.controller import NEW, STRAY, Controller, Phase, Task
from rnw.gui.maps import CompareDialog, MapsPanel
from rnw.gui.preview import PreviewView
from rnw.gui.text import LANGUAGE_NAMES, TITLE, grouped, text
from rnw.gui.theme import install as install_theme
from rnw.languages import SOURCE

if TYPE_CHECKING:
    from PySide6.QtGui import QDragEnterEvent, QDropEvent

    from rnw.app.library import World

GIB: Final[float] = float(1 << 30)
PROGRESS_STEPS: Final[int] = 100
MARKS: Final[dict[str, str]] = {"done": "✓", "running": "▶", "waiting": "·"}
CLOSE_WAIT: Final[float] = 15.0
RED: Final[str] = "color: #b00020;"
MUTED: Final[str] = ""
ICON_SIZE: Final[tuple[int, int]] = (96, 48)
DATE: Final[str] = "%Y-%m-%d %H:%M"
# Before the name of a version of a continent already listed above it.
VERSION_MARK: Final[str] = "\u21b3 "


def _progress_percent(fraction: float) -> int:
    """The one rounded percentage used by the progress bar and world list."""
    return min(100, max(0, math.floor(fraction * 100 + 0.5)))


def _duration_clock(seconds: float) -> str:
    """A compact, language-neutral countdown for the ETA line."""
    total = max(1, math.ceil(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, seconds_left = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds_left:02d}" if hours else f"{minutes}:{seconds_left:02d}"


class _Bridge(QObject):
    """Carries 'something changed' from the work thread to the window's thread."""

    changed: Signal = Signal()


def _problem_label() -> QLabel:
    label = QLabel()
    label.setStyleSheet(RED)
    label.setWordWrap(True)
    label.setVisible(False)
    return label


class SettingsDialog(QDialog):
    """The game, the profile and the choice of showing the New World in the mod list."""

    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.window_: MainWindow = window
        controller = window.controller
        self.setWindowTitle(text("settings_title"))
        layout = QVBoxLayout(self)
        grid = QGridLayout()
        self.game_choice: QComboBox = QComboBox()
        for game in controller.games:
            self.game_choice.addItem(str(game.directory), game)
        if controller.game is not None:
            self.game_choice.setCurrentIndex(max(0, self.game_choice.findData(controller.game)))
        self.profile_choice: QComboBox = QComboBox()
        for profile in controller.profiles:
            self.profile_choice.addItem(str(profile.directory), profile)
        if controller.profile is not None:
            self.profile_choice.setCurrentIndex(
                max(0, self.profile_choice.findData(controller.profile))
            )
        game_browse, profile_browse = QPushButton(text("browse")), QPushButton(text("browse"))
        self.problem: QLabel = _problem_label()
        grid.addWidget(QLabel(text("game")), 0, 0)
        grid.addWidget(self.game_choice, 0, 1)
        grid.addWidget(game_browse, 0, 2)
        grid.addWidget(QLabel(text("profile")), 1, 0)
        grid.addWidget(self.profile_choice, 1, 1)
        grid.addWidget(profile_browse, 1, 2)
        grid.addWidget(QLabel(text("language")), 2, 0)
        grid.addWidget(self._language_choice(), 2, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        layout.addWidget(self.language_note)
        layout.addWidget(self.problem)
        for choice in (self.game_choice, self.profile_choice):
            choice.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            choice.setMinimumContentsLength(24)
            choice.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            choice.setToolTip(choice.currentText())
            _ = choice.currentTextChanged.connect(choice.setToolTip)
        about = QLabel(text("about_generator"))
        about.setWordWrap(True)
        layout.addWidget(about)
        layout.addWidget(self._diagnostics_button(), alignment=Qt.AlignmentFlag.AlignLeft)
        close = QPushButton(text("close"))
        close.setDefault(True)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        _ = game_browse.clicked.connect(self._browse_game)
        _ = profile_browse.clicked.connect(self._browse_profile)
        _ = self.game_choice.activated.connect(self._pick_game)
        _ = self.profile_choice.activated.connect(self._pick_profile)
        _ = close.clicked.connect(self.accept)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        self.resize(760, self.sizeHint().height())

    def _language_choice(self) -> QComboBox:
        """The window's language: as the game's, or one of the official languages by name."""
        controller = self.window_.controller
        choice = QComboBox()
        game = discovery.game_language(controller.game) if controller.game is not None else None
        automatic = LANGUAGE_NAMES.get(game or "", LANGUAGE_NAMES[SOURCE])
        choice.addItem(text("language.game", language=automatic), "")
        for key, name in LANGUAGE_NAMES.items():
            choice.addItem(name, key)
        choice.setCurrentIndex(max(0, choice.findData(controller.preferences.language)))
        self.language_note: QLabel = QLabel()
        self.language_note.setWordWrap(True)
        self.language_note.setVisible(False)

        def picked(index: int) -> None:
            value = cast("object", choice.itemData(index))
            controller.set_language(value if isinstance(value, str) else "")
            self.language_note.setText(text("language.restart"))
            self.language_note.setVisible(True)

        _ = choice.activated.connect(picked)
        return choice

    def _pick_game(self, index: int) -> None:
        controller = self.window_.controller
        if 0 <= index < len(controller.games):
            controller.game = controller.games[index]
            self.window_.refresh()

    def _pick_profile(self, index: int) -> None:
        controller = self.window_.controller
        if 0 <= index < len(controller.profiles):
            controller.profile = controller.profiles[index]
            controller.refresh_library()

    def _diagnostics_button(self) -> QPushButton:
        button = QPushButton(text("diagnostics"))
        button.setToolTip(text("diagnostics_tip"))
        _ = button.clicked.connect(self._save_diagnostics)
        return button

    def _save_diagnostics(self) -> None:
        stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M")
        suggested = str(Path.home() / diagnostics.default_name(stamp))
        chosen, _ = QFileDialog.getSaveFileName(
            self, text("diagnostics_title"), suggested, "Zip (*.zip)"
        )
        if not chosen:
            return
        problem = self.window_.controller.save_diagnostics(Path(chosen))
        message = problem or text("diagnostics_saved", path=chosen)
        if problem:
            _ = QMessageBox.warning(self, text("diagnostics_title"), message)
        else:
            _ = QMessageBox.information(self, text("diagnostics_title"), message)

    def _browse_game(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, text("game"))
        if folder:
            problem = self.window_.controller.choose_game(Path(folder))
            self.problem.setText(problem or "")
            self.problem.setVisible(problem is not None)
            if problem is None:
                self.game_choice.insertItem(0, folder)
                self.game_choice.setCurrentIndex(0)

    def _browse_profile(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, text("profile"))
        if folder:
            problem = self.window_.controller.choose_profile(Path(folder))
            self.problem.setText(problem or "")
            self.problem.setVisible(problem is not None)
            if problem is None:
                self.profile_choice.insertItem(0, folder)
                self.profile_choice.setCurrentIndex(0)


class _ControlRow:
    """One setting: its name, a slider, the value in its unit and a reset button."""

    def __init__(self, control: controls.Control, window: MainWindow) -> None:
        self.control: controls.Control = control
        self.window: MainWindow = window
        about = text(f"control.{control.key}.about")
        self.label: QLabel = QLabel(text(f"control.{control.key}"))
        self.label.setToolTip(about)
        self.slider: QSlider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, controls.STEPS)
        self.slider.setToolTip(about)
        self.number: QDoubleSpinBox = QDoubleSpinBox()
        self.number.setDecimals(control.decimals)
        self.number.setRange(control.shown(control.low), control.shown(control.high))
        self.number.setSingleStep(math.pow(10, -control.decimals))
        self.number.setSuffix(text(f"unit.{control.unit}"))
        self.number.setKeyboardTracking(False)
        self.number.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.number.setMinimumWidth(90)
        self.reset: QToolButton = QToolButton()
        self.reset.setText(text("reset"))
        _ = self.slider.valueChanged.connect(self._slid)
        _ = self.number.valueChanged.connect(self._typed)
        _ = self.reset.clicked.connect(self._reset)

    def place(self, grid: QGridLayout, row: int) -> None:
        """Put the row's widgets into ``grid``."""
        grid.addWidget(self.label, row, 0)
        grid.addWidget(self.slider, row, 1)
        grid.addWidget(self.number, row, 2)
        grid.addWidget(self.reset, row, 3)

    def refresh(self, value: int, *, changed: bool, enabled: bool) -> None:
        """Show ``value``; mark a value changed from the world type."""
        _ = self.slider.blockSignals(True)  # noqa: FBT003 - Qt's own call
        _ = self.number.blockSignals(True)  # noqa: FBT003 - Qt's own call
        self.slider.setValue(self.control.position(value))
        self.number.setValue(self.control.shown(value))
        _ = self.slider.blockSignals(False)  # noqa: FBT003 - Qt's own call
        _ = self.number.blockSignals(False)  # noqa: FBT003 - Qt's own call
        font = self.label.font()
        font.setBold(changed)
        self.label.setFont(font)
        self.reset.setEnabled(changed and enabled)
        for widget in (self.slider, self.number):
            widget.setEnabled(enabled)

    def _slid(self, position: int) -> None:
        self.window.controller.set_value(self.control.key, self.control.value_at(position))

    def _typed(self, shown: float) -> None:
        self.window.controller.set_value(self.control.key, self.control.stored(shown))

    def _reset(self) -> None:
        self.window.controller.reset_value(self.control.key)


class _QuickRow:
    """One quick setting: its name and a button for each level; none is down when custom."""

    def __init__(self, quick: quick_settings.Quick, window: MainWindow) -> None:
        self.quick: quick_settings.Quick = quick
        self.window: MainWindow = window
        about = text(f"quick.{quick.name}.about")
        self.label: QLabel = QLabel(text(f"quick.{quick.name}"))
        self.label.setToolTip(about)
        self.buttons: dict[str, QPushButton] = {}
        self.custom: QLabel = QLabel(text("quick.custom"))
        self.custom.setStyleSheet(MUTED)
        for level in quick.levels:
            button = QPushButton(text(f"quick.{quick.name}.{level.name}"))
            button.setCheckable(True)
            button.setToolTip(about)
            _ = button.clicked.connect(lambda _checked=False, name=level.name: self._pick(name))
            self.buttons[level.name] = button

    def place(self, grid: QGridLayout, row: int) -> None:
        """Put the row's widgets into ``grid``."""
        grid.addWidget(self.label, row, 0)
        levels = QHBoxLayout()
        for button in self.buttons.values():
            levels.addWidget(button)
        levels.addWidget(self.custom)
        levels.addStretch(1)
        grid.addLayout(levels, row, 1)

    def refresh(self, level: str | None, *, enabled: bool) -> None:
        """Press the button of ``level``; none when the controls hold a custom mix."""
        for name, button in self.buttons.items():
            _ = button.blockSignals(True)  # noqa: FBT003 - Qt's own call
            button.setChecked(name == level)
            _ = button.blockSignals(False)  # noqa: FBT003 - Qt's own call
            button.setEnabled(enabled)
        self.custom.setVisible(level is None)

    def _pick(self, level: str) -> None:
        self.window.controller.set_quick(self.quick.name, level)


class MainWindow(QMainWindow):
    """The generator's window: a list of worlds and the page of the one selected."""

    game_line: QLabel
    problem_line: QLabel
    settings_button: QPushButton
    world_list: QListWidget
    stack: QStackedWidget
    resources: QLabel
    # the new world
    new_page: QWidget
    type_choice: QComboBox
    type_about: QLabel
    seed_edit: QLineEdit
    random_button: QPushButton
    code_edit: QLineEdit
    copy_button: QPushButton
    paste_button: QPushButton
    notice: QLabel
    land_image_button: QPushButton
    land_image_label: QLabel
    land_image_clear: QPushButton
    land_template_button: QPushButton
    customize_button: QToolButton
    customize_box: QWidget
    customized: QLabel
    reset_all: QPushButton
    estimate: QLabel
    install_box: QCheckBox
    generate_button: QPushButton
    cancel_button: QPushButton
    bar: QProgressBar
    status: QLabel
    eta: QLabel
    stage_list: QListWidget
    # a world
    world_page: QWidget
    name_edit: QLineEdit
    preview: PreviewView
    preview_caption: QLabel
    details: dict[str, QLabel]
    copy_code_button: QPushButton
    note: QLabel
    advice: QLabel
    add_button: QPushButton
    remove_button: QPushButton
    open_button: QPushButton
    like_button: QPushButton
    world_notice: QLabel
    export_button: QPushButton
    send_button: QPushButton
    copy_mod_button: QPushButton
    open_file_button: QPushButton
    peoples_button: QPushButton
    resources_button: QPushButton
    edit_button: QPushButton
    parent_button: QPushButton
    keep_both: QCheckBox
    check_button: QPushButton
    save_button: QPushButton
    compare_button: QPushButton
    world_tabs: QTabWidget
    maps: MapsPanel
    delete_button: QPushButton
    task_line: QLabel
    task_bar: QProgressBar
    # a stray
    stray_page: QWidget
    stray_about: QLabel
    stray_remove: QPushButton
    stray_open: QPushButton

    def __init__(self, controller: Controller) -> None:
        application = QApplication.instance()
        if isinstance(application, QApplication):
            install_theme(application)
        super().__init__()
        self.controller: Controller = controller
        self._bridge: _Bridge = _Bridge()
        self._list_key: tuple[str, ...] = ()
        self._shown_world: str = ""
        self._reported: int = 0
        self._sketched: int = 0
        self.candidates_dialog: CandidatesDialog | None = None
        self.rows: list[_ControlRow] = []
        self.quick_rows: list[_QuickRow] = []
        self.setWindowTitle(TITLE)
        self.setAcceptDrops(True)
        self._build()
        self._eta_timer: QTimer = QTimer(self)
        self._eta_timer.setInterval(1000)
        _ = self._eta_timer.timeout.connect(self._refresh_eta)
        _ = self._bridge.changed.connect(self.refresh)
        controller.subscribe(self._bridge.changed.emit)
        self.refresh()

    # -- construction ---------------------------------------------------------------------------

    def _build(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addLayout(self._header())
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._library_panel())
        self.stack = QStackedWidget()
        self.new_page = self._new_page()
        self.world_page = self._world_page()
        self.stray_page = self._stray_page()
        for page in (self.new_page, self.world_page, self.stray_page):
            _ = self.stack.addWidget(page)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([250, 950])
        layout.addWidget(splitter, 1)
        self.setCentralWidget(root)
        self.resources = QLabel()
        status = self.statusBar()
        status.addPermanentWidget(QLabel(f"v{__version__}"))
        status.addWidget(self.resources)

    def _library_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        self.select_all_button: QPushButton = QPushButton(text("select_all_worlds"))
        _ = self.select_all_button.clicked.connect(self._select_all_worlds)
        layout.addWidget(self.select_all_button)
        self.world_list = QListWidget()
        self.world_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.world_list.setIconSize(QPixmap(*ICON_SIZE).size())
        self.world_list.setMinimumWidth(220)
        self.world_list.setWordWrap(True)
        self.world_list.setToolTip(text("selection_hint"))
        _ = self.world_list.currentItemChanged.connect(self._picked)
        _ = self.world_list.itemSelectionChanged.connect(self._refresh_selection)
        layout.addWidget(self.world_list, 1)
        hint = QLabel(text("selection_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        # The splitter gives the panel its width: no text in it may set a minimum.
        self.selection_label: QLabel = QLabel()
        self.selection_label.setWordWrap(True)
        layout.addWidget(self.selection_label)
        self.library_remove: QPushButton = QPushButton()
        _ = self.library_remove.clicked.connect(self._remove_entries)
        layout.addWidget(self.library_remove)
        self.library_delete: QPushButton = QPushButton()
        _ = self.library_delete.clicked.connect(self._delete_entries)
        layout.addWidget(self.library_delete)
        self.library_status: QLabel = QLabel()
        self.library_status.setWordWrap(True)
        # An error names a path, one unbreakable word that would widen the whole window.
        self.library_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.library_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.library_status)
        return panel

    def _header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        lines = QVBoxLayout()
        self.game_line = QLabel()
        self.game_line.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.problem_line = QLabel()
        self.problem_line.setStyleSheet(RED)
        self.problem_line.setWordWrap(True)
        lines.addWidget(self.game_line)
        lines.addWidget(self.problem_line)
        row.addLayout(lines, 1)
        self.open_file_button = QPushButton(text("open_world_file"))
        self.open_file_button.setToolTip(text("open_world_file_tip"))
        _ = self.open_file_button.clicked.connect(self._open_world_file)
        row.addWidget(self.open_file_button, alignment=Qt.AlignmentFlag.AlignTop)
        self.settings_button = QPushButton(text("settings"))
        _ = self.settings_button.clicked.connect(self._settings)
        row.addWidget(self.settings_button, alignment=Qt.AlignmentFlag.AlignTop)
        return row

    def _new_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        self.new_tabs: QTabWidget = QTabWidget()
        outer.addWidget(self.new_tabs, 1)
        _ = self.new_tabs.addTab(self._new_world_tab(), text("new_tab.world"))
        _ = self.new_tabs.addTab(self._advanced_tab(), text("new_tab.advanced"))
        _ = self.new_tabs.addTab(self._delivery_tab(), text("new_tab.output"))
        self.notice = QLabel()
        self.notice.setWordWrap(True)
        self.notice.setStyleSheet(RED)
        outer.addWidget(self.notice)
        self.estimate = QLabel()
        self.estimate.setWordWrap(True)
        row = QHBoxLayout()
        row.addWidget(self.estimate, 1)
        self.generate_button = QPushButton(text("generate"))
        self.generate_button.setDefault(True)
        self.generate_button.setMinimumWidth(160)
        self.cancel_button = QPushButton(text("cancel"))
        row.addWidget(self.generate_button)
        row.addWidget(self.cancel_button)
        outer.addLayout(row)
        self.generation_hint: QLabel = QLabel()
        self.generation_hint.setWordWrap(True)
        outer.addWidget(self.generation_hint)
        self.progress_box: QGroupBox = self._progress()
        outer.addWidget(self.progress_box)
        _ = self.seed_edit.editingFinished.connect(self._seed_typed)
        _ = self.code_edit.editingFinished.connect(self._code_typed)
        _ = self.random_button.clicked.connect(self.controller.randomize)
        _ = self.copy_button.clicked.connect(self._copy)
        _ = self.paste_button.clicked.connect(self._paste)
        _ = self.install_box.toggled.connect(self._install_toggled)
        _ = self.show_new_world.toggled.connect(self.controller.set_show_new_world)
        _ = self.generate_button.clicked.connect(self._generate)
        _ = self.cancel_button.clicked.connect(self.controller.cancel)
        return page

    def _new_world_tab(self) -> QScrollArea:
        world, layout = self._scroll_page()
        layout.addWidget(self._types())
        layout.addWidget(self._quick())
        self.expand_oceans: QCheckBox = QCheckBox(text("control.new_world.expand_oceans"))
        self.expand_oceans.setChecked(bool(self.controller.value("new_world.expand_oceans")))
        self.expand_oceans.setToolTip(text("control.new_world.expand_oceans.about"))
        _ = self.expand_oceans.toggled.connect(self._ocean_toggled)
        layout.addWidget(self.expand_oceans)
        ocean_hint = QLabel(text("control.new_world.expand_oceans.about"))
        ocean_hint.setWordWrap(True)
        ocean_hint.setStyleSheet(MUTED)
        layout.addWidget(ocean_hint)
        self.show_new_world: QCheckBox = QCheckBox(text("show_new_world"))
        self.show_new_world.setChecked(self.controller.preferences.show_new_world)
        visibility = QGroupBox(text("visibility"))
        visibility_layout = QVBoxLayout(visibility)
        visibility_layout.addWidget(self.show_new_world)
        hint = QLabel(text("show_new_world_hint"))
        hint.setWordWrap(True)
        visibility_layout.addWidget(hint)
        layout.addWidget(visibility)
        layout.addStretch(1)
        return world

    def _advanced_tab(self) -> QScrollArea:
        advanced, advanced_layout = self._scroll_page()
        identity = QGroupBox(text("world_identity"))
        identity_layout = QVBoxLayout(identity)
        identity_layout.addLayout(self._seed_and_code())
        advanced_layout.addWidget(identity)
        land = QGroupBox(text("land_tools"))
        land_layout = QVBoxLayout(land)
        land_layout.addLayout(self._land_image_row())
        land_layout.addLayout(self._candidate_row())
        advanced_layout.addWidget(land)
        advanced_layout.addWidget(self._customize())
        advanced_layout.addStretch(1)
        return advanced

    def _delivery_tab(self) -> QScrollArea:
        delivery, delivery_layout = self._scroll_page()
        output = QGroupBox(text("output"))
        output_layout = QVBoxLayout(output)
        output_layout.addLayout(self._destination_row())
        self.install_box = QCheckBox(text("install"))
        output_layout.addWidget(self.install_box)
        output_hint = QLabel(text("output_hint"))
        output_hint.setWordWrap(True)
        output_layout.addWidget(output_hint)
        delivery_layout.addWidget(output)
        queue = QGroupBox(text("queue_title"))
        queue_layout = QVBoxLayout(queue)
        queue_hint = QLabel(text("queue_hint"))
        queue_hint.setWordWrap(True)
        queue_layout.addWidget(queue_hint)
        queue_layout.addLayout(self._queue_row())
        delivery_layout.addWidget(queue)
        delivery_layout.addStretch(1)
        return delivery

    @staticmethod
    def _scroll_page() -> tuple[QScrollArea, QVBoxLayout]:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        scroll.setWidget(body)
        return scroll, layout

    def _destination_row(self) -> QHBoxLayout:
        destination = QHBoxLayout()
        self.destination: QComboBox = QComboBox()
        self.destination.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for key in ("library", "mod", "world"):
            self.destination.addItem(text(f"destination.{key}"), key)
        self.destination_path: QLineEdit = QLineEdit()
        self.destination_path.setReadOnly(True)
        self.destination_button: QPushButton = QPushButton(text("destination_choose"))
        destination.addWidget(self.destination)
        destination.addWidget(self.destination_path, 1)
        destination.addWidget(self.destination_button)
        _ = self.destination.currentIndexChanged.connect(self._destination_changed)
        _ = self.destination_button.clicked.connect(self._choose_destination)
        return destination

    def _destination_changed(self, _index: int) -> None:
        controller = self.controller
        controller.output_folder, controller.world_file = None, None
        if self.destination.currentData() != "library":
            self.install_box.setChecked(False)
        self.destination_path.clear()
        self.refresh()

    def _choose_destination(self) -> None:
        kind = str(self.destination.currentIndex())
        if kind == "1":
            chosen = QFileDialog.getExistingDirectory(self, text("destination_choose"))
            if chosen:
                self.controller.output_folder = Path(chosen)
        elif kind == "2":
            chosen, _ = QFileDialog.getSaveFileName(
                self, text("export_file"), "world.rnworld", "World (*.rnworld)"
            )
            if chosen:
                self.controller.world_file = Path(chosen)
        self.refresh()

    def _candidate_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.candidates_button: QPushButton = QPushButton(text("candidates"))
        self.candidates_button.setToolTip(text("candidates_hint"))
        _ = self.candidates_button.clicked.connect(self._sketch)
        row.addWidget(self.candidates_button)
        row.addStretch(1)
        return row

    def _queue_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.enqueue_button: QPushButton = QPushButton(text("enqueue"))
        self.run_queue_button: QPushButton = QPushButton(text("run_queue"))
        self.clear_queue_button: QPushButton = QPushButton(text("clear_queue"))
        self.queue_label: QLabel = QLabel()
        for widget in (
            self.enqueue_button,
            self.run_queue_button,
            self.clear_queue_button,
            self.queue_label,
        ):
            row.addWidget(widget)
        row.addStretch(1)
        _ = self.enqueue_button.clicked.connect(self._enqueue)
        _ = self.run_queue_button.clicked.connect(self._run_queue)
        _ = self.clear_queue_button.clicked.connect(self.controller.clear_queue)
        return row

    def _sketch(self) -> None:
        problem = self.controller.sketch_candidates()
        if problem:
            self.status.setText(problem)

    def _enqueue(self) -> None:
        problem = self.controller.enqueue()
        if problem:
            self.status.setText(problem)

    def _run_queue(self) -> None:
        problem = self.controller.start_queue()
        if problem:
            self.status.setText(problem)

    def _land_image_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.land_image_button = QPushButton(text("land_image"))
        self.land_image_button.setToolTip(text("land_image_tip"))
        self.land_image_label = QLabel()
        self.land_image_label.setStyleSheet(MUTED)
        self.land_image_clear = QPushButton(text("land_image_clear"))
        self.land_template_button = QPushButton(text("land_template"))
        self.land_template_button.setToolTip(text("land_template_tip"))
        for widget in (
            self.land_image_button,
            self.land_template_button,
            self.land_image_label,
            self.land_image_clear,
        ):
            row.addWidget(widget)
        row.addStretch(1)
        _ = self.land_template_button.clicked.connect(self._save_land_template)
        _ = self.land_image_button.clicked.connect(self._choose_land_image)
        _ = self.land_image_clear.clicked.connect(self.controller.clear_land_image)
        return row

    def _save_land_template(self) -> None:
        title = text("land_template")
        chosen, _ = QFileDialog.getSaveFileName(
            self, title, str(Path.home() / "new-world-template.png"), "PNG (*.png)"
        )
        if chosen:
            problem = self.controller.save_land_template(Path(chosen))
            if problem:
                _ = QMessageBox.warning(self, title, problem)

    def _choose_land_image(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(
            self, text("land_image_title"), str(Path.home()), text("land_image_files")
        )
        if chosen:
            problem = self.controller.choose_land_image(Path(chosen))
            if problem:
                _ = QMessageBox.warning(self, text("land_image"), problem)

    def _seed_and_code(self) -> QGridLayout:
        world = QGridLayout()
        self.seed_edit = QLineEdit()
        self.random_button = QPushButton(text("random"))
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText(text("code_hint"))
        self.copy_button = QPushButton(text("copy"))
        self.paste_button = QPushButton(text("paste"))
        world.addWidget(QLabel(text("seed")), 0, 0)
        world.addWidget(self.seed_edit, 0, 1)
        world.addWidget(self.random_button, 0, 2)
        world.addWidget(QLabel(text("code")), 1, 0)
        world.addWidget(self.code_edit, 1, 1)
        buttons = QHBoxLayout()
        buttons.addWidget(self.copy_button)
        buttons.addWidget(self.paste_button)
        world.addLayout(buttons, 1, 2)
        world.setColumnStretch(1, 1)
        return world

    def _types(self) -> QGroupBox:
        types = QGroupBox(text("type"))
        layout = QVBoxLayout(types)
        self.type_choice = QComboBox()
        for name in random_types.CHOICES:
            self.type_choice.addItem(text(f"type.{name}"), name)
        self.type_about = QLabel()
        self.type_about.setWordWrap(True)
        layout.addWidget(self.type_choice)
        layout.addWidget(self.type_about)
        _ = self.type_choice.currentIndexChanged.connect(self._pick_type)
        return types

    def _quick(self) -> QGroupBox:
        box = QGroupBox(text("quick"))
        grid = QGridLayout(box)
        hint = QLabel(text("quick_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(MUTED)
        grid.addWidget(hint, 0, 0, 1, 2)
        for row, setting in enumerate(quick_settings.QUICK, start=1):
            line = _QuickRow(setting, self)
            line.place(grid, row)
            self.quick_rows.append(line)
        grid.setColumnStretch(1, 1)
        return box

    def _progress(self) -> QGroupBox:
        progress = QGroupBox(text("progress"))
        progress_layout = QVBoxLayout(progress)
        self.bar = QProgressBar()
        self.bar.setRange(0, PROGRESS_STEPS)
        self.status = QLabel()
        self.status.setWordWrap(False)
        self.status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.status.setFixedHeight(self.status.fontMetrics().height() + 4)
        self.eta = QLabel()
        self.eta.setWordWrap(False)
        self.eta.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.eta.setFixedHeight(self.eta.fontMetrics().height() + 4)
        self.stage_list = QListWidget()
        self.stage_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.stage_list.setFixedHeight(140)
        self.progress_details: QToolButton = QToolButton()
        self.progress_details.setText(text("progress_details"))
        self.progress_details.setCheckable(True)
        self.progress_details.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.progress_details.setArrowType(Qt.ArrowType.RightArrow)
        progress_layout.addWidget(self.bar)
        progress_layout.addWidget(self.status)
        progress_layout.addWidget(self.eta)
        progress_layout.addWidget(self.progress_details, alignment=Qt.AlignmentFlag.AlignLeft)
        progress_layout.addWidget(self.stage_list)
        self.stage_list.setVisible(False)
        _ = self.progress_details.toggled.connect(self._toggle_progress_details)
        return progress

    def _toggle_progress_details(self, checked: bool) -> None:  # noqa: FBT001 - Qt signal
        self.stage_list.setVisible(checked)
        self.progress_details.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )

    def _customize(self) -> QWidget:
        holder = QWidget()
        layout = QVBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        head = QHBoxLayout()
        self.customize_button = QToolButton()
        self.customize_button.setText(text("customize"))
        self.customize_button.setCheckable(True)
        self.customize_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.customize_button.setArrowType(Qt.ArrowType.RightArrow)
        self.customized = QLabel()
        self.customized.setStyleSheet(MUTED)
        head.addWidget(self.customize_button)
        head.addWidget(self.customized, 1)
        layout.addLayout(head)
        self.customize_box = QWidget()
        box = QVBoxLayout(self.customize_box)
        hint = QLabel(text("customize_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(MUTED)
        box.addWidget(hint)
        for group in controls.GROUPS:
            section = QGroupBox(text(f"group.{group}"))
            grid = QGridLayout(section)
            grid.setColumnStretch(1, 1)
            for row, control in enumerate(c for c in controls.ADVANCED if c.group == group):
                line = _ControlRow(control, self)
                line.place(grid, row)
                self.rows.append(line)
            box.addWidget(section)
        self.reset_all = QPushButton(text("reset_all"))
        _ = self.reset_all.clicked.connect(self.controller.reset_values)
        box.addWidget(self.reset_all, alignment=Qt.AlignmentFlag.AlignLeft)
        self.customize_box.setVisible(False)
        layout.addWidget(self.customize_box)
        _ = self.customize_button.toggled.connect(self._toggle_customize)
        return holder

    def _world_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(text("name_hint", limit=worldname.MAX_NAME))
        self.name_edit.setMaxLength(worldname.MAX_NAME)
        font = QFont(self.name_edit.font())
        font.setPointSizeF(font.pointSizeF() * 1.4)
        font.setBold(True)
        self.name_edit.setFont(font)
        self.name_edit.setFrame(False)
        layout.addWidget(self.name_edit)
        self.world_tabs = QTabWidget()
        layout.addWidget(self.world_tabs, 1)
        self.world_notice = QLabel()
        self.world_notice.setWordWrap(True)
        self.world_notice.setStyleSheet(RED)
        self.world_notice.setVisible(False)
        layout.addWidget(self.world_notice)
        _ = self.world_tabs.addTab(self._overview_page(), text("tab.world"))
        self.maps = MapsPanel()
        _ = self.world_tabs.addTab(self.maps, text("tab.maps"))
        _ = self.world_tabs.addTab(self._notes_page(), text("tab.notes"))
        _ = self.world_tabs.addTab(self._tools_page(), text("tab.tools"))
        self.task_line = QLabel()
        self.task_line.setWordWrap(True)
        self.task_bar = QProgressBar()
        self.task_bar.setRange(0, PROGRESS_STEPS)
        layout.addWidget(self.task_line)
        layout.addWidget(self.task_bar)
        self._connect_world_page()
        return page

    def _overview_page(self) -> QScrollArea:
        overview = QScrollArea()
        overview.setWidgetResizable(True)
        overview.setFrameShape(QFrame.Shape.NoFrame)
        overview_body = QWidget()
        overview.setWidget(overview_body)
        inner = QVBoxLayout(overview_body)
        self.preview = PreviewView()
        self.preview.setMaximumHeight(280)
        inner.addWidget(self.preview, 3)
        self.preview_caption = QLabel()
        self.preview_caption.setWordWrap(True)
        self.preview_caption.setStyleSheet(MUTED)
        inner.addWidget(self.preview_caption)
        self.world_visibility: QCheckBox = QCheckBox(text("show_new_world"))
        self.world_visibility.setToolTip(text("world_visibility_hint"))
        _ = self.world_visibility.toggled.connect(self._world_visibility_changed)
        inner.addWidget(self.world_visibility)
        self.visibility_hint: QLabel = QLabel(text("world_visibility_hint"))
        self.visibility_hint.setWordWrap(True)
        inner.addWidget(self.visibility_hint)
        inner.addLayout(self._world_buttons())
        self.note = QLabel()
        self.note.setWordWrap(True)
        inner.addWidget(self.note)
        self.advice = QLabel()
        self.advice.setWordWrap(True)
        self.advice.setFrameShape(QFrame.Shape.StyledPanel)
        self.advice.setMargin(8)
        inner.addWidget(self.advice)
        return overview

    def _world_visibility_changed(self, checked: bool) -> None:  # noqa: FBT001 - Qt signal
        world = self.controller.selected_world()
        if world is not None:
            problem = self.controller.set_world_visibility(world, show=checked)
            # Refresh first: showing a world that was not shown yet clears the notice.
            self.refresh()
            self._tell(problem or text("visibility_updated"))

    def _tools_page(self) -> QScrollArea:
        page, layout = self._scroll_page()
        versions = QGroupBox(text("world_versions"))
        versions_layout = QVBoxLayout(versions)
        versions_layout.addLayout(self._version_buttons())
        layout.addWidget(versions)
        files = QGroupBox(text("world_share"))
        files_layout = QVBoxLayout(files)
        files_layout.addLayout(self._file_buttons())
        layout.addWidget(files)
        details = QGroupBox(text("world_details"))
        details_layout = QVBoxLayout(details)
        details_layout.addLayout(self._details())
        self.check_button = QPushButton(text("check"))
        self.check_button.setToolTip(text("check_tip"))
        details_layout.addWidget(self.check_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(details)
        self.delete_button = QPushButton(text("delete"))
        layout.addWidget(self.delete_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addStretch(1)
        return page

    def _notes_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.starred_box: QCheckBox = QCheckBox(text("starred"))
        self.user_tag_edit: QLineEdit = QLineEdit()
        self.user_tag_edit.setMaxLength(64)
        self.user_tag_edit.setPlaceholderText(text("user_tag"))
        self.notes_edit: QPlainTextEdit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText(text("notes_hint"))
        self.save_notes_button: QPushButton = QPushButton(text("save_notes"))
        _ = self.save_notes_button.clicked.connect(self._save_notes)
        for widget in (
            self.starred_box,
            self.user_tag_edit,
            self.notes_edit,
            self.save_notes_button,
        ):
            layout.addWidget(widget)
        return page

    def _save_notes(self) -> None:
        world = self.controller.selected_world()
        if world is not None:
            self.controller.annotate(
                world,
                self.notes_edit.toPlainText(),
                self.user_tag_edit.text(),
                starred=self.starred_box.isChecked(),
            )
            self._tell(text("notes_saved"))

    def _connect_world_page(self) -> None:
        _ = self.name_edit.editingFinished.connect(self._renamed)
        _ = self.copy_code_button.clicked.connect(self._copy_world_code)
        _ = self.add_button.clicked.connect(self._add)
        _ = self.remove_button.clicked.connect(self._remove)
        _ = self.open_button.clicked.connect(self._open_world)
        _ = self.like_button.clicked.connect(self._like)
        _ = self.check_button.clicked.connect(self._check)
        _ = self.delete_button.clicked.connect(self._delete)
        _ = self.maps.reveal_requested.connect(self._reveal)
        _ = self.save_button.clicked.connect(self._save_picture)
        _ = self.compare_button.clicked.connect(self._compare)

    def _details(self) -> QFormLayout:
        form = QFormLayout()
        self.details = {}
        for key in (
            "code",
            "type",
            "seed",
            "custom",
            "made",
            "build",
            "generator",
            "place",
            "reproduce",
        ):
            label = QLabel()
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.details[key] = label
            if key == "code":
                row = QHBoxLayout()
                row.addWidget(label, 1)
                self.copy_code_button = QPushButton(text("copy_code"))
                row.addWidget(self.copy_code_button)
                form.addRow(text(f"detail.{key}"), row)
            else:
                form.addRow(text(f"detail.{key}"), label)
        return form

    def _world_buttons(self) -> QGridLayout:
        buttons = QGridLayout()
        self.add_button = QPushButton(text("add"))
        self.remove_button = QPushButton(text("remove"))
        self.open_button = QPushButton(text("open_folder"))
        self.save_button = QPushButton(text("save_picture"))
        self.save_button.setToolTip(text("save_picture_tip"))
        self.compare_button = QPushButton(text("compare"))
        buttons.addWidget(self.add_button, 0, 0)
        buttons.addWidget(self.remove_button, 0, 0)
        buttons.addWidget(self.open_button, 0, 1)
        buttons.addWidget(self.save_button, 1, 0)
        buttons.addWidget(self.compare_button, 1, 1)
        return buttons

    def _version_buttons(self) -> QGridLayout:
        row = QGridLayout()
        self.like_button = QPushButton(text("like_this"))
        self.peoples_button = QPushButton(text("part.peoples.button"))
        self.resources_button = QPushButton(text("part.resources.button"))
        self.edit_button = QPushButton(text("edit_same_land"))
        self.parent_button = QPushButton(text("previous_version"))
        self.undo_button: QPushButton = QPushButton(text("undo_roll"))
        self.keep_both = QCheckBox(text("keep_both"))
        self.peoples_button.setToolTip(text("part.peoples.tip"))
        self.resources_button.setToolTip(text("part.resources.tip"))
        self.edit_button.setToolTip(text("edit_same_land_tip"))
        self.keep_both.setToolTip(text("keep_both_tip"))
        for number, widget in enumerate(
            (
                self.peoples_button,
                self.resources_button,
                self.edit_button,
                self.parent_button,
                self.undo_button,
                self.keep_both,
                self.like_button,
            )
        ):
            line, column = divmod(number, 2)
            row.addWidget(widget, line, column)
        _ = self.peoples_button.clicked.connect(lambda: self._reroll("peoples"))
        _ = self.resources_button.clicked.connect(lambda: self._reroll("resources"))
        _ = self.edit_button.clicked.connect(self.controller.edit_selected)
        _ = self.parent_button.clicked.connect(self._previous_version)
        _ = self.undo_button.clicked.connect(self._undo)
        return row

    def _file_buttons(self) -> QGridLayout:
        row = QGridLayout()
        self.export_button = QPushButton(text("export_file"))
        self.export_button.setToolTip(text("export_file_tip"))
        self.send_button = QPushButton(text("send_built"))
        self.send_button.setToolTip(text("send_built_tip"))
        self.copy_mod_button = QPushButton(text("copy_mod"))
        self.copy_mod_button.setToolTip(text("copy_mod_tip"))
        self.copy_tag_button: QPushButton = QPushButton(text("copy_tag"))
        self.copy_picture_button: QPushButton = QPushButton(text("copy_picture"))
        for number, button in enumerate(
            (
                self.export_button,
                self.send_button,
                self.copy_mod_button,
                self.copy_tag_button,
                self.copy_picture_button,
            )
        ):
            line, column = divmod(number, 2)
            row.addWidget(button, line, column)
        _ = self.export_button.clicked.connect(self._export_file)
        _ = self.send_button.clicked.connect(self._send_built)
        _ = self.copy_mod_button.clicked.connect(self._copy_mod)
        _ = self.copy_tag_button.clicked.connect(self._copy_tag)
        _ = self.copy_picture_button.clicked.connect(self._copy_picture)
        return row

    def _stray_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel(text("stray_name"))
        font = QFont(title.font())
        font.setPointSizeF(font.pointSizeF() * 1.4)
        font.setBold(True)
        title.setFont(font)
        self.stray_about = QLabel()
        self.stray_about.setWordWrap(True)
        row = QHBoxLayout()
        self.stray_remove = QPushButton(text("remove"))
        self.stray_open = QPushButton(text("open_folder"))
        row.addWidget(self.stray_remove)
        row.addWidget(self.stray_open)
        row.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(self.stray_about)
        layout.addLayout(row)
        layout.addStretch(1)
        _ = self.stray_remove.clicked.connect(self._remove)
        _ = self.stray_open.clicked.connect(self._open_stray)
        return page

    # -- the controller's state, drawn ------------------------------------------------------------

    def refresh(self) -> None:
        """Make every widget equal to the controller."""
        self._refresh_header()
        self._refresh_list()
        selection = self.controller.selection
        if self.controller.selected_world() is not None:
            self.stack.setCurrentWidget(self.world_page)
            self._refresh_world()
        elif selection.startswith(STRAY) and self.controller.selected_stray() is not None:
            self.stack.setCurrentWidget(self.stray_page)
            self._refresh_stray()
        else:
            self.stack.setCurrentWidget(self.new_page)
        self._refresh_new()
        self._refresh_selection()
        self._report_transfer_failure()
        controller = self.controller
        if (
            controller.task is Task.CANDIDATES
            and controller.phase is Phase.FINISHED
            and self._sketched != controller.runs
        ):
            self._sketched = controller.runs
            self.candidates_dialog = CandidatesDialog(self, controller)
            self.candidates_dialog.show()
        free = parallel.available_memory()
        threads = parallel.thread_count()
        self.resources.setText(
            text("resources_unknown", threads=threads)
            if free is None
            else text("resources", threads=threads, free=f"{free / GIB:.1f}")
        )

    def _refresh_header(self) -> None:
        controller = self.controller
        lines: list[str] = []
        if controller.game is not None:
            game = str(controller.game.directory)
            build = controller.game.build_id
            lines.append(
                text("game_line", build=build, game=game)
                if build
                else text("game_line_unknown", game=game)
            )
        if controller.profile is not None:
            lines.append(text("profile_line", profile=str(controller.profile.directory)))
        self.game_line.setToolTip("\n".join(lines))
        self.game_line.setText(
            text("game_status", build=controller.game.build_id or "?")
            if controller.game is not None
            else TITLE
        )
        self.problem_line.setText(
            text("game_missing")
            if controller.game is None
            else text("profile_missing")
            if controller.profile is None
            else ""
        )
        self.problem_line.setVisible(bool(self.problem_line.text()))

    def _refresh_list(self) -> None:
        controller = self.controller
        selected = tuple(
            cast("object", item.data(Qt.ItemDataRole.UserRole))
            for item in self.world_list.selectedItems()
        )
        current = cast("QListWidgetItem | None", self.world_list.currentItem())
        current_id = (
            cast("object", current.data(Qt.ItemDataRole.UserRole)) if current is not None else None
        )
        preserve = current_id == controller.selection
        _ = self.world_list.blockSignals(True)  # noqa: FBT003 - Qt synchronization
        listed = controller.listed()
        key = (
            str(controller.preferences.show_new_world),
            *(
                "|".join(
                    (
                        w.id,
                        w.name,
                        str(w.starred),
                        w.user_tag,
                        controller.placement(w).value,
                        str(depth),
                        str(controller.shown(w)),
                    )
                )
                for w, depth in listed
            ),
            *(f"{STRAY}{stray.name}" for stray in controller.strays),
        )
        if key != self._list_key:
            self._list_key = key
            _ = self.world_list.blockSignals(True)  # noqa: FBT003 - Qt's own call
            self.world_list.clear()
            first = QListWidgetItem(text("new_world"))
            first.setData(Qt.ItemDataRole.UserRole, NEW)
            first.setIcon(QIcon.fromTheme("document-new"))
            self.world_list.addItem(first)
            for world, depth in listed:
                self.world_list.addItem(self._world_item(world, depth))
            for stray in controller.strays:
                item = QListWidgetItem(
                    f"{text('stray_name')}\n{text('stray_line', folder=stray.name)}"
                )
                item.setData(Qt.ItemDataRole.UserRole, f"{STRAY}{stray.name}")
                self.world_list.addItem(item)
        running = controller.busy and controller.task is Task.GENERATE
        if self.world_list.count():
            self.world_list.item(0).setText(
                text("new_world_running", percent=_progress_percent(controller.fraction))
                if running
                else text("new_world")
            )
        for row in range(self.world_list.count()):
            item = self.world_list.item(row)
            item.setSelected(
                item.data(Qt.ItemDataRole.UserRole) in selected
                if preserve
                else item.data(Qt.ItemDataRole.UserRole) == controller.selection
            )
            if item.data(Qt.ItemDataRole.UserRole) == controller.selection:
                self.world_list.setCurrentItem(item, QItemSelectionModel.SelectionFlag.NoUpdate)
        _ = self.world_list.blockSignals(False)  # noqa: FBT003 - Qt synchronization

    def selected_entries(self) -> tuple[str, ...]:
        """The selected world and stray IDs, excluding the new-world action."""
        return tuple(
            key
            for item in self.world_list.selectedItems()
            if isinstance(key := cast("object", item.data(Qt.ItemDataRole.UserRole)), str)
            and key != NEW
        )

    def _refresh_selection(self) -> None:
        controller = self.controller
        selected = self.selected_entries()
        installed = len(controller.removable_entries(selected))
        worlds = sum(world.id in selected for world in controller.worlds)
        self.selection_label.setText(
            text("selection_count", count=len(selected), installed=installed)
        )
        self.select_all_button.setEnabled(bool(controller.worlds or controller.strays))
        problem = controller.removal_problem() or (text("remove_none") if not installed else None)
        self.library_remove.setText(text("library_remove", count=installed))
        self.library_remove.setEnabled(problem is None)
        self.library_remove.setToolTip(problem or text("remove_tip"))
        problem = (
            text("ready_busy") if controller.busy else text("delete_none") if not worlds else None
        )
        self.library_delete.setText(text("library_delete", count=worlds))
        self.library_delete.setEnabled(problem is None)
        self.library_delete.setToolTip(problem or text("delete_tip"))
        multiple = len(selected) > 1
        self.remove_button.setText(
            text("remove_count", count=installed) if multiple else text("remove")
        )
        self.delete_button.setText(
            text("delete_count", count=worlds) if multiple else text("delete")
        )
        message = ""
        if controller.task in {Task.REMOVE, Task.DELETE}:
            if controller.busy:
                message = text(f"task.{controller.task.value}")
            elif controller.phase is Phase.FAILED:
                message = text(
                    "task_failed", message=controller.message, report_hint=text("report_hint")
                )
            elif controller.phase is Phase.FINISHED:
                message = text(
                    "batch_removed" if controller.task is Task.REMOVE else "batch_deleted"
                )
            elif controller.phase is Phase.CANCELLED:
                message = text("batch_cancelled")
        self.library_status.setText(message)
        self.library_status.setVisible(bool(message))

    def _select_all_worlds(self) -> None:
        self.world_list.selectAll()
        if self.world_list.count():
            self.world_list.item(0).setSelected(False)

    def _remove_entries(self) -> None:
        problem = self.controller.remove_entries(self.selected_entries())
        if problem:
            self.library_status.setText(problem)
            self.library_status.show()

    def _delete_entries(self) -> None:
        selected = self.selected_entries()
        worlds = [world for world in self.controller.worlds if world.id in selected]
        if not worlds:
            return
        answer = QMessageBox.question(
            self,
            text("delete_many_title", count=len(worlds)),
            text(
                "delete_many_question",
                count=len(worlds),
                names="\n".join(self.controller.name(world) for world in worlds),
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            problem = self.controller.delete_entries(selected)
            if problem:
                self.library_status.setText(problem)
                self.library_status.show()

    def _world_item(self, world: World, depth: int = 0) -> QListWidgetItem:
        controller = self.controller
        when = datetime.fromtimestamp(world.created).astimezone().strftime(DATE)
        place = text(f"list.{controller.placement(world).value}")
        line = text("world_line", when=when, place=place)
        if world.part:
            line = f"{text(f'part.{world.part}')} · {line}"
        title = f"{VERSION_MARK * depth}{'* ' if world.starred else ''}{controller.name(world)}"
        item = QListWidgetItem(f"{title}\n{VERSION_MARK * depth}{line}")
        item.setToolTip(world.user_tag)
        item.setData(Qt.ItemDataRole.UserRole, world.id)
        picture = controller.picture(world)
        if picture is not None:
            item.setIcon(
                QIcon(
                    QPixmap(str(picture)).scaled(
                        *ICON_SIZE,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            )
        return item

    def _ocean_toggled(self, checked: bool) -> None:  # noqa: FBT001 - Qt checkbox
        self.controller.set_value("new_world.expand_oceans", int(checked))

    def _refresh_ocean_option(self, busy: bool) -> None:  # noqa: FBT001 - UI state
        _ = self.expand_oceans.blockSignals(True)  # noqa: FBT003 - Qt synchronization
        self.expand_oceans.setChecked(bool(self.controller.value("new_world.expand_oceans")))
        _ = self.expand_oceans.blockSignals(False)  # noqa: FBT003 - Qt synchronization
        self.expand_oceans.setEnabled(not busy)

    def _refresh_new(self) -> None:
        controller = self.controller
        busy = controller.busy
        drawn = controller.land_mask
        self.land_image_label.setText(
            text("land_image_chosen", id=format(drawn.id, "x")) if drawn is not None else ""
        )
        self.land_image_clear.setVisible(drawn is not None)
        self.land_image_button.setEnabled(not busy)
        self.land_template_button.setEnabled(not busy and controller.game is not None)
        _ = self.type_choice.blockSignals(True)  # noqa: FBT003 - Qt synchronization
        shown = controller.mode or controller.preset
        self.type_choice.setCurrentIndex(random_types.CHOICES.index(shown))
        _ = self.type_choice.blockSignals(False)  # noqa: FBT003 - Qt synchronization
        self.type_about.setText(text(f"type.{shown}.about"))
        if not self.seed_edit.hasFocus():
            self.seed_edit.setText(str(controller.seed))
        if not self.code_edit.hasFocus():
            self.code_edit.setText(controller.code)
        self.notice.setText(controller.notice)
        self.notice.setVisible(bool(controller.notice))
        for row in self.rows:
            key = row.control.key
            row.refresh(controller.value(key), changed=key in controller.changes, enabled=not busy)
        for quick_row in self.quick_rows:
            quick_row.refresh(controller.quick_level(quick_row.quick.name), enabled=not busy)
        count = len(controller.changes)
        self.customized.setText(text("customized", count=count) if count else "")
        self.reset_all.setEnabled(bool(count) and not busy)
        problem = controller.problem()
        try:
            estimate = controller.estimated_locations()
            self.estimate.setText(text("estimate", count=grouped(estimate)))
            self.estimate.setStyleSheet(RED if estimate > controls.LOCATION_BUDGET else MUTED)
        except ValueError:
            self.estimate.setText("")
        self._refresh_destination(problem)
        _ = self.show_new_world.blockSignals(True)  # noqa: FBT003 - Qt synchronization
        self.show_new_world.setChecked(controller.preferences.show_new_world)
        _ = self.show_new_world.blockSignals(False)  # noqa: FBT003 - Qt synchronization
        self.show_new_world.setEnabled(not busy)
        self._refresh_ocean_option(busy)
        generating = controller.task in {Task.GENERATE, Task.QUEUE, Task.CANDIDATES}
        self.cancel_button.setEnabled(controller.phase is Phase.RUNNING and generating)
        self.cancel_button.setVisible(busy and generating)
        self.progress_box.setVisible(generating and controller.phase is not Phase.IDLE)
        for widget in (
            self.seed_edit,
            self.random_button,
            self.code_edit,
            self.paste_button,
            self.type_choice,
        ):
            widget.setEnabled(not busy)
        self.bar.setValue(_progress_percent(controller.fraction) if generating else 0)
        status = self._status_line() if generating else text("idle")
        self.status.setText(status)
        self.status.setToolTip(status)
        self._refresh_eta_state()
        self.stage_list.clear()
        for label, state in controller.stage_rows():
            mark = MARKS[state] if generating else MARKS["waiting"]
            self.stage_list.addItem(QListWidgetItem(f"{mark}  {label}"))

    def _refresh_eta_state(self) -> None:
        """Show and start the ETA timer only for one live world generation."""
        active = self.controller.task is Task.GENERATE and self.controller.phase is Phase.RUNNING
        self.eta.setVisible(active)
        if active:
            self._refresh_eta()
            if not self._eta_timer.isActive():
                self._eta_timer.start()
        else:
            self._eta_timer.stop()

    def _refresh_eta(self) -> None:
        """Refresh the countdown without rebuilding the rest of the window."""
        remaining = self.controller.estimated_remaining()
        if remaining is None:
            self.eta.clear()
            return
        self.eta.setText(text("eta", time=_duration_clock(remaining)))

    def _refresh_destination(self, problem: str | None) -> None:
        controller, busy = self.controller, self.controller.busy
        self.install_box.setChecked(controller.install)
        self.new_tabs.setTabText(
            2,
            text("new_tab.queued", count=len(controller.queue))
            if controller.queue
            else text("new_tab.output"),
        )
        is_library = self.destination.currentIndex() == 0
        target = controller.output_folder or controller.world_file
        self.destination_path.setText(str(target) if target is not None else "")
        self.destination_path.setToolTip(self.destination_path.text())
        self.destination_path.setVisible(not is_library)
        self.destination_button.setVisible(not is_library)
        self.destination_button.setEnabled(not busy and not is_library)
        self.destination.setEnabled(not busy)
        self.install_box.setEnabled(not busy and is_library)
        self.install_box.setVisible(is_library)
        needs_destination = not is_library and target is None
        if needs_destination:
            problem = text("destination_missing")
        self.generate_button.setEnabled(problem is None)
        self.generate_button.setToolTip(problem or "")
        self.generation_hint.setText(
            problem
            or text(
                "generation_install"
                if controller.install
                else "generation_copy"
                if controller.output_folder is not None
                else "generation_file"
                if controller.world_file is not None
                else "generation_keep"
            )
        )
        self.generation_hint.setVisible(not busy)
        self.enqueue_button.setEnabled(problem is None)
        self.run_queue_button.setEnabled(not busy and bool(controller.queue))
        self.clear_queue_button.setEnabled(not busy and bool(controller.queue))
        self.queue_label.setText(text("queue_count", count=len(controller.queue)))
        self.queue_label.setToolTip("\n".join(str(job.code.seed) for job in controller.queue))
        self.candidates_button.setEnabled(
            not busy
            and controller.game is not None
            and not controller.world_code().settings().mask.id
        )

    def _status_line(self) -> str:
        controller = self.controller
        match controller.phase:
            case Phase.IDLE:
                return text("idle")
            case Phase.RUNNING:
                return text("running", stages=controller.running_text() or "…")
            case Phase.CANCELLING:
                return text("cancelling")
            case Phase.FINISHED:
                seconds = round(controller.result.seconds) if controller.result else 0
                return text("finished", seconds=seconds)
            case Phase.FAILED:
                return text("failed", message=controller.message, report_hint=text("report_hint"))
            case Phase.CANCELLED:
                return text("cancelled")

    def _show_maps(self, world: World) -> None:
        controller = self.controller
        found = controller.atlas(world)
        self.maps.show_world(
            found,
            revealed=controller.revealed(world),
            identity=sum(world.id.encode()),
            words=controller.words(found) if found is not None else atlas_module.ENGLISH,
        )

    def _refresh_world(self) -> None:
        controller = self.controller
        world = controller.selected_world()
        if world is None:
            return
        if world.id != self._shown_world:
            self._shown_world = world.id
            self.notes_edit.setPlainText(world.notes)
            self.user_tag_edit.setText(world.user_tag)
            self.starred_box.setChecked(world.starred)
            self._tell(None)
        if not self.name_edit.hasFocus():
            self.name_edit.setText(controller.name(world))
        shown = self.preview.show_picture(controller.picture(world))
        state = text("preview_shown" if controller.shown(world) else "preview_hidden")
        self._refresh_visibility(world)
        self.preview_caption.setText(
            f"{state} {text('zoom_hint')}" if shown else text("preview_missing")
        )
        placement = controller.placement(world)
        self._show_maps(world)
        self.maps.set_summary(controller.summary(world))
        game_build = controller.game.build_id if controller.game is not None else ""
        changed = controller.changed_count(world)
        mod = None
        if controller.profile is not None:
            mod = controller.profile.directory / "mod" / world.folder
        values = {
            "code": world.code,
            "type": text(f"type.{world.preset}"),
            "seed": str(world.seed),
            "custom": text("custom_some", count=changed) if changed else text("custom_none"),
            "made": datetime.fromtimestamp(world.created).astimezone().strftime(DATE),
            "build": world.game_build or "?",
            "generator": world.generator,
            "reproduce": controller.reproduction(world),
            "place": text("place.in_game", path=mod)
            if placement is Placement.IN_GAME
            else text("place.kept")
            if placement is Placement.KEPT
            else text("place.code_only", seconds=round(world.seconds or 120)),
        }
        for key, value in values.items():
            self.details[key].setText(value)
        notes: list[str] = []
        if game_build and world.game_build and world.game_build != game_build:
            kind = "other_build_same" if controller.compatibility(world) else "other_build"
            notes.insert(0, text(kind, made=world.game_build, current=game_build))
        self.note.setText("\n\n".join(notes))
        self.note.setVisible(bool(notes))
        advice = controller.next_step(world) if placement is Placement.IN_GAME else ""
        self.advice.setText(advice)
        self.advice.setVisible(bool(advice))
        problem = controller.world_problem()
        self.add_button.setVisible(placement is not Placement.IN_GAME)
        self.remove_button.setVisible(placement is Placement.IN_GAME)
        for button, reason in (
            (self.add_button, problem),
            (self.remove_button, controller.removal_problem()),
            (self.delete_button, text("ready_busy") if controller.busy else None),
        ):
            button.setEnabled(reason is None)
            button.setToolTip(reason or "")
        self.like_button.setEnabled(not controller.busy)
        self.check_button.setEnabled(not controller.busy and controller.game is not None)
        can_change = not controller.busy and controller.game is not None
        for button in (self.peoples_button, self.resources_button):
            button.setEnabled(can_change)
        self.edit_button.setEnabled(not controller.busy)
        self.keep_both.setVisible(placement is Placement.IN_GAME)
        self.parent_button.setVisible(controller.parent_of(world) is not None)
        self.undo_button.setVisible(controller.parent_of(world) is not None)
        self.undo_button.setEnabled(not controller.busy)
        mine = controller.task_target == world.id and controller.task in {
            Task.ADD,
            Task.REMOVE,
            Task.DELETE,
            Task.CHECK,
            Task.REROLL,
            Task.SEND,
            Task.COPY,
            Task.UNDO,
        }
        self._refresh_task(mine=mine)

    def _refresh_visibility(self, world: World) -> None:
        _ = self.world_visibility.blockSignals(True)  # noqa: FBT003 - Qt synchronization
        self.world_visibility.setChecked(self.controller.shown(world))
        _ = self.world_visibility.blockSignals(False)  # noqa: FBT003 - Qt synchronization
        self.world_visibility.setEnabled(not self.controller.busy)

    def _refresh_task(self, *, mine: bool) -> None:
        controller = self.controller
        if not mine or controller.phase is Phase.IDLE:
            self.task_line.setText("")
            self.task_bar.setVisible(False)
            return
        if controller.busy:
            label = text(f"task.{controller.task.value}") if controller.task else ""
            running = controller.running_text()
            self.task_line.setText(f"{label} {running}".strip())
            self.task_bar.setVisible(controller.task in {Task.ADD, Task.CHECK, Task.REROLL})
            self.task_bar.setValue(_progress_percent(controller.fraction))
            return
        self.task_bar.setVisible(False)
        self.task_line.setText(
            text("task_failed", message=controller.message, report_hint=text("report_hint"))
            if controller.phase is Phase.FAILED
            else ""
        )

    def _refresh_stray(self) -> None:
        stray = self.controller.selected_stray()
        if stray is None:
            return
        self.stray_about.setText(text("stray_about", folder=stray.name))
        problem = self.controller.removal_problem()
        self.stray_remove.setEnabled(problem is None)
        self.stray_remove.setToolTip(problem or "")

    # -- what the buttons do ---------------------------------------------------------------------

    def _picked(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None:
            return
        selection = cast("object", current.data(Qt.ItemDataRole.UserRole))
        if isinstance(selection, str):
            self.controller.select(selection)

    def _settings(self) -> None:
        _ = SettingsDialog(self).exec()
        self.refresh()

    def _pick_type(self, index: int) -> None:
        if 0 <= index < len(random_types.CHOICES):
            choice = random_types.CHOICES[index]
            if choice in random_types.MODES:
                self.controller.set_mode(choice)
            else:
                self.controller.set_preset(choice)

    def _toggle_customize(self, shown: bool) -> None:  # noqa: FBT001 - Qt's signal argument
        self.customize_box.setVisible(shown)
        self.customize_button.setArrowType(
            Qt.ArrowType.DownArrow if shown else Qt.ArrowType.RightArrow
        )

    def _generate(self) -> None:
        problem = self.controller.start()
        if problem:
            self.status.setText(problem)

    def _seed_typed(self) -> None:
        problem = self.controller.set_seed(self.seed_edit.text())
        if problem:
            self.notice.setText(problem)
            self.notice.setVisible(True)
            self.seed_edit.setText(str(self.controller.seed))

    def _code_typed(self) -> None:
        if not self.code_edit.text().strip() or self.code_edit.text() == self.controller.code:
            return
        problem = self.controller.use_code(self.code_edit.text())
        if problem:
            self.notice.setText(problem)
            self.notice.setVisible(True)
            self.code_edit.setText(self.controller.code)

    def _install_toggled(self, checked: bool) -> None:  # noqa: FBT001 - Qt's signal argument
        if checked != self.controller.install:
            self.controller.install = checked
            self.refresh()

    def _copy(self) -> None:
        QApplication.clipboard().setText(self.controller.code)

    def _paste(self) -> None:
        pasted = QApplication.clipboard().text()
        if pasted.strip():
            problem = self.controller.set_seed(pasted)
            if problem:
                self.notice.setText(problem)
                self.notice.setVisible(True)

    def _renamed(self) -> None:
        world = self.controller.selected_world()
        if world is not None and self.name_edit.text() != self.controller.name(world):
            self._tell(self.controller.rename(world, self.name_edit.text()))

    def _report_transfer_failure(self) -> None:
        """A built world that could not be taken in or written is said once, in a box."""
        controller = self.controller
        failed = controller.phase is Phase.FAILED
        if (
            failed
            and controller.task
            in {Task.RECEIVE, Task.SEND, Task.COPY, Task.TEMPLATE, Task.CANDIDATES}
            and self._reported != controller.runs
        ):
            self._reported = controller.runs
            _ = QMessageBox.warning(self, text("open_world_file"), controller.message)

    def _open_world_file(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(
            self, text("open_world_file"), str(Path.home()), text("world_files")
        )
        if chosen:
            self._take_in(Path(chosen))

    def _take_in(self, path: Path) -> None:
        """Take a world file into the library and say what came of it."""
        problem = self.controller.import_file(path)
        if problem:
            _ = QMessageBox.warning(self, text("open_world_file"), problem)
            return
        taken = self.controller.last_import
        if taken is not None and not path.name.lower().endswith(".rnworld-mod"):
            self._tell(text("imported" if taken.created else "imported_again"))

    def _export_file(self) -> None:
        world = self.controller.selected_world()
        if world is None:
            return
        suggested = str(Path.home() / f"{self.controller.name(world)}.rnworld".replace(" ", "-"))
        title = text("export_file")
        chosen, _ = QFileDialog.getSaveFileName(self, title, suggested, "World file (*.rnworld)")
        if chosen:
            output = Path(chosen)
            self._tell(
                self.controller.export_file(world, output) or text("file_saved", path=chosen)
            )

    def _send_built(self) -> None:
        world = self.controller.selected_world()
        if world is None:
            return
        title = text("send_built")
        answer = QMessageBox.question(self, title, text("send_built_warning"))
        if answer != QMessageBox.StandardButton.Yes:
            return
        suggested = str(
            Path.home() / f"{self.controller.name(world)}.rnworld-mod".replace(" ", "-")
        )
        chosen, _ = QFileDialog.getSaveFileName(
            self, title, suggested, "Built world (*.rnworld-mod)"
        )
        if chosen:
            self._tell(self.controller.send_built(world, Path(chosen)))

    def _copy_mod(self) -> None:
        world = self.controller.selected_world()
        if world is None:
            return
        folder = QFileDialog.getExistingDirectory(self, text("copy_mod"))
        if folder:
            self._tell(self.controller.copy_mod_to(world, Path(folder)))

    @override
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        mime = event.mimeData()
        files = [Path(url.toLocalFile()) for url in mime.urls() if url.isLocalFile()]
        if any(worldfile.is_world_file(item) for item in files) or (
            mime.hasText() and mime.text().strip().upper().startswith("RNW")
        ):
            event.acceptProposedAction()

    @override
    def dropEvent(self, event: QDropEvent) -> None:
        mime = event.mimeData()
        for url in mime.urls():
            if url.isLocalFile() and worldfile.is_world_file(Path(url.toLocalFile())):
                self._take_in(Path(url.toLocalFile()))
                event.acceptProposedAction()
                return
        if mime.hasText() and mime.text().strip().upper().startswith("RNW"):
            self.controller.select(NEW)
            problem = self.controller.set_seed(mime.text())
            if problem:
                self.notice.setText(problem)
                self.notice.setVisible(True)
            event.acceptProposedAction()

    def _reveal(self) -> None:
        world = self.controller.selected_world()
        if world is not None:
            self.controller.reveal_world(world)

    def _save_picture(self) -> None:
        world = self.controller.selected_world()
        if world is None:
            return
        on_maps = self.world_tabs.currentWidget() is self.maps and self.controller.revealed(world)
        suggested = str(Path.home() / f"{self.controller.name(world)}.png".replace(" ", "-"))
        chosen, _ = QFileDialog.getSaveFileName(
            self, text("save_picture"), suggested, "PNG (*.png)"
        )
        if not chosen:
            return
        output = Path(chosen)
        problem = (
            self.controller.save_map(world, self.maps.layer, output)
            if on_maps
            else self.controller.save_preview(world, output)
        )
        self._tell(problem or text("picture_saved", path=chosen))

    def _compare(self) -> None:
        entries = [
            (self.controller.name(world), found)
            for world, found in self.controller.maps_to_compare()
        ]
        if len(entries) < 2:  # noqa: PLR2004 - two worlds are compared
            self._tell(text("compare_need_two"))
            return
        _ = CompareDialog(self, entries, self.maps.layer).exec()

    def _reroll(self, part: str) -> None:
        self._tell(self.controller.reroll_selected(part, keep_both=self.keep_both.isChecked()))

    def _previous_version(self) -> None:
        world = self.controller.selected_world()
        parent = self.controller.parent_of(world) if world is not None else None
        if parent is not None:
            self.controller.select(parent.id)

    def _check(self) -> None:
        self._tell(self.controller.check_selected())

    def _tell(self, message: str | None) -> None:
        """Say something about the selected world, under its tabs, until another world is shown."""
        self.world_notice.setText(message or "")
        self.world_notice.setVisible(bool(message))

    def _copy_world_code(self) -> None:
        world = self.controller.selected_world()
        if world is not None:
            QApplication.clipboard().setText(world.code)

    def _copy_tag(self) -> None:
        world = self.controller.selected_world()
        if world is not None:
            QApplication.clipboard().setText(worldname.tag_of(world.id))

    def _copy_picture(self) -> None:
        world = self.controller.selected_world()
        picture = self.controller.picture(world) if world is not None else None
        if picture is not None:
            QApplication.clipboard().setImage(QImage(str(picture)))

    def _undo(self) -> None:
        self._tell(self.controller.undo_selected())

    def _add(self) -> None:
        problem = self.controller.add_selected()
        if problem:
            self.task_line.setText(problem)

    def _remove(self) -> None:
        if len(self.selected_entries()) > 1:
            self._remove_entries()
            return
        problem = self.controller.remove_selected()
        if problem:
            self.task_line.setText(problem)

    def _like(self) -> None:
        world = self.controller.selected_world()
        if world is not None:
            self.controller.like(world)

    def _delete(self) -> None:
        if len(self.selected_entries()) > 1:
            self._delete_entries()
            return
        world = self.controller.selected_world()
        if world is None:
            return
        answer = QMessageBox.question(
            self,
            text("delete_title"),
            text("delete_question", name=self.controller.name(world)),
        )
        if answer == QMessageBox.StandardButton.Yes:
            problem = self.controller.delete_selected()
            if problem:
                self.task_line.setText(problem)

    def _open_world(self) -> None:
        controller = self.controller
        world = controller.selected_world()
        if world is None:
            return
        if controller.placement(world) is Placement.IN_GAME and controller.profile is not None:
            target = controller.profile.directory / "mod" / world.folder
        else:
            target = controller.data / "generated" / world.folder
        _ = QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    def _open_stray(self) -> None:
        stray = self.controller.selected_stray()
        if stray is not None:
            _ = QDesktopServices.openUrl(QUrl.fromLocalFile(str(stray)))

    @override
    def closeEvent(self, event: QCloseEvent) -> None:
        """Stop a running generation before the window goes, so nothing is left half written."""
        self.controller.cancel()
        self.controller.wait(CLOSE_WAIT)
        super().closeEvent(event)
