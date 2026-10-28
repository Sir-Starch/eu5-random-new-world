"""Render the public content reference from original, game-independent definitions."""

# Executable documentation script; typographic punctuation is part of the Markdown output.
# ruff: noqa: INP001, RUF001

from __future__ import annotations

import argparse
import re
from pathlib import Path

from rnw.content import RULES
from rnw.eu5_places import SPECS as PLACES
from rnw.formations import SPECS
from rnw.stories import STORIES
from rnw.storymodel import AFFORD, CLEANUP, CLEANUP_MONTHS, PULSE_START, Source, Story

OUTPUT = Path(__file__).with_name("content-reference.md")
TITLES = {modifier.name: modifier.title for story in STORIES for modifier in story.modifiers}


def source(value: Source) -> str:
    return f"`{value.kind}:{value.name}{'.' + value.block if value.block else ''}`"


def cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def effect(line: str, story: Story) -> str:
    """Explain authored effects; refuse new syntax until its explanation is supplied."""
    if match := re.fullmatch(r"var:(\w+) \?= \{ (.*) \}", line):
        place = "story centre" if match[1] == story.centre else "partner location"
        return f"At {place}: {effect(match[2], story)}"
    if match := re.fullmatch(r"owner \?= \{ (.*) \}", line):
        return f"for its owner: {effect(match[1], story)}"
    if match := re.fullmatch(r"province = \{ change_province_food_percentage = ([\d.-]+) \}", line):
        return f"province food change: {float(match[1]) * 100:+g}% (vanilla effect)"
    return direct_effect(line, story)


def direct_effect(line: str, story: Story) -> str:  # noqa: PLR0911 - one per script effect
    if match := re.fullmatch(r"change_gold_effect = \{ scale = (-?\d+) \}", line):
        return f"{'Pay' if int(match[1]) < 0 else 'Gain'} gold (vanilla scale {match[1]})"
    if match := re.fullmatch(
        r"add_(country|location)_modifier = \{ modifier = (\w+) years = (\d+) mode = add \}",
        line,
    ):
        return f"{TITLES[match[2]]} ({match[1]}, {match[3]} years)"
    if match := re.fullmatch(r"remove_(country|location)_modifier = (\w+)", line):
        return f"remove {TITLES[match[2]]}"
    if match := re.fullmatch(
        r"add_(stability|legitimacy|prestige) = \w+?_(weak|mild)_(bonus|penalty)", line
    ):
        return f"{match[1].capitalize()}: {match[2]} {match[3]} (vanilla scale)"
    if match := re.fullmatch(
        r"add_opinion_mutual_effect = \{ target = scope:target_country modifier = (\w+) \}",
        line,
    ):
        return f"mutual opinion with partner: `{match[1]}` (vanilla modifier)"
    if line == "set_variable = { name = rnw_sacred_privilege_open value = 1 }":
        return "unlock the High Priesthood of the Shrine estate privilege"
    if line == "remove_variable = rnw_sacred_privilege_open":
        return "remove the unlock for the High Priesthood of the Shrine privilege"
    if re.fullmatch(rf"set_variable = \{{ name = {story.path} value = \d+ \}}", line):
        return "record the chosen branch"
    if line in {f"remove_variable = {variable}" for variable in story.variables()}:
        return "clear story state"
    message = f"Document the new effect in {story.family}: {line}"
    raise ValueError(message)


def effects(lines: tuple[str, ...], story: Story) -> str:
    found = [effect(line, story) for line in lines]
    return "; ".join(dict.fromkeys(found)) or "None."


def story_section(story: Story) -> list[str]:
    out = [f"## {story.family}", "", f"Namespace: `{story.namespace}`.", ""]
    if story.pulse:
        pulse = story.pulse
        out += [
            (
                f"Yearly start chance: **{pulse.chance}%**; repeat cooldown: "
                f"**{pulse.quiet_years} years**. Hidden start: `{story.event(PULSE_START)}`."
            ),
            "",
            "Start conditions (all required, plus no active branch or cooldown):",
            "",
            "```text",
            *pulse.trigger,
            "```",
            "",
        ]
    else:
        out += [
            (
                "Start: a world-specific bearer and dynamic historical event window; see the "
                "[catalogue](content-catalog.md#when-stories-start)."
            ),
            "",
        ]
    out += [
        (
            f"Hidden cleanup: `{story.event(CLEANUP)}`, scheduled after "
            f"{CLEANUP_MONTHS} months. Every visible event requires the receiver to own the "
            "story centre and any partner-location variable to exist."
        ),
        "",
    ]
    if story.gate or story.immediate:
        out += [
            "Additional shared conditions and scope setup:",
            "",
            "```text",
            *story.gate,
            *story.immediate,
            "```",
            "",
        ]
    for node in story.nodes:
        out += [
            f'<a id="{story.namespace}-{node.number}"></a>',
            "",
            f"### {story.event(node.number)} — {node.title}",
            "",
        ]
        out += [
            "<details>",
            "<summary>Event text</summary>",
            "",
            node.desc.replace(r"\n\n", "\n\n"),
            "",
            "</details>",
            "",
        ]
        if node.immediate:
            out += [f"**On opening:** {effects(node.immediate, story)}.", ""]
        out += ["| Choice | Effects | Next event | AI weight |", "|---|---|---|---|"]
        for option in node.options:
            choice = f"**{option.key}.** {option.text}"
            if option.trigger:
                choice += f" **Requires:** `{option.trigger}`."
            follow = option.follow
            next_event = "End"
            if follow:
                next_event = (
                    f"[{story.event(follow.node)}](#{story.namespace}-{follow.node}); "
                    f"{follow.months[0]}–{follow.months[1]} months"
                )
            out += [
                (
                    f"| {cell(choice)} | {cell(effects(option.effects, story))} | "
                    f"{next_event} | {option.ai} |"
                )
            ]
        # Exact conditions remain available without mixing implementation state into prose.
        out += [
            "",
            "<details>",
            "<summary>Exact event conditions and effects</summary>",
            "",
            "```text",
            "# Additional node conditions",
            *node.requires,
            "# On opening",
            *node.immediate,
        ]
        for option in node.options:
            out += [f"# Choice {option.key}", *option.effects]
        out += ["```", "", "</details>", ""]
    out += [
        "### Modifiers",
        "",
        "| ID / title | Scope | Meaning | Vanilla payload source |",
        "|---|---|---|---|",
    ]
    for modifier in story.modifiers:
        out += [
            (
                f"| `{modifier.name}` — {modifier.title} | {modifier.category} | "
                f"{cell(modifier.text)} | {source(modifier.source)} |"
            )
        ]
    for privilege in story.privileges:
        out += [
            "",
            (
                f"**Estate privilege:** {privilege.title} (`{privilege.name}`), "
                f"estate `{privilege.estate}`. {privilege.text} "
                f"Available while `{privilege.opened_by}` is set. "
                f"Country modifier source: {source(privilege.source)}."
            ),
        ]
    return [*out, ""]


def render() -> str:
    nodes = sum(len(story.nodes) for story in STORIES)
    choices = sum(len(node.options) for story in STORIES for node in story.nodes)
    out = [
        "# Dynamic content: complete reference",
        "",
        (
            "Generated by `uv run python docs/build_content_reference.py`; edit the definitions, "
            "then regenerate. For eligibility, gameplay summaries and world-specific names, "
            "start with the [player catalogue](content-catalog.md). **Contains spoilers.**"
        ),
        "",
        (
            f"[V-EXEC C409] {len(STORIES)} story families, {nodes} visible events, "
            f"{choices} choices, "
            f"{len(SPECS)} formable families and {len(PLACES)} exceptional-place types. "
            "Hidden start/cleanup events are listed separately. This describes generated scripts, "
            "not a claim that every path has been observed in game."
        ),
        "",
        (
            "Gold and stability/legitimacy/prestige use vanilla scripted scales, "
            "not fixed currency or point amounts. Paid choices require "
            f"`{AFFORD}`. AI weights are relative "
            "among currently available options. Modifier descriptions explain their purpose; "
            "numeric payloads are read from the installed game at generation time. "
            "Vanilla payload text is not reproduced here."
        ),
        "",
        "## Contents",
        "",
        *[f"- [{story.family}](#{story.family})" for story in STORIES],
        "- [Formable countries](#formable-countries)",
        "- [Exceptional places](#exceptional-places)",
        "",
    ]
    for story in STORIES:
        out += story_section(story)
    out += [
        "## Formable countries",
        "",
        (
            "Territory and eligibility are explained in the "
            "[catalogue](content-catalog.md#formable-countries). "
            "Minimum counts below select opportunities at generation time; ownership fractions "
            "are requirements for formation during play."
        ),
        "",
    ]
    for spec in SPECS:
        rule = RULES[spec.family]
        out += [
            f"### {spec.family}",
            "",
            spec.description.replace("{name}", "*generated name*"),
            "",
            f"- Key: `rnw_{spec.stem}_<index>_f` (index starts at 1).",
            (
                f"- Level **{spec.level}**; rank `{spec.rank}`; "
                f"ownership fraction **{spec.fraction}**."
            ),
            (
                f"- Generation: at most **{rule.limit}**; "
                f"**{rule.places}–{rule.territory}** locations; "
                f"at least **{rule.centres}** centres and **{rule.states}** states "
                "with capitals inside; "
                f"at most **{rule.bearers}** eligible starting tags."
            ),
            f"- Additional formation conditions: {'; '.join(spec.allow) or 'none authored'}.",
            f"- Potential: {'; '.join(spec.potential) or 'world-specific starting tags'}.",
            (
                f"- Founding modifier: **{spec.modifier.title}** (`{spec.modifier.name}`), "
                f"**{spec.years} years**. {spec.modifier.text}"
            ),
            f"- Payload: {source(spec.modifier.source)}.",
            "",
        ]
    out += [
        "## Exceptional places",
        "",
        (
            "At most one place of each type, with no two on the same location. Terrain lists "
            "are ordered preferences: if none has a candidate, any suitable resource location "
            "can be used. A type without candidates is absent."
        ),
        "",
        "| Modifier / name | Resource | Terrain preference | Coast required | Vanilla source |",
        "|---|---|---|---|---|",
    ]
    for place in PLACES:
        out += [
            (
                f"| `{place.modifier}` — {place.name} | {place.material} | "
                f"{', '.join(place.topographies) or 'any'} | {place.coastal} | `{place.base}` |"
            )
        ]
    return "\n".join(out) + "\n"


class Arguments(argparse.Namespace):
    check: bool = False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("--check", action="store_true", help="Fail if the reference is stale")
    args = parser.parse_args(namespace=Arguments())
    text = render()
    if args.check:
        if OUTPUT.read_text(encoding="utf-8") != text:
            parser.exit(
                1, "Content reference is stale; run uv run python docs/build_content_reference.py\n"
            )
    else:
        _ = OUTPUT.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
