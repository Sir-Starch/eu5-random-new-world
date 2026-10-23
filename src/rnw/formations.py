"""The formable families of the content plan: what each one is called, costs and gives (N3, N4).

A formable is a country the game offers to those who hold most of a territory
(``formable_countries``). The territory and the states it is offered to are the world's
(``content``); what a family is is static and written once here: the suffix of its name, its
level and rank, the founding modifier it gives with the payload of a vanilla modifier (as the
stories do), a coat of arms, and the words that describe it. A family's political path differs by
what it asks and what it grants; none gives the same permanent bonus as another.

The levels order the families (a country can only form a formable of a higher level than its
own), so no chain of formations can run in a circle: the county-level states form the duchies,
those the kingdoms, and a kingdom the one empire.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from rnw.content import (
    CULTURAL_UNION,
    HIGHLAND_CONFEDERATION,
    MARITIME_LEAGUE,
    REGIONAL_REALM,
    RIVER_UNION,
)
from rnw.stories import COUNTRY, STATIC, Modifier, Source


@dataclass(frozen=True, slots=True)
class Spec:
    """One family of formables: its name, level, founding modifier, arms and words."""

    family: str
    stem: str
    suffix: str
    level: int
    rank: str
    fraction: str
    emblem: str
    description: str
    modifier: Modifier
    years: int
    allow: tuple[str, ...] = ()


SPECS: Final[tuple[Spec, ...]] = (
    Spec(
        family=RIVER_UNION,
        stem="union",
        suffix="Union",
        level=3,
        rank="rank_kingdom",
        fraction="0.6",
        emblem="ce_checky_15_points.dds",
        description=(
            "The towns on one river have traded, built and answered to each other for "
            "generations. A single power that holds most of them may bind them into one state, "
            "the {name}."
        ),
        modifier=Modifier(
            "rnw_union_markets",
            COUNTRY,
            Source(STATIC, "consolidated_trade_modifier"),
            "Markets of One River",
            "The towns of the river sell their goods as one market.",
        ),
        years=10,
    ),
    Spec(
        family=HIGHLAND_CONFEDERATION,
        stem="confederation",
        suffix="Confederation",
        level=2,
        rank="rank_duchy",
        fraction="0.6",
        emblem="ce_mountain.dds",
        description=(
            "The valleys of one range live apart behind their passes and agree on little but "
            "their freedom. A power that holds most of them may bind them into a confederation, "
            "the {name}, and leave each valley its own council."
        ),
        modifier=Modifier(
            "rnw_confederation_compact",
            COUNTRY,
            Source(STATIC, "iro_strong_tribal_unity"),
            "Compact of the Valleys",
            "The valleys keep their own councils and stand together against any outside power.",
        ),
        years=20,
    ),
    Spec(
        family=MARITIME_LEAGUE,
        stem="league",
        suffix="League",
        level=2,
        rank="rank_duchy",
        fraction="0.6",
        emblem="ce_anchor_shield.dds",
        description=(
            "The ports of one coast sail the same waters and fear the same storms. A power that "
            "holds most of them may join them in a league, the {name}, for the trade and the "
            "defence of their sea."
        ),
        modifier=Modifier(
            "rnw_league_charter",
            COUNTRY,
            Source(STATIC, "seal_of_hansa_modifier"),
            "Charter of the League",
            "The common charter of the ports binds their merchants and their councils.",
        ),
        years=20,
        allow=("num_of_ports >= 3",),
    ),
    Spec(
        family=CULTURAL_UNION,
        stem="commonwealth",
        suffix="Commonwealth",
        level=3,
        rank="rank_kingdom",
        fraction="0.5",
        emblem="ce_rosette_06.dds",
        description=(
            "The towns of one people speak one tongue and keep the same customs under different "
            "rulers. A power that holds most of them may gather them into a commonwealth, the "
            "{name}."
        ),
        modifier=Modifier(
            "rnw_commonwealth_unity",
            COUNTRY,
            Source(STATIC, "pue_unification_of_the_ancestral_puebloans"),
            "One People",
            "One tongue and one custom hold the commonwealth together and raise its standing.",
        ),
        years=20,
    ),
    Spec(
        family=REGIONAL_REALM,
        stem="realm",
        suffix="Realm",
        level=4,
        rank="rank_empire",
        fraction="0.5",
        emblem="ce_star_08.dds",
        description=(
            "A whole region lies under many rulers, each holding a few of its towns. A power "
            "that holds most of it may unite it into one realm, the {name}."
        ),
        modifier=Modifier(
            "rnw_realm_administration",
            COUNTRY,
            Source(STATIC, "lat_a_distinct_latin_bureaucracy"),
            "Administration of the Realm",
            "A new administration reaches across the region, and its provinces come to heel.",
        ),
        years=15,
    ),
)

BY_FAMILY: Final[dict[str, Spec]] = {spec.family: spec for spec in SPECS}
