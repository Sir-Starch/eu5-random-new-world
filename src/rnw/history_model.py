"""Game-independent, integer history facts and sparse, replayable transitions (H2)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

START: Final[int] = 1037
END: Final[int] = 1337
YEARS: Final[int] = 5
PERMILLE: Final[int] = 1000
MAX_PROPOSALS: Final[int] = 3
MIN_PARTITIONS: Final[int] = 2


class HistoryError(ValueError):
    """Invalid bootstrap, proposal or causal record; never repaired implicitly."""


class Tenure(StrEnum):
    LAND = "land"
    TRIBE = "tribe"
    COMMUNITY = "community"


class Authority(StrEnum):
    COUNCIL = "council"
    RULER = "ruler"
    SACRED = "sacred"
    CUSTOMARY = "customary"


class Action(StrEnum):
    FOUNDATION = "foundation"
    CONTACT = "contact"
    EXCHANGE = "exchange"
    UNION = "union"
    CONFLICT = "conflict"
    DEPENDENCY = "dependency"
    PROTECTION = "protection"
    PACT = "pact"
    SEPARATION = "separation"
    ACCESS = "access"


class Outcome(StrEnum):
    ACCEPTED = "accepted"
    REFUSED = "refused"
    FAILED = "failed"


class Reason(StrEnum):
    ORIGIN = "origin"
    ENCOUNTER = "encounter"
    COOPERATION = "cooperation"
    BARGAIN = "bargain"
    GRIEVANCE = "grievance"
    OPPORTUNITY = "opportunity"
    IMBALANCE = "imbalance"
    OBLIGATIONS = "obligations"
    THREAT = "threat"
    SACRED_ACCESS = "sacred_access"
    INELIGIBLE = "ineligible"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown_partner"
    SUPPORT = "insufficient_support"
    HOSTILE = "hostile"
    COMMITTED = "already_committed"
    DUPLICATE = "duplicate"
    REPELLED = "repelled"


class Factor(StrEnum):
    TRUST = "trust"
    GRIEVANCE = "grievance"
    FEAR = "fear"
    DEPENDENCE = "dependence"
    COMPETITION = "competition"
    AFFINITY = "affinity"


@dataclass(frozen=True, slots=True)
class Cohort:
    culture: str
    religion: str
    population: int
    peasants: int


@dataclass(frozen=True, slots=True)
class District:
    key: str
    region: str
    tenure: Tenure
    cohorts: tuple[Cohort, ...]
    coastal: bool = False
    defence: int = PERMILLE
    sacred: bool = False

    @property
    def population(self) -> int:
        return sum(pop.population for pop in self.cohorts)

    @property
    def peasants(self) -> int:
        return sum(pop.peasants for pop in self.cohorts)


@dataclass(frozen=True, slots=True)
class Route:
    """Verified physical contact, including a bounded water path between actual coasts."""

    first: str
    second: str
    cost: int = PERMILLE
    sea_steps: int = 0


@dataclass(frozen=True, slots=True)
class Rules:
    minimum_peasants: int = 1
    minimum_share: int = 1
    max_sea_steps: int = 4
    union_trust: int = 120
    minimum_overlord_technology: int = 1


@dataclass(frozen=True, slots=True)
class Geography:
    districts: tuple[District, ...]
    routes: tuple[Route, ...]
    rules: Rules = Rules()


@dataclass(frozen=True, slots=True)
class Founding:
    key: str
    tenure: Tenure
    districts: tuple[str, ...]
    seat: str
    authority: Authority = Authority.CUSTOMARY
    technology: int = 1


@dataclass(frozen=True, slots=True)
class Actor:
    key: str
    tenure: Tenure
    seat: str
    authority: Authority
    technology: int
    born: int
    origin: str
    homeland: tuple[str, ...]
    parents: tuple[str, ...] = ()
    ended: int | None = None
    end_cause: str = ""

    @property
    def living(self) -> bool:
        return self.ended is None


@dataclass(frozen=True, slots=True)
class Holding:
    district: str
    actor: str
    cause: str


@dataclass(frozen=True, slots=True)
class Bond:
    """Dependency/protection/access point from client to provider; pacts/exchange are mutual."""

    kind: Action
    first: str
    second: str
    cause: str
    place: str = ""


@dataclass(frozen=True, slots=True)
class Knowledge:
    first: str
    second: str
    cause: str


@dataclass(frozen=True, slots=True)
class Memory:
    first: str
    second: str
    factor: Factor
    year: int
    weight: int
    decay: int
    cause: str

    def at(self, year: int) -> int:
        return max(0, self.weight - self.decay * (year - self.year)) if year >= self.year else 0


@dataclass(frozen=True, slots=True)
class Partition:
    districts: tuple[str, ...]
    seat: str
    authority: Authority


@dataclass(frozen=True, slots=True)
class Proposal:
    kind: Action
    actor: str
    target: str = ""
    districts: tuple[str, ...] = ()
    partitions: tuple[Partition, ...] = ()
    threat: str = ""
    rank: int = 0


@dataclass(frozen=True, slots=True)
class Transfer:
    district: str
    before: str
    after: str


@dataclass(frozen=True, slots=True)
class Effects:
    created: tuple[Actor, ...] = ()
    retired: tuple[str, ...] = ()
    transfers: tuple[Transfer, ...] = ()
    bonds: tuple[Bond, ...] = ()
    knowledge: tuple[Knowledge, ...] = ()
    memories: tuple[Memory, ...] = ()


@dataclass(frozen=True, slots=True)
class Event:
    key: str
    year: int
    kind: Action
    actors: tuple[str, ...]
    causes: tuple[str, ...]
    outcome: Outcome
    reason: Reason
    effects: Effects = Effects()
    commitments: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True, slots=True)
class Snapshot:
    year: int
    actors: tuple[Actor, ...] = ()
    holdings: tuple[Holding, ...] = ()
    bonds: tuple[Bond, ...] = ()
    knowledge: tuple[Knowledge, ...] = ()
    memories: tuple[Memory, ...] = ()


@dataclass(frozen=True, slots=True)
class History:
    geography: Geography
    seed: int
    foundings: tuple[Founding, ...]
    state: Snapshot
    events: tuple[Event, ...]
    rounds: tuple[tuple[Proposal, ...], ...] = ()
