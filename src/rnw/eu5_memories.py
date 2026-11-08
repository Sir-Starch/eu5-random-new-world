"""Events of the recorded past: each one a projected memory and its cause (history plan §22, N9).

The history's memories reach the game as named opinions (``history_diplomacy``); they fade within
decades. N9 lets the strongest of them return once as a choice. Every country that holds a
qualifying memory may receive one event about it in a window of its own (vanilla's
``dynamic_historical_event``, as the stories start): the strongest by value, then the most recent.

* **Lost land.** A grievance with a place, from a conflict or a breakaway, while the other country
  still holds the place: take a core on it (vanilla's ``cb_conquer_province`` then opens) or let
  the wound close.
* **Old pact.** Trust from a defence pact or a protection agreement: renew the friendship or let it
  lapse.
* **Kin.** A memory of a migration, held with the country the cohorts moved to or from: welcome
  the kin or keep them at a distance.
* **Shrine.** A memory of an agreement of sacred access, while the other country still holds the
  shrine: honour its peace or claim it.
* **Heir.** Every heir of a fallen realm that has a restoration (N7) remembers it until it is
  restored: swear to restore it, or let it rest.

Every event names its cause, a recorded history event, in the export report (N-C6). The effects
are vanilla's: ``add_core``, ``add_opinion`` with vanilla biases, ``add_prestige`` and
``add_stability`` with vanilla values; the texts are static, translated, and name the other
country and the place through saved scopes (an heir's place is the fallen realm's seat).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rnw.content import RESTORATION
from rnw.game_texts import Bound, Text
from rnw.history_model import Action, Factor
from rnw.memory_texts import (
    BIASES_DIR,
    CHANCES,
    FIRST_YEAR,
    HEIR,
    KIN,
    LOST_LAND,
    NAMESPACE,
    OLD_PACT,
    RECOGNIZED,
    REFUSED,
    SHRINE,
    SPREAD,
    TEXTS,
    VALUES,
    VALUES_DIR,
    WINDOW,
)
from rnw.rng import derive_seed

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from rnw.content import ContentPlan, Fallen, Formation
    from rnw.eu5_start import FinalStartPlan
    from rnw.game_texts import Entry
    from rnw.loc_keys import KeySpace


class RecallError(ValueError):
    """A bias or a value that the memory events lean on is gone from the installation."""


@dataclass(frozen=True, slots=True)
class Memory:
    """One event of the recorded past for one country.

    ``bearer`` holds the memory, ``partner`` is the other country (empty for an heir), ``place``
    the location it is about, ``cause`` the recorded history event, ``realm`` the index of the
    restoration an heir remembers (-1 otherwise).
    """

    family: str
    bearer: str
    partner: str
    place: str
    cause: str
    year: int
    start: int
    until: int
    chance: int
    realm: int = -1


def _family(action: Action, factor: Factor, place: str) -> str:
    if factor is Factor.GRIEVANCE and place and action in {Action.CONFLICT, Action.SECESSION}:
        return LOST_LAND
    if factor is Factor.TRUST and action in {Action.PACT, Action.PROTECTION}:
        return OLD_PACT
    if factor in {Factor.TRUST, Factor.AFFINITY} and place and action is Action.MIGRATION:
        return KIN
    if factor in {Factor.TRUST, Factor.AFFINITY} and action is Action.ACCESS:
        return SHRINE
    return ""


def _window(seed: int, family: str, bearer: str) -> tuple[int, int, int]:
    draw = derive_seed(seed, "memory", family, bearer)
    start = FIRST_YEAR + draw % SPREAD
    return start, start + WINDOW, CHANCES[(draw >> 16) % len(CHANCES)]


def select(
    plan: FinalStartPlan, content: ContentPlan, fallen: Sequence[Fallen], seed: int
) -> tuple[Memory, ...]:
    """The memory events of a world: one per country of its strongest memory, and the heirs'.

    A shrine's place is the place of its agreement (the recorded bond); a memory whose place no
    longer exists among the world's names is passed over. ``fallen`` are the fallen realms of the
    content's facts; each restoration's heirs remember theirs.
    """
    history = plan.history
    if history is None:
        return ()
    events = {event.key: event for event in history.events}
    best: dict[str, tuple[tuple[int, int, str], Memory]] = {}
    for opinion in plan.historical_opinions:
        place = opinion.place
        if opinion.action is Action.ACCESS:
            bonds = events[opinion.cause].effects.bonds
            place = next((bond.place for bond in bonds if bond.place), "")
            if not place:
                continue
        family = _family(opinion.action, opinion.factor, place)
        if not family or (place and place not in plan.names):
            continue
        start, until, chance = _window(seed, family, opinion.first)
        memory = Memory(
            family,
            opinion.first,
            opinion.second,
            place,
            opinion.cause,
            opinion.year,
            start,
            until,
            chance,
        )
        rank = (-abs(opinion.value), -opinion.year, opinion.cause)
        if opinion.first not in best or rank < best[opinion.first][0]:
            best[opinion.first] = (rank, memory)
    found = [memory for _, memory in sorted(best.values(), key=lambda item: item[1].bearer)]
    realms = {realm.key: realm for realm in fallen}
    for formation in content.formations:
        if formation.family != RESTORATION:
            continue
        realm = realms[formation.basis]
        for heir in formation.states:
            start, until, chance = _window(seed, HEIR, heir)
            found.append(
                Memory(
                    HEIR,
                    heir,
                    "",
                    formation.seat,
                    realm.cause,
                    realm.year,
                    start,
                    until,
                    chance,
                    formation.index,
                )
            )
    return tuple(found)


def check_installation(game_dir: Path) -> None:
    """Raise unless the vanilla biases and values the events name are defined."""
    defined = {
        line.split("=")[0].strip()
        for directory in (BIASES_DIR, VALUES_DIR)
        for path in sorted((game_dir / directory).glob("*.txt"))
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if "=" in line
    }
    for needed in (RECOGNIZED, REFUSED, *VALUES):
        if needed not in defined:
            message = f"The {needed} that the memory events lean on is gone from the game"
            raise RecallError(message)


def event_id(number: int) -> str:
    """The identifier of the ``number``-th memory event (from 1)."""
    return f"{NAMESPACE}.{number}"


def entry_key(number: int) -> str:
    """The key of the name the events list shows for a memory event (vanilla's
    ``<event>.entry``, which every event with a ``dynamic_historical_event`` window has)."""
    return f"{event_id(number)}.entry"


# The scopes a family's title names, and how the events list, which has no scopes, names them.
LOCATION_SCOPE: str = "[target_location.GetNameWithNoTooltip]"
PARTNER_SCOPE: str = "[partner.GetNameWithNoTooltip]"


def numbers(memories: Sequence[Memory], keys: KeySpace | None = None) -> list[int]:
    """The number of each memory event: in order from 1, past any number whose ``.entry`` key
    shares the engine's hash with a key already taken (``loc_keys``)."""
    found: list[int] = []
    number = 0
    for _ in memories:
        number += 1
        while keys is not None and not keys.claim((entry_key(number),)):
            number += 1
        found.append(number)
    return found


def _numbered(memories: Sequence[Memory], numbered: Sequence[int] | None) -> list[int]:
    if numbered is None:
        return list(range(1, len(memories) + 1))
    if len(numbered) != len(memories):
        message = "Every memory event needs one number"
        raise RecallError(message)
    return list(numbered)


def _entry(memory: Memory) -> Bound:
    """The family's title with its scopes bound to the memory's place and partner."""
    source = f"{NAMESPACE}.{memory.family}.title"
    english = TEXTS[source]
    bindings = [
        (token, value)
        for token, value, used in (
            (
                LOCATION_SCOPE,
                f"[ShowLocationNameWithNoTooltip('{memory.place}')]",
                bool(memory.place),
            ),
            (
                PARTNER_SCOPE,
                f"[GetCountry('{memory.partner}').GetNameWithNoTooltip]",
                bool(memory.partner),
            ),
        )
        if used and token in english
    ]
    return Bound(source, tuple(bindings))


def _both(opinion: str) -> list[str]:
    return [
        f"add_opinion = {{ target = scope:partner modifier = {opinion} }}",
        f"scope:partner = {{ add_opinion = {{ target = root modifier = {opinion} }} }}",
    ]


# Each family's trigger lines, and its two options: (effects, AI chance).
def _parts(memory: Memory, restored: str) -> tuple[list[str], list[str], list[str], int, int]:
    held = f"location:{memory.place} = {{ owner ?= c:{memory.partner} }}"
    exists = f"country_exists = c:{memory.partner}"
    core = f"location:{memory.place} = {{ add_core = root }}"
    if memory.family == LOST_LAND:
        return [exists, held], [core], ["add_stability = stability_weak_bonus"], 60, 40
    if memory.family == OLD_PACT:
        return [exists], _both(RECOGNIZED), ["add_prestige = prestige_weak_bonus"], 70, 30
    if memory.family == KIN:
        return [exists], _both(RECOGNIZED), ["add_stability = stability_weak_bonus"], 60, 40
    if memory.family == SHRINE:
        claim = [core, *_both(REFUSED)]
        return [exists, held], [*_both(RECOGNIZED)], claim, 60, 40
    keep = ["add_stability = stability_weak_bonus"]
    return (
        [f"NOT = {{ country_exists = c:{restored} }}"],
        ["add_prestige = prestige_weak_bonus"],
        keep,
        70,
        30,
    )


def _lines(lines: Sequence[str], depth: int) -> str:
    return "".join("\t" * depth + line + "\n" for line in lines)


def events(
    memories: Sequence[Memory], restored: Mapping[int, str], numbered: Sequence[int] | None = None
) -> str:
    """The script of the memory events; ``restored`` gives the tag of each restoration and
    ``numbered`` the number of each event (``numbers``; in order from 1 without it)."""
    out = [f"namespace = {NAMESPACE}\n"]
    for number, memory in zip(_numbered(memories, numbered), memories, strict=True):
        base = f"{NAMESPACE}.{memory.family}"
        trigger, first, second, first_ai, second_ai = _parts(memory, restored.get(memory.realm, ""))
        scopes: list[str] = []
        if memory.partner:
            scopes.append(f"c:{memory.partner} = {{ save_scope_as = partner }}")
        if memory.place:
            scopes.append(f"location:{memory.place} = {{ save_scope_as = target_location }}")
        body = [
            f"{event_id(number)} = {{",
            "\ttype = country_event",
            f"\ttitle = {base}.title",
            f"\tdesc = {base}.desc",
            "\toutcome = neutral",
            "\tfire_only_once = yes",
            "",
            "\tdynamic_historical_event = {",
            f"\t\ttag = {memory.bearer}",
            f"\t\tfrom = {memory.start}.1.1",
            f"\t\tto = {memory.until}.1.1",
            f"\t\tmonthly_chance = {memory.chance}",
            "\t}",
            "",
            "\ttrigger = {",
            *(f"\t\t{line}" for line in trigger),
            "\t}",
            "",
            "\timmediate = {",
            *(f"\t\t{line}" for line in scopes),
            "\t}",
        ]
        for key, effects, ai in (("a", first, first_ai), ("b", second, second_ai)):
            body += [
                "",
                "\toption = {",
                f"\t\tname = {base}.{key}",
                *(f"\t\t{line}" for line in effects),
                f"\t\tai_chance = {{ base = {ai} }}",
                "\t}",
            ]
        out.append("\n" + _lines([*body, "}"], 0))
    return "".join(out)


def texts(memories: Sequence[Memory], numbered: Sequence[int] | None = None) -> dict[str, Entry]:
    """The localization: the static texts of each family that the world's events use, and the
    name of each event in the events list (its family's title, of its own place)."""
    found: dict[str, Entry] = {
        f"{NAMESPACE}.{memory.family}.{part}": Text(f"{NAMESPACE}.{memory.family}.{part}")
        for memory in memories
        for part in ("title", "desc", "a", "b")
    }
    for number, memory in zip(_numbered(memories, numbered), memories, strict=True):
        found[entry_key(number)] = _entry(memory)
    return found


def stats(
    memories: Sequence[Memory], numbered: Sequence[int] | None = None
) -> list[dict[str, object]]:
    """The report's record of each memory event and its cause (N-C6)."""
    return [
        {
            "event": event_id(number),
            "family": memory.family,
            "bearer": memory.bearer,
            **({"partner": memory.partner} if memory.partner else {}),
            **({"place": memory.place} if memory.place else {}),
            "cause": memory.cause,
            "year": memory.year,
        }
        for number, memory in zip(_numbered(memories, numbered), memories, strict=True)
    ]


def restorations(formations: Sequence[Formation], tags: Sequence[str]) -> dict[int, str]:
    """The tag of each restoration by its index, from the formations and their tags."""
    return {
        formation.index: tag
        for formation, tag in zip(formations, tags, strict=True)
        if formation.family == RESTORATION
    }
