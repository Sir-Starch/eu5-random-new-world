"""The game's map-marker GUI, as the cover of the New World changes it at country selection.

The markers of cities and raw goods hang above the map, so they would draw the covered New World
again; while the lobby is open they are hidden for its locations (a scripted GUI of the mod
names them by continent). Nothing else of the lobby is changed: the country list, its cards, the
selected country's panel and the buttons that start or join a game are the game's own, so a
country of the New World can be chosen as any other (owner, 2026-11-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

MAP_MARKERS: Final[str] = "game/in_game/gui/map_markers.gui"
GUI_FILES: Final[tuple[str]] = (MAP_MARKERS,)
LOCATION_SCRIPTED_GUI: Final[str] = "rnw_new_world_location"


@dataclass(frozen=True, slots=True)
class GuiEdit:
    path: str
    anchor: str
    replacement: str
    count: int = 1


_MARKER_SPECS: Final[tuple[tuple[str, str, str], ...]] = (
    ("market_marker", "MarketMarker.GetLocation", "max_update_rate = 4"),
    ("raw_goods_marker", "RawGoodsMarker.GetLocation", "allow_outside = yes"),
)


def _location_hidden(marker_location: str) -> str:
    return (
        f"[Not(And(IsLobbyOpen, GetScriptedGui('{LOCATION_SCRIPTED_GUI}').IsShown("
        f"GuiScope.SetRoot({marker_location}.MakeScope).End)))]"
    )


_GUI_EDITS: Final[tuple[GuiEdit, ...]] = tuple(
    GuiEdit(
        MAP_MARKERS,
        f'name = "{name}"\n\t{next_line}\n',
        f'name = "{name}"\n\tvisible = "{_location_hidden(location)}"\n\t{next_line}\n',
    )
    for name, location, next_line in _MARKER_SPECS
)


def patch_gui(path: str, source: str) -> str | None:
    """Return a fully anchored GUI override, or None when this build has drifted."""
    edits = tuple(edit for edit in _GUI_EDITS if edit.path == path)
    if not edits:
        return None
    if any(source.count(edit.anchor) != edit.count for edit in edits):
        return None
    for edit in edits:
        source = source.replace(edit.anchor, edit.replacement)
    return source


def scripted_gui_text() -> str:
    return (
        f"{LOCATION_SCRIPTED_GUI} = {{\n"
        "\tscope = location\n"
        "\tis_shown = {\n"
        "\t\tcontinent = continent:america\n"
        "\t}\n"
        "}\n"
    )
