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
        The rains came late and the harvest came in thin. In [target_location.GetNameWithNoTooltip]
        the granaries stand half empty, bread costs twice what it did a month ago, and the city eats
        more than its fields have ever grown. The reeves have brought their tallies to court. By
        their count the stores will last until midwinter, and not a day longer.
    """)
    merchants = prose("""
        The grain that fed [target_location.GetNameWithNoTooltip] last winter passed through the
        hands of a few merchant houses, and they remember who needed it. They hold the stores of the
        lower town and set the price in the market. Now they ask the court to put in writing what
        they have done for a year without asking.
    """)
    villages = prose("""
        Last winter the villages gave up their seed grain, and they have not forgiven it. At the
        spring markets of [target_location.GetNameWithNoTooltip] the farmers bring less and ask
        more, and the carters talk of fields left fallow. The stewards still call the levy a
        necessity. In the villages they have another word for it.
    """)
    fields = prose("""
        Two harvests on, the drained fields outside [target_location.GetNameWithNoTooltip] grow
        grain where reeds once stood. Families from the crowded lanes have asked for a share of the
        new land, and the stewards have asked for a tithe of it.
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
                    "Ration the stores and take grain from the villages.",
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
                    "Break new ground and drain the wet edges of the plain.",
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
                    "Break their hold. The city will keep its own granaries.",
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
                    "The levy saved the city. We owe them nothing.",
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
                    "Sell the new land and ship its grain abroad.",
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
            "The stewards share out the stores. The city eats less and grumbles more.",
        ),
        Modifier(
            "rnw_harvest_new_fields",
            LOCATION,
            Source(STATIC, "cultivators_grange_clearing_modifier"),
            "New Fields",
            "Drained marsh and cleared ground bring in more grain each year.",
        ),
        Modifier(
            "rnw_harvest_grain_charter",
            COUNTRY,
            Source(STATIC, "trusted_merchants"),
            "Charter of the Grain Merchants",
            "The grain houses hold the trade by charter and carry it for the whole country.",
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
            "Small plots, each sown with three crops together, yield more than one great field.",
        ),
    )
    return Story("harvest", "rnw_harvest", centre, path, nodes, modifiers)


def route() -> Story:
    """A road between two cities of one state, and who pays for it."""
    centre, other, path = ROUTE_FROM_VARIABLE, ROUTE_TO_VARIABLE, ROUTE_PATH_VARIABLE
    end = tuple(f"remove_variable = {name}" for name in (centre, other, path))
    first = prose("""
        [target_location.GetNameWithNoTooltip] and [other_location.GetNameWithNoTooltip] lie a few
        days apart, joined by a track the rains wash away each spring. Grain goes one way and cloth
        the other, and every cart pays a toll at every village in between. The guilds of both cities
        have come to court with the same complaint and two very different plans.
    """)
    opened = prose("""
        The first caravans crossed the new road before the last stones were laid. Carts now make the
        journey between [target_location.GetNameWithNoTooltip] and
        [other_location.GetNameWithNoTooltip] in a day, and the clerks of the two cities have
        already begun quarrelling over whose market the road was built for.
    """)
    tolls = prose("""
        The merchants who built the road have learned that a toll, once set, tends to grow. The
        carters of [other_location.GetNameWithNoTooltip] pay twice what they did, and the cloth of
        [target_location.GetNameWithNoTooltip] costs as much at the gate as the road itself. Each
        city is sure the other has the ear of the court.
    """)
    fairs = prose("""
        The villages along the way have kept their pact. Twice a year a fair is held at every
        crossing, and the traders of [target_location.GetNameWithNoTooltip] and
        [other_location.GetNameWithNoTooltip] meet there halfway, to the profit of both and the
        annoyance of their guilds.
    """)
    nodes = (
        Node(
            1,
            "A Road Between Two Cities",
            first,
            (
                Option(
                    "a",
                    "Pave a road between the two cities.",
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
                    "Let the merchants build it, and let them keep the tolls.",
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
                    "Make a pact with the villages: a market day at every crossing.",
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
                    "Put a toll at each end and let the road pay for itself.",
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
                    "They built the road. The tolls are theirs to set.",
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
                    "The fairs belong to the villages. Leave them be.",
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
            "The court pays for the roads, and the work goes quickly.",
        ),
        Modifier(
            "rnw_route_paved_road",
            LOCATION,
            Source(STATIC, "improved_flow_of_goods"),
            "A Paved Road",
            "Goods move more easily, and the towns along the road grow.",
        ),
        Modifier(
            "rnw_route_toll_charter",
            COUNTRY,
            Source(STATIC, "merchant_benefits"),
            "Charter of the Road Merchants",
            "The merchants who keep the road hold the right to toll it.",
        ),
        Modifier(
            "rnw_route_tollgates",
            LOCATION,
            Source(STATIC, "merchant_expedition"),
            "Tollgates",
            "A toll house at the gate draws merchants and their warehouses into the city.",
        ),
        Modifier(
            "rnw_route_market_days",
            LOCATION,
            Source(STATIC, "influx_of_merchants_modifier"),
            "Market Days",
            "Traders from the villages along the road come to town on fair days.",
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
            "The merchants pay, grumble, and come less often.",
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
        Envoys of [target_country.GetName] have arrived in [target_location.GetNameWithNoTooltip].
        Our two courts share their gods or their tongue, and their enemies on the same borders, yet
        for generations they have exchanged nothing but complaints. The envoys propose a council
        where our rulers would speak as equals. Our own counsellors would rather the envoys had
        stayed at home.
    """)
    met = prose("""
        Our ruler and the ruler of [target_country.GetName] have met three times, and each time they
        parted with less suspicion. The council has begun to settle small quarrels on the border
        before they grow into large ones. The matchmakers at court are already drawing up lists. The
        old counsellors think a council is close enough.
    """)
    bristles = prose("""
        The court of [target_country.GetName] understood our offer of protection exactly as it was
        meant. Its envoys have gone, its merchants have been called home, and a letter has come in
        its ruler's own hand, asking by what right we speak of deference.
    """)
    closed = prose("""
        The court of [target_country.GetName] has had its answer and looked elsewhere. Its envoys
        now wait in the halls of our other neighbours, and a border that was quiet is watched from
        both sides. Our counsellors wonder aloud whether the refusal was wise.
    """)
    nodes = (
        Node(
            1,
            "Envoys From the Next Valley",
            first,
            (
                Option(
                    "a",
                    "We will sit with them as equals.",
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
                    "Offer them our protection, and ask for their deference.",
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
                    "Thank them and keep our own counsel.",
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
                    "Bind our houses by marriage and treaty.",
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
                    "A council is enough.",
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
                    "We said what we meant.",
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
                    "Send a second embassy, with open hands.",
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
            "A ruler who keeps a council with the neighbours is trusted abroad.",
        ),
        Modifier(
            "rnw_alliance_pressure",
            COUNTRY,
            Source(STATIC, "iro_too_aggressive_consolidation"),
            "Pressure on the Neighbour",
            "Our demands for deference have made our word worth less abroad.",
        ),
        Modifier(
            "rnw_alliance_closed_doors",
            COUNTRY,
            Source(STATIC, "iro_forbade_foreign_contact"),
            "Closed Counsels",
            "The court keeps its own counsel and watches its borders more closely.",
        ),
        Modifier(
            "rnw_alliance_kinship",
            COUNTRY,
            Source(STATIC, "union_of_crowns_pact_modifier"),
            "Kinship of the Courts",
            "Two courts bound by marriage and treaty uphold each other's rule.",
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
        Our realm has outgrown its roads. In [other_location.GetNameWithNoTooltip], far from
        [target_location.GetNameWithNoTooltip], the people keep their own customs and their own
        lords. They send their dues late and their sons never. The governors write that the province
        is quiet. The merchants write that it is not.
    """)
    governor = prose("""
        The governor of [other_location.GetNameWithNoTooltip] writes that the garrison is paid and
        the dues arrive on time. He also writes that he has taken a house in the old quarter and a
        wife from a local family, and that the old lords now dine at his table. The court cannot
        decide whether to be pleased.
    """)
    charters = prose("""
        News of the charter granted to [other_location.GetNameWithNoTooltip] reached the other far
        provinces faster than any tax collector. Three more have sent delegations asking for the
        same, and the nobles of the heartland want to know why the provinces are rewarded for being
        far away.
    """)
    settlers = prose("""
        The settlers from the heartland have built their houses along the road into
        [other_location.GetNameWithNoTooltip]. They speak our tongue and keep our gods, and the old
        families of the province keep their distance. A quarrel in the market has already ended in
        knives.
    """)
    nodes = (
        Node(
            1,
            "The Far Provinces",
            first,
            (
                Option(
                    "a",
                    "Send a governor, and a garrison with him.",
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
                    "Let him stay. A governor who belongs is a governor who holds.",
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
                    "Grant a charter to every province that asks.",
                    (
                        "add_legitimacy = legitimacy_weak_bonus",
                        "add_stability = stability_weak_penalty",
                        *end,
                    ),
                    50,
                ),
                Option(
                    "b",
                    "The charter was a favour, not a precedent.",
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
                    "Give the old families seats on the town council.",
                    ("add_stability = stability_weak_bonus", *end),
                    55,
                ),
                Option(
                    "b",
                    "Stand by the settlers.",
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
            "A province left to its own customs stays quiet and prospers.",
        ),
        Modifier(
            "rnw_empire_concessions",
            COUNTRY,
            Source(STATIC, "giving_appanage_grant_admin_autonomy"),
            "Concessions to the Provinces",
            "The heartland's grip on the far lands has loosened.",
        ),
        Modifier(
            "rnw_empire_settlers",
            LOCATION,
            Source(STATIC, "birth_of_a_new_city_dip"),
            "New Neighbours",
            (
                "Settlers from the heartland draw their kin after them, and the province's "
                "markets grow."
            ),
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
