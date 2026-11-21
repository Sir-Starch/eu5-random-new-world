"""The classic window's land tools: for each continent the world generates, its land image, its
template and its drawing in the land editor, as the Tauri window offers them on the new world's
page.

The rules (which continents can be drawn, what a picture must be) live in the controller; this
module only keeps a row of buttons for each continent equal to it.
"""

# Qt windows are built in helper methods; every widget exists once the constructor returns.
# pyright: reportUninitializedInstanceVariable=false

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final

from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from rnw.gui.text import text
from rnw.settings import AMERICA, REGIONAL_PRESETS

if TYPE_CHECKING:
    from collections.abc import Callable

    from rnw.gui.controller import Controller

CONTINENTS: Final[tuple[str, ...]] = (AMERICA, *REGIONAL_PRESETS)


class LandRow(QWidget):
    """One continent's land: where it was drawn, and the buttons that change that."""

    def __init__(
        self,
        key: str,
        controller: Controller,
        open_editor: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.key: str = key
        self.controller: Controller = controller
        self._open_editor: Callable[[str], None] = open_editor
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        self.name: QLabel = QLabel(text(f"continent.{key}"))
        self.name.setStyleSheet("font-weight: 600")
        self.edit_button: QPushButton = QPushButton(text("editor.edit"))
        self.image_button: QPushButton = QPushButton(text("land_image"))
        self.image_button.setToolTip(text("land_image_tip"))
        self.template_button: QPushButton = QPushButton(text("land_template"))
        self.template_button.setToolTip(text("land_template_tip"))
        self.state: QLabel = QLabel()
        self.state.setWordWrap(True)
        self.clear_button: QPushButton = QPushButton(text("land_image_clear"))
        for widget in (
            self.name,
            self.edit_button,
            self.image_button,
            self.template_button,
            self.state,
            self.clear_button,
        ):
            row.addWidget(widget)
        row.addStretch(1)
        _ = self.edit_button.clicked.connect(self._edit)
        _ = self.image_button.clicked.connect(self._choose_image)
        _ = self.template_button.clicked.connect(self._save_template)
        _ = self.clear_button.clicked.connect(self._clear)

    def _edit(self) -> None:
        self._open_editor(self.key)

    def _clear(self) -> None:
        self.controller.clear_land_image(self.key)

    def _choose_image(self) -> None:
        chosen, _ = QFileDialog.getOpenFileName(
            self, text("land_image_title"), str(Path.home()), text("land_image_files")
        )
        if chosen:
            problem = self.controller.choose_land_image(Path(chosen), self.key)
            if problem:
                _ = QMessageBox.warning(self, text("land_image"), problem)

    def _save_template(self) -> None:
        title = text("land_template")
        chosen, _ = QFileDialog.getSaveFileName(
            self, title, str(Path.home() / "new-world-template.png"), "PNG (*.png)"
        )
        if chosen:
            problem = self.controller.save_land_template(Path(chosen), self.key)
            if problem:
                _ = QMessageBox.warning(self, title, problem)

    def refresh(self, *, busy: bool, several: bool) -> None:
        """Show the row's state: the picture the land is drawn in, if any, and what can be done."""
        controller = self.controller
        drawable = self.key in controller.drawable_continents()
        self.setVisible(drawable)
        if not drawable:
            return
        drawn = controller.drawings().get(self.key)
        if drawn is None:
            self.state.setText("")
        elif several:
            self.state.setText(
                text(
                    "land_image_of",
                    continent=text(f"continent.{self.key}"),
                    id=format(drawn.id, "x"),
                )
            )
        else:
            self.state.setText(text("land_image_chosen", id=format(drawn.id, "x")))
        self.clear_button.setVisible(drawn is not None)
        self.clear_button.setEnabled(not busy)
        self.image_button.setEnabled(not busy)
        self.name.setVisible(several)
        ready = not controller.busy and controller.game is not None
        self.template_button.setEnabled(ready)
        self.edit_button.setEnabled(ready)
        self.edit_button.setToolTip(controller.editor_problem() or text("editor.open_tip"))


class LandTools(QGroupBox):
    """The land of every continent the world generates, and the two buttons that make land: the
    sketches of continents and the land editor."""

    def __init__(
        self,
        controller: Controller,
        open_editor: Callable[[str | None], None],
        sketch: Callable[[], None],
    ) -> None:
        super().__init__(text("land_tools"))
        self.controller: Controller = controller
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        self.sketch_button: QPushButton = QPushButton(text("sketch.open"))
        self.editor_button: QPushButton = QPushButton(text("editor.open"))
        header.addWidget(self.sketch_button)
        header.addWidget(self.editor_button)
        header.addStretch(1)
        layout.addLayout(header)
        self.rows: dict[str, LandRow] = {
            key: LandRow(key, controller, open_editor) for key in CONTINENTS
        }
        for row in self.rows.values():
            layout.addWidget(row)
        _ = self.sketch_button.clicked.connect(sketch)
        _ = self.editor_button.clicked.connect(lambda: open_editor(None))

    def refresh(self, *, busy: bool) -> None:
        controller = self.controller
        drawable = controller.drawable_continents()
        self.setVisible(any(controller.continent_selection().values()))
        for row in self.rows.values():
            row.refresh(busy=busy, several=len(drawable) > 1)
        sketch_problem = controller.sketch_problem()
        editor_problem = controller.editor_problem()
        self.sketch_button.setEnabled(not controller.busy and sketch_problem is None)
        self.sketch_button.setToolTip(sketch_problem or text("sketch.open_tip"))
        self.editor_button.setEnabled(not controller.busy and editor_problem is None)
        self.editor_button.setToolTip(editor_problem or text("editor.open_tip"))
