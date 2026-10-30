"""Every game file a job reads, with its hash: the inputs of a world (ADR 0010, G).

The export reads far more of the installation than its map: setup and country definitions,
cultures and languages, templates, localization keys, terrain decals, water files, the scripts it
rewrites, the shaders it copies for the cover. A world is the same only if those files are. Rather
than list them by hand, and miss one, ``recording`` notes every file the process opens under the
game folder, by the interpreter's audit hook (PEP 578), which sees every ``open`` of every thread
whoever makes it (the standard library, Pillow, our own readers). Only the export's own process
opens game files; the native kernels read none.

``freeze`` ends the recording: a game file not seen before and opened after it is an error, so a
read that the record would miss fails loudly instead of leaving the record incomplete (hashing the
files already seen is allowed, of course).

An audit hook cannot be removed once added; ours does nothing unless a recording is active.
"""

from __future__ import annotations

import hashlib
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Final

from rnw.record import Manifest

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

HASH_BLOCK: Final[int] = 1 << 20
WRITING: Final[int] = os.O_WRONLY | os.O_RDWR


class InputsFrozenError(RuntimeError):
    """A game file was opened after the recording of the inputs ended."""


class InputRecorder:
    """The game files opened under one folder, while it is active."""

    def __init__(self, game_dir: Path) -> None:
        given = os.fspath(game_dir).rstrip("/\\")
        absolute = str(Path(game_dir).absolute()).rstrip("/\\")
        self._prefixes: tuple[str, ...] = tuple({given + os.sep, absolute + os.sep})
        self._lock: threading.Lock = threading.Lock()
        self._seen: set[str] = set()
        self._directories: set[str] = set()
        self._frozen: bool = False

    def note(self, path: str, *, directory: bool = False) -> None:
        """Record ``path`` if it is a file under the game folder; refuse a new one once frozen."""
        for prefix in self._prefixes:
            if directory and path.rstrip("/\\") == prefix.rstrip("/\\"):
                relative = "."
                break
            if path.startswith(prefix):
                relative = PurePath(path[len(prefix) :]).as_posix()
                break
        else:
            return
        with self._lock:
            seen = self._directories if directory else self._seen
            if self._frozen and relative not in seen:
                message = f"The game file {relative} was opened after its inputs were recorded"
                raise InputsFrozenError(message)
            seen.add(relative)

    def manifest(self, game_dir: Path, *, workers: int) -> Manifest:
        files = hash_files(game_dir, self.freeze(), workers=workers)
        return Manifest(
            files.files,
            {name: directory_hash(game_dir / name) for name in sorted(self._directories)},
        )

    def freeze(self) -> list[str]:
        """End the recording; the game files seen, relative to the game folder, in POSIX form."""
        with self._lock:
            self._frozen = True
            return sorted(self._seen)


_ACTIVE: list[InputRecorder] = []
_ACTIVE_LOCK: Final[threading.Lock] = threading.Lock()
_INSTALLED: list[bool] = []


def _audit(event: str, arguments: tuple[object, ...]) -> None:
    if not _ACTIVE or event not in {"open", "os.scandir", "os.listdir"}:
        return
    path = arguments[0]
    if not isinstance(path, str | bytes | os.PathLike):
        return
    if event == "open":
        flags = arguments[2]
        if not isinstance(flags, int) or flags & WRITING:
            return
    text = os.fsdecode(path)
    for recorder in tuple(_ACTIVE):
        recorder.note(text, directory=event != "open")


@contextmanager
def recording(game_dir: Path) -> Generator[InputRecorder]:
    """Record the game files opened under ``game_dir`` while the block runs."""
    recorder = InputRecorder(game_dir)
    with _ACTIVE_LOCK:
        if not _INSTALLED:
            sys.addaudithook(_audit)
            _INSTALLED.append(True)
        _ACTIVE.append(recorder)
    try:
        yield recorder
    finally:
        with _ACTIVE_LOCK:
            _ACTIVE.remove(recorder)


# Digests of files already read, by path, size and times: comparing several worlds with the
# same game reads its files once. A file written again gets a new modification time.
_DIGESTS: dict[tuple[str, int, int, int], str] = {}
KEPT_DIGESTS: Final[int] = 100_000


def file_hash(path: Path) -> str:
    """SHA-256 of a file, read in blocks; the same file unchanged is not read again."""
    status = path.stat()
    key = (str(path), status.st_size, status.st_mtime_ns, status.st_ctime_ns)
    # CPython on Windows can report creation time as ctime. It cannot validate this
    # cache after an in-place rewrite that restores mtime, so hash those files afresh.
    cacheable = os.name != "nt"
    known = _DIGESTS.get(key) if cacheable else None
    if known is not None:
        return known
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(HASH_BLOCK):
            digest.update(block)
    found = digest.hexdigest()
    if cacheable:
        if len(_DIGESTS) >= KEPT_DIGESTS:
            _DIGESTS.clear()
        _DIGESTS[key] = found
    return found


def directory_hash(path: Path) -> str:
    listing = "\0".join(sorted(item.name for item in path.iterdir())).encode("utf-8")
    return hashlib.sha256(listing).hexdigest()


def hash_files(game_dir: Path, relatives: Iterable[str], *, workers: int) -> Manifest:
    """The manifest of ``relatives`` under ``game_dir``, hashed by ``workers`` threads."""
    names = sorted(relatives)
    paths = [game_dir / name for name in names]
    if workers <= 1:
        hashes = [file_hash(path) for path in paths]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            hashes = list(pool.map(file_hash, paths))
    return Manifest(dict(zip(names, hashes, strict=True)))


@dataclass(frozen=True, slots=True)
class Comparison:
    """How the game's files differ from the ones a world read."""

    missing: list[str]
    changed: list[str]

    @property
    def same(self) -> bool:
        """Whether every file is there and equal."""
        return not self.missing and not self.changed


def compare(game_dir: Path, manifest: Manifest, *, workers: int) -> Comparison:
    """Compare the game's files with ``manifest``: the files gone and the files that changed.

    A file the world did not read, such as one a patch added to a folder it lists, is not seen
    here; rebuilding the world (``rnw verify-world``) is the check that sees it.
    """
    present = [name for name in manifest.files if (game_dir / name).is_file()]
    missing = sorted(set(manifest.files) - set(present))
    now = hash_files(game_dir, present, workers=workers)
    changed = sorted(name for name in present if now.files[name] != manifest.files[name])
    for name, digest in manifest.directories.items():
        directory = game_dir / name
        if not directory.is_dir():
            missing.append(f"{name}/")
        elif directory_hash(directory) != digest:
            changed.append(f"{name}/")
    return Comparison(missing, changed)
