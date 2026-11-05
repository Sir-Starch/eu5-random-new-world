"""Which mods of the active playset can hide a generated world's files (read only).

EU5 reads the enabled mods in the playset's order and a later mod's file replaces an earlier
mod's file of the same path. A world writes its own ``in_game/map_data/location_templates.txt``;
if the game reads another mod's file there, or the files of a second world, no template reaches
the generated locations: every one of them keeps the first good (Clay) and the climate,
vegetation, topography and resource map modes stay empty (Workshop report W1). The check reads
``playsets.json`` and the mod folders and changes nothing.

It finds whole-file replacements by path. A later mod that defines the same keys in a file of
another name is not found.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

from rnw.app import install, session

if TYPE_CHECKING:
    from rnw.app.discovery import GameInstall

WORLD_PREFIX: Final[str] = "rnw_exp_world_"
WORKSHOP_APP: Final[str] = "3450310"
SAMPLE: Final[int] = 3


@dataclass(frozen=True, slots=True)
class Replacement:
    """A mod after the world that holds files at the same paths as the world's."""

    folder: str
    title: str
    files: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Check:
    """What stands between a ticked world and the game reading all of its files."""

    other_worlds: tuple[str, ...] = ()
    replacements: tuple[Replacement, ...] = ()
    unread: tuple[str, ...] = ()

    @property
    def clear(self) -> bool:
        """Whether nothing found can hide the world's files."""
        return not self.other_worlds and not self.replacements


def workshop_root(game: GameInstall | None) -> Path | None:
    """The folder that holds the game's Workshop items, if the game's library is known."""
    if game is None or game.library is None:
        return None
    return game.library / "steamapps" / "workshop" / "content" / WORKSHOP_APP


def title(mod: Path) -> str:
    """A mod's name from its metadata, else its folder name."""
    try:
        row = cast(
            "dict[str, object]",
            json.loads((mod / install.METADATA).read_text(encoding="utf-8-sig")),
        )
    except (OSError, ValueError):
        return mod.name
    name = row.get("name")
    return name if isinstance(name, str) and name else mod.name


def world_files(mod: Path) -> dict[str, str]:
    """The files a world writes under its folders (not ``.metadata``): lower-case path → path.

    Paths are relative with ``/``. Lower case, because the game reads them on case-blind file
    systems.
    """
    found: dict[str, str] = {}
    for root, directories, names in os.walk(mod):
        directories[:] = [
            name for name in directories if not (Path(root) == mod and name.startswith("."))
        ]
        relative = Path(root).relative_to(mod)
        if relative == Path():
            continue
        for name in names:
            path = (relative / name).as_posix()
            found[path.lower()] = path
    return found


def _directory(path: str, profile: Path, workshop: Path | None) -> Path | None:
    """Where a mod of the playset lives on this machine; None when it cannot be found."""
    posix = path.replace("\\", "/").rstrip("/")
    name = posix.rsplit("/", 1)[-1]
    candidates = [Path(posix)] if Path(posix).is_absolute() else []
    candidates.append(profile / install.MODS / name)
    if workshop is not None:
        candidates.append(workshop / name)
    return next((item for item in candidates if item.is_dir()), None)


def _replaced(mod: Path, files: dict[str, str]) -> tuple[str, ...]:
    """The world's files that ``mod`` holds at the same path, found by walking only the
    folders the world has files in."""
    parents: set[str] = set()
    for path in files:
        parent = path.rpartition("/")[0]
        while parent and parent not in parents:
            parents.add(parent)
            parent = parent.rpartition("/")[0]
    found: list[str] = []
    pending: list[tuple[Path, str]] = [(mod, "")]
    while pending:
        folder, prefix = pending.pop()
        try:
            entries = list(os.scandir(folder))
        except OSError:
            continue
        for entry in entries:
            key = f"{prefix}{entry.name.lower()}"
            if entry.is_dir(follow_symlinks=False):
                if key in parents:
                    pending.append((Path(entry.path), f"{key}/"))
            elif key in files:
                found.append(files[key])
    return tuple(sorted(found))


def check(profile: Path, world: str, *, workshop: Path | None = None) -> Check | None:
    """The check of the world in ``mod/<world>``; None when the playset is unreadable, the
    world is not ticked in it or its folder is not in the profile."""
    paths = session.enabled_paths(profile)
    mod = profile / install.MODS / world
    if paths is None or not install.is_rnw_mod(mod):
        return None
    folders = [session.folder_of(path) for path in paths]
    if world not in folders:
        return None
    position = folders.index(world)
    others = tuple(
        title(profile / install.MODS / folder)
        for folder in dict.fromkeys(folders)
        if folder != world
        and folder.startswith(WORLD_PREFIX)
        and install.is_rnw_mod(profile / install.MODS / folder)
    )
    files = world_files(mod)
    replacements: list[Replacement] = []
    unread: list[str] = []
    for path, folder in zip(paths[position + 1 :], folders[position + 1 :], strict=True):
        if folder.startswith(WORLD_PREFIX) and install.is_rnw_mod(profile / install.MODS / folder):
            continue
        directory = _directory(path, profile, workshop)
        if directory is None:
            unread.append(folder)
            continue
        replaced = _replaced(directory, files)
        if replaced:
            replacements.append(Replacement(folder, title(directory), replaced))
    return Check(others, tuple(replacements), tuple(unread))
