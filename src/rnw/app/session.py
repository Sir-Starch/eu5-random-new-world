"""What the game has done since it was started, read from its own files (read only).

EU5 rewrites ``logs/debug.log`` at every launch and keeps the playsets in ``playsets.json``.
A different world can be started without restarting EU5 only while no game state has been
built in that process: generate, switch the playset to reload the mods, start a new game
works on a fresh launch, while a new game after a campaign in the same session crashes
(experiment 021, C113-C115). Applying the same playset again reloads nothing; switching to
another playset and back, or ticking a mod, does. The generator reads both files so that it
can tell the player the one thing to do next.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import TYPE_CHECKING, Final, cast

if TYPE_CHECKING:
    from pathlib import Path

LOG: Final[str] = "logs/debug.log"
PLAYSETS: Final[str] = "playsets.json"
LAUNCH: Final[str] = "Running Transition Empty->SplashScreen"
EXIT: Final[str] = "Running Transition SplashScreen->Empty"
GAME_STATE: Final[str] = "Started ClearAndRecalculateCachedData"


class GameState(Enum):
    """Where the game's current or last session stands."""

    UNKNOWN = "unknown"
    CLOSED = "closed"
    FRESH = "fresh"
    PLAYED = "played"


def game_state(profile: Path) -> GameState:
    """Closed, running without a game built since launch, or running after one; or unknown.

    A session that crashed leaves no exit line and reads as running.
    """
    try:
        text = (profile / LOG).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return GameState.UNKNOWN
    start = text.rfind(LAUNCH)
    if start < 0:
        return GameState.UNKNOWN
    session = text[start:]
    if EXIT in session:
        return GameState.CLOSED
    return GameState.PLAYED if GAME_STATE in session else GameState.FRESH


def _field(value: object, key: str) -> object:
    """``value[key]`` when ``value`` is a JSON object, else None."""
    return cast("dict[str, object]", value).get(key) if isinstance(value, dict) else None


def _items(value: object) -> list[object]:
    """The elements of a JSON array, or none."""
    return cast("list[object]", value) if isinstance(value, list) else []


def world_enabled(profile: Path, folder: str) -> bool | None:
    """Whether the active playset enables the mod in ``mod/<folder>``; None when unknown."""
    try:
        data = cast("object", json.loads((profile / PLAYSETS).read_text(encoding="utf-8-sig")))
    except (OSError, ValueError):
        return None
    active = [item for item in _items(_field(data, "playsets")) if _field(item, "isActive") is True]
    if len(active) != 1:
        return None
    for mod in _items(_field(active[0], "orderedListMods")):
        path = _field(mod, "path")
        if isinstance(path, str) and path.replace("\\", "/").rstrip("/").endswith(f"/{folder}"):
            return _field(mod, "isEnabled") is True
    return False
