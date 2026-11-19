"""The decision for every vanilla script object that names the replaced New World.

Each consumer found by ``content_inventory`` gets exactly one decision (content plan, N0):

* **keep** - a general mechanic, or one whose binding to a vanilla region or area key by
  position is accepted;
* **rebind** - a mechanic that stays but is bound again to what the generated world holds;
* **neutralize** - a literal historical identity on random land, or an object no generated
  world can reach; it is removed, or already unreachable;
* **replace** - neutralized, and the purpose worth keeping is carried by original content
  of a later stage.

The table holds identifiers only, no vanilla text. Two structural rules decide what a list
would only repeat: a definition owned by a retired tag is inert, and an object the exporter
retires today (an event of a retired tag, a modifier only such events applied, a historical
base value of a removed location) is neutralized. An explicit row overrides a rule. An
object without a decision stops the export, so a patch that adds consumers fails loudly
until they are decided (``missing``); the local test also reports rows that no longer
match anything (``stale``).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from rnw.content_inventory import Consumer


class Decision(StrEnum):
    """What becomes of a consumer."""

    KEEP = "keep"
    REBIND = "rebind"
    NEUTRALIZE = "neutralize"
    REPLACE = "replace"


@dataclass(frozen=True, slots=True)
class Verdict:
    """A decision with its reason and the stage that carries a rebinding or a replacement."""

    decision: Decision
    reason: str
    stage: str = ""


REASONS: Final[Mapping[str, str]] = {
    "coast": "Discovery follows the sea areas of the generated American coast, including new ones.",
    "generic": "A general mechanic; the key only places it, and the remap keeps it working.",
    "positional": (
        "Follows the vanilla region or area key by position; accepted until N5 chooses keys "
        "by content, and the regional families of R7b rely on it."
    ),
    "homeland": (
        "Religious content that the natives pass places in the religion's most populated "
        "generated locations."
    ),
    "name": "Not a map reference: a given name that happens to equal a location key.",
    "inert": (
        "Gated by a retired tag, or owned by one: nothing can reach or consume it, so it "
        "stays as it is."
    ),
    "country_gate": (
        "The mechanic requires an original country tag in its eligibility conditions. "
        "No generated country starts with any of those tags."
    ),
    "retired": (
        "Retired by the exporter with its country: the events of retired tags, the "
        "modifiers only they applied, the historical base values of removed locations."
    ),
    "identity": (
        "Names a historical American person, place, company, work or incident that no "
        "generated world has."
    ),
    "culture": (
        "Historical formable or start effect gated by a culture or religion that the "
        "generated world reuses: bound again to the territory that culture holds."
    ),
    "lost": (
        "Reachable only through state (a variable or flag) that a retired chain alone set: "
        "the reward stays, its path is gone."
    ),
    "canal": (
        "The Panama canal chain needs the vanilla isthmus; removed together, never positionally."
    ),
    "suez": (
        "The Suez canal chain needs the vanilla isthmus and its fixed entry points. "
        "The generated border between Africa and Asia already determines land and sea access."
    ),
    "absent_start": "This startup effect assigns offices and actions to the old 1337 countries.",
    "frontier": (
        "Settling the unowned land beside a country: vanilla names the regions whose land "
        "countries border it, and every generated American region can hold one, so the "
        "American part of the gate becomes the whole New World."
    ),
    "illustration": (
        "Holds pictures of vanilla places, some of them American: the export drops each picture "
        "of a removed place (a picture shows its place, so it is not moved) and keeps the rest."
    ),
}

KEEP: Final = Decision.KEEP
REBIND: Final = Decision.REBIND
NEUTRALIZE: Final = Decision.NEUTRALIZE
REPLACE: Final = Decision.REPLACE


class _Table:
    """The rows being written; a consumer is decided once."""

    def __init__(self) -> None:
        self.rows: dict[str, Verdict] = {}

    def add(
        self, category: str, decision: Decision, reason: str, idents: str, stage: str = ""
    ) -> None:
        """Decide the consumers named in ``idents`` (separated by whitespace)."""
        for ident in idents.split():
            key = f"{category}:{ident}"
            if key in self.rows:
                message = f"Two decisions for {key}"
                raise ValueError(message)
            self.rows[key] = Verdict(decision, reason, stage)


def _common(table: _Table) -> None:
    """Rows of the objects under ``in_game/common``."""
    add = table.add
    # The regional families of R7b, and the unique advances of retired states.
    add(
        "common/advances",
        KEEP,
        "positional",
        """
        bison_hunters canoe_travels council_of_elders experienced_fur_hunters
        federal_constitution fishing_habits maple_syrup medicinal_infusions
        moundbuilding_advance north_american_warrior_societies seasonal_economy
        shared_brotherhood shared_knowledge slash_and_burn
        stickball_game three_sisters wampum whale_hunters
        """,
    )
    add(
        "common/advances",
        NEUTRALIZE,
        "inert",
        """
        adapted_incan_army chasqui drafted_hatun_runas inc_tambo inc_vertical_economy
        llama_michis military_mita mitma quipu tambo_advance warachikuy aztec_chargers
        brave_as_hummingbird calpixcayotl chinampas nahuatl_domination
        new_trade_opportunities people_of_war pochtecayotl reformed_telpochcalli
        the_return_of_quetzalcoatl tlahtocayotl warrior_societies
        """,
    )
    add("common/advances", NEUTRALIZE, "canal", "panama_canal_advance")
    add("common/advances", REBIND, "frontier", "settle_the_frontier_advance", "W7")
    add(
        "common/area_preferences",
        KEEP,
        "positional",
        """
        castile_conquer_new_world castile_explore_america castile_explore_brazil
        castile_explore_staging dutch_explore_atlantic_route england_explore_usa
        france_explore_great_plains france_explore_usa france_random_colonies
        new_world_institution_areas_explore portugal_explore_brazil russia_colonize_alaska
        """,
    )
    # Gated by ``country_potential = { has_or_had_tag = TNC }``, a retired tag: nothing builds it.
    add("common/building_types", REPLACE, "inert", "great_temple_of_tenochtitlan", "N3")
    add(
        "common/country_interactions",
        REPLACE,
        "inert",
        "form_closer_bond_iroquois merge_tribe_iroquois",
        "N4",
    )
    add(
        "common/customizable_localization",
        KEEP,
        "positional",
        """
        GetDangerousWildAnimalName Get_ru_DangerousWildAnimalName IO_ACC IO_DAT IO_GEN
        IO_INST IO_PREP colonial_federation_name
        """,
    )
    add(
        "common/customizable_localization",
        KEEP,
        "inert",
        """
        CL_ACC CL_DAT CL_GEN CL_INST CL_PREP CL_tt country_flavor
        country_rank_spanish_article country_ru_flavor end_assya end_enna end_etut
        end_etyut end_fem end_gegu end_itat end_ityat predlog_kko predlog_obo
        predlog_sso predlog_vvo
        """,
    )
    add("common/customizable_localization", NEUTRALIZE, "inert", "country_history")
    add(
        "common/decisions",
        NEUTRALIZE,
        "canal",
        "build_panama_canal close_panama_canal_to_enemies open_panama_canal_to_all",
    )
    add("common/decisions", REPLACE, "inert", "iro_iroquois_interactions_decision", "N4")
    add("common/estate_privileges", REPLACE, "lost", "hurin_qusqu_privilege", "N3")
    add(
        "common/expedition_types",
        KEEP,
        "generic",
        """
        circumnavigation_expedition pacific_crossing_expedition
        western_ocean_voyage_expedition
        cibola_expedition city_of_caesars_expedition el_dorado_expedition
        fountain_of_youth_expedition norumbega_expedition quivira_expedition
        saguenay_expedition sierra_de_la_plata_expedition
        gold_fleet_nueva_espana_expedition gold_fleet_tierra_firme_expedition
        """,
    )
    add("common/formable_countries", REBIND, "culture", "AZT_f INC_f IRO_f MAY_f PUE_f", "N1")
    add("common/formable_countries", REPLACE, "identity", "CAN_f MEX_f USA_f", "N4")
    add("common/generic_actions", REPLACE, "identity", "pilgrimage_to_cholula", "N3")
    add("common/goods", KEEP, "positional", "cocoa coffee rice tobacco wine")
    add("common/historical_scores", NEUTRALIZE, "inert", "tag_montezuma")
    add(
        "common/holy_sites",
        KEEP,
        "homeland",
        """
        bolon_yej_te_naah cholula_holy_city ek_balam hampatu ich_kaan_ti_ho inti_waka
        llullaillaco mayapan_holy_site pyramid_magician quewar quri_kancha temple_jaguar
        temple_kukulkan teotihuacan_temple_holy_site titikaka tollan_holy_city
        waka_pukllana wayna_qhari
        """,
    )
    add("common/languages", KEEP, "name", "english_language korean_language")
    add("common/on_action", KEEP, "positional", "on_exploration_success weather_monthly_pulse")
    add("common/on_action", REBIND, "culture", "on_game_start", "N1")
    add(
        "common/scripted_country_names",
        REPLACE,
        "identity",
        """
        jamaica_scripted_country_name new_amsterdam_scripted_country_name
        new_granada_scripted_country_name new_spain_scripted_country_name
        new_york_scripted_country_name nova_scotia_scripted_country_name
        peru_scripted_country_name rio_de_la_plata_scripted_country_name
        """,
        "N4",
    )
    add("common/scripted_effects", KEEP, "positional", "setup_area_preferences")
    add(
        "common/scripted_geography",
        KEEP,
        "generic",
        "island_of_cuba_geography pacific_coast_americas_geography",
    )
    add("common/scripted_geography", NEUTRALIZE, "canal", "panama_canal_footprint")
    add(
        "common/scripted_triggers",
        KEEP,
        "positional",
        """
        is_capital_in_south_america
        is_capital_in_south_america_or_carribean is_capital_mesoamerica
        """,
    )
    add("common/scripted_triggers", REBIND, "coast", "discovered_any_in_americas_trigger", "S2")
    # D009's fleet uses coastal province identities; the geographic remap carries them.
    add("common/scripted_triggers", KEEP, "generic", "is_on_pacific_coast_americas")
    add(
        "common/situations",
        KEEP,
        "positional",
        "great_pestilence little_ice_age treaty_of_tordesillas",
    )
    add(
        "common/tests",
        KEEP,
        "positional",
        "british_start_thirteen_colonies spanish_presence_in_latin_america",
    )


def _elsewhere(table: _Table) -> None:
    """Rows of the map objects and the main menu."""
    add = table.add
    add("gfx/map", KEEP, "generic", "dynamic_game_object")
    add("gfx/map", NEUTRALIZE, "canal", "panama_canal")
    add("gfx/images", NEUTRALIZE, "illustration", "d015_monuments1 d017_sacred_sites")
    add("menu/achievements", KEEP, "positional", "plus_ultra what_a_great_guy")
    add("menu/achievements", NEUTRALIZE, "canal", "divide_the_land")
    add("menu/coat_of_arms", KEEP, "positional", "colored_emblem_texture_lists")


def _events(table: _Table) -> None:
    """Rows of the events: generic ones stay, those naming American history go."""
    add = table.add
    add(
        "events",
        KEEP,
        "generic",
        """
        earthquake_events.19 earthquake_events.21 earthquake_events.29
        earthquake_events.32 earthquake_events.33 earthquake_events.44
        earthquake_events.45 earthquake_events.48 earthquake_events.51
        earthquake_events.52 earthquake_events.53 earthquake_events.54
        earthquake_events.62 earthquake_events.63 earthquake_events.64
        earthquake_events.70 earthquake_events.71 earthquake_events.74
        earthquake_events.77 earthquake_events.78 earthquake_events.82
        earthquake_events.84 earthquake_events.85 earthquake_events.88
        circumnavigation_expedition_events.20 pacific_crossing_events.6
        pacific_crossing_events.9 exploration_monthly.39 qa_debug.29
        great_pirate_era.1 great_pirate_era.5 great_pirate_era.6 flavor_ned.7
        seven_cities.30 seven_cities_norumbega.11 seven_cities_quivira.10
        seven_cities_saguenay.2 seven_cities_saguenay.3
        seven_cities_saguenay.10 seven_cities_saguenay.11
        """,
    )
    add(
        "events",
        KEEP,
        "positional",
        """
        flavor_cas.105 flavor_cas.125 flavor_kni.12 flavor_kni.15 flavor_kni.1000
        flavor_kni.2000 flavor_por.8 flavor_por.26 republics.15
        """,
    )
    add(
        "events",
        NEUTRALIZE,
        "identity",
        """
        flavor_cas.106 flavor_cas.107 flavor_cas.108 flavor_cas.109 flavor_cas.120
        flavor_cas.146 flavor_cas.2500 flavor_cas.35 flavor_cas.36 flavor_cas.37
        flavor_cas.64 flavor_cas.86 flavor_cas.87 flavor_cas.88 flavor_eng.137
        flavor_eng.140 flavor_eng.147 flavor_eng.152 flavor_eng.159 flavor_eng.162
        flavor_eng.167 flavor_eng.177 flavor_eng.181 flavor_eng.182 flavor_eng.186
        flavor_eng.214 flavor_eng.234 flavor_fra.313 flavor_dan.28 flavor_rus.41
        flavor_sco.17 flavor_tur.73 flavor_kni.13 flavor_kni.14 flavor_por.10
        flavor_por.72 flavor_por.73 flavor_por.74 flavor_por.75 flavor_por.76
        flavor_por.77 flavor_iro.30 flavor_iro.31 flavor_iro.32 flavor_iro.62
        flavor_iro.63 flavor_iro.64 prices.10 prices.15
        d009_sephardi_diaspora.8
        """,
    )
    # The silver and Potosi chain: the exceptional places of N1 carry the purpose.
    add(
        "events",
        REPLACE,
        "identity",
        "flavor_cas.110 flavor_cas.111 flavor_cas.112 flavor_cas.113",
        "N1",
    )
    # The road to independence and the colonial rebellion: a colony that becomes a country.
    add(
        "events",
        REPLACE,
        "identity",
        """
        flavor_cas.2700 flavor_cas.2701 flavor_cas.2702 flavor_eng.224 flavor_eng.233
        flavor_eng.235 flavor_eng.242
        """,
        "N4",
    )
    # The founding of a federation; its events are unreachable once USA_f is gone.
    add(
        "events",
        REPLACE,
        "identity",
        " ".join(f"flavor_usa.{number}" for number in (*range(1, 21), 1000)),
        "N4",
    )
    add("events", REPLACE, "identity", "nahuatl_events.30", "N3")
    # A plain event with a retired tag in its trigger, and the helpers of the retired chains.
    add("events", REPLACE, "inert", "flavor_chk.32", "N3")
    add(
        "events",
        NEUTRALIZE,
        "inert",
        "is_valid_cahokia_raider_country is_huron_country is_iroquois_country",
    )


# What carries the purpose of an object the exporter retires, by the start of its identifier.
RETIRED_STAGES: Final[Mapping[str, Mapping[str, str]]] = {
    "events": {
        "flavor_chk.": "N3",
        "flavor_azt.": "N3",
        "flavor_csu.": "N3",
        "flavor_iro.": "N4",
        "flavor_pue.": "N4",
    },
    "menu/static_modifiers": {
        "chk_": "N3",
        "mexica_": "N3",
        "renewal_of_life": "N3",
        "iro_": "N4",
        "pue_": "N4",
        "guanajuato_base": "N1",
        "huancavelica_base": "N1",
        "newfoundland_fishing_grounds_base": "N1",
        "potosi_base": "N1",
        "zacatecas_base": "N1",
    },
}


@dataclass(frozen=True, slots=True)
class Carrier:
    """What carries the purpose of a replaced object in the generated world, and how far.

    ``families`` are the stories, formables and other generated content of the same kind
    (``content.FAMILIES``, ``stories.STORIES``, ``eu5_places``, ``colonial_names``); empty
    when nothing carries it, and then ``note`` says why in its first words (``none:``).
    A carrier is a design relation [INFERRED], never an equivalence: a family tells a story of
    the same kind about places and states of the generated world.
    """

    families: tuple[str, ...]
    note: str


PLACES: Final = "exceptional_places"
NAMES: Final = "colonial_names"
NONE: Final = ()


class _Carriers:
    """The rows being written; a replaced object is carried once."""

    def __init__(self) -> None:
        self.rows: dict[str, Carrier] = {}

    def add(self, category: str, idents: str, families: tuple[str, ...], note: str) -> None:
        """Say what carries the objects named in ``idents`` (separated by whitespace)."""
        for ident in idents.split():
            key = f"{category}:{ident}"
            if key in self.rows:
                message = f"Two carriers for {key}"
                raise ValueError(message)
            self.rows[key] = Carrier(families, note)


def _carriers() -> dict[str, Carrier]:
    table = _Carriers()
    add = table.add
    modifiers = "menu/static_modifiers"
    add(
        modifiers,
        """
        guanajuato_base huancavelica_base newfoundland_fishing_grounds_base potosi_base
        zacatecas_base
        """,
        (PLACES,),
        "the five natural bonuses, each a place of the generated land with the vanilla size",
    )
    add(
        "events",
        "flavor_cas.110 flavor_cas.111 flavor_cas.112 flavor_cas.113",
        (PLACES,),
        "the deposits only; the events about the mita and the discoverer have no story",
    )
    add(
        "common/generic_actions",
        "pilgrimage_to_cholula",
        ("sacred_centre",),
        "a journey to a holy centre is the first node of the sacred centre",
    )
    add(
        "events",
        "nahuatl_events.30",
        ("sacred_centre",),
        "a journey to a holy centre is the first node of the sacred centre",
    )
    add(
        "common/estate_privileges",
        "hurin_qusqu_privilege",
        ("sacred_centre",),
        "the high priesthood's seat is the sacred centre's estate privilege",
    )
    add(
        "common/building_types",
        "great_temple_of_tenochtitlan",
        ("sacred_centre",),
        "the temple's effect is a location modifier of the sacred centre, not a building",
    )
    chk = (*range(1, 13), *range(20, 25), *range(30, 36))
    add(
        "events",
        " ".join(f"flavor_chk.{number}" for number in chk),
        ("river_centre",),
        "a river city that floods, hungers and rebuilds is the river centre",
    )
    add(
        modifiers,
        """
        chk_exodus_of_cahokia chk_food_conditions_horrific chk_fortifying_center
        chk_funding_new_woodhenge_expansion chk_funding_woodhenge_restoration
        chk_maize_cravings_mod chk_new_golden_age chk_new_urban_planning
        chk_nixtamalized_maize_practice_reintroduced chk_outer_cahokia_growth
        chk_outer_cahokia_protected_flooding chk_over_reliance_on_maize
        chk_preservation_of_cahokia chk_protection_against_flooding chk_rebuilding_woodhenge
        chk_reintroduction_of_nixtamalization chk_restricted_construction
        chk_return_of_political_elite chk_river_water_polluted chk_shadow_of_cahokia_city
        chk_venerated_ruler chk_warbands_for_food_aggression
        """,
        ("river_centre",),
        "the payloads are copied under the river centre's own names",
    )
    add(
        "events",
        """
        flavor_azt.70 flavor_azt.90 flavor_azt.110 flavor_azt.200 flavor_azt.220
        flavor_azt.230 flavor_azt.240
        """,
        ("sacred_centre", "harvest", "great_alliance", "empire_periphery"),
        (
            "a great pyramid, a famine year, a triple alliance and a tribute empire have "
            "stories of their own kind"
        ),
    )
    add(
        "events",
        "flavor_azt.80 flavor_azt.120 flavor_azt.160",
        NONE,
        "none: a named ruler, a legal reform and a dynasty, told by persons",
    )
    add(
        "events",
        "flavor_azt.130 flavor_azt.140 flavor_azt.150",
        NONE,
        "none: the game has diseases of its own, and a second set would only repeat them",
    )
    add(
        "events",
        "flavor_azt.170 flavor_azt.180 flavor_azt.190",
        NONE,
        "none: the fifty-two-year cycle is a calendar of one people",
    )
    add(
        modifiers,
        """
        mexica_period_of_expansion_modifier mexica_period_of_passive_growth_modifier
        mexica_period_of_stability_modifier renewal_of_life
        """,
        NONE,
        "none: the payloads of the cycle that no family tells",
    )
    add(
        "events",
        """
        flavor_csu.200 flavor_csu.201 flavor_csu.202 flavor_csu.210 flavor_csu.211
        flavor_csu.212 flavor_csu.213
        """,
        NONE,
        "none: a war of succession and a conquest told by named persons",
    )
    add(
        "events",
        "flavor_iro.2 flavor_iro.3 flavor_iro.10 flavor_iro.13 flavor_iro.15",
        ("great_alliance",),
        (
            "a council of neighbouring peoples and the right to lead it is the great alliance; "
            "the legends of its founders have no person in the generated world"
        ),
    )
    add(
        "events",
        "flavor_iro.46 flavor_iro.47",
        ("harvest",),
        "a shared harvest and the keepers of the fields are the harvest story",
    )
    add(
        modifiers,
        "iro_earn_tribal_trust iro_seek_to_integrate iro_too_aggressive_consolidation",
        ("great_alliance",),
        "the payloads are copied under the great alliance's own names",
    )
    add(
        modifiers,
        """
        iro_matriarchal_agriculture iro_sharing_of_three_sisters_harvest
        iro_three_sisters_harvest
        """,
        ("harvest",),
        "the payloads are copied under the harvest's own names",
    )
    add(
        "events",
        "flavor_pue.101",
        ("route_market",),
        "a road between towns is the route and market",
    )
    add(
        "events",
        "flavor_pue.102 flavor_pue.103 flavor_pue.104 flavor_pue.105",
        ("harvest",),
        "irrigation and the return to ancestral seats are the new fields and the villages",
    )
    add(
        "events",
        "flavor_pue.106",
        ("cultural_union",),
        "reuniting a culture group is the formable of related peoples",
    )
    add(
        modifiers,
        """
        pue_improve_capital_irrigation pue_maintain_inner_tribal_peace pue_mesa_verde_capital
        pue_mesa_verde_reclaimed pue_return_to_mesa_verde pue_the_sky_city pue_unifying_campaign
        """,
        ("harvest", "route_market", "cultural_union"),
        "the payloads are copied under the new stories' own names",
    )
    add(
        "common/country_interactions",
        "form_closer_bond_iroquois merge_tribe_iroquois",
        NONE,
        "none: interactions between named peoples; the formables join states by decision",
    )
    add(
        "common/decisions",
        "iro_iroquois_interactions_decision",
        ("great_alliance",),
        "the decision that binds a league's peoples is the great alliance's council",
    )
    add(
        "common/formable_countries",
        "CAN_f MEX_f USA_f",
        ("postcolonial_federation",),
        "the federation of a colonial shore replaces the colonial formables of every settlers",
    )
    add(
        "events",
        " ".join(f"flavor_usa.{number}" for number in (*range(1, 21), 1000)),
        ("postcolonial_federation", "colony"),
        (
            "the formable carries the nation and the colony the road to independence; the "
            "founding steps, buildings and persons have no counterpart"
        ),
    )
    add(
        "common/scripted_country_names",
        """
        jamaica_scripted_country_name new_amsterdam_scripted_country_name
        new_granada_scripted_country_name new_spain_scripted_country_name
        new_york_scripted_country_name nova_scotia_scripted_country_name
        peru_scripted_country_name rio_de_la_plata_scripted_country_name
        """,
        (NAMES,),
        "a colony's name is the region's generated name after its founders' word for new",
    )
    add(
        "events",
        """
        flavor_cas.2700 flavor_cas.2701 flavor_cas.2702 flavor_eng.224 flavor_eng.233
        flavor_eng.235 flavor_eng.242
        """,
        ("colony",),
        "the colonial rebellion chain is the colony story's road to independence",
    )
    return table.rows


def _table() -> dict[str, Verdict]:
    table = _Table()
    _common(table)
    _elsewhere(table)
    _events(table)
    return table.rows


TABLE: Final[Mapping[str, Verdict]] = _table()
CARRIERS: Final[Mapping[str, Carrier]] = _carriers()


def _regional_table() -> dict[str, Verdict]:
    """Decisions that apply when Africa or Oceania is generated."""
    table = _Table()
    add = table.add
    add("common/advances", NEUTRALIZE, "suez", "suez_canal_advance")
    add(
        "common/advances",
        KEEP,
        "positional",
        """
        african_sturdy_grains_advance baghlah_advance bound_by_service community_of_the_faithful
        courtly_competition eastern_african_trade expanded_grazing_grounds expanded_slave_trade
        gifts_and_hostages intercontinental_trade iron_working land_of_the_ancestors
        mining_tradition nomadic_tendencies overnight_army people_of_ornaments ranching
        regnal_chronicles saquiyah skilled_cavalry_raids the_sahel_trade unlock_dhow unlock_galiot
        wandering_scholars
        """,
    )
    add(
        "common/decisions",
        NEUTRALIZE,
        "suez",
        "build_suez_canal close_suez_canal_to_enemies open_suez_canal_to_all",
    )
    add("common/scripted_geography", NEUTRALIZE, "suez", "suez_canal_footprint")
    add("gfx/map", NEUTRALIZE, "suez", "suez_canal")
    add(
        "common/area_preferences",
        KEEP,
        "positional",
        """
        castile_conquer_maghreb dutch_explore_cape_route dutch_explore_gold_coast
        england_explore_india ethiopia_colonization ethiopia_conquest explore_african_coast
        ottoman_expansion_crescent_egypt ottoman_expansion_maghreb
        """,
    )
    add(
        "common/holy_sites",
        KEEP,
        "homeland",
        """
        alexandria_episcopal_see alexandria_holy_city_gnostic andalusian_mosque_fez
        koutoubia_marrakesh_holy_site mosque_of_uqba_kairouan moulay_idriss_zerhoun
        oracle_of_ammon_holy_site qarawiyyin_fez_holy_site saint_katrine_monastery
        serapeum_holy_site sidi_bou_said sidi_boumediene_tlemcen tin_mal_mosque zaytuna_tunis
        """,
    )
    add("common/diseases", KEEP, "positional", "bubonic_plague egyptian_plague")
    add("common/goods", KEEP, "positional", "camels")
    add(
        "common/formable_countries",
        REBIND,
        "culture",
        """
        AIR_f ALG_f BEJ_f ETH_f HAU_f KON_f MAL_f MIR_f
        MOR_f MSI_f NTR_f NUB_f SKO_f SOI_f TRG_f TUN_f
        """,
    )
    add("common/formable_countries", KEEP, "positional", "CTH_f EGY_f KOA_f ROM_f")
    add("common/formable_countries", KEEP, "inert", "DAH_f")
    add(
        "common/building_types",
        KEEP,
        "positional",
        """
        caravan_stop fulani_cattle_rearing_pen funduq maghreb_palm_irrigation slave_center
        trans_saharan_trade_outposts
        """,
    )
    add(
        "common/building_types",
        NEUTRALIZE,
        "identity",
        """
        ablaq_palace great_enclosure great_hill_complex great_valley_complex
        monument_bou_inania_madrasa monument_chellah monument_dar_al_makhzen
        monument_great_mosque_algiers monument_hassan_tower monument_kairouan_mosque
        monument_kasbah_udayas monument_ksar_ait_benhaddou monument_mansourah_tlemcen
        monument_qarawiyyin qalat_al_mashwar walls_of_benin
        """,
    )
    add("common/decisions", NEUTRALIZE, "identity", "mam_ablaq_palace_decision")
    add("common/decisions", KEEP, "lost", "hafsid_caliphate_decision")
    add("common/decisions", KEEP, "positional", "maghreb_masters_of_the_sahara oran_fatwa_decision")
    add(
        "common/expedition_types",
        KEEP,
        "positional",
        "cape_route_to_india_expedition hajj_caravan_expedition pilgrimage_expedition",
    )
    add(
        "common/area_preferences",
        KEEP,
        "positional",
        "portugal_explore_middle_east timurids_anatolian_conquest",
    )
    add("common/cabinet_actions", KEEP, "positional", "oma_zanzibar_integration")
    add("common/casus_belli", KEEP, "positional", "cb_free_the_mudejar")
    add("common/advances", KEEP, "generic", "arm_highland_fortresses")
    add("common/customizable_localization", KEEP, "generic", "country_name_construction")
    add("common/international_organizations", KEEP, "positional", "ilkhanate")
    add("common/religious_order_types", KEEP, "positional", "iberian_military_order_type")
    add("common/script_values", KEEP, "positional", "bfts_gra_strait_maritime_pull")
    add("common/script_values", KEEP, "generic", "slave_market_max_level")
    add(
        "common/situations",
        KEEP,
        "positional",
        "battle_for_the_strait golden_century rise_of_timur",
    )
    add(
        "common/tests",
        KEEP,
        "positional",
        "early_colonization_started ottoman_empire_important_locations portugese_south_africa",
    )
    add("common/unit_types", KEEP, "positional", "a_bedouin_cavalry")
    add("gfx/images", KEEP, "illustration", "d009_monuments")
    add("menu/dlc", KEEP, "generic", "across_the_pillars")
    add(
        "menu/scripted_triggers",
        KEEP,
        "positional",
        "coa_def_african_colonies_trigger coa_def_bars_crescents_flag_trigger",
    )
    add(
        "common/scripted_geography",
        KEEP,
        "positional",
        """
        caliphate_of_cordoba_geography d009_maghreb_coastal_geography
        gafsa_sphere_of_influence_geography ibadi_heartland_of_the_maghreb ifriqiya_geography
        justinian_borders_geography mare_nostrum_geography mediterranean_sea_geography
        roman_borders_geography sahara_desert_geography sahel_gold_geography
        umayyad_caliphate_geography umayyad_reconquest_geography
        """,
    )
    add(
        "common/scripted_triggers",
        KEEP,
        "positional",
        """
        artillery_institution_plausible_location banking_plausible_location
        confessionalism_plausible_location discovered_route_to_india
        enlightenment_plausible_location global_trade_plausible_location
        hajj_caravan_routes_via_bab_el_mandeb hajj_caravan_routes_via_cairo
        hajj_caravan_routes_via_jeddah industrialization_plausible_location
        is_endemic_bubonic_plague_location is_endemic_typhus_location
        manufactories_plausible_location military_revolution_plausible_location
        new_world_plausible_location pike_and_shot_plausible_location
        scientific_revolution_plausible_location unit_camelry_region_trigger
        unit_moa_hunter_location_trigger
        """,
    )
    _regional_society(table)
    _regional_events(table)
    _retired_morocco(table)
    return table.rows


def _regional_society(table: _Table) -> None:
    add = table.add
    add(
        "common/scripted_country_names",
        KEEP,
        "positional",
        """
        new_south_wales_scripted_country_name new_zealand_scripted_country_name
        swan_river_colony_scripted_country_name
        """,
    )
    add("common/historical_scores", KEEP, "country_gate", "hs_mansa_musa")
    add(
        "common/generic_actions",
        KEEP,
        "positional",
        """
        adu_charter_saharan_trade_house cross_the_strait launch_a_cabalgada
        legacy_of_rustamids move_ow_good_to_new_location petition_for_the_bula_de_cruzada
        proclaim_the_ghazw raid_the_shores rot_select_core_region summon_volunteers_of_the_faith
        """,
    )
    add(
        "common/estate_privileges",
        KEEP,
        "positional",
        "local_tribal_strongholds maghrebi_zawiya_endowment mellah_charter",
    )
    add(
        "common/laws",
        KEEP,
        "positional",
        "amazigh_familial_connections bayaa_succession_law legal_code_law piracy_law",
    )
    add("common/laws", KEEP, "generic", "maritime_law medieval_levy_law mining_law")
    add(
        "common/on_action",
        KEEP,
        "positional",
        "maghrebi_location_conversion on_location_changed_owner on_pre_winning_war",
    )
    add("common/on_action", KEEP, "generic", "on_location_occupied on_siege_won")
    add("common/scripted_relations", KEEP, "positional", "parias_payments")
    add(
        "common/town_rights",
        KEEP,
        "positional",
        "guich_charter_town_rights sale_arsenal_town_rights",
    )
    add("common/languages", KEEP, "name", "korean_language")
    add(
        "common/scripted_triggers",
        KEEP,
        "positional",
        """
        can_summon_iberian_military_orders controls_and_owns_pentarchy has_all_pentarchy
        has_all_pentarchy_except has_pentarchy_modifier is_geographically_correct
        is_pentarchy_seat rustamid_legacy_trigger
        """,
    )
    add("common/scripted_triggers", KEEP, "country_gate", "is_hafsid_governor_trigger")
    add(
        "common/scripted_effects",
        KEEP,
        "positional",
        """
        add_all_possible_pentarchies add_pentarchy_modifier enable_treasure_voyages
        remove_pentarchy_modifier
        """,
    )
    add("common/scripted_effects", NEUTRALIZE, "absent_start", "maghreb_set_up")
    add(
        "common/scripted_effects",
        KEEP,
        "positional",
        """
        create_familial_governor_in_location_effect hafsid_succession_effect
        hafsid_succession_unite_two_countries
        """,
    )
    add("common/decisions", KEEP, "positional", "tur_eunuch_viziers_decision")
    add("common/decisions", NEUTRALIZE, "identity", "zan_husuni_kubwa_decision")
    add("common/estate_privileges", KEEP, "country_gate", "control_over_the_coinage")
    add("common/estate_privileges", KEEP, "positional", "kbo_lake_chad_trade_privilege")
    add(
        "common/government_reforms",
        KEEP,
        "country_gate",
        "zimbabwe_royal_cattle_control zmw_council_of_senior_wives",
    )
    add("common/government_reforms", KEEP, "lost", "INJECT:tle_support_of_banu_al_wad")
    add("common/parliament_types", KEEP, "country_gate", "ahl_al_hall_wal_aqd_parliament")
    add(
        "common/rebel_demands",
        KEEP,
        "inert",
        "rebel_demand_flavor_zmw_1 rebel_demand_flavor_zmw_2",
    )
    add(
        "menu/achievements",
        KEEP,
        "positional",
        "endured_atlas getting_things_strait holy_flush saladin_legacy",
    )
    add("menu/achievements", KEEP, "country_gate", "african_trade family_matters")


def _regional_events(table: _Table) -> None:
    """Keep events with living regional gates and retire accounts of lost places."""
    add = table.add
    add(
        "events",
        KEEP,
        "positional",
        """
        d009_morisco_diaspora.2 d009_morisco_diaspora.3 d009_morisco_diaspora.5
        d009_morisco_diaspora.8 d009_morisco_diaspora.10
        d009_sephardi_morocco.1 d009_sephardi_morocco.2 d009_sephardi_morocco.3
        d009_sephardi_morocco.4 d009_sephardi_morocco.6 d009_sephardi_morocco.7
        d009_sephardi_morocco.8 d009_sephardi_morocco.9 d009_sephardi_morocco.10
        flavor_por.9 flavor_por.11 flavor_por.29 flavor_por.31 flavor_por.51
        flavor_por.55 flavor_por.60 flavor_por.61 flavor_por.64
        flavor_mor.12 flavor_mor.16 flavor_mor.18 flavor_mor.27 flavor_mor.28 flavor_mor.1100
        flavor_mam.15 flavor_mam.30 flavor_mam.39 flavor_mam.44 flavor_mam.48
        flavor_mam.53 flavor_mam.54 flavor_mam.55 flavor_mam.70
        flavor_tur.10 flavor_tur.17 flavor_tur.22 flavor_tur.23 flavor_tur.24 flavor_tur.25
        flavor_tur.79 flavor_tur.106 flavor_tur.107 flavor_tur.145
        flavor_tur.149 flavor_tur.150 flavor_tur.204 flavor_tur.213
        """,
    )
    add(
        "events",
        NEUTRALIZE,
        "identity",
        """
        flavor_mam.2 flavor_mam.8 flavor_mam.23 flavor_mam.27 flavor_mam.33 flavor_mam.34
        flavor_mam.36 flavor_mam.37 flavor_mam.40 flavor_mam.41 flavor_mam.45 flavor_mam.58
        flavor_mam.59 flavor_mam.61 flavor_mam.78 flavor_mam.79 flavor_mam.100
        flavor_mor.1 flavor_mor.4 flavor_mor.24 flavor_mor.25 flavor_mor.33
        flavor_tur.78 flavor_tur.182
        """,
    )
    _regional_diplomacy_events(table)


def _regional_diplomacy_events(table: _Table) -> None:
    add = table.add
    add(
        "events",
        KEEP,
        "positional",
        """
        battle_for_the_strait_events.3 battle_for_the_strait_events.4
        cache_locations_in_maghreb_for_andalusian_migration
        cape_route_to_india_events.2 cape_route_to_india_events.3 cape_route_to_india_events.15
        cape_route_to_india_events.28 cape_route_to_india_events.29
        flavor_cas.1001 flavor_cas.1002 flavor_cas.1005 flavor_cas.1600 flavor_cas.1601
        flavor_eng.155 flavor_eng.156 flavor_eng.216 flavor_eng.226 flavor_eng.227 flavor_eng.236
        flavor_eng.239 flavor_eng_diplomacy.1300
        flavor_gra.1 flavor_gra.16 flavor_gra.1200
        flavor_kni.3 flavor_kni.17 flavor_ned.6 flavor_oma.5 flavor_oma.11
        flavor_mor_maghrebi_wars.1001 flavor_mor_maghrebi_wars.1004 flavor_mor_maghrebi_wars.1100
        flavor_ven.30 flavor_ven.79 flavor_ven.1000 flavor_ven.1001
        flavor_ven_tur_conflict.1000 flavor_ven_tur_conflict.1001 flavor_ven_tur_conflict.1002
        golden_century_events.43 great_pirate_era.2 great_pirate_era.3 great_pirate_era.4
        is_barbary_state maghrebi_cultural_change_events.1004
        maghrebi_culture.3 maghrebi_culture.4 maghrebi_culture.6 maghrebi_culture.7
        maghrebi_culture.8 maghrebi_culture.10 maghrebi_culture.11 maghrebi_culture.12
        maghrebi_culture.13 maghrebi_culture.18 maghrebi_culture.20 maghrebi_culture.22
        maghrebi_culture.23 maghrebi_culture.24 maghrebi_culture.25 maghrebi_culture.26
        maghrebi_culture.27 maghrebi_culture.28
        miaphysite_flavor.1 miaphysite_flavor.3 miaphysite_flavor.9 miaphysite_flavor.11
        miaphysite_flavor.13 miaphysite_flavor.15 miaphysite_flavor.31
        pacific_crossing_events.2 pacific_crossing_events.19 pacific_crossing_events.20
        western_ocean_voyage_events.2
        """,
    )
    add(
        "events",
        NEUTRALIZE,
        "identity",
        """
        earthquake_events.9 earthquake_events.38 earthquake_events.41 earthquake_events.56
        flavor_eth.60
        """,
    )
    add(
        "events",
        KEEP,
        "positional",
        """
        decline_of_mali_12_location_trigger decline_of_mali_14_location_trigger
        decline_of_mali_15_location_trigger exceptional_gift_giraffe_trigger
        fall_of_delhi.20 fall_of_delhi.21 flavor_ara.39 flavor_dah.1 flavor_dah.2
        flavor_dan.1000 flavor_eth.90 flavor_flo.51 flavor_fra.2022
        flavor_gen_tun.1 flavor_gen_tun.2 flavor_gen_tun.3 flavor_ira.20 flavor_mll.11
        flavor_mos.109 flavor_tle.8 innovativeness_events.11 innovativeness_events.16
        location_sikhism_influence_areas mysticism_vs_jurisprudence.2 prices.1
        qa_debug.28 rise_of_timur.3 rise_of_timur.9 rise_of_timur.100
        """,
    )
    add(
        "events",
        KEEP,
        "country_gate",
        """
        GFS_ahmed_buffs crisis_of_the_sayfawa_dynasty.1 crisis_of_the_sayfawa_dynasty.6
        crisis_of_the_sayfawa_dynasty.7 decline_of_mali.8 flavor_kbo.12 flavor_mal.25
        flavor_tle.1 flavor_tle.2 flavor_tle.6 flavor_tun.7 flavor_zmw.1001
        """,
    )
    add(
        "events",
        NEUTRALIZE,
        "identity",
        """
        flavor_eth.201 flavor_eth.202 flavor_eth.203 flavor_eth.204 flavor_eth.210
        ibn_battuta_events.6
        """,
    )


def _retired_morocco(table: _Table) -> None:
    """Shared Andalusi mechanics and clauses guarded by the existence of Morocco."""
    add = table.add
    add("common/advances", KEEP, "generic", "gra_taifa_subjects")
    add("common/ai_scripted_expansion_score", KEEP, "generic", "castile_spares_christian_iberia")
    add(
        "common/ai_scripted_expansion_target",
        KEEP,
        "generic",
        "bfts_contest_granada castile_contest_moroccan_iberia",
    )
    add("common/building_types", KEEP, "generic", "qadi_office saharan_trade_house")
    add(
        "common/bureaucracies",
        KEEP,
        "generic",
        "dar_al_tiraz_bureaucracy qadi_al_jamaa_bureaucracy",
    )
    add("common/cabinet_actions", KEEP, "generic", "cas_pressure_andalusi_court")
    add("common/casus_belli", KEEP, "generic", "cb_demand_andalusi_submission")
    add("common/country_interactions", KEEP, "generic", "cas_demand_war_entry")
    add("common/decisions", KEEP, "generic", "gc_decision")
    add("common/expedition_types", KEEP, "generic", "gold_caravan_expedition")
    add(
        "common/generic_actions",
        KEEP,
        "generic",
        """
        adu_build_qadi_office adu_dispatch_gold_caravan adu_integrate_natives adu_muster_the_ghuzat
        adu_proclaim_a_fatwa adu_proclaim_crown_al_andalus cas_reduce_granadan_sovereignty
        claim_andalusi_inheritance gra_reduce_moroccan_influence invoke_ummayad_legacy
        spa_enforce_conformity
        """,
    )
    add(
        "common/generic_actions",
        KEEP,
        "country_gate",
        """
        mor_attract_andalusi_craftsmen mor_force_tribute mor_garrison_granadan_strongholds
        mor_invite_granadan_advisor mor_invite_granadan_scholars mor_vassalize_granada
        """,
    )
    add("common/on_action", KEEP, "generic", "on_ending_war")
    add("common/peace_treaties", KEEP, "generic", "peace_andalusi_submission")
    add("common/religious_schools", KEEP, "lost", "isawiyya_school")
    add("common/scripted_diplomatic_objectives", KEEP, "generic", "bfts_court_granada")
    add("common/scripted_effects", KEEP, "generic", "bfts_seed_subject_year_count_effect")
    add(
        "common/scripted_triggers",
        KEEP,
        "generic",
        """
        battle_for_the_strait_castile_holds_the_strait battle_for_the_strait_contender_eliminated
        battle_for_the_strait_morocco_holds_the_strait
        battle_for_the_strait_morocco_requirements_met can_demand_andalusi_submission
        has_ascendancy_over_granada is_battle_for_the_strait_principal
        """,
    )
    add("common/subject_types", KEEP, "generic", "tributary")
    add("common/tests", KEEP, "generic", "morocco_has_left_iberia")
    add("common/town_rights", KEEP, "generic", "taifa_al_rais_town_rights")
    add("gfx/images", KEEP, "generic", "d009_golden_century_illustration")
    add("menu/achievements", KEEP, "generic", "crossing_the_pillars")
    add("menu/scripted_triggers", KEEP, "country_gate", "coa_def_MOR_ensign_trigger")
    add(
        "events",
        KEEP,
        "generic",
        """
        battle_for_the_strait_events.1 battle_for_the_strait_events.5 battle_for_the_strait_events.8
        battle_for_the_strait_events.31 battle_for_the_strait_events.40
        battle_for_the_strait_events.43 battle_for_the_strait_events.44
        battle_for_the_strait_events.56 battle_for_the_strait_events.60
        battle_for_the_strait_events.61
        d009_convivencia.1 d009_iberian_order_events.53 d009_sephardi_catastrophe.1
        flavor_cas.15 flavor_cas.152 flavor_gra.15 flavor_tur.1300
        golden_century_events.1 golden_century_events.2 golden_century_events.3
        golden_century_events.6 golden_century_events.24 golden_century_events.25
        golden_century_events.26 golden_century_events.27 golden_century_events.28
        golden_century_events.33 golden_century_events.40 golden_century_events.41
        golden_century_events.42 golden_century_events.44 golden_century_events.45
        golden_century_events.46 golden_century_events.47 golden_century_events.48
        golden_century_events.49
        """,
    )
    add(
        "events",
        NEUTRALIZE,
        "identity",
        """
        flavor_cas_rio_salado.1 flavor_cas_rio_salado.3 flavor_cas_rio_salado.4
        flavor_cas_rio_salado.5 flavor_mor.37 ibn_battuta_events.7
        """,
    )


REGIONAL_TABLE: Final[Mapping[str, Verdict]] = dict(TABLE) | _regional_table()


def decide(
    consumer: Consumer, tags: frozenset[str], table: Mapping[str, Verdict] = TABLE
) -> Verdict | None:
    """The decision for ``consumer``: its row, else the rule that covers it, else none.

    ``tags`` are the retired tags. A definition keyed by one is inert. An object the
    exporter retires is neutralized, or replaced where a later stage carries its purpose.
    """
    row = table.get(consumer.key)
    if row is not None:
        return row
    if consumer.ident in tags:
        return Verdict(KEEP, "inert")
    if consumer.retired:
        for start, stage in RETIRED_STAGES.get(consumer.category, {}).items():
            if consumer.ident.startswith(start):
                return Verdict(REPLACE, "retired", stage)
        return Verdict(NEUTRALIZE, "retired")
    return None


def missing(
    consumers: Iterable[Consumer], tags: frozenset[str], table: Mapping[str, Verdict] = TABLE
) -> list[str]:
    """Keys of the consumers without a decision."""
    return sorted(c.key for c in consumers if decide(c, tags, table) is None)


def stale(consumers: Iterable[Consumer], table: Mapping[str, Verdict] = TABLE) -> list[str]:
    """Keys of the rows that no consumer matches any more."""
    return sorted(table.keys() - {c.key for c in consumers})
