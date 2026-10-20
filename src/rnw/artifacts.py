"""Safe, reproducible output staging shared by the synthetic and EU5 writers."""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Buffer, Iterator, MutableMapping
from contextlib import contextmanager
from typing import TYPE_CHECKING, Final, Self, override

import numpy as np

from rnw.model import CellClass, World
from rnw.png import COLOR_RGB, encode_png
from rnw.settings import canonical_json

if TYPE_CHECKING:
    import re
    from collections.abc import Generator
    from pathlib import Path

    from numpy.typing import NDArray

GENERATED_DIR: Final[str] = "generated"
CLASS_COLORS: Final[dict[CellClass, tuple[int, int, int]]] = {
    CellClass.LAND: (96, 160, 72),
    CellClass.SEA: (32, 64, 150),
    CellClass.LAKE: (90, 150, 220),
    CellClass.WASTELAND: (128, 128, 128),
    CellClass.NON_OWNABLE: (200, 180, 90),
}


class OutputPathError(ValueError):
    """The requested output location is unsafe or already used."""


def check_new_output(
    output: Path,
    pattern: re.Pattern[str],
    game_dir: Path | None = None,
    *,
    replace: bool = False,
) -> None:
    """Require a directory named by ``pattern`` directly under ``generated/``.

    The path must not exist unless ``replace`` is set, must not be inside the game
    installation and must not collide with a leftover staging directory.
    """
    resolved = output.resolve()
    if game_dir is not None and resolved.is_relative_to(game_dir.resolve()):
        message = "Output path must be outside the game installation"
        raise OutputPathError(message)
    if resolved.parent.name != GENERATED_DIR:
        message = f"Output must be a new directory directly under {GENERATED_DIR}/"
        raise OutputPathError(message)
    if pattern.fullmatch(resolved.name) is None:
        message = f"Output directory name must match {pattern.pattern}"
        raise OutputPathError(message)
    if resolved.exists() and not (replace and resolved.is_dir()):
        message = f"Refusing to overwrite existing output: {resolved}"
        raise OutputPathError(message)
    for leftover in (staging_path(resolved), spool_path(resolved)):
        if leftover.exists():
            message = f"Refusing to overwrite a leftover staging directory: {leftover}"
            raise OutputPathError(message)


def staging_path(output: Path) -> Path:
    """Hidden sibling used while an output is incomplete."""
    return output.parent / f".{output.name}.partial"


@contextmanager
def staged(output: Path) -> Generator[Path]:
    """Yield a fresh staging directory; on success it replaces ``output``.

    An existing ``output`` (allowed only by ``check_new_output(..., replace=True)``) is
    moved aside first and deleted after the new directory is in place.
    """
    stage = staging_path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage.mkdir()
    try:
        yield stage
    except BaseException:
        shutil.rmtree(stage)
        raise
    swap_in(stage, output)


def swap_in(new: Path, target: Path) -> None:
    """Put ``new`` at ``target``, removing a previous ``target`` only after the move."""
    old = target.parent / f".{target.name}.old"
    if old.exists():
        shutil.rmtree(old)
    if target.exists():
        _ = target.rename(old)
    _ = new.rename(target)
    if old.exists():
        shutil.rmtree(old)


def sha256(data: bytes) -> str:
    """Hex SHA-256 of bytes."""
    return hashlib.sha256(data).hexdigest()


def pixel_digest(pixels: NDArray[np.uint8], mode: str) -> str:
    """Encoding-independent digest of decoded pixels."""
    header = f"{mode}:{pixels.shape[1]}x{pixels.shape[0]}\n".encode("ascii")
    return sha256(header + np.ascontiguousarray(pixels).tobytes())


def spool_path(output: Path) -> Path:
    """Hidden sibling where finished files wait for the bundle to be written."""
    return output.parent / f".{output.name}.spool"


class Spool(MutableMapping[str, Buffer]):
    """Files kept on disk as they are made, so the large ones do not wait in memory.

    It behaves as a mapping from a bundle-relative path to the file's bytes: storing a
    file writes it (and hashes it) at once, reading one reads it back. ``install`` moves
    every file into the staged bundle with its manifest record. Use as a context manager;
    leaving it removes whatever was not installed.
    """

    def __init__(self, root: Path) -> None:
        self._root: Path = root
        self._records: dict[str, tuple[int, str]] = {}

    def __enter__(self) -> Self:
        if self._root.exists():
            message = f"Refusing to reuse a leftover spool directory: {self._root}"
            raise OutputPathError(message)
        self._root.mkdir(parents=True)
        return self

    def __exit__(self, *_exc: object) -> None:
        shutil.rmtree(self._root, ignore_errors=True)

    @override
    def __setitem__(self, relative: str, data: Buffer) -> None:
        target = self._root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        view = memoryview(data)
        with target.open("wb") as handle:
            _ = handle.write(view)
        self._records[relative] = (view.nbytes, hashlib.sha256(view).hexdigest())

    @override
    def __getitem__(self, relative: str) -> bytes:
        if relative not in self._records:
            raise KeyError(relative)
        return (self._root / relative).read_bytes()

    @override
    def __delitem__(self, relative: str) -> None:
        del self._records[relative]
        (self._root / relative).unlink()

    @override
    def __iter__(self) -> Iterator[str]:
        return iter(self._records)

    @override
    def __len__(self) -> int:
        return len(self._records)

    def install(self, stage: Path, prefix: str) -> list[dict[str, object]]:
        """Move the files to ``stage/prefix/...``; return their manifest records, sorted."""
        records: list[dict[str, object]] = []
        for relative in sorted(self._records):
            size, digest = self._records[relative]
            target = stage / prefix / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            _ = (self._root / relative).replace(target)
            records.append({"path": f"{prefix}/{relative}", "size": size, "sha256": digest})
        self._records.clear()
        return records


def write_bytes(root: Path, relative: str, data: bytes) -> dict[str, object]:
    """Write one output file and return its manifest record."""
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    _ = target.write_bytes(data)
    return {"path": relative, "size": len(data), "sha256": sha256(data)}


def color_raster(world: World) -> NDArray[np.uint8]:
    """RGB location raster from cell colours."""
    colors = np.array([cell.color for cell in world.cells], dtype=np.int64)[world.labels]
    return np.stack([(colors >> 16) & 0xFF, (colors >> 8) & 0xFF, colors & 0xFF], axis=-1).astype(
        np.uint8
    )


def class_raster(world: World) -> NDArray[np.uint8]:
    """RGB preview of land/water classes."""
    palette = np.array([CLASS_COLORS[cell.cell_class] for cell in world.cells], dtype=np.uint8)
    return palette[world.labels]


def cells_document(world: World) -> list[dict[str, object]]:
    """Cell table in label order for the synthetic bundle."""
    return [
        {
            "index": index,
            "key": cell.key,
            "color": f"{cell.color:06x}",
            "class": cell.cell_class.value,
            "parents": list(cell.parents.chain()),
            "protected": cell.protected,
        }
        for index, cell in enumerate(world.cells)
    ]


def write_synthetic_bundle(
    world: World, spec: dict[str, object], metrics: dict[str, int], output: Path
) -> dict[str, object]:
    """Write a fully byte-deterministic synthetic world bundle."""
    with staged(output) as stage:
        records = [
            write_bytes(
                stage,
                "locations.png",
                encode_png(color_raster(world), color_type=COLOR_RGB, compression="stored"),
            ),
            write_bytes(
                stage,
                "preview.png",
                encode_png(class_raster(world), color_type=COLOR_RGB, compression="stored"),
            ),
            write_bytes(stage, "cells.json", canonical_json(cells_document(world)).encode()),
            write_bytes(stage, "metrics.json", canonical_json(metrics).encode()),
            write_bytes(stage, "settings.json", canonical_json(spec["settings"]).encode()),
        ]
        manifest: dict[str, object] = {
            "schema": 1,
            "kind": "synthetic-world",
            "spec": spec,
            "edges": len(world.edges()),
            "files": records,
        }
        _ = write_bytes(stage, "manifest.json", canonical_json(manifest).encode())
    return manifest
