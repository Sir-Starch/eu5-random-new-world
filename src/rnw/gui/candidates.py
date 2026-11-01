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
    QPushButton,
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
        # Several sketches can be taken to the queue at once; one is chosen with OK.
        self.choices.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.pictures: list[QIcon] = [
            QIcon(QPixmap.fromImage(to_image(found.picture))) for found in controller.candidates
        ]
        for _found in controller.candidates:
            item = QListWidgetItem()
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.choices.addItem(item)
        self._label_items()
        layout.addWidget(self.choices, 1)
        self.note: QLabel = QLabel()
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.queue_button: QPushButton = QPushButton(text("enqueue"))
        self.queue_button.setToolTip(text("queue_hint"))
        buttons.addButton(self.queue_button, QDialogButtonBox.ButtonRole.ActionRole)
        _ = buttons.accepted.connect(self.accept)
        _ = buttons.rejected.connect(self.reject)
        _ = self.accepted.connect(self._choose)
        _ = self.queue_button.clicked.connect(self._enqueue)
        _ = self.choices.itemDoubleClicked.connect(self._activated)
        layout.addWidget(buttons)
        self.choices.setCurrentRow(0)

    def _label_items(self) -> None:
        """Each sketch's picture and words; the ones already in the queue say so."""
        waiting = self.controller.queued_candidates()
        for number, found in enumerate(self.controller.candidates, start=1):
            item = self.choices.item(number - 1)
            words = text(
                "candidate_item", number=number, seed=found.seed, land=found.land_permille / 10
            )
            if number - 1 in waiting:
                words = f"{words}\n{text('candidates.queued')}"
            item.setText(words)
            item.setIcon(self.pictures[number - 1])

    def _enqueue(self) -> None:
        """Take the selected sketches (the current one if none is) to the queue."""
        rows = sorted({self.choices.row(item) for item in self.choices.selectedItems()})
        rows = rows or [self.choices.currentRow()]
        problems = [problem for row in rows if (problem := self.controller.enqueue_candidate(row))]
        self._label_items()
        self.note.setText(
            problems[0] if problems else text("queue_count", count=len(self.controller.queue))
        )

    def _choose(self) -> None:
        self.controller.choose_candidate(self.choices.currentRow())

    def _activated(self, _item: QListWidgetItem) -> None:
        self.accept()
