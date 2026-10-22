"""World files: a world to post, to mail, or to carry to another machine (ADR 0010, C).

Two kinds, both ZIP archives read as hostile input:

* **``.rnworld``, compact.** ``world.json`` (the record of how the world was made, its code,
  name and version), and the atlas (``atlas.json``, ``atlas_labels.png``). A few megabytes.
  Whoever opens it gets the world's maps at once and, with the game, the world made again byte for
  byte from its code. Everything in it is ours (``rnw.atlas``, H): it can be shared.
* **``.rnworld-mod``, a built world transferred.** The same, and the mod's files under ``mod/``,
  with the files of its bundle (``manifest.json``, ``inputs.json``). It is about a gigabyte and
  holds rasters derived from the game's map, which the legal notes keep out of anything shared
  (``docs/legal.md``); it is for moving a world between the player's own machines, and the other
  side refuses it unless its game files are the ones the world was made from.

A file is data and nothing in it is run. The reader accepts only the names of the layout, refuses
any path that leaves its folder, any link, directory, duplicate or executable, any member over its
size, any whole over its total, and any whose bytes do not hash to the listing in ``rnworld.json``;
it counts the bytes it reads rather than trusting the sizes an archive declares.

This module reads no game file and imports no game reader.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import stat
import zipfile
import zlib
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Final, cast

from rnw import __version__
from rnw.atlas import JSON_FILE as ATLAS_JSON
from rnw.atlas import LABELS_FILE as ATLAS_LABELS
from rnw.bundle import COVER_COPY

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Mapping
    from pathlib import Path

FORMAT: Final[int] = 1
WORLD_EXTENSION: Final[str] = ".rnworld"
MOD_EXTENSION: Final[str] = ".rnworld-mod"
META: Final[str] = "rnworld.json"
WORLD: Final[str] = "world.json"
LAND_MASK: Final[str] = "land_mask.png"
MOD_FOLDER: Final[str] = "mod"
BUNDLE_FILES: Final[tuple[str, ...]] = ("manifest.json", "inputs.json")
KIND_WORLD: Final[str] = "world"
KIND_MOD: Final[str] = "mod"
MEBIBYTE: Final[int] = 1 << 20
LIMITS: Final[dict[str, int]] = {
    META: MEBIBYTE,
    WORLD: MEBIBYTE,
    ATLAS_JSON: 32 * MEBIBYTE,
    ATLAS_LABELS: 64 * MEBIBYTE,
    LAND_MASK: 32 * MEBIBYTE,
    "manifest.json": 64 * MEBIBYTE,
    "inputs.json": 64 * MEBIBYTE,
}
WORLD_TOTAL: Final[int] = 100 * MEBIBYTE
MOD_FILES: Final[int] = 100_000
MOD_FILE_LIMIT: Final[int] = 4 << 30
MOD_TOTAL: Final[int] = 16 << 30
COVER_LIMIT: Final[int] = 8 * MEBIBYTE
CHUNK: Final[int] = 1 << 20
# A path the game and every file system can hold, and the first character that is not a control.
NAME_BYTES: Final[int] = 240
CONTROLS: Final[int] = 32
# What a mod's files never are: programs and scripts a system would run.
FORBIDDEN: Final[frozenset[str]] = frozenset(
    {
        ".exe", ".dll", ".bat", ".cmd", ".com", ".scr", ".msi", ".lnk", ".ps1", ".vbs", ".js",
        ".jar", ".sh", ".py", ".so", ".dylib", ".app", ".pif", ".cpl", ".hta", ".reg",
    }
)  # fmt: skip
SAFE_CHARACTERS: Final[str] = (
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-. ()[]{}+=,'@#&%!~"
)


class WorldFileError(ValueError):
    """A file that is not a world file, is damaged, breaks a limit, or is not to be trusted."""


@dataclass(frozen=True, slots=True)
class WorldFile:
    """What a world file holds, checked: the kind, the world's record, its atlas, its listing."""

    kind: str
    record: dict[str, object]
    atlas: tuple[bytes, bytes] | None
    files: dict[str, str]
    exported_by: str
    land_mask: bytes | None = None


def sha256(data: bytes) -> str:
    """SHA-256 of ``data``."""
    return hashlib.sha256(data).hexdigest()


@contextmanager
def _damaged() -> Generator[None]:
    """Turn what a corrupt archive raises into ``WorldFileError``."""
    try:
        yield
    except (zipfile.BadZipFile, zlib.error, NotImplementedError, RuntimeError, EOFError) as error:
        message = f"The file is damaged or of a kind this generator does not read: {error}"
        raise WorldFileError(message) from error


def check_name(name: str) -> str:
    """``name`` if it is a plain relative path inside a folder; raises ``WorldFileError``."""
    bad = (
        not name
        or len(name.encode("utf-8")) > NAME_BYTES
        or "\\" in name
        or ":" in name
        or any(part in {"", ".", ".."} for part in name.split("/"))
        or any(ord(char) < CONTROLS or char == "\x7f" for char in name)
    )
    if bad:
        message = f"The file names a path that is not allowed: {name!r}"
        raise WorldFileError(message)
    return name


def _read_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo, limit: int) -> bytes:
    """The bytes of a member, counting what is really read, never past ``limit``."""
    if info.file_size > limit:
        message = f"{info.filename} is larger than the {limit} bytes allowed"
        raise WorldFileError(message)
    chunks: list[bytes] = []
    total = 0
    with archive.open(info) as handle:
        while block := handle.read(CHUNK):
            total += len(block)
            if total > limit:
                message = f"{info.filename} holds more than the {limit} bytes allowed"
                raise WorldFileError(message)
            chunks.append(block)
    return b"".join(chunks)


def list_members(infos: Iterable[zipfile.ZipInfo]) -> dict[str, zipfile.ZipInfo]:
    """The members by name, refusing duplicates, directories, links and unsafe names."""
    found: dict[str, zipfile.ZipInfo] = {}
    for info in infos:
        name = check_name(info.filename)
        if info.is_dir():
            message = f"The file holds a folder, {name!r}"
            raise WorldFileError(message)
        kind = stat.S_IFMT(info.external_attr >> 16)
        if kind and kind != stat.S_IFREG:
            message = f"{name!r} is a link or a device, not a file"
            raise WorldFileError(message)
        if info.flag_bits & 0x1:
            message = "The file is encrypted"
            raise WorldFileError(message)
        if name in found:
            message = f"The file holds {name!r} twice"
            raise WorldFileError(message)
        found[name] = info
    return found


def _json(data: bytes, what: str) -> dict[str, object]:
    try:
        parsed = cast("object", json.loads(data.decode("utf-8")))
    except (ValueError, UnicodeDecodeError) as error:
        message = f"{what} is not valid JSON"
        raise WorldFileError(message) from error
    if not isinstance(parsed, dict):
        message = f"{what} is not an object"
        raise WorldFileError(message)
    return cast("dict[str, object]", parsed)


def _listing(meta: dict[str, object]) -> dict[str, str]:
    files = meta.get("files")
    if not isinstance(files, dict):
        message = f"{META} lists no files"
        raise WorldFileError(message)
    listed = cast("dict[object, object]", files)
    if not all(
        isinstance(name, str) and isinstance(digest, str) for name, digest in listed.items()
    ):
        message = f"{META} lists files that are not names and hashes"
        raise WorldFileError(message)
    return {check_name(str(name)): str(digest) for name, digest in listed.items()}


def _open(path: Path) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as error:
        message = f"{path.name} is not a world file: {error}"
        raise WorldFileError(message) from error


def _header(archive: zipfile.ZipFile, members: dict[str, zipfile.ZipInfo]) -> dict[str, object]:
    if META not in members:
        message = f"The file has no {META}: it is not a world file"
        raise WorldFileError(message)
    meta = _json(_read_member(archive, members[META], LIMITS[META]), META)
    found = meta.get("format")
    if isinstance(found, int) and found > FORMAT:
        message = f"The file is of format {found}; this generator reads up to {FORMAT}"
        raise WorldFileError(message)
    if found != FORMAT or meta.get("kind") not in {KIND_WORLD, KIND_MOD}:
        message = f"{META} has no readable format and kind"
        raise WorldFileError(message)
    return meta


def read(path: Path) -> WorldFile:
    """Read and check a world file; raises ``WorldFileError`` for anything not to be trusted.

    A transferred built world (``.rnworld-mod``) gives its record and atlas here too, without its
    mod, which ``extract_mod`` unpacks.
    """
    with _damaged(), _open(path) as archive:
        members = list_members(archive.infolist())
        meta = _header(archive, members)
        listed = _listing(meta)
        kind = str(meta["kind"])
        allowed = {META, WORLD, ATLAS_JSON, ATLAS_LABELS, LAND_MASK}
        if kind == KIND_MOD:
            allowed |= set(BUNDLE_FILES)
        stray = sorted(
            name
            for name in members
            if name not in allowed
            and not (kind == KIND_MOD and name.startswith((f"{MOD_FOLDER}/", f"{COVER_COPY}/")))
        )
        if stray:
            message = f"The file holds what a world file does not: {stray[:3]}"
            raise WorldFileError(message)
        if WORLD not in members:
            message = f"The file has no {WORLD}"
            raise WorldFileError(message)
        wanted = [name for name in members if name in LIMITS and name != META]
        total = 0
        loaded: dict[str, bytes] = {}
        for name in sorted(wanted):
            data = _read_member(archive, members[name], LIMITS[name])
            total += len(data)
            if total > WORLD_TOTAL:
                message = "The file is larger than a world file may be"
                raise WorldFileError(message)
            if listed.get(name) != sha256(data):
                message = f"{name} does not match the hash in {META}: the file is damaged"
                raise WorldFileError(message)
            loaded[name] = data
        if (ATLAS_JSON in loaded) != (ATLAS_LABELS in loaded):
            message = "The atlas is half there: both of its files or neither"
            raise WorldFileError(message)
        atlas = (loaded[ATLAS_JSON], loaded[ATLAS_LABELS]) if ATLAS_JSON in loaded else None
        return WorldFile(
            kind=kind,
            record=_json(loaded[WORLD], WORLD),
            atlas=atlas,
            files=listed,
            exported_by=str(meta.get("exported_by", "")),
            land_mask=loaded.get(LAND_MASK),
        )


def write(
    output: Path,
    record: Mapping[str, object],
    atlas: tuple[bytes, bytes] | None,
    land_mask: bytes | None = None,
) -> Path:
    """Write a compact world file at ``output`` (replaced); returns it."""
    parts: dict[str, bytes] = {WORLD: _dump(record)}
    if atlas is not None:
        parts[ATLAS_JSON], parts[ATLAS_LABELS] = atlas
    if land_mask is not None:
        parts[LAND_MASK] = land_mask
    meta = _meta(KIND_WORLD, {name: sha256(data) for name, data in parts.items()})
    output.parent.mkdir(parents=True, exist_ok=True)
    scratch = output.with_name(f".{output.name}.new")
    with zipfile.ZipFile(scratch, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(META, _dump(meta))
        for name, data in parts.items():
            archive.writestr(name, data)
    _ = scratch.replace(output)
    return output


def _dump(document: Mapping[str, object]) -> bytes:
    text = json.dumps(document, sort_keys=True, indent=1, ensure_ascii=False) + "\n"
    return text.encode("utf-8")


def _meta(kind: str, files: dict[str, str]) -> dict[str, object]:
    return {"format": FORMAT, "kind": kind, "exported_by": __version__, "files": files}


def mod_files(folder: Path) -> list[str]:
    """The files of a mod folder, as paths inside it, in POSIX form, sorted."""
    return sorted(
        item.relative_to(folder).as_posix() for item in folder.rglob("*") if item.is_file()
    )


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(CHUNK):
            digest.update(block)
    return digest.hexdigest()


def write_mod(  # noqa: PLR0913 - the parts of a built world
    output: Path,
    record: Mapping[str, object],
    atlas: tuple[bytes, bytes] | None,
    bundle: Mapping[str, bytes],
    mod: Path,
    *,
    land_mask: bytes | None = None,
) -> Path:
    """Write a transferred built world at ``output`` (replaced); returns it.

    ``bundle`` is the world's ``manifest.json`` and ``inputs.json``; ``mod`` its mod folder.
    """
    parts: dict[str, bytes] = {WORLD: _dump(record)}
    if atlas is not None:
        parts[ATLAS_JSON], parts[ATLAS_LABELS] = atlas
    if land_mask is not None:
        parts[LAND_MASK] = land_mask
    parts.update(bundle)
    listing = {name: sha256(data) for name, data in parts.items()}
    relatives = mod_files(mod)
    if len(relatives) > MOD_FILES:
        message = f"The mod has {len(relatives)} files; a transfer holds at most {MOD_FILES}"
        raise WorldFileError(message)
    for relative in relatives:
        if PurePosixPath(relative).suffix.lower() in FORBIDDEN:
            message = f"The mod holds a file of a kind a transfer refuses: {relative}"
            raise WorldFileError(message)
        listing[f"{MOD_FOLDER}/{relative}"] = _file_hash(mod / relative)
    output.parent.mkdir(parents=True, exist_ok=True)
    scratch = output.with_name(f".{output.name}.new")
    with zipfile.ZipFile(scratch, "w", zipfile.ZIP_STORED, allowZip64=True) as archive:
        archive.writestr(META, _dump(_meta(KIND_MOD, listing)))
        for name, data in parts.items():
            archive.writestr(name, data)
        for relative in relatives:
            archive.write(mod / relative, f"{MOD_FOLDER}/{relative}")
    _ = scratch.replace(output)
    return output


def extract_mod(path: Path, target: Path) -> WorldFile:
    """Unpack the mod of a transferred world into ``target`` (a new folder), checking every file.

    Raises ``WorldFileError`` when anything is wrong, and then ``target`` is removed: the folder
    holds only files whose bytes hash to the listing, none executable, none outside it, within the
    count and size limits. Returns what ``read`` returns for the compact part.
    """
    found = read(path)
    if found.kind != KIND_MOD:
        message = f"{path.name} is a compact world file, with no mod in it"
        raise WorldFileError(message)
    target.mkdir(parents=True)
    try:
        with _damaged(), _open(path) as archive:
            members = list_members(archive.infolist())
            _unpack(archive, members, found.files, target)
    except BaseException:
        _remove(target)
        raise
    return found


def _unpack(
    archive: zipfile.ZipFile,
    members: dict[str, zipfile.ZipInfo],
    listing: dict[str, str],
    target: Path,
) -> None:
    prefix = f"{MOD_FOLDER}/"
    names = sorted(name for name in members if name.startswith(prefix))
    if len(names) > MOD_FILES:
        message = f"The file holds {len(names)} mod files; at most {MOD_FILES} are allowed"
        raise WorldFileError(message)
    if set(names) != {name for name in listing if name.startswith(prefix)}:
        message = f"The files of the mod differ from the listing in {META}"
        raise WorldFileError(message)
    total = 0
    for name in names:
        relative = name.removeprefix(prefix)
        if PurePosixPath(relative).suffix.lower() in FORBIDDEN:
            message = f"The mod holds a file of a kind a transfer refuses: {relative}"
            raise WorldFileError(message)
        info = members[name]
        if info.file_size > MOD_FILE_LIMIT:
            message = f"{relative} is larger than a file of a mod may be"
            raise WorldFileError(message)
        destination = target.joinpath(*PurePosixPath(relative).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        written = 0
        with archive.open(info) as source, destination.open("wb") as sink:
            while block := source.read(CHUNK):
                written += len(block)
                total += len(block)
                if written > MOD_FILE_LIMIT or total > MOD_TOTAL:
                    message = "The file holds more than a transferred world may"
                    raise WorldFileError(message)
                digest.update(block)
                _ = sink.write(block)
        if digest.hexdigest() != listing[name]:
            message = f"{relative} does not match its hash in {META}: the file is damaged"
            raise WorldFileError(message)


def read_bundle(path: Path) -> dict[str, bytes]:
    """The bundle files (``manifest.json``, ``inputs.json``) of a transferred world, checked."""
    with _damaged(), _open(path) as archive:
        members = list_members(archive.infolist())
        meta = _header(archive, members)
        listed = _listing(meta)
        bundle: dict[str, bytes] = {}
        names = [
            name for name in members if name in BUNDLE_FILES or name.startswith(f"{COVER_COPY}/")
        ]
        total = 0
        for name in names:
            if name in members:
                if PurePosixPath(name).suffix.lower() in FORBIDDEN:
                    message = f"The bundle holds a file of a kind a transfer refuses: {name}"
                    raise WorldFileError(message)
                data = _read_member(archive, members[name], LIMITS.get(name, COVER_LIMIT))
                total += len(data)
                if total > WORLD_TOTAL:
                    message = "The transferred world's bundle is too large"
                    raise WorldFileError(message)
                if listed.get(name) != sha256(data):
                    message = f"{name} does not match the hash in {META}: the file is damaged"
                    raise WorldFileError(message)
                bundle[name] = data
        return bundle


def _remove(folder: Path) -> None:
    for item in sorted(folder.rglob("*"), key=lambda entry: len(entry.parts), reverse=True):
        with contextlib.suppress(OSError):
            _ = item.unlink() if item.is_file() or item.is_symlink() else item.rmdir()
    with contextlib.suppress(OSError):
        folder.rmdir()


def is_world_file(path: Path) -> bool:
    """Whether ``path`` is named as a world file of either kind."""
    name = os.fspath(path).lower()
    return name.endswith((WORLD_EXTENSION, MOD_EXTENSION))
