"""The land editor's canvas in the classic window: the area's backdrop, the drawing over it and the
pointer that draws, painted on the processor so that it also runs where the Tauri window cannot.

It owns what is shown (the camera, the layers, the tool in use) and nothing of what the generator
says: the dialog gives it a sheet and the colours of the area and listens to what the sheet becomes.
"""

# Qt windows are built in helper methods; every widget exists once the constructor returns.
# pyright: reportUninitializedInstanceVariable=false
# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, override

import numpy as np
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget

from rnw.gui.land_sheet import (
    DEFAULT_RULE,
    LAND,
    SEA,
    SHOWN,
    Rule,
    Sheet,
)
from rnw.gui.text import text

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from PySide6.QtGui import QMouseEvent, QPaintEvent, QResizeEvent, QWheelEvent

MIN_ZOOM: Final[float] = 0.1
MAX_ZOOM: Final[float] = 24.0
FIT_MARGIN: Final[int] = 24
# What the sheet is drawn on (the Tauri editor's colours): outside, the area's sea, the Americas,
# the island groups and the hatching of the coast margin where land is dropped.
OUTSIDE: Final[tuple[int, int, int]] = (20, 22, 27)
AREA: Final[tuple[int, int, int]] = (34, 62, 100)
AMERICAS: Final[tuple[int, int, int]] = (58, 100, 146)
ISLANDS: Final[tuple[int, int, int]] = (44, 96, 104)
HATCH: Final[tuple[int, int, int]] = (226, 96, 90)
VIEW_BACKGROUND: Final[tuple[int, int, int]] = (14, 15, 19)
TOOLS: Final[tuple[str, ...]] = ("brush", "eraser", "fill", "line", "rectangle", "ellipse", "pan")
SHAPES: Final[frozenset[str]] = frozenset({"line", "rectangle", "ellipse"})
HOVER_RING: Final[frozenset[str]] = frozenset({"brush", "eraser", "line"})


@dataclass(frozen=True, slots=True)
class Classes:
    """The greys the generator's picture of the area says its classes with."""

    outside: int
    area: int
    islands: int
    americas: int


@dataclass(frozen=True, slots=True)
class Layers:
    """What of the area is shown under the drawing."""

    americas: bool = True
    islands: bool = True
    margin: bool = True


def clamp_zoom(scale: float) -> float:
    return max(MIN_ZOOM, min(MAX_ZOOM, scale))


def backdrop_rgba(
    greys: NDArray[np.uint8],
    margin: NDArray[np.uint8],
    classes: Classes,
    layers: Layers,
) -> NDArray[np.uint8]:
    """What the sheet is drawn on, from the greys of the generator's picture of the area."""
    rgba = np.empty((*greys.shape, 4), dtype=np.uint8)
    rgba[...] = (*OUTSIDE, 255)
    rgba[greys == classes.area, :3] = AREA
    rgba[greys == classes.americas, :3] = AMERICAS if layers.americas else AREA
    rgba[greys == classes.islands, :3] = ISLANDS if layers.islands else AREA
    if layers.margin:
        rows, columns = np.indices(greys.shape)
        hatched = (margin == 255) & (((rows + columns) % 6) < 2)  # noqa: PLR2004 - the hatch
        shown = rgba[hatched, :3].astype(np.float64) * 0.45 + np.array(HATCH) * 0.55
        rgba[hatched, :3] = np.round(shown).astype(np.uint8)
    return rgba


def _image(rgba: NDArray[np.uint8]) -> QImage:
    """A QImage over the array's own memory: the array must outlive it."""
    rows, columns = rgba.shape[:2]
    return QImage(rgba.data, columns, rows, columns * 4, QImage.Format.Format_RGBA8888)


class LandCanvas(QWidget):
    """The sheet on its area, zoomed and panned, drawn on with the tool chosen."""

    # A stroke ended and changed the sheet, the pointer moved over a pixel (-1, -1 when it left),
    # the right button took a kind, and the zoom changed.
    committed: Signal = Signal()
    hovered: Signal = Signal(int, int)
    picked: Signal = Signal(int)
    zoomed: Signal = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self.sheet: Sheet | None = None
        self.tool: str = "brush"
        self.kind: int = LAND
        self.brush: int = 7
        self.rule: Rule = DEFAULT_RULE
        self.show_drawing: bool = True
        self.space_down: bool = False
        self.marks: list[tuple[int, int]] = []
        self._back: NDArray[np.uint8] | None = None
        self._back_image: QImage | None = None
        self._shown: NDArray[np.uint8] | None = None
        self._shown_image: QImage | None = None
        self.scale: float = 1.0
        self.offset: QPointF = QPointF(0, 0)
        self._hover: tuple[int, int] | None = None
        self._anchor: tuple[int, int] | None = None
        self._last: tuple[int, int] | None = None
        self._pan: tuple[QPointF, QPointF] | None = None
        self._auto_fit: bool = True
        self.setMouseTracking(True)
        self.setMinimumSize(320, 240)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

    # -- what is shown -------------------------------------------------------------------------

    def set_sheet(self, sheet: Sheet, back: NDArray[np.uint8]) -> None:
        """Show ``sheet`` over the backdrop ``back`` (RGBA), the whole of it in view."""
        self.sheet = sheet
        self.set_backdrop(back)
        self._shown = np.ascontiguousarray(SHOWN[sheet.kinds])
        self._shown_image = _image(self._shown)
        _ = sheet.take_dirty()
        self.marks = []
        self.fit()

    def set_backdrop(self, back: NDArray[np.uint8]) -> None:
        self._back = np.ascontiguousarray(back)
        self._back_image = _image(self._back)
        self.update()

    def clear(self) -> None:
        """Let go of the sheet and its pictures."""
        self.sheet = None
        self._back = self._back_image = self._shown = self._shown_image = None
        self.marks = []
        self.update()

    def refresh(self) -> None:
        """Bring the drawing's picture up to what the sheet has become, and paint."""
        sheet = self.sheet
        if sheet is None or self._shown is None:
            return
        box = sheet.take_dirty()
        if box is not None:
            part = sheet.kinds[box.y0 : box.y1 + 1, box.x0 : box.x1 + 1]
            self._shown[box.y0 : box.y1 + 1, box.x0 : box.x1 + 1] = SHOWN[part]
        self.update()

    def repaint_all(self) -> None:
        """The whole sheet changed (a picture was put on it)."""
        sheet = self.sheet
        if sheet is None or self._shown is None:
            return
        _ = sheet.take_dirty()
        self._shown[...] = SHOWN[sheet.kinds]
        self.update()

    # -- the camera ----------------------------------------------------------------------------

    def fit(self) -> None:
        """The sheet at the largest scale that fits the widget with a margin, centred."""
        sheet = self.sheet
        if sheet is None:
            return
        scale = clamp_zoom(
            min(
                (self.width() - FIT_MARGIN * 2) / sheet.width,
                (self.height() - FIT_MARGIN * 2) / sheet.height,
            )
        )
        self.scale = scale
        self.offset = QPointF(
            (self.width() - sheet.width * scale) / 2, (self.height() - sheet.height * scale) / 2
        )
        self._auto_fit = True
        self.zoomed.emit(self.scale)
        self.update()

    def zoom(self, factor: float, at: QPointF | None = None) -> None:
        """Zoom by ``factor`` with the point under ``at`` (the middle by default) staying put."""
        point = QPointF(self.width() / 2, self.height() / 2) if at is None else at
        scale = clamp_zoom(self.scale * factor)
        sheet_x = (point.x() - self.offset.x()) / self.scale
        sheet_y = (point.y() - self.offset.y()) / self.scale
        self.scale = scale
        self.offset = QPointF(point.x() - sheet_x * scale, point.y() - sheet_y * scale)
        self._auto_fit = False
        self.zoomed.emit(self.scale)
        self.update()

    def actual_size(self) -> None:
        self.zoom(1 / self.scale)

    def _sheet_point(self, point: QPointF) -> tuple[int, int]:
        return (
            math.floor((point.x() - self.offset.x()) / self.scale),
            math.floor((point.y() - self.offset.y()) / self.scale),
        )

    # -- painting ------------------------------------------------------------------------------

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(*VIEW_BACKGROUND))
        sheet = self.sheet
        if sheet is None or self._back_image is None:
            _ = painter.end()
            return
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, self.scale < 1)
        painter.translate(self.offset)
        painter.scale(self.scale, self.scale)
        painter.drawImage(0, 0, self._back_image)
        if self.show_drawing and self._shown_image is not None:
            painter.drawImage(0, 0, self._shown_image)
        if self.marks:
            pen = QPen(QColor(*HATCH))
            pen.setWidthF(3)
            pen.setCosmetic(False)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for x, y in self.marks:
                painter.drawEllipse(QPointF(x + 0.5, y + 0.5), 12.0, 12.0)
        if self._hover is not None and self._ring() and self._pan is None and not self.space_down:
            ring = QPen(QColor(255, 255, 255, 200))
            ring.setWidthF(1 / self.scale)
            painter.setPen(ring)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            x, y = self._hover
            half = (self.brush - 1) / 2
            painter.drawEllipse(QRectF(x - half, y - half, self.brush, self.brush))
        painter.resetTransform()
        if sheet.empty:
            painter.setPen(QColor(200, 205, 215))
            _ = painter.drawText(
                self.rect().adjusted(24, 24, -24, -24),
                int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
                text("editor.hint"),
            )
        _ = painter.end()

    def _ring(self) -> bool:
        return self.tool in HOVER_RING

    @override
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        # Until the player has moved the view, it keeps the whole sheet in sight as the widget
        # takes its size.
        if self._auto_fit:
            self.fit()

    # -- the pointer ---------------------------------------------------------------------------

    @property
    def painting(self) -> int:
        return SEA if self.tool == "eraser" else self.kind

    def _cursor(self) -> Qt.CursorShape:
        if self.space_down or self.tool == "pan":
            return Qt.CursorShape.ClosedHandCursor if self._pan else Qt.CursorShape.OpenHandCursor
        return Qt.CursorShape.CrossCursor

    def update_cursor(self) -> None:
        self.setCursor(self._cursor())

    @override
    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.sheet is None:
            return
        self.zoom(math.exp(event.angleDelta().y() * 0.0018), event.position())
        event.accept()

    @override
    def mousePressEvent(self, event: QMouseEvent) -> None:
        sheet = self.sheet
        if sheet is None:
            return
        button = event.button()
        point = self._sheet_point(event.position())
        if button == Qt.MouseButton.MiddleButton or (
            button == Qt.MouseButton.LeftButton and (self.tool == "pan" or self.space_down)
        ):
            self._pan = (event.position(), QPointF(self.offset))
            self.update_cursor()
            return
        if button == Qt.MouseButton.RightButton:
            # The right button takes the kind under the pointer, as a pipette.
            self.picked.emit(sheet.get(*point))
            return
        if button != Qt.MouseButton.LeftButton:
            return
        sheet.begin()
        if self.tool in {"brush", "eraser"}:
            sheet.stamp(*point, self.brush, self.painting, self.rule)
            self._last = point
        elif self.tool == "fill":
            _ = sheet.fill(*point, self.painting, self.rule)
            self._finish()
            return
        else:
            self._anchor = point
            self._shape(point, point)
        self.refresh()

    @override
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        sheet = self.sheet
        if sheet is None:
            return
        point = self._sheet_point(event.position())
        self._hover = point
        self.hovered.emit(*point)
        if self._pan is not None:
            start, offset = self._pan
            self.offset = QPointF(
                offset.x() + event.position().x() - start.x(),
                offset.y() + event.position().y() - start.y(),
            )
            self._auto_fit = False
            self.update()
            return
        if not sheet.drawing:
            if self._ring():
                self.update()
            return
        if self._last is not None and self.tool in {"brush", "eraser"}:
            sheet.stroke(*self._last, *point, self.brush, self.painting, self.rule)
            self._last = point
        elif self._anchor is not None:
            sheet.restore()
            self._shape(self._anchor, point)
        self.refresh()

    @override
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        del event
        self._pan = None
        self.update_cursor()
        if self.sheet is not None and self.sheet.drawing:
            self._finish()

    @override
    def leaveEvent(self, event: QEvent) -> None:
        del event
        self._hover = None
        self.hovered.emit(-1, -1)
        self.update()

    def _shape(self, start: tuple[int, int], end: tuple[int, int]) -> None:
        sheet = self.sheet
        if sheet is None:
            return
        drawn = {"line": sheet.stroke, "rectangle": sheet.rectangle, "ellipse": sheet.ellipse}
        make = drawn.get(self.tool)
        if make is not None:
            make(*start, *end, self.brush, self.painting, self.rule)

    def _finish(self) -> None:
        sheet = self.sheet
        self._anchor = self._last = None
        if sheet is None:
            return
        changed = sheet.commit()
        self.refresh()
        if changed:
            self.committed.emit()
