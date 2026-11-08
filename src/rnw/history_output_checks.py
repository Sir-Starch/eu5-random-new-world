"""Read historical EU5 artifacts back and reject unintended scopes or effects.

These checks inspect written records rather than regenerating expected scripts.
They complement the final plan's causal check; engine loading remains H7.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from rnw import eu5_history_text as writer
from rnw.history_checks import require
from rnw.history_model import HistoryError
from rnw.pdx import Block, parse

if TYPE_CHECKING:
    from collections.abc import Mapping

    from rnw.eu5_start import FinalStartPlan


def _block(parent: Block, key: str) -> Block:
    found = parent.block(key)
    if found is None:
        message = f"Historical output lacks block {key}"
        raise HistoryError(message)
    return found


def _shape(block: Block, fields: set[str]) -> None:
    require(
        len(block.entries) == len(fields)
        and {entry.key for entry in block.entries} == fields
        and all(entry.op == "=" for entry in block.entries),
        "Historical output has missing, repeated or unexpected fields",
    )


def _values(block: Block, expected: Mapping[str, str]) -> None:
    _shape(block, set(expected))
    require(
        all(
            entry.op == "=" and entry.value == expected[entry.key]
            for entry in block.entries
            if entry.key is not None
        ),
        "Historical output has an unexpected value or effect",
    )


def verify_text(plan: FinalStartPlan, written: writer.WrittenHistory) -> None:
    """Check bias values, live scopes, voluntary activation and localization binding."""
    tags = {country.tag for country in plan.countries}
    paths = {writer.BIAS_FILE}
    if tags:
        paths.update((writer.TRIGGER_FILE, writer.DECISION_FILE, writer.EVENT_FILE))
    require(set(written.files) == paths, "Historical output has unexpected files or startup hooks")
    biases = parse(written.files[writer.BIAS_FILE].decode("utf-8-sig"))
    opinions = {opinion.key: opinion for opinion in plan.historical_opinions}
    _shape(biases, set(opinions))
    for key, opinion in opinions.items():
        _values(
            _block(biases, key),
            {"value": str(opinion.value), "yearly_decay": str(opinion.yearly_decay)},
        )
    if not tags:
        require(not written.texts and not written.chronicles, "An empty world has historical text")
        return
    require(set(written.chronicles) == tags, "A living country has no chronicle")
    require(len(set(written.chronicles.values())) == len(tags), "Countries share a chronicle key")
    _trigger(written, tags)
    _decision(written)
    _event(written, tags)
    expected_texts = {
        *opinions,
        *written.chronicles.values(),
        f"{writer.DECISION}.title",
        f"{writer.DECISION}.desc",
        f"{writer.DECISION}.a",
        f"{writer.EVENT}.title",
        f"{writer.EVENT}.a",
    }
    require(
        set(written.texts) == expected_texts,
        "Historical output has missing or unexpected localization",
    )


def _trigger(written: writer.WrittenHistory, tags: set[str]) -> None:
    trigger = parse(written.files[writer.TRIGGER_FILE].decode("utf-8-sig"))
    _shape(trigger, {writer.TRIGGER})
    body = _block(trigger, writer.TRIGGER)
    _shape(body, {"OR"})
    countries = _block(body, "OR")
    require(
        len(countries.entries) == len(tags)
        and all(entry.key == "tag" and entry.op == "=" for entry in countries.entries)
        and {entry.value for entry in countries.entries if isinstance(entry.value, str)} == tags,
        "The historical trigger differs from the living country set",
    )


def _decision(written: writer.WrittenHistory) -> None:
    decision = parse(written.files[writer.DECISION_FILE].decode("utf-8-sig"))
    _shape(decision, {writer.DECISION})
    body = _block(decision, writer.DECISION)
    _shape(body, {"decision_category", "potential", "allow", "ai_will_do", "option"})
    category = body.first("decision_category")
    require(
        category is not None and category.value == "country_specific_decisions",
        "Wrong historical decision category",
    )
    _values(_block(body, "potential"), {writer.TRIGGER: "yes"})
    _values(_block(body, "allow"), {"always": "yes"})
    _values(_block(body, "ai_will_do"), {"value": "0"})
    option = _block(body, "option")
    _shape(option, {"name", "ai_chance", "effect"})
    name = option.first("name")
    require(
        name is not None and name.value == f"{writer.DECISION}.a", "Wrong history decision option"
    )
    _values(_block(option, "ai_chance"), {"value": "100"})
    _values(_block(option, "effect"), {"trigger_event_non_silently": writer.EVENT})


def _event(written: writer.WrittenHistory, tags: set[str]) -> None:
    event = parse(written.files[writer.EVENT_FILE].decode("utf-8-sig"))
    _shape(event, {"namespace", writer.EVENT})
    namespace = event.first("namespace")
    require(
        namespace is not None and namespace.value == "rnw_chronicle", "Wrong chronicle namespace"
    )
    body = _block(event, writer.EVENT)
    _shape(body, {"type", "outcome", "title", "trigger", "desc", "option"})
    for field, expected in (
        ("type", "country_event"),
        ("outcome", "neutral"),
        ("title", f"{writer.EVENT}.title"),
    ):
        found = body.first(field)
        require(found is not None and found.value == expected, "Wrong chronicle event header")
    _values(_block(body, "trigger"), {writer.TRIGGER: "yes"})
    _values(_block(body, "option"), {"name": f"{writer.EVENT}.a"})
    description = _block(body, "desc")
    _shape(description, {"first_valid"})
    branches = _block(description, "first_valid")
    selected: dict[str, str] = {}
    for entry in branches.entries:
        if entry.key != "triggered_desc" or not isinstance(entry.value, Block):
            message = "Invalid conditional chronicle"
            raise HistoryError(message)
        _shape(entry.value, {"trigger", "desc"})
        gate = _block(entry.value, "trigger")
        _shape(gate, {"tag"})
        tag, text = gate.first("tag"), entry.value.first("desc")
        if (
            tag is None
            or text is None
            or not isinstance(tag.value, str)
            or not isinstance(text.value, str)
        ):
            message = "Chronicle selection has no scalar tag or text"
            raise HistoryError(message)
        selected[tag.value] = text.value
    require(
        len(branches.entries) == len(tags) and selected == written.chronicles,
        "Chronicle descriptions differ from living country bindings",
    )


def verify_diplomacy(plan: FinalStartPlan, text: str, original: str, gone: set[str]) -> None:
    """Planned guarantees and subjecthood, with vanilla relations preserved."""
    tags = {country.tag for country in plan.countries}

    def records(source: str, key: str, kind_field: str) -> list[tuple[str, str, str]]:
        manager = parse(source).block("diplomacy_manager")
        require(manager is not None, "Diplomacy has no manager")
        found: list[tuple[str, str, str]] = []
        for entry in manager.find(key) if manager is not None else ():
            require(isinstance(entry.value, Block), "Invalid directed diplomacy record")
            if isinstance(entry.value, Block):
                fields = {
                    row.key: row.value for row in entry.value.entries if isinstance(row.value, str)
                }
                found.append(
                    (fields.get("first", ""), fields.get("second", ""), fields.get(kind_field, ""))
                )
        return found

    for key, kind_field, kind, planned in (
        ("scripted_oneway", "type", "guarantee", plan.protections),
        ("dependency", "subject_type", "vassal", plan.vassals),
    ):
        actual = records(text, key, kind_field)
        expected = [(first, second, kind) for first, second in planned]
        generated = [row for row in actual if {row[0], row[1]} & tags]
        require(Counter(generated) == Counter(expected), "Written diplomacy differs from history")
        require(
            [row for row in actual if not {row[0], row[1]} & tags]
            == [row for row in records(original, key, kind_field) if not {row[0], row[1]} & gone],
            "Old World directed diplomacy differs from vanilla",
        )
