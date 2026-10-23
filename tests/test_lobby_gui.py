from __future__ import annotations

import pytest

from rnw.eu5_lobby_gui import (
    COUNTRY_SELECTED,
    GUI_FILES,
    LOCATION_SCRIPTED_GUI,
    patch_gui,
    scripted_gui_text,
)


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


def test_country_list_hides_world_country_cards_and_start_guards_reject_them() -> None:
    source = _lobby_fixture()

    patched = patch_gui(GUI_FILES[0], source)

    assert patched is not None
    assert "visible = \"[Not(GetScriptedGui('rnw_new_world_country')" in patched
    assert patched.count(COUNTRY_SELECTED) == 7
    assert patched.count('enabled = "[And(GameLobby.CanJoin,') == 4
    assert 'enabled = "[And(GameLobby.CanStart,' in patched
    assert 'enabled = "[And4(GameLobby.CanStart,' in patched
    assert 'visible = "[Not(IsLobbyOpen)]"' in patched
    assert "GameLobby.SetRandomPlayableObserverCharacter" in patched


def test_hidden_country_cards_do_not_reserve_fixed_rows() -> None:
    source = _lobby_fixture()

    patched = patch_gui(GUI_FILES[0], source)

    assert patched is not None
    assert 'datamodel = "[AccessLobbyCountryList.GetCountries]"' in patched
    assert "ignoreinvisible = yes" in patched
    assert "fixedgridbox" not in patched
    assert "addrow = 74" not in patched
    assert "setitemsizefromcell" not in patched
    assert "spacing = 7" in patched


def test_cards_of_the_vbox_take_their_width_from_a_layout_policy_not_a_percentage() -> None:
    # The engine refuses a percentage size on a child of a vbox ("Unsupported property: size with
    # a percentage", multiplayer_lobby.gui:4792, EU5 1.4.4, experiment 036); vanilla's idiom for a
    # datamodel vbox is an expanding layout policy and a width of -1.
    patched = patch_gui(GUI_FILES[0], _lobby_fixture())

    assert patched is not None
    head = patched[patched.index("item = {") : patched.index('visible = "[Not(GetScriptedGui')]
    assert "layoutpolicy_horizontal = expanding" in head
    assert "size = { -1 67 }" in head
    assert "%" not in head


def test_country_list_layout_drift_is_refused() -> None:
    source = _lobby_fixture().replace("addrow = 74", "addrow = 80")

    assert patch_gui(GUI_FILES[0], source) is None


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
