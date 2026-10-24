from __future__ import annotations

from dataclasses import dataclass
from typing import Final

MULTIPLAYER_LOBBY: Final[str] = "game/in_game/gui/multiplayer_lobby.gui"
MAP_MARKERS: Final[str] = "game/in_game/gui/map_markers.gui"
GUI_FILES: Final[tuple[str, str]] = (MULTIPLAYER_LOBBY, MAP_MARKERS)
LOCATION_SCRIPTED_GUI: Final[str] = "rnw_new_world_location"
COUNTRY_SCRIPTED_GUI: Final[str] = "rnw_new_world_country"
COUNTRY_SCOPE: Final[str] = "rnw_country"


def new_world_country(country: str) -> str:
    """Ask about an optional country without giving the scripted GUI an empty typed root."""
    return (
        f"GetScriptedGui('{COUNTRY_SCRIPTED_GUI}').IsShown("
        f"GuiScope.AddScope('{COUNTRY_SCOPE}', {country}.MakeScope).End)"
    )


COUNTRY_SELECTED: Final[str] = (
    f"Not({new_world_country('LobbyView.GetSelectedPlayable.GetCountry')})"
)


@dataclass(frozen=True, slots=True)
class GuiEdit:
    path: str
    anchor: str
    replacement: str
    count: int = 1


# A country of the New World stays in the list, dimmed and without a click, instead of being
# hidden. A hidden card either keeps its cell of the fixed grid (a blank stretch) or, in a vbox
# that ignores invisible cards, makes the list build every card of the game at once; the owner saw
# the flags of that list flicker hard and the blank stretches return in a search (experiment 037).
# The grid stays the game's own, so the list is laid out and searched as in the vanilla lobby.
CARD_OLD_WORLD: Final[str] = f"Not({new_world_country('Country')})"
_COUNTRY_LIST_ANCHOR: Final[str] = (
    "item = {\n\t\t\t\t\t\t\t\t\twidget = {\n\t\t\t\t\t\t\t\t\t\tsize = { 100% 90% }\n"
)
_COUNTRY_LIST_REPLACEMENT: Final[str] = (
    _COUNTRY_LIST_ANCHOR + f'\t\t\t\t\t\t\t\t\t\talpha = "[TransparentIfFalse({CARD_OLD_WORLD})]"\n'
)
_CLICK_INDENT: Final[str] = "\t" * 14
_COUNTRY_CLICK_ANCHOR: Final[str] = (
    f"{_CLICK_INDENT}click_mode = single\n\n"
    f'{_CLICK_INDENT}block "click_action" {{\n'
    f'{_CLICK_INDENT}\ttitle = "LOBBYVIEW_SELECT_COUNTRY"\n'
)
_COUNTRY_CLICK_REPLACEMENT: Final[str] = _COUNTRY_CLICK_ANCHOR.replace(
    "click_mode = single\n\n",
    f'click_mode = single\n{_CLICK_INDENT}enabled = "[{CARD_OLD_WORLD}]"\n\n',
)
_SELECTED_COUNTRY_PANEL: Final[str] = "type LobbySelectedCountryPanel = widget {"
_SELECTED_COUNTRY_PANEL_REPLACEMENT: Final[str] = (
    _SELECTED_COUNTRY_PANEL
    + '\n\t\tvisible = "[Or(Not(LobbyView.HasSelectedPlayable), '
    + COUNTRY_SELECTED
    + ')]"'
)
_RANDOM_SELECTOR_ANCHOR: Final[str] = (
    "button_regular = {\n"
    "\t\t\tusing = layoutpolicy_expanding\n\n"
    "\t\t\ttext_single = {\n"
    "\t\t\t\tparentanchor = center\n"
    "\t\t\t\tmaximumsize = {200 -1}\n"
    '\t\t\t\ttext = "MULTIPLAYER_LOBBY_CHOOSE_RANDOM_CHARACTER"'
)
_RANDOM_SELECTOR_REPLACEMENT: Final[str] = _RANDOM_SELECTOR_ANCHOR.replace(
    "button_regular = {\n", 'button_regular = {\n\t\t\tvisible = "[Not(IsLobbyOpen)]"\n'
)
_MARKER_SPECS: Final[tuple[tuple[str, str, str], ...]] = (
    ("market_marker", "MarketMarker.GetLocation", "max_update_rate = 4"),
    ("raw_goods_marker", "RawGoodsMarker.GetLocation", "allow_outside = yes"),
)


def _location_hidden(marker_location: str) -> str:
    return (
        f"[Not(And(IsLobbyOpen, GetScriptedGui('{LOCATION_SCRIPTED_GUI}').IsShown("
        f"GuiScope.SetRoot({marker_location}.MakeScope).End)))]"
    )


_LOBBY_EDITS: Final[tuple[GuiEdit, ...]] = (
    GuiEdit(MULTIPLAYER_LOBBY, _COUNTRY_LIST_ANCHOR, _COUNTRY_LIST_REPLACEMENT),
    GuiEdit(MULTIPLAYER_LOBBY, _COUNTRY_CLICK_ANCHOR, _COUNTRY_CLICK_REPLACEMENT),
    GuiEdit(
        MULTIPLAYER_LOBBY,
        _SELECTED_COUNTRY_PANEL,
        _SELECTED_COUNTRY_PANEL_REPLACEMENT,
    ),
    GuiEdit(
        MULTIPLAYER_LOBBY,
        'enabled = "[And3(GameLobby.CanStart, Not(HasHostError), Not(LobbyView.ShowHosting))]"',
        (
            'enabled = "[And4(GameLobby.CanStart, Not(HasHostError), '
            f'Not(LobbyView.ShowHosting), {COUNTRY_SELECTED})]"'
        ),
    ),
    GuiEdit(
        MULTIPLAYER_LOBBY,
        'enabled = "[GameLobby.CanStart]"',
        f'enabled = "[And(GameLobby.CanStart, {COUNTRY_SELECTED})]"',
    ),
    GuiEdit(
        MULTIPLAYER_LOBBY,
        'enabled = "[GameLobby.CanJoin]"',
        f'enabled = "[And(GameLobby.CanJoin, {COUNTRY_SELECTED})]"',
        count=4,
    ),
    GuiEdit(
        MULTIPLAYER_LOBBY,
        _RANDOM_SELECTOR_ANCHOR,
        _RANDOM_SELECTOR_REPLACEMENT,
    ),
)
_MARKER_EDITS: Final[tuple[GuiEdit, ...]] = tuple(
    GuiEdit(
        MAP_MARKERS,
        f'name = "{name}"\n\t{next_line}\n',
        f'name = "{name}"\n\tvisible = "{_location_hidden(location)}"\n\t{next_line}\n',
    )
    for name, location, next_line in _MARKER_SPECS
)
_GUI_EDITS: Final[tuple[GuiEdit, ...]] = (*_LOBBY_EDITS, *_MARKER_EDITS)


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
