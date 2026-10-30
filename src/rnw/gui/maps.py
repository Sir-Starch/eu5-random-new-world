"""The maps of a world in the classic window, drawn as the Tauri window draws them.

Ten lenses over the physical map (``rnw.gui.mapstyle``), names and marks written at every zoom,
a legend that lights its entry under the pointer, isolates it on a click and zooms to it on a
double-click, one search over countries, cultures, religions, resources, areas and places, the
card of a location clicked, whose values isolate their country, culture, religion, resource or
area, and the facts of the location under the pointer. Countries shows states as the game's
political map does; Show tribes adds the tribes. Everything is drawn by the processor with
NumPy and Qt Widgets, so the window needs no web view or OpenGL (it runs under Proton as it is).

The panel knows nothing of the game or of how worlds are kept; it is given an ``Atlas`` (or none)
and whether its New World may be shown, and tells its owner when the player asks to reveal it
(ADR 0010, B). A world that is not revealed shows only a notice and a button.
"""

# Qt stubs type signals and widgets loosely; NumPy stubs type array arithmetic as Any.
# pyright: reportAny=false, reportUninitializedInstanceVariable=false

from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, override

import numpy as np
from PySide6.QtCore import (
    QEvent,
    QObject,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QGuiApplication,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QShortcut,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsView,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from rnw import atlas as atlas_module
from rnw.app import logs
from rnw.gui import mapstyle
from rnw.gui.preview import ZOOM_LIMIT, PreviewView
from rnw.gui.text import grouped, text

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    from numpy.typing import NDArray
    from PySide6.QtGui import QMouseEvent, QResizeEvent, QShowEvent, QWheelEvent

    from rnw.atlas import Atlas

MUTED: Final[str] = ""
SWATCH: Final[int] = 12
RESULTS: Final[int] = 80
# Location borders show from this zoom on, and other lenses' country borders from that one.
LOCATION_ZOOM: Final[float] = 2.2
BORDER_ZOOM: Final[float] = 0.6
PREVIEW_DELAY: Final[int] = 120
SIDE_WIDTH: Final[int] = 270
# Pictures of lenses kept for going back to them without drawing again.
KEPT_PICTURES: Final[int] = 4


@dataclass(frozen=True, slots=True)
class NameStyle:
    """How a kind of name is written: its largest size in pixels, how it grows with what it
    names (by the square root of its pixels and by how deep its point lies inside), its letters
    and its ink, as the Tauri window writes it."""

    largest: float
    area: float
    room: float
    upper: bool
    spacing: float
    weight: QFont.Weight
    italic: bool
    fill: QColor
    halo: QColor


NAME_STYLES: Final[dict[str, NameStyle]] = {
    "country": NameStyle(
        largest=20, area=0.34, room=1.5, upper=True, spacing=0.06, weight=QFont.Weight.DemiBold,
        italic=False, fill=QColor(30, 24, 16, 230), halo=QColor(255, 251, 240, 158),
    ),
    "tribe": NameStyle(
        largest=14, area=0.26, room=1.2, upper=False, spacing=0, weight=QFont.Weight.Medium,
        italic=True, fill=QColor(36, 30, 20, 209), halo=QColor(255, 251, 240, 140),
    ),
    "class": NameStyle(
        largest=18, area=0.18, room=0.9, upper=False, spacing=0.02, weight=QFont.Weight.DemiBold,
        italic=False, fill=QColor(30, 24, 16, 219), halo=QColor(255, 251, 240, 148),
    ),
    "region": NameStyle(
        largest=18, area=0.16, room=0.55, upper=True, spacing=0.24, weight=QFont.Weight.Medium,
        italic=False, fill=QColor(52, 40, 24, 189), halo=QColor(250, 245, 230, 107),
    ),
    "sea": NameStyle(
        largest=16, area=0.14, room=0.6, upper=False, spacing=0.06, weight=QFont.Weight.Normal,
        italic=True, fill=QColor(214, 232, 250, 230), halo=QColor(10, 26, 54, 128),
    ),
}  # fmt: skip
DARK_INK: Final[QColor] = QColor(26, 20, 12, 230)
LIGHT_HALO: Final[QColor] = QColor(255, 251, 240, 173)
# Zooms (screen pixels per atlas pixel) from which marks appear, as in the Tauri window.
CITY_ZOOM: Final[float] = 0.28
TOWN_ZOOM: Final[float] = 0.55
PLACE_NAME_ZOOM: Final[float] = 1.1
CAPITAL_ZOOM: Final[float] = 0.45
RICHES_ZOOM: Final[float] = 0.55
# How many names a view writes at most, the smallest name and the smallest location (in screen
# pixels across) that holds its value.
MOST_NAMES: Final[int] = 260
SMALLEST_NAME: Final[float] = 10.0
SMALLEST_COUNTRY: Final[float] = 9.0
SPOT_ROOM: Final[float] = 46.0
# A click moves the pointer at most this far (in screen pixels).
CLICK_SLACK: Final[int] = 3
MINUS: Final[str] = "\N{MINUS SIGN}"
CROSS: Final[str] = "\N{MULTIPLICATION SIGN}"


def to_image(picture: NDArray[np.uint8]) -> QImage:
    """A Qt image of an RGB picture (the image owns a copy of the pixels)."""
    height, width, _ = picture.shape
    contiguous = np.ascontiguousarray(picture)
    image = QImage(contiguous.data, width, height, 3 * width, QImage.Format.Format_RGB888)
    return image.copy()


def _rgb(colour: tuple[int, int, int]) -> QColor:
    return QColor(*colour)


class MapView(PreviewView):
    """A map: the picture of a lens, and what its owner writes over it at the view's zoom.

    Reports the pixel under the pointer, a click that did not drag the map and every change of
    the view (for a zoom read-out, a linked view and zoom-dependent lines).
    """

    moved: Signal = Signal(int, int)
    left: Signal = Signal()
    clicked: Signal = Signal(int, int)
    changed: Signal = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setBackgroundBrush(_rgb(mapstyle.COLOURS["ocean"]))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        # The map moves by dragging, as the Tauri window's does.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.overlay: Callable[[QPainter, MapView], None] | None = None
        self._press: QPointF | None = None

    def zoom(self) -> float:
        """Screen pixels per atlas pixel."""
        return self.transform().m11()

    def to_screen(self, x: float, y: float) -> QPointF:
        """The viewport point of atlas point (x, y)."""
        return QPointF(self.mapFromScene(QPointF(x, y)))

    def zoom_by(self, factor: float) -> None:
        """Zoom around the middle of the view, within its limits."""
        scale = self.zoom() * factor
        if scale < self._fit_scale() * 0.999:
            self.fit()
        elif scale <= ZOOM_LIMIT:
            anchor = self.transformationAnchor()
            self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
            self.scale(factor, factor)
            self.setTransformationAnchor(anchor)
            self.keep_fit(fitted=False)
        self.changed.emit()

    def show_box(self, box: tuple[float, float, float, float]) -> None:
        """Bring the atlas box (left, top, right, bottom) into view with a margin."""
        left, top, right, bottom = box
        margin = max(24.0, 0.15 * max(right - left, bottom - top))
        target = QRectF(
            left - margin, top - margin, right - left + 2 * margin, bottom - top + 2 * margin
        )
        self.fitInView(target, Qt.AspectRatioMode.KeepAspectRatio)
        if self.zoom() > ZOOM_LIMIT / 2:
            self.scale(ZOOM_LIMIT / 2 / self.zoom(), ZOOM_LIMIT / 2 / self.zoom())
            self.centerOn(target.center())
        self.keep_fit(fitted=False)
        self.changed.emit()

    def follow(self, other: MapView) -> None:
        """Look at what ``other`` looks at, at its zoom."""
        self.setTransform(other.transform())
        self.centerOn(other.mapToScene(other.viewport().rect().center()))
        self.keep_fit(fitted=other.is_fitted())

    @override
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        position = event.position().toPoint()
        pixel = self.pixel_at(position.x(), position.y())
        if pixel is None:
            self.left.emit()
        else:
            self.moved.emit(pixel[0], pixel[1])

    @override
    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._press = event.position()
        super().mousePressEvent(event)

    @override
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        press, self._press = self._press, None
        if press is None or event.button() != Qt.MouseButton.LeftButton:
            return
        moved = event.position() - press
        if abs(moved.x()) + abs(moved.y()) <= CLICK_SLACK:
            position = event.position().toPoint()
            pixel = self.pixel_at(position.x(), position.y())
            if pixel is not None:
                self.clicked.emit(pixel[0], pixel[1])

    @override
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if self._item.pixmap().isNull():
            return
        factor = min(2.4, ZOOM_LIMIT / max(self.zoom(), 1e-6))
        point = self.mapToScene(event.position().toPoint())
        self.scale(factor, factor)
        self.centerOn(point)
        self.keep_fit(fitted=False)
        self.changed.emit()
        event.accept()

    @override
    def leaveEvent(self, event: QEvent) -> None:
        super().leaveEvent(event)
        self.left.emit()

    @override
    def wheelEvent(self, event: QWheelEvent) -> None:
        super().wheelEvent(event)
        self.changed.emit()

    @override
    def scrollContentsBy(self, dx: int, dy: int) -> None:
        super().scrollContentsBy(dx, dy)
        self.changed.emit()

    @override
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.changed.emit()

    @override
    def drawForeground(self, painter: QPainter, rect: QRectF | QRect) -> None:
        super().drawForeground(painter, rect)
        if self.overlay is None or self._item.pixmap().isNull():
            return
        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.overlay(painter, self)
        painter.restore()


# -- what is written over the map ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Writing:
    """What a map writes over a lens: its names, its marks, and for each location its centre and
    its pixels (a location large enough on screen holds its value)."""

    names: tuple[mapstyle.Label, ...]
    places: tuple[mapstyle.Place, ...]
    centres: NDArray[np.float64]
    pixels: NDArray[np.float64]
    spots: tuple[str, ...]


def write(
    atlas: Atlas, lens: mapstyle.StyledLens, words: atlas_module.Words, *, tribes: bool
) -> Writing:
    """The writing of ``lens`` on ``atlas``."""
    counts = np.bincount(atlas.labels.ravel(), minlength=atlas.cells + 1)[1:].astype(np.float64)
    spots = tuple(mapstyle.spot(atlas, lens.layer, cell, words) for cell in range(atlas.cells))
    return Writing(
        names=tuple(mapstyle.names(atlas, lens, words, tribes=tribes)),
        places=tuple(mapstyle.places(atlas, lens.layer, words, tribes=tribes)),
        centres=mapstyle.centres(atlas),
        pixels=counts,
        spots=spots,
    )


def _font(
    base: QFont, size: float, weight: QFont.Weight, *, italic: bool = False, spacing: float = 0
) -> QFont:
    font = QFont(base)
    font.setPixelSize(max(1, round(size)))
    font.setWeight(weight)
    font.setItalic(italic)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return font


@dataclass(frozen=True, slots=True)
class Ink:
    """The fill and halo of written words, and the halo's width."""

    fill: QColor
    halo: QColor
    width: float


def _halo_text(painter: QPainter, font: QFont, at: QPointF, words: str, ink: Ink) -> None:
    """``words`` with its left end at ``at``'s x and its middle at its y, over a halo."""
    metrics = QFontMetricsF(font)
    path = QPainterPath()
    path.addText(QPointF(at.x(), at.y() + (metrics.ascent() - metrics.descent()) / 2), font, words)
    pen = QPen(ink.halo, ink.width)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.strokePath(path, pen)
    painter.fillPath(path, ink.fill)


Box = tuple[float, float, float, float]


class Scribe:
    """Writes names, marks and values over a map seen at ``zoom`` (screen pixels per atlas
    pixel): ``to_screen`` places an atlas point, ``size`` is the area written on. Places come
    first and names make way for them, as in the Tauri window."""

    def __init__(
        self,
        painter: QPainter,
        *,
        zoom: float,
        to_screen: Callable[[float, float], QPointF],
        size: tuple[float, float],
        base: QFont,
    ) -> None:
        self.painter: QPainter = painter
        self.zoom: float = zoom
        self.to_screen: Callable[[float, float], QPointF] = to_screen
        self.size: tuple[float, float] = size
        self.base: QFont = base
        self.placed: list[Box] = []
        self.marks: list[Callable[[], None]] = []

    def free(self, box: Box) -> bool:
        """Whether ``box`` overlaps nothing written yet."""
        return not any(
            box[0] < p[2] and box[2] > p[0] and box[1] < p[3] and box[3] > p[1] for p in self.placed
        )

    def visible(self, point: QPointF, margin: float) -> bool:
        """Whether ``point`` is within the area, give or take ``margin``."""
        width, height = self.size
        return -margin < point.x() < width + margin and -margin < point.y() < height + margin

    def write(self, writing: Writing, layer: str) -> None:
        """Everything ``layer`` writes."""
        for place in writing.places:
            self._place(place)
        self._names(writing.names)
        for mark in self.marks:
            mark()
        if mapstyle.profile(layer).spots is not None:
            self._spots(writing, layer)

    def _place(self, place: mapstyle.Place) -> None:
        point = self.to_screen(place.x, place.y)
        sx, sy = point.x(), point.y()
        if place.kind in {"city", "town"}:
            city = place.kind == "city"
            if self.zoom < (CITY_ZOOM if city else TOWN_ZOOM) or not self.visible(point, 20):
                return
            r = 3.6 if city else 2.4
            self.placed.append((sx - r - 1, sy - r - 1, sx + r + 1, sy + r + 1))
            self.marks.append(lambda: _dot(self.painter, point, r, city=city))
            if self.zoom >= PLACE_NAME_ZOOM:
                weight = QFont.Weight.DemiBold if city else QFont.Weight.Medium
                font = _font(self.base, 11, weight)
                advance = QFontMetricsF(font).horizontalAdvance(place.name)
                box = (sx + r + 3, sy - 7, sx + r + 5 + advance, sy + 7)
                if self.free(box):
                    self.placed.append(box)
                    ink = Ink(QColor(30, 24, 16, 235), QColor(255, 251, 240, 179), 3)
                    at = QPointF(box[0], sy)
                    self.marks.append(lambda: _halo_text(self.painter, font, at, place.name, ink))
        elif place.kind == "capital":
            if self.zoom <= CAPITAL_ZOOM or not self.visible(point, 10):
                return
            r = min(5.0, 2.5 + self.zoom * 0.6)
            self.placed.append((sx - r, sy - r, sx + r, sy + r))
            self.marks.append(lambda: _diamond(self.painter, point, r, QColor(251, 244, 226), 1.0))
        else:
            common = place.colour in {mapstyle.PRECIOUS["goods_gold"], mapstyle.PRECIOUS["silver"]}
            if (self.zoom < RICHES_ZOOM and not common) or not self.visible(point, 10):
                return
            r = max(2.6, min(6.0, 2 + self.zoom * 1.6))
            box = (sx - r - 1, sy - r - 1, sx + r + 1, sy + r + 1)
            if self.free(box):
                self.placed.append(box)
                fill = _rgb(place.colour)
                self.marks.append(lambda: _diamond(self.painter, point, r, fill, 0.8))

    def _names(self, labels: Iterable[mapstyle.Label]) -> None:
        written = 0
        for label in labels:
            style = NAME_STYLES[label.kind]
            size = min(
                style.largest,
                math.sqrt(label.weight) * self.zoom * style.area,
                label.room * self.zoom * style.room,
            )
            smallest = SMALLEST_COUNTRY if label.kind in {"country", "tribe"} else SMALLEST_NAME
            pole = self.to_screen(label.x, label.y)
            if size < smallest or not self.visible(pole, 200):
                continue
            words = label.text.upper() if style.upper else label.text
            font = _font(
                self.base, size, style.weight, italic=style.italic, spacing=size * style.spacing
            )
            advance = QFontMetricsF(font).horizontalAdvance(words)
            # At its point, or just under or over it when a capital or a city stands there.
            for sy in (pole.y(), pole.y() + size * 0.95, pole.y() - size * 0.95):
                box = (
                    pole.x() - advance / 2 - 4,
                    sy - size / 2 - 2,
                    pole.x() + advance / 2 + 4,
                    sy + size / 2 + 2,
                )
                if self.free(box):
                    self.placed.append(box)
                    ink = Ink(style.fill, style.halo, max(2.5, size * 0.22))
                    at = QPointF(pole.x() - advance / 2, sy)
                    _halo_text(self.painter, font, at, words, ink)
                    written += 1
                    break
            if written > MOST_NAMES:
                return

    def _spots(self, writing: Writing, layer: str) -> None:
        font = _font(self.base, 10.5, QFont.Weight.Medium)
        metrics = QFontMetricsF(font)
        ink = Ink(DARK_INK, LIGHT_HALO, 3)
        marked = {place.cell for place in writing.places if place.kind == "riches"}
        for cell, value in enumerate(writing.spots):
            if not value or math.sqrt(writing.pixels[cell]) * self.zoom < SPOT_ROOM:
                continue
            point = self.to_screen(float(writing.centres[cell, 0]), float(writing.centres[cell, 1]))
            if not self.visible(point, 40):
                continue
            advance = metrics.horizontalAdvance(value)
            top = 12 if layer == "resources" and cell in marked else 0
            y = point.y() + top
            box = (point.x() - advance / 2 - 2, y - 7, point.x() + advance / 2 + 2, y + 7)
            if self.free(box):
                self.placed.append(box)
                _halo_text(self.painter, font, QPointF(point.x() - advance / 2, y), value, ink)


def _dot(painter: QPainter, at: QPointF, r: float, *, city: bool) -> None:
    painter.setPen(
        QPen(QColor(42, 34, 24) if city else QColor(251, 246, 234, 217), 1.6 if city else 1.2)
    )
    painter.setBrush(QColor(251, 246, 234) if city else QColor(42, 34, 24))
    painter.drawEllipse(at, r, r)


def _diamond(painter: QPainter, at: QPointF, r: float, fill: QColor, wide: float) -> None:
    x, y = at.x(), at.y()
    painter.setPen(QPen(QColor(20, 16, 10, 225), 1.3))
    painter.setBrush(fill)
    corners = [
        QPointF(x, y - r),
        QPointF(x + r * wide, y),
        QPointF(x, y + r),
        QPointF(x - r * wide, y),
    ]
    painter.drawPolygon(QPolygonF(corners))


def marker(atlas: Atlas, cell: int, colour: QColor, tint: int) -> tuple[QImage, QPoint] | None:
    """An outline of location ``cell`` in ``colour`` over a tint of it (alpha ``tint``), and
    where it lies: drawn over the map for the location under the pointer or the one pinned."""
    rows, columns = np.nonzero(atlas.labels == cell + 1)
    if not rows.size:
        return None
    top, left = int(rows.min()), int(columns.min())
    inside = atlas.labels[top : int(rows.max()) + 1, left : int(columns.max()) + 1] == cell + 1
    padded = np.pad(inside, 1)
    edge = inside & ~(padded[:-2, 1:-1] & padded[2:, 1:-1] & padded[1:-1, :-2] & padded[1:-1, 2:])
    rgba = np.zeros((*inside.shape, 4), dtype=np.uint8)
    rgba[inside] = (colour.red(), colour.green(), colour.blue(), tint)
    rgba[edge] = (colour.red(), colour.green(), colour.blue(), 255)
    height, width = inside.shape
    image = QImage(
        np.ascontiguousarray(rgba).data, width, height, 4 * width, QImage.Format.Format_RGBA8888
    )
    return image.copy(), QPoint(left, top)


def find(atlas: Atlas, query: str, words: atlas_module.Words) -> list[atlas_module.Match]:
    """Countries, cultures, religions, resources, areas and places whose name holds ``query``."""
    found = atlas_module.find(atlas, query, limit=RESULTS, words=words)
    needle = query.strip().casefold()
    if not needle:
        return found
    areas: dict[str, list[int]] = {}
    for cell, area in enumerate(atlas.areas):
        title = mapstyle.written(area, words)
        if title and needle in title.casefold() and int(atlas.kinds[cell]) == mapstyle.LAND:
            areas.setdefault(title, []).append(cell)
    places = [match for match in found if match.kind == "place"]
    others = [match for match in found if match.kind != "place"]
    areas_found = [
        atlas_module.Match("area", label, tuple(cells)) for label, cells in areas.items()
    ]
    return [*others, *areas_found, *places][:RESULTS]


# -- drawing away from the window's thread --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Order:
    """What the panel wants drawn, with what it already has of it."""

    key: tuple[object, ...]
    base_key: tuple[object, ...]
    atlas: Atlas
    words: atlas_module.Words
    layer: str
    tribes: bool
    overlays: mapstyle.Overlays
    isolated: tuple[int, ...] | None
    lens: mapstyle.StyledLens | None
    base: NDArray[np.uint8] | None
    writing: Writing | None


@dataclass(frozen=True, slots=True)
class Drawn:
    """An order carried out: the lens, its picture, what is shown of it, and its writing."""

    order: Order
    lens: mapstyle.StyledLens
    base: NDArray[np.uint8]
    shown: NDArray[np.uint8]
    image: QImage
    writing: Writing


def carry_out(order: Order) -> Drawn:
    """Style, draw and write a lens: the slow part, done on the panel's worker thread."""
    atlas = order.atlas
    lens = order.lens or mapstyle.style(
        atlas, order.layer, order.words, tribes=order.tribes, tribes_label=text("map.tribes")
    )
    base = order.base
    if base is None:
        base = mapstyle.picture(atlas, lens, tribes=order.tribes, overlays=order.overlays)
    shown = base if order.isolated is None else mapstyle.isolate(atlas, base, order.isolated)
    writing = order.writing or write(atlas, lens, order.words, tribes=order.tribes)
    return Drawn(order, lens, base, shown, to_image(shown), writing)


@dataclass(frozen=True, slots=True)
class Failed:
    """An order that could not be carried out, and why."""

    order: Order
    reason: str


class _Delivery(QObject):
    """Brings a drawing finished on the worker thread back to the window's thread."""

    done: Signal = Signal(object)

    def carry_out(self, order: Order) -> None:
        """Carry ``order`` out (on the worker thread) and send back what came of it."""
        try:
            drawn: Drawn | Failed = carry_out(order)
        except Exception as error:  # noqa: BLE001 - shown in the window and logged, not lost in a thread
            logs.get().exception("drawing the %s lens failed", order.layer)
            drawn = Failed(order, str(error))
        self.done.emit(drawn)


# -- the panel ----------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Isolated:
    """What a legend entry, a search result or a link of a location's card shows alone."""

    label: str
    cells: tuple[int, ...]
    colour: tuple[int, int, int] | None = None


class MapsPanel(QWidget):
    """The lenses, the map with its names and marks, the legend, the search and the facts."""

    reveal_requested: Signal = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._atlas: Atlas | None = None
        self._words: atlas_module.Words = atlas_module.ENGLISH
        self._layer: str = atlas_module.LAYERS[0]
        self._identity: tuple[int, int] = (0, 0)
        self._tribes: bool = False
        self._political: bool = True
        self._names_shown: bool = True
        self._locations: bool = False
        self._isolated: Isolated | None = None
        self._preview: tuple[int, ...] | None = None
        self._pinned: int = -1
        self._hover: int = -1
        self._matches: list[atlas_module.Match] = []
        self._styled: dict[tuple[str, bool], mapstyle.StyledLens] = {}
        self._writing: dict[tuple[str, bool], Writing] = {}
        self._pictures: dict[tuple[object, ...], NDArray[np.uint8]] = {}
        self._shown: NDArray[np.uint8] | None = None
        self._drawn: tuple[object, ...] | None = None
        self._marks: list[QGraphicsPixmapItem] = []
        self._preview_timer: QTimer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(PREVIEW_DELAY)
        self._pending_preview: tuple[int, ...] | None = None
        _ = self._preview_timer.timeout.connect(self._apply_preview)
        self._zoom_timer: QTimer = QTimer(self)
        self._zoom_timer.setSingleShot(True)
        self._zoom_timer.setInterval(150)
        _ = self._zoom_timer.timeout.connect(self._draw)
        # Lenses are drawn on a thread of their own, one at a time, so the window stays awake.
        self._worker: ThreadPoolExecutor = ThreadPoolExecutor(1, thread_name_prefix="rnw-maps")
        self._delivery: _Delivery = _Delivery()
        _ = self._delivery.done.connect(self._delivered)
        self._wanted: tuple[object, ...] | None = None
        self._drawing: bool = False
        self._pending: Order | None = None
        worker = self._worker
        _ = self.destroyed.connect(lambda: worker.shutdown(wait=False, cancel_futures=True))
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.pages: QStackedWidget = QStackedWidget()
        outer.addWidget(self.pages)
        _ = self.pages.addWidget(self._covered_page())
        self.maps_page: QWidget = self._maps_page()
        _ = self.pages.addWidget(self.maps_page)
        self._shortcuts()

    @override
    def minimumSizeHint(self) -> QSize:
        """Yields width to the splitter so the side does not widen the window (ADR 0007)."""
        return QSize(0, super().minimumSizeHint().height())

    # -- the two pages -------------------------------------------------------------------------

    def _covered_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch(1)
        self.covered_notice: QLabel = QLabel()
        self.covered_notice.setWordWrap(True)
        self.covered_notice.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reveal_button: QPushButton = QPushButton(text("reveal_world"))
        self.reveal_button.setToolTip(text("reveal_world_tip"))
        layout.addWidget(self.covered_notice)
        layout.addWidget(self.reveal_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        _ = self.reveal_button.clicked.connect(self.reveal_requested)
        return page

    def _maps_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        main = QVBoxLayout()
        main.addLayout(self._toolbar())
        self.map_view: MapView = MapView()
        self.map_view.overlay = self._paint_over
        main.addWidget(self.map_view, 1)
        self.facts: QLabel = QLabel(text("facts_hint"))
        self.facts.setWordWrap(True)
        self.facts.setMinimumHeight(40)
        self.facts.setStyleSheet(MUTED)
        self.facts.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        main.addWidget(self.facts)
        self.summary: QLabel = QLabel()
        self.summary.setWordWrap(True)
        main.addWidget(self.summary)
        layout.addLayout(main, 1)
        side = QWidget()
        side.setFixedWidth(SIDE_WIDTH)
        side.setLayout(self._side())
        layout.addWidget(side)
        self._chip()
        self._card()
        self.loading: QLabel = QLabel(text("map.loading"), self.map_view.viewport())
        self.loading.setAutoFillBackground(True)
        self.loading.setMargin(8)
        self.loading.setVisible(False)
        _ = self.map_view.moved.connect(self.show_facts_at)
        _ = self.map_view.left.connect(self.clear_facts)
        _ = self.map_view.clicked.connect(self._clicked)
        _ = self.map_view.changed.connect(self._view_changed)
        return page

    def _toolbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        self.political_button: QToolButton = self._toggle(text("map.political"), "B", checked=True)
        self.names_button: QToolButton = self._toggle(text("map.labels"), "L", checked=True)
        self.locations_button: QToolButton = self._toggle(text("map.locations"), "", checked=False)
        for button in (self.political_button, self.names_button, self.locations_button):
            bar.addWidget(button)
        _ = self.political_button.toggled.connect(self._overlays_changed)
        _ = self.names_button.toggled.connect(self._overlays_changed)
        _ = self.locations_button.toggled.connect(self._overlays_changed)
        bar.addStretch(1)
        copy_view = QToolButton()
        copy_view.setText(text("map.copy_view"))
        _ = copy_view.clicked.connect(self.copy_view)
        bar.addWidget(copy_view)
        out = QToolButton()
        out.setText(MINUS)
        out.setToolTip(f"{text('map.zoom_out')} ({MINUS})")
        _ = out.clicked.connect(lambda: self.map_view.zoom_by(1 / 1.6))
        self.zoom_label: QLabel = QLabel("100%")
        self.zoom_label.setMinimumWidth(44)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        into = QToolButton()
        into.setText("+")
        into.setToolTip(f"{text('map.zoom_in')} (+)")
        _ = into.clicked.connect(lambda: self.map_view.zoom_by(1.6))
        fit = QToolButton()
        fit.setText(text("map.fit"))
        fit.setToolTip(f"{text('map.fit')} (F)")
        _ = fit.clicked.connect(self._fit)
        for widget in (out, self.zoom_label, into, fit):
            bar.addWidget(widget)
        return bar

    @staticmethod
    def _toggle(label: str, key: str, *, checked: bool) -> QToolButton:
        button = QToolButton()
        button.setText(label)
        button.setCheckable(True)
        button.setChecked(checked)
        if key:
            button.setToolTip(f"{label} ({key})")
        return button

    def _lenses(self) -> QGridLayout:
        """The ten lenses in two columns, with their keys in their tooltips."""
        lenses = QGridLayout()
        lenses.setSpacing(2)
        self.layer_buttons: QButtonGroup = QButtonGroup(self)
        for number, layer in enumerate(atlas_module.LAYERS):
            button = QToolButton()
            button.setText(text(f"layer.{layer}"))
            button.setCheckable(True)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            key = 0 if number == 9 else number + 1  # noqa: PLR2004 - the tenth lens is key 0
            button.setToolTip(f"{text(f'layer.{layer}.tip')} ({key})")
            self.layer_buttons.addButton(button, number)
            lenses.addWidget(button, number // 2, number % 2)
        self.layer_buttons.button(0).setChecked(True)
        self._mark_lens()
        return lenses

    def _side(self) -> QVBoxLayout:
        side = QVBoxLayout()
        side.setContentsMargins(0, 0, 0, 0)
        side.addLayout(self._lenses())
        self.search: QLineEdit = QLineEdit()
        self.search.setPlaceholderText(text("search_hint"))
        self.search.setToolTip(text("search_hint"))
        self.search.setClearButtonEnabled(True)
        side.addWidget(self.search)
        self.results: QListWidget = QListWidget()
        self.results.setMouseTracking(True)
        self.results.setVisible(False)
        side.addWidget(self.results, 1)
        self.legend_title: QLabel = QLabel(text("legend"))
        self.legend_title.setStyleSheet("font-weight: 600")
        side.addWidget(self.legend_title)
        self.tribes_box: QCheckBox = QCheckBox(text("map.show_tribes"))
        self.tribes_box.setToolTip(text("map.show_tribes_tip"))
        side.addWidget(self.tribes_box)
        self.ramp: QLabel = QLabel()
        self.ramp.setFixedHeight(24)
        side.addWidget(self.ramp)
        self.legend_list: QListWidget = QListWidget()
        self.legend_list.setIconSize(QSize(SWATCH, SWATCH))
        self.legend_list.setMouseTracking(True)
        side.addWidget(self.legend_list, 2)
        hint = QLabel(text("map.legend_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(MUTED)
        side.addWidget(hint)
        _ = self.layer_buttons.idClicked.connect(self._pick_layer)
        _ = self.search.textChanged.connect(self._searched)
        _ = self.results.currentRowChanged.connect(self._chosen)
        _ = self.results.itemEntered.connect(self._result_entered)
        _ = self.legend_list.itemEntered.connect(self._entry_entered)
        _ = self.legend_list.itemClicked.connect(self._entry_clicked)
        _ = self.legend_list.itemDoubleClicked.connect(self._entry_double_clicked)
        _ = self.tribes_box.toggled.connect(self._tribes_toggled)
        for listing in (self.results, self.legend_list):
            listing.viewport().installEventFilter(self)
        return side

    def _chip(self) -> None:
        """What is shown alone, over the top left of the map, with a button to let it go."""
        self.chip: QFrame = QFrame(self.map_view.viewport())
        self.chip.setFrameShape(QFrame.Shape.StyledPanel)
        self.chip.setAutoFillBackground(True)
        row = QHBoxLayout(self.chip)
        row.setContentsMargins(8, 2, 2, 2)
        self.chip_label: QLabel = QLabel()
        clear = QToolButton()
        clear.setText(CROSS)
        clear.setToolTip(f"{text('map.clear')} (Esc)")
        _ = clear.clicked.connect(lambda: self._isolate(None))
        row.addWidget(self.chip_label)
        row.addWidget(clear)
        self.chip.move(8, 8)
        self.chip.setVisible(False)

    def _card(self) -> None:
        """The card of the location clicked, over the top right of the map."""
        self.card: QFrame = QFrame(self.map_view.viewport())
        self.card.setFrameShape(QFrame.Shape.StyledPanel)
        self.card.setAutoFillBackground(True)
        self.card.setFixedWidth(280)
        self.card_layout: QVBoxLayout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(10, 8, 10, 10)
        self.card.setVisible(False)

    def _shortcuts(self) -> None:
        context = Qt.ShortcutContext.WidgetWithChildrenShortcut
        bindings: list[tuple[str, Callable[[], None]]] = [
            ("+", lambda: self.map_view.zoom_by(1.6)),
            ("=", lambda: self.map_view.zoom_by(1.6)),
            ("-", lambda: self.map_view.zoom_by(1 / 1.6)),
            ("F", self._fit),
            ("L", self.names_button.toggle),
            ("B", self.political_button.toggle),
            ("Esc", self._escape),
        ]
        for number in range(len(atlas_module.LAYERS)):
            key = "0" if number == 9 else str(number + 1)  # noqa: PLR2004 - the tenth lens is key 0
            bindings.append(
                (key, lambda number=number: self.select_layer(atlas_module.LAYERS[number]))
            )
        for key, action in bindings:
            shortcut = QShortcut(QKeySequence(key), self.maps_page)
            shortcut.setContext(context)
            _ = shortcut.activated.connect(action)

    # -- what to show --------------------------------------------------------------------------

    @property
    def layer(self) -> str:
        """The lens shown now."""
        return self._layer

    def show_world(
        self,
        atlas: Atlas | None,
        *,
        revealed: bool,
        identity: int = 0,
        words: atlas_module.Words = atlas_module.ENGLISH,
    ) -> None:
        """Show the atlas of a world, or the reason there is nothing to show.

        ``identity`` tells one world from another so that the picture is drawn afresh for a new
        one and kept (with its zoom) while only the lens or what is isolated changes.
        """
        if atlas is None:
            self._wanted = None
            self._pending = None
            self.loading.hide()
            self.covered_notice.setText(text("no_atlas"))
            self.reveal_button.setVisible(False)
            self.pages.setCurrentIndex(0)
            return
        if not revealed:
            self._wanted = None
            self._pending = None
            self.loading.hide()
            self.covered_notice.setText(text("covered_maps"))
            self.reveal_button.setVisible(True)
            self.pages.setCurrentIndex(0)
            return
        self._identity = (identity, id(words))
        words_changed = words is not self._words
        self._words = words
        if atlas is not self._atlas or words_changed:
            self._wanted = None
            self._pending = None
            self._atlas = atlas
            self._styled.clear()
            self._writing.clear()
            self._pictures.clear()
            self._isolated = None
            self._preview = None
            self._pinned = -1
            self._hover = -1
            self._matches = []
            self.results.clear()
            self.search.clear()
            self._drawn = None
            self.card.setVisible(False)
            self.chip.setVisible(False)
        self.pages.setCurrentIndex(1)
        self._draw()

    def _seen(self) -> bool:
        """Whether the maps are on screen (or would be, were the window shown): a world's maps
        are drawn only when looked at, not whenever the world is chosen."""
        window = self.window()
        return self.pages.currentIndex() == 1 and self.isVisibleTo(window) and window is not self

    @override
    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._draw()

    def shown_now(self, _index: int = 0) -> None:
        """A tab was chosen: when it is the maps', draw what waits to be drawn."""
        self._draw()

    def idle(self) -> bool:
        """Whether nothing is being drawn: what was asked for is on screen."""
        return self._wanted is None

    def _lens(self) -> mapstyle.StyledLens | None:
        """The lens shown, once it has been styled."""
        return self._styled.get((self._layer, self._tribes))

    def _current_writing(self) -> Writing | None:
        """What the lens shown writes, once it has been worked out."""
        return self._writing.get((self._layer, self._tribes))

    def _overlays(self) -> mapstyle.Overlays:
        zoom = self.map_view.zoom()
        borders = self._political and (self._layer == "countries" or zoom >= BORDER_ZOOM)
        return mapstyle.Overlays(
            political=borders, locations=self._locations and zoom >= LOCATION_ZOOM
        )

    def _draw(self) -> None:
        """Show the lens as it is wanted, drawing it on the worker thread when it is not at
        hand; the old picture stays, with a notice, until the new one comes."""
        atlas = self._atlas
        if atlas is None or not self._seen():
            return
        overlays = self._overlays()
        isolated = (
            self._preview
            if self._preview is not None
            else (self._isolated.cells if self._isolated else None)
        )
        key = (self._identity, self._layer, self._tribes, overlays, isolated)
        if key == self._drawn:
            self._wanted = None
            self._pending = None
            self.loading.hide()
            return
        if key == self._wanted:
            return
        base_key = key[:4]
        order = Order(
            key=key,
            base_key=base_key,
            atlas=atlas,
            words=self._words,
            layer=self._layer,
            tribes=self._tribes,
            overlays=overlays,
            isolated=isolated,
            lens=self._lens(),
            base=self._pictures.get(base_key),
            writing=self._current_writing(),
        )
        self._wanted = key
        if order.base is None or order.lens is None or order.writing is None:
            self.loading.adjustSize()
            self.loading.move(
                (self.map_view.viewport().width() - self.loading.width()) // 2,
                (self.map_view.viewport().height() - self.loading.height()) // 2,
            )
            self.loading.setVisible(True)
            self.loading.raise_()
        # While a picture is being drawn, keep only the latest request. Rapid world/lens
        # changes must not make the player wait for a queue of pictures no longer wanted.
        if self._drawing:
            self._pending = order
        else:
            self._submit(order)

    def _submit(self, order: Order) -> None:
        self._drawing = True
        _ = self._worker.submit(self._delivery.carry_out, order)

    def _delivered(self, drawn: Drawn | Failed) -> None:
        """A drawing came back: keep what it made and show it if it is still wanted."""
        order = drawn.order
        self._drawing = False
        pending, self._pending = self._pending, None
        if pending is not None:
            self._submit(pending)
        if order.atlas is not self._atlas:
            return
        if isinstance(drawn, Failed):
            if order.key == self._wanted:
                self._wanted = None
                self.loading.setVisible(False)
                self.facts.setText(drawn.reason)
            return
        lens_key = (order.layer, order.tribes)
        self._styled[lens_key] = drawn.lens
        self._writing[lens_key] = drawn.writing
        if order.base_key not in self._pictures:
            while len(self._pictures) >= KEPT_PICTURES:
                del self._pictures[next(iter(self._pictures))]
            self._pictures[order.base_key] = drawn.base
        if order.key != self._wanted:
            return
        self._wanted = None
        self.loading.setVisible(False)
        self._shown = drawn.shown
        self.map_view.show_image(drawn.image, f"{self._identity}")
        if order.key[:3] != (self._drawn or ())[:3]:
            self._legend(drawn.lens)
        self._drawn = order.key
        self.map_view.viewport().update()

    def _legend(self, lens: mapstyle.StyledLens) -> None:
        self.legend_list.clear()
        self.legend_title.setText(f"{text('legend')} · {text(f'layer.{self._layer}')}")
        for label, colour, count in lens.legend:
            if count <= 0:
                continue
            swatch = QPixmap(SWATCH, SWATCH)
            swatch.fill(_rgb(colour))
            item = QListWidgetItem(QIcon(swatch), f"{label}  ({grouped(count)})")
            item.setToolTip(label)
            item.setData(Qt.ItemDataRole.UserRole, lens.legend.index((label, colour, count)))
            self.legend_list.addItem(item)
        atlas = self._atlas
        tribes = sum(1 for country in atlas.countries if country.kind != "state") if atlas else 0
        self.tribes_box.setVisible(self._layer == "countries" and tribes > 0)
        self.tribes_box.setText(f"{text('map.show_tribes')} · {tribes}")
        if lens.ramp:
            self.ramp.setPixmap(self._ramp_picture(lens.ramp))
            self.ramp.setVisible(True)
        else:
            self.ramp.setVisible(False)

    def _ramp_picture(self, colours: Sequence[tuple[int, int, int]]) -> QPixmap:
        width = SIDE_WIDTH - 8
        picture = QPixmap(width, 24)
        picture.fill(Qt.GlobalColor.transparent)
        painter = QPainter(picture)
        gradient = QLinearGradient(0, 0, width, 0)
        for index, colour in enumerate(colours):
            gradient.setColorAt(index / max(1, len(colours) - 1), _rgb(colour))
        painter.fillRect(0, 0, width, 8, gradient)
        painter.setPen(self.palette().color(self.foregroundRole()))
        small = QFont(self.font())
        small.setPointSizeF(max(6.0, small.pointSizeF() * 0.85))
        painter.setFont(small)
        _ = painter.drawText(
            QRectF(0, 9, width, 15), Qt.AlignmentFlag.AlignLeft, text("legend.lowest")
        )
        _ = painter.drawText(
            QRectF(0, 9, width, 15), Qt.AlignmentFlag.AlignRight, text("legend.highest")
        )
        _ = painter.end()
        return picture

    def picture(self) -> NDArray[np.uint8] | None:
        """The picture shown, as pixels, or None when there is none."""
        if self._atlas is None or self.pages.currentIndex() != 1:
            return None
        return self._shown

    # -- writing over the map ------------------------------------------------------------------

    def _paint_over(self, painter: QPainter, view: MapView) -> None:
        writing = self._current_writing()
        if writing is None or not self._names_shown:
            return
        viewport = view.viewport()
        size = (viewport.width(), viewport.height())
        scribe = Scribe(
            painter, zoom=view.zoom(), to_screen=view.to_screen, size=size, base=self.font()
        )
        scribe.write(writing, self._layer)

    def _set_marks(self) -> None:
        atlas = self._atlas
        scene = self.map_view.scene()
        for item in self._marks:
            scene.removeItem(item)
        self._marks = []
        if atlas is None:
            return
        for cell, colour, tint in (
            (self._hover, QColor(255, 255, 255), 56),
            (self._pinned, QColor(255, 213, 74), 46),
        ):
            if cell < 0:
                continue
            found = marker(atlas, cell, colour, tint)
            if found is None:
                continue
            image, corner = found
            item = QGraphicsPixmapItem(QPixmap.fromImage(image))
            item.setPos(QPointF(corner))
            item.setZValue(1)
            scene.addItem(item)
            self._marks.append(item)

    # -- what the player does ------------------------------------------------------------------

    def _mark_lens(self) -> None:
        """The lens shown is in bold as well as pressed: some styles barely draw a press."""
        for button in self.layer_buttons.buttons():
            font = button.font()
            font.setBold(button.isChecked())
            button.setFont(font)

    def _pick_layer(self, number: int) -> None:
        self._layer = atlas_module.LAYERS[number]
        self._mark_lens()
        self._isolated = None
        self._preview = None
        self.chip.setVisible(False)
        self._draw()

    def select_layer(self, layer: str) -> None:
        """Show ``layer`` (as its button does)."""
        number = atlas_module.LAYERS.index(layer)
        self.layer_buttons.button(number).setChecked(True)
        self._pick_layer(number)

    def _tribes_toggled(self, shown: bool) -> None:  # noqa: FBT001 - Qt signal
        self._tribes = shown
        self._isolated = None
        self.chip.setVisible(False)
        self._draw()

    def _overlays_changed(self) -> None:
        self._political = self.political_button.isChecked()
        self._names_shown = self.names_button.isChecked()
        self._locations = self.locations_button.isChecked()
        self._draw()

    def _view_changed(self) -> None:
        self.zoom_label.setText(f"{round(self.map_view.zoom() * 100)}%")
        self.card.move(self.map_view.viewport().width() - self.card.width() - 8, 8)
        if self._drawn is not None and self._drawn[3] != self._overlays():
            self._zoom_timer.start()

    def _fit(self) -> None:
        self.map_view.fit()
        self.map_view.changed.emit()

    def show_facts_at(self, row: int, column: int) -> None:
        """The facts of the location under the pointer, and its outline."""
        atlas = self._atlas
        cell = -1 if atlas is None else atlas_module.cell_at(atlas, row, column)
        facts = None if atlas is None else atlas_module.describe(atlas, cell)
        self.facts.setText(
            describe_text(facts, self._words) if facts is not None else text("facts_hint")
        )
        if cell != self._hover:
            self._hover = cell
            self._set_marks()

    def clear_facts(self) -> None:
        """Nothing under the pointer."""
        self.facts.setText(text("facts_hint"))
        if self._hover >= 0:
            self._hover = -1
            self._set_marks()

    def _clicked(self, row: int, column: int) -> None:
        atlas = self._atlas
        if atlas is None:
            return
        cell = atlas_module.cell_at(atlas, row, column)
        self._pin(-1 if cell == self._pinned else cell)

    def _pin(self, cell: int) -> None:
        self._pinned = cell
        self._set_marks()
        self._fill_card()

    def _fill_card(self) -> None:
        atlas = self._atlas
        layout = self.card_layout
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()
        facts = None if atlas is None else atlas_module.describe(atlas, self._pinned)
        if atlas is None or facts is None:
            self.card.setVisible(False)
            return
        words = self._words
        head = QHBoxLayout()
        title = QLabel(f"<b>{_escape(mapstyle.written(facts.name, words) or facts.key)}</b>")
        title.setWordWrap(True)
        head.addWidget(title, 1)
        close = QToolButton()
        close.setText(CROSS)
        close.setToolTip(f"{text('close')} (Esc)")
        _ = close.clicked.connect(lambda: self._pin(-1))
        head.addWidget(close)
        holder = QWidget()
        holder.setLayout(head)
        layout.addWidget(holder)
        area = mapstyle.written(facts.area, words)
        layout.addWidget(
            QLabel(" · ".join(part for part in (text(f"kind.{facts.kind}"), area) if part))
        )
        if facts.kind == "land":
            layout.addWidget(self._card_rows(facts))
        self.card.adjustSize()
        self.card.move(self.map_view.viewport().width() - self.card.width() - 8, 8)
        self.card.setVisible(True)
        self.card.raise_()

    def _card_rows(self, facts: atlas_module.Facts) -> QWidget:
        """A land location's country, culture, religion, resource and area, each a link that
        shows it alone; its land, people and development."""
        words, cell = self._words, self._pinned
        rows: list[tuple[str, str, Callable[[], None] | None]] = []
        country = facts.country
        if country is not None:
            name = words.name(country.name) if country.name else country.tag
            rows.append(
                (
                    "fact.country",
                    f"{name} ({country.tag})",
                    lambda: self._isolate_where("owner", cell, name),
                )
            )
        else:
            rows.append(("fact.country", text("no_country"), None))
        if facts.culture:
            culture, religion = words.key(facts.culture), words.key(facts.religion)
            rows.append(
                ("fact.culture", culture, lambda: self._isolate_where("culture", cell, culture))
            )
            rows.append(
                ("fact.religion", religion, lambda: self._isolate_where("religion", cell, religion))
            )
        material = words.key(facts.material)
        riches = " \N{SIX POINTED BLACK STAR}" if facts.material in mapstyle.PRECIOUS else ""
        rows.append(
            (
                "fact.material",
                material + riches,
                lambda: self._isolate_where("material", cell, material, zoom=False),
            )
        )
        land = (facts.topography, facts.vegetation, facts.climate)
        rows.append(("fact.terrain", " · ".join(words.key(item) for item in land if item), None))
        if facts.population:
            rows.append(("fact.population", grouped(facts.population), None))
            rows.append(("fact.complexity", str(facts.complexity), None))
        if facts.area:
            area = mapstyle.written(facts.area, words)
            rows.append(("fact.area", area, lambda: self._isolate_area(cell, area)))
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        for row, (key, value, link) in enumerate(rows):
            grid.addWidget(QLabel(text(key)), row, 0)
            if link is None:
                shown = QLabel(value)
                shown.setWordWrap(True)
                grid.addWidget(shown, row, 1)
            else:
                button = QPushButton(value)
                button.setFlat(True)
                button.setStyleSheet("text-align: left; text-decoration: underline")
                _ = button.clicked.connect(link)
                grid.addWidget(button, row, 1)
        box = QWidget()
        box.setLayout(grid)
        return box

    def _isolate_where(self, field: str, cell: int, label: str, *, zoom: bool = True) -> None:
        atlas = self._atlas
        if atlas is None:
            return
        column = np.asarray(getattr(atlas, field))
        cells = tuple(int(c) for c in np.flatnonzero(column == column[cell]))
        colour = None
        if field == "owner" and int(atlas.owner[cell]) >= 0:
            colour = atlas.countries[int(atlas.owner[cell])].color
        self._isolate(Isolated(label, cells, colour), zoom=zoom)

    def _isolate_area(self, cell: int, label: str) -> None:
        atlas = self._atlas
        if atlas is None:
            return
        area = atlas.areas[cell]
        cells = tuple(
            c
            for c in range(atlas.cells)
            if atlas.areas[c] == area and int(atlas.kinds[c]) == mapstyle.LAND
        )
        self._isolate(Isolated(label, cells), zoom=True)

    def _isolate(self, isolated: Isolated | None, *, zoom: bool = False) -> None:
        """Show only ``isolated`` (the same again lets it go), and bring it into view."""
        if (
            isolated is not None
            and self._isolated is not None
            and isolated.label == self._isolated.label
        ):
            isolated = None
        self._isolated = isolated
        self._preview = None
        if isolated is None:
            self.chip.setVisible(False)
        else:
            self.chip_label.setText(
                f"{text('map.showing', name=isolated.label)}  ({grouped(len(isolated.cells))})"
            )
            self.chip.adjustSize()
            self.chip.setVisible(True)
            self.chip.raise_()
            if zoom:
                self._zoom_to(isolated.cells)
        self._draw()

    def _zoom_to(self, cells: Iterable[int]) -> None:
        atlas = self._atlas
        if atlas is None:
            return
        wanted = np.zeros(atlas.cells + 1, dtype=bool)
        chosen = np.fromiter(cells, dtype=np.int64)
        if not chosen.size:
            return
        wanted[chosen + 1] = True
        rows, columns = np.nonzero(wanted[atlas.labels])
        if rows.size:
            self.map_view.show_box(
                (
                    float(columns.min()),
                    float(rows.min()),
                    float(columns.max() + 1),
                    float(rows.max() + 1),
                )
            )

    def _escape(self) -> None:
        if self._pinned >= 0:
            self._pin(-1)
        elif self._isolated is not None:
            self._isolate(None)

    # -- the legend and the search -------------------------------------------------------------

    def _entry_cells(self, item: QListWidgetItem) -> tuple[int, ...]:
        lens = self._lens()
        if lens is None:
            return ()
        entry = int(item.data(Qt.ItemDataRole.UserRole))
        return tuple(int(c) for c in np.flatnonzero(lens.classes == entry))

    def _entry_entered(self, item: QListWidgetItem) -> None:
        self._schedule_preview(self._entry_cells(item))

    def _entry_clicked(self, item: QListWidgetItem) -> None:
        lens = self._lens()
        if lens is None:
            return
        label, colour, _ = lens.legend[int(item.data(Qt.ItemDataRole.UserRole))]
        self._preview_timer.stop()
        self._isolate(Isolated(label, self._entry_cells(item), colour))

    def _entry_double_clicked(self, item: QListWidgetItem) -> None:
        self._zoom_to(self._entry_cells(item))

    def _result_entered(self, item: QListWidgetItem) -> None:
        row = self.results.row(item)
        if 0 <= row < len(self._matches):
            self._schedule_preview(self._matches[row].cells)

    def _schedule_preview(self, cells: tuple[int, ...] | None) -> None:
        self._pending_preview = cells
        self._preview_timer.start()

    def _apply_preview(self) -> None:
        self._preview = self._pending_preview
        self._draw()

    @override
    def eventFilter(self, watched: object, event: QEvent) -> bool:
        """The pointer leaving the legend or the results lets go of what it lit."""
        if event.type() == QEvent.Type.Leave:
            self._schedule_preview(None)
        return super().eventFilter(watched, event)  # pyright: ignore[reportArgumentType]

    def _searched(self, query: str) -> None:
        atlas = self._atlas
        self.results.clear()
        self._matches = [] if atlas is None else find(atlas, query, self._words)
        for match in self._matches:
            item = QListWidgetItem(
                f"{match.label}  ·  {text(f'found.{match.kind}')}  ({grouped(len(match.cells))})"
            )
            self.results.addItem(item)
        if query.strip() and not self._matches:
            self.results.addItem(text("map.no_results"))
        self.results.setVisible(bool(query.strip()))
        if not self._matches:
            self._isolate(None)

    def _chosen(self, row: int) -> None:
        if 0 <= row < len(self._matches):
            match = self._matches[row]
            self._preview_timer.stop()
            self._isolate(Isolated(match.label, match.cells), zoom=True)
            if match.kind == "place" and len(match.cells) == 1:
                self._pin(match.cells[0])

    def set_summary(self, line: str) -> None:
        """The one line under the map: how many countries, cultures and locations."""
        self.summary.setText(line)

    # -- pictures --------------------------------------------------------------------------------

    def drawn_image(self) -> QImage | None:
        """The whole lens as it is drawn, names included, one pixel per atlas pixel."""
        shown, writing = self._shown, self._current_writing()
        if shown is None or writing is None:
            return None
        image = to_image(shown).convertToFormat(QImage.Format.Format_ARGB32)
        if self._names_shown:
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            size = (image.width(), image.height())
            scribe = Scribe(painter, zoom=1.0, to_screen=QPointF, size=size, base=self.font())
            scribe.write(writing, self._layer)
            _ = painter.end()
        return image

    def copy_view(self) -> None:
        """Put the view of the map, as it is, on the clipboard."""
        QGuiApplication.clipboard().setPixmap(self.map_view.viewport().grab())
        self.facts.setText(text("map.copied"))


def _english(_found: Atlas) -> atlas_module.Words:
    return atlas_module.ENGLISH


def _escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class CompareDialog(QDialog):
    """Two worlds' maps side by side, on one lens, moving together unless told not to."""

    def __init__(
        self,
        parent: QWidget,
        entries: list[tuple[str, Atlas]],
        layer: str,
        words: Callable[[Atlas], atlas_module.Words] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(text("compare_title"))
        self._entries: list[tuple[str, Atlas]] = entries
        self._layer: str = layer
        self._words: Callable[[Atlas], atlas_module.Words] = words or _english
        self._writing: list[Writing | None] = [None, None]
        self._following: bool = False
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.lens_choice: QComboBox = QComboBox()
        for name in atlas_module.LAYERS:
            self.lens_choice.addItem(text(f"layer.{name}"), name)
        self.lens_choice.setCurrentIndex(atlas_module.LAYERS.index(layer))
        self.linked: QCheckBox = QCheckBox(text("compare.linked"))
        self.linked.setChecked(True)
        bar.addWidget(self.lens_choice)
        bar.addWidget(self.linked)
        bar.addStretch(1)
        layout.addLayout(bar)
        columns = QHBoxLayout()
        self.choices: list[QComboBox] = []
        self.views: list[MapView] = []
        for side in range(2):
            column = QVBoxLayout()
            choice = QComboBox()
            for name, _found in entries:
                choice.addItem(name)
            choice.setCurrentIndex(min(side, len(entries) - 1))
            view = MapView()
            view.overlay = lambda painter, shown, side=side: self._paint_over(painter, shown, side)
            column.addWidget(choice)
            column.addWidget(view, 1)
            columns.addLayout(column, 1)
            self.choices.append(choice)
            self.views.append(view)
            _ = choice.currentIndexChanged.connect(self.redraw)
            _ = view.changed.connect(lambda side=side: self._moved(side))
        layout.addLayout(columns, 1)
        _ = self.lens_choice.currentIndexChanged.connect(self._pick)
        self.resize(1200, 700)
        self.redraw()

    def _pick(self, index: int) -> None:
        self._layer = atlas_module.LAYERS[index]
        self.redraw()

    def redraw(self) -> None:
        """Draw both maps on the chosen lens."""
        for side, (choice, view) in enumerate(zip(self.choices, self.views, strict=True)):
            found = self._entries[choice.currentIndex()][1]
            words = self._words(found)
            lens = mapstyle.style(
                found, self._layer, words, tribes=False, tribes_label=text("map.tribes")
            )
            shown = mapstyle.picture(found, lens, tribes=False)
            self._writing[side] = write(found, lens, words, tribes=False)
            view.show_image(to_image(shown), f"{choice.currentIndex()}")
            view.viewport().update()

    def _paint_over(self, painter: QPainter, view: MapView, side: int) -> None:
        writing = self._writing[side]
        if writing is not None:
            viewport = view.viewport()
            size = (viewport.width(), viewport.height())
            scribe = Scribe(
                painter, zoom=view.zoom(), to_screen=view.to_screen, size=size, base=self.font()
            )
            scribe.write(writing, self._layer)

    def _moved(self, side: int) -> None:
        if self._following or not self.linked.isChecked():
            return
        self._following = True
        try:
            self.views[1 - side].follow(self.views[side])
        finally:
            self._following = False


def describe_text(
    facts: atlas_module.Facts, words: atlas_module.Words = atlas_module.ENGLISH
) -> str:
    """What the atlas says of a location, in a few lines, as ``words`` write it."""
    lines = [f"{mapstyle.written(facts.name, words) or facts.key}  ({text(f'kind.{facts.kind}')})"]
    if facts.kind == "land":
        country = facts.country
        owner = words.name(country.name) if country is not None else text("no_country")
        lines.append(f"{text('fact.country')}: {owner}")
        if facts.culture:
            culture = words.key(facts.culture)
            religion = words.key(facts.religion)
            lines.append(f"{text('fact.culture')}: {culture} · {text('fact.religion')}: {religion}")
        material = words.key(facts.material)
        land = " · ".join(
            words.key(item) for item in (facts.vegetation, facts.topography, facts.climate) if item
        )
        lines.append(f"{text('fact.material')}: {material} · {land}")
        if facts.population:
            population = f"{text('fact.population')}: {grouped(facts.population)}"
            lines.append(f"{population} · {text('fact.complexity')}: {facts.complexity}")
    return "\n".join(lines)
