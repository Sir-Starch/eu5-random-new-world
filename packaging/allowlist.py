"""What a public release may hold, and the check that it holds nothing of the game (ADR 0010, H).

A release is built from our sources and the wheels we depend on. It must never carry a file of
EU5: not a folder of its installation, not a shader, not a raster or texture of its map, not a
world the generator made on a player's machine (which is derived from the game). The generator
reads the game at the player's side and writes there; nothing flows back into what is published.

``problems`` takes the paths of a release (or of the repository) and names every one that breaks
the rule; ``problems_in_folder`` walks a built folder. The release builders call it before they
finish, and the test suite calls it on the repository's own files. A run with a folder as its
argument prints the problems and exits with 1 when there are any.
"""

from __future__ import annotations

import sys
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterable

# Folders of the game's installation, and of what the generator writes on a player's machine.
GAME_FOLDERS: Final[frozenset[str]] = frozenset(
    {
        "game",
        "jomini",
        "clausewitz",
        "in_game",
        "main_menu",
        "loading_screen",
        "generated",
        "local_data",
        "third_party",
    }
)
# Kinds of file that are the game's (shaders and textures), whatever folder they sit in.
GAME_SUFFIXES: Final[frozenset[str]] = frozenset({".shader", ".fxh", ".dds", ".gui"})
# What a release carries from others: the interpreter and the wheels.
VENDORED: Final[tuple[str, ...]] = ("generator/python/", "generator/site/")
# Files of the repository that name these folders in their text, not the game's own.
REPOSITORY_NOTES: Final[tuple[str, ...]] = (
    "src/rnw/",
    "tests/",
    "docs/",
    "experiments/",
    "packaging/",
    "native/",
    "AGENTS.md",
    "README.md",
    ".github/",
)


def problems(paths: Iterable[str], ignore: tuple[str, ...] = ()) -> list[str]:
    """The paths among ``paths`` that are a file of the game or of a generated world, each with
    why. ``ignore`` lists prefixes of paths that are ours although they mention such names."""
    found: list[str] = []
    for path in paths:
        if any(path.startswith(prefix) for prefix in ignore) and not _is_game_kind(path):
            continue
        reason = _reason(path)
        if reason is not None:
            found.append(f"{path}: {reason}")
    return found


def _is_game_kind(path: str) -> bool:
    return PurePosixPath(path).suffix.lower() in GAME_SUFFIXES


def _reason(path: str) -> str | None:
    parts = PurePosixPath(path).parts
    folders = [part for part in parts[:-1] if part in GAME_FOLDERS]
    if folders:
        return f"inside a folder of the game or of generated worlds ({folders[0]})"
    if _is_game_kind(path):
        return f"a {PurePosixPath(path).suffix.lower()} file, a kind the game's data is made of"
    return None


def problems_in_folder(root: Path, vendored: tuple[str, ...] = VENDORED) -> list[str]:
    """``problems`` for every file under ``root``, by path relative to it.

    Third-party libraries (``vendored`` prefixes) are held only to the rule on kinds of file: a
    wheel may have a folder of any name, but not a shader or a texture of the game.
    """
    found: list[str] = []
    for item in sorted(root.rglob("*")):
        if not item.is_file():
            continue
        relative = item.relative_to(root).as_posix()
        if any(relative.startswith(prefix) for prefix in vendored):
            reason = f"a {item.suffix.lower()} file, a kind the game's data is made of"
            if _is_game_kind(relative):
                found.append(f"{relative}: {reason}")
        else:
            found.extend(problems([relative]))
    return found


def main(arguments: list[str]) -> int:
    """Check each folder given; print what is wrong; exit 1 if anything is."""
    found: list[str] = []
    for argument in arguments:
        found.extend(problems_in_folder(Path(argument)))
    for line in found:
        print(line)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
