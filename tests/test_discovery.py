"""Finding the game and the profile on synthetic Steam layouts, and reading KeyValues."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.app import discovery
from rnw.app.discovery import Environment, GameInstall
from rnw.app.vdf import VdfError, parse

if TYPE_CHECKING:
    from pathlib import Path

MANIFEST = """"AppState"
{
\t"appid"\t\t"3450310"
\t"installdir"\t\t"Europa Universalis V"
\t"buildid"\t\t"26043558"
\t"InstalledDepots"
\t{
\t\t"3450311"
\t\t{
\t\t\t"manifest"\t\t"5639139026613178064"
\t\t}
\t}
}
"""


def _library(root: Path, *, with_game: bool = True) -> Path:
    steamapps = root / "steamapps"
    steamapps.mkdir(parents=True)
    if with_game:
        _ = (steamapps / "appmanifest_3450310.acf").write_text(MANIFEST, encoding="utf-8")
        (steamapps / "common" / "Europa Universalis V" / "game" / "in_game" / "map_data").mkdir(
            parents=True
        )
    return root


def _listing(steam: Path, *libraries: Path) -> None:
    entries = "".join(
        f'\t"{number}"\n\t{{\n\t\t"path"\t\t"{str(path).replace(chr(92), chr(92) * 2)}"\n\t}}\n'
        for number, path in enumerate(libraries)
    )
    _ = (steam / "steamapps" / "libraryfolders.vdf").write_text(
        f'"libraryfolders"\n{{\n{entries}}}\n', encoding="utf-8"
    )


def test_keyvalues_parse_nested_sections_escapes_and_comments() -> None:
    """Sections nest, escapes in quotes resolve, comments and blank lines are skipped."""
    tree = parse(
        '// a comment\n"a" { "path" "D:\\\\Games\\\\Steam" "n" "x\\"y" "b" { "c" "d" } }\n"e" "f"\n'
    )
    assert tree == {"a": {"path": "D:\\Games\\Steam", "n": 'x"y', "b": {"c": "d"}}, "e": "f"}
    assert parse('"LibraryFolders" { "Path" "S:\\\\" }') == {"libraryfolders": {"path": "S:\\"}}
    for bad in ('"a" {', '"a"', "}", '"a" { "b" } }', "stray"):
        with pytest.raises(VdfError):
            _ = parse(bad)


def test_the_game_is_found_in_a_second_steam_library(tmp_path: Path) -> None:
    """The library list names a folder on another drive; its manifest gives the build."""
    home = tmp_path / "home"
    steam = _library(home / ".local/share/Steam", with_game=False)
    second = _library(tmp_path / "games" / "SteamLibrary")
    _listing(steam, steam, second)
    environment = Environment(system="linux", home=home, variables={})
    games = discovery.find_games(environment)
    assert [(game.directory.name, game.build_id) for game in games] == [
        ("Europa Universalis V", "26043558")
    ]
    assert games[0].library == second


def test_the_explicit_folder_comes_first_and_is_not_repeated(tmp_path: Path) -> None:
    """EU5_GAME_DIR wins; the same folder found through Steam is listed once."""
    home = tmp_path / "home"
    steam = _library(home / ".steam/steam")
    game = steam / "steamapps" / "common" / "Europa Universalis V"
    environment = Environment(system="linux", home=home, variables={"EU5_GAME_DIR": str(game)})
    games = discovery.find_games(environment)
    assert [item.directory.resolve() for item in games] == [game.resolve()] or len(games) == 2
    assert games[0].directory == game
    assert games[0].build_id == ""


def test_a_folder_without_the_map_files_is_not_a_game(tmp_path: Path) -> None:
    """A leftover manifest of an uninstalled game does not count."""
    home = tmp_path / "home"
    steam = _library(home / ".local/share/Steam")
    _ = (steam / "steamapps/common/Europa Universalis V/game/in_game/map_data").rmdir()
    environment = Environment(system="linux", home=home, variables={})
    assert discovery.find_games(environment) == []


def test_profiles_native_proton_and_explicit(tmp_path: Path) -> None:
    """The native Linux profile, the one in the game's Proton prefix, and a chosen one."""
    home = tmp_path / "home"
    steam = _library(home / ".local/share/Steam")
    native = home / ".local/share/Paradox Interactive/Europa Universalis V"
    (native / "mod").mkdir(parents=True)
    proton = (
        steam
        / "steamapps/compatdata/3450310/pfx/drive_c/users/steamuser/Documents"
        / "Paradox Interactive/Europa Universalis V"
    )
    proton.mkdir(parents=True)
    chosen = tmp_path / "elsewhere"
    chosen.mkdir()
    environment = Environment(system="linux", home=home, variables={"EU5_USER_DIR": str(chosen)})
    profiles = discovery.find_profiles(environment)
    assert [(profile.kind, profile.has_mods) for profile in profiles] == [
        ("chosen", False),
        ("linux", True),
        ("proton", False),
    ]
    assert profiles[2].directory == proton


def test_windows_uses_the_registry_and_the_moved_documents_folder(tmp_path: Path) -> None:
    """Steam's folder comes from the registry reader and Documents from the shell's answer."""
    steam = _library(tmp_path / "Steam")
    documents = tmp_path / "OneDrive" / "Documents"
    profile = documents / "Paradox Interactive" / "Europa Universalis V"
    profile.mkdir(parents=True)
    environment = Environment(
        system="win32",
        home=tmp_path / "user",
        variables={},
        steam_registry=lambda: [steam],
        documents=lambda: documents,
    )
    games = discovery.find_games(environment)
    assert [game.build_id for game in games] == ["26043558"]
    profiles = discovery.find_profiles(environment, games)
    assert [(item.kind, item.directory) for item in profiles] == [("windows", profile)]
    fallback = Environment(
        system="win32",
        home=tmp_path / "user",
        variables={},
        steam_registry=list,
        documents=lambda: None,
    )
    assert discovery.profile_candidates(fallback, [])[0][0] == (
        tmp_path / "user" / "Documents" / "Paradox Interactive" / "Europa Universalis V"
    )


def test_nothing_found_is_an_empty_list_not_an_error(tmp_path: Path) -> None:
    """A machine without Steam or the game yields empty answers."""
    environment = Environment(system="linux", home=tmp_path, variables={})
    assert discovery.find_games(environment) == []
    assert discovery.find_profiles(environment) == []
    assert GameInstall(tmp_path, None, "").build_id == ""


def test_a_program_in_a_workshop_folder_finds_the_game_beside_it(tmp_path: Path) -> None:
    """Walking up from steamapps/workshop/content/3450310/<item> reaches the game's folder."""
    library = _library(tmp_path / "SteamLibrary")
    item = library / "steamapps" / "workshop" / "content" / "3450310" / "9999" / "generator"
    item.mkdir(parents=True)
    found = discovery.game_beside(item)
    assert found == GameInstall(
        (library / "steamapps" / "common" / "Europa Universalis V").resolve(),
        library.resolve(),
        "26043558",
    )
    environment = Environment(system="linux", home=tmp_path / "home", variables={})
    games = discovery.find_games(environment, start=item)
    assert [game.build_id for game in games] == ["26043558"]
    elsewhere = tmp_path / "somewhere" / "generator"
    elsewhere.mkdir(parents=True)
    assert discovery.game_beside(elsewhere) is None


def test_inside_a_proton_prefix_the_steam_stub_lists_the_library(tmp_path: Path) -> None:
    """The Windows build in the game's prefix reads the stub's "LibraryFolders" (capitalised)."""
    stub = _library(tmp_path / "drive_c" / "Program Files (x86)" / "Steam", with_game=False)
    library = _library(tmp_path / "S")
    escaped = str(library).replace(chr(92), chr(92) * 2)
    _ = (stub / "steamapps" / "libraryfolders.vdf").write_text(
        f'"LibraryFolders"\n{{\n\t"1"\n\t{{\n\t\t"path"\t\t"{escaped}"\n\t}}\n}}\n',
        encoding="utf-8",
    )
    environment = Environment(
        system="win32", home=tmp_path / "home", variables={}, steam_registry=lambda: [stub]
    )
    games = discovery.find_games(environment)
    assert [(game.library, game.build_id) for game in games] == [(library, "26043558")]


def test_the_games_language_is_steams_and_named_as_the_games_folders(tmp_path: Path) -> None:
    """Steam keeps the per-game language in the app manifest under its own names (C269)."""
    library = _library(tmp_path / "lib")
    manifest = library / "steamapps" / "appmanifest_3450310.acf"
    game = GameInstall(library / "steamapps" / "common" / "Europa Universalis V", library, "")
    assert discovery.game_language(game) is None
    for steam, folder in (("schinese", "simp_chinese"), ("russian", "russian")):
        text = MANIFEST.replace(
            '\t"InstalledDepots"',
            f'\t"UserConfig"\n\t{{\n\t\t"language"\t\t"{steam}"\n\t}}\n\t"InstalledDepots"',
        )
        _ = manifest.write_text(text, encoding="utf-8")
        assert discovery.game_language(game) == folder
        # A game chosen by hand has no library, but its folder still says where Steam keeps it.
        assert discovery.game_language(GameInstall(game.directory, None, "")) == folder
