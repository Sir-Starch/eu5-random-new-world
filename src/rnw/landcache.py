from __future__ import annotations

import hashlib
import sys
from dataclasses import replace
from math import prod
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import epoch
from rnw.model import CellClass
from rnw.newworld import NewWorld, generate_new_world, seal_pockets
from rnw.progress import checkpoint

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.settings import NewWorldSettings

STRIP: Final[int] = 256
KINDS: Final[tuple[CellClass, ...]] = tuple(CellClass)
ARRAYS: Final[tuple[str, ...]] = (
    "labels",
    "elevation",
    "pixels",
    "centroids",
    "interior",
    "mean_elevation",
    "spread",
    "edges",
)


class CacheError(ValueError):
    pass


def _hash_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def cache_key(
    domain: NDArray[np.bool_],
    seed: int,
    settings: NewWorldSettings,
    drawn: NDArray[np.bool_] | None,
    sea_bands: NDArray[np.bool_] | None = None,
) -> str:
    spec = (4, epoch.CURRENT, seed, replace(settings, precious_permille=0), domain.shape)
    digest = hashlib.sha256(repr(spec).encode("ascii"))
    for raster in (domain, drawn, sea_bands):
        digest.update(b"none" if raster is None else b"raster")
        if raster is not None:
            for row in range(0, len(raster), STRIP):
                checkpoint()
                digest.update(raster[row : row + STRIP].tobytes())
    return digest.hexdigest()


def get_world(  # noqa: PLR0913 - the cache key includes each independent geography input.
    cache: Path | None,
    domain: NDArray[np.bool_],
    *,
    seed: int,
    settings: NewWorldSettings,
    drawn: NDArray[np.bool_] | None,
    sea_bands: NDArray[np.bool_] | None = None,
) -> NewWorld:
    target = None if cache is None else cache / cache_key(domain, seed, settings, drawn, sea_bands)
    if target is not None and target.exists():
        return _read(target, domain.shape)
    world = seal_pockets(
        generate_new_world(
            domain.copy(),
            seed=seed,
            settings=settings,
            drawn=drawn,
            sea_bands=sea_bands,
        )
    )
    if target is not None:
        _write(target, world)
    return world


def _write(target: Path, world: NewWorld) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    rasters = {"labels": world.labels, "elevation": world.elevation}
    tables = {
        "pixels": world.pixels,
        "centroids": world.centroids,
        "interior": world.interior,
        "mean_elevation": world.mean_elevation,
        "spread": world.spread,
    }
    with TemporaryDirectory(prefix=".land-", dir=target.parent) as temporary:
        stage = Path(temporary)
        for name, raster in rasters.items():
            checkpoint()
            raster.tofile(stage / name)
        for name, table in tables.items():
            table.tofile(stage / name)
        np.array(world.edges, dtype=np.int32).tofile(stage / "edges")
        _ = (stage / "classes").write_bytes(bytes(KINDS.index(kind) for kind in world.classes))
        lines = [f"{file.name}\t{_hash_file(file)}\n" for file in sorted(stage.iterdir())]
        _ = (stage / "hashes.txt").write_text("".join(lines), encoding="ascii")
        _ = stage.rename(target)


def _i32(target: Path, name: str, shape: tuple[int, ...]) -> NDArray[np.int32]:
    path = target / name
    if path.stat().st_size != prod(shape) * np.dtype(np.int32).itemsize:
        raise CacheError(path)
    return np.fromfile(path, dtype=np.int32).reshape(shape)


def _i64(target: Path, name: str, shape: tuple[int, ...]) -> NDArray[np.int64]:
    path = target / name
    if path.stat().st_size != prod(shape) * np.dtype(np.int64).itemsize:
        raise CacheError(path)
    return np.fromfile(path, dtype=np.int64).reshape(shape)


def _read(target: Path, shape: tuple[int, ...]) -> NewWorld:
    try:
        lines = (target / "hashes.txt").read_text(encoding="ascii").splitlines()
        hashes = dict(line.split("\t", maxsplit=1) for line in lines)
        expected = {*ARRAYS, "classes"}
        if set(hashes) != expected or any(
            _hash_file(target / name) != hashes[name] for name in expected
        ):
            raise CacheError(target)
        classes = tuple(KINDS[code] for code in (target / "classes").read_bytes())
        count = len(classes)
        edge_bytes = (target / "edges").stat().st_size
        if edge_bytes % 8:
            raise CacheError(target)
        data = (target / "edges").read_bytes()
        edges = tuple(
            (
                int.from_bytes(data[index : index + 4], sys.byteorder, signed=True),
                int.from_bytes(data[index + 4 : index + 8], sys.byteorder, signed=True),
            )
            for index in range(0, edge_bytes, 8)
        )
        return NewWorld(
            labels=_i32(target, "labels", shape),
            classes=classes,
            elevation=_i32(target, "elevation", shape),
            pixels=_i64(target, "pixels", (count,)),
            centroids=_i64(target, "centroids", (count, 2)),
            interior=_i64(target, "interior", (count, 2)),
            mean_elevation=_i64(target, "mean_elevation", (count,)),
            spread=_i64(target, "spread", (count,)),
            edges=edges,
        )
    except (OSError, ValueError, TypeError, KeyError, IndexError) as error:
        message = f"Land cache {target} is damaged; remove this entry and retry: {error}"
        raise CacheError(message) from error
