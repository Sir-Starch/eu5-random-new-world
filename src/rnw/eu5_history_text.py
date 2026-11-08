"""Original historical biases and a voluntary, generated-country chronicle.

This adapter is callable independently ahead of exporter activation. Its output
uses only live tags in script; extinct predecessors occur in localized prose.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw import game_texts, history_archive, history_story, history_text
from rnw.history_checks import require
from rnw.history_model import HistoryError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rnw.eu5_start import FinalStartPlan
    from rnw.loc_keys import KeySpace
    from rnw.wording import Name

BIAS_FILE: Final[str] = "in_game/common/biases/rnw_history.txt"
TRIGGER_FILE: Final[str] = "in_game/common/scripted_triggers/rnw_history.txt"
DECISION_FILE: Final[str] = "in_game/common/decisions/rnw_history.txt"
EVENT_FILE: Final[str] = "in_game/events/rnw_chronicle.txt"
TRIGGER: Final[str] = "rnw_has_recorded_history"
DECISION: Final[str] = "rnw_our_history"
EVENT: Final[str] = "rnw_chronicle.1"


@dataclass(frozen=True, slots=True)
class WrittenHistory:
    files: dict[str, bytes]
    texts: dict[str, game_texts.Entry]
    chronicles: dict[str, str]


def guarantee_lines(protections: Sequence[tuple[str, str]]) -> str:
    """Setup diplomacy, directed from provider to protected country."""
    return "".join(
        f"\tscripted_oneway = {{ first = {first} second = {second} type = guarantee }}\n"
        for first, second in protections
    )


def build(plan: FinalStartPlan, keys: KeySpace, locations: Sequence[str]) -> WrittenHistory:
    """The biases, the Our History decision and event, and each living country's story.

    ``locations`` are the world's location keys (the archive's places, ``history_archive``).
    """
    if plan.history is None:
        msg = "Historical text needs a projected history"
        raise HistoryError(msg)
    tags = tuple(sorted(country.tag for country in plan.countries))
    require(set(tags) == set(plan.history_tags.values()), "History text has different living tags")
    events = {event.key: event for event in plan.history.events}
    texts: dict[str, game_texts.Entry] = {
        opinion.key: history_text.opinion_text(opinion, plan.names, events[opinion.cause])
        for opinion in plan.historical_opinions
    }
    biases = "".join(
        f"{opinion.key} = {{ value = {opinion.value} yearly_decay = {opinion.yearly_decay} }}\n"
        for opinion in plan.historical_opinions
    )
    files = {BIAS_FILE: biases.encode("utf-8-sig")}
    if not tags:
        return WrittenHistory(files, texts, {})
    # A decision is named by ``<key>.title`` and ``<key>.desc``, as vanilla's decisions are.
    static = (
        f"{DECISION}.title",
        f"{DECISION}.desc",
        f"{DECISION}.a",
        f"{EVENT}.title",
        f"{EVENT}.a",
    )
    # The world's key space reserves the mod's static keys at its start; a bare one claims them.
    require(
        keys.holds(static) or keys.claim(static),
        "The fixed historical interface keys collide with localization",
    )
    chronicle_keys = {tag: keys.next("rnw_chronicle_", 0) for tag in tags}
    trigger = (
        f"{TRIGGER} = {{\n\tOR = {{\n" + "".join(f"\t\ttag = {tag}\n" for tag in tags) + "\t}\n}\n"
    )
    decision = (
        f"{DECISION} = {{\n"
        "\tdecision_category = country_specific_decisions\n"
        f"\tpotential = {{ {TRIGGER} = yes }}\n"
        "\tallow = { always = yes }\n"
        "\tai_will_do = { value = 0 }\n"
        "\toption = {\n"
        f"\t\tname = {DECISION}.a\n"
        "\t\tai_chance = { value = 100 }\n"
        f"\t\teffect = {{ trigger_event_non_silently = {EVENT} }}\n"
        "\t}\n}\n"
    )
    descriptions = "".join(
        (
            "\t\t\ttriggered_desc = {\n"
            f"\t\t\t\ttrigger = {{ tag = {tag} }}\n"
            f"\t\t\t\tdesc = {chronicle_keys[tag]}\n"
            "\t\t\t}\n"
        )
        for tag in tags
    )
    event = (
        f"namespace = rnw_chronicle\n\n{EVENT} = {{\n"
        "\ttype = country_event\n"
        "\toutcome = neutral\n"
        f"\ttitle = {EVENT}.title\n"
        f"\ttrigger = {{ {TRIGGER} = yes }}\n"
        f"\tdesc = {{\n\t\tfirst_valid = {{\n{descriptions}\t\t}}\n\t}}\n"
        f"\toption = {{ name = {EVENT}.a }}\n"
        "}\n"
    )
    for key in static:
        texts[key] = game_texts.Text(key)
    texts.update((chronicle_keys[tag], story) for tag, story in stories(plan, locations).items())
    files.update(
        (path, text.encode("utf-8-sig"))
        for path, text in ((TRIGGER_FILE, trigger), (DECISION_FILE, decision), (EVENT_FILE, event))
    )
    return WrittenHistory(files, texts, chronicle_keys)


def stories(plan: FinalStartPlan, locations: Sequence[str]) -> dict[str, history_story.Story]:
    """Each living country's story, told from the history archive as the window tells it: a
    country by its name on the map, a predecessor by the name of its seat."""
    archive = history_archive.build(plan, locations)
    names = {country.tag: country.name for country in plan.countries}
    called: dict[int, Name] = {
        fact.actor: names[fact.tag] for fact in archive.countries if fact.tag in names
    }

    def name(actor: int) -> Name:
        return called.get(actor) or plan.names[locations[archive.actors[actor].seat]]

    def place(index: int) -> Name:
        return plan.names[locations[index]]

    actors = {fact.tag: fact.actor for fact in archive.countries}
    return {
        tag: history_story.tell(archive, actors[tag], name=name, place=place)
        for tag in sorted(plan.history_tags.values())
    }
