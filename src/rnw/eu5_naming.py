"""A name for the new state: the founder of a formable chooses between two generated names (N9).

A formable is named after its seat, or a realm after its region (``eu5_formation._naming``). Its
founder is asked once, when it forms it, whether to keep that name or to take the other one the
world offers: a seat-named formation the name of its seat's region, a realm the name of its
throne (history plan §22.2, the naming choice). The second name is renamed into with vanilla's
``change_country_name`` and ``change_country_adjective``, as ``fall_of_delhi`` renames with them;
that the engine accepts a generated key there is [INFERRED]. The nation of a colonial shore is
renamed by its founders' tradition instead, and the empire keeps the continent's name.

Formation is where RNW raises a country's rank, so the choice at formation is the choice at the
new rank; a rank reached otherwise keeps the game's own titles.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw import wording
from rnw.formations import BY_FAMILY
from rnw.formations import NAMING_DESC as DESC
from rnw.formations import NAMING_EVENT as NAMESPACE
from rnw.formations import NAMING_KEEP as KEEP
from rnw.formations import NAMING_TAKE as TAKE
from rnw.formations import NAMING_TITLE as TITLE
from rnw.game_texts import Described, Text
from rnw.wording import Phrase

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from rnw.content import Formation
    from rnw.game_texts import Entry
    from rnw.wording import Name

EVENT_FILE: Final[str] = f"in_game/events/{NAMESPACE}.txt"


@dataclass(frozen=True, slots=True)
class Naming:
    """A formation's founder may take ``other`` instead of its name, in event ``number``."""

    tag: str
    name: Phrase
    other: Phrase
    number: int


def alternative(
    formation: Formation, name: Phrase, names: Mapping[str, Name], regions: Mapping[str, Name]
) -> Phrase | None:
    """The second name of a formation, if the world offers one that differs from its name."""
    spec = BY_FAMILY[formation.family]
    if spec.renamed or formation.continent or not name.term.startswith(wording.FORMATION):
        return None
    word = names.get(formation.throne) if formation.region else regions.get(formation.home)
    if not isinstance(word, str) or word == name.word:
        return None
    return Phrase(wording.FORMATION + spec.stem, word)


def namings(
    pairs: Sequence[tuple[Formation, str, Phrase]],
    names: Mapping[str, Name],
    regions: Mapping[str, Name],
) -> dict[str, Naming]:
    """Each formation's choice, by tag: ``pairs`` are (formation, tag, name)."""
    found: dict[str, Naming] = {}
    for formation, tag, name in pairs:
        other = alternative(formation, name, names, regions)
        if other is not None:
            found[tag] = Naming(tag, name, other, len(found) + 1)
    return found


def event_id(naming: Naming) -> str:
    return f"{NAMESPACE}.{naming.number}"


def other_key(tag: str) -> str:
    """The key of the second name (``change_country_name``) and, with ``_ADJ``, its adjective."""
    return f"{tag}_other"


def fires(naming: Naming) -> str:
    """The line of the formation's effect that asks its founder."""
    return f"trigger_event_non_silently = {{ id = {event_id(naming)} }}"


def events(choices: Sequence[Naming]) -> str:
    """The script of the naming events: keep the name, or take the other one."""
    out = [f"namespace = {NAMESPACE}\n"]
    for naming in choices:
        event, key = event_id(naming), other_key(naming.tag)
        lines = [
            f"{event} = {{",
            "\ttype = country_event",
            f"\ttitle = {TITLE}",
            f"\tdesc = {DESC}",
            "\toutcome = neutral",
            "\tfire_only_once = yes",
            "",
            f"\ttrigger = {{ tag = {naming.tag} }}",
            "",
            f"\toption = {{ name = {event}.a ai_chance = {{ base = 70 }} }}",
            "",
            "\toption = {",
            f"\t\tname = {event}.b",
            f"\t\tchange_country_name = {key}",
            f"\t\tchange_country_adjective = {key}_ADJ",
            "\t\tai_chance = { base = 30 }",
            "\t}",
            "}",
        ]
        out.append("\n" + "".join(f"{line}\n" for line in lines))
    return "".join(out)


def texts(choices: Sequence[Naming]) -> dict[str, Entry]:
    """The second names and adjectives, and the event's texts with both names filled in."""
    found: dict[str, Entry] = {}
    if choices:
        found[TITLE] = Text(TITLE)
        found[DESC] = Text(DESC)
    for naming in choices:
        key = other_key(naming.tag)
        found[key] = naming.other
        found[f"{key}_ADJ"] = wording.adjective(naming.other.word)
        found[f"{event_id(naming)}.a"] = Described(KEEP, naming.name)
        found[f"{event_id(naming)}.b"] = Described(TAKE, naming.other)
    return found
