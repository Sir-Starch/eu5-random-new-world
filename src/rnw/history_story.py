"""The story of a country as the game's Our History tells it: prose built from recorded facts.

The owner's sitting of 2026-11-08 judged the first chronicle a list of dated records ("1192:
Society Unichita could no longer hold society Kiosaghe, which broke away. Recorded place:
Oletan.") and asked for a procedurally written description. This module writes it from the same
facts, in three paragraphs:

1. **Origins.** What the country's lineage did before the country began (its predecessors' wars,
   unions and pacts), then how it began: the record opening on its people (the first round of the
   history is the start of the record, not a founding), a union, a breakaway or a division.
2. **Fortunes.** What happened to it afterwards, in order; lands that broke away from one holder
   one after another are told in one sentence.
3. **Today.** Its place in 1337: its overlord or freedom, its vassals, allies, protectors and
   rivals, as the world's setup writes them.

The facts are the history archive's (``history_archive``): the export and the generator's window
read the same archive through ``tell``, so the game and the window tell the same story. The events
are the chronicle's selection (D27). A sentence claims only what the record holds: who, when,
where, and the kind of event; no reasons, battles or numbers it does not have. Names are kept as
names until a language renders them (``history_text.render``); lists follow a colon or a
generic noun in inflected languages (``docs/localization.md`` §3.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw import history_text
from rnw.history_model import Action, Outcome
from rnw.history_text import Sentence

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping, Sequence

    from rnw.history_archive import Archive, EventFact
    from rnw.wording import Name

PREFIX: Final[str] = "rnw_story_"
# The English source of every sentence of the story, by key (``history_text.sources`` adds them).
TEXTS: Final[dict[str, str]] = {
    f"{PREFIX}origin_foundation": (
        "The memory of {name} reaches back to {year}, when its people already lived around {place}."
    ),
    f"{PREFIX}origin_home": (
        "The memory of {name} reaches back to {year}, when its people already lived on this land."
    ),
    f"{PREFIX}origin_union": "{name} arose in {year}, when {first} and {second} became one.",
    f"{PREFIX}origin_joined": "{name} took its present shape in {year}, when {first} joined it.",
    f"{PREFIX}origin_secession": "{name} began in {year}, when it broke away from {first}.",
    f"{PREFIX}origin_separation": (
        "{name} is one of the heirs of {first}, which fell apart in {year}."
    ),
    f"{PREFIX}origin_remnant": (
        "{name} is what remained of an older {name}, which fell apart in {year}."
    ),
    f"{PREFIX}origin_other": "{name} enters the record in {year}.",
    f"{PREFIX}when_year": "In {year},",
    f"{PREFIX}when_same": "That same year,",
    f"{PREFIX}when_soon": "Soon after,",
    f"{PREFIX}union": "{when} {second} and {third} joined to form {first}.",
    f"{PREFIX}joined": "{when} {second} joined {first}.",
    f"{PREFIX}separation": "{when} {first} fell apart into several successors.",
    f"{PREFIX}secession": "{when} {second} broke away from {first}.",
    f"{PREFIX}losses": "From {start} to {end} {first} lost one land after another: {list}.",
    f"{PREFIX}lost_item": "{name} ({year})",
    f"{PREFIX}independence": "{when} {first} threw off the rule of {second}.",
    f"{PREFIX}dependency": "{when} {first} bowed to {second} and became its vassal.",
    f"{PREFIX}protection": "{when} {second} took {first} under its protection.",
    f"{PREFIX}pact": "{when} {first} and {second} swore to defend each other.",
    f"{PREFIX}access": (
        "{when} {second} opened the sacred place of {place} to the pilgrims of {first}."
    ),
    f"{PREFIX}conflict": "{when} {first} and {second} went to war over {place}.",
    f"{PREFIX}conflict_for": "{when} {first} fought {second} for {place}.",
    f"{PREFIX}wars": "From {start} to {end} {first} and {second} fought one war after another.",
    f"{PREFIX}wars_over": (
        "From {start} to {end} {first} and {second} fought one war after another over {list}."
    ),
    f"{PREFIX}conflict_open": "{when} {first} and {second} went to war.",
    f"{PREFIX}pressure": "{when} {first} and {second} came to blows, but no land changed hands.",
    f"{PREFIX}repelled": "{when} {first} and {second} fought, and the attack was beaten back.",
    f"{PREFIX}reform": "{when} {first} changed the way it was governed.",
    f"{PREFIX}resisted": (
        "{when} {first} tried to change the way it was governed, but the attempt failed."
    ),
    f"{PREFIX}migration": "{when} people from {first} settled in {second}.",
    f"{PREFIX}exchange": "{when} {first} began to trade with {second}.",
    f"{PREFIX}contact": "{when} {first} first met {second}.",
    f"{PREFIX}now_vassal": "Today {name} is a vassal of {first}.",
    f"{PREFIX}now_free": "Today {name} bows to no one.",
    f"{PREFIX}now_subjects": "It is the overlord of {list}.",
    f"{PREFIX}now_allies": "It is allied with {list}.",
    f"{PREFIX}now_protectors": "It is under the protection of {list}.",
    f"{PREFIX}now_allies_protecting": "It is allied with {list}, under whose protection it stands.",
    f"{PREFIX}now_rivals": "It counts {list} among its rivals.",
    f"{PREFIX}list_pair": "{first} and {second}",
    f"{PREFIX}list_series": "{first}, {second}",
}
# Events of this kind, one after another from one holder, make one sentence of losses.
LOSS: Final[Action] = Action.SECESSION
# A sentence within this many years of the one before begins "Soon after".
SOON: Final[int] = 10


@dataclass(frozen=True, slots=True)
class Story:
    """A country's story: paragraphs of sentences, each a structured text (``Sentence``)."""

    paragraphs: tuple[tuple[Sentence, ...], ...]


def listing(items: Sequence[Sentence | Name]) -> Sentence | Name:
    """``a``, ``a and b``, ``a, b and c``: a list in the language's own words."""
    if len(items) == 1:
        return items[0]
    head: Sentence | Name = items[0]
    for item in items[1:-1]:
        head = Sentence(f"{PREFIX}list_series", (("first", head), ("second", item)))
    return Sentence(f"{PREFIX}list_pair", (("first", head), ("second", items[-1])))


type Field = tuple[str, "Name | int | Sentence"]


@dataclass(frozen=True, slots=True)
class _Teller:
    archive: Archive
    actor: int
    name: Callable[[int], Name]
    place: Callable[[int], Name]

    def sentence(self, key: str, *fields: Field) -> Sentence:
        return Sentence(f"{PREFIX}{key}", fields)

    def origin(self, index: int) -> Sentence:  # noqa: PLR0911 - one per beginning
        """How the country began; a predecessor named as the country is told apart from it."""
        event = self.archive.events[index]
        own = self.name(self.actor)
        name, year = ("name", own), ("year", event.year)
        parents = [self.name(parent) for parent in self.archive.actors[self.actor].parents]
        if event.kind is Action.FOUNDATION:
            seat = self.place(self.archive.actors[self.actor].seat)
            if seat == own:
                return self.sentence("origin_home", name, year)
            return self.sentence("origin_foundation", name, year, ("place", seat))
        if event.kind is Action.UNION and len(parents) >= 2:  # noqa: PLR2004 - a union joins two
            first, second = parents[:2]
            if own in {first, second}:
                other = second if own == first else first
                return self.sentence("origin_joined", name, year, ("first", other))
            return self.sentence("origin_union", name, year, ("first", first), ("second", second))
        if event.kind is Action.SECESSION and event.actors:
            return self.sentence(
                "origin_secession", name, year, ("first", self.name(event.actors[0]))
            )
        if event.kind is Action.SEPARATION and event.retired:
            parent = self.name(event.retired[0])
            if parent == own:
                return self.sentence("origin_remnant", name, year)
            return self.sentence("origin_separation", name, year, ("first", parent))
        return self.sentence("origin_other", name, year)

    def pair(self, event: EventFact) -> tuple[int, int] | None:
        """The two sides an event names, as the window's timeline names them."""
        if event.kind in {Action.CONFLICT, Action.PRESSURE}:
            ours = sorted(self.archive.lineage(self.actor).intersection(event.actors))
            if not ours:
                return None
            other = next((key for key in event.actors if key != ours[0]), None)
            return None if other is None else (ours[0], other)
        if event.partners:
            return event.partners[0], event.partners[1]
        if len(event.actors) >= 2:  # noqa: PLR2004 - two sides
            return event.actors[0], event.actors[1]
        return None

    def told(self, index: int, when: Field) -> Sentence | None:  # noqa: PLR0911 - one per kind
        """One event of the course, opened by ``when``; None when the record lacks what its
        sentence names."""
        event = self.archive.events[index]
        failed = event.outcome is Outcome.FAILED
        if event.kind is Action.UNION and event.created:
            created = event.created[0]
            parents = [self.name(parent) for parent in self.archive.actors[created].parents]
            if len(parents) < 2:  # noqa: PLR2004 - a union joins two
                return None
            made = self.name(created)
            if made in parents[:2]:
                other = parents[1] if made == parents[0] else parents[0]
                return self.sentence("joined", when, ("first", made), ("second", other))
            return self.sentence(
                "union", when, ("first", made), ("second", parents[0]), ("third", parents[1])
            )
        if event.kind is Action.SEPARATION and event.retired:
            return self.sentence("separation", when, ("first", self.name(event.retired[0])))
        if event.kind is Action.SECESSION and event.actors and event.created:
            return self.sentence(
                "secession",
                when,
                ("first", self.name(event.actors[0])),
                ("second", self.name(event.created[0])),
            )
        if event.kind is Action.MIGRATION and len(event.places) >= 2:  # noqa: PLR2004 - from, to
            return self.sentence(
                "migration",
                when,
                ("first", self.place(event.places[0])),
                ("second", self.place(event.places[1])),
            )
        if event.kind is Action.REFORM and event.actors:
            kind = "resisted" if failed else "reform"
            return self.sentence(kind, when, ("first", self.name(event.actors[0])))
        sides = self.pair(event)
        if sides is None:
            return None
        first, second = ("first", self.name(sides[0])), ("second", self.name(sides[1]))
        if event.kind in {Action.CONFLICT, Action.PRESSURE} and failed:
            return self.sentence("repelled", when, first, second)
        if event.kind is Action.CONFLICT and event.places:
            at = ("place", self.place(event.places[0]))
            phrased = ("conflict", "conflict_for")[event.wording % 2]
            return self.sentence(phrased, when, first, second, at)
        if event.kind is Action.ACCESS and event.places:
            at = ("place", self.place(event.places[0]))
            return self.sentence("access", when, first, second, at)
        key = {
            Action.CONFLICT: "conflict_open",
            Action.PRESSURE: "pressure",
            Action.INDEPENDENCE: "independence",
            Action.DEPENDENCY: "dependency",
            Action.PROTECTION: "protection",
            Action.PACT: "pact",
            Action.EXCHANGE: "exchange",
            Action.CONTACT: "contact",
        }.get(event.kind)
        return None if key is None else self.sentence(key, when, first, second)

    def group(self, rows: Sequence[int], when: Field) -> Sentence | None:
        """Events of one run (``_run``): one is told as itself; lands that broke away from one
        holder are told as losses, the wars of one pair as one war after another."""
        if len(rows) == 1:
            return self.told(rows[0], when)
        events = [self.archive.events[index] for index in rows]
        start, end = ("start", events[0].year), ("end", events[-1].year)
        if events[0].kind is LOSS:
            items: list[Sentence | Name] = [
                Sentence(
                    f"{PREFIX}lost_item",
                    (("name", self.name(event.created[0])), ("year", event.year)),
                )
                for event in events
            ]
            first = ("first", self.name(events[0].actors[0]))
            return self.sentence("losses", start, end, first, ("list", listing(items)))
        sides = self.pair(events[0])
        if sides is None:
            return None
        first, second = ("first", self.name(sides[0])), ("second", self.name(sides[1]))
        places: list[int] = []
        for event in events:
            places.extend(place for place in event.places if place not in places)
        if not places:
            return self.sentence("wars", start, end, first, second)
        named: list[Sentence | Name] = [self.place(place) for place in places]
        return self.sentence("wars_over", start, end, first, second, ("list", listing(named)))

    def _run(self, index: int) -> tuple[object, ...] | None:
        """What an event shares with the ones before it to be told with them, if anything."""
        event = self.archive.events[index]
        if event.kind is LOSS and event.actors and event.created:
            return ("loss", event.actors[0])
        if event.kind in {Action.CONFLICT, Action.PRESSURE}:
            sides = self.pair(event)
            return None if sides is None else ("war", *sorted(sides))
        return None

    def course(self, rows: Sequence[int]) -> list[Sentence]:
        """The events in order, each opened by its time: its year, or "that same year" and "soon
        after" within a paragraph (never two in a row); runs of events make one sentence."""
        groups: list[list[int]] = []
        runs: list[tuple[object, ...] | None] = []
        for index in rows:
            run = self._run(index)
            if run is not None and runs and runs[-1] == run:
                groups[-1].append(index)
            else:
                groups.append([index])
                runs.append(run)
        told: list[Sentence] = []
        year: int | None = None
        relative = False
        for group in groups:
            start = self.archive.events[group[0]].year
            dated = year is None or relative or start - year > SOON or len(group) > 1
            if dated:
                when: Field = ("when", self.sentence("when_year", ("year", start)))
            elif start == year:
                when = ("when", self.sentence("when_same"))
            else:
                when = ("when", self.sentence("when_soon"))
            sentence = self.group(group, when)
            if sentence is not None:
                told.append(sentence)
                relative = not dated
                year = self.archive.events[group[-1]].year
        return told

    def related(self, kind: str, *, ours: str) -> list[int]:
        """The other countries of the setup's ``kind`` relations in which the country stands
        ``ours`` (``first`` or ``second``; ``any`` for a relation without sides), in order."""
        found: list[int] = []
        for relation, first, second in self.archive.relations:
            if relation != kind or self.actor not in {first, second}:
                continue
            side = "first" if first == self.actor else "second"
            other = second if side == "first" else first
            if ours in {side, "any"} and other != self.actor and other not in found:
                found.append(other)
        return found

    def today(self) -> list[Sentence]:
        """The country's place in 1337, from the relations its setup writes: an overlord is the
        first of a ``vassal`` pair, a guarantor the first of a ``guarantee`` pair."""
        name = ("name", self.name(self.actor))
        lords = self.related("vassal", ours="second")
        told = [
            self.sentence("now_vassal", name, ("first", self.name(lords[0])))
            if lords
            else self.sentence("now_free", name)
        ]
        allies = self.related("alliance", ours="any")
        protectors = self.related("guarantee", ours="second")
        together = bool(allies) and set(allies) == set(protectors)
        for key, members in (
            ("now_subjects", self.related("vassal", ours="first")),
            ("now_allies_protecting" if together else "now_allies", allies),
            ("now_protectors", [] if together else protectors),
            ("now_rivals", self.related("rival", ours="first")),
        ):
            if members:
                names: list[Sentence | Name] = [self.name(member) for member in members]
                told.append(self.sentence(key, ("list", listing(names))))
        return told


def origin(
    archive: Archive,
    actor: int,
    *,
    name: Callable[[int], Name],
    place: Callable[[int], Name],
) -> Sentence:
    """How the country began, as its story tells it (the Society tab's origin)."""
    return _Teller(archive, actor, name, place).origin(archive.actors[actor].origin)


def tell(
    archive: Archive,
    actor: int,
    *,
    name: Callable[[int], Name],
    place: Callable[[int], Name],
) -> Story:
    """The story of the living country of ``actor``, from its chronicle's events.

    ``name`` names an actor (a country as the map names it, a predecessor by its seat) and
    ``place`` a location of the archive.
    """
    teller = _Teller(archive, actor, name, place)
    rows = sorted(
        dict(archive.chronicles)[actor],
        key=lambda index: (archive.events[index].year, index),
    )
    origin = archive.actors[actor].origin
    before = [
        index
        for index in rows
        if index != origin and archive.events[index].year < archive.events[origin].year
    ]
    after = [index for index in rows if index != origin and index not in before]
    beginning = (*teller.course(before), teller.origin(origin))
    parts = [beginning, tuple(teller.course(after)), tuple(teller.today())]
    return Story(tuple(part for part in parts if part))


# Sentences follow each other with a space, but not in the languages that write none.
UNSPACED: Final[frozenset[str]] = frozenset({"japanese", "simp_chinese"})


def source_keys(story: Story) -> Iterator[str]:
    """The keys of the static texts the story's sentences are written from."""
    for paragraph in story.paragraphs:
        for sentence in paragraph:
            yield from history_text.source_keys(sentence)


def render(story: Story, language: str, texts: Mapping[str, str]) -> str:
    """The story in ``language`` as the game's text: paragraphs apart (``\\n\\n``)."""
    return "\\n\\n".join(paragraphs(story, language, texts))


def paragraphs(story: Story, language: str, texts: Mapping[str, str]) -> tuple[str, ...]:
    """The story's paragraphs in ``language``, for a reader that lays them out itself."""
    joint = "" if language in UNSPACED else " "
    return tuple(
        joint.join(history_text.render(sentence, language, texts) for sentence in paragraph)
        for paragraph in story.paragraphs
    )
