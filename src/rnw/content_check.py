"""The export's check that every consumer of the replaced content has a decision.

A patch that adds a script object naming the American tags, locations, provinces, areas,
regions or subcontinents fails the export here until ``content_decisions`` decides it
(content plan, N0). The check reads the same script files the export rewrites and changes
no output.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Final

from rnw.content_decisions import decide, missing
from rnw.content_inventory import read_footprint, scan

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

MODIFIERS: Final[str] = "menu/static_modifiers"
SHOWN: Final[int] = 12


def check_decisions(
    game_dir: Path,
    *,
    events: Iterable[str],
    modifiers: Iterable[str],
    removed_tags: Iterable[str],
) -> dict[str, object]:
    """Counts of the consumers by decision; raises ``ValueError`` on a missing decision.

    ``events`` and ``modifiers`` are the objects the exporter retired, ``removed_tags`` the
    tags it removed, which the footprint of the vanilla Americas must cover.
    """
    footprint = read_footprint(game_dir)
    outside = sorted(set(removed_tags) - footprint.tags)
    if outside:
        message = f"Tags retired outside the American footprint: {', '.join(outside)}"
        raise ValueError(message)
    consumers = scan(game_dir, footprint, {"events": events, MODIFIERS: modifiers})
    undecided = missing(consumers.values(), footprint.tags)
    if undecided:
        shown = ", ".join(undecided[:SHOWN]) + (" ..." if len(undecided) > SHOWN else "")
        message = (
            f"{len(undecided)} script objects naming the replaced content have no decision: {shown}"
        )
        raise ValueError(message)
    counts: Counter[str] = Counter()
    for consumer in consumers.values():
        verdict = decide(consumer, footprint.tags)
        if verdict is not None:
            counts[verdict.decision.value] += 1
    return {"content_consumers": len(consumers), "content_decisions": dict(sorted(counts.items()))}
