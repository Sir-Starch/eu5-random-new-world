"""The stories of the content plan that wait for the ocean to be crossed (N4): contact and colony.

Their bearers are not in the world when it is made: a native country meets strangers, a colony
asks what it is, and neither happens until the game has made a colony or sent a ship. So these
two are *pulse* stories (``storymodel.Pulse``): every year the game offers each country a small
chance of their hidden start, which begins the story only for a country that meets its conditions
then. The conditions keep them to the New World (a capital on the continent of America) and to
the right kind of country; the Old World never meets them.

Everything else is as in the other stories: static English prose, no tag and no location in a
script, payloads copied from vanilla modifiers at generation time, a graph that can be checked.
"""

from __future__ import annotations

from typing import Final

from rnw.storymodel import (
    AFFORD,
    COUNTRY,
    LOCATION,
    STATIC,
    Follow,
    Modifier,
    Node,
    Option,
    Pulse,
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

CONTACT_HOME_VARIABLE: Final[str] = "rnw_contact_home"
CONTACT_SEAT_VARIABLE: Final[str] = "rnw_contact_seat"
CONTACT_PATH_VARIABLE: Final[str] = "rnw_contact_path"
COLONY_HOME_VARIABLE: Final[str] = "rnw_colony_home"
COLONY_SEAT_VARIABLE: Final[str] = "rnw_colony_seat"
COLONY_PATH_VARIABLE: Final[str] = "rnw_colony_path"
# Something of the New World: a capital on the continent of America.
IN_AMERICA: Final[str] = "capital.continent = continent:america"


def _mutual(opinion: str) -> str:
    """Both countries think better or worse of each other (the game's own mutual effect)."""
    return f"add_opinion_mutual_effect = {{ target = scope:target_country modifier = {opinion} }}"


def _without(name: str) -> str:
    return f"remove_country_modifier = {name}"


def _setup(home: str, seat: str, *, outsider: str) -> tuple[str, ...]:
    """Store the country's capital and the other power's, the one the story is about.

    ``outsider`` is the effect, in the country's scope, that saves the other power's capital as
    ``seat_place``; the capitals travel through the story in variables (a country's scope does
    not outlast the event that saved it).
    """
    return (
        "capital = { save_scope_as = home_place }",
        outsider,
        f"set_variable = {{ name = {home} value = scope:home_place }}",
        f"set_variable = {{ name = {seat} value = scope:seat_place }}",
    )


def contact() -> Story:
    """Ships from beyond the ocean reach a native country with a port."""
    centre, other, path = CONTACT_HOME_VARIABLE, CONTACT_SEAT_VARIABLE, CONTACT_PATH_VARIABLE
    end = tuple(f"remove_variable = {name}" for name in (centre, other, path))
    first = prose("""
        Ships of [target_country.GetName] have anchored off the coast near
        [target_location.GetNameWithNoTooltip]. Their sailors say they have crossed the ocean, and
        that their rulers want trade, and perhaps more than trade. Nobody on the coast has ever seen
        their like. The elders have met three times and settled nothing.
    """)
    merchants = prose("""
        The strangers have returned with more ships and more goods. Their merchants want a house on
        the quay of [target_location.GetNameWithNoTooltip], the right to buy inland and a hearing at
        court. Our own traders want exactly the opposite.
    """)
    watch = prose("""
        The strangers keep to the one port they were given, and the watchmen of
        [target_location.GetNameWithNoTooltip] count their ships every week. Inland, people whisper
        that the strangers bring sickness and strange gods. The elders ask whether one open port is
        prudence or plain fear.
    """)
    ready = prose("""
        For a whole season the levies have stood on the shore at
        [target_location.GetNameWithNoTooltip], and the strangers have not landed. Their ships come
        and go beyond the reef, and the men are wanted back in the fields.
    """)
    nodes = (
        Node(
            1,
            "Strangers on the Shore",
            first,
            (
                Option(
                    "a",
                    "Receive their envoys and trade with them.",
                    (
                        country("rnw_contact_envoys", 10),
                        _mutual("succesful_embassy"),
                        set_to(path, 1),
                    ),
                    40,
                    Follow(2, (30, 54)),
                ),
                Option(
                    "b",
                    "Let them into one port only, and watch it.",
                    (
                        location(centre, "rnw_contact_one_port", 15),
                        "add_stability = stability_weak_bonus",
                        set_to(path, 2),
                    ),
                    35,
                    Follow(3, (30, 54)),
                ),
                Option(
                    "c",
                    "Raise the coast against them!",
                    (
                        country("rnw_contact_coast_levies", 8),
                        location(centre, "rnw_contact_coast_watch", 8),
                        _mutual("opinion_insulted"),
                        set_to(path, 3),
                    ),
                    25,
                    Follow(4, (36, 72)),
                ),
            ),
            requires=(f"NOT = {{ has_variable = {path} }}",),
        ),
        Node(
            2,
            "The Strangers' Merchants",
            merchants,
            (
                Option(
                    "a",
                    "Give them their house on the quay.",
                    (location(centre, "rnw_contact_trading_house", 15), *end),
                    55,
                ),
                Option(
                    "b",
                    "Keep them on the coast and off the inland roads.",
                    (gold(2), "add_stability = stability_weak_bonus", *end),
                    45,
                ),
            ),
            requires=path_is(path, 1),
        ),
        Node(
            3,
            "Watch at the Single Port",
            watch,
            (
                Option(
                    "a",
                    "Keep the watch and the single port.",
                    ("add_stability = stability_weak_bonus", *end),
                    55,
                ),
                Option(
                    "b",
                    "Open a second port and ease the quarrels.",
                    (
                        gold(-2),
                        unlocation(centre, "rnw_contact_one_port"),
                        _mutual("succesful_embassy"),
                        *end,
                    ),
                    45,
                    trigger=AFFORD,
                ),
            ),
            requires=path_is(path, 2),
        ),
        Node(
            4,
            "The Coast Stands Ready",
            ready,
            (
                Option(
                    "a",
                    "Stand the levies down and send an envoy.",
                    (
                        gold(-2),
                        unlocation(centre, "rnw_contact_coast_watch"),
                        _without("rnw_contact_coast_levies"),
                        _mutual("succesful_embassy"),
                        *end,
                    ),
                    50,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Keep the watch through the year.",
                    (
                        "add_prestige = prestige_weak_bonus",
                        "add_stability = stability_mild_penalty",
                        *end,
                    ),
                    50,
                ),
            ),
            requires=path_is(path, 3),
        ),
    )
    modifiers = (
        Modifier(
            "rnw_contact_envoys",
            COUNTRY,
            Source(STATIC, "iro_welcoming_to_outsiders"),
            "Welcome to Outsiders",
            "Envoys from beyond the ocean bring new knowledge, and our voice carries farther.",
        ),
        Modifier(
            "rnw_contact_one_port",
            LOCATION,
            Source(STATIC, "entry_port_modifier"),
            "The One Open Port",
            "Every foreign ship must put in at one port, and its quays and warehouses grow.",
        ),
        Modifier(
            "rnw_contact_coast_levies",
            COUNTRY,
            Source(STATIC, "enhanced_colonial_militia"),
            "Levies of the Coast",
            "The coast has taken up arms, and more men can be called.",
        ),
        Modifier(
            "rnw_contact_coast_watch",
            LOCATION,
            Source(STATIC, "hun_city_league_obligation"),
            "The Coast Watch",
            "Lookouts and beacons along the shore make any landing costly.",
        ),
        Modifier(
            "rnw_contact_trading_house",
            LOCATION,
            Source(STATIC, "surveyed_smugglers_cove"),
            "A House on the Quay",
            "The strangers' merchants keep a house and a warehouse on the quay.",
        ),
    )
    return Story(
        "contact",
        "rnw_contact",
        centre,
        path,
        nodes,
        modifiers,
        other=other,
        immediate=(f"var:{other} ?= {{ owner ?= {{ save_scope_as = target_country }} }}",),
        gate=(f"var:{other} ?= {{ owner ?= {{ NOT = {{ this = root }} }} }}",),
        pulse=Pulse(
            trigger=(
                "NOT = { is_subject_type = colonial_nation }",
                IN_AMERICA,
                "culture ?= { is_culture_native_american = yes }",
                "num_of_ports > 0",
                "any_known_country = { capital_in_old_world_trigger = yes }",
            ),
            chance=4,
            setup=_setup(
                centre,
                other,
                outsider=(
                    "random_known_country = { limit = { capital_in_old_world_trigger = yes } "
                    "capital = { save_scope_as = seat_place } }"
                ),
            ),
            quiet_years=60,
        ),
    )


def colony() -> Story:
    """A colonial nation asks what it is: a subject, a people or a country."""
    centre, other, path = COLONY_HOME_VARIABLE, COLONY_SEAT_VARIABLE, COLONY_PATH_VARIABLE
    end = tuple(f"remove_variable = {name}" for name in (centre, other, path))
    first = prose("""
        For the first time, the settlers of [target_location.GetNameWithNoTooltip] have met in
        assembly without the governor's leave. They pay taxes to [target_country.GetName], fight
        their own neighbours and farm a land that is not the one their fathers left. They want to
        know what they are: subjects, a people or a country.
    """)
    council = prose("""
        The council of [target_country.GetName] has heard the petition. Seats may be granted, its
        members reply, in time, and to those who pay the most. The richest colonists think the price
        fair and are already counting their coin. The poorer settlers have stopped coming to the
        assembly.
    """)
    people = prose("""
        A generation has been born in [target_location.GetNameWithNoTooltip] that has never seen the
        old country. It speaks a tongue of its own, half the old language and half the words of the
        coast, and it sings of the river rather than the sea. The old country's officers complain
        that it is hard to command a people that will not answer to its name.
    """)
    road = prose("""
        For a whole season the assembly of [target_location.GetNameWithNoTooltip] has refused to pay
        its dues. [target_country.GetName] has answered with a stern letter and a few ships. The
        militia captains say they are ready. The older members of the assembly say that independence
        is a word that costs more than it buys.
    """)
    nodes = (
        Node(
            1,
            "A Colonial Assembly",
            first,
            (
                Option(
                    "a",
                    "Petition the old country for seats in its council.",
                    (
                        country("rnw_colony_seats", 15),
                        _mutual("succesful_embassy"),
                        set_to(path, 1),
                    ),
                    40,
                    Follow(2, (36, 60)),
                ),
                Option(
                    "b",
                    "We are neither the old country nor the natives. We are a people of our own.",
                    (country("rnw_colony_people", 15), set_to(path, 2)),
                    35,
                    Follow(3, (36, 60)),
                ),
                Option(
                    "c",
                    "Demand self-government.",
                    (
                        country("rnw_colony_agitation", 10),
                        _mutual("outrageous_demands"),
                        set_to(path, 3),
                    ),
                    25,
                    Follow(4, (30, 54)),
                ),
            ),
            requires=(f"NOT = {{ has_variable = {path} }}",),
        ),
        Node(
            2,
            "The Council Answers",
            council,
            (
                Option(
                    "a",
                    "Pay the price of a seat.",
                    (gold(-2), country("rnw_colony_ties", 15), *end),
                    55,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "A seat bought with coin is no seat at all.",
                    ("add_legitimacy = legitimacy_weak_bonus", *end),
                    45,
                ),
            ),
            requires=path_is(path, 1),
        ),
        Node(
            3,
            "A People of Two Worlds",
            people,
            (
                Option(
                    "a",
                    "Let the courts hear cases in the colonial tongue.",
                    (
                        "add_legitimacy = legitimacy_weak_bonus",
                        "add_stability = stability_weak_bonus",
                        *end,
                    ),
                    55,
                ),
                Option(
                    "b",
                    "Hold to the old country's tongue and law.",
                    (
                        _mutual("opinion_sent_help"),
                        "add_stability = stability_weak_penalty",
                        *end,
                    ),
                    45,
                ),
            ),
            requires=path_is(path, 2),
        ),
        Node(
            4,
            "The Road to Independence",
            road,
            (
                Option(
                    "a",
                    "Call out the militia and prepare for war.",
                    (country("rnw_colony_militia", 5), *end),
                    45,
                ),
                Option(
                    "b",
                    "Negotiate autonomy in return for the dues.",
                    (
                        gold(-2),
                        _without("rnw_colony_agitation"),
                        country("rnw_colony_autonomy", 15),
                        _mutual("succesful_embassy"),
                        *end,
                    ),
                    55,
                    trigger=AFFORD,
                ),
            ),
            requires=path_is(path, 3),
        ),
    )
    modifiers = (
        Modifier(
            "rnw_colony_seats",
            COUNTRY,
            Source(STATIC, "receiving_support_loyalists"),
            "Seats at the Table",
            "A voice in the old country's council binds the colony to it.",
        ),
        Modifier(
            "rnw_colony_people",
            COUNTRY,
            Source(STATIC, "culture_influence_power"),
            "A Colonial People",
            "A people with its own tongue and songs earns its neighbours' respect.",
        ),
        Modifier(
            "rnw_colony_agitation",
            COUNTRY,
            Source(STATIC, "receiving_agitate_for_liberty"),
            "Agitation for Liberty",
            "Speeches in the assembly loosen the colony's loyalty to the old country.",
        ),
        Modifier(
            "rnw_colony_ties",
            COUNTRY,
            Source(STATIC, "receiving_strengthen_family_ties"),
            "Ties of Kinship",
            "Council seats bought with coin bind the great families to the old country.",
        ),
        Modifier(
            "rnw_colony_militia",
            COUNTRY,
            Source(STATIC, "nap_struggle_for_independence"),
            "The Militia Stands",
            "Every man who can bear arms is on the rolls, and they drill well.",
        ),
        Modifier(
            "rnw_colony_autonomy",
            COUNTRY,
            Source(STATIC, "receiving_appanage_grant_admin_autonomy"),
            "Autonomy Granted",
            "The colony governs itself and pays less, and it is loyal for it.",
        ),
    )
    return Story(
        "colony",
        "rnw_colony",
        centre,
        path,
        nodes,
        modifiers,
        other=other,
        immediate=(f"var:{other} ?= {{ owner ?= {{ save_scope_as = target_country }} }}",),
        gate=(f"var:{other} ?= {{ owner ?= {{ NOT = {{ this = root }} }} }}",),
        pulse=Pulse(
            trigger=("is_subject_type = colonial_nation", IN_AMERICA),
            chance=6,
            setup=_setup(
                centre,
                other,
                outsider="overlord ?= { capital = { save_scope_as = seat_place } }",
            ),
            quiet_years=40,
        ),
    )
