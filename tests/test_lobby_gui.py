from __future__ import annotations

import pytest

from rnw.eu5_lobby_gui import (
    GUI_FILES,
    LOCATION_SCRIPTED_GUI,
    patch_gui,
    scripted_gui_text,
)

CLICK = "\t" * 14


def _lobby_fixture() -> str:
    """What the game's lobby file holds where the cover used to gate the country list."""
    return (
        "\t\t\t\t\t\t\tfixedgridbox = {\n"
        '\t\t\t\t\t\t\t\tdatamodel = "[AccessLobbyCountryList.GetCountries]"\n'
        "item = {\n"
        "\t\t\t\t\t\t\t\t\twidget = {\n"
        "\t\t\t\t\t\t\t\t\t\tsize = { 100% 90% }\n"
        "\t\t\t\t\t\t\t\t\t}\n"
        f"{CLICK}click_mode = single\n\n"
        f'{CLICK}block "click_action" {{\n'
        f'{CLICK}\ttitle = "LOBBYVIEW_SELECT_COUNTRY"\n'
        f'{CLICK}\ton_action = "[SetLobbyCountry(Country.Self)]"\n'
        "type LobbySelectedCountryPanel = widget {\n\t}\n"
        'enabled = "[And3(GameLobby.CanStart, Not(HasHostError), Not(LobbyView.ShowHosting))]"\n'
        'enabled = "[GameLobby.CanJoin]"\n'
    )


def test_the_countries_of_the_new_world_can_be_chosen_so_the_lobby_file_is_not_changed() -> None:
    """The list, the click, the selected panel and the buttons are the game's own (2026-11-01)."""
    assert GUI_FILES == ("game/in_game/gui/map_markers.gui",)
    assert patch_gui("game/in_game/gui/multiplayer_lobby.gui", _lobby_fixture()) is None
    assert patch_gui("game/in_game/gui/context_menu.gui", "visible = yes") is None


@pytest.mark.parametrize("marker", ["market_marker", "raw_goods_marker"])
def test_world_cities_and_resource_markers_are_hidden_during_lobby_only(marker: str) -> None:
    source = (
        'name = "market_marker"\n\tmax_update_rate = 4\n'
        'name = "raw_goods_marker"\n\tallow_outside = yes\n'
    )

    patched = patch_gui(GUI_FILES[0], source)

    assert patched is not None
    assert "And(IsLobbyOpen, GetScriptedGui('rnw_new_world_location')" in patched
    assert patched.count(f'name = "{marker}"') == 1


def test_gui_overrides_fail_closed_when_any_source_anchor_is_missing_or_duplicated() -> None:
    marker_source = 'name = "market_marker"\n\tmax_update_rate = 4\n'
    marker_source += 'name = "raw_goods_marker"\n\tallow_outside = yes\n'

    assert patch_gui(GUI_FILES[0], marker_source.replace('name = "market_marker"', "")) is None
    assert patch_gui(GUI_FILES[0], marker_source + marker_source) is None
    assert patch_gui("game/in_game/gui/unknown.gui", marker_source) is None


def test_location_scripted_gui_resolves_the_location_scope_to_america() -> None:
    emitted = scripted_gui_text()

    assert LOCATION_SCRIPTED_GUI in emitted
    assert "scope = location" in emitted
    assert "continent = continent:america" in emitted
