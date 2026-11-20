"""Independent continent choices survive canonical settings and world-code round trips."""

from __future__ import annotations

from itertools import combinations

import pytest

from rnw.app.worldcode import decode, encode, new_code
from rnw.settings import MoroccoPolicy, SettingsError, build_settings

CONTINENTS = ("america", "africa", "oceania")
SELECTIONS = [names for i in range(1, 4) for names in combinations(CONTINENTS, i)]


@pytest.mark.parametrize("enabled", SELECTIONS)
def test_each_selection_round_trips(enabled: tuple[str, ...]) -> None:
    changes: dict[str, object] = {"continents": {key: key in enabled for key in CONTINENTS}}
    settings = build_settings("continents", changes)
    assert settings.continents.america == ("america" in enabled)
    assert tuple(r.key for r in settings.continents.regions) == tuple(
        name for name in enabled if name != "america"
    )
    assert build_settings("continents", settings.to_json_data()) == settings
    assert decode(encode(new_code("continents", 17, changes))).settings() == settings


def test_independent_preset_and_resource_settings_keep_their_own_defaults() -> None:
    changes: dict[str, object] = {
        "continents": {
            "africa": {"morocco": "granada", "resources": {"coffee": 0}},
            "oceania": {
                "preset": "supercontinent",
                "new_world": {"land_permille": 300},
                "natives": {"population_permille": 444},
            },
        },
    }
    settings = build_settings("wall", changes)
    africa, oceania = settings.continents.regions
    assert africa.preset == "supercontinent"
    assert africa.morocco is MoroccoPolicy.GRANADA
    assert africa.resources == (("coffee", 0),)
    assert africa.new_world.ocean_band_px == 820
    assert africa.natives.state_share_permille == 443
    assert oceania.new_world.ocean_band_px == 560
    assert oceania.new_world.land_permille == 300
    assert oceania.natives.population_permille == 444
    assert oceania.natives.state_share_permille == 24
    assert settings.new_world.landform == 1
    assert "continents" not in build_settings("wall").to_json_data()


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"america": False}, "Choose at least one continent"),
        ({"america": 1}, "switch must be true or false"),
        ({"antarctica": True}, "Unknown continents"),
        ({"africa": {"preset": "wall"}}, "Invalid africa preset"),
        ({"africa": {"morocco": "spain"}}, "Unknown Morocco option"),
        ({"oceania": {"morocco": "granada"}}, "Unknown oceania settings"),
        ({"africa": {"mamluks": "syria"}}, "Unknown Mamluk option"),
        ({"oceania": {"mamluks": "damascus"}}, "Unknown oceania settings"),
        ({"africa": {"resources": {"coffee": True}}}, "Resource weight for coffee"),
    ],
)
def test_invalid_continent_choices_fail_at_resolution(
    options: dict[str, object], message: str
) -> None:
    with pytest.raises(SettingsError, match=message):
        _ = build_settings("continents", {"continents": options})
