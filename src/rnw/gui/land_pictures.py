"""What the classic window's land editor draws with besides the canvas: the generator's report
told in sentences, the small pictures of the tools, the layers and the ready lands, and the draft
of each continent kept in the data folder."""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, cast

import numpy as np
from PIL import Image
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPen, QPixmap, QPolygonF

from rnw import landmask
from rnw.gui import studio
from rnw.gui.land_canvas import AREA, HATCH, OUTSIDE
from rnw.gui.land_sheet import SEA, SHOWN
from rnw.gui.text import text
from rnw.landmask import LandMaskError

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

THUMB_EVERY: Final[int] = 4

# -- what the generator says about a picture ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Line:
    """One sentence of the generator's report: how bad it is, its string and its values."""

    level: str  # "ok", "warn" or "error"
    key: str
    values: dict[str, str]

    def says(self) -> str:
        return text(self.key, **self.values)


def _shown(number: float) -> str:
    return f"{number:g}"


def say_report(report: dict[str, object]) -> list[Line]:
    """The sentences a report is told in, the worst first; the picture can be made into a world
    when none of them is an error (the Tauri editor's ``sayReport``)."""
    land = cast("int", report["land"])
    kept = cast("int", report["kept"])
    refusal = cast("str", report["refusal"])
    share = f"{land / 10:.1f}"
    lines: list[Line] = []
    if refusal == "share":
        low, high = cast("int", report["low"]) / 10, cast("int", report["high"]) / 10
        lines.append(
            Line(
                "error",
                "editor.check.share",
                {"share": share, "low": _shown(low), "high": _shown(high)},
            )
        )
    if refusal == "outside":
        lines.append(Line("error", "editor.check.outside_all", {"kept": str(kept)}))
    if refusal == "lake_open":
        count = len(cast("list[object]", report["open_lakes"]))
        lines.append(Line("error", "editor.check.lake_open", {"count": str(count)}))
    if not refusal and kept < 100:  # noqa: PLR2004 - a percentage
        lines.append(Line("warn", "editor.check.dropped", {"dropped": str(100 - kept)}))
    specks = cast("int", report["specks"])
    if specks:
        lines.append(Line("warn", "editor.check.specks", {"count": str(specks)}))
    islands = cast("int", report["islands"])
    if islands:
        lines.append(Line("warn", "editor.check.islands", {"count": str(islands)}))
    if not refusal:
        lines.append(Line("ok", "editor.check.land", {"share": share}))
    return lines


# -- pictures ---------------------------------------------------------------------------------


def grey(url: str) -> NDArray[np.uint8]:
    """The greys of a picture the generator sent (the area's classes, or its coast margin)."""
    return np.asarray(Image.open(io.BytesIO(studio.png_of(url))).convert("L"), dtype=np.uint8)


def thumbnail(kinds: NDArray[np.uint8], inside: NDArray[np.bool_]) -> QPixmap:
    """A small picture of a drawing on the area's sea, every ``THUMB_EVERY``th pixel."""
    part = np.ascontiguousarray(kinds[::THUMB_EVERY, ::THUMB_EVERY])
    outside = ~inside[::THUMB_EVERY, ::THUMB_EVERY]
    base = np.where(outside[..., np.newaxis], np.array(OUTSIDE), np.array(AREA))
    shown = SHOWN[part].astype(np.float64)
    alpha = shown[..., 3:4] / 255
    rgb = np.ascontiguousarray(
        np.round(base * (1 - alpha) + shown[..., :3] * alpha).astype(np.uint8)
    )
    rows, columns = rgb.shape[:2]
    image = QImage(rgb.data, columns, rows, columns * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(image.copy())


def swatch(kind: int, size: int = 14) -> QIcon:
    pixmap = QPixmap(size, size)
    if kind == SEA:
        pixmap.fill(QColor(*AREA))
    else:
        red, green, blue, _alpha = (int(value) for value in SHOWN[kind])
        pixmap.fill(QColor(red, green, blue))
    return QIcon(pixmap)


def layer_icon(colour: tuple[int, int, int], *, hatched: bool = False) -> QIcon:
    pixmap = QPixmap(16, 16)
    pixmap.fill(QColor(*colour))
    if hatched:
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(*HATCH), 2))
        for offset in range(-16, 16, 6):
            painter.drawLine(offset, 16, offset + 16, 0)
        _ = painter.end()
    return QIcon(pixmap)


def tool_icon(name: str, colour: QColor) -> QIcon:
    """A small drawing of a tool, in the colour of the window's text."""
    pixmap = QPixmap(22, 22)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(colour, 2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    match name:
        case "brush":
            wide = QPen(colour, 5)
            wide.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(wide)
            painter.drawLine(QPointF(6, 16), QPointF(16, 6))
        case "eraser":
            painter.translate(11, 11)
            painter.rotate(-40)
            painter.drawRect(QRectF(-8, -4, 16, 8))
            painter.drawLine(QPointF(-2, -4), QPointF(-2, 4))
        case "fill":
            painter.drawPolygon(
                QPolygonF([QPointF(4, 11), QPointF(11, 4), QPointF(17, 10), QPointF(10, 17)])
            )
            painter.drawLine(QPointF(17, 14), QPointF(17, 17))
            painter.setBrush(colour)
            painter.drawEllipse(QPointF(17, 18), 1.5, 1.5)
        case "line":
            painter.drawLine(QPointF(4, 18), QPointF(18, 4))
            painter.setBrush(colour)
            painter.drawEllipse(QPointF(4, 18), 1.6, 1.6)
            painter.drawEllipse(QPointF(18, 4), 1.6, 1.6)
        case "rectangle":
            painter.drawRect(QRectF(4, 5, 14, 12))
        case "ellipse":
            painter.drawEllipse(QRectF(3, 5, 16, 12))
        case _:  # the hand: a cross of four arrows
            painter.drawLine(QPointF(11, 3), QPointF(11, 19))
            painter.drawLine(QPointF(3, 11), QPointF(19, 11))
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                tip = QPointF(11 + dx * 8, 11 + dy * 8)
                painter.drawLine(tip, QPointF(tip.x() - dx * 3 - dy * 3, tip.y() - dy * 3 - dx * 3))
                painter.drawLine(tip, QPointF(tip.x() - dx * 3 + dy * 3, tip.y() - dy * 3 + dx * 3))
    _ = painter.end()
    return QIcon(pixmap)


# -- drafts -----------------------------------------------------------------------------------


class Drafts:
    """What was drawn and not used, one picture for each continent, kept in the data folder so
    that closing the editor (or the generator) loses nothing."""

    def __init__(self, folder: Path) -> None:
        self.folder: Path = folder

    def _path(self, continent: str) -> Path:
        return self.folder / f"land-draft-{continent}.png"

    def load(self, continent: str, shape: tuple[int, int]) -> NDArray[np.uint8] | None:
        """The draft of ``continent`` when it is the size of the sheet; else None."""
        try:
            kinds = landmask.decode_kinds(self._path(continent).read_bytes())
        except (OSError, LandMaskError):
            return None
        return kinds if kinds.shape == shape else None

    def save(self, continent: str, kinds: NDArray[np.uint8]) -> None:
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            _ = self._path(continent).write_bytes(studio.kinds_png(kinds))
        except OSError:
            pass  # A draft is a convenience.
