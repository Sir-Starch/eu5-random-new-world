"""Bounded, game-independent history inside an atlas, with no extra archive member.

The portable record contains facts and references, never localized paragraphs or
per-round rasters. Integer references and bounded compressed JSON keep large
causal closures practical. Import validates the data before a viewer uses it.
"""

from __future__ import annotations

import base64
import json
import lzma
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, cast

from rnw.history_model import (
    END,
    START,
    Action,
    Authority,
    Exchange,
    Factor,
    Livelihood,
    Military,
    Outcome,
    Society,
    Tenure,
    TrajectoryKind,
)
from rnw.history_text import chronicles
from rnw.progress import checkpoint
from rnw.rng import derive_seed

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rnw.eu5_start import FinalStartPlan
    from rnw.history_model import History

FORMAT: Final[int] = 1
MAX_BYTES: Final[int] = 8 * 1024 * 1024
MAX_RAW: Final[int] = 24 * 1024 * 1024
MAX_ACTORS: Final[int] = 25_000
MAX_EVENTS: Final[int] = 250_000
MAX_ROWS: Final[int] = 500_000
MAX_DEPTH: Final[int] = 256
MAX_JSON_DEPTH: Final[int] = 24
MAX_TOKENS: Final[int] = 4_000_000
MAX_STRING: Final[int] = 128
RELATIONS: Final[tuple[str, ...]] = ("vassal", "alliance", "rival", "guarantee", "exchange")
AXES: Final[tuple[str, ...]] = (
    "centralization",
    "authority",
    "livelihood",
    "exchange",
    "religious_authority",
    "military",
    "integration",
    "tradition",
)
TENURES: Final[tuple[Tenure, ...]] = tuple(Tenure)
ACTIONS: Final[tuple[Action, ...]] = tuple(Action)
OUTCOMES: Final[tuple[Outcome, ...]] = tuple(Outcome)
FACTORS: Final[tuple[Factor, ...]] = tuple(Factor)
GROUPS: Final[tuple[TrajectoryKind, ...]] = tuple(TrajectoryKind)
AUTHORITIES: Final[tuple[Authority, ...]] = tuple(Authority)
LIVELIHOODS: Final[tuple[Livelihood, ...]] = tuple(Livelihood)
EXCHANGES: Final[tuple[Exchange, ...]] = tuple(Exchange)
MILITARIES: Final[tuple[Military, ...]] = tuple(Military)


class HistoryArchiveError(ValueError):
    """Invalid or excessive portable facts; never silently shortened."""


def _require(condition: bool, message: str) -> None:  # noqa: FBT001 - a validation predicate
    if not condition:
        raise HistoryArchiveError(message)


@dataclass(frozen=True, slots=True)
class ActorFact:
    seat: int
    tenure: Tenure
    born: int
    ended: int | None
    origin: int
    end_cause: int | None
    parents: tuple[int, ...]
    society: Society
    axis_causes: tuple[int, ...]
    technology: int


@dataclass(frozen=True, slots=True)
class EventFact:
    year: int
    kind: Action
    outcome: Outcome
    actors: tuple[int, ...]
    causes: tuple[int, ...]
    places: tuple[int, ...]
    created: tuple[int, ...]
    retired: tuple[int, ...]
    partners: tuple[int, ...]
    wording: int


@dataclass(frozen=True, slots=True)
class CountryFact:
    tag: str
    actor: int
    level: int
    government: str
    rank: str
    great: bool
    landed: bool


@dataclass(frozen=True, slots=True)
class MemoryFact:
    first: int
    second: int
    factor: Factor
    amount: int
    cause: int


@dataclass(frozen=True, slots=True)
class BiasFact:
    first: int
    second: int
    factor: Factor
    value: int
    decay: int
    cause: int
    place: int


@dataclass(frozen=True, slots=True)
class BondFact:
    kind: Action
    first: int
    second: int
    cause: int
    place: int


@dataclass(frozen=True, slots=True)
class GroupFact:
    kind: TrajectoryKind
    members: tuple[int, ...]
    causes: tuple[int, ...]
    hearths: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class AtlasLinks:
    keys: tuple[str, ...]
    owners: tuple[int, ...]
    countries: tuple[tuple[str, int], ...]
    land: frozenset[int]


@dataclass(frozen=True, slots=True)
class Archive:
    digest: str
    actors: tuple[ActorFact, ...]
    events: tuple[EventFact, ...]
    countries: tuple[CountryFact, ...]
    initial: tuple[tuple[int, int], ...]
    changes: tuple[tuple[int, int, int, int], ...]
    memories: tuple[MemoryFact, ...]
    biases: tuple[BiasFact, ...]
    bonds: tuple[BondFact, ...]
    relations: tuple[tuple[str, int, int], ...]
    groups: tuple[GroupFact, ...]
    chronicles: tuple[tuple[int, tuple[int, ...]], ...]

    def lineage(self, actor: int) -> frozenset[int]:
        pending, seen = [actor], set[int]()
        while pending:
            key = pending.pop()
            if key not in seen:
                seen.add(key)
                pending.extend(self.actors[key].parents)
        return frozenset(seen)


def _event_order(history: History, seeds: set[str]) -> tuple[str, ...]:
    events = {event.key: event for event in history.events}
    _require(len(events) <= MAX_EVENTS, "History has too many events")
    ordered: list[str] = []
    done: set[str] = set()
    visiting: set[str] = set()

    def visit(key: str, depth: int) -> None:
        _require(depth <= MAX_DEPTH, "History references are too deep")
        if key in done:
            return
        _require(key in events and key not in visiting, "History has missing or cyclic causes")
        visiting.add(key)
        for cause in sorted(events[key].causes):
            visit(cause, depth + 1)
        visiting.remove(key)
        done.add(key)
        ordered.append(key)

    for key in sorted(seeds, key=lambda key: (events[key].year, key)):
        visit(key, 0)
    return tuple(ordered)


def build(plan: FinalStartPlan, keys: Sequence[str]) -> Archive:
    """Causal closure of the projected facts, predecessor context and ownership changes."""
    history = plan.history
    _require(history is not None, "Cannot invent history for a legacy world")
    if history is None:
        message = "No historical record"
        raise HistoryArchiveError(message)
    locations = {key: number for number, key in enumerate(keys)}
    actors = tuple(sorted(history.state.actors, key=lambda actor: actor.key))
    _require(len(actors) <= MAX_ACTORS, "History has too many actors")
    ai = {actor.key: number for number, actor in enumerate(actors)}
    living = {actor.key for actor in actors if actor.living}
    selected = chronicles(plan)
    axis_causes = {actor.key: [actor.origin] * len(AXES) for actor in actors}
    for event in history.events:
        for reform in event.effects.reforms:
            for index, axis in enumerate(AXES):
                if getattr(reform.before, axis) != getattr(reform.after, axis):
                    axis_causes[reform.actor][index] = event.key
    seeds = {
        key
        for actor in actors
        for key in (actor.origin, actor.society_cause, actor.end_cause)
        if key
    }
    seeds.update(key for causes in axis_causes.values() for key in causes)
    seeds.update(holding.cause for holding in history.state.holdings)
    seeds.update(bond.cause for bond in history.state.bonds if {bond.first, bond.second} <= living)
    seeds.update(
        memory.cause
        for memory in history.state.memories
        if memory.at(END) and {memory.first, memory.second} <= living
    )
    seeds.update(cause for group in plan.historical_groups for cause in group.causes)
    seeds.update(row.event for chronicle in selected.values() for row in chronicle.rows)
    seeds.update(event.key for event in history.events if event.effects.transfers)
    order = _event_order(history, seeds)
    ei = {key: number for number, key in enumerate(order)}
    by_event = {event.key: event for event in history.events}
    event_facts: list[EventFact] = []
    for key in order:
        if len(event_facts) % 256 == 0:
            checkpoint()
        event = by_event[key]
        places = (
            tuple(settlement.district for settlement in event.effects.settlements)
            if event.kind is Action.MIGRATION
            else tuple(
                sorted(
                    {
                        *(transfer.district for transfer in event.effects.transfers),
                        *(settlement.district for settlement in event.effects.settlements),
                        *(bond.place for bond in event.effects.bonds if bond.place),
                    }
                )
            )
        )
        bond = event.effects.bonds[0] if event.effects.bonds else None
        event_facts.append(
            EventFact(
                event.year,
                event.kind,
                event.outcome,
                tuple(ai[actor] for actor in event.actors),
                tuple(
                    sorted(
                        ei[cause]
                        for cause in set(event.causes)
                        - {
                            earlier
                            for parent in event.causes
                            for earlier in by_event[parent].causes
                        }
                    )
                ),
                tuple(locations[place] for place in places),
                tuple(ai[actor.key] for actor in event.effects.created),
                tuple(ai[actor] for actor in event.effects.retired),
                (ai[bond.first], ai[bond.second]) if bond is not None else (),
                derive_seed(history.seed, "history", "wording", event.key) % 2,
            )
        )
    memories: Counter[tuple[int, int, Factor, int]] = Counter()
    for memory in history.state.memories:
        if (amount := memory.at(END)) and {memory.first, memory.second} <= living:
            memories[ai[memory.first], ai[memory.second], memory.factor, ei[memory.cause]] += amount
    tag_actor = {country.tag: ai[country.history_actor] for country in plan.countries}
    hearths = {hearth.key: locations[hearth.centre] for hearth in history.geography.hearths}
    stats = cast("dict[str, object] | None", plan.stats.get("history"))
    _require(
        stats is not None and isinstance(stats.get("digest"), str),
        "Projected history has no digest",
    )
    model_digest = cast("str", stats["digest"]) if stats is not None else ""
    return Archive(
        model_digest,
        tuple(
            ActorFact(
                locations[actor.seat],
                actor.tenure,
                actor.born,
                actor.ended,
                ei[actor.origin],
                ei[actor.end_cause] if actor.end_cause else None,
                tuple(ai[parent] for parent in actor.parents),
                actor.society,
                tuple(ei[key] for key in axis_causes[actor.key]),
                actor.technology,
            )
            for actor in actors
        ),
        tuple(event_facts),
        tuple(
            CountryFact(
                country.tag,
                ai[country.history_actor],
                country.level
                if country.level is not None
                else actors[ai[country.history_actor]].technology,
                dict(country.government)["type"],
                country.rank,
                country.great,
                country.kind == "state" or country.landed,
            )
            for country in sorted(plan.countries, key=lambda country: country.tag)
        ),
        tuple(
            sorted(
                (locations[key], ai[founding.key])
                for founding in history.foundings
                for key in founding.districts
            )
        ),
        tuple(
            (ei[event.key], locations[transfer.district], ai[transfer.before], ai[transfer.after])
            for event in (by_event[key] for key in order)
            if event.kind is not Action.FOUNDATION
            for transfer in event.effects.transfers
        ),
        tuple(
            MemoryFact(first, second, factor, amount, cause)
            for (first, second, factor, cause), amount in sorted(memories.items())
        ),
        tuple(
            BiasFact(
                tag_actor[opinion.first],
                tag_actor[opinion.second],
                opinion.factor,
                opinion.value,
                opinion.yearly_decay,
                ei[opinion.cause],
                locations[opinion.place] if opinion.place else -1,
            )
            for opinion in plan.historical_opinions
        ),
        tuple(
            BondFact(
                bond.kind,
                ai[bond.first],
                ai[bond.second],
                ei[bond.cause],
                locations[bond.place] if bond.place else -1,
            )
            for bond in history.state.bonds
            if {bond.first, bond.second} <= living
        ),
        tuple(
            (kind, tag_actor[first], tag_actor[second])
            for kind, pairs in (
                ("vassal", plan.vassals),
                ("alliance", plan.alliances),
                ("rival", plan.rivals),
                ("guarantee", plan.protections),
                ("exchange", plan.exchanges),
            )
            for first, second in pairs
        ),
        tuple(
            GroupFact(
                TrajectoryKind(group.kind),
                tuple(ai[actor] for actor in group.actors),
                tuple(sorted(ei[cause] for cause in group.causes)),
                tuple(sorted(hearths[key] for key in group.hearths)),
            )
            for group in plan.historical_groups
        ),
        tuple(
            (tag_actor[tag], tuple(ei[row.event] for row in chronicle.rows))
            for tag, chronicle in sorted(selected.items())
        ),
    )


def _profile(society: Society) -> list[int]:
    return [
        society.centralization,
        AUTHORITIES.index(society.authority),
        LIVELIHOODS.index(society.livelihood),
        EXCHANGES.index(society.exchange),
        society.religious_authority,
        MILITARIES.index(society.military),
        society.integration,
        society.tradition,
    ]


def to_data(archive: Archive) -> dict[str, object]:
    """The closed wire schema, with integer references and no localized prose."""
    return {
        "v": FORMAT,
        "digest": archive.digest,
        "a": [
            [
                a.seat,
                TENURES.index(a.tenure),
                a.born,
                a.ended if a.ended is not None else -1,
                a.origin,
                a.end_cause if a.end_cause is not None else -1,
                list(a.parents),
                _profile(a.society),
                list(a.axis_causes),
                a.technology,
            ]
            for a in archive.actors
        ],
        "e": [
            [
                e.year,
                ACTIONS.index(e.kind),
                OUTCOMES.index(e.outcome),
                list(e.actors),
                list(e.causes),
                list(e.places),
                list(e.created),
                list(e.retired),
                list(e.partners),
                e.wording,
            ]
            for e in archive.events
        ],
        "c": [
            [c.tag, c.actor, c.level, c.government, c.rank, int(c.great), int(c.landed)]
            for c in archive.countries
        ],
        "i": [list(row) for row in archive.initial],
        "o": [list(row) for row in archive.changes],
        "m": [
            [m.first, m.second, FACTORS.index(m.factor), m.amount, m.cause]
            for m in archive.memories
        ],
        "p": [
            [b.first, b.second, FACTORS.index(b.factor), b.value, b.decay, b.cause, b.place]
            for b in archive.biases
        ],
        "b": [[ACTIONS.index(b.kind), b.first, b.second, b.cause, b.place] for b in archive.bonds],
        "r": [[RELATIONS.index(kind), first, second] for kind, first, second in archive.relations],
        "g": [
            [GROUPS.index(g.kind), list(g.members), list(g.causes), list(g.hearths)]
            for g in archive.groups
        ],
        "h": [[actor, list(events)] for actor, events in archive.chronicles],
    }


# Column order groups similar small facts before compression. Rows and their causal
# meaning are unchanged; a cause already reachable through another direct cause is
# omitted at construction. This preserves the complete ancestor closure.
COLUMNS: Final[dict[str, int]] = {
    "a": 10,
    "e": 10,
    "c": 7,
    "i": 2,
    "o": 4,
    "m": 5,
    "p": 7,
    "b": 5,
    "r": 3,
    "g": 4,
    "h": 2,
}


def pack(archive: Archive) -> dict[str, object]:
    data = to_data(archive)
    for key in COLUMNS:
        rows = cast("list[list[object]]", data[key])
        data[key] = [list(column) for column in zip(*rows, strict=True)] if rows else []
    raw = json.dumps(data, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")
    _require(len(raw) <= MAX_RAW, "Expanded history exceeds its portable budget")
    compressor = lzma.LZMACompressor(preset=6)
    chunks: list[bytes] = []
    for offset in range(0, len(raw), 65536):
        checkpoint()
        chunks.append(compressor.compress(raw[offset : offset + 65536]))
    chunks.append(compressor.flush())
    checkpoint()
    result: dict[str, object] = {
        "format": FORMAT,
        "codec": "xz-json-columns-base85",
        "raw_size": len(raw),
        "data": base64.b85encode(b"".join(chunks)).decode("ascii"),
    }
    _require(
        len(json.dumps(result, separators=(",", ":")).encode("ascii")) <= MAX_BYTES,
        "History exceeds its portable budget",
    )
    return result


def _scan(raw: bytes) -> None:
    """Bound JSON nesting, tokens and strings before allocation by the JSON reader."""
    depth = tokens = length = 0
    quoted = escaped = False
    for byte in raw:
        if quoted:
            length += 1
            _require(length <= MAX_STRING, "History contains an excessive string")
            if escaped:
                escaped = False
            elif byte == ord("\\"):
                escaped = True
            elif byte == ord('"'):
                quoted = False
        elif byte == ord('"'):
            quoted, length = True, 0
        elif byte in (91, 123):
            depth += 1
            tokens += 1
            _require(depth <= MAX_JSON_DEPTH, "History JSON is too deeply nested")
        elif byte in (93, 125):
            depth -= 1
        elif byte == ord(","):
            tokens += 1
        _require(tokens <= MAX_TOKENS, "History contains too many values")


def unpack(value: object) -> Archive:
    """Decode with a hard expansion limit; structural validation follows at the atlas boundary."""
    try:
        _require(isinstance(value, dict), "History is not an object")
        wrapper = cast("dict[str, object]", value)
        _require(
            set(wrapper) == {"format", "codec", "raw_size", "data"}
            and type(wrapper["format"]) is int
            and wrapper["format"] == FORMAT
            and wrapper["codec"] == "xz-json-columns-base85",
            "Unsupported history encoding",
        )
        size = _integer(wrapper["raw_size"], 0, MAX_RAW)
        encoded = _word(wrapper["data"], MAX_BYTES)
        _require(len(encoded) <= MAX_BYTES, "Encoded history exceeds its budget")
        compressed = base64.b85decode(encoded)
        decoder = lzma.LZMADecompressor(memlimit=64 * 1024 * 1024)
        raw = decoder.decompress(compressed, max_length=size + 1)
        _require(
            len(raw) == size and decoder.eof and not decoder.unused_data,
            "History is truncated, excessive or has trailing data",
        )
        _scan(raw)
        parsed = cast("object", json.loads(raw.decode("ascii")))
        _require(isinstance(parsed, dict), "History data is not an object")
        columns = cast("dict[str, object]", parsed)
        for key, width in COLUMNS.items():
            values = [_list(column) for column in _list(columns[key], width)]
            _require(not values or len(values) == width, "Invalid history columns")
            _require(
                not values or all(len(column) == len(values[0]) for column in values),
                "History columns differ",
            )
            columns[key] = [list(row) for row in zip(*values, strict=True)] if values else []
        return from_data(columns)
    except HistoryArchiveError:
        raise
    except (ValueError, TypeError, KeyError, UnicodeError, lzma.LZMAError, RecursionError) as error:
        message = "The portable history is damaged"
        raise HistoryArchiveError(message) from error


def _integer(value: object, low: int = 0, high: int = (1 << 31) - 1) -> int:
    _require(type(value) is int and low <= value <= high, "History has an invalid integer")
    return cast("int", value)


def _word(value: object, maximum: int = MAX_STRING) -> str:
    _require(
        isinstance(value, str) and len(value) <= maximum,
        "History has an invalid string",
    )
    return cast("str", value)


def _list(value: object, limit: int = MAX_ROWS) -> list[object]:
    _require(
        isinstance(value, list) and len(cast("list[object]", value)) <= limit,
        "History has an excessive or invalid list",
    )
    return cast("list[object]", value)


def _ints(value: object, limit: int = MAX_ROWS) -> tuple[int, ...]:
    return tuple(_integer(item) for item in _list(value, limit))


def _rows(value: object, columns: int, limit: int = MAX_ROWS) -> list[list[object]]:
    rows = [_list(row, columns) for row in _list(value, limit)]
    _require(all(len(row) == columns for row in rows), "History has inconsistent rows")
    return rows


def _society(value: object) -> Society:
    row = _ints(value, len(AXES))
    _require(len(row) == len(AXES), "History has an invalid society profile")
    return Society(
        _integer(row[0], 0, 1000),
        AUTHORITIES[_integer(row[1], 0, len(AUTHORITIES) - 1)],
        LIVELIHOODS[_integer(row[2], 0, len(LIVELIHOODS) - 1)],
        EXCHANGES[_integer(row[3], 0, len(EXCHANGES) - 1)],
        _integer(row[4], 0, 1000),
        MILITARIES[_integer(row[5], 0, len(MILITARIES) - 1)],
        _integer(row[6], 0, 1000),
        _integer(row[7], 0, 1000),
    )


def from_data(value: object) -> Archive:
    _require(isinstance(value, dict), "History data is not an object")
    data = cast("dict[str, object]", value)
    _require(
        set(data) == {"v", "digest", "a", "e", "c", "i", "o", "m", "p", "b", "r", "g", "h"}
        and type(data["v"]) is int
        and data["v"] == FORMAT,
        "History has an unknown schema",
    )
    actors = tuple(
        ActorFact(
            _integer(r[0]),
            TENURES[_integer(r[1], 0, len(TENURES) - 1)],
            _integer(r[2], START, END),
            None if r[3] == -1 else _integer(r[3], START, END),
            _integer(r[4]),
            None if r[5] == -1 else _integer(r[5]),
            _ints(r[6], MAX_ACTORS),
            _society(r[7]),
            _ints(r[8], len(AXES)),
            _integer(r[9], 0, 100),
        )
        for r in _rows(data["a"], 10, MAX_ACTORS)
    )
    events = tuple(
        EventFact(
            _integer(r[0], START, END),
            ACTIONS[_integer(r[1], 0, len(ACTIONS) - 1)],
            OUTCOMES[_integer(r[2], 0, len(OUTCOMES) - 1)],
            _ints(r[3], MAX_ACTORS),
            _ints(r[4], MAX_EVENTS),
            _ints(r[5]),
            _ints(r[6], MAX_ACTORS),
            _ints(r[7], MAX_ACTORS),
            _ints(r[8], 2),
            _integer(r[9], 0, 1),
        )
        for r in _rows(data["e"], 10, MAX_EVENTS)
    )
    return Archive(
        _word(data["digest"]),
        actors,
        events,
        tuple(
            CountryFact(
                _word(r[0], 3),
                _integer(r[1]),
                _integer(r[2], 0, 100),
                _word(r[3], 64),
                _word(r[4], 64),
                bool(_integer(r[5], 0, 1)),
                bool(_integer(r[6], 0, 1)),
            )
            for r in _rows(data["c"], 7, MAX_ACTORS)
        ),
        tuple((_integer(r[0]), _integer(r[1])) for r in _rows(data["i"], 2)),
        tuple(
            (_integer(r[0]), _integer(r[1]), _integer(r[2]), _integer(r[3]))
            for r in _rows(data["o"], 4)
        ),
        tuple(
            MemoryFact(
                _integer(r[0]),
                _integer(r[1]),
                FACTORS[_integer(r[2], 0, len(FACTORS) - 1)],
                _integer(r[3], 1),
                _integer(r[4]),
            )
            for r in _rows(data["m"], 5)
        ),
        tuple(
            BiasFact(
                _integer(r[0]),
                _integer(r[1]),
                FACTORS[_integer(r[2], 0, len(FACTORS) - 1)],
                _integer(r[3], -50, 50),
                _integer(r[4], 1, 3),
                _integer(r[5]),
                _integer(r[6], -1),
            )
            for r in _rows(data["p"], 7, 2000)
        ),
        tuple(
            BondFact(
                ACTIONS[_integer(r[0], 0, len(ACTIONS) - 1)],
                _integer(r[1]),
                _integer(r[2]),
                _integer(r[3]),
                _integer(r[4], -1),
            )
            for r in _rows(data["b"], 5)
        ),
        tuple(
            (RELATIONS[_integer(r[0], 0, len(RELATIONS) - 1)], _integer(r[1]), _integer(r[2]))
            for r in _rows(data["r"], 3)
        ),
        tuple(
            GroupFact(
                GROUPS[_integer(r[0], 0, len(GROUPS) - 1)],
                _ints(r[1], MAX_ACTORS),
                _ints(r[2], MAX_EVENTS),
                _ints(r[3]),
            )
            for r in _rows(data["g"], 4, MAX_ACTORS)
        ),
        tuple((_integer(r[0]), _ints(r[1], 8)) for r in _rows(data["h"], 2, MAX_ACTORS)),
    )
