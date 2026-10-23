"""Script edits that carry the content decisions out (content plan, N1).

``content_decisions`` says what becomes of every vanilla object that names the replaced
Americas; this module writes it into the world's mod:

* **Guard.** An object that names a historical American person, place or incident, or that
  needs the vanilla isthmus, is *neutralized* by closing the gate vanilla gives it: the
  ``trigger`` of an event, the ``potential`` of a decision, an advance, a formable or a
  generic action, the ``country_trigger`` of a scripted country name. The object stays in the
  file, so no reference to it dangles, and nothing can fire, offer or apply it.
* **Rebind.** A historical formable gated by a culture that the generated world reuses
  (``AZT_f``, ``INC_f``, ``IRO_f``, ``MAY_f``, ``PUE_f``) keeps its gating and takes as its
  territory the places where that culture lives, as many as the vanilla territory had; its
  start-effect twin in ``on_game_start`` finds the seat of the same religion. A culture too
  thin to carry the formable neutralizes it instead.

Only the lines of the objects named are touched; every other byte of a file stays.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.content_decisions import Decision
from rnw.eu5_remap import script_files
from rnw.pdx import Block, Edits, Entry, PdxSyntaxError, line_span, parse

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path

    from rnw.content_check import Checked
    from rnw.content_decisions import Verdict
    from rnw.content_inventory import Consumer
    from rnw.geography import Location

# The block through which vanilla gates each kind of object.
GATES: Final[Mapping[str, str]] = {
    "events": "trigger",
    "common/decisions": "potential",
    "common/advances": "potential",
    "common/generic_actions": "potential",
    "common/formable_countries": "potential",
    "common/scripted_country_names": "country_trigger",
}
# Objects that need no edit once the ones that offer them are guarded.
UNGATED: Final[frozenset[str]] = frozenset(
    {"common/scripted_geography", "gfx/map", "menu/achievements"}
)
NEUTRALIZED_REASONS: Final[frozenset[str]] = frozenset({"identity", "canal"})
ALWAYS_NO: Final[str] = "always = no"
FORMABLES: Final[str] = "common/formable_countries"
GAME_START: Final[str] = "common/on_action:on_game_start"
NAHUATL: Final[str] = "nahuatl"
TENOCHTITLAN: Final[str] = "tenochtitlan"
TERRITORY_KEYS: Final[frozenset[str]] = frozenset({"regions", "areas", "provinces", "locations"})
CULTURE: Final[re.Pattern[str]] = re.compile(r"\bculture\s*=\s*culture:([A-Za-z0-9_]+)")
LANGUAGE: Final[re.Pattern[str]] = re.compile(r"\blanguage\s*=\s*language:([A-Za-z0-9_]+)")
GROUP: Final[re.Pattern[str]] = re.compile(r"\bculture_group:([A-Za-z0-9_]+)")
RELIGION: Final[re.Pattern[str]] = re.compile(r"\breligion\s*=\s*religion:([A-Za-z0-9_]+)")
OWNS_SEAT: Final[re.Pattern[str]] = re.compile(r"(\bowns\s*=\s*location:)([A-Za-z0-9_]+)")
POP_LINE: Final[re.Pattern[str]] = re.compile(
    r"size\s*=\s*([0-9.]+)\s+culture\s*=\s*([A-Za-z0-9_]+)\s+religion\s*=\s*([A-Za-z0-9_]+)"
)
# A culture must hold at least a third of the vanilla territory's size, and three places.
MIN_SHARE: Final[int] = 3
MIN_PLACES: Final[int] = 3
LIST_WIDTH: Final[int] = 8


class ContentError(ValueError):
    """A decision that the installed scripts cannot carry out."""


@dataclass(frozen=True, slots=True)
class Target:
    """One object to guard: where it stands and the gate that closes it."""

    file: str
    category: str
    ident: str
    gate: str


def guard_targets(
    consumers: Mapping[str, Consumer], verdicts: Mapping[str, Verdict | None]
) -> list[Target]:
    """The objects whose decision is to be neutralized now, with their files and gates."""
    targets: list[Target] = []
    for key, consumer in consumers.items():
        verdict = verdicts[key]
        if verdict is None or verdict.reason not in NEUTRALIZED_REASONS:
            continue
        if verdict.decision not in {Decision.NEUTRALIZE, Decision.REPLACE}:
            continue
        gate = GATES.get(consumer.category)
        if gate is None:
            if consumer.category in UNGATED:
                continue
            message = f"No gate for {key}: {consumer.category} is neither gated nor ungated"
            raise ContentError(message)
        targets.extend(
            Target(file, consumer.category, consumer.ident, gate) for file in consumer.files
        )
    return targets


def _gate_edit(text: str, entry: Entry, gate: str, edits: Edits) -> None:
    block = entry.value
    if not isinstance(block, Block):
        message = f"{entry.key} is not a block"
        raise ContentError(message)
    existing = block.first(gate)
    if existing is None:
        line = text.rfind("\n", 0, block.close) + 1
        if text[line : block.close].strip():  # the brace shares its line with other text
            edits.insert(block.close, f"{gate} = {{ {ALWAYS_NO} }} ")
        else:
            edits.insert(line, f"\t{gate} = {{ {ALWAYS_NO} }}\n")
    elif isinstance(existing.value, Block):
        edits.insert(existing.value.open + 1, f"\n\t\t{ALWAYS_NO}")
    else:
        message = f"{entry.key}: {gate} is not a block"
        raise ContentError(message)


def guard_text(text: str, idents: Iterable[str], gate: str) -> tuple[str, int]:
    """``text`` with the gate of every top-level object in ``idents`` closed; and how many."""
    wanted = set(idents)
    edits = Edits()
    count = 0
    for entry in parse(text).entries:
        if entry.key in wanted:
            _gate_edit(text, entry, gate, edits)
            count += 1
    return (edits.apply(text) if count else text), count


def _decode(raw: bytes) -> tuple[str, str]:
    bom = "\ufeff" if raw.startswith(b"\xef\xbb\xbf") else ""
    return raw.decode("utf-8-sig"), bom


class Scripts:
    """The script files being written: a mod copy where there is one, else the game's file."""

    def __init__(self, files: Mapping[str, Path], outputs: Mapping[str, bytes]) -> None:
        self._files: Mapping[str, Path] = files
        self._text: dict[str, tuple[str, str]] = {
            relative: _decode(data) for relative, data in outputs.items() if relative in files
        }
        self._dirty: set[str] = set()

    def read(self, relative: str) -> str:
        """The current text of one script file."""
        if relative not in self._text:
            self._text[relative] = _decode(self._files[relative].read_bytes())
        return self._text[relative][0]

    def original(self, relative: str) -> str:
        """The text the game ships for one script file."""
        return _decode(self._files[relative].read_bytes())[0]

    def write(self, relative: str, text: str) -> None:
        """Replace the text of one script file."""
        _ = self.read(relative)
        self._text[relative] = (text, self._text[relative][1])
        self._dirty.add(relative)

    def changed(self) -> dict[str, bytes]:
        """The files written to, as bytes, with the byte order mark they had."""
        return {
            relative: (self._text[relative][1] + self._text[relative][0]).encode("utf-8")
            for relative in sorted(self._dirty)
        }


def guard_scripts(scripts: Scripts, targets: Sequence[Target]) -> dict[str, int]:
    """Close the gate of every target; returns the number of objects guarded per category."""
    grouped: dict[tuple[str, str, str], set[str]] = {}
    for target in targets:
        grouped.setdefault((target.file, target.category, target.gate), set()).add(target.ident)
    counts: dict[str, int] = {}
    for (file, category, gate), idents in sorted(grouped.items()):
        text, found = guard_text(scripts.read(file), idents, gate)
        if found < len(idents):
            message = f"{file}: {len(idents) - found} of the objects to neutralize are missing"
            raise ContentError(message)
        scripts.write(file, text)
        counts[category] = counts.get(category, 0) + found
    return dict(sorted(counts.items()))


@dataclass(frozen=True, slots=True)
class Selector:
    """What a formable's ``potential`` asks of a country's culture or religion."""

    cultures: frozenset[str]
    languages: frozenset[str]
    groups: frozenset[str]
    religions: frozenset[str]

    def empty(self) -> bool:
        """Whether the formable asks for no culture at all."""
        return not (self.cultures or self.languages or self.groups)


def selector_of(potential: str) -> Selector:
    """The cultures, languages, culture groups and religions a ``potential`` names."""
    return Selector(
        frozenset(CULTURE.findall(potential)),
        frozenset(LANGUAGE.findall(potential)),
        frozenset(GROUP.findall(potential)),
        frozenset(RELIGION.findall(potential)),
    )


@dataclass(frozen=True, slots=True)
class Place:
    """A generated location with the culture and religion that hold most of it."""

    key: str
    culture: str
    religion: str
    population: int


def places(pops: Mapping[str, Sequence[str]]) -> list[Place]:
    """The inhabited generated locations, from the pop lines of the start state."""
    found: list[Place] = []
    for key in sorted(pops):
        size_of: dict[tuple[str, str], int] = {}
        for line in pops[key]:
            match = POP_LINE.search(line)
            if match:
                milli = round(float(match.group(1)) * 1000)
                pair = (match.group(2), match.group(3))
                size_of[pair] = size_of.get(pair, 0) + milli
        if size_of:
            (culture, religion), _ = max(size_of.items(), key=lambda item: (item[1], item[0]))
            found.append(Place(key, culture, religion, sum(size_of.values())))
    return found


def culture_traits(game_dir: Path) -> dict[str, tuple[str, frozenset[str]]]:
    """Language and culture groups of every vanilla culture, from ``common/cultures``."""
    traits: dict[str, tuple[str, frozenset[str]]] = {}
    for path in sorted((game_dir / "game/in_game/common/cultures").glob("*.txt")):
        for entry in parse(path.read_text(encoding="utf-8-sig")).entries:
            if entry.key is None or not isinstance(entry.value, Block):
                continue
            language = entry.value.first("language")
            groups = entry.value.block("culture_groups")
            traits[entry.key] = (
                language.value if language and isinstance(language.value, str) else "",
                frozenset(word.value for word in groups.words() if isinstance(word.value, str))
                if groups is not None
                else frozenset(),
            )
    return traits


def matches(
    selector: Selector, place: Place, traits: Mapping[str, tuple[str, frozenset[str]]]
) -> bool:
    """Whether the culture (or, where none is asked, the religion) of ``place`` is the one."""
    if selector.empty():
        return place.religion in selector.religions
    language, groups = traits.get(place.culture, ("", frozenset()))
    return (
        place.culture in selector.cultures
        or language in selector.languages
        or bool(groups & selector.groups)
    )


def territory_size(block: Block, hierarchy: Mapping[str, Location]) -> int:
    """How many vanilla locations the territory lists of a formable cover."""
    wanted: dict[str, set[str]] = {}
    for entry in block.entries:
        if entry.key in TERRITORY_KEYS and isinstance(entry.value, Block):
            wanted[entry.key] = {
                word.value for word in entry.value.words() if isinstance(word.value, str)
            }
    found: set[str] = set()
    for key, location in hierarchy.items():
        if (
            location.region in wanted.get("regions", ())
            or location.area in wanted.get("areas", ())
            or location.province in wanted.get("provinces", ())
            or key in wanted.get("locations", ())
        ):
            found.add(key)
    return len(found)


def _list(keys: Sequence[str]) -> str:
    rows = [" ".join(keys[start : start + LIST_WIDTH]) for start in range(0, len(keys), LIST_WIDTH)]
    return "\tlocations = {\n" + "".join(f"\t\t{row}\n" for row in rows) + "\t}\n"


@dataclass(frozen=True, slots=True)
class Basis:
    """What a rebinding reads: the inhabited places, the cultures' traits and the vanilla map."""

    candidates: Sequence[Place]
    traits: Mapping[str, tuple[str, frozenset[str]]]
    hierarchy: Mapping[str, Location]


@dataclass(frozen=True, slots=True)
class Rebinding:
    """What one formable was bound to."""

    formable: str
    places: tuple[str, ...]
    seat: str
    vanilla_size: int


def rebind_formable(
    text: str, entry: Entry, vanilla: Block, basis: Basis, edits: Edits
) -> Rebinding | None:
    """Edits that give ``entry`` the places of its culture; ``None`` if the culture is too thin."""
    block = entry.value
    if not isinstance(block, Block) or entry.key is None:
        message = "A formable is a block"
        raise ContentError(message)
    potential = block.first("potential")
    if potential is None:
        message = f"{entry.key} has no potential to read a culture from"
        raise ContentError(message)
    selector = selector_of(text[potential.start : potential.end])
    size = territory_size(vanilla, basis.hierarchy)
    if size == 0:
        message = f"{entry.key}: the vanilla territory names no known location"
        raise ContentError(message)
    ranked = sorted(
        (place for place in basis.candidates if matches(selector, place, basis.traits)),
        key=lambda place: (-place.population, place.key),
    )
    chosen = ranked[:size]
    if len(chosen) < max(MIN_PLACES, size // MIN_SHARE):
        return None
    territory = [entry_ for entry_ in block.entries if entry_.key in TERRITORY_KEYS]
    for old in territory:
        edits.deletions.append(line_span(text, old.start, old.end))
    keys = sorted(place.key for place in chosen)
    edits.insert(line_span(text, territory[0].start, territory[0].end)[0], _list(keys))
    allow = block.first("allow")
    seat = chosen[0].key
    if allow is not None:
        for match in OWNS_SEAT.finditer(text, allow.start, allow.end):
            edits.deletions.append((match.start(2), match.end(2)))
            edits.insert(match.start(2), seat)
    return Rebinding(entry.key, tuple(keys), seat, size)


def rebind_formables(
    scripts: Scripts, basis: Basis, rebound: Mapping[str, Sequence[str]]
) -> tuple[dict[str, Rebinding], list[Target]]:
    """Rebind the formables named in ``rebound`` (file -> formable keys).

    Returns what each was bound to and the formables to neutralize instead, because their
    culture is too thin in this world.
    """
    done: dict[str, Rebinding] = {}
    thin: list[Target] = []
    for file, keys in sorted(rebound.items()):
        text = scripts.read(file)
        vanilla = {
            entry.key: entry.value
            for entry in parse(scripts.original(file)).entries
            if entry.key is not None and isinstance(entry.value, Block)
        }
        edits = Edits()
        for entry in parse(text).entries:
            if entry.key is None or entry.key not in keys:
                continue
            found = rebind_formable(text, entry, vanilla[entry.key], basis, edits)
            if found is None:
                thin.append(Target(file, FORMABLES, entry.key, GATES[FORMABLES]))
            else:
                done[entry.key] = found
        scripts.write(file, edits.apply(text))
        missing = set(keys) - done.keys() - {target.ident for target in thin}
        if missing:
            message = f"{file}: formables to rebind are missing: {', '.join(sorted(missing))}"
            raise ContentError(message)
    return done, thin


def rebind_game_start(scripts: Scripts, file: str, *, old_seat: str, seat: str | None) -> bool:
    """Point the start effect for the Nahuatl god at the seat of the religion; ``False`` if none.

    ``old_seat`` is the location the remap put in place of Tenochtitlan. Without a seat
    (the religion is absent from this world) the clause that needed it can never hold.
    """
    text = scripts.read(file)
    for entry in parse(text).entries:
        if entry.key != "on_game_start" or not isinstance(entry.value, Block):
            continue
        body = text[entry.start : entry.end]
        pattern = re.compile(rf"scope:current_country\s*=\s*location:{re.escape(old_seat)}\.owner")
        if not pattern.search(body):
            message = f"on_game_start no longer names location:{old_seat}.owner"
            raise ContentError(message)
        replacement = (
            f"scope:current_country = location:{seat}.owner" if seat is not None else ALWAYS_NO
        )
        scripts.write(
            file, text[: entry.start] + pattern.sub(replacement, body) + text[entry.end :]
        )
        return seat is not None
    message = "No on_game_start in the file"
    raise ContentError(message)


def carry_out(  # noqa: PLR0913, PLR0917 - the decisions need the scripts, the world and the remap.
    game_dir: Path,
    scripts: dict[str, bytes],
    checked: Checked,
    pops: Mapping[str, Sequence[str]],
    hierarchy: Mapping[str, Location],
    remap: Mapping[str, str],
) -> dict[str, object]:
    """Write every decision of the table that edits scripts into ``scripts``; return the counts.

    Neutralizations close their gates; the rebinds read the world's pop lines. The result
    names what each rebound formable was bound to, so the report shows it.
    """
    store = Scripts(script_files(game_dir), scripts)
    basis = Basis(places(pops), culture_traits(game_dir), hierarchy)
    rebound: dict[str, list[str]] = {}
    seat_file = ""
    for key, consumer in checked.consumers.items():
        if checked.verdicts[key].decision is not Decision.REBIND:
            continue
        if consumer.category == FORMABLES:
            rebound.setdefault(consumer.files[0], []).append(consumer.ident)
        elif key == GAME_START:
            seat_file = consumer.files[0]
        else:
            message = f"{key} is to be rebound, and nothing here knows how"
            raise ContentError(message)
    done, thin = rebind_formables(store, basis, rebound)
    generated = {place.key for place in basis.candidates}
    for rebinding in done.values():
        stray = sorted(set(rebinding.places) - generated)
        if stray:
            message = f"{rebinding.formable} is bound to places that are not generated: {stray[:5]}"
            raise ContentError(message)
    guarded = guard_scripts(store, [*guard_targets(checked.consumers, checked.verdicts), *thin])
    nahuatl = [place for place in basis.candidates if place.religion == NAHUATL]
    seat = max(nahuatl, key=lambda place: (place.population, place.key)).key if nahuatl else None
    if not seat_file:
        message = f"{GAME_START} is no longer to be rebound"
        raise ContentError(message)
    start_bound = rebind_game_start(store, seat_file, old_seat=remap[TENOCHTITLAN], seat=seat)
    changed = store.changed()
    for relative, data in changed.items():
        try:
            _ = parse(data.decode("utf-8-sig"))
        except PdxSyntaxError as error:
            message = f"{relative} no longer reads after the decisions: {error}"
            raise ContentError(message) from error
    scripts.update(changed)
    return {
        "guarded": guarded,
        "formables": {
            tag: {
                "places": len(found.places),
                "seat": found.seat,
                "vanilla_places": found.vanilla_size,
            }
            for tag, found in sorted(done.items())
        },
        "formables_too_thin": sorted(target.ident for target in thin),
        "game_start_bound": start_bound,
    }
