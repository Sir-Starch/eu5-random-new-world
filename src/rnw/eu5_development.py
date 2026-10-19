"""Start development of a generated New World: society terms, harbours, market villages.

EU5 sums the rules of ``14_development.txt`` per location at the 1337 start. The vanilla
Americas get their civilisation level from region, province and location entries
[V-LOCAL C73]. The generated world keeps the rules and replaces those positional inputs
by values from its own society model: a term that follows complexity, harbour values on
the vanilla distribution, and market villages in the most complex state capitals.
All arithmetic is integer.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.pdx import Block, parse

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from numpy.typing import NDArray

    from rnw.eu5_natives import NativeWorld
    from rnw.geography import Location

PERMILLE: Final[int] = 1000
HUNDREDTHS: Final[int] = 100
VILLAGE: Final[str] = "market_village"
CITY: Final[str] = "city"
TOWN: Final[str] = "town"
CAPITAL: Final[str] = "capital"
MEMBER: Final[str] = "member"
TRIBE: Final[str] = "tribe"
UNORGANISED: Final[str] = "unorganised"
CLASSES: Final[tuple[str, ...]] = (CITY, TOWN, CAPITAL, MEMBER, TRIBE, UNORGANISED)
HEADER: Final[str] = "\n\t# RNW generated natives\n"
HARBOR_FIELD: Final[str] = "natural_harbor_suitability"
NUMBER: Final[re.Pattern[str]] = re.compile(r"-?[0-9]+(?:\.[0-9]+)?")
# 48 directions, 7.5 degrees apart, as integers scaled by 1024 (cos, sin of k * 7.5 deg).
RAY_SCALE: Final[int] = 1024
RAY_DIRECTIONS: Final[tuple[tuple[int, int], ...]] = (
    (1024, 0), (1015, 134), (989, 265), (946, 392), (887, 512), (812, 623),
    (724, 724), (623, 812), (512, 887), (392, 946), (265, 989), (134, 1015),
    (0, 1024), (-134, 1015), (-265, 989), (-392, 946), (-512, 887), (-623, 812),
    (-724, 724), (-812, 623), (-887, 512), (-946, 392), (-989, 265), (-1015, 134),
    (-1024, 0), (-1015, -134), (-989, -265), (-946, -392), (-887, -512), (-812, -623),
    (-724, -724), (-623, -812), (-512, -887), (-392, -946), (-265, -989), (-134, -1015),
    (0, -1024), (134, -1015), (265, -989), (392, -946), (512, -887), (623, -812),
    (724, -724), (812, -623), (887, -512), (946, -392), (989, -265), (1015, -134),
)  # fmt: skip
# Complexity (permille) from which a location is fully developed is fitted per world
# among these candidates: vanilla's keyed entries lift state land to a similar level on
# any terrain (Mesoamerica +12 on jungle, Great Plains +5), whereas generated worlds differ
# in how much development their physical rules give state land [V-EXEC C75].
FULL_CANDIDATES: Final[range] = range(250, 3001, 5)
SHELTER_REACH: Final[int] = 64
SHELTER_START: Final[int] = 2


class DevelopmentError(ValueError):
    """Vanilla development data is missing or inconsistent."""


@dataclass(frozen=True, slots=True)
class Site:
    """The inputs of one land location's start development."""

    kind: str
    harbour: int
    rank: str
    vegetation: str
    climate: str
    topography: str
    keyed: int


@dataclass(frozen=True, slots=True, eq=False)
class DevelopmentCalibration:
    """Rules and distributions read from the vanilla 1337 Americas."""

    society_max: int
    harbours: tuple[int, ...]
    village_permille: int
    rules: dict[str, int]
    vanilla_means: dict[str, tuple[int, int]]


@dataclass(frozen=True, slots=True, eq=False)
class Development:
    """Generated development inputs, ready to serialize."""

    terms: dict[str, int]
    harbours: dict[str, int]
    villages: tuple[tuple[str, str], ...]
    stats: dict[str, object]


def to_milli(value: str) -> int:
    """A decimal such as ``-0.25`` in thousandths."""
    return _scaled(value, 3)


def to_hundredths(value: str) -> int:
    """A decimal with at most two places in hundredths; more places are an error."""
    return _scaled(value, 2)


def _scaled(value: str, places: int) -> int:
    if not NUMBER.fullmatch(value):
        message = f"Not a decimal number: {value!r}"
        raise DevelopmentError(message)
    sign = -1 if value.startswith("-") else 1
    whole, _, fraction = value.lstrip("-").partition(".")
    if len(fraction.rstrip("0")) > places:
        message = f"More than {places} decimal places: {value!r}"
        raise DevelopmentError(message)
    return sign * (int(whole) * 10**places + int((fraction + "0" * places)[:places]))


def hundredths_text(value: int) -> str:
    """Hundredths as the two-place decimal vanilla writes, such as ``-0.10``."""
    sign = "-" if value < 0 else ""
    return f"{sign}{abs(value) // HUNDREDTHS}.{abs(value) % HUNDREDTHS:02d}"


def development_rules(text: str) -> dict[str, int]:
    """Every numeric entry of the ``development`` block, in thousandths."""
    block = parse(text).block("development")
    if block is None:
        message = "No development block"
        raise DevelopmentError(message)
    return {
        entry.key: to_milli(entry.value)
        for entry in block.entries
        if entry.key is not None and isinstance(entry.value, str) and NUMBER.fullmatch(entry.value)
    }


def template_harbours(text: str) -> dict[str, int]:
    """``natural_harbor_suitability`` of every template that has one, in hundredths."""
    out: dict[str, int] = {}
    for entry in parse(text).entries:
        if entry.key is None or not isinstance(entry.value, Block):
            continue
        field = entry.value.first(HARBOR_FIELD)
        if field is not None and isinstance(field.value, str):
            out[entry.key] = to_hundredths(field.value)
    return out


def _template_fields(text: str, keys: Iterable[str]) -> dict[str, dict[str, str]]:
    """Biome fields and raw harbour value of the named templates."""
    wanted = set(keys)
    names = {"vegetation", "climate", "topography", HARBOR_FIELD}
    out: dict[str, dict[str, str]] = {}
    for entry in parse(text).entries:
        if entry.key not in wanted or not isinstance(entry.value, Block):
            continue
        out[entry.key] = {
            e.key: e.value
            for e in entry.value.entries
            if e.key in names and isinstance(e.value, str)
        }
    return out


def _words(block: Block | None) -> list[str]:
    return [] if block is None else [w.value for w in block.words() if isinstance(w.value, str)]


def site_value(rules: Mapping[str, int], site: Site) -> int:
    """Start development of one location in thousandths, clamped at zero.

    Sums ``base``, ``coastal`` times harbour suitability, the rank, the vegetation,
    climate and topography values and the keyed entries. The river term is left out:
    the engine's river size is unknown [UNKNOWN].
    """
    total = rules.get("base", 0)
    total += rules.get("coastal", 0) * site.harbour // HUNDREDTHS
    total += rules.get(site.rank, 0) if site.rank else 0
    total += sum(rules.get(name, 0) for name in (site.vegetation, site.climate, site.topography))
    return max(0, total + site.keyed)


def class_means(rules: Mapping[str, int], sites: Iterable[Site]) -> dict[str, tuple[int, int]]:
    """Per class: (locations, mean estimated development in thousandths, half up)."""
    sums: dict[str, int] = dict.fromkeys(CLASSES, 0)
    counts: dict[str, int] = dict.fromkeys(CLASSES, 0)
    for site in sites:
        sums[site.kind] += site_value(rules, site)
        counts[site.kind] += 1
    return {kind: (counts[kind], _mean_milli(sums[kind], counts[kind])) for kind in CLASSES}


def _mean_milli(total: int, count: int) -> int:
    return (2 * total + count) // (2 * count) if count else 0


def calibrate(
    *,
    rules_text: str,
    templates_text: str,
    buildings_text: str,
    countries_text: str,
    american: Mapping[str, Location],
) -> DevelopmentCalibration:
    """Society maximum, harbour distribution, village share and class means of vanilla.

    ``american`` holds the vanilla American land locations with their hierarchy.
    """
    rules = development_rules(rules_text)
    if not american:
        message = "No vanilla American land locations"
        raise DevelopmentError(message)
    fields = _template_fields(templates_text, american)
    harbours = {
        key: to_hundredths(found[HARBOR_FIELD])
        for key, found in fields.items()
        if HARBOR_FIELD in found
    }
    keyed = {
        key: sum(rules.get(name, 0) for name in (loc.region, loc.area, loc.province, loc.key))
        for key, loc in american.items()
    }
    society_max = (max(keyed.values()) + PERMILLE // 2) // PERMILLE
    if society_max < 1:
        message = "Vanilla American locations receive no keyed development"
        raise DevelopmentError(message)
    ranks, villages = _buildings(buildings_text)
    members, capitals, holders = _countries(countries_text)
    state_capitals = sorted(c for c in capitals if c in american and c in members)
    if not state_capitals:
        message = "No vanilla American state capitals"
        raise DevelopmentError(message)
    with_village = sum(1 for c in state_capitals if c in villages)
    share = (PERMILLE * with_village + len(state_capitals) // 2) // len(state_capitals)
    sites: list[Site] = []
    for key in american:
        if key not in fields:
            continue
        sites.append(
            Site(
                kind=_kind(key, ranks.get(key, ""), capitals & members, members, holders),
                harbour=harbours.get(key, 0),
                rank=ranks.get(key, ""),
                vegetation=fields[key].get("vegetation", ""),
                climate=fields[key].get("climate", ""),
                topography=fields[key].get("topography", ""),
                keyed=keyed[key],
            )
        )
    american_harbours = sorted(harbours[key] for key in american if key in harbours)
    if not american_harbours:
        message = "No vanilla American harbour values"
        raise DevelopmentError(message)
    return DevelopmentCalibration(
        society_max=society_max,
        harbours=tuple(american_harbours),
        village_permille=share,
        rules=rules,
        vanilla_means=class_means(rules, sites),
    )


def _kind(key: str, rank: str, capitals: set[str], members: set[str], holders: set[str]) -> str:
    if rank in {CITY, TOWN}:
        return rank
    if key in capitals:
        return CAPITAL
    if key in members:
        return MEMBER
    return TRIBE if key in holders else UNORGANISED


def _buildings(text: str) -> tuple[dict[str, str], set[str]]:
    """Ranks of ``locations`` and the locations holding a market village."""
    root = parse(text)
    ranks: dict[str, str] = {}
    for entry in (root.block("locations") or Block()).entries:
        if entry.key is not None and isinstance(entry.value, Block):
            rank = entry.value.first("rank")
            if rank is not None and isinstance(rank.value, str):
                ranks[entry.key] = rank.value
    villages: set[str] = set()
    for entry in (root.block("building_manager") or Block()).find(VILLAGE):
        if isinstance(entry.value, Block):
            where = entry.value.first("location")
            if where is not None and isinstance(where.value, str):
                villages.add(where.value)
    return ranks, villages


def _countries(text: str) -> tuple[set[str], set[str], set[str]]:
    """State locations, state capitals and locations held by pop countries."""
    members: set[str] = set()
    capitals: set[str] = set()
    holders: set[str] = set()
    holder = parse(text).block("countries", "countries")
    for entry in (holder or Block()).entries:
        if entry.key is None or not isinstance(entry.value, Block):
            continue
        kind = entry.value.first("type")
        if kind is not None and kind.value == "pop":
            holders.update(_words(entry.value.block("add_pops_from_locations")))
            continue
        members.update(_words(entry.value.block("own_control_core")))
        members.update(_words(entry.value.block("own_control_integrated")))
        capital = entry.value.first("capital")
        if capital is not None and isinstance(capital.value, str):
            capitals.add(capital.value)
    return members, capitals, holders


def society_term(level: int, society_max: int, full: int) -> int:
    """``society_max`` times a complexity level that counts fully from ``full``, halves up."""
    return (society_max * min(PERMILLE, level * PERMILLE // full) + PERMILLE // 2) // PERMILLE


def society_terms(
    complexity: Mapping[str, int], keys: Sequence[str], society_max: int, full: int
) -> dict[str, int]:
    """Keyed development per location from its complexity (permille).

    Only terms of at least 1 are returned, in key order.
    """
    terms: dict[str, int] = {}
    for key in keys:
        term = society_term(complexity.get(key, 0), society_max, full)
        if term >= 1:
            terms[key] = term
    return terms


def fit_full(
    calibration: DevelopmentCalibration, sites: Sequence[Site], levels: Sequence[int]
) -> int:
    """The saturation whose terms bring generated state land to the vanilla mean.

    ``sites`` carry no keyed entry yet and ``levels`` are their complexities. The estimated
    mean development of state capitals and members together is compared with the vanilla
    one; the smallest candidate with the closest mean wins. Without state land the
    largest candidate is returned.
    """
    state = [
        (site, level)
        for site, level in zip(sites, levels, strict=True)
        if site.kind in {CAPITAL, MEMBER}
    ]
    if not state:
        return FULL_CANDIDATES[-1]
    vanilla = [calibration.vanilla_means[kind] for kind in (CAPITAL, MEMBER)]
    vanilla_count = sum(n for n, _ in vanilla)
    vanilla_total = sum(n * mean for n, mean in vanilla)

    def gap(full: int) -> int:
        total = sum(
            site_value(
                calibration.rules,
                replace(site, keyed=PERMILLE * society_term(level, calibration.society_max, full)),
            )
            for site, level in state
        )
        return abs(total * vanilla_count - vanilla_total * len(state))

    return min(FULL_CANDIDATES, key=lambda full: (gap(full), full))


def shelter(
    water: NDArray[np.bool_],
    docks: NDArray[np.int64],
    *,
    reach: int = SHELTER_REACH,
    start: int = SHELTER_START,
) -> NDArray[np.int64]:
    """Rays out of ``reach`` pixels (48 directions) that meet land, per dock.

    ``docks`` holds (row, column) pairs on the world raster; columns wrap around the
    map and rows are clamped. A ray meets land at the first non-water pixel from
    ``start`` pixels outwards.
    """
    height, width = water.shape
    radii = np.arange(start, reach, dtype=np.int64)
    scores = np.zeros(len(docks), dtype=np.int64)
    for dx, dy in RAY_DIRECTIONS:
        columns = (docks[:, 1:2] + dx * radii[None, :] // RAY_SCALE) % width
        rows = np.clip(docks[:, 0:1] + dy * radii[None, :] // RAY_SCALE, 0, height - 1)
        scores += np.any(~water[rows, columns], axis=1)
    return scores


def harbour_values(scores: Mapping[str, int], harbours: Sequence[int]) -> dict[str, int]:
    """Quantile-map shelter scores onto the sorted vanilla harbour values (hundredths).

    Ports sort by (score, key); the port of 0-based rank ``i`` of ``n`` takes the vanilla
    value at index ``(2i + 1) * m // (2n)`` of the ``m`` sorted values.
    """
    order = sorted(scores, key=lambda key: (scores[key], key))
    count, size = len(order), len(harbours)
    return {key: harbours[(2 * i + 1) * size // (2 * count)] for i, key in enumerate(order)}


def market_villages(
    states: Sequence[tuple[str, str]],
    complexity: Mapping[str, int],
    population: Mapping[str, int],
    permille: int,
) -> tuple[tuple[str, str], ...]:
    """(tag, capital) of the most complex state capitals, a vanilla share of them.

    ``states`` holds (tag, capital); ties break by population, then by capital key.
    """
    count = (len(states) * permille + PERMILLE // 2) // PERMILLE
    ranked = sorted(
        states,
        key=lambda s: (-complexity.get(s[1], 0), -population.get(s[1], 0), s[1]),
    )
    return tuple(ranked[:count])


def development_lines(terms: Mapping[str, int]) -> str:
    """Entries for ``development = { ... }`` of ``14_development.txt``."""
    body = "".join(f"\t{key} = {term}\n" for key, term in terms.items())
    return HEADER + body if body else ""


def building_lines(villages: Sequence[tuple[str, str]]) -> str:
    """Entries for ``building_manager = { ... }`` of ``07_cities_and_buildings.txt``."""
    body = "".join(
        f"\t{VILLAGE} = {{ tag = {tag} level = 1 location = {where} }}\n" for tag, where in villages
    )
    return HEADER + body if body else ""


def spearman_permille(first: Sequence[int], second: Sequence[int]) -> int:
    """Rank correlation in permille (average ranks, exact integer arithmetic)."""
    count = len(first)
    if count < 2:  # noqa: PLR2004 - a correlation needs two points
        return 0
    x, y = _doubled_ranks(first), _doubled_ranks(second)
    sx, sy = sum(x), sum(y)
    top = count * sum(a * b for a, b in zip(x, y, strict=True)) - sx * sy
    low = (count * sum(a * a for a in x) - sx * sx) * (count * sum(b * b for b in y) - sy * sy)
    if low <= 0:
        return 0
    root = math.isqrt(low)
    return (PERMILLE * abs(top) + root // 2) // root * (1 if top >= 0 else -1)


def _doubled_ranks(values: Sequence[int]) -> list[int]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0] * len(values)
    start = 0
    while start < len(order):
        stop = start
        while stop + 1 < len(order) and values[order[stop + 1]] == values[order[start]]:
            stop += 1
        for position in range(start, stop + 1):
            ranks[order[position]] = start + stop
        start = stop + 1
    return ranks


def _histogram(values: Iterable[int]) -> dict[str, int]:
    return {hundredths_text(v): n for v, n in sorted(Counter(values).items())}


def build_development(
    *,
    calibration: DevelopmentCalibration,
    natives: NativeWorld,
    cells: Sequence[tuple[str, str, str, str]],
    scores: Mapping[str, int],
) -> Development:
    """Terms, harbours and market villages of a generated world, with their statistics.

    ``cells`` lists the generated land locations as (key, vegetation, climate,
    topography); ``scores`` maps each port location to its shelter score.
    """
    keys = [key for key, *_ in cells]
    harbours = harbour_values(scores, calibration.harbours) if scores else {}
    sites = generated_sites(natives, cells, harbours)
    full = fit_full(calibration, sites, [natives.complexity.get(key, 0) for key in keys])
    terms = society_terms(natives.complexity, keys, calibration.society_max, full)
    states = [(c.tag, c.capital) for c in natives.countries if c.kind == "state"]
    villages = market_villages(
        states, natives.complexity, natives.population, calibration.village_permille
    )
    parts = Development(terms=terms, harbours=harbours, villages=villages, stats={})
    stats = _stats(calibration, natives, cells, parts, len(states))
    stats["society_full_permille"] = full
    return replace(parts, stats=stats)


def generated_sites(
    natives: NativeWorld, cells: Sequence[tuple[str, str, str, str]], harbours: Mapping[str, int]
) -> list[Site]:
    """Development inputs of the generated land locations, without keyed entries."""
    kinds = _generated_kinds(natives)
    return [
        Site(
            kind=kinds.get(key, UNORGANISED),
            harbour=harbours.get(key, 0),
            rank=natives.ranks[key][0] if key in natives.ranks else "",
            vegetation=vegetation,
            climate=climate,
            topography=topography,
            keyed=0,
        )
        for key, vegetation, climate, topography in cells
    ]


def _stats(
    calibration: DevelopmentCalibration,
    natives: NativeWorld,
    cells: Sequence[tuple[str, str, str, str]],
    parts: Development,
    state_count: int,
) -> dict[str, object]:
    terms, harbours, villages = parts.terms, parts.harbours, parts.villages
    keys = [key for key, *_ in cells]
    sites = [
        replace(site, keyed=PERMILLE * terms.get(key, 0))
        for key, site in zip(keys, generated_sites(natives, cells, harbours), strict=True)
    ]
    generated = class_means(calibration.rules, sites)
    ported = sorted(harbours.values())
    vanilla = list(calibration.harbours)
    return {
        "society_max": calibration.society_max,
        "entries": len(terms),
        "positive_permille": PERMILLE * len(terms) // max(1, len(keys)),
        "population_spearman_permille": spearman_permille(
            [terms.get(key, 0) for key in keys], [natives.population.get(key, 0) for key in keys]
        ),
        "harbours": {
            "generated": _histogram(ported),
            "vanilla": _histogram(vanilla),
            "generated_zero_permille": PERMILLE * ported.count(0) // max(1, len(ported)),
            "vanilla_zero_permille": PERMILLE * vanilla.count(0) // len(vanilla),
            "generated_mean_hundredths": _mean(ported),
            "vanilla_mean_hundredths": _mean(vanilla),
        },
        "market_villages": {
            "count": len(villages),
            "state_capitals": state_count,
            "share_permille": PERMILLE * len(villages) // max(1, state_count),
            "vanilla_share_permille": calibration.village_permille,
        },
        "estimated_mean_hundredths": {
            "generated": {k: [n, (m + 5) // 10] for k, (n, m) in generated.items()},
            "vanilla": {k: [n, (m + 5) // 10] for k, (n, m) in calibration.vanilla_means.items()},
        },
    }


def _mean(values: Sequence[int]) -> int:
    return _mean_milli(sum(values), len(values))


def _generated_kinds(natives: NativeWorld) -> dict[str, str]:
    kinds: dict[str, str] = {}
    for country in natives.countries:
        if country.kind == "state":
            kinds.update(dict.fromkeys(country.members, MEMBER))
            kinds[country.capital] = CAPITAL
        else:
            kinds.update(dict.fromkeys(country.members, TRIBE))
    for key, (rank, _) in natives.ranks.items():
        kinds[key] = rank
    return kinds
