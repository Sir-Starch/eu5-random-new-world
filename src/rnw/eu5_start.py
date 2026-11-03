"""The final native start plan, shared by writers, checks, content, AI and atlas.

Construction owns the facts here. Serialization belongs to the EU5 adapters; readers
must not recover population or identity by parsing generated script (history plan H1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rnw.wording import Name


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
    level: int | None = None
    great: bool = False
    rank: str = ""
    landed: bool = False
    currency: tuple[tuple[str, int], ...] = ()
    archetype: str = ""
    laws: tuple[tuple[str, str], ...] = ()
    parliament: str = ""


@dataclass(frozen=True, slots=True)
class PopCohort:
    """One pop's type, milli-population and identities, before script serialization."""

    kind: str
    amount: int
    culture: str
    religion: str


@dataclass(frozen=True, slots=True, eq=False)
class FinalStartPlan:
    """The complete projected start state; static construction supplies it in H1.

    H4 will replace that construction with history's surviving outcomes. Writers and
    verifiers consume this same boundary, including tribes and unorganized population.
    ``population`` retains the calibrated society budget; ``pops`` also contains the
    existing additive diaspora cohorts. H1 deliberately preserves that distinction.
    """

    pops: dict[str, tuple[PopCohort, ...]]
    countries: tuple[Country, ...]
    ranks: dict[str, tuple[str, str]]
    markets: tuple[str, ...]
    holy_sites: dict[str, str]
    names: dict[str, Name]
    vassals: tuple[tuple[str, str], ...]
    complexity: dict[str, int]
    population: dict[str, int]
    stats: dict[str, object]
    technology: dict[str, object] = field(default_factory=dict)
    roads: tuple[tuple[str, str], ...] = ()
    opinions: tuple[tuple[str, str, str], ...] = ()
    extraordinary: dict[str, object] = field(default_factory=dict)
    alliances: tuple[tuple[str, str], ...] = ()
    rivals: tuple[tuple[str, str], ...] = ()
    confederations: tuple[tuple[str, ...], ...] = ()
    confederation_date: str = ""
    archetypes: dict[str, object] = field(default_factory=dict)
