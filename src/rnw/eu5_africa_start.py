"""Start rules for African countries with retained territory outside Africa."""

# NumPy scalar conversions are typed dynamically.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final

from rnw.eu5_natives import country_records, map_colors, new_tags
from rnw.eu5_rewrite import (
    drop_block_entries,
    owned_locations,
    prune_regional_setup,
)
from rnw.eu5_start import Country
from rnw.model import CellClass
from rnw.pdx import Block, Edits, parse
from rnw.rng import derive_seed
from rnw.settings import DEFAULT_MOROCCO_POLICY, MamlukPolicy, MoroccoPolicy
from rnw.societies import STATE

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from rnw.eu5_newworld import Plan
    from rnw.eu5_rewrite import SetupResult
    from rnw.geography import Location
    from rnw.loc_keys import KeySpace
    from rnw.newworld import NewWorld

MOROCCO: Final[str] = "MOR"
MAMLUKS: Final[str] = "MAM"
CAIRO: Final[str] = "cairo"
DAMASCUS: Final[str] = "damascus"
CASTILE: Final[str] = "CAS"
GRANADA: Final[str] = "GRA"
IBERIAN_HOLDINGS: Final[tuple[str, ...]] = ("ronda", "algeciras", "gibraltar", "marbella")
AFRICAN_HOLDINGS: Final[int] = 86
COUNTRIES_FILE: Final[str] = "10_countries.txt"
COUNTRIES_BLOCK: Final[tuple[str, ...]] = ("countries", "countries")
type Point = tuple[int, int]


class AfricanStartError(ValueError):
    """The selected result cannot be built from the start map and country data."""


@dataclass(frozen=True, slots=True)
class MoroccoStart:
    """Territory reserved before any other polity can claim it."""

    policy: MoroccoPolicy
    africa: tuple[str, ...] = ()
    capital: str = ""
    capital_province: str = ""


@dataclass(frozen=True, slots=True)
class MamlukStart:
    """Asian holdings and their replacement territory in Africa."""

    asia: frozenset[str]
    core: tuple[str, ...]
    integrated: tuple[str, ...]
    capital: str
    policy: MamlukPolicy

    @property
    def africa(self) -> tuple[str, ...]:
        return self.core + self.integrated


def _distance(first: Point, second: Point, width: int) -> int:
    across = abs(first[1] - second[1]) % width
    return (first[0] - second[0]) ** 2 + min(across, width - across) ** 2


def _nearest_holdings(
    africa: Mapping[str, Point], origins: Collection[Point], width: int, count: int
) -> tuple[str, ...]:
    return tuple(
        sorted(
            africa,
            key=lambda key: (min(_distance(africa[key], point, width) for point in origins), key),
        )[:count]
    )


def _african_points(plan: Plan, world: NewWorld) -> dict[str, Point]:
    return {
        cell.key: (int(world.centroids[i, 0]), int(world.centroids[i, 1]))
        for i, cell in enumerate(plan.cells)
        if cell.kind is CellClass.LAND and cell.continent == "africa"
    }


def plan_morocco(
    africa: Mapping[str, Point],
    original: Mapping[str, Point],
    width: int,
    policy: MoroccoPolicy = DEFAULT_MOROCCO_POLICY,
) -> MoroccoStart:
    """Reserve nearest passable African locations by wrapped centre distance.

    Callers supply final passable African candidates. The four Iberian centres
    act as one set of origins, and a location's key breaks equal-distance ties.
    The capital is chosen within those holdings using the centre of vanilla Fez.
    """
    if policy is not MoroccoPolicy.RESTORE:
        return MoroccoStart(policy)
    missing = {*IBERIAN_HOLDINGS, "fez"} - original.keys()
    if missing:
        message = f"Missing original Moroccan locations: {', '.join(sorted(missing))}"
        raise AfricanStartError(message)
    if width <= 0 or len(africa) < AFRICAN_HOLDINGS:
        message = f"Morocco requires {AFRICAN_HOLDINGS} passable locations in generated Africa"
        raise AfricanStartError(message)
    owned = _nearest_holdings(
        africa, [original[key] for key in IBERIAN_HOLDINGS], width, AFRICAN_HOLDINGS
    )
    capital = min(owned, key=lambda key: (_distance(africa[key], original["fez"], width), key))
    return MoroccoStart(policy, owned, capital)


def reserve_morocco(
    plan: Plan,
    world: NewWorld,
    original: Mapping[str, Point],
    policy: MoroccoPolicy,
) -> MoroccoStart:
    """Reserve 1337 ownership against the finished passable African locations."""
    start = plan_morocco(_african_points(plan, world), original, int(world.labels.shape[1]), policy)
    if start.capital:
        province = next(cell.province for cell in plan.cells if cell.key == start.capital)
        return replace(start, capital_province=province)
    return start


def plan_mamluks(  # noqa: PLR0913 - original ownership and both maps.
    africa: Mapping[str, Point],
    original: Mapping[str, Point],
    width: int,
    territory: Block,
    original_africa: Collection[str],
    *,
    reserved: Collection[str] = (),
    policy: MamlukPolicy = MamlukPolicy.RESTORE,
) -> MamlukStart:
    """Reserve the same amount of land as in the installed 1337 start."""
    owned = owned_locations(territory)
    replaced = owned.intersection(original_africa)
    asia = owned - replaced
    core = territory.block("own_control_core")
    integrated = territory.block("own_control_integrated")
    core_count = len(replaced.intersection(word.value for word in core.words())) if core else 0
    integrated_count = (
        len(replaced.intersection(word.value for word in integrated.words())) if integrated else 0
    )
    capital = territory.first("capital")
    if (
        capital is None
        or capital.value != CAIRO
        or CAIRO not in replaced
        or not asia
        or not core_count
        or core_count + integrated_count != len(replaced)
        or (asia | {CAIRO}) - original.keys()
    ):
        message = "Missing or unexpected Mamluk territory in the installed 1337 start"
        raise AfricanStartError(message)
    if policy is MamlukPolicy.DAMASCUS:
        if DAMASCUS not in asia:
            message = "The independent sultanate needs Damascus among the retained holdings"
            raise AfricanStartError(message)
        return MamlukStart(frozenset(asia), (), (), DAMASCUS, policy)
    available = {key: point for key, point in africa.items() if key not in reserved}
    if width <= 0 or len(available) < len(replaced):
        message = f"The Mamluks require {len(replaced)} unreserved passable locations in Africa"
        raise AfricanStartError(message)
    holdings = _nearest_holdings(available, [original[key] for key in asia], width, len(replaced))
    ranked = sorted(holdings, key=lambda key: (_distance(africa[key], original[CAIRO], width), key))
    return MamlukStart(
        frozenset(asia), tuple(ranked[:core_count]), tuple(ranked[core_count:]), ranked[0], policy
    )


def reserve_mamluks(  # noqa: PLR0913 - the installed setup and finished map.
    plan: Plan,
    world: NewWorld,
    original: Mapping[str, Point],
    text: str,
    original_africa: Collection[str],
    *,
    reserved: Collection[str],
    policy: MamlukPolicy,
) -> MamlukStart:
    mamluks = _countries(text).block(MAMLUKS)
    if mamluks is None:
        message = "The installed 1337 start is missing the Mamluks"
        raise AfricanStartError(message)
    return plan_mamluks(
        _african_points(plan, world),
        original,
        int(world.labels.shape[1]),
        mamluks,
        original_africa,
        reserved=reserved,
        policy=policy,
    )


def algeciras(
    seed: int,
    reserved: frozenset[str],
    keys: KeySpace,
    colors: frozenset[tuple[int, int, int]],
) -> Country:
    """Build a separate Andalusi Sunni state from the local 1337 precedent."""
    key = derive_seed(seed, "africa", "algeciras")
    (tag,) = new_tags(1, reserved, key, keys)
    ((color, color2),) = map_colors([set()], key, colors)
    return Country(
        tag=tag,
        name="Algeciras",
        kind=STATE,
        members=IBERIAN_HOLDINGS,
        capital="algeciras",
        culture="andalusi",
        religion="sunni",
        include="muslim_monarchy_no_abrahamic_dhimmi",
        areas=(),
        color=color,
        color2=color2,
        level=3,
        rank="rank_duchy",
    )


def damascus_sultanate(  # noqa: PLR0913, PLR0917 - geography and shared country allocators.
    start: MamlukStart,
    hierarchy: Mapping[str, Location],
    seed: int,
    reserved: frozenset[str],
    keys: KeySpace,
    colors: frozenset[tuple[int, int, int]],
) -> Country:
    """Build a Sunni Levantine monarchy with a new tag and capital in Damascus."""
    key = derive_seed(seed, "africa", "damascus")
    (tag,) = new_tags(1, reserved, key, keys)
    ((color, color2),) = map_colors([set()], key, colors)
    return Country(
        tag=tag,
        name="Sultanate of Damascus",
        kind=STATE,
        members=tuple(sorted(start.asia)),
        capital=DAMASCUS,
        culture="levantine_culture",
        religion="sunni",
        include="muslim_monarchy",
        areas=tuple(sorted({hierarchy[location].area for location in start.asia})),
        color=color,
        color2=color2,
        government=(("type", "monarchy"), ("heir_selection", "cognatic_primogeniture")),
        rank="rank_kingdom",
    )


def _countries(text: str) -> Block:
    countries = parse(text).block(*COUNTRIES_BLOCK)
    if countries is None:
        message = "Missing 1337 country records"
        raise AfricanStartError(message)
    return countries


def _grant(text: str, tag: str, field: str, locations: tuple[str, ...]) -> str:
    country = _countries(text).block(tag)
    if country is None:
        message = f"Missing 1337 recipient {tag}"
        raise AfricanStartError(message)
    if owned_locations(country).intersection(locations):
        message = f"Recipient {tag} already owns one of its new holdings"
        raise AfricanStartError(message)
    edits = Edits()
    members = " ".join(locations)
    current = country.block(field)
    if current is None:
        edits.insert(country.open + 1, f"\n\t\t{field} = {{ {members} }}\n")
    else:
        edits.insert(current.close, f" {members} ")
    return edits.apply(text)


def _verify_ownership(text: str, tag: str, expected: set[str]) -> None:
    owners: dict[str, list[str]] = {key: [] for key in expected}
    for entry in _countries(text).entries:
        if entry.key and isinstance(entry.value, Block):
            for key in expected.intersection(owned_locations(entry.value)):
                owners[key].append(entry.key)
    for key, tags in owners.items():
        if tags != [tag]:
            message = f"Expected {key} to belong only to {tag}, got {tags}"
            raise AfricanStartError(message)


def prepare_mamluk_start(
    start: MamlukStart,
    text: str,
    removed: set[str],
    final_locations: set[str],
    sultanate: Country | None,
) -> str:
    """Add the new owner or African holdings before pruning the original setup."""
    countries = _countries(text)
    mamluks = countries.block(MAMLUKS)
    if (
        mamluks is None
        or frozenset(owned_locations(mamluks) - removed) != start.asia
        or start.asia - final_locations
    ):
        message = "Mamluk territory must contain its retained Asian holdings"
        raise AfricanStartError(message)
    if start.policy is MamlukPolicy.DAMASCUS:
        if (
            sultanate is None
            or frozenset(sultanate.members) != start.asia
            or sultanate.capital != DAMASCUS
            or countries.first(sultanate.tag) is not None
        ):
            message = "The Sultanate of Damascus needs a fresh tag and all the Asian holdings"
            raise AfricanStartError(message)
        remaining = drop_block_entries(text, COUNTRIES_BLOCK, {MAMLUKS})
        edits = Edits()
        edits.insert(_countries(remaining).close, country_records((sultanate,)))
        return edits.apply(remaining)
    new_land = set(start.africa)
    if (
        len(new_land) != len(start.africa)
        or new_land & (start.asia | removed)
        or new_land - final_locations
        or start.capital not in start.core
    ):
        message = "Mamluk territory must contain its retained holdings and a new African capital"
        raise AfricanStartError(message)
    text = _grant(text, MAMLUKS, "own_control_core", start.core)
    if start.integrated:
        text = _grant(text, MAMLUKS, "own_control_integrated", start.integrated)
    return text


def verify_mamluk_start(start: MamlukStart, text: str, tag: str) -> None:
    _verify_ownership(text, tag, set(start.asia).union(start.africa))
    mamluks = _countries(text).block(tag)
    capital = mamluks.first("capital") if mamluks is not None else None
    if capital is None or capital.value != start.capital:
        message = f"The 1337 capital of {tag} must be {start.capital}"
        raise AfricanStartError(message)


def _discover_capital(text: str, province: str) -> str:
    # The vanilla rivalry survives and Castile already knew Morocco's old seat.
    castile = _countries(text).block(CASTILE)
    if castile is None or not province:
        message = "Castile needs the new Moroccan capital's province for its starting rivalry"
        raise AfricanStartError(message)
    edits = Edits()
    known = castile.block("discovered_provinces")
    if known is None:
        edits.insert(castile.open + 1, f"\n\t\tdiscovered_provinces = {{ {province} }}\n")
    elif all(word.value != province for word in known.words()):
        edits.insert(known.close, f" {province} ")
    return edits.apply(text)


def apply_morocco_start(  # noqa: PLR0913 - the selected policy and its regional setup inputs.
    start: MoroccoStart,
    texts: dict[str, str],
    removed: set[str],
    pops_added: dict[str, list[str]],
    *,
    location_replacements: Mapping[str, str],
    replacement_capitals: Mapping[str, str],
    final_locations: set[str],
    emirate: Country | None = None,
    surviving_places: Collection[str] = (),
) -> SetupResult:
    """Apply the reservation in the 1337 setup and retire Morocco where selected."""
    prepared = texts.copy()
    text = prepared[COUNTRIES_FILE]
    countries = _countries(text)
    morocco = countries.block(MOROCCO)
    expected: set[str] = set(IBERIAN_HOLDINGS)
    if morocco is None or owned_locations(morocco) - removed != expected:
        message = "Morocco's surviving territory does not match its four 1337 Iberian holdings"
        raise AfricanStartError(message)
    if expected - final_locations:
        message = "Morocco's four Iberian holdings must exist on the finished map"
        raise AfricanStartError(message)
    capitals = dict(replacement_capitals)
    places = dict(location_replacements)
    discarded = set(removed)
    if start.policy is MoroccoPolicy.RESTORE:
        new_land = set(start.africa)
        if (
            len(start.africa) != AFRICAN_HOLDINGS
            or len(new_land) != AFRICAN_HOLDINGS
            or new_land & (expected | removed)
            or new_land - final_locations
            or start.capital not in new_land
        ):
            message = "Morocco needs 86 distinct new African holdings and a capital among them"
            raise AfricanStartError(message)
        capitals[MOROCCO] = start.capital
        places["fez"] = start.capital
        prepared[COUNTRIES_FILE] = _discover_capital(
            _grant(text, MOROCCO, "own_control_core", start.africa), start.capital_province
        )
        recipient = MOROCCO
        expected.update(start.africa)
    else:
        discarded.add(MOROCCO)
        prepared[COUNTRIES_FILE] = drop_block_entries(text, COUNTRIES_BLOCK, {MOROCCO})
        if start.policy in (MoroccoPolicy.CASTILE, MoroccoPolicy.GRANADA):
            recipient = CASTILE if start.policy is MoroccoPolicy.CASTILE else GRANADA
            prepared[COUNTRIES_FILE] = _grant(
                prepared[COUNTRIES_FILE], recipient, "own_control_integrated", IBERIAN_HOLDINGS
            )
        else:
            if (
                emirate is None
                or emirate.members != IBERIAN_HOLDINGS
                or emirate.capital not in expected
                or countries.first(emirate.tag) is not None
            ):
                message = "The Emirate needs its own unused tag and all four Iberian holdings"
                raise AfricanStartError(message)
            recipient = emirate.tag
            remaining = prepared[COUNTRIES_FILE]
            edits = Edits()
            edits.insert(_countries(remaining).close, country_records((emirate,)))
            prepared[COUNTRIES_FILE] = edits.apply(remaining)
    result = prune_regional_setup(
        prepared,
        discarded,
        pops_added,
        location_replacements=places,
        replacement_capitals=capitals,
        final_locations=final_locations,
        surviving_places=surviving_places,
    )
    _verify_ownership(result.texts[COUNTRIES_FILE], recipient, expected)
    return result
