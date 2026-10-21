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

from PySide6.QtCore import QObject, QRectF, Qt, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from rnw import __version__, parallel
from rnw.app import controls
from rnw.app.library import Placement
from rnw.gui.controller import NEW, STRAY, Controller, Phase, Task
from rnw.gui.text import TITLE, text
from rnw.settings import WORLD_TYPES

if TYPE_CHECKING:
    from PySide6.QtGui import QMouseEvent, QResizeEvent, QWheelEvent

    from rnw.app.library import World

GIB: Final[float] = float(1 << 30)
PROGRESS_STEPS: Final[int] = 1000
MARKS: Final[dict[str, str]] = {"done": "✓", "running": "▶", "waiting": "·"}
CLOSE_WAIT: Final[float] = 15.0
RED: Final[str] = "color: #b00020;"
MUTED: Final[str] = "color: palette(mid);"
ICON_SIZE: Final[tuple[int, int]] = (96, 48)
ZOOM_STEP: Final[float] = 1.25
ZOOM_LIMIT: Final[float] = 16.0
DATE: Final[str] = "%Y-%m-%d %H:%M"


class _Bridge(QObject):
    """Carries 'something changed' from the work thread to the window's thread."""

    changed: Signal = Signal()


class PreviewView(QGraphicsView):
    """A picture that zooms with the wheel, moves by dragging and fits on a double-click."""

    def __init__(self) -> None:
        super().__init__()
        self._scene: QGraphicsScene = QGraphicsScene(self)
        self._item: QGraphicsPixmapItem = QGraphicsPixmapItem()
        self._item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self._scene.addItem(self._item)
        self.setScene(self._scene)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setMinimumHeight(220)
        self._path: str = ""
        self._fitted: bool = True

    def show_picture(self, path: Path | None) -> bool:
        """Show the picture at ``path`` (none: empty); returns whether one is shown."""
        key = str(path) if path is not None else ""
        if key == self._path:
            return not self._item.pixmap().isNull()
        self._path = key
        picture = QPixmap(key) if key else QPixmap()
        self._item.setPixmap(picture)
        self._scene.setSceneRect(QRectF(picture.rect()))
        self.fit()
        return not picture.isNull()

    def fit(self) -> None:
        """Show the whole picture."""
        self.resetTransform()
        if not self._item.pixmap().isNull():
            self.fitInView(self._item, Qt.AspectRatioMode.KeepAspectRatio)
        self._fitted = True

    @override
    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._item.pixmap().isNull():
            return
        factor = math.pow(ZOOM_STEP, event.angleDelta().y() / 120)
        scale = self.transform().m11() * factor
        if scale < self._fit_scale() or scale > ZOOM_LIMIT:
            return
        self.scale(factor, factor)
        self._fitted = False

    @override
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self.fit()
        super().mouseDoubleClickEvent(event)

    @override
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._fitted:
            self.fit()

    def _fit_scale(self) -> float:
        width = self._item.pixmap().width()
        return min(1.0, self.viewport().width() / width) * 0.98 if width else 1.0


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
        self.problem: QLabel = QLabel()
        self.problem.setStyleSheet(RED)
        self.problem.setWordWrap(True)
        grid.addWidget(QLabel(text("game")), 0, 0)
        grid.addWidget(self.game_choice, 0, 1)
        grid.addWidget(game_browse, 0, 2)
        grid.addWidget(QLabel(text("profile")), 1, 0)
        grid.addWidget(self.profile_choice, 1, 1)
        grid.addWidget(profile_browse, 1, 2)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)
        layout.addWidget(self.problem)
        self.reveal: QCheckBox = QCheckBox(text("reveal_thumbnails"))
        self.reveal.setChecked(controller.preferences.reveal_thumbnails)
        hint = QLabel(text("reveal_thumbnails_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(MUTED)
        layout.addWidget(self.reveal)
        layout.addWidget(hint)
        about = QLabel(text("about_generator"))
        about.setWordWrap(True)
        layout.addWidget(about)
        close = QPushButton(text("close"))
        close.setDefault(True)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        _ = game_browse.clicked.connect(self._browse_game)
        _ = profile_browse.clicked.connect(self._browse_profile)
        _ = self.game_choice.activated.connect(self._pick_game)
        _ = self.profile_choice.activated.connect(self._pick_profile)
        _ = self.reveal.toggled.connect(controller.set_reveal_thumbnails)
        _ = close.clicked.connect(self.accept)
        self.resize(720, 0)

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

    def _browse_game(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, text("game"))
        if folder:
            problem = self.window_.controller.choose_game(Path(folder))
            self.problem.setText(problem or "")
            if problem is None:
                self.game_choice.insertItem(0, folder)
                self.game_choice.setCurrentIndex(0)

    def _browse_profile(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, text("profile"))
        if folder:
            problem = self.window_.controller.choose_profile(Path(folder))
            self.problem.setText(problem or "")
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
    type_buttons: QButtonGroup
    seed_edit: QLineEdit
    random_button: QPushButton
    code_edit: QLineEdit
    copy_button: QPushButton
    paste_button: QPushButton
    notice: QLabel
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
    stage_list: QListWidget
    # a world
    world_page: QWidget
    name_edit: QLineEdit
    preview: PreviewView
    preview_caption: QLabel
    reveal_button: QPushButton
    details: dict[str, QLabel]
    copy_code_button: QPushButton
    note: QLabel
    advice: QLabel
    add_button: QPushButton
    remove_button: QPushButton
    open_button: QPushButton
    like_button: QPushButton
    delete_button: QPushButton
    task_line: QLabel
    task_bar: QProgressBar
    # a stray
    stray_page: QWidget
    stray_about: QLabel
    stray_remove: QPushButton
    stray_open: QPushButton

    def __init__(self, controller: Controller) -> None:
        super().__init__()
        self.controller: Controller = controller
        self._bridge: _Bridge = _Bridge()
        self._list_key: tuple[str, ...] = ()
        self.rows: list[_ControlRow] = []
        self.setWindowTitle(TITLE)
        self._build()
        _ = self._bridge.changed.connect(self.refresh)
        controller.subscribe(self._bridge.changed.emit)
        self.refresh()

    # -- construction ---------------------------------------------------------------------------

    def _build(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addLayout(self._header())
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.world_list = QListWidget()
        self.world_list.setIconSize(QPixmap(*ICON_SIZE).size())
        self.world_list.setMinimumWidth(300)
        self.world_list.setWordWrap(True)
        _ = self.world_list.currentItemChanged.connect(self._picked)
        splitter.addWidget(self.world_list)
        self.stack = QStackedWidget()
        self.new_page = self._new_page()
        self.world_page = self._world_page()
        self.stray_page = self._stray_page()
        for page in (self.new_page, self.world_page, self.stray_page):
            _ = self.stack.addWidget(page)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 900])
        layout.addWidget(splitter, 1)
        self.setCentralWidget(root)
        self.resources = QLabel()
        status = self.statusBar()
        status.addPermanentWidget(QLabel(f"v{__version__}"))
        status.addWidget(self.resources)

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
        self.settings_button = QPushButton(text("settings"))
        _ = self.settings_button.clicked.connect(self._settings)
        row.addWidget(self.settings_button, alignment=Qt.AlignmentFlag.AlignTop)
        return row

    def _new_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.addWidget(self._types())
        layout.addLayout(self._seed_and_code())
        self.notice = QLabel()
        self.notice.setWordWrap(True)
        self.notice.setStyleSheet(RED)
        layout.addWidget(self.notice)
        layout.addWidget(self._customize())
        layout.addStretch(1)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        self.estimate = QLabel()
        self.estimate.setWordWrap(True)
        outer.addWidget(self.estimate)
        self.install_box = QCheckBox(text("install"))
        outer.addWidget(self.install_box)
        row = QHBoxLayout()
        self.generate_button = QPushButton(text("generate"))
        self.generate_button.setDefault(True)
        self.cancel_button = QPushButton(text("cancel"))
        row.addWidget(self.generate_button, 1)
        row.addWidget(self.cancel_button)
        outer.addLayout(row)
        outer.addWidget(self._progress())
        _ = self.seed_edit.editingFinished.connect(self._seed_typed)
        _ = self.code_edit.editingFinished.connect(self._code_typed)
        _ = self.random_button.clicked.connect(self.controller.randomize)
        _ = self.copy_button.clicked.connect(self._copy)
        _ = self.paste_button.clicked.connect(self._paste)
        _ = self.install_box.toggled.connect(self._install_toggled)
        _ = self.generate_button.clicked.connect(self._generate)
        _ = self.cancel_button.clicked.connect(self.controller.cancel)
        return page

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
        type_grid = QGridLayout(types)
        self.type_buttons = QButtonGroup(self)
        for row, name in enumerate(WORLD_TYPES):
            button = QRadioButton(text(f"type.{name}"))
            about = QLabel(text(f"type.{name}.about"))
            about.setWordWrap(True)
            about.setStyleSheet(MUTED)
            self.type_buttons.addButton(button, row)
            type_grid.addWidget(button, row, 0)
            type_grid.addWidget(about, row, 1)
        type_grid.setColumnStretch(1, 1)
        _ = self.type_buttons.idClicked.connect(self._pick_type)
        return types

    def _progress(self) -> QGroupBox:
        progress = QGroupBox(text("progress"))
        progress_layout = QVBoxLayout(progress)
        self.bar = QProgressBar()
        self.bar.setRange(0, PROGRESS_STEPS)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.stage_list = QListWidget()
        self.stage_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.stage_list.setFixedHeight(140)
        progress_layout.addWidget(self.bar)
        progress_layout.addWidget(self.status)
        progress_layout.addWidget(self.stage_list)
        return progress

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
            for row, control in enumerate(c for c in controls.CONTROLS if c.group == group):
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
        self.name_edit.setPlaceholderText(text("name_hint"))
        font = QFont(self.name_edit.font())
        font.setPointSizeF(font.pointSizeF() * 1.4)
        font.setBold(True)
        self.name_edit.setFont(font)
        self.name_edit.setFrame(False)
        layout.addWidget(self.name_edit)
        self.preview = PreviewView()
        layout.addWidget(self.preview, 3)
        caption = QHBoxLayout()
        self.preview_caption = QLabel()
        self.preview_caption.setWordWrap(True)
        self.preview_caption.setStyleSheet(MUTED)
        self.reveal_button = QPushButton(text("show_world"))
        self.reveal_button.setCheckable(True)
        caption.addWidget(self.preview_caption, 1)
        caption.addWidget(self.reveal_button)
        layout.addLayout(caption)
        layout.addLayout(self._details())
        self.note = QLabel()
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.advice = QLabel()
        self.advice.setWordWrap(True)
        self.advice.setFrameShape(QFrame.Shape.StyledPanel)
        self.advice.setMargin(8)
        layout.addWidget(self.advice)
        layout.addLayout(self._world_buttons())
        self.task_line = QLabel()
        self.task_line.setWordWrap(True)
        self.task_bar = QProgressBar()
        self.task_bar.setRange(0, PROGRESS_STEPS)
        layout.addWidget(self.task_line)
        layout.addWidget(self.task_bar)
        _ = self.name_edit.editingFinished.connect(self._renamed)
        _ = self.reveal_button.toggled.connect(self.controller.set_revealed)
        _ = self.copy_code_button.clicked.connect(self._copy_world_code)
        _ = self.add_button.clicked.connect(self._add)
        _ = self.remove_button.clicked.connect(self._remove)
        _ = self.open_button.clicked.connect(self._open_world)
        _ = self.like_button.clicked.connect(self._like)
        _ = self.delete_button.clicked.connect(self._delete)
        return page

    def _details(self) -> QFormLayout:
        form = QFormLayout()
        self.details = {}
        for key in ("code", "type", "seed", "custom", "made", "build", "generator", "place"):
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

    def _world_buttons(self) -> QHBoxLayout:
        buttons = QHBoxLayout()
        self.add_button = QPushButton(text("add"))
        self.remove_button = QPushButton(text("remove"))
        self.open_button = QPushButton(text("open_folder"))
        self.like_button = QPushButton(text("like_this"))
        self.delete_button = QPushButton(text("delete"))
        for button in (self.add_button, self.remove_button, self.open_button, self.like_button):
            buttons.addWidget(button)
        buttons.addStretch(1)
        buttons.addWidget(self.delete_button)
        return buttons

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
        self.game_line.setText("\n".join(lines))
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
        key = (
            *(f"{w.id}|{w.name}|{controller.placement(w).value}" for w in controller.worlds),
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
            for world in controller.worlds:
                self.world_list.addItem(self._world_item(world))
            for stray in controller.strays:
                item = QListWidgetItem(
                    f"{text('stray_name')}\n{text('stray_line', folder=stray.name)}"
                )
                item.setData(Qt.ItemDataRole.UserRole, f"{STRAY}{stray.name}")
                self.world_list.addItem(item)
            _ = self.world_list.blockSignals(False)  # noqa: FBT003 - Qt's own call
        running = controller.busy and controller.task is Task.GENERATE
        if self.world_list.count():
            self.world_list.item(0).setText(
                text("new_world_running", percent=round(controller.fraction * 100))
                if running
                else text("new_world")
            )
        for row in range(self.world_list.count()):
            item = self.world_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == controller.selection:
                if self.world_list.currentRow() != row:
                    _ = self.world_list.blockSignals(True)  # noqa: FBT003 - Qt's own call
                    self.world_list.setCurrentRow(row)
                    _ = self.world_list.blockSignals(False)  # noqa: FBT003 - Qt's own call
                break

    def _world_item(self, world: World) -> QListWidgetItem:
        controller = self.controller
        when = datetime.fromtimestamp(world.created).astimezone().strftime(DATE)
        place = text(f"list.{controller.placement(world).value}")
        item = QListWidgetItem(
            f"{controller.name(world)}\n{text('world_line', when=when, place=place)}"
        )
        item.setData(Qt.ItemDataRole.UserRole, world.id)
        covered = controller.covered_picture(world)
        if covered is not None:
            item.setIcon(
                QIcon(
                    QPixmap(str(covered)).scaled(
                        *ICON_SIZE,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            )
        return item

    def _refresh_new(self) -> None:
        controller = self.controller
        busy = controller.busy
        self.type_buttons.button(WORLD_TYPES.index(controller.preset)).setChecked(True)
        if not self.seed_edit.hasFocus():
            self.seed_edit.setText(str(controller.seed))
        if not self.code_edit.hasFocus():
            self.code_edit.setText(controller.code)
        self.notice.setText(controller.notice)
        self.notice.setVisible(bool(controller.notice))
        for row in self.rows:
            key = row.control.key
            row.refresh(controller.value(key), changed=key in controller.changes, enabled=not busy)
        count = len(controller.changes)
        self.customized.setText(text("customized", count=count) if count else "")
        self.reset_all.setEnabled(bool(count) and not busy)
        problem = controller.problem()
        try:
            estimate = controller.estimated_locations()
            self.estimate.setText(text("estimate", count=f"{estimate:,}"))
            self.estimate.setStyleSheet(RED if estimate > controls.LOCATION_BUDGET else MUTED)
        except ValueError:
            self.estimate.setText("")
        self.install_box.setChecked(controller.install)
        self.generate_button.setEnabled(problem is None)
        self.generate_button.setToolTip(problem or "")
        generating = controller.task is Task.GENERATE
        self.cancel_button.setEnabled(controller.phase is Phase.RUNNING and generating)
        for widget in (
            self.seed_edit,
            self.random_button,
            self.code_edit,
            self.paste_button,
            self.install_box,
            *self.type_buttons.buttons(),
        ):
            widget.setEnabled(not busy)
        self.bar.setValue(round(controller.fraction * PROGRESS_STEPS) if generating else 0)
        self.status.setText(self._status_line() if generating else text("idle"))
        self.stage_list.clear()
        for label, state in controller.stage_rows():
            mark = MARKS[state] if generating else MARKS["waiting"]
            self.stage_list.addItem(QListWidgetItem(f"{mark}  {label}"))

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

    def _refresh_world(self) -> None:
        controller = self.controller
        world = controller.selected_world()
        if world is None:
            return
        if not self.name_edit.hasFocus():
            self.name_edit.setText(controller.name(world))
        shown = self.preview.show_picture(controller.picture(world))
        state = text("preview_shown" if controller.revealed else "preview_hidden")
        self.preview_caption.setText(
            f"{state} {text('zoom_hint')}" if shown else text("preview_missing")
        )
        _ = self.reveal_button.blockSignals(True)  # noqa: FBT003 - Qt's own call
        self.reveal_button.setChecked(controller.revealed)
        self.reveal_button.setText(text("hide_world" if controller.revealed else "show_world"))
        _ = self.reveal_button.blockSignals(False)  # noqa: FBT003 - Qt's own call
        placement = controller.placement(world)
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
            "place": text("place.in_game", path=mod)
            if placement is Placement.IN_GAME
            else text("place.kept")
            if placement is Placement.KEPT
            else text("place.code_only", seconds=round(world.seconds or 120)),
        }
        for key, value in values.items():
            self.details[key].setText(value)
        notes = [text("standalone")]
        if game_build and world.game_build and world.game_build != game_build:
            notes.insert(0, text("other_build", made=world.game_build, current=game_build))
        self.note.setText("\n\n".join(notes))
        advice = controller.next_step(world) if placement is Placement.IN_GAME else ""
        self.advice.setText(advice)
        self.advice.setVisible(bool(advice))
        problem = controller.world_problem()
        self.add_button.setVisible(placement is not Placement.IN_GAME)
        self.remove_button.setVisible(placement is Placement.IN_GAME)
        for button in (self.add_button, self.remove_button, self.delete_button):
            button.setEnabled(problem is None)
            button.setToolTip(problem or "")
        self.like_button.setEnabled(not controller.busy)
        mine = controller.task_target == world.id and controller.task in {
            Task.ADD,
            Task.REMOVE,
            Task.DELETE,
        }
        self._refresh_task(mine=mine)

    def _refresh_task(self, *, mine: bool) -> None:
        controller = self.controller
        if not mine or controller.phase is Phase.IDLE:
            self.task_line.setText("")
            self.task_bar.setVisible(False)
            return
        if controller.busy:
            label = text(f"task.{controller.task.value}") if controller.task else ""
            running = ", ".join(controller.running)
            self.task_line.setText(f"{label} {running}".strip())
            self.task_bar.setVisible(controller.task is Task.ADD)
            self.task_bar.setValue(round(controller.fraction * PROGRESS_STEPS))
            return
        self.task_bar.setVisible(False)
        self.task_line.setText(
            text("task_failed", message=controller.message)
            if controller.phase is Phase.FAILED
            else ""
        )

    def _refresh_stray(self) -> None:
        stray = self.controller.selected_stray()
        if stray is None:
            return
        self.stray_about.setText(text("stray_about", folder=stray.name))
        problem = self.controller.world_problem()
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
        if 0 <= index < len(WORLD_TYPES):
            self.controller.set_preset(WORLD_TYPES[index])

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
            self.controller.rename(world, self.name_edit.text())

    def _copy_world_code(self) -> None:
        world = self.controller.selected_world()
        if world is not None:
            QApplication.clipboard().setText(world.code)

    def _add(self) -> None:
        problem = self.controller.add_selected()
        if problem:
            self.task_line.setText(problem)

    def _remove(self) -> None:
        problem = self.controller.remove_selected()
        if problem:
            self.task_line.setText(problem)

    def _like(self) -> None:
        world = self.controller.selected_world()
        if world is not None:
            self.controller.like(world)

    def _delete(self) -> None:
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
