"""The list of worlds a player has generated: a JSON file, newest first, never large."""

from __future__ import annotations

import contextlib
import json
import time
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Final, cast

if TYPE_CHECKING:
    from pathlib import Path

FILE: Final[str] = "history.json"
LIMIT: Final[int] = 200
SCHEMA: Final[int] = 1


@dataclass(frozen=True, slots=True)
class Entry:
    """One generation: the world code, when, for which game build, and what became of it."""

    code: str
    when: int
    game_build: str
    outcome: str
    note: str = ""


def load(directory: Path) -> list[Entry]:
    """Entries of ``directory``'s history, newest first; a missing or damaged file is empty."""
    with contextlib.suppress(OSError, ValueError, KeyError, TypeError):
        data = cast("dict[str, object]", json.loads((directory / FILE).read_text(encoding="utf-8")))
        if data.get("schema") == SCHEMA:
            rows = cast("list[dict[str, object]]", data["entries"])
            return [
                Entry(
                    code=str(row["code"]),
                    when=int(str(row["when"])),
                    game_build=str(row.get("game_build", "")),
                    outcome=str(row.get("outcome", "")),
                    note=str(row.get("note", "")),
                )
                for row in rows
            ]
    return []


def record(directory: Path, entry: Entry) -> list[Entry]:
    """Put ``entry`` first, keep the newest ``LIMIT``, write the file whole; returns the list."""
    entries = [entry, *load(directory)][:LIMIT]
    directory.mkdir(parents=True, exist_ok=True)
    document = {"schema": SCHEMA, "entries": [asdict(item) for item in entries]}
    scratch = directory / f".{FILE}.new"
    _ = scratch.write_text(json.dumps(document, indent=1, ensure_ascii=False), encoding="utf-8")
    _ = scratch.replace(directory / FILE)
    return entries


def now() -> int:
    """Seconds since the epoch, for entries."""
    return int(time.time())
