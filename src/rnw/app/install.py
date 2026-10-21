"""Installing a generated mod into the player's profile, and removing it again.

Only folders named ``rnw_exp_*`` that carry mod metadata are ever replaced or removed;
no other mod, playset, save or setting is read or written. A mod is copied beside its
place first and swapped in, so an interrupted install leaves the old one in place.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Final

from rnw.artifacts import swap_in, when_free

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

PREFIX: Final[str] = "rnw_exp_"
METADATA: Final[str] = ".metadata/metadata.json"
MODS: Final[str] = "mod"


class InstallError(ValueError):
    """The mod cannot be installed or removed without touching something that is not ours."""


def is_rnw_mod(path: Path) -> bool:
    """Whether ``path`` is a generated mod folder of this project."""
    return path.is_dir() and path.name.startswith(PREFIX) and (path / METADATA).is_file()


def installed_mods(profile: Path) -> list[Path]:
    """The generated mods in the profile's ``mod`` folder, by name."""
    folder = profile / MODS
    if not folder.is_dir():
        return []
    return sorted(path for path in folder.iterdir() if is_rnw_mod(path))


def install(prepared: Path, profile: Path, *, replace: bool = False) -> Path:
    """Copy the generated mod ``prepared`` into ``profile/mod``; returns where it went."""
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
    target.parent.mkdir(exist_ok=True)
    incoming = target.parent / f".{target.name}.partial"
    if incoming.exists():
        when_free(lambda: shutil.rmtree(incoming))
    _ = shutil.copytree(prepared, incoming)
    swap_in(incoming, target)
    return target


def uninstall(names: Iterable[str], profile: Path) -> list[Path]:
    """Remove the named generated mods from ``profile/mod``; refuses any other folder."""
    targets = [profile / MODS / name for name in names]
    bad = [str(target) for target in targets if not is_rnw_mod(target)]
    if bad:
        message = f"Not installed rnw_exp_* mods: {', '.join(bad)}"
        raise InstallError(message)
    for target in targets:
        when_free(lambda target=target: shutil.rmtree(target))
    return targets
