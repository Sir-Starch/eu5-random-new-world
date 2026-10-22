"""The maps of a world: its atlas by layer, with a legend, facts under the cursor and a search.

The panel knows nothing of the game or of how worlds are kept; it is given an ``Atlas`` (or none)
and whether its New World may be shown, and tells its owner when the player asks to reveal it
(ADR 0010, B). A world that is not revealed shows only a notice and a button.
"""

# Qt stubs type signals and widgets loosely; NumPy stubs type array arithmetic as Any.
# pyright: reportAny=false, reportUninitializedInstanceVariable=false

from __future__ import annotations

from typing import TYPE_CHECKING, Final, override

import numpy as np
from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from rnw import atlas as atlas_module
from rnw.gui.preview import PreviewView
from rnw.gui.text import text

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray
    from PySide6.QtGui import QMouseEvent

    from rnw.atlas import Atlas

MUTED: Final[str] = ""
SWATCH: Final[int] = 14
RESULTS: Final[int] = 40


def to_image(picture: NDArray[np.uint8]) -> QImage:
    """A Qt image of an RGB picture (the image owns a copy of the pixels)."""
    height, width, _ = picture.shape
    contiguous = np.ascontiguousarray(picture)
    image = QImage(contiguous.data, width, height, 3 * width, QImage.Format.Format_RGB888)
    return image.copy()


class MapView(PreviewView):
    """The picture of a layer; reports the pixel under the cursor."""

    moved: Signal = Signal(int, int)
    left: Signal = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

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
    def leaveEvent(self, event: QEvent) -> None:
        super().leaveEvent(event)
        self.left.emit()


class MapsPanel(QWidget):
    """Layers, the map, the legend, what lies under the cursor and a search."""

    reveal_requested: Signal = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._atlas: Atlas | None = None
        self._layer: str = atlas_module.LAYERS[0]
        self._highlight: tuple[int, ...] = ()
        self._matches: list[atlas_module.Match] = []
        self._identity: int = 0
        self._drawn: tuple[int, str, tuple[int, ...]] | None = None
        outer = QVBoxLayout(self)
        self.pages: QStackedWidget = QStackedWidget()
        outer.addWidget(self.pages)
        _ = self.pages.addWidget(self._covered_page())
        _ = self.pages.addWidget(self._maps_page())

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
        layout = QVBoxLayout(page)
        buttons = QHBoxLayout()
        self.layer_buttons: QButtonGroup = QButtonGroup(self)
        for number, layer in enumerate(atlas_module.LAYERS):
            button = QPushButton(text(f"layer.{layer}"))
            button.setCheckable(True)
            button.setToolTip(text(f"layer.{layer}.tip"))
            self.layer_buttons.addButton(button, number)
            buttons.addWidget(button)
        self.layer_buttons.button(0).setChecked(True)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        body = QHBoxLayout()
        self.map_view: MapView = MapView()
        body.addWidget(self.map_view, 3)
        body.addLayout(self._side(), 1)
        layout.addLayout(body, 1)
        self.facts: QLabel = QLabel(text("facts_hint"))
        self.facts.setWordWrap(True)
        self.facts.setMinimumHeight(60)
        self.facts.setStyleSheet(MUTED)
        layout.addWidget(self.facts)
        self.summary: QLabel = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        _ = self.layer_buttons.idClicked.connect(self._pick_layer)
        _ = self.map_view.moved.connect(self.show_facts_at)
        _ = self.map_view.left.connect(self.clear_facts)
        return page

    def _side(self) -> QVBoxLayout:
        side = QVBoxLayout()
        self.search: QLineEdit = QLineEdit()
        self.search.setPlaceholderText(text("search_hint"))
        self.search.setClearButtonEnabled(True)
        self.results: QListWidget = QListWidget()
        self.results.setMaximumHeight(150)
        self.legend_list: QListWidget = QListWidget()
        self.legend_list.setIconSize(QSize(SWATCH, SWATCH))
        self.legend_title: QLabel = QLabel(text("legend"))
        self.legend_title.setStyleSheet(MUTED)
        for widget in (self.search, self.results, self.legend_title):
            side.addWidget(widget)
        side.addWidget(self.legend_list, 1)
        _ = self.search.textChanged.connect(self._searched)
        _ = self.results.currentRowChanged.connect(self._chosen)
        return side

    # -- what to show --------------------------------------------------------------------------

    @property
    def layer(self) -> str:
        """The layer shown now."""
        return self._layer

    def show_world(self, atlas: Atlas | None, *, revealed: bool, identity: int = 0) -> None:
        """Show the atlas of a world, or the reason there is nothing to show.

        ``identity`` tells one world from another so that the picture is drawn afresh for a new
        one and kept (with its zoom) while only the layer or the highlight changes.
        """
        if atlas is None:
            self.covered_notice.setText(text("no_atlas"))
            self.reveal_button.setVisible(False)
            self.pages.setCurrentIndex(0)
            return
        if not revealed:
            self.covered_notice.setText(text("covered_maps"))
            self.reveal_button.setVisible(True)
            self.pages.setCurrentIndex(0)
            return
        self._identity = identity
        if atlas is not self._atlas:
            self._atlas = atlas
            self._highlight = ()
            self._matches = []
            self.results.clear()
            self.search.clear()
            self._drawn = None
        self.pages.setCurrentIndex(1)
        self._draw()

    def _draw(self) -> None:
        atlas = self._atlas
        if atlas is None:
            return
        key = (self._identity, self._layer, self._highlight)
        if key != self._drawn:
            picture = atlas_module.render(atlas, self._layer, highlight=self._highlight)
            self.map_view.show_image(to_image(picture), f"{self._identity}:{self._layer}")
            self._legend(atlas)
            self._drawn = key

    def _legend(self, atlas: Atlas) -> None:
        self.legend_list.clear()
        for label, colour, count in atlas_module.legend(atlas, self._layer):
            swatch = QPixmap(SWATCH, SWATCH)
            swatch.fill(QColor(*colour))
            suffix = f"  ({count})" if count else ""
            item = QListWidgetItem(QIcon(swatch), f"{label}{suffix}")
            self.legend_list.addItem(item)

    def picture(self) -> NDArray[np.uint8] | None:
        """The picture shown, as pixels, or None when there is none."""
        atlas = self._atlas
        if atlas is None or self.pages.currentIndex() != 1:
            return None
        return atlas_module.render(atlas, self._layer, highlight=self._highlight)

    # -- what the player does ------------------------------------------------------------------

    def _pick_layer(self, number: int) -> None:
        self._layer = atlas_module.LAYERS[number]
        self._drawn = None
        self._draw()

    def select_layer(self, layer: str) -> None:
        """Show ``layer`` (as the buttons do)."""
        number = atlas_module.LAYERS.index(layer)
        self.layer_buttons.button(number).setChecked(True)
        self._pick_layer(number)

    def show_facts_at(self, row: int, column: int) -> None:
        atlas = self._atlas
        facts = (
            None
            if atlas is None
            else atlas_module.describe(atlas, atlas_module.cell_at(atlas, row, column))
        )
        self.facts.setText(describe_text(facts) if facts is not None else text("facts_hint"))

    def clear_facts(self) -> None:
        self.facts.setText(text("facts_hint"))

    def _searched(self, query: str) -> None:
        atlas = self._atlas
        self.results.clear()
        self._matches = [] if atlas is None else atlas_module.find(atlas, query, limit=RESULTS)
        for match in self._matches:
            self.results.addItem(f"{text(f'found.{match.kind}')}: {match.label}")
        if not self._matches:
            self._set_highlight(())

    def _chosen(self, row: int) -> None:
        if 0 <= row < len(self._matches):
            self._set_highlight(self._matches[row].cells)

    def _set_highlight(self, cells: Sequence[int]) -> None:
        wanted = tuple(cells)
        if wanted != self._highlight:
            self._highlight = wanted
            self._draw()

    def set_summary(self, line: str) -> None:
        """The one line under the map: how many countries, cultures and locations."""
        self.summary.setText(line)


class CompareDialog(QDialog):
    """Two worlds' maps side by side, on one layer."""

    def __init__(self, parent: QWidget, entries: list[tuple[str, Atlas]], layer: str) -> None:
        super().__init__(parent)
        self.setWindowTitle(text("compare_title"))
        self._entries: list[tuple[str, Atlas]] = entries
        self._layer: str = layer
        layout = QVBoxLayout(self)
        buttons = QHBoxLayout()
        self.layer_buttons: QButtonGroup = QButtonGroup(self)
        for number, name in enumerate(atlas_module.LAYERS):
            button = QPushButton(text(f"layer.{name}"))
            button.setCheckable(True)
            button.setChecked(name == layer)
            self.layer_buttons.addButton(button, number)
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
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
            column.addWidget(choice)
            column.addWidget(view, 1)
            columns.addLayout(column, 1)
            self.choices.append(choice)
            self.views.append(view)
            _ = choice.currentIndexChanged.connect(self.redraw)
        layout.addLayout(columns, 1)
        _ = self.layer_buttons.idClicked.connect(self._pick)
        self.resize(1200, 700)
        self.redraw()

    def _pick(self, number: int) -> None:
        self._layer = atlas_module.LAYERS[number]
        self.redraw()

    def redraw(self) -> None:
        """Draw both maps on the chosen layer."""
        for choice, view in zip(self.choices, self.views, strict=True):
            found = self._entries[choice.currentIndex()][1]
            picture = atlas_module.render(found, self._layer)
            view.show_image(to_image(picture), f"{choice.currentIndex()}:{self._layer}")


def describe_text(facts: atlas_module.Facts) -> str:
    """What the atlas says of a location, in a few lines."""
    lines = [f"{facts.name or facts.key}  ({text(f'kind.{facts.kind}')})"]
    if facts.kind == "land":
        owner = facts.country.name if facts.country is not None else text("no_country")
        lines.append(f"{text('fact.country')}: {owner}")
        if facts.culture:
            culture = atlas_module.pretty(facts.culture)
            religion = atlas_module.pretty(facts.religion)
            lines.append(f"{text('fact.culture')}: {culture} · {text('fact.religion')}: {religion}")
        material = atlas_module.pretty(facts.material)
        land = " · ".join(
            item for item in (facts.vegetation, facts.topography, facts.climate) if item
        )
        lines.append(f"{text('fact.material')}: {material} · {land}")
        if facts.population:
            population = f"{text('fact.population')}: {facts.population}"
            lines.append(f"{population} · {text('fact.complexity')}: {facts.complexity}")
    return "\n".join(lines)
