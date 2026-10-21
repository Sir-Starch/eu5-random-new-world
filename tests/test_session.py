"""Reading what the game did since launch, on synthetic logs and playsets."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from rnw.app import session
from rnw.app.service import Result
from rnw.app.session import GameState
from rnw.gui.controller import Controller
from rnw.gui.text import text

if TYPE_CHECKING:
    from pathlib import Path

LAUNCH = "[06:47:13][pdx_transition_task.cpp:138]: Running Transition Empty->SplashScreen\n"
LOBBY = "[06:47:17][pdx_transition_task.cpp:138]: Running Transition MainMenu->Game\n"
BUILT = "[06:51:46][gamestate.cpp:735]: Started ClearAndRecalculateCachedData\n"
EXIT = "[21:16:17][pdx_transition_task.cpp:138]: Running Transition SplashScreen->Empty\n"
FOLDER = "rnw_exp_new_world"


def _log(profile: Path, *lines: str) -> None:
    (profile / "logs").mkdir(parents=True, exist_ok=True)
    _ = (profile / session.LOG).write_text("".join(lines), encoding="utf-8")


def _playsets(profile: Path, *, enabled: bool | None) -> None:
    mods: list[dict[str, object]] = (
        [] if enabled is None else [{"path": f"C:/x/mod/{FOLDER}/", "isEnabled": enabled}]
    )
    payload: dict[str, object] = {
        "playsets": [
            {"name": "Default", "orderedListMods": []},
            {"name": "RNW", "isActive": True, "orderedListMods": mods},
        ]
    }
    _ = (profile / session.PLAYSETS).write_text(json.dumps(payload), encoding="utf-8-sig")


def test_the_session_is_read_from_the_last_launch_on(tmp_path: Path) -> None:
    """Only a built game counts as played; the country screen alone does not; exit closes."""
    assert session.game_state(tmp_path) is GameState.UNKNOWN
    _log(tmp_path, "no launch line\n")
    assert session.game_state(tmp_path) is GameState.UNKNOWN
    _log(tmp_path, LAUNCH, LOBBY)
    assert session.game_state(tmp_path) is GameState.FRESH
    _log(tmp_path, LAUNCH, LOBBY, BUILT)
    assert session.game_state(tmp_path) is GameState.PLAYED
    _log(tmp_path, LAUNCH, BUILT, EXIT)
    assert session.game_state(tmp_path) is GameState.CLOSED
    _log(tmp_path, LAUNCH, BUILT, EXIT, LAUNCH)
    assert session.game_state(tmp_path) is GameState.FRESH


def test_the_active_playset_says_whether_the_world_is_ticked(tmp_path: Path) -> None:
    """Enabled, present but off, absent, or no readable playsets."""
    assert session.world_enabled(tmp_path, FOLDER) is None
    _playsets(tmp_path, enabled=True)
    assert session.world_enabled(tmp_path, FOLDER) is True
    _playsets(tmp_path, enabled=False)
    assert session.world_enabled(tmp_path, FOLDER) is False
    _playsets(tmp_path, enabled=None)
    assert session.world_enabled(tmp_path, FOLDER) is False
    _ = (tmp_path / session.PLAYSETS).write_text("{broken", encoding="utf-8")
    assert session.world_enabled(tmp_path, FOLDER) is None


def test_the_window_says_restart_only_after_a_game_in_this_session(tmp_path: Path) -> None:
    """Fresh session: reload by switching playsets; played: restart; closed: start EU5."""
    profile = tmp_path / "profile"
    profile.mkdir()
    controller = Controller(data=tmp_path / "data")
    assert controller.choose_profile(profile) is None
    result = Result("RNW1-x", tmp_path / "bundle", profile / "mod" / FOLDER, 1.0, {})
    _playsets(profile, enabled=True)
    _log(profile, LAUNCH, LOBBY)
    assert controller.next_step(result) == text("next_fresh")
    _log(profile, LAUNCH, BUILT)
    assert controller.next_step(result) == text("next_played")
    _log(profile, LAUNCH, BUILT, EXIT)
    assert controller.next_step(result) == text("next_start")
    _playsets(profile, enabled=None)
    _log(profile, LAUNCH)
    assert controller.next_step(result) == text("next_fresh_tick")
    _log(profile, LAUNCH, BUILT)
    assert controller.next_step(result).startswith(text("next_tick"))
    uninstalled = Result("RNW1-x", tmp_path / "bundle", None, 1.0, {})
    assert controller.next_step(uninstalled) == ""
