"""The generator's log and the file a player attaches to a bug report."""

from __future__ import annotations

import zipfile
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from rnw.app import diagnostics, discovery, library, logs
from rnw.app.diagnostics import Redactor, Snapshot
from rnw.app.discovery import GameInstall, Profile
from rnw.cli import app

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@pytest.fixture(autouse=True)
def _quiet_log() -> Iterator[None]:
    """Each test starts and ends with no log file open."""
    logs.stop()
    yield
    logs.stop()


def test_a_text_loses_what_names_the_player(tmp_path: Path) -> None:
    """The home folder, the user's name, Steam ids and addresses become placeholders."""
    home = tmp_path / "home" / "alice"
    redact = Redactor(home=home, user="alice")
    text = (
        f"opened {home}/.local/share/x and /home/bob/y and C:\\Users\\Carol\\Documents "
        "as alice (alice@example.com) steam 76561198012345678 in /userdata/12345678/config "
        "also C:\\users\\steamuser\\Documents"
    )
    done = redact(text)
    assert str(home) not in done
    assert "<home>/.local/share/x" in done
    assert "/home/<user>/y" in done
    assert "C:\\Users\\<user>\\Documents" in done
    assert "as <user> (<email>)" in done
    assert "<steamid>" in done
    assert "76561198012345678" not in done
    assert "/userdata/<steamid>/config" in done
    assert "C:\\users\\steamuser\\Documents" in done
    assert "alice" not in done


def test_a_short_user_name_is_not_hunted_through_the_text() -> None:
    """A two-letter name would blank half of every sentence; only the folder is replaced."""
    assert Redactor(home=None, user="al")("al and alone") == "al and alone"


def test_the_tail_of_a_file_is_its_last_lines_or_nothing(tmp_path: Path) -> None:
    """Lines count from the end; a missing file is None."""
    path = tmp_path / "x.log"
    _ = path.write_text("\n".join(str(number) for number in range(10)), encoding="utf-8")
    assert diagnostics.tail(path, 3) == "7\n8\n9\n"
    assert diagnostics.tail(tmp_path / "none.log") is None


def test_the_log_is_written_once_per_folder_and_never_stops_the_program(tmp_path: Path) -> None:
    """Starting twice writes one header; another folder moves the log; a bad folder is reported."""
    logs.start(tmp_path / "one")
    logs.start(tmp_path / "one")
    logs.get().info("hello")
    text = (tmp_path / "one" / logs.FILE).read_text(encoding="utf-8")
    assert text.count("start generator") == 1
    assert "hello" in text
    logs.start(tmp_path / "two")
    logs.get().info("moved")
    assert "moved" in (tmp_path / "two" / logs.FILE).read_text(encoding="utf-8")
    assert "moved" not in (tmp_path / "one" / logs.FILE).read_text(encoding="utf-8")
    blocked = tmp_path / "file"
    _ = blocked.write_text("not a folder", encoding="utf-8")
    logs.start(blocked)
    assert logs.status()
    logs.get().info("goes nowhere")


def _snapshot(tmp_path: Path) -> Snapshot:
    data = tmp_path / "data"
    world = library.World(
        id="abcdefghij",
        code="RNW1-TEST-1",
        preset="continents",
        seed=1,
        generator="0.9.22",
        game_build="26043558",
        created=1,
        seconds=1.0,
    )
    library.save(data, world)
    profile = tmp_path / "profile"
    for name, text in (("error.log", "e1\ne2\n"), ("debug.log", "d1\n"), ("game.log", "g\n")):
        (profile / "logs").mkdir(parents=True, exist_ok=True)
        _ = (profile / "logs" / name).write_text(text, encoding="utf-8")
    (profile / "crashes" / "crash_2026").mkdir(parents=True)
    (profile / "mod").mkdir(exist_ok=True)
    game = GameInstall(tmp_path / "game", None, "26043558")
    return Snapshot(
        data=data,
        games=(game,),
        game=game,
        profiles=(Profile(profile, "linux", has_mods=True),),
        profile=Profile(profile, "linux", has_mods=True),
        worlds=(world,),
        show_new_world=False,
    )


def test_the_file_holds_the_logs_and_a_report_and_nothing_else(tmp_path: Path) -> None:
    """The zip has the readme, report, own logs, game log tails and crash names; names redacted."""
    snapshot = _snapshot(tmp_path)
    logs.start(snapshot.data)
    logs.get().error("failed in /home/zed/mods")
    _ = (snapshot.data / diagnostics.LAST_ERROR).write_text("Traceback zed@x.org\n", "utf-8")
    output = diagnostics.write(tmp_path / "out" / "d.zip", snapshot, Redactor(user="zed"))
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        contents = {name: archive.read(name).decode("utf-8") for name in names}
    assert names == {
        "README.txt",
        "report.txt",
        logs.FILE,
        diagnostics.LAST_ERROR,
        "game-logs/error.log",
        "game-logs/debug.log",
        "game-logs/game.log",
        "game-logs/crash-folders.txt",
    }
    assert "Random New World Generator" in contents["report.txt"]
    assert "build 26043558" in contents["report.txt"]
    assert "RNW1-TEST-1" in contents["report.txt"]
    assert "crash_2026" in contents["game-logs/crash-folders.txt"]
    assert contents["game-logs/error.log"] == "e1\ne2\n"
    assert "/home/<user>/mods" in contents[logs.FILE]
    assert "<email>" in contents[diagnostics.LAST_ERROR]
    assert "zed" not in "".join(contents.values())
    assert not list(output.parent.glob(".*.new"))


def test_a_file_without_a_game_or_logs_still_reports(tmp_path: Path) -> None:
    """With nothing found the report says so and the zip has just the readme and the report."""
    output = diagnostics.write(tmp_path / "d.zip", Snapshot(data=tmp_path / "data"))
    with zipfile.ZipFile(output) as archive:
        assert set(archive.namelist()) == {"README.txt", "report.txt"}
        assert "found: none" in archive.read("report.txt").decode("utf-8")


def _no_games(*_arguments: object, **_keywords: object) -> list[GameInstall]:
    return []


def _no_profiles(*_arguments: object, **_keywords: object) -> list[Profile]:
    return []


def test_the_command_writes_the_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """``rnw diagnostics-file`` finds nothing here and still writes a readable file."""
    monkeypatch.setattr(discovery, "find_games", _no_games)
    monkeypatch.setattr(discovery, "find_profiles", _no_profiles)
    output = tmp_path / "out.zip"
    result = CliRunner().invoke(
        app, ["diagnostics-file", str(output), "--data-dir", str(tmp_path / "data")]
    )
    assert result.exit_code == 0, result.output
    assert zipfile.is_zipfile(output)
