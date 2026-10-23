"""Script rewrites for removed content: events, location lists, DLC files (synthetic)."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

import pytest

from rnw.eu5_events import mentions, names_tag, retire_events, retire_modifiers
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
        "dlc/D1_pack/in_game/common/holy_sites/d1.txt",
        "city = { location = gone }\n",
    )
    _write(
        game,
        "in_game/gfx/map/map_objects/dynamic_game_objects.txt",
        "o = { map_id = { volcano } }\n",
    )
    rewrite = remap_scripts(tmp_path, REMAP, {"AAA"})
    assert sorted(rewrite.outputs) == [
        "in_game/common/holy_sites/a.txt",
        "in_game/common/holy_sites/d1.txt",
        "in_game/events/DHE/flavor.txt",
        "in_game/gfx/map/map_objects/dynamic_game_objects.txt",
    ]
    assert rewrite.outputs["in_game/common/holy_sites/d1.txt"] == (b"city = { location = fresh }\n")
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


CHAIN = """flavor_ch.1 = {
\tdynamic_historical_event = { tag = AAA }
\toption = { trigger_event = { id = flavor_ch.2 } }
}
flavor_ch.2 = {
\toption = { trigger_event = { id = flavor_ch.3 } }
}
flavor_ch.3 = {
\ttitle = flavor_ch.3.title
}
flavor_ch.4 = {
\toption = { trigger_event = { id = flavor_ch.5 } }
}
flavor_ch.5 = { }
"""


def test_follow_ups_that_only_dropped_events_fired_go_with_them() -> None:
    """The chain of a dropped event is dropped; an event another file fires stays."""
    result = retire_events(CHAIN, {"AAA"}, Counter())
    assert result.events == ("flavor_ch.1", "flavor_ch.2", "flavor_ch.3")
    assert result.text.startswith("flavor_ch.4 = {")
    assert "flavor_ch.5 = { }" in result.text
    fired = retire_events(CHAIN, {"AAA"}, Counter({"flavor_ch.2": 1}))
    assert fired.events == ("flavor_ch.1",)
    assert "flavor_ch.3 = {" in fired.text
    assert retire_events(CHAIN, {"AAA"}).events == ("flavor_ch.1",)


def test_event_mentions_count_ids_not_numbers() -> None:
    """Ids with a namespace count; localization keys of an event count for the event."""
    text = "id = a.1 x = 1.5 a.12 = { title = a.1.title }"
    assert mentions(text) == Counter({"a.1": 2, "a.12": 1})


def test_modifiers_only_dropped_events_applied_leave_their_file() -> None:
    """A modifier goes when the dropped events name it and nothing else does."""
    texts = {
        "main_menu/common/static_modifiers/country.txt": (
            "used_mod = {\n\ta = 1\n}\ngone_mod = {\n\ta = 2\n}\nother = {\n}\n"
        ),
        "in_game/common/x.txt": "e = { add_country_modifier = { modifier = used_mod } }\n",
    }
    removed = "add_country_modifier = { modifier = gone_mod }\nmodifier = used_mod\n"
    changed, dropped = retire_modifiers(texts, removed)
    assert dropped == ("gone_mod",)
    assert changed == {
        "main_menu/common/static_modifiers/country.txt": (
            "used_mod = {\n\ta = 1\n}\nother = {\n}\n"
        )
    }
    assert retire_modifiers(texts, "") == ({}, ())


def test_remap_scripts_retires_event_modifiers(tmp_path: Path) -> None:
    """The events file and the static modifier file of a dropped event are both rewritten."""
    game = tmp_path / "game"
    _write(
        game,
        "in_game/events/flavor.txt",
        "ev.1 = {\n\tdynamic_historical_event = { tag = AAA }\n\tmodifier = m_only\n}\n",
    )
    _write(game, "main_menu/common/static_modifiers/c.txt", "m_only = {\n\tx = 1\n}\nkeep = {\n}\n")
    rewrite = remap_scripts(tmp_path, {}, {"AAA"})
    assert rewrite.modifiers == ("m_only",)
    assert rewrite.outputs["main_menu/common/static_modifiers/c.txt"] == b"keep = {\n}\n"


IMAGES = """d1_monuments = {
\ttag = "monuments1"

\tillustration_image = { #Alpha 0
\t\ttexture_file = "gfx/empty.dds"
\t\tpriority = 1
\t\tscope = location
\t}

\t#the pyramid
\tillustration_image = {
\t\ttexture_file = "gfx/pyramid.dds"
\t\tscope = location
\t\ttrigger = {
\t\t\thas_newsletter_subscription = yes
\t\t\tthis = location:gone
\t\t}
\t}

\tillustration_image = {
\t\ttexture_file = "gfx/buddha.dds"
\t\tscope = location
\t\ttrigger = {
\t\t\tthis = location:kept
\t\t}
\t}
}
"""


def test_the_illustration_of_a_removed_place_is_dropped_and_the_others_stay(tmp_path: Path) -> None:
    """A picture bound to a place that is gone would make the engine log the comparison every
    frame (``Invalid right side during comparison 'location'``, EU5 1.4.4, experiment 036); it
    is not moved to another place either, since the picture shows that place."""
    game = tmp_path / "game"
    _write(game, "dlc/D1_pack/in_game/gfx/images/d1_images_location.txt", IMAGES)
    _write(game, "in_game/gfx/images/00_images_location.txt", IMAGES.replace("gone", "kept"))
    rewrite = remap_scripts(tmp_path, REMAP, set())
    assert sorted(rewrite.outputs) == ["in_game/gfx/images/d1_images_location.txt"]
    text = rewrite.outputs["in_game/gfx/images/d1_images_location.txt"].decode()
    assert "pyramid" not in text
    assert "location:gone" not in text
    assert "location:fresh" not in text  # dropped, not rebound
    assert "gfx/empty.dds" in text
    assert "this = location:kept" in text
    assert text.count("illustration_image") == 2
    assert 'tag = "monuments1"' in text
    assert rewrite.illustrations == {"in_game/gfx/images/d1_images_location.txt": 1}


def test_an_illustration_naming_a_removed_province_is_dropped_too(tmp_path: Path) -> None:
    game = tmp_path / "game"
    text = IMAGES.replace("location:gone", "province_definition:lost_province")
    _write(game, "in_game/gfx/images/d1.txt", text)
    rewrite = remap_scripts(tmp_path, REMAP, set())
    assert "lost_province" not in rewrite.outputs["in_game/gfx/images/d1.txt"].decode()


def test_a_province_definition_scope_is_remapped_like_a_location_scope() -> None:
    """An exploration event asks ``province_definition = province_definition:KEY``; a key that is
    gone makes the engine log ``Invalid province_definition key`` at load (EU5 1.4.4, sitting
    038), whether or not the event can fire."""
    text = (
        "event = {\n\ttrigger = {\n\t\tlocation = {\n\t\t\tOR = {\n"
        "\t\t\t\tprovince_definition = province_definition:lost_province\n"
        "\t\t\t\tprovince_definition = province_definition:kept_province\n"
        "\t\t\t}\n\t\t}\n\t}\n}\n"
    )
    new, count = remap_text(text, REMAP)
    assert count == 1
    assert "province_definition:fresh_province" in new
    assert "province_definition:kept_province" in new
    assert "lost_province" not in new


MONUMENTS = """mesh_list = { name = "d1_gone_mesh" }
mesh_list = { name = "d1_kept_mesh" }

template unique_buildings
{
\tcode =
\t[[
\t\t# the pyramid
\t\td1_gone = {
\t\t\tonly_in_location = gone
\t\t\tmesh_list = d1_gone_mesh
\t\t\tlink_tooltip = { type = holy_site data = gone_holy_site }
\t\t}
\t\td1_kept = {
\t\t\tonly_in_location = kept
\t\t\tmesh_list = d1_kept_mesh
\t\t}
\t]]
}
"""


def test_the_model_of_a_removed_place_is_dropped_and_the_others_stay(tmp_path: Path) -> None:
    """A unique building bound to a place that is gone is dropped, not moved to the nearest
    generated place: a model of a pyramid shows that pyramid, as a picture does."""
    game = tmp_path / "game"
    _write(game, "dlc/D1_pack/in_game/gfx/map/city_data/D1_monuments.txt", MONUMENTS)
    _write(game, "in_game/gfx/map/city_data/00_kept.txt", MONUMENTS.replace("gone", "kept2"))
    rewrite = remap_scripts(tmp_path, REMAP, set())
    assert sorted(rewrite.outputs) == ["in_game/gfx/map/city_data/D1_monuments.txt"]
    text = rewrite.outputs["in_game/gfx/map/city_data/D1_monuments.txt"].decode()
    assert "d1_gone = {" not in text
    assert "# the pyramid" not in text
    assert "fresh" not in text  # dropped, not rebound
    assert "only_in_location = kept" in text
    assert text.count("mesh_list") == 3  # the two definitions stay; only the building goes
    assert rewrite.monuments == {"in_game/gfx/map/city_data/D1_monuments.txt": 1}


def test_city_data_that_names_a_removed_place_elsewhere_stops_the_export(tmp_path: Path) -> None:
    """Only the models bound to a place are dropped; any other name of a removed place is an
    unknown that must be decided, as with the pictures."""
    game = tmp_path / "game"
    _write(game, "in_game/gfx/map/city_data/00_x.txt", "other = {\n\tlocation = gone\n}\n")
    with pytest.raises(RemapError, match="outside the pictures and models"):
        _ = remap_scripts(tmp_path, REMAP, set())
