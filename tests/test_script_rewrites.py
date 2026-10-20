"""Script rewrites for removed content: events, location lists, DLC files (synthetic)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.eu5_events import names_tag, retire_events
from rnw.eu5_nw_export import DONOR_MODIFIER, retired_base_modifiers
from rnw.eu5_remap import RemapError, remap_scripts, remap_text

if TYPE_CHECKING:
    from pathlib import Path

EVENTS = """namespace = flavor_xx

# Gone with its country
flavor_xx.1 = { # first
\ttype = country_event
\tdynamic_historical_event = {
\t\ttag = AAA
\t\tfrom = 1337.1.1
\t}
\toption = { name = flavor_xx.1.a }
}

flavor_xx.2 = {
\tdynamic_historical_event = {
\t\ttag = AAA
\t\ttag = BBB
\t\ttag = KEEP
\t}
}

flavor_xx.3 = {
\tdynamic_historical_event = { tag = BBB }
\tdynamic_historical_event = { tag = AAA }
}

flavor_xx.4 = {
\ttype = country_event
\ttrigger = { tag = AAA }
}

flavor_xx.5 = {
\tdynamic_historical_event = { tag = KEEP }
}
"""


def test_events_of_removed_tags_go_and_shared_events_lose_the_tags() -> None:
    """Only dynamic historical events change; a trigger naming a tag is not one."""
    result = retire_events(EVENTS, {"AAA", "BBB"})
    assert result.events == ("flavor_xx.1", "flavor_xx.3")
    assert result.tags == 2
    assert "flavor_xx.2 = {" in result.text
    assert "tag = KEEP" in result.text
    assert "tag = AAA\n\t\ttag = BBB" not in result.text
    assert "flavor_xx.4 = {\n\ttype = country_event\n\ttrigger = { tag = AAA }\n}" in result.text
    assert "flavor_xx.5 = {\n\tdynamic_historical_event = { tag = KEEP }\n}" in result.text
    assert "# Gone with its country\n\nflavor_xx.2" in result.text  # comments stay
    assert result.text.startswith("namespace = flavor_xx\n")


def test_events_without_removed_tags_stay_byte_for_byte() -> None:
    """Nothing is edited when no event names a removed tag."""
    result = retire_events(EVENTS, {"ZZZ"})
    assert result.text == EVENTS
    assert result.events == ()
    assert result.tags == 0
    assert names_tag(EVENTS, {"AAA"})
    assert not names_tag(EVENTS, {"ZZZ"})


FLAVOR = """ev.1 = {
\tdynamic_historical_event = { tag = AAA }
}
ev.2 = {
\tdynamic_historical_event = { tag = KEEP }
\ttrigger = { owns = location:gone }
}
"""
REMAP = {"gone": "fresh", "also_gone": "fresh", "lost_province": "fresh_province", "volcano": "x"}


def test_location_lists_remap_without_repeats() -> None:
    """Removed entries of province and location lists point at generated ones once."""
    text = (
        "geo = {\n\tprovince_definition = {\n\t\tlost_province kept_province\n\t}\n"
        "\tlocations = { gone kept also_gone fresh }\n}\n"
        "formable = { provinces = { lost_province lost_province } }\n"
    )
    new, count = remap_text(text, REMAP)
    assert count == 5
    assert "province_definition = {\n\t\tfresh_province kept_province\n\t}" in new
    words = new.split("locations = {")[1].split("}")[0].split()
    assert words == ["kept", "fresh"]
    assert new.split("provinces = {")[1].split("}")[0].split() == ["fresh_province"]


def test_removed_map_ids_are_dropped_not_remapped() -> None:
    """A map object needs its own locator, so a removed ``map_id`` entry just goes."""
    text = "dynamic_game_object = {\n\tmap_id = { kept volcano other }\n}\n"
    new, count = remap_text(text, REMAP)
    assert count == 1
    assert new.split("map_id = {")[1].split("}")[0].split() == ["kept", "other"]


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def test_scripts_of_the_game_and_its_dlc_are_rewritten(tmp_path: Path) -> None:
    """DLC files are rewritten at their own virtual path, events retired before remapping."""
    game = tmp_path / "game"
    _write(game, "in_game/common/holy_sites/a.txt", "a = { location = gone }\n")
    _write(game, "in_game/common/holy_sites/untouched.txt", "b = { location = kept }\n")
    _write(
        game,
        "in_game/events/DHE/flavor.txt",
        FLAVOR,
    )
    _write(
        game,
        "dlc/D1_pack/in_game/gfx/map/city_data/d1.txt",
        "city = { only_in_location = gone }\n",
    )
    _write(
        game,
        "in_game/gfx/map/map_objects/dynamic_game_objects.txt",
        "o = { map_id = { volcano } }\n",
    )
    rewrite = remap_scripts(tmp_path, REMAP, {"AAA"})
    assert sorted(rewrite.outputs) == [
        "in_game/common/holy_sites/a.txt",
        "in_game/events/DHE/flavor.txt",
        "in_game/gfx/map/city_data/d1.txt",
        "in_game/gfx/map/map_objects/dynamic_game_objects.txt",
    ]
    assert rewrite.outputs["in_game/gfx/map/city_data/d1.txt"] == (
        b"city = { only_in_location = fresh }\n"
    )
    events = rewrite.outputs["in_game/events/DHE/flavor.txt"].decode()
    assert "ev.1" not in events
    assert "owns = location:fresh" in events
    assert rewrite.retired == {"in_game/events/DHE/flavor.txt": ("ev.1",)}
    assert rewrite.remapped["in_game/events/DHE/flavor.txt"] == 1


def test_a_dlc_file_may_not_shadow_a_base_game_file(tmp_path: Path) -> None:
    """Which of two files at one path the engine loads is unknown, so the export refuses."""
    game = tmp_path / "game"
    _write(game, "in_game/common/holy_sites/a.txt", "a = { location = gone }\n")
    _write(game, "dlc/D1_pack/in_game/common/holy_sites/a.txt", "a = { location = gone }\n")
    with pytest.raises(RemapError, match="exists in the base game and in D1_pack"):
        _ = remap_scripts(tmp_path, REMAP, set())


def test_base_values_used_only_by_removed_locations_are_retired() -> None:
    """A modifier a kept template also names stays; templates are the only users."""
    bodies = {
        "gone_a": "{ modifier = only_removed topography = hills }",
        "gone_b": "{ modifier = shared }",
        "kept": "{ modifier = shared vegetation = forest }",
        "plain": "{ topography = hills }",
    }
    assert retired_base_modifiers(bodies, {"gone_a", "gone_b"}) == {"only_removed"}
    assert retired_base_modifiers(bodies, set()) == set()


def test_a_donors_base_value_is_not_copied_to_generated_locations() -> None:
    """Potosi's silver stays with Potosi; other template fields are untouched."""
    body = "{ modifier = potosi_base topography = flatland vegetation = forest }"
    assert DONOR_MODIFIER.sub("", body) == "{ topography = flatland vegetation = forest }"
    plain = "{ topography = flatland movement_assistance = { -90.16 4.98 } }"
    assert DONOR_MODIFIER.sub("", plain) == plain
