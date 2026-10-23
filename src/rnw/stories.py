"""The pilot stories of the content plan (N3): the river centre and the sacred centre.

The framework is in ``storymodel``; the stories of N4 are in ``stories_n4``. ``STORIES`` lists all
of them, in the order the content plan offers them.
"""

from __future__ import annotations

from typing import Final

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
        For generations the great river has fed [target_location.GetNameWithNoTooltip]. Its
        floods laid down the black fields, its barges carried the grain and its landing stages
        made the city rich. Now the channel shifts a little each spring. Silt chokes the old
        canals, the floods reach farther into the lower streets, and the granaries hold less
        than the stewards report.

        The elders of the city have come to the court. They agree that something must be done,
        and agree on nothing else.
    """)
    held = prose("""
        The spring flood came as it always had, and this year it stopped at the new
        embankments. In the lower streets of [target_location.GetNameWithNoTooltip] the water
        that once stood in the markets for a month never rose past the wharves. The wardens of
        the banks ask what the city should do with the peace it has bought.
    """)
    due = prose("""
        The tolls have filled the treasury and the banks have been left alone. This spring the
        river rose, found the weakest stretch and went through it. When the water fell the
        lower quarters of [target_location.GetNameWithNoTooltip] lay under mud, the wells were
        fouled and barges stood stranded in the streets. The collectors report that the tolls
        were paid in full, and that nobody is left to pay them next year.
    """)
    wardens = prose("""
        The guilds of the river quarter have kept the banks for years now. They have done it
        more cheaply than the court could, and they have done it for themselves: their landings
        are better built than the rest and their quarter of
        [target_location.GetNameWithNoTooltip] is richer for it. They ask that their charter be
        written down.
    """)
    nodes = (
        Node(
            1,
            "The River Turns",
            first,
            (
                Option(
                    "a",
                    "Raise embankments and cut new canals.",
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
                    "Squeeze the river trade and leave the banks as they are.",
                    (country("rnw_river_toll_regime", 10), set_to(path, 2)),
                    30,
                    Follow(3, (30, 54)),
                ),
                Option(
                    "c",
                    "Let the guilds of the river quarter keep the banks themselves.",
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
                    "Move the grain stores to higher ground and let the lower town drain.",
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
                    "Confirm the charter.",
                    ("add_legitimacy = legitimacy_weak_bonus", *end),
                    55,
                ),
                Option(
                    "b",
                    "Take back the banks and the revenues with them.",
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
            "Raised banks keep the floods out of the streets and take some of the fields.",
        ),
        Modifier(
            "rnw_river_flood_security",
            LOCATION,
            Source(STATIC, "chk_outer_cahokia_protected_flooding"),
            "Safe from the Floods",
            "Granaries on the banks and years without floods let the city grow.",
        ),
        Modifier(
            "rnw_river_toll_regime",
            COUNTRY,
            Source(STATIC, "chk_restricted_construction"),
            "River Tolls",
            "Tolls on the river trade fill the treasury while the court builds little.",
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
            "The river quarter keeps its own banks and its quarter grows.",
        ),
        Modifier(
            "rnw_river_ceded_authority",
            COUNTRY,
            Source(STATIC, "chk_exodus_of_cahokia"),
            "Ceded Authority",
            "The care of the river is in the guilds' hands, and their payments cost standing.",
        ),
    )
    return Story("river_centre", "rnw_river", centre, path, nodes, modifiers)


def _sacred() -> Story:
    centre, path = SACRED_CENTRE_VARIABLE, SACRED_PATH_VARIABLE
    end = (f"remove_variable = {centre}", f"remove_variable = {path}")
    gate = prose("""
        Every season more pilgrims come to [target_location.GetNameWithNoTooltip]. They sleep in
        the lanes, they leave offerings at the old stones and they carry the name of the place
        back to villages the court has never heard of. The priests of the shrine say the place
        has outgrown its walls. The stewards say it has outgrown the treasury.
    """)
    prospers = prose("""
        The endowment has done what the stewards doubted. The road is paved, the hostels are
        full and the pilgrims who come to [target_location.GetNameWithNoTooltip] now stay to
        trade. The priests propose to crown the work with a great temple, and ask the court to
        begin it.
    """)
    murmur = prose("""
        The tithe has filled the treasury, and the priests of
        [target_location.GetNameWithNoTooltip] have noticed. They say the offerings belong to
        those who made them and to those who tend the stones. Some of them say it from the
        pulpit, and the pilgrims listen.
    """)
    seat = prose("""
        The high priest of [target_location.GetNameWithNoTooltip] now sits among the estates,
        and the old order of the shrine has a voice in the councils of the
        [ROOT.GetCountry.GetFlavorRank]. The priests are grateful. The others ask what the price
        of a seat will be.
    """)
    nodes = (
        Node(
            1,
            "Pilgrims at the Gate",
            gate,
            (
                Option(
                    "a",
                    "Endow the shrine and the road that leads to it.",
                    (gold(-3), location(centre, "rnw_sacred_endowment", 20), set_to(path, 1)),
                    50,
                    Follow(2, (30, 60)),
                    AFFORD,
                ),
                Option(
                    "b",
                    "Tithe the offerings for the treasury.",
                    (gold(3), "add_stability = stability_weak_penalty", set_to(path, 2)),
                    30,
                    Follow(3, (24, 48)),
                ),
                Option(
                    "c",
                    "Give the high priest of the shrine a seat of his own among the estates.",
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
                    "Let the offerings pay for the road and nothing more.",
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
                    "Return a part of the tithe to the shrine.",
                    (gold(-2), "add_stability = stability_mild_bonus", *end),
                    55,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Hold the tithe and answer the pulpits.",
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
                    "Welcome the priesthood into the councils.",
                    ("add_stability = stability_weak_bonus", *end),
                    55,
                ),
                Option(
                    "b",
                    "Confine its power to the shrine and its lands.",
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
            "An endowed shrine and a paved road draw pilgrims, and the priests grow in standing.",
        ),
        Modifier(
            "rnw_sacred_great_temple",
            LOCATION,
            Source(BUILDING, "great_temple_of_tenochtitlan", "modifier"),
            "The Great Temple",
            "A temple raised over the old stones holds the faith of the whole country.",
        ),
    )
    privileges = (
        Privilege(
            "rnw_sacred_priesthood",
            CLERGY,
            SACRED_PRIVILEGE_VARIABLE,
            Source(PRIVILEGE, "hurin_qusqu_privilege", "country_modifier"),
            "High Priesthood of the Shrine",
            "The high priest of the shrine serves the faith directly and sits among the estates.",
        ),
    )
    return Story("sacred_centre", "rnw_sacred", centre, path, nodes, modifiers, privileges)


STORIES: Final[tuple[Story, ...]] = (_river(), _sacred(), harvest(), route(), alliance(), empire())
