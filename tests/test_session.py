"""Reading what the game did since launch, on synthetic logs and playsets."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from rnw.app import session
from rnw.app.library import World
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


def _installed(profile: Path, folder: str, name: str) -> None:
    mod = profile / "mod" / folder
    (mod / ".metadata").mkdir(parents=True)
    _ = (mod / ".metadata/metadata.json").write_text(f'{{"name": "{name}"}}', encoding="utf-8-sig")


def _active(profile: Path, *folders: str) -> None:
    mods: list[dict[str, object]] = [
        {"path": f"C:/x/mod/{folder}/", "isEnabled": True} for folder in folders
    ]
    payload: dict[str, object] = {"playsets": [{"isActive": True, "orderedListMods": mods}]}
    _ = (profile / session.PLAYSETS).write_text(json.dumps(payload), encoding="utf-8-sig")


def test_the_window_says_what_to_do_in_eu5_for_one_world_at_a_time(tmp_path: Path) -> None:
    """Fresh session: tick or switch playsets; after a game: restart; closed: start EU5.

    Only one world may be ticked, so another ticked world is to be unticked.
    """
    profile = tmp_path / "profile"
    profile.mkdir()
    controller = Controller(data=tmp_path / "data")
    assert controller.choose_profile(profile) is None
    world = World("abc", "RNW1-x", "continents", 1, "0.9.14", "26043558", 0, 1.0)
    other = World("def", "RNW1-y", "islands", 2, "0.9.14", "26043558", 0, 1.0)
    _installed(profile, world.folder, "Mine")
    _installed(profile, other.folder, "Other")
    controller.worlds = [world, other]
    assert controller.next_step(other) != ""
    _active(profile, world.folder)
    _log(profile, LAUNCH, LOBBY)
    assert controller.next_step(world) == text("next_fresh_switch")
    _active(profile, other.folder)
    assert controller.next_step(world) == text(
        "next_fresh", tick=text("tick_self_untick", name="Mine")
    )
    _active(profile, world.folder, other.folder)
    assert text("untick_others") in controller.next_step(world)
    _active(profile)
    _log(profile, LAUNCH, BUILT)
    played = controller.next_step(world)
    assert played.startswith(text("next_played", tick="").split(" Close")[0])
    assert text("tick_self", name="Mine") in played
    _log(profile, LAUNCH, BUILT, EXIT)
    assert controller.next_step(world).startswith("Start EU5.")
    (profile / session.PLAYSETS).unlink()
    assert text("tick_unknown", name="Mine") in controller.next_step(world)
    elsewhere = World("ghi", "RNW1-z", "islands", 3, "0.9.14", "26043558", 0, 1.0)
    assert controller.next_step(elsewhere) == ""
