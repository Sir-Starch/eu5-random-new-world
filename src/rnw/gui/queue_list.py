"""The worlds waiting in the queue, one row for each, as the Tauri window lists them: the one being
made marked, a failed one with its error, and a button to take any of them out."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QToolButton, QVBoxLayout, QWidget

from rnw.app.worldcode import encode
from rnw.gui.text import text
from rnw.gui.view import queue_type

if TYPE_CHECKING:
    from rnw.app.service import Request
    from rnw.gui.controller import Controller

MAKING: Final[str] = "▶"
FAILED: Final[str] = "⚠"
REMOVE: Final[str] = "✕"


class QueueList(QWidget):
    """A row for each queued world, kept equal to the controller's queue."""

    def __init__(self, controller: Controller) -> None:
        super().__init__()
        self.controller: Controller = controller
        self._shown: tuple[tuple[str, bool, str], ...] = ()
        self._buttons: list[QToolButton] = []
        self.rows: QVBoxLayout = QVBoxLayout(self)
        self.rows.setContentsMargins(0, 0, 0, 0)
        self.rows.setSpacing(2)
        self.setVisible(False)

    def refresh(self) -> None:
        """Rebuild the rows when the queue changed; else only say which may be removed."""
        controller = self.controller
        entries = controller.queue_entries()
        key = tuple((encode(job.code), running, error) for job, running, error in entries)
        if key != self._shown:
            self._shown = key
            self._rebuild(entries)
        for button, (_code, running, _error) in zip(self._buttons, key, strict=True):
            button.setEnabled(not running)
        self.setVisible(bool(key))

    def _rebuild(self, entries: list[tuple[Request, bool, str]]) -> None:
        while self.rows.count():
            item = self.rows.takeAt(0)
            widget = None if item is None else item.widget()
            if widget is not None:
                widget.setParent(None)  # gone from the list now, freed when the loop is idle
                widget.deleteLater()
        self._buttons = []
        for job, running, error in entries:
            row = QWidget()
            line = QHBoxLayout(row)
            line.setContentsMargins(0, 0, 0, 0)
            mark = QLabel(MAKING if running else FAILED if error else "")
            mark.setFixedWidth(16)
            mark.setToolTip(text("queue_making") if running else error)
            name = QLabel(f"{queue_type(job.code)}  ·  {job.code.seed}")
            name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            remove = QToolButton()
            remove.setText(REMOVE)
            remove.setToolTip(text("queue_remove"))
            remove.setAccessibleName(text("queue_remove"))
            code = encode(job.code)
            _ = remove.clicked.connect(
                lambda _checked=False, code=code: self.controller.dequeue(code)
            )
            line.addWidget(mark)
            line.addWidget(name, 1)
            line.addWidget(remove)
            self.rows.addWidget(row)
            self._buttons.append(remove)
