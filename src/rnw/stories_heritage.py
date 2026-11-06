"""Vanilla American chains adapted to generated facts (history plan §22, N9; content plan).

Vanilla tells four American stories through tags that a generated world does not have: the decline
of Cahokia (``flavor_CHK``), the Grand Council of the Haudenosaunee (``flavor_IRO``), the balance
of the Aztec Triple Alliance (``flavor_AZT``) and the founding of the United States
(``flavor_usa``). Here each is a story of the generated world, bound to a recorded fact:

* **The Sunset of X** begins at the seat of a realm the history divided, for the state that holds
  it (``content.declining_centres``);
* **The Grand Council** for the largest state of a projected confederation, while it leads it
  (``content.councils``);
* **The Balance of the Alliance** for the strongest member of an alliance of three or more, with
  its strongest ally as the junior partner (``content.seniors``);
* **Assembly of the Delegates** when a nation of a colonial shore is founded: its formation starts
  the story (``founding``) instead of a start event.

Their modifiers copy the payloads of the vanilla chains' own modifiers (``chk_``, ``iro_``,
``usa_``) under the stories' names.
"""

from __future__ import annotations

from typing import Final

from rnw.content import CONFEDERATION_COUNCIL, DECLINING_CENTRE, NATION_FOUNDING, SENIOR_PARTNER
from rnw.stories_n4 import _mutual  # pyright: ignore[reportPrivateUsage]
from rnw.storymodel import (
    AFFORD,
    CLEANUP,
    CLEANUP_MONTHS,
    COUNTRY,
    LOCATION,
    STATIC,
    Follow,
    Modifier,
    Node,
    Option,
    Source,
    Story,
    country,
    gold,
    location,
    path_is,
    prose,
    set_to,
)

DECLINE_CENTRE: Final[str] = "rnw_decline_centre"
DECLINE_PATH: Final[str] = "rnw_decline_path"
COUNCIL_CENTRE: Final[str] = "rnw_council_centre"
COUNCIL_PATH: Final[str] = "rnw_council_path"
SENIOR_CENTRE: Final[str] = "rnw_senior_centre"
SENIOR_OTHER: Final[str] = "rnw_senior_other"
SENIOR_PATH: Final[str] = "rnw_senior_path"
NATION_CENTRE: Final[str] = "rnw_nation_centre"
NATION_PATH: Final[str] = "rnw_nation_path"
LEADS: Final[str] = (
    "is_leader_of_international_organization_of_type = { type = tribal_confederation }"
)


def _ends(*names: str) -> tuple[str, ...]:
    return tuple(f"remove_variable = {name}" for name in names)


def _members(effect: str) -> str:
    """An effect on every other member of the confederation the bearer leads."""
    return (
        "random_international_organization = { limit = { international_organization_type = "
        "international_organization_type:tribal_confederation leader_country = root } "
        f"every_international_organization_member = {{ limit = {{ NOT = {{ this = root }} }} "
        f"{effect} }} }}"
    )


def _government(kind: str) -> str:
    return (
        f"if = {{ limit = {{ NOT = {{ government_type = government_type:{kind} }} }} "
        f"change_government_type = government_type:{kind} }}"
    )


def decline() -> Story:
    """The seat of a fallen realm, half empty, and whether it rises again (``flavor_CHK``)."""
    centre, path = DECLINE_CENTRE, DECLINE_PATH
    end = _ends(centre, path)
    nodes = (
        Node(
            1,
            "The Sunset of [target_location.GetNameWithNoTooltip]",
            prose("""
                [target_location.GetNameWithNoTooltip] was once the seat of a realm that ruled every
                valley around it. The realm broke apart long ago. Its great courts stand half empty,
                the outer quarters return to forest, and the families who kept them drift away to
                younger towns.

                The elders of the city ask whether it will be great again, or only safe.
            """),
            (
                Option(
                    "a",
                    "Rebuild the old courts and call the families home.",
                    (gold(-3), location(centre, "rnw_decline_rebuilding", 20), set_to(path, 1)),
                    55,
                    Follow(2, (36, 72)),
                    AFFORD,
                ),
                Option(
                    "b",
                    "Wall in the heart of the city and let the rest go.",
                    (location(centre, "rnw_decline_fortified", 30), set_to(path, 2)),
                    45,
                    Follow(3, (24, 60)),
                ),
            ),
            requires=(f"NOT = {{ has_variable = {path} }}",),
        ),
        Node(
            2,
            "A New Golden Age",
            prose("""
                The courts of [target_location.GetNameWithNoTooltip] are full again. Craftsmen work
                on
                the old terraces, and pilgrims come to see what the ancestors built. Some at court
                say
                that the city should now lead the land as it once did.
            """),
            (
                Option(
                    "a",
                    "Let the city lead again.",
                    (gold(-2), country("rnw_decline_golden_age", 15), *end),
                    60,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Be content with the city restored.",
                    ("add_prestige = prestige_weak_bonus", *end),
                    40,
                ),
            ),
            requires=path_is(path, 1),
        ),
        Node(
            3,
            "The Shadow over [target_location.GetNameWithNoTooltip]",
            prose("""
                Behind its new walls [target_location.GetNameWithNoTooltip] is safe, and smaller
                every
                year. The empty quarters outside have become fields and thickets, and travellers
                speak
                of the city as a ruin with a garrison.
            """),
            (
                Option(
                    "a",
                    "The walls were worth it.",
                    (
                        "add_stability = stability_weak_bonus",
                        country("rnw_decline_shadow", 10),
                        *end,
                    ),
                    50,
                ),
                Option(
                    "b",
                    "Invite settlers into the empty quarters.",
                    (location(centre, "rnw_decline_resettled", 20), *end),
                    50,
                ),
            ),
            requires=path_is(path, 2),
        ),
    )
    modifiers = (
        Modifier(
            "rnw_decline_rebuilding",
            LOCATION,
            Source(STATIC, "chk_rebuilding_woodhenge"),
            "Rebuilding the Old Courts",
            "Masons and families return to the courts of the old seat.",
        ),
        Modifier(
            "rnw_decline_fortified",
            LOCATION,
            Source(STATIC, "chk_fortifying_center"),
            "The Walled Heart",
            "The heart of the old seat is walled and garrisoned.",
        ),
        Modifier(
            "rnw_decline_golden_age",
            COUNTRY,
            Source(STATIC, "chk_new_golden_age"),
            "The Old Seat Leads Again",
            "The restored city draws craftsmen, scholars and tribute from the whole land.",
        ),
        Modifier(
            "rnw_decline_shadow",
            COUNTRY,
            Source(STATIC, "chk_shadow_of_cahokia"),
            "A Ruin with a Garrison",
            "Travellers speak of the old seat as a shadow of what it was.",
        ),
        Modifier(
            "rnw_decline_resettled",
            LOCATION,
            Source(STATIC, "chk_outer_cahokia_growth"),
            "Settlers in the Empty Quarters",
            "New families fill the empty quarters of the old seat.",
        ),
    )
    return Story(DECLINING_CENTRE, "rnw_decline", centre, path, nodes, modifiers)


def council() -> Story:
    """The leader of a confederation before its Grand Council (``flavor_IRO``)."""
    centre, path = COUNCIL_CENTRE, COUNCIL_PATH
    end = _ends(centre, path)
    nodes = (
        Node(
            1,
            "The Grand Council",
            prose("""
                The chiefs of every people in our confederation have gathered at
                [target_location.GetNameWithNoTooltip] for the Grand Council. By the old law nothing
                is decided until all of them agree, and this year they have much to agree on.

                Our own chief may let the council speak with one slow voice, or speak first and
                loudest.
            """),
            (
                Option(
                    "a",
                    "Let the council decide together.",
                    (country("rnw_council_peace", 20), set_to(path, 1)),
                    60,
                    Follow(2, (24, 60)),
                ),
                Option(
                    "b",
                    "Our voice will lead the council.",
                    (
                        country("rnw_council_assertive", 15),
                        "add_prestige = prestige_weak_bonus",
                        _members("add_opinion = { target = root modifier = opinion_irritated }"),
                        set_to(path, 2),
                    ),
                    40,
                    Follow(3, (24, 60)),
                ),
            ),
            requires=(f"NOT = {{ has_variable = {path} }}",),
        ),
        Node(
            2,
            "A New Delegation",
            prose("""
                A people beyond our borders has sent a delegation to the council at
                [target_location.GetNameWithNoTooltip]. Its envoys ask to sit among the chiefs and
                to
                keep the law of the confederation as their own.
            """),
            (
                Option(
                    "a",
                    "Give them a seat by the fire.",
                    ("add_stability = stability_weak_bonus", *end),
                    60,
                ),
                Option(
                    "b",
                    "The council is full.",
                    ("add_prestige = prestige_weak_bonus", *end),
                    40,
                ),
            ),
            requires=path_is(path, 1),
        ),
        Node(
            3,
            "The Chiefs Are Angered",
            prose("""
                The chiefs whose words were cut short at the council have gone home from
                [target_location.GetNameWithNoTooltip] in anger. Some of them speak of leaving the
                confederation.
            """),
            (
                Option(
                    "a",
                    "Send gifts to every chief.",
                    (
                        gold(-2),
                        _members(
                            "add_opinion = { target = root modifier = opinion_good_relations }"
                        ),
                        *end,
                    ),
                    55,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Their anger will pass.",
                    ("add_stability = stability_mild_penalty", *end),
                    45,
                ),
            ),
            requires=path_is(path, 2),
        ),
    )
    modifiers = (
        Modifier(
            "rnw_council_peace",
            COUNTRY,
            Source(STATIC, "iro_memory_of_the_great_peacemaker"),
            "One Voice of the Council",
            "The chiefs decide together, slowly, and their peoples keep what they decide.",
        ),
        Modifier(
            "rnw_council_assertive",
            COUNTRY,
            Source(STATIC, "iro_disregarded_council_of_fifty_diplomacy"),
            "A Council Overruled",
            "Our chief speaks for the council, and the other chiefs resent it.",
        ),
    )
    return Story(
        CONFEDERATION_COUNCIL, "rnw_council", centre, path, nodes, modifiers, gate=(LEADS,)
    )


def senior() -> Story:
    """The strongest member of an alliance and its junior partner (``flavor_AZT``)."""
    centre, other, path = SENIOR_CENTRE, SENIOR_OTHER, SENIOR_PATH
    end = _ends(centre, other, path)
    nodes = (
        Node(
            1,
            "The Balance of the Alliance",
            prose("""
                For a generation our court and its allies have stood together, and no neighbour has
                dared to test them. Now our court is the strongest of them all, and our nobles ask
                why the spoils of every war should be shared alike with [target_country.GetName].
            """),
            (
                Option(
                    "a",
                    "We will take the first place among our allies.",
                    (
                        "add_prestige = prestige_weak_bonus",
                        _mutual("opinion_irritated"),
                        set_to(path, 1),
                    ),
                    50,
                    Follow(2, (24, 60)),
                ),
                Option(
                    "b",
                    "We stood together as equals, and so we remain.",
                    (_mutual("opinion_good_relations"), set_to(path, 2)),
                    50,
                    Follow(3, (36, 72)),
                ),
            ),
            requires=(f"NOT = {{ has_variable = {path} }}",),
        ),
        Node(
            2,
            "The Junior Partner Protests",
            prose("""
                Envoys of [target_country.GetName] remind our court that their warriors bled beside
                ours. They ask for an equal share of the tribute, or they will think again about the
                alliance.
            """),
            (
                Option(
                    "a",
                    "Give them their share of the tribute.",
                    (gold(-2), _mutual("opinion_good_relations"), *end),
                    50,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "They need us more than we need them.",
                    ("add_prestige = prestige_weak_bonus", _mutual("opinion_refused_claim"), *end),
                    50,
                ),
            ),
            requires=path_is(path, 1),
        ),
        Node(
            3,
            "Gifts among Equals",
            prose("""
                The court of [target_country.GetName] has sent gifts to honour the old alliance, and
                waits to see what ours will send in return.
            """),
            (
                Option(
                    "a",
                    "Send richer gifts in return.",
                    (gold(-1), "add_prestige = prestige_weak_bonus", *end),
                    55,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Our thanks will do.",
                    ("add_stability = stability_weak_bonus", *end),
                    45,
                ),
            ),
            requires=path_is(path, 2),
        ),
    )
    return Story(
        SENIOR_PARTNER,
        "rnw_senior",
        centre,
        path,
        nodes,
        other=other,
        immediate=(f"var:{other} ?= {{ owner ?= {{ save_scope_as = target_country }} }}",),
        gate=(f"var:{other} ?= {{ owner ?= {{ NOT = {{ this = root }} }} }}",),
    )


def nation() -> Story:
    """A nation of a colonial shore decides how it is governed (``flavor_usa``)."""
    centre, path = NATION_CENTRE, NATION_PATH
    end = _ends(centre, path)
    nodes = (
        Node(
            1,
            "Assembly of the Delegates",
            prose("""
                Delegates of every town of the new nation have gathered at
                [target_location.GetNameWithNoTooltip] to decide how it shall be governed. Some want
                a republic of free towns; others say that a young nation needs a crown to hold it
                together.
            """),
            (
                Option(
                    "a",
                    "A republic of free towns.",
                    (_government("republic"), set_to(path, 1)),
                    50,
                    Follow(2, (12, 36)),
                ),
                Option(
                    "b",
                    "A crown to hold the nation together.",
                    (_government("monarchy"), set_to(path, 2)),
                    50,
                    Follow(3, (12, 36)),
                ),
            ),
            requires=(f"NOT = {{ has_variable = {path} }}",),
        ),
        Node(
            2,
            "The Frontier Ordinance",
            prose("""
                The assembly at [target_location.GetNameWithNoTooltip] must decide what becomes of
                the
                land beyond the settled shore. Surveyors want it measured, sold and joined by roads;
                others say that it belongs to the peoples who live there.
            """),
            (
                Option(
                    "a",
                    "Survey the frontier and build roads into it.",
                    (country("rnw_nation_roads", 25), *end),
                    60,
                ),
                Option(
                    "b",
                    "Leave the frontier to its peoples.",
                    ("add_stability = stability_weak_bonus", *end),
                    40,
                ),
            ),
            requires=path_is(path, 1),
        ),
        Node(
            3,
            "A Crown for the Nation",
            prose("""
                The delegates have chosen a crown, and the new court at
                [target_location.GetNameWithNoTooltip] must decide whom it rewards: the founders of
                the
                towns, or the old families who came from across the sea.
            """),
            (
                Option(
                    "a",
                    "Reward the founders of the towns.",
                    ("add_legitimacy = legitimacy_weak_bonus", *end),
                    55,
                ),
                Option(
                    "b",
                    "Honour the old families.",
                    ("add_prestige = prestige_weak_bonus", *end),
                    45,
                ),
            ),
            requires=path_is(path, 2),
        ),
    )
    modifiers = (
        Modifier(
            "rnw_nation_roads",
            COUNTRY,
            Source(STATIC, "usa_postal_roads_expansion"),
            "Roads into the Frontier",
            "Surveyors and road builders push the nation's roads beyond the settled shore.",
        ),
    )
    return Story(NATION_FOUNDING, "rnw_nation", centre, path, nodes, modifiers)


def founding(story: Story) -> tuple[str, ...]:
    """The effects that start the founding story for the founder of a nation, at its capital."""
    return (
        "capital = { save_scope_as = home_place }",
        f"set_variable = {{ name = {story.centre} value = scope:home_place }}",
        f"trigger_event_non_silently = {{ id = {story.event(story.nodes[0].number)} }}",
        f"trigger_event_silently = {{ id = {story.event(CLEANUP)} months = {CLEANUP_MONTHS} }}",
    )
