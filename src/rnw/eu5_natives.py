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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.eu5_biomes import latitude_tenths
from rnw.eu5_canvas import NEW_WORLD
from rnw.eu5_remap import remap_text
from rnw.model import CellClass
from rnw.names import NameGenerator
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
    from rnw.newworld import NewWorld
    from rnw.settings import NativeSettings

SETUP: Final[str] = "game/main_menu/setup/1337"
TEMPLATE_DIR: Final[str] = "game/main_menu/setup/templates"
COUNTRY_DIR: Final[str] = "game/in_game/setup/countries"
HOLY_SITE_DIR: Final[str] = "game/in_game/common/holy_sites"
COUNTRY_NAMES: Final[str] = "game/main_menu/localization/english/country_names_l_english.yml"
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
NO_COAST: Final[str] = "_no_coast"
TAG_WORD: Final[re.Pattern[str]] = re.compile(r"(?<![A-Za-z0-9_])([A-Z]{3})(?![A-Za-z0-9_])")
OPERATORS: Final[frozenset[str]] = frozenset({"AND", "NOT", "NOR", "ALL", "ANY", "YES"})
LETTERS: Final[str] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
COLOR_TRIES: Final[int] = 6


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


@dataclass(frozen=True, slots=True, eq=False)
class NativeWorld:
    """Native start state for generated locations, ready to serialize."""

    pops: dict[str, list[str]]
    countries: tuple[Country, ...]
    ranks: dict[str, tuple[str, str]]
    markets: tuple[str, ...]
    holy_sites: dict[str, str]
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
    countries = _countries(_text(game_dir, f"{SETUP}/10_countries.txt"))
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
    templates = frozenset(path.stem for path in (game_dir / TEMPLATE_DIR).glob("*.txt"))
    names = set(TAG_WORD.findall(_text(game_dir, COUNTRY_NAMES)))
    reserved = frozenset(words | names | set(countries) | OPERATORS)
    return VanillaNatives(
        density=density,
        population_per_location=total // len(american),
        cultures=cultures,
        religions=religions,
        templates=templates,
        reserved_tags=reserved,
        holy_sites=_holy_sites(game_dir),
    )


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
    for wet, members in shores.items():
        if sea[wet]:
            is_coastal[members] = True
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


def new_tags(count: int, reserved: frozenset[str], seed: int) -> list[str]:
    rng = SplitMix64(derive_seed(seed, "natives", "tags"))
    taken = set(reserved)
    tags: list[str] = []
    while len(tags) < count:
        tag = "".join(LETTERS[rng.below(len(LETTERS))] for _ in range(3))
        if tag not in taken:
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


def _colors(
    neighbours: list[set[int]], seed: int
) -> list[tuple[tuple[int, int, int], tuple[int, int, int]]]:
    """Map colours that differ from already coloured neighbours, plus a second colour."""
    rng = SplitMix64(derive_seed(seed, "natives", "colors"))
    out: list[tuple[tuple[int, int, int], tuple[int, int, int]]] = []
    for number, near in enumerate(neighbours):
        options = [
            hsv_rgb(rng.below(360), 350 + rng.below(450), 400 + rng.below(450))
            for _ in range(COLOR_TRIES)
        ]
        taken = [out[other][0] for other in near if other < number]

        def spread(color: tuple[int, int, int], taken: list[tuple[int, int, int]] = taken) -> int:
            if not taken:
                return 0
            return min(sum(abs(a - b) for a, b in zip(color, t, strict=True)) for t in taken)

        best = max(range(COLOR_TRIES), key=lambda i: (spread(options[i]), -i))
        second = hsv_rgb(rng.below(360), 300 + rng.below(500), 300 + rng.below(600))
        out.append((options[best], second))
    return out


def _include(
    vanilla: VanillaNatives, culture: str, *, state: bool, advanced: bool, coastal: bool
) -> str:
    info = vanilla.cultures.get(culture)
    name = (info.state_include if state else info.tribe_include) if info else ""
    if not name:
        name = (ADVANCED_STATE if advanced else DEFAULT_STATE) if state else DEFAULT_TRIBE
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
) -> list[Country]:
    keys = [plan.cells[cell].key for cell in cells.cells]
    tags = new_tags(len(societies.polities), vanilla.reserved_tags, seed)
    colors = _colors(neighbours, seed)
    tribe_names = NameGenerator(seed, "tribes", frozenset(cell.name for cell in plan.cells))
    religion_areas: dict[int, set[str]] = {}
    for node, zone in enumerate(societies.religion.tolist()):
        religion_areas.setdefault(zone, set()).add(plan.cells[cells.cells[node]].area)
    countries: list[Country] = []
    for number, polity in enumerate(societies.polities):
        is_state = polity.kind == STATE
        areas = religion_areas[int(societies.religion[polity.capital])] | {
            plan.cells[cells.cells[node]].area for node in polity.members
        }
        name = plan.cells[cells.cells[polity.capital]].name if is_state else tribe_names.next()
        countries.append(
            Country(
                tag=tags[number],
                name=name,
                kind=polity.kind,
                members=tuple(keys[node] for node in polity.members),
                capital=keys[polity.capital],
                culture=cultures[polity.culture],
                religion=religions[int(societies.religion[polity.capital])],
                include=_include(
                    vanilla,
                    cultures[polity.culture],
                    state=is_state,
                    advanced=int(societies.complexity[polity.capital]) >= ADVANCED_PERMILLE,
                    coastal=any(cells.coastal[node] for node in polity.members),
                ),
                areas=tuple(sorted(areas)),
                color=colors[number][0],
                color2=colors[number][1],
            )
        )
    return countries


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
) -> NativeWorld:
    """Societies, their cultures and religions, countries and their names."""
    graph, cells = land_graph(world, biomes, river_pixels, vanilla)
    target = vanilla.population_per_location * len(cells.cells)
    societies = generate_societies(graph, settings, seed=seed, target=target)
    keys = [plan.cells[cell].key for cell in cells.cells]
    religions, cultures, state = _identities(societies, cells, vanilla, seed)
    countries = _countries_of(
        societies,
        cells=cells,
        plan=plan,
        vanilla=vanilla,
        religions=religions,
        cultures=cultures,
        neighbours=_neighbours(societies, graph.edges),
        seed=seed,
    )
    ranks = _rank_setups(societies, keys, cultures, vanilla)
    holy = _place_holy_sites(vanilla, religions, societies, keys)
    stats: dict[str, object] = {
        "land_locations": len(keys),
        "population_milli": int(societies.population.sum()),
        "inhabited_locations": int(np.count_nonzero(societies.population)),
        "hearths": len(societies.hearths),
        "state_locations": int(np.count_nonzero(state)),
        "states": sum(1 for c in countries if c.kind == STATE),
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
    }
    return NativeWorld(
        pops=_pop_lines(societies, keys, religions, cultures),
        countries=tuple(countries),
        ranks=ranks,
        markets=tuple(keys[node] for node in societies.markets),
        holy_sites=holy,
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
        lines.append("\t\tgovernment = {\n\t\t\truler = random\n\t\t}\n")
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
