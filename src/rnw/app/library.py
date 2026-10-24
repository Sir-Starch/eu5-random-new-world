"""The worlds a player has made, kept by the generator; each one is a mod of its own.

A world lives in ``generated/<folder>/`` of the generator's data folder: the export's bundle
(``manifest.json``, ``report.json``, ``settings.json``, ``preview.png``, the covered
``preview_hidden.png`` and ``selection_cover/``, a copy of the mod's files that cover the New
World at country selection) and ``world.json``, which this module writes. Until the world is
added to the game, the mod itself is there too (``generated/<folder>/<folder>/``); adding it
moves the mod into the profile's ``mod/`` folder, and removing it from the game deletes it
there, after which the code regenerates it byte for byte. A world is named by its code and
the game build it was made for, so the same code on the same build is the same mod.

Whether the New World is shown before it is played is one choice of the player
(``rnw.app.preferences``); ``show`` makes a world's mod follow it: the picture in the game's mod
list, and the files that cover the New World at country selection, taken out or put back.

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

from rnw import worldname
from rnw.app import install
from rnw.app.paths import workspace
from rnw.app.worldcode import WorldCodeError, decode
from rnw.atlas import JSON_FILE as ATLAS_JSON
from rnw.atlas import LABELS_FILE as ATLAS_LABELS
from rnw.atlas import Atlas, AtlasError
from rnw.atlas import from_files as atlas_from_files
from rnw.bundle import COVER_COPY
from rnw.landmask import LandMask, LandMaskError
from rnw.landmask import read as read_land_mask
from rnw.layers import land_key
from rnw.pictures import center_column, tagged, thumbnail
from rnw.png import COLOR_RGB, encode_png
from rnw.pngread import read_rgb
from rnw.record import Manifest, NewerFormatError, Record, RecordError, output_entries

if TYPE_CHECKING:
    from pathlib import Path

RECORD: Final[str] = "world.json"
SCHEMA: Final[int] = 1
FOLDER_PREFIX: Final[str] = "rnw_exp_world_"
ID_LENGTH: Final[int] = 10
PREVIEW: Final[str] = "preview.png"
PREVIEW_HIDDEN: Final[str] = "preview_hidden.png"
ATLAS_CACHE: Final[int] = 4
INPUTS: Final[str] = "inputs.json"
LAND_MASK: Final[str] = "land_mask.png"
MANIFEST: Final[str] = "manifest.json"
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
    record: Record | None = None
    # The world this one is a version of, and the part (``rnw.layers``) made again; blank for a
    # world made from its seed.
    parent: str = ""
    part: str = ""
    # The player chose to see this world's New World in the generator (the global setting shows
    # every world's); its atlas and maps stay covered until then.
    revealed: bool = False
    notes: str = ""
    starred: bool = False
    user_tag: str = ""
    show_new_world: bool | None = None

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


def document(world: World) -> dict[str, object]:
    """The content of a world's ``world.json``: its fields, with the record in its own layout."""
    plain = cast("dict[str, object]", asdict(world))
    return {
        "schema": SCHEMA,
        **{key: value for key, value in plain.items() if key != "record"},
        "record": None if world.record is None else world.record.to_json(),
    }


def save(data: Path, world: World) -> None:
    """Write ``world.json`` into the world's folder, whole."""
    target = folder(data, world)
    target.mkdir(parents=True, exist_ok=True)
    scratch = target / f".{RECORD}.new"
    text = json.dumps(document(world), indent=1, ensure_ascii=False)
    _ = scratch.write_text(text, encoding="utf-8")
    _ = scratch.replace(target / RECORD)


def _read_record(data: object) -> Record | None:
    """The record of a world; None for a world made before records, or whose record is damaged.

    A record of a newer layout raises ``NewerFormatError``: the world was written by a newer
    generator, and is not listed until this one is updated, as with a newer ``schema``.
    """
    if data is None:
        return None
    try:
        return Record.from_json(data)
    except NewerFormatError:
        raise
    except RecordError:
        return None


def world_of(row: dict[str, object]) -> World | None:
    """The world a ``world.json`` document describes; None when its schema is not this one.

    Raises ``KeyError``, ``ValueError`` or ``TypeError`` when a field is missing or mistyped, and
    ``NewerFormatError`` for a record of a newer layout.
    """
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
        record=_read_record(row.get("record")),
        parent=str(row.get("parent", "")),
        part=str(row.get("part", "")),
        revealed=row.get("revealed") is True,
        notes=str(row.get("notes", ""))[:16384],
        starred=row.get("starred") is True,
        user_tag=str(row.get("user_tag", ""))[:64],
        show_new_world=(
            True
            if row.get("show_new_world") is True
            else False
            if row.get("show_new_world") is False
            else None
        ),
    )


def _read(path: Path) -> World | None:
    with contextlib.suppress(OSError, ValueError, KeyError, TypeError):
        return world_of(cast("dict[str, object]", json.loads(path.read_text(encoding="utf-8"))))
    return None


def load_one(folder_path: Path) -> World | None:
    """The world recorded in one folder of the library, or None."""
    return _read(folder_path / RECORD)


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


def land_of(world: World) -> str:
    """Names the world's land, so that versions of one continent are told together; a world
    whose code cannot be read is a land of its own."""
    try:
        code = decode(world.code)
        return land_key(code.settings(), code.seed)
    except (WorldCodeError, ValueError):
        return world.id


def grouped(worlds: list[World]) -> list[tuple[World, int]]:
    """The worlds in the order the window lists them, with how far each is indented.

    Versions of one continent stand together, the first made first and the others after it,
    indented; continents go newest first by their latest version.
    """
    groups: dict[str, list[World]] = {}
    for world in worlds:
        groups.setdefault(land_of(world), []).append(world)
    ordered = sorted(
        groups.values(), key=lambda group: (-max(world.created for world in group), group[0].id)
    )
    return [
        (world, 0 if number == 0 else 1)
        for group in ordered
        for number, world in enumerate(
            sorted(group, key=lambda world: (bool(world.parent), world.created, world.id))
        )
    ]


def reveal(data: Path, world: World, *, revealed: bool = True) -> World:
    """The world with its New World shown in the generator (or covered again), saved."""
    changed = replace(world, revealed=revealed)
    save(data, changed)
    return changed


def world_shown(world: World, *, default: bool = False) -> bool:
    """The saved per-world choice, or the old global choice for an un-migrated record."""
    return default if world.show_new_world is None else world.show_new_world


def migrate_visibility(data: Path, *, default: bool) -> list[World]:
    """Give legacy worlds their old global choice before it becomes a new-world default."""
    migrated: list[World] = []
    for world in load(data):
        current = replace(world, show_new_world=default) if world.show_new_world is None else world
        if current is not world:
            save(data, current)
        migrated.append(current)
    return migrated


_ATLASES: dict[tuple[str, int, int, int, int], Atlas] = {}


def atlas(data: Path, world: World) -> Atlas | None:
    """The world's atlas from its bundle, or None if it has none (made before atlases) or it
    cannot be read. Kept in memory while the files are as they were."""
    folder_path = folder(data, world)
    document, labels = folder_path / ATLAS_JSON, folder_path / ATLAS_LABELS
    try:
        first, second = document.stat(), labels.stat()
    except OSError:
        return None
    # Sizes too: two writes within one tick of the file system's clock share a time.
    key = (str(folder_path), first.st_mtime_ns, first.st_size, second.st_mtime_ns, second.st_size)
    if key not in _ATLASES:
        try:
            _ATLASES[key] = atlas_from_files(document.read_bytes(), labels.read_bytes())
        except (OSError, AtlasError):
            return None
        if len(_ATLASES) > ATLAS_CACHE:
            _ = _ATLASES.pop(next(iter(_ATLASES)))
    return _ATLASES[key]


def rename(data: Path, world: World, name: str) -> World:
    """The world with the player's ``name`` (blank: the default name), saved."""
    renamed = replace(world, name=worldname.clean_name(name))
    save(data, renamed)
    return renamed


def land_mask(data: Path, world: World) -> LandMask | None:
    """The image the world's land is drawn from, if the world has one and its folder still holds
    it; None otherwise."""
    path = folder(data, world) / LAND_MASK
    with contextlib.suppress(OSError, LandMaskError):
        return read_land_mask(path)
    return None


def inputs_manifest(data: Path, world: World) -> Manifest | None:
    """The game files the world's export read, with their hashes, if the bundle still has them."""
    path = folder(data, world) / INPUTS
    with contextlib.suppress(OSError, ValueError):
        return Manifest.from_json(cast("object", json.loads(path.read_text(encoding="utf-8"))))
    return None


def exported_outputs(data: Path, world: World) -> dict[str, str] | None:
    """Path inside the mod to hash for every file the export wrote (but ``.metadata``), from the
    bundle's manifest; None if the bundle has none."""
    path = folder(data, world) / MANIFEST
    with contextlib.suppress(OSError, ValueError, KeyError, TypeError):
        document = cast("dict[str, object]", json.loads(path.read_text(encoding="utf-8")))
        files = cast("list[dict[str, object]]", document["files"])
        return output_entries(files, world.folder)
    return None


def retitle(world: World, mod: Path) -> bool:
    """Write the world's title (its name, or the default) into the mod's metadata.

    The rest of the metadata is kept as it is. Returns False when the file cannot be read or
    replaced, as while the game holds it: the new name then shows after the world is added again.
    """
    target = mod / install.METADATA
    title = worldname.label(world.preset, worldname.tag_of(world.id), world.name).title
    scratch = target.with_name(f".{target.name}.new")
    try:
        document = cast("dict[str, object]", json.loads(target.read_text(encoding="utf-8-sig")))
        document["name"] = title
        text = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
        _ = scratch.write_bytes(text.encode("utf-8-sig"))
        _ = scratch.replace(target)
    except (OSError, ValueError):
        with contextlib.suppress(OSError):
            scratch.unlink(missing_ok=True)
        return False
    return True


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

    The covered one carries the world's tag in the middle, for the covered worlds all look
    alike; the full one shows the real New World and needs none. The export already wrote the
    covered one; this is for the player who asked for the full one, and for going back.
    Returns False when the preview is missing.
    """
    source = picture(data, world, revealed=revealed)
    covered = picture(data, world, revealed=False)
    if source is None or covered is None:
        return False
    center = center_column(read_rgb(covered))
    square = thumbnail(read_rgb(source), center)
    if not revealed:
        square = tagged(square, worldname.tag_of(world.id))
    data_bytes = encode_png(square, color_type=COLOR_RGB, compression="zlib")
    target = mod / THUMBNAIL
    target.parent.mkdir(parents=True, exist_ok=True)
    scratch = target.with_name(f".{target.name}.new")
    _ = scratch.write_bytes(data_bytes)
    _ = scratch.replace(target)
    return True


def write_cover(data: Path, world: World, mod: Path, *, covered: bool) -> bool:
    """Put the files that cover the New World at country selection into the mod, or take them out.

    The files come from the copy the export keeps beside the mod; folders left empty are
    removed. Returns False when the world has no such copy (made before the cover).
    """
    source = folder(data, world) / COVER_COPY
    if not source.is_dir():
        return False
    for path in sorted(item for item in source.rglob("*") if item.is_file()):
        target = mod / path.relative_to(source)
        if covered:
            target.parent.mkdir(parents=True, exist_ok=True)
            scratch = target.with_name(f".{target.name}.new")
            _ = shutil.copyfile(path, scratch)
            _ = scratch.replace(target)
            continue
        target.unlink(missing_ok=True)
        parent = target.parent
        while parent != mod and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent
    return True


def show(data: Path, world: World, mod: Path, *, shown: bool) -> None:
    """Make the world's mod show the New World before it is played, or keep it hidden."""
    if picture(data, world, revealed=shown) is None or picture(data, world, revealed=False) is None:
        message = (
            f"The pictures for {world.folder} are missing; its in-game picture cannot be changed"
        )
        raise OSError(message)
    cover = folder(data, world) / COVER_COPY
    if not cover.is_dir() or not any(path.is_file() for path in cover.rglob("*")):
        message = f"The saved country-selection cover for {world.folder} is missing"
        raise OSError(message)
    if not write_thumbnail(data, world, mod, revealed=shown):
        message = f"The picture for {world.folder} could not be written"
        raise OSError(message)
    if not write_cover(data, world, mod, covered=not shown):
        message = f"The saved country-selection cover for {world.folder} is missing"
        raise OSError(message)


def now() -> int:
    """Seconds since the epoch, for records."""
    return int(time.time())
