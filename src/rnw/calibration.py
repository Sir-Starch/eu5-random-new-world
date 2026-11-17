"""Exact reusable calibration of the original installed map, independent of a world's seed.

A cache hit verifies every recorded file's content and every read directory's inventory.
The original map's content fingerprints and the code identity select the entry; moved maps
must never be passed here. Arrays are bounded, checked, non-pickle archives, written atomically.
"""

# NumPy archive access is typed as Any.
# pyright: reportAny=false
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import zipfile
from dataclasses import fields
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import inputs
from rnw.eu5_biomes import SizeModel
from rnw.landcache import CacheError, code_identity
from rnw.parallel import worker_count
from rnw.record import Manifest
from rnw.timing import span

if TYPE_CHECKING:
    from collections.abc import Callable

    from rnw.eu5_map import Eu5Map

SCHEMA: Final[int] = 1
LIMIT: Final[int] = 64 << 20
KEPT: Final[int] = 4
BOOL_FIELDS: Final = frozenset({"dry", "vote_dry"})


def get_sizes(
    cache: Path | None, game_dir: Path, original: Eu5Map, make: Callable[[], SizeModel]
) -> SizeModel:
    """The original map's size model, recomputing after any dependency changes."""
    if cache is None:
        return make()
    key = hashlib.sha256(
        repr((SCHEMA, code_identity(), original.inputs, original.labels.shape)).encode("utf-8")
    ).hexdigest()
    folder = cache / "calibration"
    target = folder / f"{key}.npz"
    if target.exists():
        with span("size calibration cache read"):
            model, manifest = _read(target)
            if inputs.compare(game_dir, manifest, workers=worker_count(4)).same:
                inputs.note_manifest(game_dir, manifest)
                os.utime(target, None)
                return model
    with span("size calibration compute"), inputs.recording(game_dir) as recorder:
        model = make()
        manifest = recorder.manifest(game_dir, workers=worker_count(4))
    _write(target, model, manifest)
    for stale in sorted(folder.glob("*.npz"), key=lambda p: p.stat().st_mtime, reverse=True)[KEPT:]:
        stale.unlink(missing_ok=True)
    return model


def _read(path: Path) -> tuple[SizeModel, Manifest]:
    try:
        with zipfile.ZipFile(path) as archive:
            if sum(item.file_size for item in archive.infolist()) > LIMIT:
                message = "Size calibration cache exceeds its memory limit"
                raise CacheError(message)
        with np.load(path, allow_pickle=False) as archive:
            names = {field.name for field in fields(SizeModel)}
            if set(archive.files) != names | {"metadata"}:
                message = "Size calibration cache has unexpected arrays"
                raise CacheError(message)
            metadata = json.loads(archive["metadata"].tobytes().decode("utf-8"))
            arrays = {name: archive[name] for name in names}
            if metadata["schema"] != SCHEMA or any(
                a.dtype != (np.bool_ if name in BOOL_FIELDS else np.int64)
                for name, a in arrays.items()
            ):
                message = "Size calibration cache has an invalid schema or dtype"
                raise CacheError(message)
            model = SizeModel(**arrays)
            if model.digest() != metadata["digest"]:
                message = "Size calibration cache failed its checksum"
                raise CacheError(message)
            manifest = Manifest.from_json(metadata["inputs"])
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, EOFError) as error:
        message = f"Cannot read size calibration cache {path.name}: {error}"
        raise CacheError(message) from error
    return model, manifest


def _write(path: Path, model: SizeModel, manifest: Manifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = json.dumps(
        {"schema": SCHEMA, "digest": model.digest(), "inputs": manifest.to_json()},
        sort_keys=True,
    ).encode("utf-8")
    arrays = {field.name: getattr(model, field.name) for field in fields(SizeModel)}
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            np.savez_compressed(stream, metadata=np.frombuffer(metadata, dtype=np.uint8), **arrays)
        _ = temporary.replace(path)
    finally:
        if temporary is not None:
            with contextlib.suppress(FileNotFoundError):
                temporary.unlink()
