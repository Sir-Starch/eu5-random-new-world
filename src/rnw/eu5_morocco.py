"""The start rule for Morocco's retained Iberian holdings when Africa is regenerated."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from rnw.eu5_natives import country_records, map_colors, new_tags
from rnw.eu5_rewrite import (
    drop_block_entries,
    owned_locations,
    prune_regional_setup,
)
from rnw.eu5_start import Country
from rnw.pdx import Block, Edits, parse
from rnw.rng import derive_seed
from rnw.societies import STATE

if TYPE_CHECKING:
    from collections.abc import Mapping

    from rnw.eu5_rewrite import SetupResult
    from rnw.loc_keys import KeySpace

MOROCCO: Final[str] = "MOR"
CASTILE: Final[str] = "CAS"
GRANADA: Final[str] = "GRA"
IBERIAN_HOLDINGS: Final[tuple[str, ...]] = ("ronda", "algeciras", "gibraltar", "marbella")
AFRICAN_HOLDINGS: Final[int] = 86
COUNTRIES_FILE: Final[str] = "10_countries.txt"
COUNTRIES_BLOCK: Final[tuple[str, ...]] = ("countries", "countries")
type Point = tuple[int, int]


class MoroccoPolicy(StrEnum):
    """Selectable results for the 1337 start when Africa is generated."""

    RESTORE = "restore"
    EMIRATE = "emirate"
    CASTILE = "castile"
    GRANADA = "granada"


DEFAULT_MOROCCO_POLICY: Final[MoroccoPolicy] = MoroccoPolicy.RESTORE


class MoroccoError(ValueError):
    """The selected result cannot be built from the start map and country data."""


@dataclass(frozen=True, slots=True)
class MoroccoStart:
    """Territory reserved before any other polity can claim it."""

    policy: MoroccoPolicy
    africa: tuple[str, ...] = ()
    capital: str = ""


def _distance(first: Point, second: Point, width: int) -> int:
    across = abs(first[1] - second[1]) % width
    return (first[0] - second[0]) ** 2 + min(across, width - across) ** 2


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
        raise MoroccoError(message)
    if width <= 0 or len(africa) < AFRICAN_HOLDINGS:
        message = f"Morocco requires {AFRICAN_HOLDINGS} passable locations in generated Africa"
        raise MoroccoError(message)
    european = [original[key] for key in IBERIAN_HOLDINGS]
    ranked = sorted(
        africa,
        key=lambda key: (min(_distance(africa[key], point, width) for point in european), key),
    )
    owned = tuple(ranked[:AFRICAN_HOLDINGS])
    capital = min(owned, key=lambda key: (_distance(africa[key], original["fez"], width), key))
    return MoroccoStart(policy, owned, capital)


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


def _countries(text: str) -> Block:
    countries = parse(text).block(*COUNTRIES_BLOCK)
    if countries is None:
        message = "Missing 1337 country records"
        raise MoroccoError(message)
    return countries


def _grant(text: str, tag: str, field: str, locations: tuple[str, ...]) -> str:
    country = _countries(text).block(tag)
    if country is None:
        message = f"Missing 1337 recipient {tag}"
        raise MoroccoError(message)
    if owned_locations(country).intersection(locations):
        message = f"Recipient {tag} already owns one of its new holdings"
        raise MoroccoError(message)
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
            raise MoroccoError(message)


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
) -> SetupResult:
    """Apply the reservation in the 1337 setup and retire Morocco where selected."""
    prepared = texts.copy()
    text = prepared[COUNTRIES_FILE]
    countries = _countries(text)
    morocco = countries.block(MOROCCO)
    expected: set[str] = set(IBERIAN_HOLDINGS)
    if morocco is None or owned_locations(morocco) - removed != expected:
        message = "Morocco's surviving territory does not match its four 1337 Iberian holdings"
        raise MoroccoError(message)
    if expected - final_locations:
        message = "Morocco's four Iberian holdings must exist on the finished map"
        raise MoroccoError(message)
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
            raise MoroccoError(message)
        capitals[MOROCCO] = start.capital
        places["fez"] = start.capital
        prepared[COUNTRIES_FILE] = _grant(text, MOROCCO, "own_control_core", start.africa)
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
                raise MoroccoError(message)
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
    )
    _verify_ownership(result.texts[COUNTRIES_FILE], recipient, expected)
    return result
