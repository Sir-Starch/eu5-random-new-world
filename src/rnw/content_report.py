"""The inventory of the New World's vanilla content consumers, decided and counted.

Joins ``content_inventory`` (what names the replaced content), the exporter's own
retirements and ``content_decisions`` (what becomes of each) into one report, for the
``rnw content-inventory`` command and the local drift test (content plan, N0).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.content_decisions import CARRIERS, REASONS, Decision, Verdict, decide, missing, stale
from rnw.content_inventory import (
    GEOGRAPHY,
    Consumer,
    Footprint,
    read_footprint,
    scan,
    summarize,
)
from rnw.eu5_nw_export import TEMPLATES, retired_base_modifiers
from rnw.eu5_remap import remap_scripts
from rnw.pdx import Block, parse

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

POSITIONAL: Final[str] = "positional"
# The category of the files that hold static modifiers and the historical base values.
MODIFIERS: Final[str] = "menu/static_modifiers"


@dataclass(frozen=True, slots=True)
class Inventory:
    """Every consumer of the replaced content with its decision."""

    footprint: Footprint
    consumers: Mapping[str, Consumer]
    verdicts: Mapping[str, Verdict | None]
    events: int
    modifiers: int
    base_values: int

    @property
    def missing(self) -> list[str]:
        """Consumers without a decision."""
        return missing(self.consumers.values(), self.footprint.tags)

    @property
    def stale(self) -> list[str]:
        """Decisions that no consumer matches."""
        return stale(self.consumers.values())

    @property
    def replaced(self) -> list[str]:
        """The consumers whose decision is to replace them."""
        return sorted(
            key
            for key, verdict in self.verdicts.items()
            if verdict is not None and verdict.decision is Decision.REPLACE
        )

    @property
    def uncarried(self) -> list[str]:
        """Replaced consumers that nothing says carries them (not even ``none:``)."""
        return [key for key in self.replaced if key not in CARRIERS]

    @property
    def stale_carriers(self) -> list[str]:
        """Carriers of objects that are no longer replaced."""
        return sorted(CARRIERS.keys() - set(self.replaced))


def build(game_dir: Path) -> Inventory:
    """Scan the installation and decide every consumer it finds."""
    footprint = read_footprint(game_dir)
    rewrite = remap_scripts(game_dir, {}, set(footprint.tags))
    events = sorted({event for found in rewrite.retired.values() for event in found})
    templates = (game_dir / TEMPLATES).read_text(encoding="utf-8-sig")
    bodies = {
        entry.key: templates[entry.value.open : entry.value.close + 1]
        for entry in parse(templates).entries
        if entry.key is not None and isinstance(entry.value, Block)
    }
    values = sorted(retired_base_modifiers(bodies, set(footprint.keys["location"])))
    consumers = scan(
        game_dir, footprint, {"events": events, MODIFIERS: [*rewrite.modifiers, *values]}
    )
    verdicts = {key: decide(consumer, footprint.tags) for key, consumer in consumers.items()}
    return Inventory(
        footprint, consumers, verdicts, len(events), len(rewrite.modifiers), len(values)
    )


def _positional(inventory: Inventory) -> dict[str, object]:
    """What N5 would make semantic: the consumers kept by position and the keys they name."""
    chosen = [
        consumer
        for key, consumer in inventory.consumers.items()
        if (verdict := inventory.verdicts[key]) is not None and verdict.reason == POSITIONAL
    ]
    keys = {
        kind: sorted({word for c in chosen for word in c.refs.get(kind, ())}) for kind in GEOGRAPHY
    }
    return {
        "consumers": len(chosen),
        "files": len({file for c in chosen for file in c.files}),
        "keys": {kind: len(names) for kind, names in keys.items()},
        "by_category": dict(sorted(Counter(c.category for c in chosen).items())),
    }


def _carriers(inventory: Inventory) -> dict[str, object]:
    """What carries the purpose of the replaced objects: by family, and what nothing carries."""
    by_family: Counter[str] = Counter()
    for key in inventory.replaced:
        carrier = CARRIERS.get(key)
        by_family.update(carrier.families if carrier is not None else ())
    return {
        "replaced": len(inventory.replaced),
        "carried": sum(
            1 for key in inventory.replaced if key in CARRIERS and CARRIERS[key].families
        ),
        "none": sorted(
            key for key in inventory.replaced if key in CARRIERS and not CARRIERS[key].families
        ),
        "undecided": inventory.uncarried,
        "stale": inventory.stale_carriers,
        "by_family": dict(sorted(by_family.items())),
    }


def report(inventory: Inventory) -> dict[str, object]:
    """The inventory as plain data for the JSON file."""
    decisions: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    rows: list[dict[str, object]] = []
    for key, consumer in inventory.consumers.items():
        verdict = inventory.verdicts[key]
        if verdict is not None:
            decisions[verdict.decision.value] += 1
            reasons[f"{verdict.decision.value}/{verdict.reason}"] += 1
        rows.append(
            {
                "key": key,
                "files": list(consumer.files),
                "refs": {kind: list(names) for kind, names in consumer.refs.items()},
                "retired": consumer.retired,
                "decision": verdict.decision.value if verdict else None,
                "reason": verdict.reason if verdict else None,
                "stage": verdict.stage if verdict else None,
            }
        )
    return {
        "footprint": {
            "tags": len(inventory.footprint.tags),
            **{kind: len(names) for kind, names in inventory.footprint.keys.items()},
        },
        "retired": {
            "events": inventory.events,
            "modifiers": inventory.modifiers,
            "base_values": inventory.base_values,
        },
        "consumers": len(inventory.consumers),
        "decisions": {decision.value: decisions[decision.value] for decision in Decision},
        "reasons": dict(sorted(reasons.items())),
        "categories": summarize(inventory.consumers.values()),
        "positional": _positional(inventory),
        "missing": inventory.missing,
        "stale": inventory.stale,
        "carriers": _carriers(inventory),
        "reason_text": {
            reason: REASONS[reason] for reason in sorted({k.split("/")[1] for k in reasons})
        },
        "table": rows,
    }
