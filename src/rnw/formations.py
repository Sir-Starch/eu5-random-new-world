"""The formable families of the content plan: what each one is called, costs and gives (N3, N4).

A formable is a country the game offers to those who hold most of a territory
(``formable_countries``). The territory and the states it is offered to are the world's
(``content``); what a family is is static and written once here: the stem of its name (each
language writes the name from it, ``wording``), its level and rank, the founding modifier it
gives with the payload of a vanilla modifier (as the stories do), a coat of arms, and the words
that describe it. A family's political path differs by
what it asks and what it grants; none gives the same permanent bonus as another. A family's
``potential`` is the states the world names when it is empty (the formable is offered to them);
a family whose bearers do not exist at the start (a colonial federation) states in script who sees
it.

The levels order the families (a country can only form a formable of a higher level than its
own), so no chain of formations can run in a circle: the county-level states form the duchies,
those the kingdoms, a kingdom the realm of its region, and an empire the one empire of the New
World (level 5, above every rank, as vanilla's ``EUR_f``). Each level is a goal of its own:
whoever holds enough of a territory may form it, not only the states of 1337 (history plan §22,
N6); a cultural commonwealth asks for the people's culture group from anyone else; and a
formation gives cores on the rest of its territory, so that vanilla's ``cb_conquer_province``
opens against every remaining holder.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from rnw.content import (
    CULTURAL_UNION,
    HIGHLAND_CONFEDERATION,
    MARITIME_LEAGUE,
    NEW_WORLD_EMPIRE,
    POSTCOLONIAL_FEDERATION,
    REGIONAL_REALM,
    RESTORATION,
    RIVER_UNION,
)
from rnw.storymodel import COUNTRY, REFORM, STATIC, Modifier, Source

# The highest level a country rank has; a formable above it is formed by an empire and keeps it.
TOP_RANK_LEVEL: Final[int] = 4
# The key of the formation's tooltip for the cores it gives (``hidden_effect`` does the work).
CORES_TOOLTIP: Final[str] = "rnw_formation_cores_tt"
# The adjective of the empire of the New World, whose name is the continent's own text.
EMPIRE_ADJECTIVE: Final[str] = "rnw_formation_new_world_empire_adj"
# The event the other heirs receive when one restores the fallen realm (N7), its texts and the
# tooltip of the formation that sends it. ``restorer`` is the restored country.
RESTORATION_EVENT: Final[str] = "rnw_restoration"
HEIRS_TOOLTIP: Final[str] = "rnw_restoration_heirs_tt"
EXTRA_TEXTS: Final[dict[str, str]] = {
    HEIRS_TOOLTIP: (
        "Every other heir of the old realm must recognize the restoration or contest it."
    ),
    f"{RESTORATION_EVENT}.title": "The Old Realm Restored",
    f"{RESTORATION_EVENT}.desc": (
        "Envoys of [restorer.GetNameWithNoTooltip] have come with a proclamation: the realm "
        "that our ancestors shared is restored, and its new crown calls every land it once held "
        "its own, ours among them. Our council must decide whether to bow to the old name or to "
        "deny it."
    ),
    f"{RESTORATION_EVENT}.a": "We recognize the restored crown.",
    f"{RESTORATION_EVENT}.b": "The old crown is no more theirs than ours.",
    CORES_TOOLTIP: (
        "Every [location|e] of the territory that another country holds becomes our [core|e], "
        "and its holder can be fought for it."
    ),
    EMPIRE_ADJECTIVE: "American",
}


@dataclass(frozen=True, slots=True)
class Reform:
    """A government reform of the mod that a formation opens, with a vanilla reform's
    ``country_modifier`` copied under its own name (as the stories copy modifiers)."""

    name: str
    source: Source
    title: str
    text: str


def _reform(name: str, vanilla: str, title: str, text: str) -> Reform:
    return Reform(name, Source(REFORM, vanilla, "country_modifier"), title, text)


@dataclass(frozen=True, slots=True)
class Spec:
    """One family of formables: its name, level, founding modifier, arms and words.

    ``rule`` is the game rule that shows it (``plausible`` or ``fantasy``); ``cores`` says whether
    founding it gives cores over its territory; ``renamed`` that its founder takes the name of its
    own naming tradition (``colonial_names.TRADITIONS``), if it has one; ``heirs`` that it is
    offered to the heirs of a fallen realm, the others of whom must accept or contest it.
    """

    family: str
    stem: str
    level: int
    rank: str
    fraction: str
    emblem: str
    description: str
    modifier: Modifier
    years: int
    allow: tuple[str, ...] = ()
    potential: tuple[str, ...] = ()
    rule: str = "plausible"
    cores: bool = True
    renamed: bool = False
    heirs: bool = False
    reform: Reform | None = None

    @property
    def rank_level(self) -> int:
        """The level of the rank the formation raises its founder to."""
        return min(self.level, TOP_RANK_LEVEL)


SPECS: Final[tuple[Spec, ...]] = (
    Spec(
        family=RIVER_UNION,
        stem="union",
        level=3,
        rank="rank_kingdom",
        fraction="0.6",
        emblem="ce_checky_15_points.dds",
        description=(
            "The towns on one river have traded, built and answered to each other for "
            "generations. A power that holds most of them may bind them into one state: the "
            "{name}."
        ),
        modifier=Modifier(
            "rnw_union_markets",
            COUNTRY,
            Source(STATIC, "consolidated_trade_modifier"),
            "Markets of One River",
            "The river towns sell their goods as one market.",
        ),
        years=10,
        reform=_reform(
            "rnw_reform_river_markets",
            "son_trans_saharan_trade",
            "Charter of the River Markets",
            (
                "The towns of the river trade under one charter, and their merchants "
                "travel the whole of its course."
            ),
        ),
    ),
    Spec(
        family=HIGHLAND_CONFEDERATION,
        stem="confederation",
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
        reform=_reform(
            "rnw_reform_valley_council",
            "iro_council_of_the_fifty",
            "Council of the Valleys",
            (
                "The chiefs of every valley sit in one council, and nothing is decided "
                "until all of them agree."
            ),
        ),
    ),
    Spec(
        family=MARITIME_LEAGUE,
        stem="league",
        level=2,
        rank="rank_duchy",
        fraction="0.6",
        emblem="ce_anchor_shield.dds",
        description=(
            "The ports of one coast sail the same waters and fear the same storms. A power "
            "that holds most of them may unite them in a league, the {name}, to trade "
            "together and defend their sea."
        ),
        modifier=Modifier(
            "rnw_league_charter",
            COUNTRY,
            Source(STATIC, "seal_of_hansa_modifier"),
            "Charter of the League",
            "One charter binds the merchants and the councils of every port.",
        ),
        years=20,
        reform=_reform(
            "rnw_reform_port_council",
            "signoria_of_venice",
            "Council of the Ports",
            (
                "The merchant houses of every port govern the league together, and its "
                "ships carry their goods to every shore."
            ),
        ),
        allow=("num_of_ports >= 3",),
    ),
    Spec(
        family=CULTURAL_UNION,
        stem="commonwealth",
        level=3,
        rank="rank_kingdom",
        fraction="0.5",
        emblem="ce_rosette_06.dds",
        description=(
            "The towns of one people speak one tongue and keep one custom under many rulers. "
            "A power that holds most of them may gather them into a commonwealth: the {name}."
        ),
        modifier=Modifier(
            "rnw_commonwealth_unity",
            COUNTRY,
            Source(STATIC, "pue_unification_of_the_ancestral_puebloans"),
            "One People",
            "One tongue and one custom hold the commonwealth together and raise its standing.",
        ),
        years=20,
        reform=_reform(
            "rnw_reform_one_people",
            "iro_reforged_law_of_peace",
            "Law of One People",
            (
                "One law binds the peoples of the commonwealth and keeps the peace among "
                "its many towns."
            ),
        ),
    ),
    Spec(
        family=REGIONAL_REALM,
        stem="realm",
        level=4,
        rank="rank_empire",
        fraction="0.4",
        emblem="ce_star_08.dds",
        description=(
            "A whole region lies divided among many rulers, each holding a few of its towns. "
            "A power that holds much of it and its greatest city may unite it into one realm, "
            "the {name}, and claim the rest of the region as its own."
        ),
        modifier=Modifier(
            "rnw_realm_administration",
            COUNTRY,
            Source(STATIC, "lat_a_distinct_latin_bureaucracy"),
            "Administration of the Realm",
            "A new administration reaches across the region, and its provinces come to heel.",
        ),
        years=15,
        reform=_reform(
            "rnw_reform_realm_provinces",
            "subah_organization_reform",
            "Provinces of the Realm",
            (
                "The realm is divided into provinces under its governors, and its towns "
                "grow under their care."
            ),
        ),
    ),
    Spec(
        family=POSTCOLONIAL_FEDERATION,
        stem="federation",
        level=3,
        rank="rank_kingdom",
        fraction="0.35",
        emblem="ce_star_05.dds",
        description=(
            "Colonies on one shore, settled from one old country or from several, have come "
            "to share one grievance and one future. An independent state of settlers, or the "
            "leader of their colonial federation, that holds enough of the shore with its capital "
            "there may proclaim a nation of its own: the {name}. Founders of Spanish, Portuguese, "
            "English, French or Dutch tongue give it a name in their own tradition."
        ),
        modifier=Modifier(
            "rnw_federation_founded",
            COUNTRY,
            Source(STATIC, "new_colonial_nation_founded"),
            "A Nation Founded",
            "A young nation of settlers grows fast and has little patience for rebels.",
        ),
        years=10,
        reform=_reform(
            "rnw_reform_national_articles",
            "constitutional_state",
            "Articles of the Nation",
            "Written articles bind the states of the nation and the assembly that speaks for them.",
        ),
        allow=(
            (
                "OR = { is_subject = no is_leader_of_international_organization_of_type = "
                "{ type = colonial_federation } }"
            ),
        ),
        potential=(
            (
                "OR = { culture ?= { is_culture_native_american = no } "
                "religion.group = religion_group:christian }"
            ),
        ),
        renamed=True,
    ),
    Spec(
        family=NEW_WORLD_EMPIRE,
        stem="empire",
        level=5,
        rank="rank_empire",
        fraction="0.5",
        emblem="ce_arapaho_sun_shield.dds",
        description=(
            "No ruler has ever held this continent from shore to shore. An empire that leads the "
            "world and holds half of it, with its court on its soil, may proclaim itself "
            "the empire of all its peoples: {name}."
        ),
        modifier=Modifier(
            "rnw_empire_coronation",
            COUNTRY,
            Source(STATIC, "fc_imperial_coronation"),
            "A Crown Over the Continent",
            "Envoys from every corner of the continent attend the new court and bring it honour.",
        ),
        years=20,
        allow=("is_hegemon = yes", "country_rank = country_rank:rank_empire"),
        rule="fantasy",
        cores=False,
    ),
    Spec(
        family=RESTORATION,
        stem="restoration",
        level=3,
        rank="rank_kingdom",
        fraction="0.5",
        emblem="ce_crown_head.dds",
        description=(
            "A realm once held these lands, until it broke apart among its heirs, who remember it "
            "still. An heir that holds enough of its old land, with its capital there, may raise "
            "it again and claim the rest of it as its own: {name}. The other heirs must accept "
            "the restoration or contest it."
        ),
        modifier=Modifier(
            "rnw_restoration_heirs",
            COUNTRY,
            Source(STATIC, "dlh_restored_authority_modifier"),
            "Heirs of the Old Realm",
            (
                "The restored crown gathers the old offices and brings its lost provinces back "
                "under one rule."
            ),
        ),
        years=20,
        reform=_reform(
            "rnw_reform_restored_crown",
            "dan_the_kings_law",
            "Law of the Restored Crown",
            (
                "The restored crown takes back the old rights of its predecessors and "
                "rules from one seat again."
            ),
        ),
        heirs=True,
    ),
)

BY_FAMILY: Final[dict[str, Spec]] = {spec.family: spec for spec in SPECS}
