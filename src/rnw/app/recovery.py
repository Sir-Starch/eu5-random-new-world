"""Recognize installed RNW worlds without changing their mods or playsets.

New application-generated mods carry a small library bundle in .metadata. Older
mods can still supply their code and title; their missing build/record is never
invented. Installed folder aliases keep manual exports usable in place.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import re
import shutil
from dataclasses import replace
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Final, cast

from rnw import atlas, worldname
from rnw.app import install, library, logs
from rnw.app.exchange import checked_world
from rnw.app.worldcode import IN_TEXT, decode
from rnw.bundle import COVER_COPY
from rnw.epoch import parse
from rnw.pngread import read_rgb
from rnw.record import manifest_digest

if TYPE_CHECKING:
    from pathlib import Path

RECEIPT: Final[str] = ".metadata/rnw-library"
ASSETS: Final[tuple[str, ...]] = (
    library.PREVIEW,
    library.PREVIEW_HIDDEN,
    library.INPUTS,
    library.MANIFEST,
    "report.json",
    "settings.json",
    atlas.JSON_FILE,
    atlas.LABELS_FILE,
    library.LAND_MASK,
)
Signature = tuple[tuple[str, int, int], ...]


def _copy(source: Path, target: Path) -> None:
    """Copy fixed bundle paths, refusing links rather than following them outside the mod."""
    if source.is_symlink() or any(path.is_symlink() for path in source.rglob("*")):
        message = "A world recovery bundle must not contain symbolic links"
        raise ValueError(message)
    for name in ASSETS:
        path = source / name
        if path.is_file():
            target.mkdir(parents=True, exist_ok=True)
            _ = shutil.copyfile(path, target / name)
    cover = source / COVER_COPY
    if cover.is_dir():
        _ = shutil.copytree(cover, target / COVER_COPY, dirs_exist_ok=True)


def write(data: Path, world: library.World, mod: Path) -> None:
    """Keep recovery data with a generated mod; never include private library notes."""
    target = mod / RECEIPT
    if mod.is_symlink() or (mod / ".metadata").is_symlink() or target.is_symlink():
        message = "A world recovery destination must not be a symbolic link"
        raise ValueError(message)
    _copy(library.folder(data, world), target)
    portable = replace(world, notes="", starred=False, user_tag="", revealed=False, mod_folder="")
    target.mkdir(parents=True, exist_ok=True)
    _ = (target / library.RECORD).write_text(
        json.dumps(library.document(portable), ensure_ascii=False, indent=1), encoding="utf-8"
    )


def _document(path: Path) -> dict[str, object]:
    if path.is_symlink():
        message = "A world metadata file must not be a symbolic link"
        raise ValueError(message)
    document = cast("object", json.loads(path.read_text(encoding="utf-8-sig")))
    if not isinstance(document, dict):
        message = "World metadata must be an object"
        raise TypeError(message)
    return cast("dict[str, object]", document)


def _legacy(mod: Path, metadata: dict[str, object]) -> library.World:
    match = IN_TEXT.search(str(metadata.get("short_description", "")))
    if match is None:
        message = "The installed world has no readable world code"
        raise ValueError(message)
    text = match.group()
    code = decode(text)
    release = str(metadata.get("version", ""))
    _ = parse(release)
    suffix = mod.name.removeprefix(library.FOLDER_PREFIX)
    ident = (
        suffix
        if re.fullmatch(r"[a-z2-7]{10}", suffix)
        else library.world_id(text, f"installed:{mod.name}")
    )
    return library.World(
        id=ident,
        code=text,
        preset=code.preset,
        seed=code.seed,
        generator=release,
        game_build="",
        created=int((mod / install.METADATA).stat().st_mtime),
        seconds=0.0,
        show_new_world=not (mod / "main_menu/gfx/FX/rnw_new_world_cover.fxh").is_file(),
    )


def _read(mod: Path, metadata: dict[str, object]) -> library.World:
    path = mod / RECEIPT / library.RECORD
    if not path.is_file():
        return _legacy(mod, metadata)
    if (
        mod.is_symlink()
        or (mod / ".metadata").is_symlink()
        or path.is_symlink()
        or (mod / RECEIPT).is_symlink()
    ):
        message = "A world receipt must not be a symbolic link"
        raise ValueError(message)
    world = checked_world(_document(path))
    code = decode(world.code)
    if (world.seed, world.preset) != (code.seed, code.preset):
        message = "World receipt and world code disagree"
        raise ValueError(message)
    record = world.record
    if record is not None and (
        (record.seed, record.preset, record.release) != (world.seed, world.preset, world.generator)
        or record.resolved_settings() != code.settings()
        or (record.code is not None and record.code != world.code)
    ):
        message = "World receipt and reproducibility record disagree"
        raise ValueError(message)
    return world


def _restore(data: Path, mod: Path, world: library.World) -> None:
    target = library.folder(data, world)
    source = mod / RECEIPT
    if source.is_dir():
        _copy(source, target)
    else:
        thumbnail = mod / library.THUMBNAIL
        if thumbnail.is_file() and not thumbnail.is_symlink():
            with contextlib.suppress(OSError, ValueError):
                _ = read_rgb(thumbnail)
                target.mkdir(parents=True, exist_ok=True)
                for name in (library.PREVIEW, library.PREVIEW_HIDDEN):
                    _ = shutil.copyfile(thumbnail, target / name)
    rebase_bundle(target, world.folder)
    _verify_assets(data, world)
    library.save(data, world)


def _verify_assets(data: Path, world: library.World) -> None:
    target = library.folder(data, world)
    record = world.record
    if record is not None:
        inputs = library.inputs_manifest(data, world)
        outputs = library.exported_outputs(data, world)
        if (
            inputs is None
            or inputs.digest != record.game.inputs_sha256
            or outputs is None
            or len(outputs) != record.output_count
            or manifest_digest(outputs) != record.output_sha256
        ):
            message = "The recovery bundle does not match the world's reproducibility record"
            raise ValueError(message)
        _verify_bundle_files(target)
        wanted = decode(world.code).settings().mask.id
        if wanted:
            mask = library.land_mask(data, world)
            if mask is None or mask.id != wanted:
                message = "The recovery land image is missing or does not match the world code"
                raise ValueError(message)
    if (
        (target / atlas.JSON_FILE).exists() or (target / atlas.LABELS_FILE).exists()
    ) and library.atlas(data, world) is None:
        message = "The recovery atlas is incomplete or damaged"
        raise ValueError(message)
    for name in (library.PREVIEW, library.PREVIEW_HIDDEN):
        if (target / name).is_file():
            _ = read_rgb(target / name)


def _verify_bundle_files(target: Path) -> None:
    """Verify only small library assets, never hash the world's map on the UI thread."""
    files = _document(target / library.MANIFEST).get("files", [])
    if not isinstance(files, list):
        message = "A recovery manifest must list its files"
        raise TypeError(message)
    for item in cast("list[object]", files):
        if not isinstance(item, dict):
            message = "A recovery manifest entry must be an object"
            raise TypeError(message)
        entry = cast("dict[str, object]", item)
        path = str(entry.get("path", ""))
        if path.startswith(install.PREFIX):
            continue
        parts = path.split("/")
        if (
            any(part in {"", ".", ".."} for part in parts)
            or "\\" in path
            or (path not in ASSETS and not path.startswith(COVER_COPY + "/"))
        ):
            message = "A recovery asset must stay inside the library bundle"
            raise ValueError(message)
        with (target / path).open("rb") as handle:
            found = hashlib.file_digest(handle, "sha256").hexdigest()
        if found != entry.get("sha256"):
            message = f"The recovery asset {path} does not match its manifest"
            raise ValueError(message)


def rebase_bundle(target: Path, mod_folder: str) -> None:
    """Keep manifest paths relative to the installed directory without changing output hashes."""
    # Manifest paths describe the original mod directory, which may now be an alias.
    for name in (library.MANIFEST, "report.json"):
        path = target / name
        if not path.is_file():
            continue
        document = _document(path)
        files = document.get("files", [])
        if isinstance(files, list):
            for item in cast("list[object]", files):
                if isinstance(item, dict):
                    entry = cast("dict[str, object]", item)
                    if not str(entry.get("path", "")).startswith(install.PREFIX):
                        continue
                    parts = str(entry["path"]).split("/")
                    if not parts[1:] or any(part in {"", ".", ".."} for part in parts):
                        message = "A recovery manifest path must stay inside its mod"
                        raise ValueError(message)
                    entry["path"] = "/".join((mod_folder, *parts[1:]))
        if name == "report.json":
            document["mod"] = mod_folder
        _ = path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")


def _install_record(data: Path, mod: Path, world: library.World) -> None:
    target = library.folder(data, world)
    if target.exists():
        message = f"Recovery would overwrite existing library files: {target.name}"
        raise ValueError(message)
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".rnw-recover-", dir=target.parent) as temporary:
        staged_data = target.parent / temporary
        _restore(staged_data, mod, world)
        _ = library.folder(staged_data, world).rename(target)


def _upgrade(data: Path, mod: Path, previous: library.World) -> library.World | None:
    """A copied mod can arrive metadata first; finish its partial entry when the receipt arrives."""
    restored = _read(mod, _document(mod / install.METADATA))
    if restored.record is None:
        return None
    if restored.code != previous.code:
        message = "The arriving recovery data belongs to a different world"
        raise ValueError(message)
    target = library.folder(data, previous)
    # A metadata-only adoption creates just these files. Preserve any other
    # existing user/bundle files rather than replacing an unrelated partial library.
    if any(
        path.name not in {library.RECORD, library.PREVIEW, library.PREVIEW_HIDDEN}
        for path in target.iterdir()
    ):
        message = "Existing library assets must not be overwritten during automatic recovery"
        raise ValueError(message)
    changed = replace(
        previous,
        record=restored.record,
        game_build=restored.game_build,
        generator=restored.generator,
        seconds=restored.seconds,
    )
    with TemporaryDirectory(prefix=".rnw-recover-", dir=target.parent) as temporary:
        staged_data = target.parent / temporary
        _restore(staged_data, mod, changed)
        backup = target.rename(staged_data / "previous")
        try:
            _ = library.folder(staged_data, changed).rename(target)
        except OSError:
            _ = backup.rename(target)
            raise
    return changed


def adopt(data: Path, profile: Path | None) -> list[library.World]:
    """Register recognizable installed worlds once, preserving all existing records."""
    known = library.load(data)
    ids = {world.id for world in known}
    adopted: list[library.World] = []
    for previous in known:
        mod = library.installed(profile, previous)
        if not previous.mod_folder or previous.record is not None or mod is None:
            continue
        if not (mod / RECEIPT / library.RECORD).is_file():
            continue
        try:
            upgraded = _upgrade(data, mod, previous)
        except (OSError, ValueError, KeyError, TypeError) as error:
            logs.get().warning("cannot complete installed world %s: %s", mod.name, error)
            continue
        if upgraded is not None:
            adopted.append(upgraded)
    for mod in library.strays(profile, known):
        try:
            if mod.is_symlink() or (mod / ".metadata").is_symlink():
                continue
            metadata = _document(mod / install.METADATA)
            world = _read(mod, metadata)
            if world.id in ids:
                world = replace(world, id=library.world_id(world.code, f"installed:{mod.name}"))
            if world.id in ids:
                continue
            title = str(metadata.get("name", "")).removeprefix(worldname.GAME_PREFIX)
            world = replace(world, name=worldname.clean_name(title), mod_folder=mod.name)
            # Validate the alias with the same rules used when loading a saved record.
            if library.world_of(library.document(world)) is None:
                continue
            _install_record(data, mod, world)
        except (OSError, ValueError, KeyError, TypeError) as error:
            logs.get().warning("cannot adopt installed world %s: %s", mod.name, error)
            continue
        ids.add(world.id)
        adopted.append(world)
    return adopted


def signature(data: Path, profile: Path | None) -> Signature:
    """Cheap change detection; unchanged polls never reload records or redraw the window."""
    paths = list((data / "generated").glob(f"{library.FOLDER_PREFIX}*/{library.RECORD}"))
    if profile is not None:
        paths.extend((profile / install.MODS).glob("rnw_exp_*/.metadata/metadata.json"))
        paths.extend((profile / install.MODS).glob(f"rnw_exp_*/{RECEIPT}/**/*"))
    found: list[tuple[str, int, int]] = []
    for path in sorted(paths):
        with contextlib.suppress(OSError):
            stat = path.stat()
            found.append((str(path), stat.st_mtime_ns, stat.st_size))
    return tuple(found)
