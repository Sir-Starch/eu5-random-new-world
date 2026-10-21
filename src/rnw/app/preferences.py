"""What the player chose once and the generator remembers: a JSON file in its data folder."""

from __future__ import annotations

import contextlib
import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Final, cast

if TYPE_CHECKING:
    from pathlib import Path

FILE: Final[str] = "preferences.json"


@dataclass(frozen=True, slots=True)
class Preferences:
    """The player's choices; every default keeps the New World hidden."""

    reveal_thumbnails: bool = False


def load(data: Path) -> Preferences:
    """The saved choices; a missing or damaged file gives the defaults."""
    with contextlib.suppress(OSError, ValueError, TypeError):
        row = cast("dict[str, object]", json.loads((data / FILE).read_text(encoding="utf-8")))
        return Preferences(reveal_thumbnails=row.get("reveal_thumbnails") is True)
    return Preferences()


def save(data: Path, preferences: Preferences) -> None:
    """Write the choices, whole."""
    data.mkdir(parents=True, exist_ok=True)
    scratch = data / f".{FILE}.new"
    _ = scratch.write_text(json.dumps(asdict(preferences), indent=1), encoding="utf-8")
    _ = scratch.replace(data / FILE)
