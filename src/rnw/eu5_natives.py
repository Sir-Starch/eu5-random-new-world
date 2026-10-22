"""EU5 1.4.1 native start state for a generated New World (R6a).

NOT GAME VALIDATED. Calibrated on the vanilla 1337 Americas, read-only: tribal
population density per climate, population per land location, and the homeland of
every American culture and religion (pop-weighted climate, vegetation, topography,
latitude, coast and share living in states) [V-EXEC C67]. ``rnw.societies`` makes the
societies; each religion zone takes the unused vanilla American religion whose
homeland fits best, and each culture zone a culture of that religion. Countries get
new tags; their coats of arms are left to the engine, which already draws them for 635
vanilla tags without one [V-LOCAL C67].
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.eu5_biomes import latitude_tenths
from rnw.eu5_canvas import NEW_WORLD
from rnw.eu5_remap import remap_text
from rnw.model import CellClass
from rnw.names import MarkovNames, name_key
from rnw.pdx import Block, parse
from rnw.rng import SplitMix64, derive_seed, hash_grid
from rnw.societies import (
    CITY,
    PERMILLE,
    STATE,
    STEP_COST,
    LandGraph,
    Societies,
    generate_societies,
)

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

    from rnw.eu5_biomes import CellBiomes
    from rnw.eu5_map import Eu5Map
    from rnw.eu5_newworld import Plan, VanillaGeometry
    from rnw.geography import Location
    from rnw.loc_keys import KeySpace
    from rnw.newworld import NewWorld
    from rnw.settings import NativeSettings

SETUP: Final[str] = "game/main_menu/setup/1337"
TEMPLATE_DIR: Final[str] = "game/main_menu/setup/templates"
# Government fields a country entry adds when its template leaves the type open.
GOVERNMENT_FIELDS: Final[tuple[str, ...]] = ("type", "heir_selection")
COUNTRY_DIR: Final[str] = "game/in_game/setup/countries"
HOLY_SITE_DIR: Final[str] = "game/in_game/common/holy_sites"
NAMED_COLORS: Final[str] = "game/main_menu/common/named_colors/02_map.txt"
COUNTRY_NAME: Final[re.Pattern[str]] = re.compile(
    r'^\s*([A-Za-z0-9_]+):\d*\s+"([^"]*)"', re.MULTILINE
)
COUNTRY_NAMES: Final[str] = "game/main_menu/localization/english/country_names_l_english.yml"
LOCATION_NAMES: Final[str] = "game/main_menu/localization/english/location_names"
CULTURE_DIR: Final[str] = "game/in_game/common/cultures"
LANGUAGE_DIR: Final[str] = "game/in_game/common/languages"
NAME_LINE: Final[re.Pattern[str]] = re.compile(r'^ *([A-Za-z0-9_]+):\d* *"([^"]*)"', re.MULTILINE)
# A place-name corpus needs this many vanilla names; smaller ones back off from the
# language to its family, then to the culture's religion, then to the whole Americas.
MIN_CORPUS: Final[int] = 40
WASTELAND_SUFFIX: Final[str] = " Highlands"
DEFINITION_FILE: Final[str] = "in_game/setup/countries/rnw_natives.txt"
CLIMATES: Final[tuple[str, ...]] = (
    "arctic", "subpolar", "continental", "oceanic", "mediterranean", "subtropical",
    "tropical", "arid", "hot_semi_arid", "cold_arid", "cold_semi_arid",
)  # fmt: skip
VEGETATIONS: Final[tuple[str, ...]] = (
    "desert", "sparse", "grasslands", "farmland", "woods", "forest", "jungle",
)  # fmt: skip
TOPOGRAPHIES: Final[tuple[str, ...]] = ("flatland", "hills", "plateau", "mountains", "wetlands")
# Farming potential (permille) by template field [INFERRED design]: warm wet climates and
# open land farm best; cool tropical highlands farm like lowlands elsewhere; rivers
# lift dry land most (irrigation), coasts a little.
CLIMATE_FARMING: Final[dict[str, int]] = {
    "tropical": 900, "subtropical": 1000, "mediterranean": 1000, "oceanic": 800,
    "continental": 700, "hot_semi_arid": 600, "cold_semi_arid": 400, "arid": 300,
    "cold_arid": 200, "subpolar": 100, "arctic": 0,
}  # fmt: skip
VEGETATION_FARMING: Final[dict[str, int]] = {
    "farmland": 1000, "grasslands": 1000, "woods": 900, "sparse": 700, "forest": 700,
    "jungle": 600, "desert": 300,
}  # fmt: skip
TOPOGRAPHY_FARMING: Final[dict[str, int]] = {
    "flatland": 1000, "hills": 900, "plateau": 800, "wetlands": 500, "mountains": 400,
}  # fmt: skip
HIGHLAND_CLIMATES: Final[frozenset[str]] = frozenset({"tropical", "arid", "hot_semi_arid"})
HIGHLAND_FARMING: Final[dict[str, int]] = {"plateau": 1000, "mountains": 700}
RIVER_FARMING: Final[int] = 500
# Growing seasons shorten towards the poles: full potential up to 40 degrees, none at 65.
FARMING_LATITUDES: Final[tuple[int, int]] = (400, 650)
COAST_FARMING: Final[int] = 100
# Tribal density by topography relative to flatland [INFERRED; the vanilla fit gives
# mountains 3.0 only because of the Andes].
TOPOGRAPHY_DENSITY: Final[dict[str, int]] = {
    "flatland": 1000, "hills": 900, "plateau": 800, "wetlands": 800, "mountains": 600,
}  # fmt: skip
WATER_DENSITY: Final[int] = 1200
# Cost of entering a location, in steps of 1000.
TOPOGRAPHY_COST: Final[dict[str, int]] = {
    "flatland": 1000, "hills": 1300, "plateau": 1300, "wetlands": 1800, "mountains": 2500,
}  # fmt: skip
VEGETATION_COST: Final[dict[str, int]] = {"jungle": 500, "forest": 200, "desert": 700}
MATCH_NOISE: Final[int] = 200
# An unused candidate is taken over reusing a better one if it is at most this much worse.
MATCH_SLACK: Final[int] = 1000
# Elites in state capitals and burghers in towns, as (minimum milli-pops, per 10,000 of
# the location): vanilla capitals hold nobles 0.012-0.085 (0.7 per 10,000 of big ones),
# clergy 0.030-0.344 (about 25) and town burghers 2.4-10.7 (about 400) [V-EXEC C67].
NOBLES: Final[tuple[int, int]] = (15, 7)
CLERGY: Final[tuple[int, int]] = (30, 25)
BURGHERS: Final[tuple[int, int]] = (0, 400)
MYRIAD: Final[int] = 10_000
ELITES: Final[tuple[tuple[str, tuple[int, int]], ...]] = (("nobles", NOBLES), ("clergy", CLERGY))
DEFAULT_STATE: Final[str] = "amerindian_monarchy"
ADVANCED_STATE: Final[str] = "amerindian_advanced_monarchy_not_nahuatl"
DEFAULT_TRIBE: Final[str] = "amerindian_tribe"
DEFAULT_CITY: Final[str] = "mexican_city"
DEFAULT_TOWN: Final[str] = "south_east_woodlands_town"
ADVANCED_PERMILLE: Final[int] = 700
# Vanilla 1337 sets up 4 vassals among 223 American states (C70). The most populous 5%
# of states take up to three bordering states of their religion with under a third of
# their population as vassals.
OVERLORD_PERMILLE: Final[int] = 50
MAX_VASSALS: Final[int] = 3
VASSAL_SHARE: Final[int] = 3
COLOR_CHANNELS: Final[int] = 3
# EU5 logged every vassal of a lord whose template sets no starting technology (the
# default `amerindian_monarchy`, tribes) as invalid at the start, and none of the lords with
# a technology of at least 2 [V-GAME 1.4.2, C99]; vanilla's lords all have one. Overlords
# therefore come only from templates at the lowest technology level a vanilla lord has.
VASSAL_LORD: Final[re.Pattern[str]] = re.compile(
    r"first\s*=\s*(\w+)\s+second\s*=\s*\w+\s+subject_type\s*=\s*vassal"
)
# EU5 logs every enabled culture and religion without a pop in the setup [V-GAME 1.4.2,
# C95], and vanilla has none. Each one the zones did not take gets a small pop of its own
# in the zone whose homeland fits it best.
DIASPORA_MILLI: Final[int] = 50
NO_COAST: Final[str] = "_no_coast"
TAG_WORD: Final[re.Pattern[str]] = re.compile(r"(?<![A-Za-z0-9_])([A-Z]{3})(?![A-Za-z0-9_])")
OPERATORS: Final[frozenset[str]] = frozenset({"AND", "NOT", "NOR", "ALL", "ANY", "YES"})
LETTERS: Final[str] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
COLOR_TRIES: Final[int] = 6
COLOR_DEFINITION: Final[re.Pattern[str]] = re.compile(
    r"^\s*([A-Za-z0-9_]+)\s*=\s*(rgb|hsv360|hsv)\s*\{([^{}]*)\}", re.MULTILINE
)
COUNTRY_COLOR: Final[re.Pattern[str]] = re.compile(
    r"^\s*color\s*=\s*(?:(rgb|hsv360|hsv)\s*\{([^{}]*)\}|([A-Za-z0-9_]+))", re.MULTILINE
)


class NativesError(ValueError):
    """Vanilla native data is missing or inconsistent."""


@dataclass(frozen=True, slots=True)
class Culture:
    """A vanilla American culture: religion, homeland and the setups it used."""

    religion: str
    homeland: tuple[int, ...]
    population: int
    state_include: str
    tribe_include: str
    city_setup: str
    town_setup: str


@dataclass(frozen=True, slots=True)
class HolySite:
    """A holy site of a vanilla religion and its vanilla location."""

    name: str
    location: str
    religion: str
    importance: int


@dataclass(frozen=True, slots=True, eq=False)
class VanillaNatives:
    """Calibration read from the vanilla 1337 Americas."""

    density: dict[str, int]
    population_per_location: int
    cultures: dict[str, Culture]
    religions: dict[str, tuple[tuple[int, ...], int]]
    templates: frozenset[str]
    reserved_tags: frozenset[str]
    holy_sites: tuple[HolySite, ...]
    places: tuple[tuple[str, str], ...] = ()
    languages: dict[str, tuple[str, str]] = field(default_factory=dict)
    reserved_names: frozenset[str] = frozenset()
    governments: dict[str, tuple[tuple[str, str], ...]] = field(default_factory=dict)
    colors: frozenset[tuple[int, int, int]] = frozenset()
    levels: dict[str, int] = field(default_factory=dict)
    overlord_level: int = 0


@dataclass(frozen=True, slots=True)
class Country:
    """One generated native country."""

    tag: str
    name: str
    kind: str
    members: tuple[str, ...]
    capital: str
    culture: str
    religion: str
    include: str
    areas: tuple[str, ...]
    color: tuple[int, int, int]
    color2: tuple[int, int, int]
    government: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class NativeWorld:
    """Native start state for generated locations, ready to serialize."""

    pops: dict[str, list[str]]
    countries: tuple[Country, ...]
    ranks: dict[str, tuple[str, str]]
    markets: tuple[str, ...]
    holy_sites: dict[str, str]
    names: dict[str, str]
    vassals: tuple[tuple[str, str], ...]
    complexity: dict[str, int]
    population: dict[str, int]
    stats: dict[str, object]


def _milli(value: str) -> int:
    whole, _, fraction = value.partition(".")
    return int(whole or "0") * PERMILLE + int((fraction + "000")[:3])


def _size(milli: int) -> str:
    return f"{milli // PERMILLE}.{milli % PERMILLE:03d}"


def _text(game_dir: Path, relative: str) -> str:
    return (game_dir / relative).read_text(encoding="utf-8-sig")


def _shares(values: list[str], weights: list[int], vocabulary: tuple[str, ...]) -> list[int]:
    total = max(1, sum(weights))
    sums = dict.fromkeys(vocabulary, 0)
    for value, weight in zip(values, weights, strict=True):
        if value in sums:
            sums[value] += weight
    return [sums[name] * PERMILLE // total for name in vocabulary]


def homeland(  # noqa: PLR0913, PLR0917 - a homeland combines every template field.
    climates: list[str],
    vegetations: list[str],
    topographies: list[str],
    latitudes: list[int],
    coastal: list[bool],
    state: list[bool],
    weights: list[int],
) -> tuple[int, ...]:
    """Feature vector compared by L1 distance: climate counts double, latitude half."""
    total = max(1, sum(weights))
    latitude = sum(abs(lat) * w for lat, w in zip(latitudes, weights, strict=True)) // total
    coast = sum(w for flag, w in zip(coastal, weights, strict=True) if flag) * PERMILLE // total
    states = sum(w for flag, w in zip(state, weights, strict=True) if flag) * PERMILLE // total
    return (
        *(2 * share for share in _shares(climates, weights, CLIMATES)),
        *_shares(vegetations, weights, VEGETATIONS),
        *_shares(topographies, weights, TOPOGRAPHIES),
        2 * states,
        latitude // 2,
        coast // 2,
    )


def _pops(text: str) -> dict[str, list[tuple[str, int, str, str]]]:
    holder = parse(text).block("locations")
    out: dict[str, list[tuple[str, int, str, str]]] = {}
    if holder is None:
        return out
    for entry in holder.entries:
        if entry.key is None or not isinstance(entry.value, Block):
            continue
        rows: list[tuple[str, int, str, str]] = []
        for pop in entry.value.find("define_pop"):
            if isinstance(pop.value, Block):
                fields = {e.key: e.value for e in pop.value.entries if isinstance(e.value, str)}
                rows.append(
                    (
                        fields.get("type", ""),
                        _milli(fields.get("size", "0")),
                        fields.get("culture", ""),
                        fields.get("religion", ""),
                    )
                )
        out[entry.key] = rows
    return out


def _countries(text: str) -> dict[str, tuple[str, list[str], list[str]]]:
    """Tag -> (kind, locations, includes) of the 1337 setup."""
    holder = parse(text).block("countries", "countries")
    out: dict[str, tuple[str, list[str], list[str]]] = {}
    if holder is None:
        return out
    for entry in holder.entries:
        if entry.key is None or not isinstance(entry.value, Block):
            continue
        kind = entry.value.first("type")
        pop = kind is not None and kind.value == "pop"
        locations: list[str] = []
        for key in ("own_control_core", "own_control_integrated", "add_pops_from_locations"):
            block = entry.value.block(key)
            if block is not None:
                locations += [word.value for word in block.words() if isinstance(word.value, str)]
        includes = [
            e.value.strip('"') for e in entry.value.find("include") if isinstance(e.value, str)
        ]
        out[entry.key] = ("pop" if pop else "land", locations, includes)
    return out


def _definitions(game_dir: Path) -> tuple[dict[str, str], set[str]]:
    cultures: dict[str, str] = {}
    words: set[str] = set()
    for path in sorted((game_dir / COUNTRY_DIR).glob("*.txt")):
        text = path.read_text(encoding="utf-8-sig")
        words |= set(TAG_WORD.findall(text))
        for entry in parse(text).entries:
            if entry.key and isinstance(entry.value, Block):
                culture = entry.value.first("culture_definition")
                if culture is not None and isinstance(culture.value, str):
                    cultures[entry.key] = culture.value
    return cultures, words


def _holy_sites(game_dir: Path) -> tuple[HolySite, ...]:
    sites: list[HolySite] = []
    for path in sorted((game_dir / HOLY_SITE_DIR).glob("*.txt")):
        for entry in parse(path.read_text(encoding="utf-8-sig")).entries:
            if entry.key is None or not isinstance(entry.value, Block):
                continue
            location = entry.value.first("location")
            religions = entry.value.block("religions")
            importance = entry.value.first("importance")
            if location is None or religions is None or not isinstance(location.value, str):
                continue
            names = [word.value for word in religions.words() if isinstance(word.value, str)]
            level = importance.value if importance is not None else "1"
            if names:
                sites.append(
                    HolySite(
                        entry.key,
                        location.value,
                        names[0],
                        int(level) if isinstance(level, str) and level.isdigit() else 1,
                    )
                )
    return tuple(sites)


def template_governments(
    templates: dict[str, str], setup_text: str
) -> dict[str, tuple[tuple[str, str], ...]]:
    """Government fields a generated country writes with each usable template.

    A generated country writes what the vanilla countries with the same template write
    most often. Vanilla templates may set no type (Tlaxcala adds ``type = republic`` to
    ``amerindian_advanced_republic_not_nahuatl_no_coast``) or a heir selection that every
    user overrides (``amerindian_advanced_monarchy*`` set ``tribal_oldest_male``; all their
    users write ``cognatic_primogeniture``). A template is usable only if its fields, the
    template itself or a template it includes give a government type.
    """
    roots = {name: parse(text) for name, text in templates.items()}

    def typed(name: str, seen: frozenset[str]) -> bool:
        root = roots.get(name)
        if root is None or name in seen:
            return False
        government = root.block("government")
        if government is not None and government.first("type") is not None:
            return True
        return any(
            typed(include.value.strip('"'), seen | {name})
            for include in root.find("include")
            if isinstance(include.value, str)
        )

    holder = parse(setup_text).block("countries", "countries")
    used: dict[str, Counter[tuple[tuple[str, str], ...]]] = {}
    for entry in holder.entries if holder is not None else []:
        if not isinstance(entry.value, Block):
            continue
        government = entry.value.block("government")
        fields = tuple(
            (key, value.value)
            for key in GOVERNMENT_FIELDS
            if government is not None
            and (value := government.first(key)) is not None
            and isinstance(value.value, str)
        )
        for include in entry.value.find("include"):
            name = include.value.strip('"') if isinstance(include.value, str) else ""
            if name in roots:
                used.setdefault(name, Counter())[fields] += 1
    out: dict[str, tuple[tuple[str, str], ...]] = {}
    for name in roots:
        counts = used.get(name, Counter())
        fields = min(counts, key=lambda each: (-counts[each], each), default=())
        if any(key == "type" for key, _ in fields) or typed(name, frozenset()):
            out[name] = fields
    return out


def _most_common(values: list[str]) -> str:
    if not values:
        return ""
    counts = Counter(values)
    return min(counts, key=lambda value: (-counts[value], value))


def vanilla_natives(  # noqa: C901 - one pass over the vanilla Americas.
    game_dir: Path,
    game_map: Eu5Map,
    geometry: VanillaGeometry,
    attributes: dict[str, dict[str, str]],
    hierarchy: dict[str, Location],
) -> VanillaNatives:
    """Calibrate density, totals and homelands on the vanilla 1337 Americas."""
    index = {key: number for number, key in enumerate(game_map.keys)}
    american = [
        key
        for key, location in hierarchy.items()
        if location.continent == NEW_WORLD
        and key in index
        and game_map.classes[index[key]] is CellClass.LAND
    ]
    if not american:
        message = "No vanilla American land locations"
        raise NativesError(message)
    pixels = np.bincount(game_map.labels.ravel(), minlength=len(game_map.keys))
    pops = _pops(_text(game_dir, f"{SETUP}/06_pops.txt"))
    setup_text = _text(game_dir, f"{SETUP}/10_countries.txt")
    countries = _countries(setup_text)
    tag_cultures, words = _definitions(game_dir)
    owned = {
        location
        for kind, locations, _ in countries.values()
        if kind == "land"
        for location in locations
    }
    rows = latitude_tenths(geometry.rows)
    climate_sums: dict[str, list[int]] = {}
    for key in american:
        size = sum(row[1] for row in pops.get(key, []))
        climate = attributes.get(key, {}).get("climate", "")
        if key not in owned:
            entry = climate_sums.setdefault(climate, [0, 0])
            entry[0] += size
            entry[1] += int(pixels[index[key]])
    density = {
        climate: sums[0] * PERMILLE // max(1, sums[1]) for climate, sums in climate_sums.items()
    }
    total = sum(row[1] for key in american for row in pops.get(key, []))
    culture_rows: dict[str, list[tuple[str, int]]] = {}
    religion_rows: dict[str, list[tuple[str, int]]] = {}
    for key in american:
        for _, amount, culture, religion in pops.get(key, []):
            culture_rows.setdefault(culture, []).append((key, amount))
            religion_rows.setdefault(religion, []).append((key, amount))
    coastal = _vanilla_coastal(game_map, american, index)

    def profile(rows_of: list[tuple[str, int]]) -> tuple[int, ...]:
        keys = [key for key, _ in rows_of]
        return homeland(
            [attributes.get(key, {}).get("climate", "") for key in keys],
            [attributes.get(key, {}).get("vegetation", "") for key in keys],
            [attributes.get(key, {}).get("topography", "") for key in keys],
            [int(rows[index[key]]) for key in keys],
            [key in coastal for key in keys],
            [key in owned for key in keys],
            [amount for _, amount in rows_of],
        )

    includes: dict[tuple[str, str], list[str]] = {}
    for tag, (kind, _, names) in countries.items():
        culture = tag_cultures.get(tag, "")
        chosen = [name for name in names if not name.startswith("expl_")]
        if culture and chosen:
            includes.setdefault((culture, kind), []).append(chosen[0])
    setups = _town_setups(_text(game_dir, f"{SETUP}/07_cities_and_buildings.txt"), pops)
    cultures: dict[str, Culture] = {}
    for culture, rows_of in sorted(culture_rows.items()):
        faiths = Counter[str]()
        for key, _ in rows_of:
            for _, amount, name, religion in pops.get(key, []):
                if name == culture:
                    faiths[religion] += amount
        cultures[culture] = Culture(
            religion=min(faiths, key=lambda r: (-faiths[r], r)),
            homeland=profile(rows_of),
            population=sum(amount for _, amount in rows_of),
            state_include=_most_common(includes.get((culture, "land"), [])),
            tribe_include=_most_common(includes.get((culture, "pop"), [])),
            city_setup=setups.get((culture, CITY), ""),
            town_setup=setups.get((culture, "town"), ""),
        )
    religions = {
        religion: (profile(rows_of), sum(amount for _, amount in rows_of))
        for religion, rows_of in sorted(religion_rows.items())
    }
    template_texts = {
        path.stem: path.read_text(encoding="utf-8-sig")
        for path in sorted((game_dir / TEMPLATE_DIR).glob("*.txt"))
    }
    templates = frozenset(template_texts)
    levels = template_levels(template_texts)
    country_text = _text(game_dir, COUNTRY_NAMES)
    names = set(TAG_WORD.findall(country_text))
    country_words = {
        name for key, name in COUNTRY_NAME.findall(country_text) if not key.endswith("_ADJ")
    }
    reserved = frozenset(words | names | set(countries) | OPERATORS)
    place_names = _location_names(game_dir)
    places = tuple(
        (place_names[key], _main_culture(pops[key]))
        for key in american
        if key in place_names and pops.get(key)
    )
    return VanillaNatives(
        density=density,
        population_per_location=total // len(american),
        cultures=cultures,
        religions=religions,
        templates=templates,
        reserved_tags=reserved,
        holy_sites=_holy_sites(game_dir),
        places=places,
        languages=_languages(game_dir, set(cultures)),
        reserved_names=frozenset(
            name_key(name) for name in (*place_names.values(), *country_words)
        ),
        governments=template_governments(template_texts, setup_text),
        colors=vanilla_colors(game_dir),
        levels=levels,
        overlord_level=overlord_level(
            setup_text, _text(game_dir, f"{SETUP}/12_diplomacy.txt"), levels
        ),
    )


def _rgb(kind: str, body: str) -> tuple[int, int, int] | None:
    """8-bit RGB of an ``rgb``, ``hsv360`` or ``hsv`` colour body, None if malformed."""
    try:
        values = [float(word) for word in body.split()]
    except ValueError:
        return None
    if len(values) != COLOR_CHANNELS:
        return None
    if kind == "rgb":
        return (int(values[0]), int(values[1]), int(values[2]))
    if kind == "hsv360":
        return hsv_rgb(int(values[0]) % 360, round(values[1] * 10), round(values[2] * 10))
    return hsv_rgb(
        int(values[0] * 360) % 360, round(values[1] * PERMILLE), round(values[2] * PERMILLE)
    )


def template_levels(templates: dict[str, str]) -> dict[str, int]:
    """Starting technology level of each template that sets one, itself or through includes."""
    roots = {name: parse(text) for name, text in templates.items()}

    def level(name: str, seen: frozenset[str]) -> int | None:
        root = roots.get(name)
        if root is None or name in seen:
            return None
        own = root.first("starting_technology_level")
        if own is not None and isinstance(own.value, str) and own.value.isdigit():
            return int(own.value)
        known = [
            found
            for include in root.find("include")
            if isinstance(include.value, str)
            if (found := level(include.value.strip('"'), seen | {name})) is not None
        ]
        return max(known) if known else None

    return {name: found for name in roots if (found := level(name, frozenset())) is not None}


def overlord_level(setup_text: str, diplomacy_text: str, levels: dict[str, int]) -> int:
    """The lowest technology level among the vanilla vassal lords whose template has one."""
    lords = set(VASSAL_LORD.findall(diplomacy_text))
    holder = parse(setup_text).block("countries", "countries")
    found: list[int] = []
    for entry in holder.entries if holder is not None else []:
        if entry.key in lords and isinstance(entry.value, Block):
            known = [
                levels[name]
                for include in entry.value.find("include")
                if isinstance(include.value, str)
                if (name := include.value.strip('"')) in levels
            ]
            found += [max(known)] if known else []
    if not found:
        message = "No vanilla vassal lord has a template with a starting technology level"
        raise NativesError(message)
    return min(found)


def vanilla_colors(game_dir: Path) -> frozenset[tuple[int, int, int]]:
    """Map colours of every vanilla country definition, named ones resolved.

    EU5 logs two countries with the same colour [V-GAME 1.4.2, C95], so generated colours
    avoid these. HSV colours are converted with this module's rounding, which can differ
    from the engine's by one unit; a clash is logged only for an exact match.
    """
    named: dict[str, tuple[int, int, int]] = {}
    for match in COLOR_DEFINITION.finditer(_text(game_dir, NAMED_COLORS)):
        color = _rgb(match.group(2), match.group(3))
        if color is not None:
            named[match.group(1)] = color
    colors: set[tuple[int, int, int]] = set()
    for path in sorted((game_dir / COUNTRY_DIR).glob("*.txt")):
        for match in COUNTRY_COLOR.finditer(path.read_text(encoding="utf-8-sig")):
            color = (
                _rgb(match.group(1), match.group(2))
                if match.group(1)
                else named.get(match.group(3))
            )
            if color is not None:
                colors.add(color)
    return frozenset(colors)


def _main_culture(rows: list[tuple[str, int, str, str]]) -> str:
    sizes = Counter[str]()
    for _, amount, culture, _ in rows:
        sizes[culture] += amount
    return min(sizes, key=lambda culture: (-sizes[culture], culture))


def _location_names(game_dir: Path) -> dict[str, str]:
    """English display names of every location (all ``location_names`` files)."""
    names: dict[str, str] = {}
    for path in sorted((game_dir / LOCATION_NAMES).glob("*.yml")):
        names.update(NAME_LINE.findall(path.read_text(encoding="utf-8-sig")))
    return names


def _languages(game_dir: Path, cultures: set[str]) -> dict[str, tuple[str, str]]:
    """Language and language family of the given cultures ("" where unknown)."""
    language: dict[str, str] = {}
    for path in sorted((game_dir / CULTURE_DIR).glob("*.txt")):
        for entry in parse(path.read_text(encoding="utf-8-sig")).entries:
            if entry.key in cultures and isinstance(entry.value, Block):
                value = entry.value.first("language")
                if value is not None and isinstance(value.value, str):
                    language[entry.key] = value.value
    family: dict[str, str] = {}
    wanted = set(language.values())
    for path in sorted((game_dir / LANGUAGE_DIR).glob("*.txt")):
        for entry in parse(path.read_text(encoding="utf-8-sig")).entries:
            if entry.key in wanted and isinstance(entry.value, Block):
                value = entry.value.first("family")
                if value is not None and isinstance(value.value, str):
                    family[entry.key] = value.value
    return {
        culture: (language.get(culture, ""), family.get(language.get(culture, ""), ""))
        for culture in sorted(cultures)
    }


def _vanilla_coastal(game_map: Eu5Map, keys: list[str], index: dict[str, int]) -> set[str]:
    sea = np.array([kind is CellClass.SEA for kind in game_map.classes], dtype=bool)
    wanted = np.zeros(len(game_map.keys), dtype=bool)
    wanted[[index[key] for key in keys]] = True
    labels = game_map.labels
    found = np.zeros(len(game_map.keys), dtype=bool)
    for first, second in ((labels[:, :-1], labels[:, 1:]), (labels[:-1], labels[1:])):
        touch = sea[first] & wanted[second]
        found[second[touch]] = True
        touch = sea[second] & wanted[first]
        found[first[touch]] = True
    return {key for key in keys if found[index[key]]}


def _town_setups(
    text: str, pops: dict[str, list[tuple[str, int, str, str]]]
) -> dict[tuple[str, str], str]:
    holder = parse(text).block("locations")
    found: dict[tuple[str, str], list[str]] = {}
    if holder is None:
        return {}
    for entry in holder.entries:
        if entry.key not in pops or not isinstance(entry.value, Block) or not pops[entry.key]:
            continue
        fields = {e.key: e.value for e in entry.value.entries if isinstance(e.value, str)}
        rank, setup = fields.get("rank", ""), fields.get("town_setup", "")
        if rank and setup:
            main = max(pops[entry.key], key=lambda row: (row[1], row[2]))[2]
            found.setdefault((main, rank), []).append(setup)
    return {key: _most_common(values) for key, values in found.items()}


@dataclass(frozen=True, slots=True, eq=False)
class _Cells:
    """Generated land cells in societies order, with their template fields."""

    cells: list[int]
    climate: list[str]
    vegetation: list[str]
    topography: list[str]
    latitude: list[int]
    coastal: list[bool]
    seas: list[list[int]]


def land_graph(
    world: NewWorld, biomes: CellBiomes, river_pixels: NDArray[np.int64], vanilla: VanillaNatives
) -> tuple[LandGraph, _Cells]:
    """Capacity, farming potential, travel cost and contacts of generated land."""
    land = [i for i, kind in enumerate(world.classes) if kind is CellClass.LAND]
    position = np.full(len(world.classes), -1, dtype=np.int64)
    position[land] = np.arange(len(land))
    water = np.array([kind in {CellClass.SEA, CellClass.LAKE} for kind in world.classes])
    sea = np.array([kind is CellClass.SEA for kind in world.classes])
    pairs = np.array(world.edges, dtype=np.int64).reshape(-1, 2)
    both = (position[pairs[:, 0]] >= 0) & (position[pairs[:, 1]] >= 0)
    edges = position[pairs[both]]
    shores: dict[int, list[int]] = {}
    for first, second in pairs.tolist():
        for wet, dry in ((first, second), (second, first)):
            if water[wet] and position[dry] >= 0:
                shores.setdefault(wet, []).append(int(position[dry]))
    links = sorted(
        {
            (a, b)
            for members in shores.values()
            for i, a in enumerate(sorted(set(members)))
            for b in sorted(set(members))[i + 1 :]
        }
    )
    is_coastal = np.zeros(len(land), dtype=bool)
    seas: list[list[int]] = [[] for _ in land]
    for wet, members in sorted(shores.items()):
        if sea[wet]:
            is_coastal[members] = True
            for member in sorted(set(members)):
                seas[member].append(wet)
    climate = [biomes.climate[cell] for cell in land]
    vegetation = [biomes.vegetation[cell] for cell in land]
    topography = [biomes.topography[cell] for cell in land]
    river = river_pixels[land] > 0
    latitudes = latitude_tenths(world.centroids[land, 0].astype(np.int64)).tolist()
    low, high = FARMING_LATITUDES
    capacity: list[int] = []
    potential: list[int] = []
    cost: list[int] = []
    for n, cell in enumerate(land):
        highland = climate[n] in HIGHLAND_CLIMATES
        farm_topography = HIGHLAND_FARMING.get(topography[n]) if highland else None
        farm = (
            CLIMATE_FARMING.get(climate[n], 0)
            * VEGETATION_FARMING.get(vegetation[n], 700)
            // PERMILLE
            * (farm_topography or TOPOGRAPHY_FARMING.get(topography[n], 700))
            // PERMILLE
        )
        if river[n]:
            farm += (PERMILLE - farm) * RIVER_FARMING // PERMILLE
        if is_coastal[n]:
            farm += (PERMILLE - farm) * COAST_FARMING // PERMILLE
        season = min(high - low, max(0, high - abs(latitudes[n])))
        potential.append(farm * season // (high - low))
        dense = (
            PERMILLE
            if highland and farm_topography
            else TOPOGRAPHY_DENSITY.get(topography[n], PERMILLE)
        )
        wet = WATER_DENSITY if river[n] or is_coastal[n] else PERMILLE
        capacity.append(
            int(world.pixels[cell]) * vanilla.density.get(climate[n], 0) // PERMILLE
            * dense // PERMILLE * wet // PERMILLE
        )  # fmt: skip
        cost.append(
            TOPOGRAPHY_COST.get(topography[n], STEP_COST) + VEGETATION_COST.get(vegetation[n], 0)
        )
    graph = LandGraph(
        capacity=np.array(capacity, dtype=np.int64),
        potential=np.array(potential, dtype=np.int64),
        cost=np.array(cost, dtype=np.int64),
        edges=edges.reshape(-1, 2),
        links=np.array(links, dtype=np.int64).reshape(-1, 2),
    )
    cells = _Cells(
        cells=land,
        climate=climate,
        vegetation=vegetation,
        topography=topography,
        latitude=latitudes,
        coastal=is_coastal.tolist(),
        seas=seas,
    )
    return graph, cells


def _zone_homelands(
    zones: NDArray[np.int64], cells: _Cells, societies: Societies, state: NDArray[np.bool_]
) -> list[tuple[tuple[int, ...], int]]:
    out: list[tuple[tuple[int, ...], int]] = []
    for zone in range(int(zones.max()) + 1 if zones.size else 0):
        members = np.flatnonzero(zones == zone).tolist()
        weights = [max(1, int(societies.population[n])) for n in members]
        out.append(
            (
                homeland(
                    [cells.climate[n] for n in members],
                    [cells.vegetation[n] for n in members],
                    [cells.topography[n] for n in members],
                    [cells.latitude[n] for n in members],
                    [cells.coastal[n] for n in members],
                    [bool(state[n]) for n in members],
                    weights,
                ),
                sum(int(societies.population[n]) for n in members),
            )
        )
    return out


def match_homelands(
    zones: list[tuple[tuple[int, ...], int]],
    candidates: list[tuple[str, tuple[int, ...]]],
    *,
    key: int,
    preferred: list[list[int]] | None = None,
) -> list[str]:
    """Greedy best fit, biggest zone first.

    A zone takes the best unused candidate of its preferred list (or of all, without
    one) unless reusing the best of that list fits better by more than MATCH_SLACK.
    """
    if not candidates:
        return [""] * len(zones)
    vectors = np.array([vector for _, vector in candidates], dtype=np.int64)
    used = np.zeros(len(candidates), dtype=bool)
    everyone = list(range(len(candidates)))
    order = sorted(range(len(zones)), key=lambda z: (-zones[z][1], z))
    chosen = [""] * len(zones)
    for zone in order:
        distance = np.abs(vectors - np.array(zones[zone][0], dtype=np.int64)).sum(axis=1)
        noise = hash_grid(
            key, np.full(len(candidates), zone, dtype=np.int64), np.arange(len(candidates))
        ) % np.uint64(MATCH_NOISE)
        score = (distance + noise.astype(np.int64)).tolist()
        own = preferred[zone] if preferred is not None and preferred[zone] else everyone
        best = min(own, key=lambda c: (score[c], c))
        free = [c for c in own if not used[c]]
        pick = best
        if free:
            fresh = min(free, key=lambda c: (score[c], c))
            if score[fresh] <= score[best] + MATCH_SLACK:
                pick = fresh
        used[pick] = True
        chosen[zone] = candidates[pick][0]
    return chosen


def new_tags(count: int, reserved: frozenset[str], seed: int, keys: KeySpace) -> list[str]:
    """Fresh three-letter tags whose name and adjective keys have free hashes."""
    rng = SplitMix64(derive_seed(seed, "natives", "tags"))
    taken = set(reserved)
    tags: list[str] = []
    while len(tags) < count:
        tag = "".join(LETTERS[rng.below(len(LETTERS))] for _ in range(3))
        if tag not in taken and keys.claim((tag, f"{tag}_ADJ")):
            taken.add(tag)
            tags.append(tag)
    return tags


def hsv_rgb(hue: int, saturation: int, value: int) -> tuple[int, int, int]:
    """Integer HSV (hue 0-359, saturation and value permille) to 8-bit RGB."""
    chroma = value * saturation // PERMILLE
    sector, rest = divmod(hue, 60)
    middle = chroma * (rest if sector % 2 == 0 else 60 - rest) // 60
    low = value - chroma
    table = (
        (chroma, middle, 0), (middle, chroma, 0), (0, chroma, middle),
        (0, middle, chroma), (middle, 0, chroma), (chroma, 0, middle),
    )  # fmt: skip
    red, green, blue = table[sector % 6]
    return (
        (red + low) * 255 // PERMILLE,
        (green + low) * 255 // PERMILLE,
        (blue + low) * 255 // PERMILLE,
    )


def map_colors(
    neighbours: list[set[int]], seed: int, taken: frozenset[tuple[int, int, int]]
) -> list[tuple[tuple[int, int, int], tuple[int, int, int]]]:
    """Map colours that differ from coloured neighbours and are unused, plus a second colour."""
    rng = SplitMix64(derive_seed(seed, "natives", "colors"))
    used = set(taken)
    out: list[tuple[tuple[int, int, int], tuple[int, int, int]]] = []

    def draw() -> tuple[int, int, int]:
        return hsv_rgb(rng.below(360), 350 + rng.below(450), 400 + rng.below(450))

    for number, near in enumerate(neighbours):
        options = [draw() for _ in range(COLOR_TRIES)]
        nearby = [out[other][0] for other in near if other < number]

        def spread(color: tuple[int, int, int], nearby: list[tuple[int, int, int]] = nearby) -> int:
            if not nearby:
                return 0
            return min(sum(abs(a - b) for a, b in zip(color, t, strict=True)) for t in nearby)

        ranked = sorted(range(COLOR_TRIES), key=lambda i: (-spread(options[i]), i))
        free = [options[i] for i in ranked if options[i] not in used]
        chosen = free[0] if free else draw()
        while chosen in used:
            chosen = draw()
        used.add(chosen)
        second = hsv_rgb(rng.below(360), 300 + rng.below(500), 300 + rng.below(600))
        out.append((chosen, second))
    return out


def _include(  # noqa: PLR0913 - the template depends on the culture, the polity and its coast.
    vanilla: VanillaNatives,
    culture: str,
    *,
    state: bool,
    advanced: bool,
    coastal: bool,
    empire: bool = False,
) -> str:
    info = vanilla.cultures.get(culture)
    name = (info.state_include if state else info.tribe_include) if info else ""
    if not name:
        name = (ADVANCED_STATE if advanced else DEFAULT_STATE) if state else DEFAULT_TRIBE
    if empire and vanilla.levels.get(name, -1) < vanilla.overlord_level:
        # A great empire leads vassals, which a lord without a starting technology cannot (C99).
        name = ADVANCED_STATE
    base = name.removesuffix(NO_COAST)
    if not coastal and base + NO_COAST in vanilla.templates:
        return base + NO_COAST
    if coastal and base in vanilla.templates:
        return base
    return name


def _identities(
    societies: Societies, cells: _Cells, vanilla: VanillaNatives, seed: int
) -> tuple[list[str], list[str], NDArray[np.bool_]]:
    """Religion per religion zone and culture per culture zone; state land mask."""
    state = np.zeros(len(cells.cells), dtype=bool)
    for polity in societies.polities:
        if polity.kind == STATE:
            state[list(polity.members)] = True
    religion_names = sorted(vanilla.religions)
    religions = match_homelands(
        _zone_homelands(societies.religion, cells, societies, state),
        [(name, vanilla.religions[name][0]) for name in religion_names],
        key=derive_seed(seed, "natives", "religions"),
    )
    culture_zones = _zone_homelands(societies.culture, cells, societies, state)
    culture_names = sorted(vanilla.cultures)
    zone_religion = [""] * len(culture_zones)
    for node, zone in enumerate(societies.culture.tolist()):
        zone_religion[zone] = religions[int(societies.religion[node])]
    by_religion: dict[str, list[int]] = {}
    for number, name in enumerate(culture_names):
        by_religion.setdefault(vanilla.cultures[name].religion, []).append(number)
    cultures = match_homelands(
        culture_zones,
        [(name, vanilla.cultures[name].homeland) for name in culture_names],
        key=derive_seed(seed, "natives", "cultures"),
        preferred=[by_religion.get(name, []) for name in zone_religion],
    )
    return religions, cultures, state


def diaspora(  # noqa: PLR0913 - a diaspora needs the zones, identities and vanilla tables.
    societies: Societies,
    keys: list[str],
    *,
    zones: list[tuple[tuple[int, ...], int]],
    state: NDArray[np.bool_],
    religions: list[str],
    cultures: list[str],
    vanilla: VanillaNatives,
    seed: int,
) -> dict[str, list[str]]:
    """Small pops of the vanilla cultures and religions no zone took, by best homeland fit."""
    inhabited = np.flatnonzero(societies.population > 0).tolist()
    by_zone: dict[int, list[int]] = {}
    for node in inhabited:
        by_zone.setdefault(int(societies.culture[node]), []).append(node)
    if not by_zone:
        return {}
    zone_ids = np.array(sorted(by_zone), dtype=np.int64)
    vectors = np.array([zones[int(zone)][0] for zone in zone_ids], dtype=np.int64)
    used_cultures = {cultures[int(societies.culture[node])] for node in inhabited}
    used_religions = {religions[int(societies.religion[node])] for node in inhabited}

    def place(name: str, homeland_vector: tuple[int, ...]) -> tuple[int, int]:
        """(node, culture zone) best fitting ``homeland_vector``; ties by noise and key."""
        stream = derive_seed(seed, "natives", "diaspora", name)
        noise = hash_grid(stream, zone_ids, np.zeros(zone_ids.size, dtype=np.int64)) % np.uint64(
            MATCH_NOISE
        )
        distance = np.abs(vectors - np.array(homeland_vector, dtype=np.int64)).sum(axis=1)
        zone = int(zone_ids[int(np.argmin(distance + noise.astype(np.int64)))])
        members = by_zone[zone]
        return members[SplitMix64(stream).below(len(members))], zone

    pops: dict[str, list[str]] = {}

    def add(node: int, culture: str, religion: str) -> None:
        kind = "peasants" if state[node] else "tribesmen"
        size = _size(DIASPORA_MILLI)
        row = f"\tdefine_pop = {{\ttype = {kind}\tsize = {size}\tculture = {culture}\t"
        pops.setdefault(keys[node], []).append(row + f"religion = {religion} }}")

    for name in sorted(set(vanilla.cultures) - used_cultures):
        info = vanilla.cultures[name]
        node, _ = place(name, info.homeland)
        add(node, name, info.religion)
        used_religions.add(info.religion)
    for name in sorted(set(vanilla.religions) - used_religions):
        node, _ = place(name, vanilla.religions[name][0])
        add(node, cultures[int(societies.culture[node])], name)
    return pops


def _pop_lines(
    societies: Societies, keys: list[str], religions: list[str], cultures: list[str]
) -> dict[str, list[str]]:
    """``define_pop`` lines per inhabited location: elites, peasants, tribesmen."""
    pops: dict[str, list[str]] = {}
    elite = {polity.capital for polity in societies.polities if polity.kind == STATE}
    for node, key in enumerate(keys):
        total = int(societies.population[node])
        if total <= 0:
            continue
        culture = cultures[int(societies.culture[node])]
        religion = religions[int(societies.religion[node])]
        rows: list[tuple[str, int]] = []
        if node in elite:
            rows += [(kind, max(low, total * share // MYRIAD)) for kind, (low, share) in ELITES]
        if node in societies.ranks:
            rows.append(("burghers", max(BURGHERS[0], total * BURGHERS[1] // MYRIAD)))
        rows.append(("peasants", int(societies.peasants[node])))
        rows.append(("tribesmen", total - sum(amount for _, amount in rows)))
        pops[key] = [
            (
                f"\tdefine_pop = {{\ttype = {kind}\tsize = {_size(amount)}\t"
                f"culture = {culture}\treligion = {religion} }}"
            )
            for kind, amount in rows
            if amount > 0
        ]
    return pops


class PlaceNamer:
    """Place names in a culture's language: one Markov chain per vanilla name corpus."""

    __slots__: tuple[str, ...] = ("_chains", "_corpora", "_seed", "_used", "_vanilla")

    def __init__(self, vanilla: VanillaNatives, seed: int) -> None:
        self._vanilla: VanillaNatives = vanilla
        self._seed: int = seed
        self._used: set[str] = set(vanilla.reserved_names)
        self._chains: dict[str, MarkovNames] = {}
        self._corpora: dict[str, list[str]] = {}
        for name, culture in vanilla.places:
            for key in [*self._keys(culture), "all"]:
                self._corpora.setdefault(key, []).append(name)

    def _keys(self, culture: str) -> list[str]:
        language, family = self._vanilla.languages.get(culture, ("", ""))
        info = self._vanilla.cultures.get(culture)
        religion = info.religion if info is not None else ""
        pairs = (("language", language), ("family", family), ("religion", religion))
        return [f"{kind}:{value}" for kind, value in pairs if value]

    def name(self, culture: str) -> str:
        """A new place name for ``culture``, unique among all names drawn."""
        key = next(
            (key for key in self._keys(culture) if len(self._corpora.get(key, ())) >= MIN_CORPUS),
            "all",
        )
        chain = self._chains.get(key)
        if chain is None:
            chain = MarkovNames(self._corpora.get(key, []), self._seed, key, self._used)
            self._chains[key] = chain
        return chain.next()


def _majority(cultures: list[str]) -> str:
    counts = Counter(cultures)
    return min(counts, key=lambda culture: (-counts[culture], culture)) if counts else ""


def _place_names(
    world: NewWorld,
    plan: Plan,
    cells: _Cells,
    culture_of: list[str],
    namer: PlaceNamer,
) -> dict[str, str]:
    """Names of land and wasteland locations, provinces and areas in local languages."""
    culture: dict[int, str] = dict(zip(cells.cells, culture_of, strict=True))
    names = {plan.cells[cell].key: namer.name(culture[cell]) for cell in cells.cells}
    near: dict[int, list[str]] = {}
    for first, second in world.edges:
        for waste, land in ((first, second), (second, first)):
            if world.classes[waste] is CellClass.WASTELAND and land in culture:
                near.setdefault(waste, []).append(culture[land])
    for waste in sorted(near):
        culture[waste] = _majority(near[waste])
        names[plan.cells[waste].key] = namer.name(culture[waste]) + WASTELAND_SUFFIX
    members: dict[str, list[str]] = {}
    for cell, value in sorted(culture.items()):
        members.setdefault(plan.cells[cell].province, []).append(value)
        members.setdefault(plan.cells[cell].area, []).append(value)
    for key in sorted(set(plan.province_names) | set(plan.display_overrides)):
        if members.get(key):
            names[key] = namer.name(_majority(members[key]))
    return names


def _neighbours(societies: Societies, edges: NDArray[np.int64]) -> list[set[int]]:
    owner = np.full(len(societies.population), -1, dtype=np.int64)
    for number, polity in enumerate(societies.polities):
        owner[list(polity.members)] = number
    neighbours: list[set[int]] = [set() for _ in societies.polities]
    for first, second in edges.tolist():
        a, b = int(owner[first]), int(owner[second])
        if a >= 0 and b >= 0 and a != b:
            neighbours[a].add(b)
            neighbours[b].add(a)
    return neighbours


def _countries_of(  # noqa: PLR0913 - a country draws on every identity table.
    societies: Societies,
    *,
    cells: _Cells,
    plan: Plan,
    vanilla: VanillaNatives,
    religions: list[str],
    cultures: list[str],
    neighbours: list[set[int]],
    seed: int,
    names: dict[str, str],
    namer: PlaceNamer,
    loc_keys: KeySpace,
) -> list[Country]:
    keys = [plan.cells[cell].key for cell in cells.cells]
    tags = new_tags(len(societies.polities), vanilla.reserved_tags, seed, loc_keys)
    colors = map_colors(neighbours, seed, vanilla.colors)
    religion_areas: dict[int, set[str]] = {}
    for node, zone in enumerate(societies.religion.tolist()):
        known = religion_areas.setdefault(zone, set())
        known.add(plan.cells[cells.cells[node]].area)
        known.update(plan.cells[sea].area for sea in cells.seas[node])
    countries: list[Country] = []
    for number, polity in enumerate(societies.polities):
        is_state = polity.kind == STATE
        areas = religion_areas[int(societies.religion[polity.capital])] | {
            plan.cells[cells.cells[node]].area for node in polity.members
        }
        name = names[keys[polity.capital]] if is_state else namer.name(cultures[polity.culture])
        include = _include(
            vanilla,
            cultures[polity.culture],
            state=is_state,
            advanced=int(societies.complexity[polity.capital]) >= ADVANCED_PERMILLE,
            coastal=any(cells.coastal[node] for node in polity.members),
            empire=polity.great,
        )
        if include not in vanilla.governments:
            message = f"Template {include} has no government type, and no vanilla country sets one"
            raise NativesError(message)
        countries.append(
            Country(
                tag=tags[number],
                name=name,
                kind=polity.kind,
                members=tuple(keys[node] for node in polity.members),
                capital=keys[polity.capital],
                culture=cultures[polity.culture],
                religion=religions[int(societies.religion[polity.capital])],
                include=include,
                areas=tuple(sorted(areas)),
                color=colors[number][0],
                color2=colors[number][1],
                government=vanilla.governments[include],
            )
        )
    return countries


def vassal_pairs(
    societies: Societies, religions: list[str], neighbours: list[set[int]], able: set[int]
) -> list[tuple[int, int]]:
    """(overlord, vassal) polity pairs among neighbouring states of one religion.

    Overlords are the most populous states in ``able``; their number is the share of all
    states.
    """
    states = [n for n, polity in enumerate(societies.polities) if polity.kind == STATE]
    people = {
        n: int(societies.population[list(societies.polities[n].members)].sum()) for n in states
    }
    faith = {n: religions[int(societies.religion[societies.polities[n].capital])] for n in states}
    ranked = sorted(states, key=lambda n: (-people[n], n))
    count = max(1, (len(ranked) * OVERLORD_PERMILLE + PERMILLE // 2) // PERMILLE)
    overlords = [n for n in ranked if n in able][:count]
    taken = set(overlords)
    pairs: list[tuple[int, int]] = []
    for lord in overlords:
        options = sorted(
            (n for n in neighbours[lord] if n in people and n not in taken),
            key=lambda n: (-people[n], n),
        )
        chosen = [
            n
            for n in options
            if faith[n] == faith[lord] and VASSAL_SHARE * people[n] < people[lord]
        ][:MAX_VASSALS]
        taken.update(chosen)
        pairs += [(lord, n) for n in chosen]
    return pairs


def _rank_setups(
    societies: Societies, keys: list[str], cultures: list[str], vanilla: VanillaNatives
) -> dict[str, tuple[str, str]]:
    """Rank and the town setup the culture used in vanilla, else a plain American one."""
    ranks: dict[str, tuple[str, str]] = {}
    for node, rank in sorted(societies.ranks.items()):
        info = vanilla.cultures.get(cultures[int(societies.culture[node])])
        if rank == CITY:
            setup = (info.city_setup if info else "") or DEFAULT_CITY
        else:
            setup = (info.town_setup if info else "") or DEFAULT_TOWN
        ranks[keys[node]] = (rank, setup)
    return ranks


def build_natives(  # noqa: PLR0913 - the start state reads the whole generated world.
    *,
    world: NewWorld,
    plan: Plan,
    biomes: CellBiomes,
    river_pixels: NDArray[np.int64],
    vanilla: VanillaNatives,
    settings: NativeSettings,
    seed: int,
    loc_keys: KeySpace,
) -> NativeWorld:
    """Societies, their cultures and religions, countries and their names."""
    graph, cells = land_graph(world, biomes, river_pixels, vanilla)
    target = vanilla.population_per_location * len(cells.cells)
    societies = generate_societies(graph, settings, seed=seed, target=target)
    keys = [plan.cells[cell].key for cell in cells.cells]
    religions, cultures, state = _identities(societies, cells, vanilla, seed)
    namer = PlaceNamer(vanilla, seed)
    culture_of = [cultures[int(zone)] for zone in societies.culture.tolist()]
    names = _place_names(world, plan, cells, culture_of, namer)
    countries = _countries_of(
        societies,
        cells=cells,
        plan=plan,
        vanilla=vanilla,
        religions=religions,
        cultures=cultures,
        neighbours=_neighbours(societies, graph.edges),
        seed=seed,
        names=names,
        namer=namer,
        loc_keys=loc_keys,
    )
    ranks = _rank_setups(societies, keys, cultures, vanilla)
    able = {
        number
        for number, country in enumerate(countries)
        if vanilla.levels.get(country.include, -1) >= vanilla.overlord_level
    }
    pairs = vassal_pairs(societies, religions, _neighbours(societies, graph.edges), able)
    vassals = tuple((countries[lord].tag, countries[vassal].tag) for lord, vassal in pairs)
    pops = _pop_lines(societies, keys, religions, cultures)
    for where, rows in diaspora(
        societies,
        keys,
        zones=_zone_homelands(societies.culture, cells, societies, state),
        state=state,
        religions=religions,
        cultures=cultures,
        vanilla=vanilla,
        seed=seed,
    ).items():
        pops.setdefault(where, []).extend(rows)
    holy = _place_holy_sites(vanilla, religions, societies, keys)
    stats: dict[str, object] = {
        "land_locations": len(keys),
        "population_milli": int(societies.population.sum()),
        "inhabited_locations": int(np.count_nonzero(societies.population)),
        "hearths": len(societies.hearths),
        "state_locations": int(np.count_nonzero(state)),
        "states": sum(1 for c in countries if c.kind == STATE),
        "great_empires": [len(polity.members) for polity in societies.polities if polity.great],
        "largest_ordinary_state": max(
            (len(p.members) for p in societies.polities if p.kind == STATE and not p.great),
            default=0,
        ),
        "tribes": sum(1 for c in countries if c.kind != STATE),
        "tribe_locations": sum(len(c.members) for c in countries if c.kind != STATE),
        "religion_zones": int(societies.religion.max()) + 1 if keys else 0,
        "religions": len(set(religions)),
        "culture_zones": int(societies.culture.max()) + 1 if keys else 0,
        "cultures": len(set(cultures)),
        "peasants_milli": int(societies.peasants.sum()),
        "ranks": dict(Counter(rank for rank, _ in ranks.values())),
        "markets": len(societies.markets),
        "holy_sites_placed": len(holy),
        "names_in_local_languages": len(names),
        "vassals": len(vassals),
    }
    return NativeWorld(
        pops=pops,
        countries=tuple(countries),
        ranks=ranks,
        markets=tuple(keys[node] for node in societies.markets),
        holy_sites=holy,
        names=names,
        vassals=vassals,
        complexity=dict(zip(keys, societies.complexity.tolist(), strict=True)),
        population=dict(zip(keys, societies.population.tolist(), strict=True)),
        stats=stats,
    )


def _place_holy_sites(
    vanilla: VanillaNatives, religions: list[str], societies: Societies, keys: list[str]
) -> dict[str, str]:
    """Vanilla location -> generated location for holy sites of placed religions."""
    ranked: dict[str, list[int]] = {}
    for node in np.argsort(-societies.population, kind="stable").tolist():
        if societies.population[node] > 0:
            ranked.setdefault(religions[int(societies.religion[node])], []).append(node)
    taken: set[int] = set()
    moved: dict[str, str] = {}
    sites = sorted(vanilla.holy_sites, key=lambda s: (s.religion, -s.importance, s.name))
    for site in sites:
        options = [node for node in ranked.get(site.religion, []) if node not in taken]
        if options and site.location not in moved:
            taken.add(options[0])
            moved[site.location] = keys[options[0]]
    return moved


def _locations_block(keys: tuple[str, ...], indent: str) -> str:
    lines = [" ".join(keys[i : i + 8]) for i in range(0, len(keys), 8)]
    return "".join(f"{indent}\t{line}\n" for line in lines)


def country_records(countries: tuple[Country, ...]) -> str:
    """Records for ``countries = { countries = { ... } }`` of ``10_countries.txt``."""
    parts: list[str] = ["\n\t# RNW generated natives\n"]
    for country in countries:
        lines = [f"\t{country.tag} = {{\n"]
        if country.kind == STATE:
            lines.append("\t\town_control_core = {\n")
            lines.append(_locations_block(country.members, "\t\t"))
            lines.append("\t\t}\n")
            lines.append(f"\t\tcapital = {country.capital}\n")
        else:
            lines.append("\t\ttype = pop\n")
            lines.append("\t\tadd_pops_from_locations = {\n")
            lines.append(_locations_block(country.members, "\t\t"))
            lines.append("\t\t}\n")
        lines.append(f'\t\tinclude = "{country.include}"\n')
        lines.append("\t\tdiscovered_areas = {\n")
        lines.append(_locations_block(country.areas, "\t\t"))
        lines.append("\t\t}\n")
        lines.append("\t\tgovernment = {\n")
        lines.extend(f"\t\t\t{key} = {value}\n" for key, value in country.government)
        lines.append("\t\t\truler = random\n\t\t}\n")
        lines.append("\t}\n")
        parts.append("".join(lines))
    return "".join(parts)


def country_definitions(countries: tuple[Country, ...]) -> bytes:
    """``in_game/setup/countries`` file with colours, culture and religion per tag."""
    lines: list[str] = []
    for country in countries:
        red, green, blue = country.color
        red2, green2, blue2 = country.color2
        body = [
            f"{country.tag} = {{",
            f"\tcolor = rgb {{ {red} {green} {blue} }}",
            f"\tcolor2 = rgb {{ {red2} {green2} {blue2} }}",
            "",
            f"\tculture_definition = {country.culture}",
            f"\treligion_definition = {country.religion}",
            "}",
        ]
        lines.append("\n".join(body) + "\n")
    return "\n".join(lines).encode("utf-8-sig")


def country_names(countries: tuple[Country, ...]) -> dict[str, str]:
    """Localization keys of the country names and adjectives."""
    names: dict[str, str] = {}
    for country in countries:
        names[country.tag] = country.name
        names[f"{country.tag}_ADJ"] = country.name
    return names


def city_lines(ranks: dict[str, tuple[str, str]]) -> str:
    """Entries for ``locations = { ... }`` of ``07_cities_and_buildings.txt``."""
    body = "".join(
        f"\t{key} = {{ rank = {rank} town_setup = {setup} }}\n"
        for key, (rank, setup) in ranks.items()
    )
    return "\n\t# RNW generated natives\n" + body if body else ""


def vassal_lines(vassals: tuple[tuple[str, str], ...]) -> str:
    """Entries for ``diplomacy_manager = { ... }`` of ``12_diplomacy.txt``."""
    body = "".join(
        f"\tdependency = {{ first = {lord} second = {vassal} subject_type = vassal }}\n"
        for lord, vassal in vassals
    )
    return "\n\t# RNW generated natives\n" + body if body else ""


def market_lines(markets: tuple[str, ...]) -> str:
    """Entries for ``market_manager = { ... }`` of ``03_markets.txt``."""
    body = "".join(f"\tadd_market = {key}\n" for key in markets)
    return "\n\t# RNW generated natives\n" + body if body else ""


def holy_site_outputs(
    game_dir: Path, remap: dict[str, str], moved: dict[str, str]
) -> dict[str, bytes]:
    """Holy site files with removed locations remapped and placed religions' sites moved.

    Only sites on removed vanilla locations (keys of ``remap``) move.
    """
    merged = remap | {key: value for key, value in moved.items() if key in remap}
    outputs: dict[str, bytes] = {}
    for path in sorted((game_dir / HOLY_SITE_DIR).glob("*.txt")):
        raw = path.read_bytes()
        new, count = remap_text(raw.decode("utf-8-sig"), merged)
        if count:
            relative = path.relative_to(game_dir).as_posix().removeprefix("game/")
            bom = "\ufeff" if raw.startswith(b"\xef\xbb\xbf") else ""
            outputs[relative] = (bom + new).encode("utf-8")
    return outputs
