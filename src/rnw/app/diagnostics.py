"""A file a player can attach to a bug report: the generator's logs and what it knows, redacted.

``write`` packs, into one ZIP, the generator's own log (``rnw.app.logs``), the last error with its
traceback, the Windows launcher's log, the tail of the game's logs, and a report of the machine,
the program, the game found, the worlds of the library and what the profile holds of this project.
It holds no game file and no world file; nothing is sent anywhere (the program has no network);
the player reads the list in ``README.txt`` and decides whom to give it to.

Redaction runs over every text before it is written: the home folder, the user's name, Steam
account numbers and e-mail addresses become placeholders, so a log from a player's machine does
not name the player.
"""

from __future__ import annotations

import contextlib
import getpass
import os
import platform
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from rnw import __version__, epoch, parallel
from rnw.app import install, library, logs, session
from rnw.record import verdict

if TYPE_CHECKING:
    from rnw.app.discovery import GameInstall, Profile
    from rnw.app.library import World

README: Final[str] = "README.txt"
REPORT: Final[str] = "report.txt"
LAST_ERROR: Final[str] = "last-error.log"
LAUNCHER_LOG: Final[str] = "launcher.log"
GAME_LOGS: Final[tuple[str, ...]] = ("error.log", "debug.log", "game.log")
TAIL_LINES: Final[int] = 4000
READ_LIMIT: Final[int] = 4 * 1024 * 1024
STEAM_ID: Final[re.Pattern[str]] = re.compile(r"\b7656119\d{10}\b")
USERDATA: Final[re.Pattern[str]] = re.compile(r"(?i)(userdata[\\/])\d+")
EMAIL: Final[re.Pattern[str]] = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
HOME_FOLDER: Final[re.Pattern[str]] = re.compile(
    r"(?i)(/home/|/users/|[a-z]:\\users\\)[^/\\\s\"']+"
)
KEPT_USERS: Final[frozenset[str]] = frozenset({"steamuser", "public", "default", "shared"})
CONTENTS: Final[str] = """\
This file was made by Random New World Generator so that a problem can be looked into.
Nothing in it was sent anywhere: the program has no network. Read it, and give it only to whom
you want to.

report.txt        the program, the machine, the game found, your worlds, the mods of this project
generator.log*    what the generator did, with the time of each stage and every error
last-error.log    the last error with its traceback, if there was one
launcher.log      the Windows launcher's output, if there is one
game-logs/        the last {lines} lines of the game's own logs (error, debug, game), if found

It holds no game file and no world file. Your home folder, your user name, Steam account numbers
and e-mail addresses are replaced by placeholders (<home>, <user>, <steamid>, <email>) in every
text; look through it if you want to be sure.
"""


@dataclass(frozen=True, slots=True)
class Snapshot:
    """What the window knows when a report is asked for."""

    data: Path
    games: tuple[GameInstall, ...] = ()
    game: GameInstall | None = None
    profiles: tuple[Profile, ...] = ()
    profile: Profile | None = None
    worlds: tuple[World, ...] = ()
    strays: tuple[Path, ...] = ()
    show_new_world: bool = False
    program_folder: Path | None = None


class Redactor:
    """Replaces what names the player in a text."""

    def __init__(self, home: Path | None = None, user: str | None = None) -> None:
        self._home: str = str(Path.home() if home is None else home)
        name = user if user is not None else _user()
        self._user: re.Pattern[str] | None = (
            re.compile(rf"(?i)\b{re.escape(name)}\b") if len(name) >= 3 else None  # noqa: PLR2004
        )

    def __call__(self, text: str) -> str:
        """``text`` with the home folder, the user's name, Steam ids and addresses replaced."""
        for variant in {self._home, self._home.replace("\\", "/"), self._home.replace("/", "\\")}:
            if len(variant) > 1:
                text = text.replace(variant, "<home>")
        text = EMAIL.sub("<email>", text)
        text = HOME_FOLDER.sub(_home_placeholder, text)
        if self._user is not None:
            text = self._user.sub("<user>", text)
        text = USERDATA.sub(r"\1<steamid>", text)
        return STEAM_ID.sub("<steamid>", text)


def _user() -> str:
    with contextlib.suppress(OSError, KeyError, ImportError):
        return getpass.getuser()
    return os.environ.get("USERNAME", "")


def _home_placeholder(match: re.Match[str]) -> str:
    """``/home/<name>`` becomes ``/home/<user>``, but the generic Wine user is kept."""
    folder = match.group(0)
    prefix = match.group(1)
    name = folder.removeprefix(prefix)
    return folder if name.lower() in KEPT_USERS else f"{prefix}<user>"


def tail(path: Path, lines: int = TAIL_LINES) -> str | None:
    """The last ``lines`` lines of a text file, or None if it cannot be read."""
    try:
        with path.open("rb") as handle:
            _ = handle.seek(0, os.SEEK_END)
            size = handle.tell()
            _ = handle.seek(max(0, size - READ_LIMIT))
            raw = handle.read()
    except OSError:
        return None
    return "\n".join(raw.decode("utf-8", errors="replace").splitlines()[-lines:]) + "\n"


def _memory() -> str:
    free = parallel.available_memory()
    return "unknown" if free is None else f"{free / parallel.GIB:.1f} GiB free"


def _qt() -> str:
    with contextlib.suppress(ImportError):
        import PySide6  # noqa: PLC0415 - optional

        return f"PySide6 {PySide6.__version__}"
    return "no PySide6"


def _worlds_text(snapshot: Snapshot) -> list[str]:
    lines: list[str] = []
    profile = snapshot.profile.directory if snapshot.profile is not None else None
    for world in snapshot.worlds:
        place = library.placement(snapshot.data, profile, world)
        record = world.record
        if record is None:
            made = "no record"
        else:
            state = verdict(record).value
            made = (
                f"epoch {record.algorithm}, release {record.release}, {state}, "
                f"inputs {record.game.inputs_count} files, output {record.output_count} files"
            )
        head = f"  {world.id}  {world.preset}  seed {world.seed}  generator {world.generator}"
        lines.append(f"{head}  build {world.game_build}  {place.value}  [{made}]")
        lines.append(f"    code {world.code}")
    return lines or ["  none"]


def _mods_text(snapshot: Snapshot) -> list[str]:
    if snapshot.profile is None:
        return ["  no profile"]
    directory = snapshot.profile.directory
    mods = [item.name for item in install.installed_mods(directory)]
    enabled = session.enabled_mods(directory)
    state = session.game_state(directory)
    return [
        f"  game session: {state.value}",
        f"  mods of this project in the profile: {', '.join(mods) or 'none'}",
        "  mods ticked in the active playset: "
        + ("unknown" if enabled is None else ", ".join(sorted(enabled)) or "none"),
    ]


def report_text(snapshot: Snapshot) -> str:
    """The report: the program, the machine, the game, the library, the profile."""
    game, profile = snapshot.game, snapshot.profile
    found = ", ".join(str(item.directory) for item in snapshot.games) or "none"
    profiles = ", ".join(f"{item.directory} ({item.kind})" for item in snapshot.profiles)
    log_file = f"none, {logs.status()}" if logs.status() else logs.FILE
    lines = [
        f"Random New World Generator {__version__} (algorithm epoch {epoch.CURRENT})",
        f"Python {platform.python_version()}, {platform.platform()}",
        f"{_qt()}; {parallel.cores()} usable cores; {_memory()}",
        f"packaged: {bool(getattr(sys, 'frozen', False))}",
        f"program folder: {snapshot.program_folder}",
        f"data folder: {snapshot.data}",
        f"log file: {log_file}",
        f"show the New World before it is played: {snapshot.show_new_world}",
        "",
        "Game",
        f"  found: {found}",
        f"  used: {game.directory if game else 'none'}",
        f"  Steam build: {game.build_id if game else '-'}",
        f"  profiles: {profiles or 'none'}",
        f"  profile used: {profile.directory if profile else 'none'}",
        "",
        "Profile",
        *_mods_text(snapshot),
        f"  older worlds in the game without a record: {len(snapshot.strays)}",
        "",
        "Worlds",
        *_worlds_text(snapshot),
        "",
    ]
    return "\n".join(lines)


def _game_logs(profile: Profile | None) -> dict[str, str]:
    found: dict[str, str] = {}
    if profile is None:
        return found
    for name in GAME_LOGS:
        text = tail(profile.directory / "logs" / name)
        if text is not None:
            found[f"game-logs/{name}"] = text
    crashes = profile.directory / "crashes"
    if crashes.is_dir():
        names = sorted(item.name for item in crashes.iterdir())[-20:]
        found["game-logs/crash-folders.txt"] = "\n".join(names) + "\n"
    return found


def collect(snapshot: Snapshot) -> dict[str, str]:
    """Every text of the file, by its name inside it, before redaction."""
    texts = {README: CONTENTS.format(lines=TAIL_LINES), REPORT: report_text(snapshot)}
    for name in (
        logs.FILE,
        *(f"{logs.FILE}.{number}" for number in range(1, logs.BACKUPS + 1)),
        LAST_ERROR,
        LAUNCHER_LOG,
    ):
        content = tail(snapshot.data / name)
        if content is not None:
            texts[name] = content
    texts.update(_game_logs(snapshot.profile))
    return texts


def write(output: Path, snapshot: Snapshot, redact: Redactor | None = None) -> Path:
    """Make the diagnostics file at ``output`` (replaced); returns it."""
    redactor = redact if redact is not None else Redactor()
    output.parent.mkdir(parents=True, exist_ok=True)
    scratch = output.with_name(f".{output.name}.new")
    with zipfile.ZipFile(scratch, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in collect(snapshot).items():
            archive.writestr(name, redactor(content))
    _ = scratch.replace(output)
    logs.get().info("diagnostics written to %s", output.name)
    return output


def default_name(stamp: str) -> str:
    """The suggested file name, with a ``stamp`` such as ``20261022-1530``."""
    return f"rnw-diagnostics-{stamp}.zip"
