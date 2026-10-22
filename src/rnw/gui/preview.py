"""A picture that zooms with the wheel, moves by dragging and fits on a double-click.

Used for a world's preview and for the maps of its atlas (``rnw.gui.maps``).
"""

# Qt stubs type signals and widgets loosely.
# pyright: reportAny=false

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Final, override

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView

if TYPE_CHECKING:
    from pathlib import Path

    from PySide6.QtGui import QImage, QMouseEvent, QResizeEvent, QWheelEvent

ZOOM_STEP: Final[float] = 1.25
ZOOM_LIMIT: Final[float] = 16.0


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

    def show_image(self, image: QImage, key: str) -> None:
        """Show ``image``, drawn afresh when ``key`` differs from the last one shown.

        The view keeps its zoom and position while only the colours change (the same ``key``
        prefix is the caller's to keep), and fits when the size of the picture changes.
        """
        old = self._item.pixmap()
        picture = QPixmap.fromImage(image)
        self._path = key
        self._item.setPixmap(picture)
        self._scene.setSceneRect(QRectF(picture.rect()))
        if old.isNull() or old.size() != picture.size():
            self.fit()

    def pixel_at(self, x: int, y: int) -> tuple[int, int] | None:
        """The (row, column) of the picture under the viewport point (x, y), or None."""
        if self._item.pixmap().isNull():
            return None
        point = self.mapToScene(x, y)
        row, column = int(point.y()), int(point.x())
        pixmap = self._item.pixmap()
        if 0 <= row < pixmap.height() and 0 <= column < pixmap.width():
            return row, column
        return None

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
