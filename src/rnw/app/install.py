"""Installing a generated mod into the player's profile, and removing it again.

Only folders named ``rnw_exp_*`` that carry mod metadata are ever replaced or removed, and
the installer's own work folder ``mod/.rnw-install``; no other mod, playset, save or setting
is read or written.

The game may be running and may hold files of the installed world open: under Windows rules
(Windows itself, and Wine under Proton) such a file cannot be deleted, and on Windows the
folder around it may not even be renamed (experiment 021). So a world is copied into
``.rnw-install/incoming`` first, the installed one is moved into ``.rnw-install/retired`` by
one rename on the same drive, and the copy is renamed into its place. Retired worlds are
deleted when the game has let go of them, by this install or a later one; a file still held
never fails an install. The work folder has no metadata of its own, so the game lists
nothing inside it as a mod.
"""

from __future__ import annotations

import contextlib
import shutil
import time
from typing import TYPE_CHECKING, Final

from rnw.artifacts import when_free

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

PREFIX: Final[str] = "rnw_exp_"
METADATA: Final[str] = ".metadata/metadata.json"
MODS: Final[str] = "mod"
WORK: Final[str] = ".rnw-install"
INCOMING: Final[str] = "incoming"
RETIRED: Final[str] = "retired"


class InstallError(ValueError):
    """The mod cannot be installed or removed without touching something that is not ours."""


class WorldInUseError(InstallError):
    """The system refuses to move the installed mod because the game holds its files."""


def is_rnw_mod(path: Path) -> bool:
    """Whether ``path`` is a generated mod folder of this project."""
    return path.is_dir() and path.name.startswith(PREFIX) and (path / METADATA).is_file()


def installed_mods(profile: Path) -> list[Path]:
    """The generated mods in the profile's ``mod`` folder, by name."""
    folder = profile / MODS
    if not folder.is_dir():
        return []
    return sorted(path for path in folder.iterdir() if is_rnw_mod(path))


def stage(prepared: Path, profile: Path, *, replace: bool = False, move: bool = False) -> Path:
    """Copy (or, with ``move``, move) the mod ``prepared`` into the work folder; returns it.

    The copy is complete when this returns; ``put_in_place`` swaps it in. Moving keeps a
    world on the disk once: a rename on the same drive, a copy and delete across drives.
    """
    if not is_rnw_mod(prepared):
        message = "The prepared directory must be a valid rnw_exp_* mod"
        raise InstallError(message)
    if not profile.is_dir():
        message = f"The profile folder does not exist: {profile}"
        raise InstallError(message)
    target = profile / MODS / prepared.name
    if target.exists() and not (replace and is_rnw_mod(target)):
        message = f"The destination exists and is not a replaceable rnw_exp_* mod: {target}"
        raise InstallError(message)
    incoming = profile / MODS / WORK / INCOMING / prepared.name
    incoming.parent.mkdir(parents=True, exist_ok=True)
    if incoming.exists():
        when_free(lambda: shutil.rmtree(incoming))
    _ = shutil.move(prepared, incoming) if move else shutil.copytree(prepared, incoming)
    return incoming


def put_in_place(incoming: Path) -> Path:
    """Swap a staged copy into ``mod/``; the mod it replaces is retired, not deleted.

    Raises ``WorldInUseError``, changing nothing, when the installed mod cannot be moved.
    """
    mods = incoming.parent.parent.parent
    target = mods / incoming.name
    retired = _retire(target) if target.exists() else None
    try:
        _ = when_free(lambda: incoming.rename(target))
    except OSError:
        if retired is not None:
            _ = retired.rename(target)
        raise
    _ = sweep(mods.parent)
    return target


def discard(incoming: Path) -> None:
    """Delete a staged copy that will not be installed."""
    shutil.rmtree(incoming, ignore_errors=True)
    _tidy(incoming.parent.parent)


def install(prepared: Path, profile: Path, *, replace: bool = False) -> Path:
    """Copy the generated mod ``prepared`` into ``profile/mod``; returns where it went."""
    incoming = stage(prepared, profile, replace=replace)
    try:
        return put_in_place(incoming)
    except (OSError, InstallError):
        discard(incoming)
        raise


def _retire(target: Path) -> Path:
    folder = target.parent / WORK / RETIRED
    folder.mkdir(parents=True, exist_ok=True)
    place = folder / f"{target.name}.{time.time_ns()}"
    try:
        _ = target.rename(place)
    except PermissionError as error:
        message = (
            f"The game is using {target.name}: untick it in the game's playset and apply "
            "the playset, or close the game"
        )
        raise WorldInUseError(message) from error
    return place


def sweep(profile: Path) -> list[Path]:
    """Delete what the game no longer holds of retired mods; returns what is still left.

    Each retired mod loses its metadata first. This never raises: what cannot be deleted now
    is deleted by a later install, uninstall or start of the generator.
    """
    work = profile / MODS / WORK
    left: list[Path] = []
    if (work / RETIRED).is_dir():
        for retired in sorted((work / RETIRED).iterdir()):
            with contextlib.suppress(OSError):
                (retired / METADATA).unlink(missing_ok=True)
            shutil.rmtree(retired, ignore_errors=True)
            if retired.exists():
                left.append(retired)
    _tidy(work)
    return left


def _tidy(work: Path) -> None:
    """Remove the work folder's empty parts, so a finished install leaves no trace."""
    for folder in (work / RETIRED, work / INCOMING, work):
        with contextlib.suppress(OSError):
            folder.rmdir()


def uninstall(names: Iterable[str], profile: Path) -> list[Path]:
    """Remove the named generated mods from ``profile/mod``; refuses any other folder."""
    targets = [profile / MODS / name for name in names]
    bad = [str(target) for target in targets if not is_rnw_mod(target)]
    if bad:
        message = f"Not installed rnw_exp_* mods: {', '.join(bad)}"
        raise InstallError(message)
    for target in targets:
        _ = _retire(target)
    _ = sweep(profile)
    return targets
