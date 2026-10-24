from __future__ import annotations

import pytest

from rnw.eu5_lobby_gui import (
    CARD_OLD_WORLD,
    COUNTRY_SELECTED,
    GUI_FILES,
    LOCATION_SCRIPTED_GUI,
    patch_gui,
    scripted_gui_text,
)

CLICK = "\t" * 14


def _lobby_fixture() -> str:
    return (
        "\t\t\t\t\t\t\tfixedgridbox = {\n"
        '\t\t\t\t\t\t\t\tdatamodel = "[AccessLobbyCountryList.GetCountries]"\n'
        "\t\t\t\t\t\t\t\taddcolumn = 100%\n"
        "\t\t\t\t\t\t\t\taddrow = 74\n"
        "\t\t\t\t\t\t\t\tdatamodel_wrap = 1\n"
        "\t\t\t\t\t\t\t\tflipdirection = yes\n"
        "\t\t\t\t\t\t\t\tsetitemsizefromcell = yes\n\n"
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
        'enabled = "[GameLobby.CanStart]"\n'
        'enabled = "[GameLobby.CanJoin]"\n'
        'enabled = "[GameLobby.CanJoin]"\n'
        "button_regular = {\n"
        "\t\t\tusing = layoutpolicy_expanding\n\n"
        "\t\t\ttext_single = {\n"
        "\t\t\t\tparentanchor = center\n"
        "\t\t\t\tmaximumsize = {200 -1}\n"
        '\t\t\t\ttext = "MULTIPLAYER_LOBBY_CHOOSE_RANDOM_CHARACTER"\n'
        "\t\t\t}\n"
        "\t\t\taction_tooltip = {\n"
        '\t\t\t\ton_action = "[GameLobby.SetRandomPlayableObserverCharacter]"\n'
        'enabled = "[GameLobby.CanJoin]"\n'
        'enabled = "[GameLobby.CanJoin]"\n'
    )


def test_world_country_cards_are_dimmed_and_cannot_be_chosen_and_start_guards_reject_them() -> None:
    patched = patch_gui(GUI_FILES[0], _lobby_fixture())

    assert patched is not None
    assert f'alpha = "[TransparentIfFalse({CARD_OLD_WORLD})]"' in patched
    assert f'enabled = "[{CARD_OLD_WORLD}]"' in patched
    assert patched.count(COUNTRY_SELECTED) == 7
    assert patched.count('enabled = "[And(GameLobby.CanJoin,') == 4
    assert 'enabled = "[And(GameLobby.CanStart,' in patched
    assert 'enabled = "[And4(GameLobby.CanStart,' in patched
    assert 'visible = "[Not(IsLobbyOpen)]"' in patched
    assert "GameLobby.SetRandomPlayableObserverCharacter" in patched
    assert "SetRoot(LobbyView.GetSelectedPlayable.GetCountry.MakeScope)" not in patched
    assert (
        "GuiScope.AddScope('rnw_country', LobbyView.GetSelectedPlayable.GetCountry.MakeScope)"
        in patched
    )


def test_the_list_stays_the_games_own_fixed_grid_and_no_card_is_hidden() -> None:
    # Hidden cards made the flags flicker and the blank stretches return in a search, with the
    # list as a vbox of every card (experiment 037); the grid is the game's, untouched.
    source = _lobby_fixture()
    patched = patch_gui(GUI_FILES[0], source)

    assert patched is not None
    for kept in (
        "fixedgridbox = {",
        "addrow = 74",
        "datamodel_wrap = 1",
        "setitemsizefromcell = yes",
        "size = { 100% 90% }",
    ):
        assert kept in patched
    assert "vbox" not in patched
    assert "ignoreinvisible" not in patched
    card = patched[patched.index("item = {") : patched.index("type LobbySelectedCountryPanel")]
    assert "visible" not in card


def test_the_click_of_a_card_is_the_games_own_and_only_gated() -> None:
    patched = patch_gui(GUI_FILES[0], _lobby_fixture())

    assert patched is not None
    assert 'on_action = "[SetLobbyCountry(Country.Self)]"' in patched
    assert 'title = "LOBBYVIEW_SELECT_COUNTRY"' in patched
    gated = patched[patched.index("click_mode = single") : patched.index('block "click_action"')]
    assert gated.count("enabled") == 1


def test_country_list_layout_drift_is_refused() -> None:
    assert patch_gui(GUI_FILES[0], _lobby_fixture().replace("size = { 100% 90% }", "x")) is None
    assert (
        patch_gui(GUI_FILES[0], _lobby_fixture().replace("LOBBYVIEW_SELECT_COUNTRY", "OTHER"))
        is None
    )


@pytest.mark.parametrize("marker", ["market_marker", "raw_goods_marker"])
def test_world_cities_and_resource_markers_are_hidden_during_lobby_only(marker: str) -> None:
    source = (
        'name = "market_marker"\n\tmax_update_rate = 4\n'
        'name = "raw_goods_marker"\n\tallow_outside = yes\n'
    )

    patched = patch_gui(GUI_FILES[1], source)

    assert patched is not None
    assert "And(IsLobbyOpen, GetScriptedGui('rnw_new_world_location')" in patched
    assert patched.count(f'name = "{marker}"') == 1


def test_gui_overrides_fail_closed_when_any_source_anchor_is_missing_or_duplicated() -> None:
    source = _lobby_fixture()
    marker_source = 'name = "market_marker"\n\tmax_update_rate = 4\n'
    marker_source += 'name = "raw_goods_marker"\n\tallow_outside = yes\n'

    assert (
        patch_gui(
            GUI_FILES[0], source.replace("type LobbySelectedCountryPanel = widget {", "Missing")
        )
        is None
    )
    assert patch_gui(GUI_FILES[0], source + source) is None
    assert patch_gui(GUI_FILES[1], marker_source.replace('name = "market_marker"', "")) is None
    assert patch_gui(GUI_FILES[1], marker_source + marker_source) is None
    assert patch_gui("game/in_game/gui/unknown.gui", source) is None


def test_location_scripted_gui_resolves_the_location_scope_to_america() -> None:
    emitted = scripted_gui_text()

    assert LOCATION_SCRIPTED_GUI in emitted
    assert "scope = location" in emitted
    assert "continent = continent:america" in emitted
