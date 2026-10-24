"""Finding the EU5 installation and the player's profile (read-only).

The game is a Steam game (app 3450310). Steam keeps a list of library folders, and the
app manifest of the game in one of them names the install folder and the build. The
profile holds ``mod/``, ``logs/`` and the settings: ``Documents/Paradox Interactive/
Europa Universalis V`` on Windows (the Documents folder may have been moved, to OneDrive
for one), ``~/.local/share/Paradox Interactive/...`` for a native Linux build, and the same
path inside the game's Proton prefix when it runs through Proton.

Everything the search reads about the machine goes through ``Environment``, so tests (and
a player whose Steam sits somewhere unusual) can supply their own.
"""

from __future__ import annotations

import contextlib
import ctypes
import os
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

from rnw.app.vdf import Section, VdfError, parse

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

APP_ID: Final[str] = "3450310"
GAME_FOLDER: Final[str] = "Europa Universalis V"
PROFILE_PARTS: Final[tuple[str, str]] = ("Paradox Interactive", GAME_FOLDER)
MAP_MARKER: Final[tuple[str, ...]] = ("game", "in_game", "map_data")
GAME_DIR_VARIABLE: Final[str] = "EU5_GAME_DIR"
USER_DIR_VARIABLE: Final[str] = "EU5_USER_DIR"
LINUX_STEAM_ROOTS: Final[tuple[str, ...]] = (
    ".local/share/Steam",
    ".steam/steam",
    ".steam/root",
    ".var/app/com.valvesoftware.Steam/.local/share/Steam",
    "snap/steam/common/.local/share/Steam",
)
WINDOWS_STEAM_ROOTS: Final[tuple[str, ...]] = (
    r"C:\Program Files (x86)\Steam",
    r"C:\Program Files\Steam",
)
PROTON_DOCUMENTS: Final[tuple[str, ...]] = ("pfx", "drive_c", "users", "steamuser", "Documents")


@dataclass(frozen=True, slots=True)
class GameInstall:
    """An EU5 installation: its folder, the Steam library that holds it and its build."""

    directory: Path
    library: Path | None
    build_id: str


@dataclass(frozen=True, slots=True)
class Profile:
    """A player profile: the folder with ``mod/`` and where it was found."""

    directory: Path
    kind: str
    has_mods: bool


@dataclass(frozen=True, slots=True)
class Environment:
    """What the search may know of the machine; the defaults read the real one."""

    system: str = field(default_factory=lambda: sys.platform)
    home: Path = field(default_factory=Path.home)
    variables: Mapping[str, str] = field(default_factory=lambda: dict(os.environ))
    steam_registry: Callable[[], list[Path]] = field(default_factory=lambda: _registry_roots)
    documents: Callable[[], Path | None] = field(default_factory=lambda: _known_documents)

    @property
    def windows(self) -> bool:
        """Whether this is Windows."""
        return self.system == "win32"


def _registry_roots() -> list[Path]:
    """Steam's folder from the Windows registry (nothing elsewhere)."""
    if sys.platform != "win32":
        return []
    import winreg  # noqa: PLC0415 - exists on Windows only

    found: list[Path] = []
    for hive, key, name in (
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
    ):
        with contextlib.suppress(OSError), winreg.OpenKey(hive, key) as handle:
            value = cast("object", winreg.QueryValueEx(handle, name)[0])
            found.append(Path(str(value)))
    return found


class _Guid(ctypes.Structure):
    """``GUID`` of the shell's known-folder calls."""

    _fields_: tuple[tuple[str, type], ...] = (  # pyright: ignore[reportIncompatibleVariableOverride]
        ("data1", ctypes.c_uint32),
        ("data2", ctypes.c_uint16),
        ("data3", ctypes.c_uint16),
        ("data4", ctypes.c_ubyte * 8),
    )


FOLDERID_DOCUMENTS: Final[uuid.UUID] = uuid.UUID("FDD39AD0-238F-46AF-ADB4-6C85480369C7")


def _known_documents() -> Path | None:
    """The Documents folder as Windows has it (moved to OneDrive, say), else None."""
    if sys.platform != "win32":
        return None
    guid = _Guid.from_buffer_copy(FOLDERID_DOCUMENTS.bytes_le)
    path = ctypes.c_wchar_p()
    shell, ole = ctypes.windll.shell32, ctypes.windll.ole32
    result = int(shell.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(path)))  # pyright: ignore[reportAny]
    try:
        return Path(path.value) if result == 0 and path.value else None
    finally:
        _ = ole.CoTaskMemFree(path)  # pyright: ignore[reportAny]


def steam_roots(environment: Environment) -> list[Path]:
    """Steam folders that exist, in the order they are tried."""
    candidates: list[Path] = []
    if environment.windows:
        candidates += environment.steam_registry()
        candidates += [Path(root) for root in WINDOWS_STEAM_ROOTS]
    else:
        candidates += [environment.home / relative for relative in LINUX_STEAM_ROOTS]
    seen: set[Path] = set()
    roots: list[Path] = []
    for candidate in candidates:
        with contextlib.suppress(OSError):
            resolved = candidate.resolve()
            if resolved.is_dir() and resolved not in seen:
                seen.add(resolved)
                roots.append(resolved)
    return roots


def libraries(root: Path) -> list[Path]:
    """The Steam root and every library folder it lists, those that exist."""
    found = [root]
    listing = root / "steamapps" / "libraryfolders.vdf"
    with contextlib.suppress(OSError, VdfError):
        tree = parse(listing.read_text(encoding="utf-8", errors="replace"))
        folders = tree.get("libraryfolders", {})
        if isinstance(folders, dict):
            for entry in folders.values():
                path = entry.get("path") if isinstance(entry, dict) else None
                if isinstance(path, str) and Path(path).is_dir():
                    found.append(Path(path))
    unique: list[Path] = []
    for library in found:
        if library not in unique:
            unique.append(library)
    return unique


def _manifest(library: Path) -> Section | None:
    with contextlib.suppress(OSError, VdfError):
        text = (library / "steamapps" / f"appmanifest_{APP_ID}.acf").read_text(
            encoding="utf-8", errors="replace"
        )
        state = parse(text).get("appstate")
        return state if isinstance(state, dict) else None
    return None


# Steam's names of the game's languages where they differ from the game's folders (C269).
STEAM_LANGUAGES: Final[dict[str, str]] = {
    "brazilian": "braz_por",
    "schinese": "simp_chinese",
    "koreana": "korean",
    "latam": "spanish",
}


def game_language(game: GameInstall) -> str | None:
    """The language Steam runs the game in, as the game's folder names it (C269).

    Steam keeps it in the game's app manifest, ``UserConfig`` then ``MountedConfig``. None when
    the game is not in a Steam library or the manifest says nothing.
    """
    library = game.library
    if library is None and game.directory.parent.parent.name == "steamapps":
        library = game.directory.parent.parent.parent
    state = _manifest(library) if library is not None else None
    for section in ("userconfig", "mountedconfig"):
        config = state.get(section) if state is not None else None
        language = config.get("language") if isinstance(config, dict) else None
        if isinstance(language, str) and language:
            return STEAM_LANGUAGES.get(language, language)
    return None


def is_game(directory: Path) -> bool:
    """Whether ``directory`` is an EU5 installation (it holds the map data)."""
    return directory.joinpath(*MAP_MARKER).is_dir()


def game_beside(start: Path) -> GameInstall | None:
    """The game whose Steam library holds ``start``, for a program started from a Workshop item.

    A Workshop item lives in ``<library>/steamapps/workshop/content/3450310/<item>/``, and the
    game in ``<library>/steamapps/common/``; walking up from ``start`` finds the library
    without Steam's registry or library list, which a Windows program inside a Proton prefix
    cannot see.
    """
    for parent in (start.resolve(), *start.resolve().parents):
        if parent.name == "steamapps":
            library = parent.parent
            state = _manifest(library)
            folder = state.get("installdir") if state is not None else None
            directory = parent / "common" / (folder if isinstance(folder, str) else GAME_FOLDER)
            build = state.get("buildid") if state is not None else None
            if is_game(directory):
                return GameInstall(directory, library, build if isinstance(build, str) else "")
    return None


def find_games(
    environment: Environment | None = None, start: Path | None = None
) -> list[GameInstall]:
    """EU5 installations found: beside ``start``, ``EU5_GAME_DIR``, then every Steam library."""
    environment = environment or Environment()
    found: list[GameInstall] = []
    nearby = game_beside(start) if start is not None else None
    if nearby is not None:
        found.append(nearby)
    explicit = environment.variables.get(GAME_DIR_VARIABLE)
    if explicit and is_game(Path(explicit)):
        found.append(GameInstall(Path(explicit), None, ""))
    for root in steam_roots(environment):
        for library in libraries(root):
            state = _manifest(library)
            if state is None:
                continue
            folder = state.get("installdir")
            directory = (
                library
                / "steamapps"
                / "common"
                / (folder if isinstance(folder, str) else GAME_FOLDER)
            )
            build = state.get("buildid")
            install = GameInstall(directory, library, build if isinstance(build, str) else "")
            if is_game(directory) and all(item.directory != directory for item in found):
                found.append(install)
    return found


def profile_candidates(
    environment: Environment, games: list[GameInstall]
) -> list[tuple[Path, str]]:
    """Places a profile may be, in the order they are tried, with the kind of each."""
    explicit = environment.variables.get(USER_DIR_VARIABLE)
    places: list[tuple[Path, str]] = []
    if explicit:
        places.append((Path(explicit), "chosen"))
    if environment.windows:
        documents = environment.documents() or environment.home / "Documents"
        places.append((documents.joinpath(*PROFILE_PARTS), "windows"))
    else:
        data = environment.variables.get("XDG_DATA_HOME")
        base = Path(data) if data else environment.home / ".local" / "share"
        places.append((base.joinpath(PROFILE_PARTS[0], PROFILE_PARTS[1]), "linux"))
        for game in games:
            if game.library is not None:
                prefix = game.library / "steamapps" / "compatdata" / APP_ID
                places.append((prefix.joinpath(*PROTON_DOCUMENTS, *PROFILE_PARTS), "proton"))
    return places


def find_profiles(
    environment: Environment | None = None, games: list[GameInstall] | None = None
) -> list[Profile]:
    """Profiles that exist; a profile the game has never run in does not exist yet."""
    environment = environment or Environment()
    games = find_games(environment) if games is None else games
    found: list[Profile] = []
    for directory, kind in profile_candidates(environment, games):
        if directory.is_dir() and all(item.directory != directory for item in found):
            found.append(Profile(directory, kind, (directory / "mod").is_dir()))
    return found
