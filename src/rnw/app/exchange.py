"""Worlds in and out of the library as files (ADR 0010, C).

``export_world`` and ``import_world`` move the compact ``.rnworld``: the record of how a world was
made, its code and its atlas. A world imported this way is its code and its maps (``Placement
.CODE_ONLY``); added to the game it is made again from the code, which needs the game.

Nothing here reads the game: the compact world file is ours (``rnw.atlas``, ADR 0010, H). Built
worlds are moved by ``rnw.app.transfer``, which does. Everything read from a file is checked by
``rnw.worldfile`` first, and the world's id, which names a folder, is held to the pattern ids
have.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import atlas as atlas_module
from rnw import landmask as land_mask_module
from rnw import pictures, worldfile
from rnw.app import install, library
from rnw.app.worldcode import WorldCodeError, decode
from rnw.png import COLOR_RGB, encode_png
from rnw.record import NewerFormatError, RecordError

if TYPE_CHECKING:
    from pathlib import Path

    from rnw.app.library import World

ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"[a-z2-7]{10}")
PICTURE_MARGIN: Final[int] = 1


class ExchangeError(ValueError):
    """A world that cannot be moved, and why."""


@dataclass(frozen=True, slots=True)
class Imported:
    """A world taken from a file: the library's record of it, and whether it is new there."""

    world: World
    created: bool


def checked_world(record: dict[str, object]) -> World:
    """The world a file describes, if it is one this generator can hold in its library."""
    try:
        world = library.world_of(record)
    except NewerFormatError as error:
        raise ExchangeError(str(error)) from error
    except (KeyError, ValueError, TypeError, RecordError) as error:
        message = f"The world in the file is damaged: {error!r}"
        raise ExchangeError(message) from error
    if world is None:
        message = "The world in the file is of a layout this generator does not know"
        raise ExchangeError(message)
    if ID_PATTERN.fullmatch(world.id) is None:
        message = "The world in the file has an id that is not one"
        raise ExchangeError(message)
    try:
        _ = decode(world.code)
    except WorldCodeError as error:
        message = f"The world in the file has a code that cannot be read: {error}"
        raise ExchangeError(message) from error
    return replace(world, revealed=False, mod_folder="")


def export_world(data: Path, world: World, output: Path) -> Path:
    """Write the compact world file of ``world`` at ``output``; returns it.

    The record, the code, the name, the version and the atlas go in; nothing of the game and no
    mod does. The world is written covered: whoever opens it chooses to reveal it.
    """
    record = library.document(replace(world, revealed=False))
    image = library.folder(data, world) / library.LAND_MASK
    drawn = image.read_bytes() if image.is_file() else None
    return worldfile.write(output, record, atlas_files(data, world), drawn)


def atlas_files(data: Path, world: World) -> tuple[bytes, bytes] | None:
    folder = library.folder(data, world)
    document, labels = folder / atlas_module.JSON_FILE, folder / atlas_module.LABELS_FILE
    if not (document.is_file() and labels.is_file()):
        return None
    return document.read_bytes(), labels.read_bytes()


def copy_mod(mod: Path, destination: Path) -> Path:
    """Copy a world's mod into ``destination``, a folder of the player's choice (a mods folder to
    manage by hand, a folder to upload from); returns the mod's new folder.

    Refuses anything that is not a mod of this project, and an existing folder of its name: it
    never replaces what the player has there.
    """
    if not install.is_rnw_mod(mod):
        message = f"{mod} is not a mod of this project"
        raise ExchangeError(message)
    if not destination.is_dir():
        message = f"{destination} is not a folder"
        raise ExchangeError(message)
    target = destination / mod.name
    if target.exists():
        message = f"{target} exists already; it was not replaced"
        raise ExchangeError(message)
    staged = destination / f".{mod.name}.copying"
    shutil.rmtree(staged, ignore_errors=True)
    try:
        _ = shutil.copytree(mod, staged)
        _ = staged.rename(target)
    except BaseException:
        shutil.rmtree(staged, ignore_errors=True)
        raise
    return target


def import_world(data: Path, path: Path) -> Imported:
    """Take the world of a ``.rnworld`` into the library, as its code and its maps.

    A world the library already has is left as it is (its mod, name and pictures are the player's),
    and given its atlas if it had none. Raises ``ExchangeError`` or ``WorldFileError`` for a file
    that is not to be trusted.
    """
    found = worldfile.read(path)
    world = checked_world(found.record)
    if found.atlas is not None:
        check_atlas(found.atlas)
    if found.land_mask is not None:
        check_land_mask(found.land_mask, world)
    target = library.folder(data, world)
    existing = library.load_one(target)
    if existing is None:
        library.save(data, world)
    if found.atlas is not None:
        keep_atlas(target, found.atlas)
    if found.land_mask is not None:
        keep_land_mask(target, found.land_mask)
    draw_previews(target)
    return Imported(existing or world, created=existing is None)


def check_land_mask(data: bytes, world: World) -> None:
    """The land image of a file must be the one the world's code names, before it is kept."""
    try:
        mask = land_mask_module.from_bytes(data)
    except land_mask_module.LandMaskError as error:
        message = f"The land image in the file is not usable: {error}"
        raise ExchangeError(message) from error
    wanted = decode(world.code).settings().mask.id
    if mask.id != wanted:
        message = "The land image in the file is not the one the world's code names"
        raise ExchangeError(message)


def keep_land_mask(target: Path, data: bytes) -> None:
    """Write a file's land image into a world's folder if it has none."""
    image = target / library.LAND_MASK
    if not image.is_file():
        target.mkdir(parents=True, exist_ok=True)
        _ = image.write_bytes(data)


def check_atlas(files: tuple[bytes, bytes]) -> None:
    """Read the atlas of a file before anything is written: a damaged one takes nothing in."""
    try:
        _ = atlas_module.from_files(*files)
    except atlas_module.AtlasError as error:
        message = f"The atlas in the file is damaged: {error}"
        raise ExchangeError(message) from error


def keep_atlas(target: Path, files: tuple[bytes, bytes]) -> None:
    """Write the atlas of a file into a world's folder if it has none, after reading it."""
    document, labels = target / atlas_module.JSON_FILE, target / atlas_module.LABELS_FILE
    if document.is_file() and labels.is_file():
        return
    target.mkdir(parents=True, exist_ok=True)
    _ = document.write_bytes(files[0])
    _ = labels.write_bytes(files[1])


def draw_previews(target: Path) -> None:
    """Pictures for a world that has none, drawn from its atlas: the land, and the same covered."""
    covered, shown = target / library.PREVIEW_HIDDEN, target / library.PREVIEW
    if covered.is_file() and shown.is_file():
        return
    document, labels = target / atlas_module.JSON_FILE, target / atlas_module.LABELS_FILE
    if not (document.is_file() and labels.is_file()):
        return
    found = atlas_module.from_files(document.read_bytes(), labels.read_bytes())
    inside = (found.labels > 0)[:, :, np.newaxis]
    flat = np.where(
        inside,
        np.array(pictures.TERRA_INCOGNITA, dtype=np.uint8),
        np.array(pictures.BACKGROUND, dtype=np.uint8),
    ).astype(np.uint8)
    for path, picture in (
        (covered, flat),
        (shown, atlas_module.render(found, "land", borders=False)),
    ):
        if not path.is_file():
            _ = path.write_bytes(encode_png(picture, color_type=COLOR_RGB, compression="zlib"))
