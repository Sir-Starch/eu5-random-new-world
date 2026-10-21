"""The worlds a player has made, kept by the generator; each one is a mod of its own.

A world lives in ``generated/<folder>/`` of the generator's data folder: the export's bundle
(``manifest.json``, ``report.json``, ``settings.json``, ``preview.png`` and the covered
``preview_hidden.png``) and ``world.json``, which this module writes. Until the world is
added to the game, the mod itself is there too (``generated/<folder>/<folder>/``); adding it
moves the mod into the profile's ``mod/`` folder, and removing it from the game deletes it
there, after which the code regenerates it byte for byte. A world is named by its code and
the game build it was made for, so the same code on the same build is the same mod.

Mods of the project that the library does not know (worlds made before it, or by the
command line) are listed as strays, so the player can see and remove everything that is in
the game.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import shutil
import time
from dataclasses import asdict, dataclass, replace
from enum import Enum
from typing import TYPE_CHECKING, Final, cast

from rnw.app import install
from rnw.app.paths import workspace
from rnw.eu5_map import open_png
from rnw.pictures import center_column, thumbnail
from rnw.png import COLOR_RGB, encode_png

if TYPE_CHECKING:
    from pathlib import Path

RECORD: Final[str] = "world.json"
SCHEMA: Final[int] = 1
FOLDER_PREFIX: Final[str] = "rnw_exp_world_"
ID_LENGTH: Final[int] = 10
PREVIEW: Final[str] = "preview.png"
PREVIEW_HIDDEN: Final[str] = "preview_hidden.png"
THUMBNAIL: Final[str] = ".metadata/thumbnail.png"
MAP_MARKER: Final[str] = "in_game/map_data"


class Placement(Enum):
    """Where a world's mod is."""

    IN_GAME = "in_game"
    KEPT = "kept"
    CODE_ONLY = "code_only"


@dataclass(frozen=True, slots=True)
class World:
    """One world: its code, the game build it was made for and the player's name for it."""

    id: str
    code: str
    preset: str
    seed: int
    generator: str
    game_build: str
    created: int
    seconds: float
    name: str = ""

    @property
    def folder(self) -> str:
        """The mod's folder and id."""
        return f"{FOLDER_PREFIX}{self.id}"


def world_id(code: str, game_build: str) -> str:
    """Ten letters and digits naming the world of ``code`` on ``game_build``."""
    digest = hashlib.sha256(f"{code}|{game_build}".encode()).digest()
    return base64.b32encode(digest).decode("ascii").lower()[:ID_LENGTH]


def folder(data: Path, world: World) -> Path:
    """The world's folder in the generator's data."""
    return workspace(data) / world.folder


def save(data: Path, world: World) -> None:
    """Write ``world.json`` into the world's folder, whole."""
    target = folder(data, world)
    target.mkdir(parents=True, exist_ok=True)
    document = {"schema": SCHEMA, **asdict(world)}
    scratch = target / f".{RECORD}.new"
    _ = scratch.write_text(json.dumps(document, indent=1, ensure_ascii=False), encoding="utf-8")
    _ = scratch.replace(target / RECORD)


def _read(path: Path) -> World | None:
    with contextlib.suppress(OSError, ValueError, KeyError, TypeError):
        row = cast("dict[str, object]", json.loads(path.read_text(encoding="utf-8")))
        if row.get("schema") != SCHEMA:
            return None
        return World(
            id=str(row["id"]),
            code=str(row["code"]),
            preset=str(row["preset"]),
            seed=int(str(row["seed"])),
            generator=str(row["generator"]),
            game_build=str(row["game_build"]),
            created=int(str(row["created"])),
            seconds=float(str(row["seconds"])),
            name=str(row.get("name", "")),
        )
    return None


def load(data: Path) -> list[World]:
    """The worlds in the generator's data, newest first; a damaged record is skipped."""
    root = workspace(data)
    if not root.is_dir():
        return []
    worlds = [
        world
        for path in sorted(root.glob(f"{FOLDER_PREFIX}*/{RECORD}"))
        if (world := _read(path)) is not None and path.parent.name == world.folder
    ]
    return sorted(worlds, key=lambda world: (-world.created, world.id))


def rename(data: Path, world: World, name: str) -> World:
    """The world with the player's ``name`` (blank: the default name), saved."""
    renamed = replace(world, name=name.strip())
    save(data, renamed)
    return renamed


def forget(data: Path, world: World) -> None:
    """Delete the world's folder in the generator's data (its kept mod included)."""
    shutil.rmtree(folder(data, world), ignore_errors=True)


def kept(data: Path, world: World) -> Path | None:
    """The world's mod in the generator's data, if it was not added to the game."""
    mod = folder(data, world) / world.folder
    return mod if install.is_rnw_mod(mod) else None


def installed(profile: Path | None, world: World) -> Path | None:
    """The world's mod in the profile, if it is in the game."""
    if profile is None:
        return None
    mod = profile / install.MODS / world.folder
    return mod if install.is_rnw_mod(mod) else None


def placement(data: Path, profile: Path | None, world: World) -> Placement:
    """In the game, kept beside the generator, or only its code and pictures."""
    if installed(profile, world) is not None:
        return Placement.IN_GAME
    return Placement.KEPT if kept(data, world) is not None else Placement.CODE_ONLY


def picture(data: Path, world: World, *, revealed: bool) -> Path | None:
    """The world's preview, covered unless ``revealed``; None if it has none."""
    path = folder(data, world) / (PREVIEW if revealed else PREVIEW_HIDDEN)
    return path if path.is_file() else None


def strays(profile: Path | None, worlds: list[World]) -> list[Path]:
    """Generated worlds in the profile that the library does not know."""
    if profile is None:
        return []
    known = {world.folder for world in worlds}
    return [
        mod
        for mod in install.installed_mods(profile)
        if mod.name not in known and (mod / MAP_MARKER).is_dir()
    ]


def write_thumbnail(data: Path, world: World, mod: Path, *, revealed: bool) -> bool:
    """Make the mod's picture in the game's mod list from the covered or the full preview.

    The export already wrote the covered one; this is for the player who asked for the
    full one, and for going back. Returns False when the preview is missing.
    """
    source = picture(data, world, revealed=revealed)
    covered = picture(data, world, revealed=False)
    if source is None or covered is None:
        return False
    center = center_column(open_png(covered, "RGB"))
    data_bytes = encode_png(
        thumbnail(open_png(source, "RGB"), center), color_type=COLOR_RGB, compression="zlib"
    )
    target = mod / THUMBNAIL
    target.parent.mkdir(parents=True, exist_ok=True)
    scratch = target.with_name(f".{target.name}.new")
    _ = scratch.write_bytes(data_bytes)
    _ = scratch.replace(target)
    return True


def now() -> int:
    """Seconds since the epoch, for records."""
    return int(time.time())
