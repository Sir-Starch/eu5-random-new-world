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

    # Show the New World before it is played: in the generator's pictures, in the game's mod
    # list and on the new-game screen, where its countries can then be chosen.
    show_new_world: bool = False
    # The game's folder and the profile's, when the player chose them by hand because they were
    # not found: remembered, so that the question is asked once (ADR 0010, D).
    game_dir: str = ""
    profile_dir: str = ""


def load(data: Path) -> Preferences:
    """The saved choices; a missing or damaged file gives the defaults."""
    with contextlib.suppress(OSError, ValueError, TypeError):
        row = cast("dict[str, object]", json.loads((data / FILE).read_text(encoding="utf-8")))
        return Preferences(
            show_new_world=row.get("show_new_world") is True,
            game_dir=str(row.get("game_dir", "")),
            profile_dir=str(row.get("profile_dir", "")),
        )
    return Preferences()


def save(data: Path, preferences: Preferences) -> None:
    """Write the choices, whole."""
    data.mkdir(parents=True, exist_ok=True)
    scratch = data / f".{FILE}.new"
    _ = scratch.write_text(json.dumps(asdict(preferences), indent=1), encoding="utf-8")
    _ = scratch.replace(data / FILE)
