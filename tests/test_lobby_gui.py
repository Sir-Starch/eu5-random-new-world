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
