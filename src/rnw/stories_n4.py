"""The stories of the content plan's expansion (N4): harvest, route, alliance and empire.

Like the pilots in ``stories`` they are static data: original English prose, scripts that name no
tag and no location, and the payload of every modifier copied from a vanilla one at generation
time. Each is about a place a state holds (the harvest's centre, a route's two ends, the capital
and a neighbour's, the capital and the most distant subject's), and each goes forward through
delayed events the state's choices select, as the pilots do.
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

HARVEST_CENTRE_VARIABLE: Final[str] = "rnw_harvest_centre"
HARVEST_PATH_VARIABLE: Final[str] = "rnw_harvest_path"
ROUTE_FROM_VARIABLE: Final[str] = "rnw_route_from"
ROUTE_TO_VARIABLE: Final[str] = "rnw_route_to"
ROUTE_PATH_VARIABLE: Final[str] = "rnw_route_path"
ALLIANCE_HOME_VARIABLE: Final[str] = "rnw_alliance_home"
ALLIANCE_SEAT_VARIABLE: Final[str] = "rnw_alliance_seat"
ALLIANCE_PATH_VARIABLE: Final[str] = "rnw_alliance_path"
EMPIRE_HOME_VARIABLE: Final[str] = "rnw_empire_home"
EMPIRE_FAR_VARIABLE: Final[str] = "rnw_empire_far"
EMPIRE_PATH_VARIABLE: Final[str] = "rnw_empire_path"


def _food(centre: str, amount: str) -> str:
    """The food of the province of the centre changes by a fraction of what it holds."""
    return f"var:{centre} ?= {{ province = {{ change_province_food_percentage = {amount} }} }}"


def _partner(seat: str, effect: str) -> str:
    """An effect on the country that holds the place in the variable ``seat``."""
    return f"var:{seat} ?= {{ owner ?= {{ {effect} }} }}"


def _partner_modifier(seat: str, name: str, years: int) -> str:
    modifier = f"add_country_modifier = {{ modifier = {name} years = {years} mode = add }}"
    return _partner(seat, modifier)


def _mutual(opinion: str) -> str:
    """Both countries think better or worse of each other (the game's own mutual effect)."""
    return f"add_opinion_mutual_effect = {{ target = scope:target_country modifier = {opinion} }}"


def _without(name: str) -> str:
    return f"remove_country_modifier = {name}"


def harvest() -> Story:
    """A thin harvest in a city the land cannot easily feed."""
    centre, path = HARVEST_CENTRE_VARIABLE, HARVEST_PATH_VARIABLE
    end = (f"remove_variable = {centre}", f"remove_variable = {path}")
    first = prose("""
        The rains came late and the grain came in thin. In [target_location.GetNameWithNoTooltip]
        the granaries stand half empty, the price of bread has doubled in a month and the city
        eats more than the fields around it have ever grown. The reeves have come to the court
        with their tallies. They agree that the winter will be hard, and agree on little else.
    """)
    merchants = prose("""
        The grain that fed [target_location.GetNameWithNoTooltip] last winter came by the hands
        of a few merchant houses, and they have not forgotten who needed it. They keep the stores
        of the lower town, they set the price in the market and they now ask the court to write
        down what they have been doing for a year.
    """)
    villages = prose("""
        The villages that gave up their seed grain last winter have not forgotten it. At the
        spring markets of [target_location.GetNameWithNoTooltip] the farmers sell less and ask
        more, and the carters talk of fields left fallow. The stewards say the levy was needed.
        The farmers say it was a theft.
    """)
    fields = prose("""
        Two harvests on, the drained fields beyond [target_location.GetNameWithNoTooltip] bear
        grain where there was reed. Families from the crowded lanes have asked for the new land,
        and the stewards have asked for the tithe of it.
    """)
    nodes = (
        Node(
            1,
            "A Thin Harvest",
            first,
            (
                Option(
                    "a",
                    "Buy grain from the lands beyond the hills.",
                    (
                        gold(-3),
                        _food(centre, "0.15"),
                        location(centre, "rnw_harvest_bought_grain", 8),
                        set_to(path, 1),
                    ),
                    45,
                    Follow(2, (30, 54)),
                    AFFORD,
                ),
                Option(
                    "b",
                    "Ration the stores and requisition from the villages.",
                    (
                        _food(centre, "0.1"),
                        location(centre, "rnw_harvest_rationing", 6),
                        "add_stability = stability_weak_penalty",
                        set_to(path, 2),
                    ),
                    35,
                    Follow(3, (30, 54)),
                ),
                Option(
                    "c",
                    "Open new fields and drain the wet margins of the plain.",
                    (
                        gold(-2),
                        location(centre, "rnw_harvest_new_fields", 20),
                        set_to(path, 3),
                    ),
                    20,
                    Follow(4, (48, 84)),
                    AFFORD,
                ),
            ),
            requires=(f"NOT = {{ has_variable = {path} }}",),
            immediate=(_food(centre, "-0.2"),),
        ),
        Node(
            2,
            "The Grain Merchants",
            merchants,
            (
                Option(
                    "a",
                    "Grant the grain merchants their charter.",
                    (country("rnw_harvest_grain_charter", 10), *end),
                    55,
                ),
                Option(
                    "b",
                    "Break their hold and build public granaries.",
                    (gold(-2), location(centre, "rnw_harvest_public_granaries", 20), *end),
                    45,
                    trigger=AFFORD,
                ),
            ),
            requires=path_is(path, 1),
        ),
        Node(
            3,
            "The Villages Remember",
            villages,
            (
                Option(
                    "a",
                    "Repay the villages in coin and seed.",
                    (
                        gold(-2),
                        unlocation(centre, "rnw_harvest_rationing"),
                        "add_stability = stability_weak_bonus",
                        *end,
                    ),
                    55,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Hold to the levy; it saved the city.",
                    (gold(2), "add_stability = stability_mild_penalty", *end),
                    45,
                ),
            ),
            requires=path_is(path, 2),
        ),
        Node(
            4,
            "The New Fields Bear",
            fields,
            (
                Option(
                    "a",
                    "Give the new land to the families of the city.",
                    (
                        location(centre, "rnw_harvest_shared_fields", 20),
                        "add_legitimacy = legitimacy_weak_bonus",
                        *end,
                    ),
                    55,
                ),
                Option(
                    "b",
                    "Sell the new land and its grain abroad.",
                    (gold(3), *end),
                    45,
                ),
            ),
            requires=path_is(path, 3),
        ),
    )
    modifiers = (
        Modifier(
            "rnw_harvest_bought_grain",
            LOCATION,
            Source(STATIC, "cheap_food_in_location"),
            "Grain From Abroad",
            "Bought grain keeps bread cheap and the city growing.",
        ),
        Modifier(
            "rnw_harvest_rationing",
            LOCATION,
            Source(STATIC, "enforced_rationing_policy"),
            "Rationing",
            "The stores are shared out by the stewards, and the city eats less and grumbles more.",
        ),
        Modifier(
            "rnw_harvest_new_fields",
            LOCATION,
            Source(STATIC, "cultivators_grange_clearing_modifier"),
            "New Fields",
            "Drained margins and cleared ground bring in more grain every year.",
        ),
        Modifier(
            "rnw_harvest_grain_charter",
            COUNTRY,
            Source(STATIC, "trusted_merchants"),
            "Charter of the Grain Merchants",
            "The grain houses are trusted with the trade, and they trade for the whole country.",
        ),
        Modifier(
            "rnw_harvest_public_granaries",
            LOCATION,
            Source(STATIC, "mam_granary_of_the_mediterranean"),
            "Public Granaries",
            "Granaries filled in good years feed the city in bad ones.",
        ),
        Modifier(
            "rnw_harvest_shared_fields",
            LOCATION,
            Source(STATIC, "iro_three_sisters_harvest"),
            "Fields of the Many Families",
            "Many small plots, each sown with three crops together, yield more than one large one.",
        ),
    )
    return Story("harvest", "rnw_harvest", centre, path, nodes, modifiers)


def route() -> Story:
    """A road between two cities of one state, and who pays for it."""
    centre, other, path = ROUTE_FROM_VARIABLE, ROUTE_TO_VARIABLE, ROUTE_PATH_VARIABLE
    end = tuple(f"remove_variable = {name}" for name in (centre, other, path))
    first = prose("""
        [target_location.GetNameWithNoTooltip] and [other_location.GetNameWithNoTooltip] lie a
        few days apart over a track that the rains wash out every spring. Grain goes one way and
        cloth the other, and every cart pays the toll of each village between. The guilds of both
        cities have come to the court with the same plea and with different plans.
    """)
    opened = prose("""
        The first caravans crossed the new road before the last stones were set. Between
        [target_location.GetNameWithNoTooltip] and [other_location.GetNameWithNoTooltip] the carts
        now pass in a day, and the clerks of both cities have begun to quarrel over whose market
        the road serves.
    """)
    tolls = prose("""
        The merchants who built the road have found that a toll is a thing that grows. The
        carters of [other_location.GetNameWithNoTooltip] pay twice what they did and the guilds of
        [target_location.GetNameWithNoTooltip] sell their cloth at the gate for the price of the
        road. Each side says the other has the ear of the court.
    """)
    fairs = prose("""
        The villages between the two cities have kept their pact. On every crossing a fair is
        held twice a year, and the traders of [target_location.GetNameWithNoTooltip] and
        [other_location.GetNameWithNoTooltip] meet there half way, to the profit of both and the
        annoyance of the guilds of each.
    """)
    nodes = (
        Node(
            1,
            "A Road Between Two Cities",
            first,
            (
                Option(
                    "a",
                    "Build a paved road between the two cities.",
                    (
                        gold(-4),
                        country("rnw_route_road_works", 8),
                        location(centre, "rnw_route_paved_road", 20),
                        location(other, "rnw_route_paved_road", 20),
                        set_to(path, 1),
                    ),
                    40,
                    Follow(2, (36, 60)),
                    AFFORD,
                ),
                Option(
                    "b",
                    "Let the merchants build it and keep the tolls.",
                    (
                        country("rnw_route_toll_charter", 12),
                        location(centre, "rnw_route_tollgates", 15),
                        set_to(path, 2),
                    ),
                    35,
                    Follow(3, (30, 54)),
                ),
                Option(
                    "c",
                    "Make a pact with the villages between: a market day at every crossing.",
                    (
                        location(centre, "rnw_route_market_days", 10),
                        location(other, "rnw_route_market_days", 10),
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
            "The Road Is Open",
            opened,
            (
                Option(
                    "a",
                    "Garrison the road and keep it in repair.",
                    (gold(-2), location(centre, "rnw_route_royal_road", 20), *end),
                    55,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Charge a toll at each end and let the road look to itself.",
                    (gold(3), location(other, "rnw_route_tolls_resented", 10), *end),
                    45,
                ),
            ),
            requires=path_is(path, 1),
        ),
        Node(
            3,
            "The Tolls Grow Heavy",
            tolls,
            (
                Option(
                    "a",
                    "Cap the tolls at the old rate.",
                    (
                        unlocation(centre, "rnw_route_tollgates"),
                        "add_legitimacy = legitimacy_weak_bonus",
                        *end,
                    ),
                    55,
                ),
                Option(
                    "b",
                    "Let the tolls stand; the road is theirs.",
                    (gold(2), "add_stability = stability_mild_penalty", *end),
                    45,
                ),
            ),
            requires=path_is(path, 2),
        ),
        Node(
            4,
            "The Market Days",
            fairs,
            (
                Option(
                    "a",
                    "Charter the fairs and send a bailiff to every crossing.",
                    (
                        gold(-2),
                        location(centre, "rnw_route_chartered_fairs", 20),
                        location(other, "rnw_route_chartered_fairs", 20),
                        *end,
                    ),
                    55,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Leave the fairs to the villages.",
                    ("add_stability = stability_weak_bonus", *end),
                    45,
                ),
            ),
            requires=path_is(path, 3),
        ),
    )
    modifiers = (
        Modifier(
            "rnw_route_road_works",
            COUNTRY,
            Source(STATIC, "fra_royal_postal_roads_expansion"),
            "Road Works",
            "The court pays for roads and the work goes quickly.",
        ),
        Modifier(
            "rnw_route_paved_road",
            LOCATION,
            Source(STATIC, "improved_flow_of_goods"),
            "A Paved Road",
            "Goods move more easily and the roadside towns grow.",
        ),
        Modifier(
            "rnw_route_toll_charter",
            COUNTRY,
            Source(STATIC, "merchant_benefits"),
            "Charter of the Road Merchants",
            "The merchants who keep the road are given the right of the toll.",
        ),
        Modifier(
            "rnw_route_tollgates",
            LOCATION,
            Source(STATIC, "merchant_expedition"),
            "Tollgates",
            "A toll house at the gate brings merchants and their warehouses to the city.",
        ),
        Modifier(
            "rnw_route_market_days",
            LOCATION,
            Source(STATIC, "influx_of_merchants_modifier"),
            "Market Days",
            "Traders from the villages along the way come to town on fair days.",
        ),
        Modifier(
            "rnw_route_royal_road",
            LOCATION,
            Source(STATIC, "strengthened_crown_control"),
            "The Court's Road",
            "A garrisoned road keeps the trade in the court's hands.",
        ),
        Modifier(
            "rnw_route_tolls_resented",
            LOCATION,
            Source(STATIC, "upset_merchants"),
            "Resented Tolls",
            "The merchants pay and grumble, and they bring less.",
        ),
        Modifier(
            "rnw_route_chartered_fairs",
            LOCATION,
            Source(STATIC, "BYZ_grand_fair_of_st_demetrius"),
            "Chartered Fairs",
            "A great fair in season fills the warehouses and the inns.",
        ),
    )
    return Story(
        "route_market",
        "rnw_route",
        centre,
        path,
        nodes,
        modifiers,
        other=other,
        immediate=(f"var:{other} ?= {{ save_scope_as = other_location }}",),
        gate=(f"var:{other} ?= {{ owner ?= root }}",),
        holds_other=True,
    )


def alliance() -> Story:
    """A council of neighbours who share a faith or a people, and what the court makes of it."""
    centre, other, path = ALLIANCE_HOME_VARIABLE, ALLIANCE_SEAT_VARIABLE, ALLIANCE_PATH_VARIABLE
    end = tuple(f"remove_variable = {name}" for name in (centre, other, path))
    first = prose("""
        Envoys of [target_country.GetName] have come to [target_location.GetNameWithNoTooltip].
        The two courts keep the same gods or speak the same tongue, they have the same enemies on
        the same borders, and for generations they have sent each other nothing but complaints.
        The envoys propose a council where the rulers of both would speak as equals. The court's
        own counsellors would rather it were not so.
    """)
    met = prose("""
        The rulers of [target_country.GetName] and of this court have met three times, and each
        time they have parted with less suspicion. The council has begun to settle small quarrels
        along the border before they become large ones. Some at court say it should bind the two
        crowns more closely. Others say it should stay a council.
    """)
    bristles = prose("""
        The court of [target_country.GetName] took the offer of protection for what it was. Its
        envoys have left, its merchants have been recalled, and a letter has come in the hand of
        its ruler, asking by what right this court speaks of deference.
    """)
    closed = prose("""
        The court of [target_country.GetName] has taken its answer and turned elsewhere. Its
        envoys now sit in the lanes of the other neighbours, and a border that was quiet is
        watched from both sides. The counsellors ask whether the refusal was wise.
    """)
    nodes = (
        Node(
            1,
            "Envoys From the Next Valley",
            first,
            (
                Option(
                    "a",
                    "Sit in a council of equals.",
                    (
                        gold(-2),
                        country("rnw_alliance_council", 10),
                        _partner_modifier(other, "rnw_alliance_trust", 10),
                        _mutual("succesful_embassy"),
                        set_to(path, 1),
                    ),
                    40,
                    Follow(2, (36, 60)),
                    AFFORD,
                ),
                Option(
                    "b",
                    "Offer protection and ask for deference.",
                    (
                        country("rnw_alliance_pressure", 10),
                        _mutual("outrageous_demands"),
                        set_to(path, 2),
                    ),
                    35,
                    Follow(3, (30, 54)),
                ),
                Option(
                    "c",
                    "Thank them and keep your own counsel.",
                    (
                        country("rnw_alliance_closed_doors", 10),
                        _mutual("denied_aid"),
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
            "The Council Meets",
            met,
            (
                Option(
                    "a",
                    "Bind the two courts by marriage and treaty.",
                    (
                        gold(-2),
                        country("rnw_alliance_kinship", 15),
                        _partner_modifier(other, "rnw_alliance_kinship", 15),
                        _mutual("opinion_military_aid"),
                        *end,
                    ),
                    50,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Keep the council as it is.",
                    ("add_stability = stability_weak_bonus", *end),
                    50,
                ),
            ),
            requires=path_is(path, 1),
        ),
        Node(
            3,
            "The Neighbour Bristles",
            bristles,
            (
                Option(
                    "a",
                    "Withdraw the demand and send gifts.",
                    (
                        gold(-3),
                        _without("rnw_alliance_pressure"),
                        _mutual("opinion_sent_help"),
                        *end,
                    ),
                    50,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Stand firm.",
                    (
                        "add_prestige = prestige_weak_bonus",
                        "add_stability = stability_mild_penalty",
                        *end,
                    ),
                    50,
                ),
            ),
            requires=path_is(path, 2),
        ),
        Node(
            4,
            "A Door Closed",
            closed,
            (
                Option(
                    "a",
                    "Send a second embassy with an open hand.",
                    (
                        gold(-2),
                        _without("rnw_alliance_closed_doors"),
                        _mutual("succesful_embassy"),
                        *end,
                    ),
                    50,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Let the refusal stand.",
                    ("add_legitimacy = legitimacy_weak_bonus", *end),
                    50,
                ),
            ),
            requires=path_is(path, 3),
        ),
    )
    modifiers = (
        Modifier(
            "rnw_alliance_council",
            COUNTRY,
            Source(STATIC, "iro_assertive_council_of_fifty"),
            "Council of Neighbours",
            "The court shares its counsels with a neighbour, and its nobles gain a voice.",
        ),
        Modifier(
            "rnw_alliance_trust",
            COUNTRY,
            Source(STATIC, "iro_earn_tribal_trust"),
            "Trust of the Council",
            "A neighbour who has sat at the council is believed abroad.",
        ),
        Modifier(
            "rnw_alliance_pressure",
            COUNTRY,
            Source(STATIC, "iro_too_aggressive_consolidation"),
            "Pressure on the Neighbour",
            "Demands of deference have made the court's word worth less abroad.",
        ),
        Modifier(
            "rnw_alliance_closed_doors",
            COUNTRY,
            Source(STATIC, "iro_forbade_foreign_contact"),
            "Closed Counsels",
            "The court keeps its own counsel, and its borders are watched more closely.",
        ),
        Modifier(
            "rnw_alliance_kinship",
            COUNTRY,
            Source(STATIC, "union_of_crowns_pact_modifier"),
            "Kinship of the Courts",
            "Two courts joined by marriage and treaty support each other's rule.",
        ),
    )
    return Story(
        "great_alliance",
        "rnw_alliance",
        centre,
        path,
        nodes,
        modifiers,
        other=other,
        immediate=(f"var:{other} ?= {{ owner ?= {{ save_scope_as = target_country }} }}",),
        gate=(f"var:{other} ?= {{ owner ?= {{ NOT = {{ this = root }} }} }}",),
    )


def empire() -> Story:
    """A far province of a state that holds subjects, and how it is held."""
    centre, other, path = EMPIRE_HOME_VARIABLE, EMPIRE_FAR_VARIABLE, EMPIRE_PATH_VARIABLE
    end = tuple(f"remove_variable = {name}" for name in (centre, other, path))
    first = prose("""
        The reach of this court has outgrown its roads. In [other_location.GetNameWithNoTooltip],
        far from [target_location.GetNameWithNoTooltip], the people keep their own customs and
        their own lords, send their dues late and their sons never. The governors write that the
        province is quiet. The merchants write that it is not.
    """)
    governor = prose("""
        The governor of [other_location.GetNameWithNoTooltip] writes that the garrison is paid and
        the dues arrive. He also writes that he has taken a house in the old quarter and a wife
        from a local family, and that the old lords now dine at his table. The court is not sure
        whether to be pleased.
    """)
    charters = prose("""
        Word of the charter of [other_location.GetNameWithNoTooltip] reached the other far
        provinces faster than any tax collector. Delegations from three more have asked for the
        same, and the nobles of the heartland ask why the periphery is paid for its distance.
    """)
    settlers = prose("""
        The settlers from the heartland have built their houses along the road into
        [other_location.GetNameWithNoTooltip]. They speak the court's tongue and keep the court's
        gods, and the old families of the province keep their distance. A quarrel in the market
        has already ended in knives.
    """)
    nodes = (
        Node(
            1,
            "The Far Provinces",
            first,
            (
                Option(
                    "a",
                    "Send a governor with a garrison.",
                    (
                        gold(-3),
                        country("rnw_empire_governors", 15),
                        set_to(path, 1),
                    ),
                    40,
                    Follow(2, (36, 60)),
                    AFFORD,
                ),
                Option(
                    "b",
                    "Grant the province a charter of its own customs.",
                    (
                        location(other, "rnw_empire_charter", 20),
                        country("rnw_empire_concessions", 15),
                        set_to(path, 2),
                    ),
                    35,
                    Follow(3, (36, 60)),
                ),
                Option(
                    "c",
                    "Settle families from the heartland among them.",
                    (
                        gold(-2),
                        location(other, "rnw_empire_settlers", 15),
                        set_to(path, 3),
                    ),
                    25,
                    Follow(4, (36, 72)),
                    AFFORD,
                ),
            ),
            requires=(f"NOT = {{ has_variable = {path} }}",),
        ),
        Node(
            2,
            "The Governor's Reach",
            governor,
            (
                Option(
                    "a",
                    "Rotate the governors every few years.",
                    (gold(-2), "add_stability = stability_weak_bonus", *end),
                    50,
                    trigger=AFFORD,
                ),
                Option(
                    "b",
                    "Let him stay; a governor who belongs is a governor who holds.",
                    ("add_legitimacy = legitimacy_weak_bonus", *end),
                    50,
                ),
            ),
            requires=path_is(path, 1),
        ),
        Node(
            3,
            "Charters Multiply",
            charters,
            (
                Option(
                    "a",
                    "Extend the charters to every province that asks.",
                    (
                        "add_legitimacy = legitimacy_weak_bonus",
                        "add_stability = stability_weak_penalty",
                        *end,
                    ),
                    50,
                ),
                Option(
                    "b",
                    "Refuse; the charter was a favour.",
                    (
                        unlocation(other, "rnw_empire_charter"),
                        "add_stability = stability_mild_penalty",
                        "add_prestige = prestige_weak_bonus",
                        *end,
                    ),
                    50,
                ),
            ),
            requires=path_is(path, 2),
        ),
        Node(
            4,
            "New Neighbours",
            settlers,
            (
                Option(
                    "a",
                    "Give the old families a seat in the town council.",
                    ("add_stability = stability_weak_bonus", *end),
                    55,
                ),
                Option(
                    "b",
                    "Back the settlers against the old families.",
                    (gold(2), "add_stability = stability_mild_penalty", *end),
                    45,
                ),
            ),
            requires=path_is(path, 3),
        ),
    )
    modifiers = (
        Modifier(
            "rnw_empire_governors",
            COUNTRY,
            Source(STATIC, "delhi_loyal_governors_modifier"),
            "Loyal Governors",
            "Governors in the far provinces keep the court's hand on them.",
        ),
        Modifier(
            "rnw_empire_charter",
            LOCATION,
            Source(STATIC, "minority_prospers"),
            "Charter of Customs",
            "A province that keeps its own customs is quiet, and it prospers.",
        ),
        Modifier(
            "rnw_empire_concessions",
            COUNTRY,
            Source(STATIC, "giving_appanage_grant_admin_autonomy"),
            "Concessions to the Periphery",
            "Rule from the heartland loosens its grip on the far lands.",
        ),
        Modifier(
            "rnw_empire_settlers",
            LOCATION,
            Source(STATIC, "birth_of_a_new_city_dip"),
            "New Neighbours",
            "Settlers from the heartland draw their kin to the province and its markets.",
        ),
    )
    return Story(
        "empire_periphery",
        "rnw_empire",
        centre,
        path,
        nodes,
        modifiers,
        other=other,
        immediate=(f"var:{other} ?= {{ save_scope_as = other_location }}",),
        gate=(f"var:{other} ?= {{ owner ?= {{ NOT = {{ this = root }} }} }}",),
    )
