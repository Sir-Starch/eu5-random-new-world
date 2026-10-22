from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from rnw.gui.maps import to_image
from rnw.gui.text import text

if TYPE_CHECKING:
    from rnw.gui.controller import Controller


class CandidatesDialog(QDialog):
    def __init__(self, parent: QWidget, controller: Controller) -> None:
        super().__init__(parent)
        self.controller: Controller = controller
        self.setWindowTitle(text("candidates"))
        self.resize(720, 480)
        layout = QVBoxLayout(self)
        hint = QLabel(text("candidates_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.choices: QListWidget = QListWidget()
        self.choices.setViewMode(QListWidget.ViewMode.IconMode)
        self.choices.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.choices.setIconSize(QSize(192, 96))
        self.choices.setWordWrap(True)
        for number, found in enumerate(self.controller.candidates, start=1):
            item = QListWidgetItem(
                QIcon(QPixmap.fromImage(to_image(found.picture))),
                text(
                    "candidate_item", number=number, seed=found.seed, land=found.land_permille / 10
                ),
            )
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.choices.addItem(item)
        layout.addWidget(self.choices, 1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        _ = buttons.accepted.connect(self.accept)
        _ = buttons.rejected.connect(self.reject)
        _ = self.accepted.connect(self._choose)
        _ = self.choices.itemDoubleClicked.connect(self._activated)
        layout.addWidget(buttons)
        self.choices.setCurrentRow(0)

    def _choose(self) -> None:
        self.controller.choose_candidate(self.choices.currentRow())

    def _activated(self, _item: QListWidgetItem) -> None:
        self.accept()
