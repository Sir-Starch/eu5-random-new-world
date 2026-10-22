"""The reproducibility record of a world, and what is read from it (ADR 0010, G).

A seed does not give the same world in a year: the algorithm moves on, the presets are retuned,
the game's files change with a patch. A hash proves a file is whole; it does not make a rebuild a
reproduction. So every world carries a record of what made it:

* ``format``: the version of this layout, so an old record is always readable;
* ``algorithm``: the epoch of the generator that made it (``rnw.epoch``), and ``release``, the
  version that made it, which tells the player where to find the original generator;
* ``settings``: every resolved value; the preset is only a label, and the world is made again
  from these, whatever the presets have become;
* ``game``: the game's label and the digest of its map contract, the digest of **every game file
  the export read** (``Manifest``, kept beside the world) and how many there are;
* ``output``: the digest of every file the world's mod is made of but its ``.metadata``, which is
  presentation and is written anew, so that a rebuild can be *checked* against it.

This module is data and its rules only; it reads no game file, so the viewer and the files of
worlds can use it without the game (ADR 0010, H).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Final, cast

from rnw import epoch
from rnw.settings import SettingsError, build_settings

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from rnw.settings import Settings

FORMAT: Final[int] = 1
METADATA_DIR: Final[str] = ".metadata/"


class RecordError(ValueError):
    """A record that is damaged or not a record."""


class NewerFormatError(RecordError):
    """A record written by a newer generator, in a layout this one cannot read."""

    def __init__(self, found: int) -> None:
        super().__init__(f"The record is of format {found}; this generator reads up to {FORMAT}")
        self.found: int = found


class Verdict(Enum):
    """What opening a world finds out about whether this generator makes it again."""

    IDENTICAL = "identical"
    SAME_ALGORITHM = "same_algorithm"
    OTHER_INPUTS = "other_inputs"
    OTHER_ALGORITHM = "other_algorithm"
    NEWER_FORMAT = "newer_format"


def manifest_digest(entries: Mapping[str, str]) -> str:
    """One digest of a set of files: SHA-256 of ``path TAB hash`` lines in path order."""
    lines = "".join(f"{path}\t{entries[path]}\n" for path in sorted(entries))
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


def output_entries(files: Iterable[Mapping[str, object]], mod: str) -> dict[str, str]:
    """Path (inside the mod) to hash for every file of ``mod`` in an export's file list, but its
    ``.metadata``; files outside the mod (pictures, the report) are not part of the world."""
    prefix = f"{mod}/"
    entries: dict[str, str] = {}
    for item in files:
        path, digest = str(item["path"]), str(item["sha256"])
        if path.startswith(prefix) and not path.removeprefix(prefix).startswith(METADATA_DIR):
            entries[path.removeprefix(prefix)] = digest
    return entries


@dataclass(frozen=True, slots=True)
class Manifest:
    """The game files an export read, each with its SHA-256: path under the game folder, in
    POSIX form, to hash."""

    files: dict[str, str]
    directories: dict[str, str] = field(default_factory=dict)

    @property
    def digest(self) -> str:
        """One digest of the whole manifest."""
        listed = {**self.files, **{f"{name}/": digest for name, digest in self.directories.items()}}
        return manifest_digest(listed)

    def to_json(self) -> dict[str, object]:
        """The manifest as a JSON document."""
        return {
            "format": FORMAT,
            "files": dict(sorted(self.files.items())),
            "directories": dict(sorted(self.directories.items())),
        }

    @classmethod
    def from_json(cls, data: object) -> Manifest:
        """Read a manifest; raises ``RecordError`` when it is not one."""
        if not isinstance(data, dict):
            message = "A manifest of inputs is an object"
            raise RecordError(message)
        document = cast("dict[str, object]", data)
        found = document.get("format")
        if isinstance(found, int) and found > FORMAT:
            raise NewerFormatError(found)
        files = document.get("files")
        if found != FORMAT or not isinstance(files, dict):
            message = "A manifest of inputs has a format and files"
            raise RecordError(message)
        listed = cast("dict[object, object]", files)
        if not all(
            isinstance(path, str) and isinstance(digest, str) for path, digest in listed.items()
        ):
            message = "A manifest of inputs maps paths to hashes"
            raise RecordError(message)
        directories = document.get("directories", {})
        if not isinstance(directories, dict):
            message = "A manifest's directories map paths to hashes"
            raise RecordError(message)
        folders = cast("dict[object, object]", directories)
        for path, digest in [*listed.items(), *folders.items()]:
            if not isinstance(path, str) or not isinstance(digest, str):
                message = "A manifest maps paths to hashes"
                raise RecordError(message)
            if (
                not path
                or "\\" in path
                or ":" in path
                or "\0" in path
                or PurePosixPath(path).is_absolute()
                or ".." in PurePosixPath(path).parts
            ):
                message = "A manifest path must stay inside the game installation"
                raise RecordError(message)
        return cls(
            {str(path): str(digest) for path, digest in listed.items()},
            {str(path): str(digest) for path, digest in folders.items()},
        )


@dataclass(frozen=True, slots=True)
class GameRecord:
    """The game a world was made from."""

    label: str
    fingerprint_sha256: str
    supported: str
    inputs_sha256: str
    inputs_count: int


@dataclass(frozen=True, slots=True)
class Record:
    """Everything needed to make a world again, or to know why it cannot be made again."""

    format: int
    algorithm: int
    release: str
    code: str | None
    preset: str
    seed: int
    settings: dict[str, object]
    game: GameRecord
    output_sha256: str
    output_count: int

    def resolved_settings(self) -> Settings:
        """The settings the world was made with, read from the record and not from the presets."""
        try:
            return build_settings(self.preset, dict(self.settings))
        except SettingsError as error:
            message = f"The record's settings cannot be read: {error}"
            raise RecordError(message) from error

    def to_json(self) -> dict[str, object]:
        """The record as a JSON document."""
        return {
            "format": self.format,
            "algorithm": self.algorithm,
            "release": self.release,
            "code": self.code,
            "preset": self.preset,
            "seed": self.seed,
            "settings": self.settings,
            "game": {
                "label": self.game.label,
                "fingerprint_sha256": self.game.fingerprint_sha256,
                "supported": self.game.supported,
                "inputs_sha256": self.game.inputs_sha256,
                "inputs_count": self.game.inputs_count,
            },
            "output": {"sha256": self.output_sha256, "count": self.output_count},
        }

    @classmethod
    def from_json(cls, data: object) -> Record:
        """Read a record; raises ``NewerFormatError`` for a newer layout, else ``RecordError``."""
        if not isinstance(data, dict):
            message = "A record is an object"
            raise RecordError(message)
        document = cast("dict[str, object]", data)
        found = document.get("format")
        if isinstance(found, int) and found > FORMAT:
            raise NewerFormatError(found)
        try:
            game = cast("dict[str, object]", document["game"])
            output = cast("dict[str, object]", document["output"])
            code = document["code"]
            record = cls(
                format=_integer(found),
                algorithm=_integer(document["algorithm"]),
                release=_text(document["release"]),
                code=None if code is None else _text(code),
                preset=_text(document["preset"]),
                seed=_integer(document["seed"]),
                settings=dict(cast("dict[str, object]", document["settings"])),
                game=GameRecord(
                    label=_text(game["label"]),
                    fingerprint_sha256=_text(game["fingerprint_sha256"]),
                    supported=_text(game["supported"]),
                    inputs_sha256=_text(game["inputs_sha256"]),
                    inputs_count=_integer(game["inputs_count"]),
                ),
                output_sha256=_text(output["sha256"]),
                output_count=_integer(output["count"]),
            )
        except (KeyError, TypeError, AttributeError) as error:
            message = f"The record is damaged: {error!r}"
            raise RecordError(message) from error
        if record.format != FORMAT:
            message = f"The record has format {record.format!r}"
            raise RecordError(message)
        return record


def _text(value: object) -> str:
    if not isinstance(value, str):
        message = f"Expected text, found {value!r}"
        raise TypeError(message)
    return value


def _integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        message = f"Expected a whole number, found {value!r}"
        raise TypeError(message)
    return value


def canonical(data: object) -> str:
    """Compact JSON with sorted keys, as a record or a manifest is written beside a world."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def verdict(record: Record, *, inputs_same: bool | None = None) -> Verdict:
    """Whether this generator makes the record's world again.

    ``inputs_same`` is the result of comparing the game's files with the ones the world read:
    True, False, or None when they have not been compared (a window that opens a world does not
    hash a gigabyte to draw a line). Never silent: the answer is one of five states.
    """
    if record.format > FORMAT:
        return Verdict.NEWER_FORMAT
    if record.algorithm != epoch.CURRENT:
        return Verdict.OTHER_ALGORITHM
    if inputs_same is None:
        return Verdict.SAME_ALGORITHM
    return Verdict.IDENTICAL if inputs_same else Verdict.OTHER_INPUTS
