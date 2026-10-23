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
        settle_the_frontier_advance shared_brotherhood shared_knowledge slash_and_burn
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
    add("common/building_types", REPLACE, "retired", "great_temple_of_tenochtitlan", "N3")
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
        discovered_any_in_americas_trigger is_capital_in_south_america
        is_capital_in_south_america_or_carribean is_capital_mesoamerica
        """,
    )
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


def _table() -> dict[str, Verdict]:
    table = _Table()
    _common(table)
    _elsewhere(table)
    _events(table)
    return table.rows


TABLE: Final[Mapping[str, Verdict]] = _table()


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
