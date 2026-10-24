"""The pilot stories of the content plan (N3): the river centre and the sacred centre.

The framework is in ``storymodel``; the stories of N4 are in ``stories_n4`` (bearers in the
finished world) and ``stories_colonial`` (bearers found in play). ``STORIES`` lists all of them,
in the order the content plan offers them.
"""

from __future__ import annotations

from typing import Final

from rnw.stories_colonial import colony, contact
from rnw.stories_n4 import alliance, empire, harvest, route
from rnw.storymodel import (
    AFFORD,
    BUILDING,
    CLERGY,
    COUNTRY,
    LOCATION,
    PRIVILEGE,
    STATIC,
    Follow,
    Modifier,
    Node,
    Option,
    Privilege,
    Source,
    Story,
    country,
    gold,
    location,
    path_is,
    prose,
    set_to,
    unlocation,
)

RIVER_CENTRE_VARIABLE: Final[str] = "rnw_river_centre"
RIVER_PATH_VARIABLE: Final[str] = "rnw_river_path"
SACRED_CENTRE_VARIABLE: Final[str] = "rnw_sacred_centre"
SACRED_PATH_VARIABLE: Final[str] = "rnw_sacred_path"
SACRED_PRIVILEGE_VARIABLE: Final[str] = "rnw_sacred_privilege_open"


def _river() -> Story:
    centre, path = RIVER_CENTRE_VARIABLE, RIVER_PATH_VARIABLE
    end = (f"remove_variable = {centre}", f"remove_variable = {path}")
    first = prose("""
        For as long as anyone remembers, the great river has fed
        [target_location.GetNameWithNoTooltip]. Its floods laid down the black fields, its barges
        carried the grain and its landings made the city rich. Now the channel creeps a little
        farther every spring. Silt chokes the old canals, the floodwater climbs into the lower
        streets, and the granaries hold less than the stewards report.

        The elders of the city have come to court. Each of them has a remedy, and every remedy costs
        somebody else.
    """)
    held = prose("""
        The spring flood came as it always does, and this year it stopped at the new embankments. In
        the lower streets of [target_location.GetNameWithNoTooltip], where the water used to stand
        in the markets for a month, it never rose past the wharves. Now the wardens of the banks ask
        what we mean to do with the peace we have bought.
    """)
    due = prose("""
        The tolls filled the treasury and the banks were left alone. This spring the river rose,
        found the weakest stretch and broke through. When the water fell, the lower quarters of
        [target_location.GetNameWithNoTooltip] lay under mud, the wells were fouled and barges sat
        stranded in the streets. The collectors report that every toll was paid in full. Next year
        there will be nobody left to pay them.
    """)
    wardens = prose("""
        For some years now the river guilds have kept the banks. They do it more cheaply than the
        court ever did, and they do it for themselves: their own landings are the best built on the
        river, and their quarter of [target_location.GetNameWithNoTooltip] has grown rich. Now they
        want their charter written down and sealed.
    """)
    nodes = (
        Node(
            1,
            "The River Turns",
            first,
            (
                Option(
                    "a",
                    "Raise embankments and dig new canals.",
                    (
                        gold(-3),
                        country("rnw_river_works_levy", 6),
                        location(centre, "rnw_river_embankments", 15),
                        set_to(path, 1),
                    ),
                    50,
                    Follow(2, (36, 60)),
                    AFFORD,
                ),
                Option(
                    "b",
                    "Tax the barges, not the treasury. The banks have held this long.",
                    (country("rnw_river_toll_regime", 10), set_to(path, 2)),
                    30,
                    Follow(3, (30, 54)),
                ),
                Option(
                    "c",
                    "The river guilds know the banks best. Let them keep them.",
                    (
                        location(centre, "rnw_river_guild_wardens", 20),
                        country("rnw_river_ceded_authority", 10),
                        set_to(path, 3),
                    ),
                    20,
                    Follow(4, (36, 72)),
                ),
            ),
            requires=(f"NOT = {{ has_variable = {path} }}",),
        ),
        Node(
            2,
            "The Banks Hold",
            held,
            (
                Option(
                    "a",
                    "Build granaries on the new banks.",
                    (gold(-2), location(centre, "rnw_river_flood_security", 20), *end),
                    60,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Keep the surplus in the treasury.",
                    (gold(3), "add_stability = stability_weak_bonus", *end),
                    40,
                ),
            ),
            requires=path_is(path, 1),
        ),
        Node(
            3,
            "The River Takes Its Due",
            due,
            (
                Option(
                    "a",
                    "Clear the channels at once, whatever it costs.",
                    (
                        gold(-3),
                        unlocation(centre, "rnw_river_silted"),
                        "add_stability = stability_weak_bonus",
                        *end,
                    ),
                    55,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Move the grain stores uphill and let the lower town drain.",
                    ("add_stability = stability_mild_penalty", *end),
                    45,
                ),
            ),
            requires=path_is(path, 2),
            immediate=(location(centre, "rnw_river_silted", 15),),
        ),
        Node(
            4,
            "The River Wardens",
            wardens,
            (
                Option(
                    "a",
                    "Seal the charter.",
                    ("add_legitimacy = legitimacy_weak_bonus", *end),
                    55,
                ),
                Option(
                    "b",
                    "The banks are ours, and so are their revenues.",
                    (
                        unlocation(centre, "rnw_river_guild_wardens"),
                        "add_stability = stability_mild_penalty",
                        gold(2),
                        *end,
                    ),
                    45,
                ),
            ),
            requires=path_is(path, 3),
        ),
    )
    modifiers = (
        Modifier(
            "rnw_river_works_levy",
            COUNTRY,
            Source(STATIC, "chk_funding_woodhenge_restoration"),
            "River Works Levy",
            "The treasury pays for embankments and canals.",
        ),
        Modifier(
            "rnw_river_embankments",
            LOCATION,
            Source(STATIC, "chk_protection_against_flooding"),
            "New Embankments",
            "High banks keep the floods out of the streets, at the cost of some fields.",
        ),
        Modifier(
            "rnw_river_flood_security",
            LOCATION,
            Source(STATIC, "chk_outer_cahokia_protected_flooding"),
            "Safe from the Floods",
            "With granaries on the banks and years without a flood, the city grows.",
        ),
        Modifier(
            "rnw_river_toll_regime",
            COUNTRY,
            Source(STATIC, "chk_restricted_construction"),
            "River Tolls",
            "Tolls on the river trade fill the treasury, and little gets built.",
        ),
        Modifier(
            "rnw_river_silted",
            LOCATION,
            Source(STATIC, "chk_river_water_polluted"),
            "Silt and Fouled Wells",
            "The flood left mud in the streets and filth in the wells.",
        ),
        Modifier(
            "rnw_river_guild_wardens",
            LOCATION,
            Source(STATIC, "chk_outer_cahokia_growth"),
            "Guild Wardens of the Banks",
            "The river guilds keep the banks, and their quarter thrives.",
        ),
        Modifier(
            "rnw_river_ceded_authority",
            COUNTRY,
            Source(STATIC, "chk_exodus_of_cahokia"),
            "Ceded Authority",
            "The guilds hold the river now, and the court is seen to answer to them.",
        ),
    )
    return Story("river_centre", "rnw_river", centre, path, nodes, modifiers)


def _sacred() -> Story:
    centre, path = SACRED_CENTRE_VARIABLE, SACRED_PATH_VARIABLE
    end = (f"remove_variable = {centre}", f"remove_variable = {path}")
    gate = prose("""
        Every season brings more pilgrims to [target_location.GetNameWithNoTooltip]. They sleep in
        the lanes, leave offerings at the old stones and carry the name of the place home to
        villages the court has never heard of. The priests of the shrine complain that it has
        outgrown its walls; the stewards, that it has outgrown the treasury.
    """)
    prospers = prose("""
        The endowment has done what the stewards said it never would. The road is paved, the hostels
        are full, and the pilgrims who come to [target_location.GetNameWithNoTooltip] now stay on to
        trade. The priests would crown the work with a great temple, and they ask us to lay its
        first stone.
    """)
    murmur = prose("""
        The tithe has filled the treasury, and the priests of [target_location.GetNameWithNoTooltip]
        have noticed. The offerings, they say, belong to those who gave them and to those who tend
        the stones. A few have begun to say so in their sermons, and the pilgrims are listening.
    """)
    seat = prose("""
        The high priest of [target_location.GetNameWithNoTooltip] now sits among the estates, and
        the old order of the shrine has a voice in our councils. The priests are grateful. The
        other estates are counting what that voice will cost them.
    """)
    nodes = (
        Node(
            1,
            "Pilgrims at the Gate",
            gate,
            (
                Option(
                    "a",
                    "Endow the shrine and pave the pilgrims' road.",
                    (gold(-3), location(centre, "rnw_sacred_endowment", 20), set_to(path, 1)),
                    50,
                    Follow(2, (30, 60)),
                    AFFORD,
                ),
                Option(
                    "b",
                    "Offerings are wealth. Let the treasury take its tithe.",
                    (gold(3), "add_stability = stability_weak_penalty", set_to(path, 2)),
                    30,
                    Follow(3, (24, 48)),
                ),
                Option(
                    "c",
                    "Give the high priest a seat among the estates.",
                    (
                        "add_legitimacy = legitimacy_weak_bonus",
                        set_to(SACRED_PRIVILEGE_VARIABLE, 1),
                        set_to(path, 3),
                    ),
                    20,
                    Follow(4, (24, 60)),
                ),
            ),
            requires=(f"NOT = {{ has_variable = {path} }}",),
        ),
        Node(
            2,
            "The Shrine Prospers",
            prospers,
            (
                Option(
                    "a",
                    "Raise the great temple.",
                    (gold(-4), location(centre, "rnw_sacred_great_temple", 40), *end),
                    55,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "The road was enough. Let the offerings keep it.",
                    (gold(2), "add_stability = stability_weak_bonus", *end),
                    45,
                ),
            ),
            requires=path_is(path, 1),
        ),
        Node(
            3,
            "The Priests Murmur",
            murmur,
            (
                Option(
                    "a",
                    "Return part of the tithe to the shrine.",
                    (gold(-2), "add_stability = stability_mild_bonus", *end),
                    55,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Keep the tithe and answer the sermons.",
                    (
                        "add_legitimacy = legitimacy_weak_bonus",
                        "add_prestige = prestige_weak_penalty",
                        *end,
                    ),
                    45,
                ),
            ),
            requires=path_is(path, 2),
        ),
        Node(
            4,
            "A Priesthood With a Seat",
            seat,
            (
                Option(
                    "a",
                    "Welcome the priesthood to our councils.",
                    ("add_stability = stability_weak_bonus", *end),
                    55,
                ),
                Option(
                    "b",
                    "Their place is at the shrine. Keep them to it.",
                    (
                        location(centre, "rnw_sacred_endowment", 20),
                        f"remove_variable = {SACRED_PRIVILEGE_VARIABLE}",
                        *end,
                    ),
                    45,
                ),
            ),
            requires=path_is(path, 3),
        ),
    )
    modifiers = (
        Modifier(
            "rnw_sacred_endowment",
            LOCATION,
            Source(BUILDING, "great_temple_of_tenochtitlan", "modifier"),
            "Endowed Shrine",
            "A rich shrine and a paved road draw the pilgrims, and the priests grow in standing.",
        ),
        Modifier(
            "rnw_sacred_great_temple",
            LOCATION,
            Source(BUILDING, "great_temple_of_tenochtitlan", "modifier"),
            "The Great Temple",
            "A temple raised over the old stones draws the faithful of the whole country.",
        ),
    )
    privileges = (
        Privilege(
            "rnw_sacred_priesthood",
            CLERGY,
            SACRED_PRIVILEGE_VARIABLE,
            Source(PRIVILEGE, "hurin_qusqu_privilege", "country_modifier"),
            "High Priesthood of the Shrine",
            "The high priest of the shrine answers to the faith alone and sits among the estates.",
        ),
    )
    return Story("sacred_centre", "rnw_sacred", centre, path, nodes, modifiers, privileges)


STORIES: Final[tuple[Story, ...]] = (
    _river(),
    _sacred(),
    harvest(),
    route(),
    alliance(),
    empire(),
    contact(),
    colony(),
)
