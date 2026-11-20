"""The windows use the same independent continent controls as world codes and the CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rnw.app import controls
from rnw.gui.controller import Controller
from rnw.layers import land_key
from rnw.settings import MamlukPolicy, MoroccoPolicy, build_settings

if TYPE_CHECKING:
    from pathlib import Path


def test_continent_presets_and_overrides_travel_independently(tmp_path: Path) -> None:
    controller = Controller(data=tmp_path)
    assert controller.continent_selection() == {"america": True, "africa": False, "oceania": False}
    initial = controller.code
    controller.set_continent("africa", enabled=True)
    controller.set_continent("oceania", enabled=True)
    assert controller.region_settings("africa").preset == "supercontinent"
    assert controller.region_settings("oceania").preset == "archipelago"
    controller.set_region_preset("africa", "continents")
    controller.set_region_value("africa", "resources.coffee", 1500)
    controller.set_morocco("castile")
    assert controller.region_settings("africa").mamluks is MamlukPolicy.RESTORE
    controller.set_mamluks("damascus")
    controller.set_asia_connection(required=True)
    controller.set_region_value("oceania", "natives.state_share_permille", 24)
    controller.set_region_value("oceania", "resources.coffee", 1500)
    controller.set_continent("america", enabled=False)
    restored = Controller(data=tmp_path)
    assert restored.use_code(controller.code) is None
    africa, oceania = restored.world_code().settings().continents.regions
    assert africa.preset == "continents"
    assert africa.resources == (("coffee", 1500),)
    assert africa.morocco is MoroccoPolicy.CASTILE
    assert africa.mamluks is MamlukPolicy.DAMASCUS
    assert oceania.mamluks is None
    assert africa.require_asia_connection
    assert not oceania.require_asia_connection
    assert oceania.natives.state_share_permille == 24
    assert oceania.resources == ()
    assert not restored.continent_selection()["america"]
    assert "wall" not in controls.REGION_TYPES
    assert "omerika" not in controls.REGION_TYPES
    controller.set_continent("africa", enabled=False)
    controller.set_continent("oceania", enabled=False)
    assert controller.code == ""
    controller.set_continent("africa", enabled=True)
    assert controller.region_settings("africa") == africa
    controller.set_continent("africa", enabled=False)
    controller.set_continent("america", enabled=True)
    assert controller.code == initial


def test_land_versions_distinguish_regional_geography(tmp_path: Path) -> None:
    controller = Controller(data=tmp_path)
    legacy = land_key(controller.world_code().settings(), 17)
    controller.set_continent("africa", enabled=True)
    original = land_key(controller.world_code().settings(), 17)
    assert legacy != original
    controller.set_region_value("africa", "resources.coffee", 200)
    controller.set_morocco("granada")
    controller.set_mamluks("damascus")
    assert land_key(controller.world_code().settings(), 17) == original
    controller.set_asia_connection(required=True)
    assert land_key(controller.world_code().settings(), 17) != original
    controller.set_asia_connection(required=False)
    controller.set_region_value("africa", "new_world.land_permille", 500)
    assert land_key(controller.world_code().settings(), 17) != original
    assert (
        controls.estimated_locations(
            build_settings("continents", {"continents": {"africa": True, "oceania": True}})
        )
        < controls.LOCATION_BUDGET
    )


def test_circumnavigation_option_is_optional_and_roundtrips(tmp_path: Path) -> None:
    controller = Controller(data=tmp_path)
    assert controller.sea_circumnavigation() is None
    controller.set_continent("africa", enabled=True)
    assert controller.sea_circumnavigation() is True
    default = land_key(controller.world_code().settings(), 17)
    controller.set_sea_circumnavigation(enabled=False)
    restored = Controller(data=tmp_path)
    assert restored.use_code(controller.code) is None
    assert restored.sea_circumnavigation() is False
    assert land_key(restored.world_code().settings(), 17) != default
    restored.set_sea_circumnavigation(enabled=True)
    assert land_key(restored.world_code().settings(), 17) == default
