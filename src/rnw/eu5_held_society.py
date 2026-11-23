"""The society of a restored country's African holdings, carried onto the generated ones.

Morocco and the Mamluks keep their tags when Africa is generated, but their African land is
replaced. The generated cells reserved for them start as tribal ground, and a country made of
tribesmen has no tax base, no levies and no market. Each reserved holding takes over one
donor, a location the country owned in the installed 1337 start: its pops, its town and
buildings, its institutions and its market travel together. The capital takes the capital's;
the others pair by size and by how much the generated ground can carry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.eu5_start import PopCohort
from rnw.pdx import Block, parse

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

PERMILLE: Final[int] = 1000
# Pop types that farm or trade; a location of tribesmen alone is not settled.
SETTLED: Final[frozenset[str]] = frozenset({"peasants", "slaves", "burghers"})
# The share of settled pops at which the generator's complexity is full (societies.PEASANT_PEAK).
FULL_SETTLED_PERMILLE: Final[int] = 600
# A unique monument is bound to its place in vanilla and does not travel.
UNTRAVELLED_PREFIX: Final[str] = "monument_"
POPS_FILE: Final[str] = "06_pops.txt"
TOWNS_FILE: Final[str] = "07_cities_and_buildings.txt"
MARKETS_FILE: Final[str] = "03_markets.txt"
INSTITUTIONS_FILE: Final[str] = "08_institutions.txt"


class HeldSocietyError(ValueError):
    """A donor or a reserved holding cannot be paired."""


@dataclass(frozen=True, slots=True)
class Donor:
    """One location of the installed 1337 start as its country held it in Africa."""

    key: str
    pops: tuple[PopCohort, ...]
    rank: tuple[str, str] | None
    market: bool
    institutions: tuple[tuple[str, str], ...]
    buildings: tuple[tuple[str, int], ...]

    @property
    def coastal(self) -> bool:
        """Whether its town is a coastal one, with a wharf the sea must reach."""
        return self.rank is not None and "coastal" in self.rank[1]

    @property
    def population(self) -> int:
        return sum(pop.amount for pop in self.pops)

    @property
    def complexity(self) -> int:
        """Complexity as the societies model has it: settled share of the pops over its peak."""
        total = self.population
        settled = sum(pop.amount for pop in self.pops if pop.kind in SETTLED)
        if total <= 0:
            return 0
        return min(PERMILLE, settled * PERMILLE * PERMILLE // (total * FULL_SETTLED_PERMILLE))


@dataclass(frozen=True, slots=True)
class HeldSociety:
    """What the reserved generated holdings carry, keyed by their own location keys."""

    pops: dict[str, tuple[PopCohort, ...]]
    ranks: dict[str, tuple[str, str]]
    markets: tuple[str, ...]
    complexity: dict[str, int]
    institutions: dict[str, tuple[tuple[str, str], ...]]
    buildings: tuple[tuple[str, str, int, str], ...]

    def merge(self, other: HeldSociety) -> HeldSociety:
        overlap = self.pops.keys() & other.pops.keys()
        if overlap:
            message = f"Holding {min(overlap)} takes the society of two donors"
            raise HeldSocietyError(message)
        return HeldSociety(
            self.pops | other.pops,
            self.ranks | other.ranks,
            self.markets + other.markets,
            self.complexity | other.complexity,
            self.institutions | other.institutions,
            self.buildings + other.buildings,
        )


EMPTY: Final[HeldSociety] = HeldSociety({}, {}, (), {}, {}, ())


def _milli(value: str) -> int:
    whole, _, fraction = value.partition(".")
    return int(whole or "0") * PERMILLE + int((fraction + "000")[:3])


def _pops_of(texts: Mapping[str, str], keys: Collection[str]) -> dict[str, tuple[PopCohort, ...]]:
    holder = parse(texts[POPS_FILE]).block("locations")
    found: dict[str, tuple[PopCohort, ...]] = {}
    for entry in holder.entries if holder is not None else ():
        if entry.key not in keys or not isinstance(entry.value, Block):
            continue
        rows: list[PopCohort] = []
        for pop in entry.value.find("define_pop"):
            if not isinstance(pop.value, Block):
                continue
            fields = {e.key: e.value for e in pop.value.entries if isinstance(e.value, str)}
            rows.append(
                PopCohort(
                    fields.get("type", ""),
                    _milli(fields.get("size", "0")),
                    fields.get("culture", ""),
                    fields.get("religion", ""),
                )
            )
        found[entry.key or ""] = tuple(rows)
    return found


def _ranks_of(texts: Mapping[str, str], keys: Collection[str]) -> dict[str, tuple[str, str]]:
    holder = parse(texts[TOWNS_FILE]).block("locations")
    found: dict[str, tuple[str, str]] = {}
    for entry in holder.entries if holder is not None else ():
        if entry.key not in keys or not isinstance(entry.value, Block):
            continue
        fields = {e.key: e.value for e in entry.value.entries if isinstance(e.value, str)}
        if fields.get("rank") and fields.get("town_setup"):
            found[entry.key or ""] = (fields["rank"], fields["town_setup"])
    return found


def _buildings_of(
    texts: Mapping[str, str], keys: Collection[str], owner: str
) -> dict[str, list[tuple[str, int]]]:
    manager = parse(texts[TOWNS_FILE]).block("building_manager")
    found: dict[str, list[tuple[str, int]]] = {}
    for entry in manager.entries if manager is not None else ():
        if (
            not isinstance(entry.value, Block)
            or entry.key is None
            or entry.key.startswith(UNTRAVELLED_PREFIX)
        ):
            continue
        tag, where, level = (entry.value.first(name) for name in ("tag", "location", "level"))
        if (
            tag is not None
            and where is not None
            and tag.value == owner
            and where.value in keys
            and level is not None
            and isinstance(level.value, str)
        ):
            found.setdefault(str(where.value), []).append((entry.key, int(level.value)))
    return found


def _institutions_of(
    texts: Mapping[str, str], keys: Collection[str]
) -> dict[str, tuple[tuple[str, str], ...]]:
    holder = parse(texts[INSTITUTIONS_FILE]).block("locations")
    found: dict[str, tuple[tuple[str, str], ...]] = {}
    for entry in holder.entries if holder is not None else ():
        if entry.key not in keys or not isinstance(entry.value, Block):
            continue
        found[entry.key or ""] = tuple(
            (str(e.key), e.value)
            for e in entry.value.entries
            if e.key is not None and isinstance(e.value, str)
        )
    return found


def _markets_of(texts: Mapping[str, str]) -> set[str]:
    manager = parse(texts[MARKETS_FILE]).block("market_manager")
    return {
        entry.value
        for entry in (manager.find("add_market") if manager is not None else ())
        if isinstance(entry.value, str)
    }


def read_donors(texts: Mapping[str, str], keys: Collection[str], owner: str) -> dict[str, Donor]:
    """The donors among ``keys`` of the installed 1337 start; ``owner`` is the building tag."""
    pops = _pops_of(texts, keys)
    ranks = _ranks_of(texts, keys)
    buildings = _buildings_of(texts, keys, owner)
    institutions = _institutions_of(texts, keys)
    markets = _markets_of(texts)
    missing = sorted(set(keys) - pops.keys())
    if missing or any(not rows for rows in pops.values()):
        message = (
            f"The installed 1337 start has no population for {', '.join(missing) or 'a donor'}"
        )
        raise HeldSocietyError(message)
    return {
        key: Donor(
            key,
            pops[key],
            ranks.get(key),
            key in markets,
            institutions.get(key, ()),
            tuple(buildings.get(key, ())),
        )
        for key in sorted(keys)
    }


def pair_holdings(  # noqa: PLR0913, PLR0917 - the donors, the holdings and the ground.
    donors: Mapping[str, Donor],
    donor_capital: str,
    holdings: Sequence[str],
    capital: str,
    potential: Mapping[str, int],
    coastal: Collection[str] = (),
) -> dict[str, str]:
    """Holding -> donor: capital to capital, coastal towns to the shore, then size to ground.

    Within each step the largest donors take the holdings with the best ground.
    """
    if len(donors) != len(holdings) or capital not in holdings or donor_capital not in donors:
        message = "Holdings and donors do not pair one to one around their capitals"
        raise HeldSocietyError(message)
    pairs = {capital: donor_capital}
    others = sorted(
        (key for key in donors if key != donor_capital),
        key=lambda key: (-donors[key].population, key),
    )
    places = sorted(
        (key for key in holdings if key != capital),
        key=lambda key: (-potential.get(key, 0), key),
    )
    shore = [key for key in places if key in coastal]
    for donor in [key for key in others if donors[key].coastal][: len(shore)]:
        place = shore.pop(0)
        pairs[place] = donor
        places.remove(place)
        others.remove(donor)
    return pairs | dict(zip(places, others, strict=True))


def carry_society(donors: Mapping[str, Donor], pairs: Mapping[str, str], owner: str) -> HeldSociety:
    """The society of every paired holding, written under the holding's own key."""
    pops: dict[str, tuple[PopCohort, ...]] = {}
    ranks: dict[str, tuple[str, str]] = {}
    markets: list[str] = []
    complexity: dict[str, int] = {}
    institutions: dict[str, tuple[tuple[str, str], ...]] = {}
    buildings: list[tuple[str, str, int, str]] = []
    for holding, key in sorted(pairs.items()):
        donor = donors[key]
        pops[holding] = donor.pops
        complexity[holding] = donor.complexity
        if donor.rank is not None:
            ranks[holding] = donor.rank
        if donor.market:
            markets.append(holding)
        if donor.institutions:
            institutions[holding] = donor.institutions
        buildings.extend((kind, owner, level, holding) for kind, level in donor.buildings)
    return HeldSociety(pops, ranks, tuple(markets), complexity, institutions, tuple(buildings))


def institution_lines(society: HeldSociety) -> str:
    """Entries for ``locations = { ... }`` of ``08_institutions.txt``."""
    body = "".join(
        f"{key} = {{\n" + "".join(f"\t{name} = {value}\n" for name, value in rows) + "}\n"
        for key, rows in sorted(society.institutions.items())
    )
    return "\n# RNW restored holdings\n" + body if body else ""


def building_lines(society: HeldSociety) -> str:
    """Entries for ``building_manager = { ... }`` of ``07_cities_and_buildings.txt``."""
    body = "".join(
        f"\t{kind} = {{ tag = {tag} level = {level} location = {where} }}\n"
        for kind, tag, level, where in society.buildings
    )
    return "\n\t# RNW restored holdings\n" + body if body else ""
