"""The export's check that every consumer of the replaced content has a decision.

A patch that adds a script object naming the American tags, locations, provinces, areas,
regions or subcontinents fails the export here until ``content_decisions`` decides it
(content plan, N0). The check reads the same script files the export rewrites and changes
no output.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.content_decisions import TABLE, Verdict, decide, missing
from rnw.content_inventory import (
    Consumer,
    Footprint,
    category_of,
    objects,
    read_footprint,
    residuals,
    scan,
)
from rnw.eu5_remap import script_files

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from collections.abc import Set as AbstractSet
    from pathlib import Path

MODIFIERS: Final[str] = "menu/static_modifiers"
SHOWN: Final[int] = 12
# Words that are not references: the decision says a given name equals a location key.
NOT_A_REFERENCE: Final[str] = "name"


@dataclass(frozen=True, slots=True)
class Checked:
    """The consumers of the replaced content, each with the decision it has."""

    footprint: Footprint
    consumers: Mapping[str, Consumer]
    verdicts: Mapping[str, Verdict]

    def stats(self) -> dict[str, object]:
        """Counts of the consumers by decision, for the export's report."""
        counts = Counter(verdict.decision.value for verdict in self.verdicts.values())
        return {
            "content_consumers": len(self.consumers),
            "content_decisions": dict(sorted(counts.items())),
        }


def check_decisions(
    game_dir: Path,
    *,
    events: Iterable[str],
    modifiers: Iterable[str],
    removed_tags: Iterable[str],
    table: Mapping[str, Verdict] = TABLE,
) -> Checked:
    """The consumers with their decisions; raises ``ValueError`` on a missing decision.

    ``events`` and ``modifiers`` are the objects the exporter retired, ``removed_tags`` the
    tags it removed, which the footprint of the vanilla Americas must cover.
    """
    footprint = read_footprint(game_dir)
    outside = sorted(set(removed_tags) - footprint.tags)
    if outside:
        message = f"Tags retired outside the American footprint: {', '.join(outside)}"
        raise ValueError(message)
    consumers = scan(game_dir, footprint, {"events": events, MODIFIERS: modifiers})
    undecided = missing(consumers.values(), footprint.tags, table)
    if undecided:
        shown = ", ".join(undecided[:SHOWN]) + (" ..." if len(undecided) > SHOWN else "")
        message = (
            f"{len(undecided)} script objects naming the replaced content have no decision: {shown}"
        )
        raise ValueError(message)
    verdicts: dict[str, Verdict] = {}
    for key, consumer in consumers.items():
        verdict = decide(consumer, footprint.tags, table)
        if verdict is None:  # pragma: no cover - ``missing`` returned nothing
            raise ValueError(key)
        verdicts[key] = verdict
    return Checked(footprint, consumers, verdicts)


def _shown(items: list[str]) -> str:
    return ", ".join(items[:SHOWN]) + (" ..." if len(items) > SHOWN else "")


def check_outcomes(
    game_dir: Path,
    scripts: Mapping[str, bytes],
    checked: Checked,
    present: Mapping[str, AbstractSet[str]],
) -> dict[str, int]:
    """Stop the export unless the scripts it writes keep what was decided (content plan, F1).

    ``scripts`` are the script files the export wrote, by mod path; every other script file is
    the game's own. Two things must hold, and neither is a repair of anything: no object of the
    game's scripts has vanished that the exporter did not retire (its events and modifiers), and
    no object still names an American key that the generated world lacks (the engine logs each
    such key as an error when it loads the scripts, EU5 1.4.4, C223). A word that the decision
    table calls a given name is no reference. Raises ``ValueError`` listing the offenders.
    """
    files = script_files(game_dir)
    original = {relative: path.read_bytes().decode("utf-8-sig") for relative, path in files.items()}
    final = {
        relative: scripts[relative].decode("utf-8-sig") if relative in scripts else text
        for relative, text in original.items()
    }
    vanished: list[str] = []
    for relative in sorted(scripts.keys() & files.keys()):
        category = category_of(relative)
        for ident in sorted(objects(original[relative]) - objects(final[relative])):
            consumer = checked.consumers.get(f"{category}:{ident}")
            if consumer is None or not consumer.retired:
                vanished.append(f"{category}:{ident}")
    if vanished:
        message = (
            f"{len(vanished)} script objects vanished that no decision retires: {_shown(vanished)}"
        )
        raise ValueError(message)
    named = {
        key: kinds
        for key, kinds in residuals(final, checked.footprint, present).items()
        if checked.verdicts.get(key) is None or checked.verdicts[key].reason != NOT_A_REFERENCE
    }
    if named:
        shown = [
            f"{key} ({', '.join(f'{kind} {names[0]}' for kind, names in kinds.items())})"
            for key, kinds in named.items()
        ]
        message = (
            f"{len(named)} script objects name keys the generated world lacks: {_shown(shown)}"
        )
        raise ValueError(message)
    counted = sum(len(objects(text)) for text in final.values())
    return {"objects": counted, "rewritten": len(scripts)}
