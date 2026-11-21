"""The land editor in the classic window: draw the land of a continent of a new world on the area
the generator can fill, from a ready land or from nothing, with ground kinds (mountains, highlands,
lowlands, lakes), and see what the generator will make of it before it begins.

It is the Qt twin of ``desktop/src/components/LandEditor.svelte`` and asks the generator for the
same things through ``rnw.gui.studio``; the drawing itself is ``rnw.gui.land_sheet`` on the
canvas of ``rnw.gui.land_canvas``. Everything slow (a ready land, a check, added terrain, a
picture from a file) runs on a worker so that the window stays awake.
"""

# Qt windows are built in helper methods; every widget exists once the constructor returns.
# pyright: reportUninitializedInstanceVariable=false
# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import math
import threading
from concurrent.futures import ThreadPoolExecutor
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast, override

import numpy as np
from PySide6.QtCore import QObject, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QIcon,
    QImage,
    QKeyEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from rnw.gui import studio
from rnw.gui.controller import Phase, Task
from rnw.gui.land_canvas import (
    AMERICAS,
    AREA,
    HATCH,
    ISLANDS,
    TOOLS,
    Classes,
    LandCanvas,
    Layers,
    backdrop_rgba,
)
from rnw.gui.land_pictures import (
    Drafts,
    Line,
    grey,
    layer_icon,
    say_report,
    swatch,
    thumbnail,
    tool_icon,
)
from rnw.gui.land_sheet import LAND, MAX_SIZE, MIN_SIZE, Rule, Sheet
from rnw.gui.text import explain, text
from rnw.settings import AMERICA

if TYPE_CHECKING:
    from collections.abc import Callable

    from numpy.typing import NDArray
    from PySide6.QtGui import QDragEnterEvent, QDropEvent, QResizeEvent

    from rnw.gui.controller import Controller
    from rnw.landarea import LandArea
    from rnw.settings import NewWorldSettings

KIND_NAMES: Final[tuple[str, ...]] = ("sea", "land", "mountains", "highlands", "lowlands", "lake")
TOOL_KEYS: Final[dict[str, str]] = {
    "b": "brush",
    "e": "eraser",
    "g": "fill",
    "l": "line",
    "r": "rectangle",
    "o": "ellipse",
    "h": "pan",
}
THUMB_ICON: Final[QSize] = QSize(104, 68)
CHECK_DELAY_MS: Final[int] = 350
DRAFT_DELAY_MS: Final[int] = 1200
POLL_MS: Final[int] = 120
MESSAGE_SECONDS: Final[int] = 8
GLOBE_WIDTH: Final[int] = 270
ZOOMS: Final[dict[str, float]] = {"+": 1.25, "=": 1.25, "-": 0.8}
# Below this size the brush changes by a pixel, above it by a quarter.
FINE_SIZE: Final[int] = 8


def resized(size: int, *, larger: bool) -> int:
    """The brush size after ``[`` or ``]``."""
    if larger:
        return min(MAX_SIZE, round(size * 1.25) if size >= FINE_SIZE else size + 1)
    return max(MIN_SIZE, round(size * 0.8) if size > FINE_SIZE else size - 1)


SIZE_AT_START: Final[int] = 7


# -- work off the window's thread ---------------------------------------------------------------


class _Async(QObject):
    """Run work on threads and hand each result back on the window's thread, dropping the results
    of runs that a newer run of the same name has replaced."""

    done: Signal = Signal(str, int, object, object)

    def __init__(self) -> None:
        super().__init__()
        self._pools: dict[str, ThreadPoolExecutor] = {
            "work": ThreadPoolExecutor(max_workers=2, thread_name_prefix="land-editor"),
            "gallery": ThreadPoolExecutor(max_workers=1, thread_name_prefix="land-gallery"),
        }
        self._runs: dict[str, int] = {}
        self._lock: threading.Lock = threading.Lock()
        self._closed: bool = False

    def submit(
        self,
        name: str,
        work: Callable[[], object],
        tag: object = None,
        *,
        pool: str = "work",
        replace: bool = True,
    ) -> int:
        """Start ``work``; ``replace`` makes it the current run of ``name``."""
        with self._lock:
            run = self._runs.get(name, 0) + (1 if replace else 0)
            self._runs[name] = run

        def job() -> None:
            try:
                payload: object = work()
            except Exception as error:  # noqa: BLE001 - the window tells the player what failed
                payload = error
            if self._closed:
                return
            try:
                self.done.emit(name, run, tag, payload)
            except RuntimeError:  # the window is gone
                return

        _ = self._pools[pool].submit(job)
        return run

    def current(self, name: str, run: int) -> bool:
        return self._runs.get(name, 0) == run

    def cancel(self, name: str) -> None:
        """Drop the results of what runs under ``name`` now."""
        with self._lock:
            self._runs[name] = self._runs.get(name, 0) + 1

    def close(self) -> None:
        self._closed = True
        for pool in self._pools.values():
            pool.shutdown(wait=False, cancel_futures=True)


# -- the editor -------------------------------------------------------------------------------


class _Gallery(QListWidget):
    """Ready lands to start from, as small pictures to click."""

    def __init__(self) -> None:
        super().__init__()
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Static)
        self.setIconSize(THUMB_ICON)
        self.setWordWrap(True)
        self.setSpacing(4)
        self.setUniformItemSizes(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSelectionMode(QListWidget.SelectionMode.NoSelection)

    def fit_height(self) -> None:
        """Tall enough for every row of its items, since the panel scrolls, not the gallery."""
        count = self.count()
        if not count:
            self.setFixedHeight(0)
            return
        width = max(self.viewport().width(), THUMB_ICON.width() + 12)
        cell = self.sizeHintForRow(0)
        cell_width = THUMB_ICON.width() + 14
        per_row = max(1, width // cell_width)
        rows = math.ceil(count / per_row)
        self.setFixedHeight(rows * (cell + self.spacing()) + 12)

    @override
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.fit_height()


class LandEditorDialog(QDialog):
    """Draw the land of one continent of the new world, and use it for the world."""

    def __init__(
        self, parent: QWidget | None, controller: Controller, continent: str = AMERICA
    ) -> None:
        super().__init__(parent)
        self.controller: Controller = controller
        self.continent: str = continent
        self.drafts: Drafts = Drafts(controller.data)
        self.setWindowTitle(text("editor.title"))
        self.resize(1180, 760)
        self.setAcceptDrops(True)
        self._work: _Async = _Async()
        _ = self._work.done.connect(self._arrived)
        self.stage: str = "preparing"
        self.sheet: Sheet | None = None
        self.area: LandArea | None = None
        self.settings: NewWorldSettings | None = None
        self.info: dict[str, object] = {}
        self.inside: NDArray[np.bool_] | None = None
        self.greys: NDArray[np.uint8] | None = None
        self.margin: NDArray[np.uint8] | None = None
        self.classes: Classes | None = None
        self.report: dict[str, object] | None = None
        self.lines: list[Line] = []
        self.checking: bool = False
        self.working: bool = False
        self.version: int = 0
        self.seed: int = int.from_bytes(np.random.default_rng().bytes(4), "little") & 0x7FFFFFFF
        self._decorations: int = 0
        self._sketched: str = ""
        self._started: int = 0
        self.used: bool = False
        self._build()
        self._check_timer: QTimer = QTimer(self)
        self._check_timer.setSingleShot(True)
        self._check_timer.setInterval(CHECK_DELAY_MS)
        _ = self._check_timer.timeout.connect(self._run_check)
        self._draft_timer: QTimer = QTimer(self)
        self._draft_timer.setSingleShot(True)
        self._draft_timer.setInterval(DRAFT_DELAY_MS)
        _ = self._draft_timer.timeout.connect(self._save_draft)
        self._poll_timer: QTimer = QTimer(self)
        self._poll_timer.setInterval(POLL_MS)
        _ = self._poll_timer.timeout.connect(self._poll)
        self._begin()

    # -- construction ------------------------------------------------------------------------

    def _build(self) -> None:
        self.canvas: LandCanvas = LandCanvas()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._top())
        self.pages: QStackedWidget = QStackedWidget()
        layout.addWidget(self.pages, 1)
        _ = self.pages.addWidget(self._wait_page())
        _ = self.pages.addWidget(self._failed_page())
        _ = self.pages.addWidget(self._ready_page())
        layout.addWidget(self._footer())
        self._show_stage("preparing")

    def _top(self) -> QWidget:  # noqa: PLR0915 - one bar of buttons, built in order
        bar = QFrame()
        bar.setFrameShape(QFrame.Shape.StyledPanel)
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 4, 8, 4)
        row.addWidget(QLabel(f"<b>{text('editor.title')}</b>"))
        self.continent_group: QButtonGroup = QButtonGroup(self)
        self.continent_buttons: dict[str, QPushButton] = {}
        self.continent_box: QWidget = QWidget()
        switch = QHBoxLayout(self.continent_box)
        switch.setContentsMargins(0, 0, 0, 0)
        for key in self.controller.drawable_continents():
            button = QPushButton(text(f"continent.{key}"))
            button.setCheckable(True)
            button.setChecked(key == self.continent)
            button.setToolTip(text("editor.continent_tip", continent=text(f"continent.{key}")))
            self.continent_group.addButton(button)
            self.continent_buttons[key] = button
            switch.addWidget(button)
            _ = button.clicked.connect(lambda _checked=False, key=key: self._choose(key))
        row.addWidget(self.continent_box)
        self.continent_box.setVisible(len(self.continent_buttons) > 1)
        self.continent_name: QLabel = QLabel(text(f"continent.{self.continent}"))
        self.continent_name.setVisible(len(self.continent_buttons) <= 1)
        row.addWidget(self.continent_name)
        self.size_label: QLabel = QLabel()
        row.addWidget(self.size_label)
        row.addSpacing(8)
        self.undo_button: QToolButton = self._tool_button("↶", f"{text('editor.undo')} (Ctrl+Z)")
        self.redo_button: QToolButton = self._tool_button(
            "↷", f"{text('editor.redo')} (Ctrl+Shift+Z)"
        )
        row.addWidget(self.undo_button)
        row.addWidget(self.redo_button)
        row.addSpacing(8)
        zoom_out = self._tool_button("\u2212", f"{text('editor.zoom_out')} (-)")
        self.zoom_button: QToolButton = self._tool_button("100 %", text("editor.zoom_100"))
        self.zoom_button.setMinimumWidth(56)
        zoom_in = self._tool_button("+", f"{text('editor.zoom_in')} (+)")
        zoom_fit = self._tool_button("⤢", f"{text('editor.zoom_fit')} (0)")
        for button in (zoom_out, self.zoom_button, zoom_in, zoom_fit):
            row.addWidget(button)
        row.addSpacing(8)
        self.layer_drawing: QToolButton = self._layer_button(
            layer_icon((118, 166, 92)), "editor.layer.drawing"
        )
        self.layer_americas: QToolButton = self._layer_button(
            layer_icon(AMERICAS), "editor.layer.americas"
        )
        self.layer_islands: QToolButton = self._layer_button(
            layer_icon(ISLANDS), "editor.layer.islands"
        )
        self.layer_margin: QToolButton = self._layer_button(
            layer_icon(AREA, hatched=True), "editor.layer.margin"
        )
        for button in (
            self.layer_drawing,
            self.layer_americas,
            self.layer_islands,
            self.layer_margin,
        ):
            row.addWidget(button)
            _ = button.toggled.connect(self._layers_changed)
        row.addStretch(1)
        cancel = QPushButton(text("editor.cancel"))
        self.use_button: QPushButton = QPushButton(text("editor.use"))
        self.use_button.setDefault(False)
        self.use_button.setToolTip(text("editor.use_tip"))
        row.addWidget(cancel)
        row.addWidget(self.use_button)
        _ = cancel.clicked.connect(self.reject)
        _ = self.use_button.clicked.connect(self._use)
        _ = self.undo_button.clicked.connect(self._undo)
        _ = self.redo_button.clicked.connect(self._redo)
        _ = zoom_out.clicked.connect(lambda: self.canvas.zoom(0.8))
        _ = zoom_in.clicked.connect(lambda: self.canvas.zoom(1.25))
        _ = zoom_fit.clicked.connect(self.canvas.fit)
        _ = self.zoom_button.clicked.connect(self.canvas.actual_size)
        return bar

    @staticmethod
    def _tool_button(label: str, tip: str) -> QToolButton:
        button = QToolButton()
        button.setText(label)
        button.setToolTip(tip)
        button.setAccessibleName(tip)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    def _layer_button(self, icon: QIcon, key: str) -> QToolButton:
        button = QToolButton()
        button.setIcon(icon)
        button.setCheckable(True)
        button.setChecked(True)
        button.setToolTip(text(key))
        button.setAccessibleName(text(key))
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    def _wait_page(self) -> QWidget:
        page = QWidget()
        column = QVBoxLayout(page)
        column.addStretch(1)
        self.wait_title: QLabel = QLabel(text("editor.preparing"))
        self.wait_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint = QLabel(text("editor.preparing_hint"))
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bar = QProgressBar()
        bar.setRange(0, 0)
        bar.setMaximumWidth(360)
        cancel = QPushButton(text("editor.cancel"))
        for widget in (self.wait_title, hint):
            column.addWidget(widget)
        column.addWidget(bar, 0, Qt.AlignmentFlag.AlignHCenter)
        column.addWidget(cancel, 0, Qt.AlignmentFlag.AlignHCenter)
        column.addStretch(1)
        _ = cancel.clicked.connect(self.reject)
        return page

    def _failed_page(self) -> QWidget:
        page = QWidget()
        column = QVBoxLayout(page)
        column.addStretch(1)
        self.failure: QLabel = QLabel()
        self.failure.setWordWrap(True)
        self.failure.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.failure.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        close = QPushButton(text("editor.close"))
        column.addWidget(self.failure)
        column.addWidget(close, 0, Qt.AlignmentFlag.AlignHCenter)
        column.addStretch(1)
        _ = close.clicked.connect(self.reject)
        return page

    def _ready_page(self) -> QWidget:
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        column.addWidget(self._options())
        body = QHBoxLayout()
        body.setSpacing(0)
        body.addWidget(self._tools())
        body.addWidget(self.canvas, 1)
        body.addWidget(self._side())
        column.addLayout(body, 1)
        _ = self.canvas.committed.connect(self._changed)
        _ = self.canvas.hovered.connect(self._hovered)
        _ = self.canvas.picked.connect(self._pick_kind)
        _ = self.canvas.zoomed.connect(self._zoomed)
        return page

    def _options(self) -> QWidget:
        bar = QFrame()
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 4, 8, 4)
        self.kind_group: QButtonGroup = QButtonGroup(self)
        self.kind_buttons: list[QPushButton] = []
        for number, name in enumerate(KIND_NAMES):
            button = QPushButton(f"{text(f'editor.kind.{name}')}  {number + 1}")
            button.setIcon(swatch(number))
            button.setCheckable(True)
            button.setToolTip(f"{text(f'editor.kind.{name}.tip')} ({number + 1})")
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.kind_group.addButton(button, number)
            self.kind_buttons.append(button)
            row.addWidget(button)
        self.kind_buttons[LAND].setChecked(True)
        _ = self.kind_group.idClicked.connect(self._kind_chosen)
        row.addSpacing(12)
        row.addWidget(QLabel(text("editor.size")))
        self.size_slider: QSlider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(MIN_SIZE, MAX_SIZE)
        self.size_slider.setValue(SIZE_AT_START)
        self.size_slider.setMinimumWidth(120)
        self.size_slider.setAccessibleName(text("editor.size"))
        self.size_slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.size_value: QLabel = QLabel(str(self.size_slider.value()))
        self.size_value.setMinimumWidth(24)
        row.addWidget(self.size_slider)
        row.addWidget(self.size_value)
        row.addSpacing(12)
        self.on_ground: QCheckBox = QCheckBox(text("editor.on_ground"))
        self.on_ground.setToolTip(text("editor.on_ground_tip"))
        self.on_ground.setChecked(True)
        self.on_ground.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.filled: QCheckBox = QCheckBox(text("editor.filled"))
        self.filled.setChecked(True)
        self.filled.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        row.addWidget(self.on_ground)
        row.addWidget(self.filled)
        row.addStretch(1)
        _ = self.size_slider.valueChanged.connect(self._size_changed)
        _ = self.on_ground.toggled.connect(self._rule_changed)
        _ = self.filled.toggled.connect(self._rule_changed)
        return bar

    def _tools(self) -> QWidget:
        bar = QFrame()
        column = QVBoxLayout(bar)
        column.setContentsMargins(6, 6, 6, 6)
        column.setSpacing(4)
        self.tool_group: QButtonGroup = QButtonGroup(self)
        self.tool_buttons: dict[str, QToolButton] = {}
        colour = self.palette().buttonText().color()
        hotkeys = {name: key.upper() for key, name in TOOL_KEYS.items()}
        for name in TOOLS:
            button = QToolButton()
            button.setIcon(tool_icon(name, colour))
            button.setIconSize(QSize(22, 22))
            button.setCheckable(True)
            tip = f"{text(f'editor.tool.{name}')} ({hotkeys[name]})"
            button.setToolTip(tip)
            button.setAccessibleName(tip)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.tool_group.addButton(button)
            self.tool_buttons[name] = button
            column.addWidget(button)
            _ = button.clicked.connect(lambda _checked=False, name=name: self._tool_chosen(name))
        self.tool_buttons["brush"].setChecked(True)
        column.addStretch(1)
        return bar

    def _side(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedWidth(GLOBE_WIDTH + 70)
        inner = QWidget()
        column = QVBoxLayout(inner)
        column.addWidget(self._world_box())
        column.addWidget(self._start_box())
        column.addWidget(self._decorate_box())
        column.addWidget(self._check_box())
        column.addWidget(self._picture_box())
        column.addStretch(1)
        scroll.setWidget(inner)
        return scroll

    def _note(self, words: str = "") -> QLabel:
        label = QLabel(words)
        label.setWordWrap(True)
        label.setStyleSheet("color: palette(placeholder-text)")
        return label

    def _world_box(self) -> QGroupBox:
        self.world_box: QGroupBox = QGroupBox(text("editor.world"))
        column = QVBoxLayout(self.world_box)
        self.globe: QLabel = QLabel()
        self.globe.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.globe_note: QLabel = self._note()
        column.addWidget(self.globe)
        column.addWidget(self.globe_note)
        self.world_box.setVisible(False)
        return self.world_box

    def _start_box(self) -> QGroupBox:
        box = QGroupBox(text("editor.start"))
        column = QVBoxLayout(box)
        again = QPushButton(text("editor.reroll"))
        again.setToolTip(text("editor.reroll_tip"))
        column.addWidget(again, 0, Qt.AlignmentFlag.AlignLeft)
        _ = again.clicked.connect(self._again)
        self.galleries: dict[str, _Gallery] = {}
        self.gallery_titles: dict[str, QLabel] = {}
        for name, title in (
            ("ready", "editor.group_ready"),
            ("known", "editor.group_known"),
            ("sketches", "editor.group_sketches"),
        ):
            label = QLabel(f"<b>{text(title)}</b>")
            gallery = _Gallery()
            self.gallery_titles[name] = label
            self.galleries[name] = gallery
            column.addWidget(label)
            column.addWidget(gallery)
            _ = gallery.itemClicked.connect(self._start_clicked)
        self.sketch_note: QLabel = self._note(text("editor.sketch_composed"))
        column.addWidget(self.sketch_note)
        self.sketch_button: QPushButton = QPushButton(text("editor.sketch_run"))
        self.sketch_button.setToolTip(text("editor.sketch_tip"))
        column.addWidget(self.sketch_button, 0, Qt.AlignmentFlag.AlignLeft)
        _ = self.sketch_button.clicked.connect(self._sketch)
        return box

    def _decorate_box(self) -> QGroupBox:
        box = QGroupBox(text("editor.decorate"))
        column = QVBoxLayout(box)
        column.addWidget(self._note(text("editor.decorate_tip")))
        self.adds: dict[str, QCheckBox] = {}
        for name, on in (
            ("mountains", True),
            ("highlands", True),
            ("lowlands", False),
            ("lakes", True),
        ):
            check = QCheckBox(text(f"editor.add.{name}"))
            check.setChecked(on)
            check.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.adds[name] = check
            column.addWidget(check)
        self.decorate_button: QPushButton = QPushButton(text("editor.decorate_run"))
        column.addWidget(self.decorate_button, 0, Qt.AlignmentFlag.AlignLeft)
        _ = self.decorate_button.clicked.connect(self._decorate)
        return box

    def _check_box(self) -> QGroupBox:
        box = QGroupBox(text("editor.check"))
        column = QVBoxLayout(box)
        self.report_label: QLabel = QLabel(text("editor.checking"))
        self.report_label.setWordWrap(True)
        self.report_label.setTextFormat(Qt.TextFormat.RichText)
        column.addWidget(self.report_label)
        return box

    def _picture_box(self) -> QGroupBox:
        box = QGroupBox(text("editor.picture"))
        grid = QGridLayout(box)
        self.import_button: QPushButton = QPushButton(text("editor.import"))
        self.as_is_button: QPushButton = QPushButton(text("editor.as_is"))
        self.as_is_button.setToolTip(text("editor.as_is_tip"))
        self.export_button: QPushButton = QPushButton(text("editor.export"))
        self.template_button: QPushButton = QPushButton(text("land_template"))
        self.template_button.setToolTip(text("land_template_tip"))
        self.clear_button: QPushButton = QPushButton(text("editor.clear"))
        for number, button in enumerate(
            (
                self.import_button,
                self.as_is_button,
                self.export_button,
                self.template_button,
                self.clear_button,
            )
        ):
            grid.addWidget(button, number, 0)
        _ = self.import_button.clicked.connect(self._import_picture)
        _ = self.as_is_button.clicked.connect(self._use_as_is)
        _ = self.export_button.clicked.connect(self._export_picture)
        _ = self.template_button.clicked.connect(self._save_template)
        _ = self.clear_button.clicked.connect(self._clear_sheet)
        return box

    def _footer(self) -> QWidget:
        bar = QFrame()
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 2, 8, 2)
        self.coordinates: QLabel = QLabel()
        self.coordinates.setMinimumWidth(80)
        self.under: QLabel = QLabel()
        self.under.setMinimumWidth(80)
        self.verdict: QLabel = QLabel()
        self.message: QLabel = QLabel()
        keys = QLabel(text("editor.keys"))
        keys.setStyleSheet("color: palette(placeholder-text)")
        for widget in (self.coordinates, self.under, self.verdict, self.message):
            row.addWidget(widget)
        row.addStretch(1)
        row.addWidget(keys)
        return bar

    # -- stages ------------------------------------------------------------------------------

    def _show_stage(self, stage: str) -> None:
        self.stage = stage
        self.pages.setCurrentIndex({"preparing": 0, "loading": 0, "failed": 1, "ready": 2}[stage])
        self.wait_title.setText(
            text("editor.loading" if stage == "loading" else "editor.preparing")
        )
        ready = stage == "ready"
        self.use_button.setEnabled(False)
        self.continent_box.setEnabled(ready or stage == "failed")
        if not ready:
            self.size_label.setText("")

    def _begin(self) -> None:
        """Cut the area of the continent drawn now (a second from the land cache, else several)."""
        controller = self.controller
        self._started = controller.runs
        problem = controller.prepare_land_area(self.continent)
        if problem:
            self._fail(problem)
            return
        self._show_stage("preparing")
        self._poll_timer.start()

    def _fail(self, message: str) -> None:
        self._poll_timer.stop()
        self.failure.setText(message or text("editor.failed"))
        self._show_stage("failed")

    def _poll(self) -> None:
        """Watch the controller: the area cut, the sketches new, the work done."""
        controller = self.controller
        if self.stage == "preparing":
            if controller.land_sheet(self.continent) is not None and not controller.busy:
                self._open()
            elif (
                not controller.busy
                and controller.phase is Phase.FAILED
                and controller.task is Task.TEMPLATE
                and controller.runs > self._started
            ):
                self._fail(controller.message)
            return
        if self.stage != "ready":
            return
        key = ",".join(str(found.seed) for found in controller.candidates)
        if key != self._sketched:
            self._sketched = key
            self._load_sketches()
        self._refresh_buttons()

    def _open(self) -> None:
        """The area is cut: open the sheet on it."""
        controller = self.controller
        area = controller.land_sheet(self.continent)
        if area is None:
            return
        self._show_stage("loading")
        self.area = area
        self.settings = controller.land_settings(self.continent)
        seed = controller.world_code().seed
        chosen = next(
            (one for one in controller.candidates if one.composed and one.seed == seed), None
        )
        try:
            found = studio.opening(
                area,
                controller.drawings().get(self.continent),
                controller.candidates,
                self.settings,
                chosen,
                self.continent,
            )
            self.greys = grey(cast("str", found["backdrop"]))
            self.margin = grey(cast("str", found["margin"]))
            classes = cast("dict[str, int]", found["classes"])
            self.classes = Classes(
                classes["outside"], classes["area"], classes["islands"], classes["americas"]
            )
            self.inside = self.greys != self.classes.outside
            image = cast("str", found["image"])
            start = (
                studio.kinds_of(image, area)
                if image
                else self.drafts.load(self.continent, area.picture_shape)
            )
            self.sheet = Sheet(cast("int", found["width"]), cast("int", found["height"]), start)
        except (studio.StudioError, OSError, ValueError) as error:
            self._fail(str(error))
            return
        self.info = found
        self._poll_timer.start()
        self.size_label.setText(f"{self.sheet.width} \u00d7 {self.sheet.height}")
        self.canvas.set_sheet(self.sheet, self._back())
        self._show_stage("ready")
        self.canvas.fit()
        self.canvas.setFocus()
        self._show_world(cast("dict[str, object] | None", found.get("world")))
        self._sketched = ",".join(str(one.seed) for one in controller.candidates)
        self._schedule_check()
        self._load_starts()
        self._load_known()
        self._load_sketches()
        self._refresh_buttons()

    def _back(self) -> NDArray[np.uint8]:
        assert self.greys is not None  # noqa: S101 - the sheet is open
        assert self.margin is not None  # noqa: S101 - the sheet is open
        assert self.classes is not None  # noqa: S101 - the sheet is open
        return backdrop_rgba(
            self.greys,
            self.margin,
            self.classes,
            Layers(
                self.layer_americas.isChecked(),
                self.layer_islands.isChecked(),
                self.layer_margin.isChecked(),
            ),
        )

    def _show_world(self, world: dict[str, object] | None) -> None:
        """The whole map with the sheet's frame on it."""
        self.world_box.setVisible(world is not None)
        if world is None:
            return
        picture = QImage.fromData(studio.png_of(cast("str", world["picture"])))
        scaled = picture.scaledToWidth(GLOBE_WIDTH, Qt.TransformationMode.SmoothTransformation)
        pixmap = QPixmap.fromImage(scaled)
        painter = QPainter(pixmap)
        pen = QPen(QColor(*HATCH), 2)
        painter.setPen(pen)
        left, top, width, height = cast("list[float]", world["frame"])
        parts = (
            [(left, top, width, height)]
            if left + width <= 1
            else [(left, top, 1 - left, height), (0.0, top, left + width - 1, height)]
        )
        for x, y, w, h in parts:
            painter.drawRect(
                QRectF(
                    x * pixmap.width(), y * pixmap.height(), w * pixmap.width(), h * pixmap.height()
                )
            )
        _ = painter.end()
        self.globe.setPixmap(pixmap)
        key = (
            "editor.world_sketch"
            if world["sketch"]
            else "editor.world_tip_others"
            if world["others"]
            else "editor.world_tip"
        )
        words = text(key, continent=text(f"continent.{self.continent}"))
        self.globe.setToolTip(words)
        self.globe_note.setText(words)

    # -- drawing choices -----------------------------------------------------------------------

    def _tool_chosen(self, name: str) -> None:
        self.canvas.tool = name
        self.tool_buttons[name].setChecked(True)
        self.canvas.update_cursor()
        self.canvas.update()

    def _kind_chosen(self, kind: int) -> None:
        self.canvas.kind = kind
        if self.canvas.tool in {"eraser", "pan"}:
            self._tool_chosen("brush")

    def _pick_kind(self, kind: int) -> None:
        self.kind_buttons[kind].setChecked(True)
        self._kind_chosen(kind)

    def _size_changed(self, value: int) -> None:
        self.canvas.brush = value
        self.size_value.setText(str(value))
        self.canvas.update()

    def _rule_changed(self) -> None:
        self.canvas.rule = Rule(self.on_ground.isChecked(), self.filled.isChecked())

    def _layers_changed(self) -> None:
        self.canvas.show_drawing = self.layer_drawing.isChecked()
        if self.stage == "ready" and self.greys is not None:
            self.canvas.set_backdrop(self._back())
        self.canvas.update()

    def _zoomed(self, scale: float) -> None:
        self.zoom_button.setText(f"{round(scale * 100)} %")

    def _hovered(self, x: int, y: int) -> None:
        sheet = self.sheet
        if sheet is None or x < 0 or y < 0:
            self.coordinates.setText("")
            self.under.setText("")
            return
        self.coordinates.setText(f"{x}, {y}")
        self.under.setText(text(f"editor.kind.{KIND_NAMES[sheet.get(x, y)]}"))

    # -- the sheet changed -------------------------------------------------------------------

    def _changed(self) -> None:
        self.version += 1
        self._schedule_check()
        self._draft_timer.start()
        self._refresh_buttons()

    def _undo(self) -> None:
        if self.sheet is not None and self.sheet.undo():
            self.canvas.refresh()
            self._changed()

    def _redo(self) -> None:
        if self.sheet is not None and self.sheet.redo():
            self.canvas.refresh()
            self._changed()

    def take(self, kinds: NDArray[np.uint8]) -> bool:
        """Put a drawing on the sheet as one step of the undo; whether it differs."""
        sheet = self.sheet
        if sheet is None:
            return False
        different = sheet.replace(kinds)
        self.canvas.repaint_all()
        if different:
            self._changed()
        return different

    def _clear_sheet(self) -> None:
        sheet = self.sheet
        if sheet is not None and sheet.clear():
            self.canvas.repaint_all()
            self._changed()

    def _refresh_buttons(self) -> None:
        sheet = self.sheet
        ready = self.stage == "ready" and sheet is not None
        controller = self.controller
        self.undo_button.setEnabled(ready and sheet is not None and sheet.can_undo)
        self.redo_button.setEnabled(ready and sheet is not None and sheet.can_redo)
        empty = sheet is None or sheet.empty
        refused = self.report is None or cast("str", self.report["refusal"]) != ""
        usable = ready and not self.working and not self.checking and not refused
        self.use_button.setEnabled(usable)
        self.use_button.setToolTip(
            text("editor.use_blocked") if refused else text("editor.use_tip")
        )
        self.decorate_button.setEnabled(
            ready
            and not self.working
            and not empty
            and any(c.isChecked() for c in self.adds.values())
        )
        for button in (self.import_button, self.as_is_button):
            button.setEnabled(ready and not self.working)
        self.export_button.setEnabled(ready and not empty)
        self.clear_button.setEnabled(ready and not empty)
        self.template_button.setEnabled(
            ready and not controller.busy and controller.game is not None
        )
        sketching = controller.busy and controller.task is Task.CANDIDATES
        # With other continents switched on a sketch shows the whole world: it is chosen on the new
        # world's page, and the editor then offers its land of the continent drawn here.
        composed = any(on for key, on in controller.continent_selection().items() if key != AMERICA)
        self.sketch_note.setVisible(composed)
        self.sketch_button.setEnabled(
            ready
            and not sketching
            and not composed
            and controller.sketch_problem() is None
            and not controller.busy
        )
        self.sketch_button.setText(
            controller.running_text() or text("stage.candidates")
            if sketching
            else text("editor.sketch_run")
        )
        self._show_verdict()

    def _show_verdict(self) -> None:
        if self.stage != "ready" or not self.lines or self.checking:
            self.verdict.setText("")
            return
        first = self.lines[0]
        mark = {"ok": "✓", "warn": "⚠", "error": "✕"}[first.level]
        self.verdict.setText(f"{mark} {first.says()}")
        self.verdict.setToolTip(first.says())

    # -- what the generator says --------------------------------------------------------------

    def _schedule_check(self) -> None:
        self.checking = True
        self._check_timer.start()
        self._refresh_buttons()

    def _run_check(self) -> None:
        sheet, area, settings = self.sheet, self.area, self.settings
        if sheet is None or area is None or settings is None:
            return
        kinds = sheet.kinds.copy()
        _ = self._work.submit("check", lambda: studio.report_of(kinds, area, settings))

    def _show_report(self, report: dict[str, object]) -> None:
        self.report = report
        self.lines = say_report(report)
        self.checking = False
        marks = {"ok": "✓", "warn": "⚠", "error": "✕"}
        self.report_label.setText(
            "<br>".join(f"{marks[line.level]} {escape(line.says())}" for line in self.lines)
        )
        self.canvas.marks = [
            (int(place[0]), int(place[1]))
            for place in cast("list[list[int]]", report["open_lakes"])
        ]
        self.canvas.update()
        self._refresh_buttons()

    def _tell(self, words: str) -> None:
        self.message.setText(words)
        QTimer.singleShot(
            MESSAGE_SECONDS * 1000,
            lambda: self.message.setText("") if self.message.text() == words else None,
        )

    # -- the ready lands -----------------------------------------------------------------------

    def _add_tile(self, group: str, label: str, tag: str) -> int:
        gallery = self.galleries[group]
        item = QListWidgetItem(label)
        item.setToolTip(label)
        item.setData(Qt.ItemDataRole.UserRole, tag)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setSizeHint(QSize(THUMB_ICON.width() + 12, THUMB_ICON.height() + 38))
        gallery.addItem(item)
        gallery.fit_height()
        return gallery.count() - 1

    def _fill_tile(self, group: str, index: int, kinds: NDArray[np.uint8]) -> None:
        gallery = self.galleries[group]
        if index >= gallery.count() or self.inside is None:
            return
        item = gallery.item(index)
        item.setIcon(QIcon(thumbnail(kinds, self.inside)))
        item.setData(Qt.ItemDataRole.UserRole + 1, kinds)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)

    def _start_clicked(self, item: QListWidgetItem) -> None:
        kinds = item.data(Qt.ItemDataRole.UserRole + 1)
        if isinstance(kinds, np.ndarray):
            _ = self.take(cast("NDArray[np.uint8]", kinds))

    def _own_land(self) -> str:
        return (
            text("editor.americas")
            if self.continent == AMERICA
            else text(f"editor.own.{self.continent}")
        )

    def _load_starts(self) -> None:
        area, settings = self.area, self.settings
        if area is None or settings is None:
            return
        gallery = self.galleries["ready"]
        gallery.clear()
        self._work.cancel("ready")
        seed = self.seed
        sheet_area: LandArea = area
        land_settings: NewWorldSettings = settings
        entries: list[tuple[str, Callable[[], str]]] = [
            (
                text(f"editor.preset.{preset}"),
                lambda preset=preset: studio.preset(sheet_area, preset, seed, land_settings),
            )
            for preset in cast("list[str]", self.info["presets"])
        ]
        entries.append((self._own_land(), lambda: studio.real_americas(area)))
        for label, make in entries:
            index = self._add_tile("ready", label, label)
            _ = self._work.submit(
                "ready",
                lambda make=make: studio.kinds_of(make(), area),
                ("ready", index),
                pool="gallery",
                replace=False,
            )

    def _load_known(self) -> None:
        area, settings = self.area, self.settings
        if area is None or settings is None:
            return
        self.galleries["known"].clear()
        self._work.cancel("known")
        lands = cast("list[str]", self.info["lands"])
        self.gallery_titles["known"].setVisible(bool(lands))
        self.galleries["known"].setVisible(bool(lands))
        for land in lands:
            index = self._add_tile("known", text(f"editor.land.{land}"), land)
            _ = self._work.submit(
                "known",
                lambda land=land: studio.kinds_of(studio.known(area, land, settings), area),
                ("known", index),
                pool="gallery",
                replace=False,
            )

    def _load_sketches(self) -> None:
        """The continents sketched in the window (one task, six pictures) join the ready lands."""
        area = self.area
        controller = self.controller
        if area is None:
            return
        self.galleries["sketches"].clear()
        self._work.cancel("sketches")
        sheet_area: LandArea = area
        found = list(controller.candidates)
        composed = bool(self.info.get("composed"))
        starts: list[tuple[str, Callable[[], str]]] = []
        if composed:
            starts.append(
                (
                    text("editor.composed_start"),
                    lambda: studio.composed_start(area, found, controller.world_code().seed),
                )
            )
        elif not (found and found[0].composed):
            starts.extend(
                (
                    text("editor.sketch", number=number + 1),
                    lambda number=number: studio.sketch(sheet_area, found, number),
                )
                for number, one in enumerate(found)
                if one.picture.shape[:2] == area.picture_shape
            )
        self.gallery_titles["sketches"].setVisible(bool(starts))
        self.galleries["sketches"].setVisible(bool(starts))
        for label, make in starts:
            index = self._add_tile("sketches", label, label)
            _ = self._work.submit(
                "sketches",
                lambda make=make: studio.kinds_of(make(), area),
                ("sketches", index),
                pool="gallery",
                replace=False,
            )

    def _again(self) -> None:
        self.seed = int.from_bytes(np.random.default_rng().bytes(4), "little") & 0x7FFFFFFF
        self._load_starts()

    def _sketch(self) -> None:
        problem = self.controller.sketch_candidates()
        if problem:
            self._tell(problem)

    # -- added terrain ---------------------------------------------------------------------------

    def _decorate(self) -> None:
        sheet = self.sheet
        if sheet is None or self.working:
            return
        parts = [name for name, check in self.adds.items() if check.isChecked()]
        if not parts:
            return
        self.working = True
        self._decorations += 1
        kinds, seed = sheet.kinds.copy(), self.seed + self._decorations
        _ = self._work.submit("decorate", lambda: studio.decorated(kinds, seed, parts))
        self._refresh_buttons()

    # -- pictures --------------------------------------------------------------------------------

    def _import_picture(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(
            self, text("land_image_title"), str(Path.home()), text("land_image_files")
        )
        if chosen:
            self.bring(Path(chosen))

    def bring(self, path: Path) -> None:
        """A picture dropped on the editor, or chosen, goes onto the sheet."""
        area = self.area
        if area is None or self.working or self.stage != "ready":
            return
        self.working = True
        _ = self._work.submit("import", lambda: studio.imported(area, path))
        self._refresh_buttons()

    def _use_as_is(self) -> None:
        """The picture as it is, at its own size and without the editor (finer than the sheet)."""
        chosen, _ = QFileDialog.getOpenFileName(
            self, text("land_image_title"), str(Path.home()), text("land_image_files")
        )
        if not chosen:
            return
        problem = self.controller.choose_land_image(Path(chosen), self.continent)
        if problem:
            _ = QMessageBox.warning(self, text("land_image"), problem)
            return
        self.used = True
        self.accept()

    def _export_picture(self) -> None:
        sheet = self.sheet
        if sheet is None:
            return
        chosen, _ = QFileDialog.getSaveFileName(
            self, text("editor.export"), str(Path.home() / "new-world-land.png"), "PNG (*.png)"
        )
        if not chosen:
            return
        try:
            _ = Path(chosen).write_bytes(studio.kinds_png(sheet.kinds))
        except OSError as error:
            _ = QMessageBox.warning(self, text("editor.export"), explain(error))
            return
        self._tell(text("picture_saved", path=chosen))

    def _save_template(self) -> None:
        """The grey picture of the area to paint on elsewhere, saved where the player says."""
        title = text("land_template")
        chosen, _ = QFileDialog.getSaveFileName(
            self, title, str(Path.home() / "new-world-template.png"), "PNG (*.png)"
        )
        if not chosen:
            return
        problem = self.controller.save_land_template(Path(chosen), self.continent)
        if problem:
            _ = QMessageBox.warning(self, title, problem)
            return
        self._tell(text("picture_saved", path=chosen))

    def _use(self) -> None:
        sheet = self.sheet
        if sheet is None or not self.use_button.isEnabled():
            return
        problem = self.controller.use_land_picture(studio.kinds_png(sheet.kinds), self.continent)
        if problem:
            _ = QMessageBox.warning(self, text("editor.title"), problem)
            return
        self.used = True
        self.accept()

    # -- results from the workers -------------------------------------------------------------

    def _arrived(self, name: str, run: int, tag: object, payload: object) -> None:
        if name == "check":
            if self._work.current(name, run) and isinstance(payload, dict):
                self._show_report(cast("dict[str, object]", payload))
        elif name == "decorate":
            self._decorated(payload)
        elif name == "import":
            self._imported(payload)
        elif (
            isinstance(tag, tuple)
            and isinstance(payload, np.ndarray)
            and self._work.current(name, run)
        ):
            # a tile of a gallery: ``tag`` is (group, index)
            group, index = cast("tuple[str, int]", tag)
            self._fill_tile(group, index, cast("NDArray[np.uint8]", payload))

    def _decorated(self, payload: object) -> None:
        self.working = False
        if isinstance(payload, np.ndarray):
            if not self.take(cast("NDArray[np.uint8]", payload)):
                self._tell(text("editor.nothing_added"))
        elif isinstance(payload, Exception):
            self._tell(explain(payload))
        self._refresh_buttons()

    def _imported(self, payload: object) -> None:
        self.working = False
        if isinstance(payload, Exception):
            _ = QMessageBox.warning(self, text("editor.import"), explain(payload))
        elif isinstance(payload, dict) and self.area is not None:
            got = cast("dict[str, str]", payload)
            try:
                _ = self.take(studio.kinds_of(got["image"], self.area))
            except studio.StudioError as error:
                _ = QMessageBox.warning(self, text("editor.import"), str(error))
            else:
                if got["fit"] in {"stretched", "centered"}:
                    self._tell(text(f"editor.fit.{got['fit']}"))
        self._refresh_buttons()

    # -- drafts and closing --------------------------------------------------------------------

    def _save_draft(self) -> None:
        if self.sheet is not None and self.version > 0:
            self.drafts.save(self.continent, self.sheet.kinds)

    def _choose(self, key: str) -> None:
        """Go to another continent's sheet: this one's draft is kept, its pictures are let go."""
        if key == self.continent or self.stage in {"preparing", "loading"}:
            self.continent_buttons[self.continent].setChecked(True)
            return
        self._save_draft()
        self._draft_timer.stop()
        self._check_timer.stop()
        for name in ("check", "ready", "known", "sketches", "decorate", "import"):
            self._work.cancel(name)
        self.working = False
        self.checking = False
        self.sheet = None
        self.report = None
        self.lines = []
        self.version = 0
        self.canvas.clear()
        for gallery in self.galleries.values():
            gallery.clear()
        self.continent = key
        self.continent_name.setText(text(f"continent.{key}"))
        self.report_label.setText(text("editor.checking"))
        self._begin()

    def _finish(self) -> None:
        self._poll_timer.stop()
        self._check_timer.stop()
        self._draft_timer.stop()
        self._save_draft()
        self._work.close()

    @override
    def done(self, result: int) -> None:
        self._finish()
        super().done(result)

    @override
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.stage == "ready" and self._key(event):
            event.accept()
        else:
            super().keyPressEvent(event)

    def _key(self, event: QKeyEvent) -> bool:
        """Carry out a key of the editor; whether it was one."""
        control = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        key = event.key()
        if control and key in {Qt.Key.Key_Z, Qt.Key.Key_Y}:
            if key == Qt.Key.Key_Y or event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._redo()
            else:
                self._undo()
            return True
        if control or event.modifiers() & Qt.KeyboardModifier.AltModifier:
            return False
        letter = event.text().lower()
        if letter in TOOL_KEYS:
            self._tool_chosen(TOOL_KEYS[letter])
        elif len(letter) == 1 and letter in "123456":
            self._pick_kind(int(letter) - 1)
        elif letter in ZOOMS:
            self.canvas.zoom(ZOOMS[letter])
        elif letter in {"[", "]"}:
            self.size_slider.setValue(resized(self.size_slider.value(), larger=letter == "]"))
        elif letter == "0":
            self.canvas.fit()
        elif key == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.canvas.space_down = True
            self.canvas.update_cursor()
        else:
            return False
        return True

    @override
    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.canvas.space_down = False
            self.canvas.update_cursor()
        super().keyReleaseEvent(event)

    @override
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    @override
    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.bring(Path(urls[0].toLocalFile()))
            event.acceptProposedAction()


__all__ = ["Drafts", "LandEditorDialog", "Line", "say_report", "thumbnail"]
