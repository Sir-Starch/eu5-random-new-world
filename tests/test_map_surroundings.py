"""The classic window's map around a world's own lands: the lands it keeps from the game in one grey
and the names of its continents, as the Tauri window shows them."""

# Qt stubs type signals and widgets loosely; NumPy stubs type array arithmetic as Any.
# pyright: reportAny=false

from __future__ import annotations

import time
from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw import atlas as atlas_module
from rnw.app import surroundings
from rnw.gui import mapstyle
from rnw.gui.text import text
from tests.fakes import synthetic_atlas

try:  # the window needs PySide6 and the system's graphics libraries
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QFont, QImage, QPainter
    from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

    from rnw.gui import maps
except ImportError:
    pytest.skip("PySide6 is not available", allow_module_level=True)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rnw.atlas import Atlas

KEPT_COLUMNS = 10


@pytest.fixture(scope="module")
def application() -> QApplication:
    """One QApplication for the module (Qt allows a single one per process)."""
    existing = QApplication.instance()
    return existing if isinstance(existing, QApplication) else QApplication([])


def pump(condition: Callable[[], bool], timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    app = QApplication.instance()
    while not condition():
        assert time.monotonic() < deadline, "the map was not drawn in time"
        if app is not None:
            app.processEvents()
        time.sleep(0.01)


def _world() -> tuple[Atlas, surroundings.Surroundings]:
    """The test atlas with open sea along its left edge, which is land the world keeps, and its
    six locations in two continents."""
    found = synthetic_atlas()
    labels = found.labels.copy()
    labels[:, :KEPT_COLUMNS] = 0
    kept = np.zeros(found.size, dtype=np.bool_)
    kept[:, : KEPT_COLUMNS - 2] = True
    continent = np.array([0, 0, 0, 1, 1, 1], dtype=np.int8)
    return replace(found, labels=labels), surroundings.Surroundings(kept, continent)


def _lens(found: Atlas) -> mapstyle.StyledLens:
    words: atlas_module.Words = atlas_module.ENGLISH
    return mapstyle.style(found, "countries", words, tribes=False, tribes_label="Tribes")


def test_the_lands_a_world_keeps_lie_in_one_grey_under_the_open_sea_only() -> None:
    found, around = _world()
    assert around.kept is not None
    lens = _lens(found)
    bare = mapstyle.picture(found, lens, tribes=False)
    laid = mapstyle.picture(found, lens, tribes=False, kept=mapstyle.kept_alpha(around.kept))
    grey = np.array(mapstyle.COLOURS["kept"])
    # deep in the kept land the sea is the kept grey; its soft edge is between sea and grey
    assert np.abs(laid[10, 2].astype(int) - grey).max() <= 1
    assert not np.array_equal(bare[10, 2], laid[10, 2])
    # the world's own lands and the sea away from the kept land are as they were
    assert np.array_equal(bare[:, KEPT_COLUMNS + 4 :], laid[:, KEPT_COLUMNS + 4 :])
    edge = laid[10, KEPT_COLUMNS - 3 : KEPT_COLUMNS - 1].astype(int)
    assert (np.abs(edge - grey).max(axis=1) > 1).any()  # softened, not stepped


def test_the_continents_are_named_where_they_are_broadest_when_there_are_several() -> None:
    found, around = _world()
    names = [text(f"continent.{key}") for key in surroundings.CONTINENTS]
    labels = mapstyle.continent_names(found, around.continent, names)
    assert {label.text for label in labels} == {names[0], names[1]}
    assert all(label.kind == "continent" and label.weight > 0 for label in labels)
    assert labels[0].weight >= labels[1].weight
    # one continent alone needs no name; a map without continents has none
    one = np.zeros_like(around.continent)
    assert mapstyle.continent_names(found, one, names) == []
    assert mapstyle.continent_names(found, around.continent[:2], names) == []


@pytest.mark.usefixtures("application")
def test_the_names_of_the_continents_are_written_from_afar_and_fade_when_near() -> None:
    found, around = _world()
    names = [text(f"continent.{key}") for key in surroundings.CONTINENTS]
    labels = mapstyle.continent_names(found, around.continent, names)
    image = QImage(800, 400, QImage.Format.Format_RGB32)
    for zoom, written in ((0.05, 0), (6.0, 0)):
        painter = QPainter(image)
        scribe = maps.Scribe(
            painter,
            zoom=zoom,
            to_screen=lambda x, y, zoom=zoom: QPointF(x * zoom, y * zoom),
            size=(800.0, 400.0),
            base=QFont(),
        )
        scribe._continents(labels)  # pyright: ignore[reportPrivateUsage]
        _ = painter.end()
        assert len(scribe.placed) == written
    # seen whole at a size that gives them room, both are written; seen close, none is
    far = maps.Scribe(
        QPainter(image),
        zoom=0.3,
        to_screen=lambda x, y: QPointF(x * 8, y * 8),
        size=(800.0, 400.0),
        base=QFont(),
    )
    try:
        far._continents([replace(label, weight=label.weight * 4000) for label in labels])  # pyright: ignore[reportPrivateUsage]
        assert len(far.placed) == len(labels)
    finally:
        _ = far.painter.end()
    near = maps.Scribe(
        QPainter(image),
        zoom=0.6,
        to_screen=lambda x, y: QPointF(x * 8, y * 8),
        size=(800.0, 400.0),
        base=QFont(),
    )
    try:
        near._continents([replace(label, weight=label.weight * 4000) for label in labels])  # pyright: ignore[reportPrivateUsage]
        assert not near.placed
    finally:
        _ = near.painter.end()


@pytest.mark.usefixtures("application")
def test_the_map_of_a_world_shows_its_surroundings_and_keys_them_in_the_legend() -> None:
    found, around = _world()
    window = QWidget()
    layout = QVBoxLayout(window)
    panel = maps.MapsPanel()
    layout.addWidget(panel)
    window.resize(1100, 700)
    window.show()
    try:
        panel.show_world(found, revealed=True, around=lambda: around)
        pump(lambda: panel._drawn is not None)  # pyright: ignore[reportPrivateUsage]
        writing = panel._current_writing()  # pyright: ignore[reportPrivateUsage]
        assert writing is not None
        assert writing.kept
        assert len(writing.continents) == 2
        last = panel.legend_list.item(panel.legend_list.count() - 1)
        assert last.text() == text("map.kept")
        assert last.data(Qt.ItemDataRole.UserRole) is None
        panel._entry_clicked(last)  # pyright: ignore[reportPrivateUsage]
        panel._entry_entered(last)  # pyright: ignore[reportPrivateUsage]
        assert panel._isolated is None  # pyright: ignore[reportPrivateUsage]
        # a world whose surroundings cannot be read is drawn without them
        panel.show_world(replace(found), revealed=True, around=_broken)
        pump(lambda: panel._current_writing() is not None and not panel._current_writing().kept)  # pyright: ignore[reportPrivateUsage, reportOptionalMemberAccess]
        names = [panel.legend_list.item(row).text() for row in range(panel.legend_list.count())]
        assert text("map.kept") not in names
    finally:
        _ = window.close()


def _broken() -> surroundings.Surroundings:
    message = "the game's regions are gone"
    raise OSError(message)
