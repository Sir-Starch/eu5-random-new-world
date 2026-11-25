"""The Mediterranean follows the new water and its retained shores."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw.eu5_canvas import Canvas
from rnw.eu5_map import Eu5Map
from rnw.eu5_newworld import outside_contacts
from rnw.eu5_sea_basins import (
    GEOGRAPHY_FILE,
    MEDITERRANEAN,
    mediterranean_areas,
    mediterranean_cells,
)
from rnw.hierarchy import contact_graph
from rnw.model import CellClass
from rnw.newworld import derive_world

if TYPE_CHECKING:
    from pathlib import Path


def test_mediterranean_membership_comes_from_the_installed_script(tmp_path: Path) -> None:
    source = tmp_path / GEOGRAPHY_FILE
    source.parent.mkdir(parents=True)
    text = f"{MEDITERRANEAN} = {{ area = {{ west # a comment\n east }} }}\n"
    unrelated = "another_geography = { area = { outside } }"
    _ = source.write_text(text + unrelated, encoding="utf-8-sig")
    assert mediterranean_areas(tmp_path) == {"west", "east"}
    _ = source.write_text(unrelated, encoding="utf-8")
    with pytest.raises(ValueError, match="Missing Mediterranean sea areas"):
        _ = mediterranean_areas(tmp_path)


@pytest.mark.parametrize("land_bridge", [False, True])
def test_mediterranean_keeps_its_shore_areas_and_stops_at_other_water(*, land_bridge: bool) -> None:
    # Two retained shores in one basin, with newly flooded land between them. The western
    # outlet has Atlantic water, and a cut-off former Mediterranean cell has an eastern outlet.
    labels = np.array([[-1, 0, 1, 2, 3, -1, 4, 5, -1, 6, -1, 7, -1]], dtype=np.int32)
    old = np.array([[2, 2, 3, 3, 3, 1, 3, 0, 0, 2, 4, 2, 3]], dtype=np.int32)
    sea = CellClass.SEA
    land = CellClass.LAND
    world = derive_world(
        labels,
        (sea, sea, sea, sea, sea, land if land_bridge else sea, sea, sea),
        np.ones_like(labels),
        wrap_x=True,
    )
    game = Eu5Map(
        keys=("open", "west", "east", "land", "other"),
        colors=np.arange(5),
        classes=(sea, sea, sea, land, sea),
        ambiguous=np.zeros(5, dtype=bool),
        continents=("atlantic", "africa", "europe", "africa", "asia"),
        rgb=np.empty((*labels.shape, 3), dtype=np.uint8),
        labels=old,
        rivers=np.zeros(labels.shape, dtype=np.uint8),
        locations_chunks=(),
        rivers_chunks=(),
        points=(),
        inputs=(),
    )
    canvas = Canvas(0, 0, labels >= 0, labels.shape, np.zeros(5, bool), np.zeros(5, bool))
    graph = contact_graph(world.centroids, world.edges, [kind is sea for kind in world.classes])
    found = mediterranean_cells(
        game,
        canvas,
        world,
        graph,
        contacts=outside_contacts(game, canvas, world, len(game.keys)),
        original_areas=("atlantic", "west", "east", "land", "other_sea"),
        basin_areas={"west", "east"},
    )
    assert found == {0: "east", 1: "east", 2: "west", 3: "west", 4: "west"}
