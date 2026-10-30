"""Which window opens: the Tauri window first, the classic one when chosen or when it cannot."""

from __future__ import annotations

import os
import stat
import sys
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from rnw import cli
from rnw.app import preferences
from rnw.gui import start

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="fake windows are shell scripts")


def _window(folder: Path, body: str) -> Path:
    """A stand-in window program: a shell script that does ``body``."""
    program = folder / start.FOLDER / start.program_name()
    program.parent.mkdir(parents=True, exist_ok=True)
    _ = program.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    program.chmod(program.stat().st_mode | stat.S_IXUSR)
    return program


def test_the_window_is_found_beside_the_application_or_in_the_hub(tmp_path: Path) -> None:
    beside = _window(tmp_path / "app", "exit 0")
    assert start.find_window(tmp_path / "app", package=tmp_path / "x" / "y") == beside
    hub = tmp_path / "hub"
    inside = _window(hub / "generator", "exit 0")
    assert start.find_window(hub, package=tmp_path / "x" / "y") == inside
    assert start.find_window(tmp_path / "none", package=tmp_path / "x" / "y") is None
    assert start.packaged(hub)
    assert not start.packaged(tmp_path / "app")


def test_the_classic_window_is_chosen_by_flag_environment_or_setting(tmp_path: Path) -> None:
    program = tmp_path / "app"
    window = _window(program, "exit 0")
    data = tmp_path / "data"
    assert start.choose(["rnw"], program_folder=program, variables={}, data=data).program == window
    by_flag = start.choose(["rnw", start.CLASSIC], program_folder=program, variables={}, data=data)
    assert by_flag.program is None
    assert by_flag.reason
    by_variable = start.choose(
        ["rnw"], program_folder=program, variables={start.ENV_WINDOW: "Classic"}, data=data
    )
    assert by_variable.program is None
    preferences.save(data, preferences.Preferences(window=start.CLASSIC_WINDOW))
    by_setting = start.choose(["rnw"], program_folder=program, variables={}, data=data)
    assert by_setting.program is None
    assert "Settings" in by_setting.reason


def test_a_window_that_cannot_open_hands_over_to_the_classic_one(tmp_path: Path) -> None:
    closed = start.run_window(_window(tmp_path / "a", "exit 0"))
    assert closed == start.Outcome(0, opened=True)
    no_view = start.run_window(_window(tmp_path / "b", f"exit {start.NO_WINDOW}"))
    assert not no_view.opened
    assert "web view" in no_view.reason
    crashed = start.run_window(_window(tmp_path / "c", "exit 127"))
    assert not crashed.opened
    missing = start.run_window(tmp_path / "nowhere" / start.program_name())
    assert not missing.opened
    assert "could not start" in missing.reason


def test_a_window_that_fails_after_it_opened_stays_its_own(tmp_path: Path) -> None:
    times = iter((0.0, start.STARTUP + 1))
    late = start.run_window(_window(tmp_path, "exit 1"), clock=lambda: next(times))
    assert late == start.Outcome(1, opened=True)


def test_the_window_gets_the_arguments_and_the_environment(tmp_path: Path) -> None:
    record = tmp_path / "record.txt"
    window = _window(tmp_path / "app", f'echo "$@ $RNW_DATA" > "{record}"')
    outcome = start.run_window(window, ["--x"], variables={**os.environ, "RNW_DATA": "here"})
    assert outcome.opened
    assert record.read_text(encoding="utf-8").strip() == "--x here"


def test_the_window_self_test_runs_on_a_data_folder_of_its_own(tmp_path: Path) -> None:
    window = _window(tmp_path / "app", f'echo "$1 $RNW_DATA {start.SELF_TEST_LINE}"')
    code, output = start.self_test(window, tmp_path / "scratch")
    assert code == 0
    assert output == f"--self-test {tmp_path / 'scratch'} {start.SELF_TEST_LINE}"


def test_the_command_line_opens_the_classic_window_on_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import rnw.gui.__main__ as entry  # noqa: PLC0415 - the module the command imports

    seen: list[list[str]] = []

    def opened(argv: list[str]) -> int:
        seen.append(argv)
        return 0

    monkeypatch.setattr(entry, "main", opened)
    result = CliRunner().invoke(cli.app, ["gui", "--classic"])
    assert result.exit_code == 0
    assert seen == [["rnw-gui", "--classic"]]
