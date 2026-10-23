"""The inventory of the New World's vanilla content consumers and their decisions (synthetic)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.content import FORMABLE_FAMILIES
from rnw.content_check import Checked, check_decisions, check_outcomes
from rnw.content_decisions import (
    CARRIERS,
    REASONS,
    RETIRED_STAGES,
    TABLE,
    Decision,
    Verdict,
    decide,
    missing,
    stale,
)
from rnw.content_inventory import (
    Consumer,
    category_of,
    lost_states,
    read_footprint,
    references,
    scan,
    summarize,
)

if TYPE_CHECKING:
    from pathlib import Path

# Where each carrier of a replaced object landed (content plan): the stage that wrote it.
STAGE_OF = {
    "exceptional_places": "N1",
    "river_centre": "N3",
    "sacred_centre": "N3",
    "harvest": "N4",
    "route_market": "N4",
    "great_alliance": "N4",
    "empire_periphery": "N4",
    "contact": "N4",
    "colony": "N4",
    "colonial_names": "N4",
    **dict.fromkeys(FORMABLE_FAMILIES, "N4"),
    "river_union": "N3",
}
KNOWN_CARRIERS = frozenset(STAGE_OF)

DEFINITIONS = """america = {
\tnorth_america = {
\t\tr_one = { a_one = { p_one = { loc_a loc_b circle } } }
\t}
}
europe = {
\twestern_europe = { r_eu = { a_eu = { p_eu = { loc_eu } } } }
}
"""
COUNTRIES = """countries = {
\tcountries = {
\t\tAAA = { own_control_core = { loc_a } }
\t\tBBB = { own_control_core = { loc_b } }
\t\tKEP = { own_control_core = { loc_eu } }
\t}
}
"""
DEFINED = "AAA = { color = red }\nBBB = { color = blue }\nKEP = { color = green }\n"
EVENTS = """namespace = flavor_xx

flavor_xx.1 = { # first: only the retired tags
\tdynamic_historical_event = { tag = AAA }
\toption = { name = flavor_xx.1.a set_variable = { name = chain_unlocked value = 1 } }
}
flavor_xx.2 = { # shared with a kept tag
\tdynamic_historical_event = { tag = AAA tag = KEP }
}
flavor_xx.3 = { # a dependent event: only the retired event fires it
\ttrigger_event = { id = flavor_xx.1 }
}
flavor_xx.4 = { # generic, names no American key
\ttrigger = { owns = location:loc_eu }
}
flavor_xx.5 = { # a comment names loc_a but the code does not
\t# loc_a
\ttrigger = { has_variable = unrelated }
}
flavor_xx.6 = {
\ttrigger = { owns = location:loc_a }
}
"""
PRIVILEGE = """reward = {
\tpotential = { has_variable = chain_unlocked }
}
unrelated_reward = {
\tpotential = { has_variable = other }
}
"""
KEYWORDS = """trigger_a = { circle = { size = 3 } }
trigger_b = { owns = location:circle }
trigger_c = { circle_of_life = yes }
"""


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def _install(root: Path) -> Path:
    game = root / "game"
    _write(game, "in_game/map_data/definitions.txt", DEFINITIONS)
    _write(game, "main_menu/setup/1337/10_countries.txt", COUNTRIES)
    _write(game, "in_game/setup/countries/00_countries.txt", DEFINED)
    _write(game, "in_game/events/DHE/flavor_xx.txt", EVENTS)
    _write(game, "in_game/common/estate_privileges/rewards.txt", PRIVILEGE)
    _write(game, "in_game/common/scripted_triggers/keywords.txt", KEYWORDS)
    return root


def test_the_footprint_is_the_american_keys_and_the_tags_that_go_with_them(tmp_path: Path) -> None:
    """A tag whose setup record names an American location is retired; others are not."""
    footprint = read_footprint(_install(tmp_path))
    assert footprint.tags == {"AAA", "BBB"}
    assert footprint.keys["location"] == {"loc_a", "loc_b", "circle"}
    assert footprint.keys["province"] == {"p_one"}
    assert footprint.keys["area"] == {"a_one"}
    assert footprint.keys["region"] == {"r_one"}
    assert footprint.keys["subcontinent"] == {"north_america"}


def test_consumers_are_the_objects_that_name_replaced_content(tmp_path: Path) -> None:
    """Shared and retired events, a key in code, and nothing for comments or Old World keys."""
    root = _install(tmp_path)
    footprint = read_footprint(root)
    found = scan(root, footprint, {"events": ["flavor_xx.1", "flavor_xx.3"]})
    assert found["events:flavor_xx.2"].refs == {"tag": ("AAA",)}
    assert found["events:flavor_xx.6"].refs == {"location": ("loc_a",)}
    assert "events:flavor_xx.4" not in found
    assert "events:flavor_xx.5" not in found
    assert found["events:flavor_xx.1"].retired
    assert found["events:flavor_xx.1"].refs["tag"] == ("AAA",)
    # An adapted dependent event names no key, yet it goes with its parent.
    assert found["events:flavor_xx.3"].retired
    assert found["events:flavor_xx.3"].refs == {}
    assert found["events:flavor_xx.3"].files == ("in_game/events/DHE/flavor_xx.txt",)


def test_a_reward_whose_path_was_retired_is_a_consumer_of_state(tmp_path: Path) -> None:
    """The privilege that reads a variable only a retired event sets is found, others are not."""
    root = _install(tmp_path)
    found = scan(root, read_footprint(root), {"events": ["flavor_xx.1"]})
    assert found["common/estate_privileges:reward"].refs == {"state": ("chain_unlocked",)}
    assert "common/estate_privileges:unrelated_reward" not in found


def test_state_set_elsewhere_is_not_lost() -> None:
    """A variable that a kept object also sets stays reachable."""
    objects = {
        "events:a": "x = { set_variable = { name = shared } }",
        "events:b": "x = { set_country_flag = shared }",
        "common/rewards:r": "x = { has_variable = shared has_country_flag = only_a }",
        "events:c": "x = { set_country_flag = only_a }",
    }
    assert lost_states(objects, ["events:a", "events:c"]) == {"common/rewards:r": {"only_a"}}


def test_a_word_that_is_also_a_script_key_counts_only_with_a_scope(tmp_path: Path) -> None:
    """``circle`` is a location and a script word; only ``location:circle`` is a reference."""
    root = _install(tmp_path)
    found = scan(root, read_footprint(root))
    assert "common/scripted_triggers:trigger_a" not in found
    assert found["common/scripted_triggers:trigger_b"].refs == {"location": ("circle",)}
    assert "common/scripted_triggers:trigger_c" not in found


def test_references_see_values_lists_and_scopes_but_not_keys_or_comments(tmp_path: Path) -> None:
    """Values, list items and prefixed words count; keys and comments do not."""
    footprint = read_footprint(_install(tmp_path))
    text = (
        "x = { location = loc_a # loc_b\n loc_b = yes\n list = { a_one r_one }\n"
        ' y = "p_one" z = area:a_one tag = AAA }'
    )
    found = references(text, footprint, frozenset())
    assert found == {
        "location": {"loc_a"},
        "area": {"a_one"},
        "region": {"r_one"},
        "province": {"p_one"},
        "tag": {"AAA"},
    }


def test_categories_follow_the_directory_of_the_file() -> None:
    """Events share one category; common and menu objects take their directory's name."""
    assert category_of("in_game/events/DHE/flavor_cas.txt") == "events"
    assert category_of("in_game/common/advances/x.txt") == "common/advances"
    assert category_of("main_menu/common/achievements/x.txt") == "menu/achievements"
    assert category_of("in_game/gfx/map/canal_gfx/c.txt") == "gfx/map"


def test_an_object_without_a_decision_stops_the_export(tmp_path: Path) -> None:
    """Unclassified consumers are listed; rows and rules decide the rest."""
    root = _install(tmp_path)
    footprint = read_footprint(root)
    found = scan(root, footprint, {"events": ["flavor_xx.1", "flavor_xx.3"]})
    table = {
        "events:flavor_xx.2": Verdict(Decision.KEEP, "generic"),
        "events:flavor_xx.6": Verdict(Decision.NEUTRALIZE, "identity"),
        "events:flavor_xx.old": Verdict(Decision.KEEP, "generic"),
    }
    assert missing(found.values(), footprint.tags, table) == [
        "common/estate_privileges:reward",
        "common/scripted_triggers:trigger_b",
    ]
    # The retired events are decided by the rule, not by a row.
    assert decide(found["events:flavor_xx.1"], footprint.tags, table) == Verdict(
        Decision.NEUTRALIZE, "retired"
    )
    assert "events:flavor_xx.old" in stale(found.values(), table)
    assert "events:flavor_xx.2" not in stale(found.values(), table)


def test_a_definition_owned_by_a_retired_tag_is_inert() -> None:
    """The coat of arms of a retired tag is kept: nothing consumes it."""
    owned = Consumer("menu/coat_of_arms", "AAA", (), {"tag": ("AAA",)})
    assert decide(owned, frozenset({"AAA"}), {}) == Verdict(Decision.KEEP, "inert")
    assert decide(owned, frozenset(), {}) is None


def test_the_summary_counts_consumers_and_the_keys_they_name() -> None:
    """Per category: how many consumers, and how many name each kind."""
    consumers = [
        Consumer("events", "a", (), {"tag": ("AAA",), "location": ("x",)}),
        Consumer("events", "b", (), {"location": ("y",)}),
    ]
    assert summarize(consumers) == {"events": {"consumers": 2, "tag": 1, "location": 2}}


def test_the_table_is_consistent() -> None:
    """Every row has a known reason, rebindings and replacements name a stage, none repeats."""
    for key, verdict in TABLE.items():
        assert verdict.reason in REASONS, key
        needs_stage = verdict.decision in {Decision.REBIND, Decision.REPLACE}
        assert bool(verdict.stage) == needs_stage, key
        assert verdict.stage in {"", "N1", "N3", "N4"}, key
    stages = {stage for rules in RETIRED_STAGES.values() for stage in rules.values()}
    assert stages <= {"N1", "N3", "N4"}


@pytest.mark.parametrize(
    "key",
    [
        "common/scripted_country_names:new_spain_scripted_country_name",
        "common/scripted_country_names:peru_scripted_country_name",
        "common/formable_countries:USA_f",
        "common/formable_countries:AZT_f",
    ],
)
def test_historical_identities_are_not_kept(key: str) -> None:
    """A literal American identity is never left as it is."""
    assert TABLE[key].decision is not Decision.KEEP


def test_the_export_check_stops_on_an_object_without_a_decision(tmp_path: Path) -> None:
    """A patch that adds a consumer fails the export until the table decides it."""
    root = _install(tmp_path)
    with pytest.raises(ValueError, match="have no decision"):
        _ = check_decisions(root, events=["flavor_xx.1"], modifiers=[], removed_tags=["AAA"])


def test_the_export_check_refuses_tags_outside_the_footprint(tmp_path: Path) -> None:
    """The retired tags of an export must be covered by the vanilla Americas' footprint."""
    root = _install(tmp_path)
    with pytest.raises(ValueError, match="outside the American footprint: KEP"):
        _ = check_decisions(root, events=[], modifiers=[], removed_tags=["AAA", "KEP"])


DECIDED = {
    "events:flavor_xx.2": Verdict(Decision.KEEP, "generic"),
    "events:flavor_xx.6": Verdict(Decision.NEUTRALIZE, "identity"),
    "common/estate_privileges:reward": Verdict(Decision.REPLACE, "lost", "N3"),
    "common/scripted_triggers:trigger_b": Verdict(Decision.KEEP, "positional"),
}
PRESENT = {
    "location": frozenset({"fresh", "loc_eu"}),
    "province": frozenset({"fresh_province"}),
    "area": frozenset({"fresh_area"}),
    "region": frozenset({"r_one"}),
    "subcontinent": frozenset({"north_america"}),
}
EVENTS_FILE = "in_game/events/DHE/flavor_xx.txt"


def _checked(root: Path) -> Checked:
    return check_decisions(
        root,
        events=["flavor_xx.1", "flavor_xx.3"],
        modifiers=[],
        removed_tags=["AAA", "BBB"],
        table=DECIDED,
    )


def _without(text: str, event: str) -> str:
    """``text`` without the event ``event`` (its block runs to the next unindented brace)."""
    start = text.index(f"{event} = {{")
    return text[:start] + text[text.index("\n}\n", start) + 3 :]


def _written(*, dropped: tuple[str, ...], rebind: bool = True) -> dict[str, bytes]:
    text = EVENTS
    for event in dropped:
        text = _without(text, event)
    if rebind:
        text = text.replace("location:loc_a", "location:fresh")
    triggers = KEYWORDS.replace("location:circle", "location:fresh") if rebind else KEYWORDS
    return {
        EVENTS_FILE: text.encode(),
        "in_game/common/scripted_triggers/keywords.txt": triggers.encode(),
    }


def test_the_outcomes_hold_when_only_retired_objects_vanish_and_no_key_is_left(
    tmp_path: Path,
) -> None:
    """The retired events go, the neutralized one is rebound: nothing is left to decide."""
    root = _install(tmp_path)
    checked = _checked(root)
    scripts = _written(dropped=("flavor_xx.1", "flavor_xx.3"))
    assert check_outcomes(root, scripts, checked, PRESENT)["rewritten"] == 2


def test_an_object_that_vanishes_without_a_decision_stops_the_export(tmp_path: Path) -> None:
    """A generic event cannot go: only what the exporter retires may leave a file."""
    root = _install(tmp_path)
    checked = _checked(root)
    scripts = _written(dropped=("flavor_xx.1", "flavor_xx.3", "flavor_xx.4"))
    with pytest.raises(ValueError, match=r"vanished that no decision retires: events:flavor_xx.4"):
        _ = check_outcomes(root, scripts, checked, PRESENT)


def test_a_key_the_world_lacks_stops_the_export_even_in_a_neutralized_object(
    tmp_path: Path,
) -> None:
    """The engine logs a missing key at load whether or not the gate is closed (C223)."""
    root = _install(tmp_path)
    checked = _checked(root)
    scripts = _written(dropped=("flavor_xx.1", "flavor_xx.3"), rebind=False)
    with pytest.raises(ValueError, match=r"events:flavor_xx.6 \(location loc_a\)"):
        _ = check_outcomes(root, scripts, checked, PRESENT)


def test_an_american_area_the_world_keeps_is_no_residue(tmp_path: Path) -> None:
    """A key that the generated world defines again (an area kept by position) may stay."""
    root = _install(tmp_path)
    checked = _checked(root)
    scripts = _written(dropped=("flavor_xx.1", "flavor_xx.3"))
    scripts[EVENTS_FILE] = scripts[EVENTS_FILE].replace(
        b"has_variable = unrelated", b"area = area:a_one"
    )
    with pytest.raises(ValueError, match=r"area a_one"):
        _ = check_outcomes(root, scripts, checked, PRESENT)
    kept = {**PRESENT, "area": frozenset({"a_one"})}
    assert check_outcomes(root, scripts, checked, kept)["rewritten"] == 2


def test_a_given_name_that_equals_a_location_key_is_no_residue(tmp_path: Path) -> None:
    """The table says ``name``: ``circle`` in a language file is not a place."""
    root = _install(tmp_path)
    table = {**DECIDED, "common/scripted_triggers:trigger_b": Verdict(Decision.KEEP, "name")}
    checked = check_decisions(
        root,
        events=["flavor_xx.1", "flavor_xx.3"],
        modifiers=[],
        removed_tags=["AAA", "BBB"],
        table=table,
    )
    scripts = _written(dropped=("flavor_xx.1", "flavor_xx.3"))
    scripts["in_game/common/scripted_triggers/keywords.txt"] = KEYWORDS.encode()
    assert check_outcomes(root, scripts, checked, PRESENT)["rewritten"] == 2


def test_every_replacement_names_what_carries_it() -> None:
    """A replaced object belongs to a chain with a carrier, or says why none carries it."""
    replaced = {key for key, verdict in TABLE.items() if verdict.decision is Decision.REPLACE}
    assert replaced <= CARRIERS.keys()
    for key, carrier in CARRIERS.items():
        assert carrier.note, key
        assert bool(carrier.families) != carrier.note.startswith("none:"), key
        assert set(carrier.families) <= KNOWN_CARRIERS, key
    # The rest are the objects the exporter retires, found by their chains' prefixes.
    for key in CARRIERS.keys() - replaced:
        category, _, ident = key.partition(":")
        assert any(ident.startswith(start) for start in RETIRED_STAGES.get(category, {})), key


def test_a_replacement_is_told_in_the_stage_that_carries_it() -> None:
    """The stage a replaced object names is the stage of one of its carriers, where it has any."""
    rules = {
        (category, start): stage
        for category, rules_ in RETIRED_STAGES.items()
        for start, stage in rules_.items()
    }
    for key, carrier in CARRIERS.items():
        if not carrier.families:
            continue
        category, _, ident = key.partition(":")
        verdict = TABLE.get(key)
        stage = (
            verdict.stage
            if verdict is not None
            else next(
                stage
                for (cat, start), stage in rules.items()
                if cat == category and ident.startswith(start)
            )
        )
        assert stage in {STAGE_OF[family] for family in carrier.families}, key
