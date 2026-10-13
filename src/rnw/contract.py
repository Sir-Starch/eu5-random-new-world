"""Fingerprint the installed EU5 files that define the researched map contract."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, override

if TYPE_CHECKING:
    from pathlib import Path

CONTRACT_FILES: Final[tuple[str, ...]] = (
    "game/in_game/map_data/default.map",
    "game/in_game/map_data/definitions.txt",
    "game/in_game/map_data/named_locations/00_default.txt",
    "game/in_game/map_data/location_templates.txt",
    "game/in_game/map_data/locations.png",
    "game/in_game/map_data/rivers.png",
    "game/in_game/map_data/adjacencies.csv",
    "game/in_game/map_data/ports.csv",
    "game/in_game/gfx/terrain2/heightmap.png",
    "game/in_game/gfx/terrain2/biomes.png",
)


@dataclass(frozen=True, slots=True)
class MissingContractFileError(Exception):
    """A required source file for the fingerprint is absent."""

    relative_path: str

    @override
    def __str__(self) -> str:
        return f"Missing map-contract file: {self.relative_path}"


@dataclass(frozen=True, slots=True)
class FileFingerprint:
    """A stable digest, with no copied game bytes."""

    path: str
    size: int
    sha256: str


def fingerprint(game_dir: Path) -> tuple[FileFingerprint, ...]:
    """Hash selected map inputs in a fixed order using bounded memory."""
    records: list[FileFingerprint] = []
    for relative in CONTRACT_FILES:
        source = game_dir / relative
        if not source.is_file():
            raise MissingContractFileError(relative)
        with source.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        records.append(FileFingerprint(relative, source.stat().st_size, digest))
    return tuple(records)
