"""Made land kept on disk, so it is not made twice (ADR 0010).

Three kinds of entry live under the cache folder. A *world* entry holds the finished cells and
relief of a continent, so rerolling its resources or peoples skips the geography. A *stage*
entry holds only the land stage (land, ocean and lake masks) of a sketched continent
(``rnw.app.candidates``), so the world made from the chosen sketch starts from the land the
player saw instead of drawing it again. A *canvas* entry holds the area of the game's map that
a New World replaces (``rnw.eu5_canvas.select_canvas``), which depends only on the map's files
and two settings. Each is keyed by everything that shapes it, the generator's own code
included; an entry is the same data the generator would make, never an approximation. Each
kind keeps its most recently used entries and removes the rest.
"""

# NumPy stubs type array shapes, loaded archives and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import contextlib
import hashlib
import os
import re
import shutil
import sys
import time
import zipfile
import zlib
from dataclasses import replace
from math import prod
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import TYPE_CHECKING, Final

import numpy as np

import rnw
from rnw import __version__, epoch
from rnw.eu5_canvas import Canvas, OceanRemainder, select_canvas
from rnw.eu5_pacific import IslandGroup
from rnw.islands import Footprint
from rnw.model import CellClass
from rnw.newworld import NewWorld, generate_new_world, seal_pockets
from rnw.progress import checkpoint

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

    from rnw.eu5_map import Eu5Map
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
    "moves",
    "edges",
)


# Land stages of sketched continents live in this folder of the cache.
STAGES: Final[str] = "stages"
STAGE_SUFFIX: Final[str] = ".land"
# Sketched land kept for the worlds made from it: two batches of the most sketches.
KEPT_STAGES: Final[int] = 24
# Finished continents kept for rerolls, about 0.6 GiB each on the continents preset; the
# cache had no bound and grew by one per world (13 GiB on the owner's machine, 2026-11-07).
KEPT_WORLDS: Final[int] = 4
# An entry used this recently stays whatever its rank: another copy of the generator sharing
# the data folder may be reading it.
RECENT_SECONDS: Final[int] = 3600
ENTRY: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}")
STAGE_MASKS: Final[tuple[str, ...]] = ("land", "ocean", "lakes")
# Canvases of the game's map live in this folder: one per band, Pacific side and game version.
CANVASES: Final[str] = "canvases"
CANVAS_SUFFIX: Final[str] = ".canvas.npz"
KEPT_CANVASES: Final[int] = 4
# Files of the generator's own code that its identity covers (``code_identity``).
CODE_SUFFIXES: Final[frozenset[str]] = frozenset({".py", ".pyc", ".so", ".pyd"})
_CODE: list[str] = []

type LandStage = tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_]]


class CacheError(ValueError):
    pass


def _hash_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def cache_key(  # noqa: PLR0913, PLR0917 - the key covers each independent geography input.
    domain: NDArray[np.bool_],
    seed: int,
    settings: NewWorldSettings,
    drawn: NDArray[np.bool_] | None,
    sea_bands: NDArray[np.bool_] | None = None,
    groups: Sequence[Footprint] = (),
    template: NDArray[np.bool_] | None = None,
) -> str:
    # The first number is the layout of the construction (8: the Americas' template of Omerika;
    # 7: the water band along the canvas's boundary and the crossings as chains of cells); the
    # code's identity keeps an entry made by earlier code from being read when the land or the sea
    # cells change inside an epoch. The template matters only to a world that uses it.
    spec = (
        8,
        epoch.CURRENT,
        code_identity(),
        seed,
        replace(settings, precious_permille=0),
        domain.shape,
        len(groups),
    )
    digest = hashlib.sha256(repr(spec).encode("ascii"))
    for group in groups:
        digest.update(group.rows.tobytes())
        digest.update(group.columns.tobytes())
    for raster in (domain, drawn, sea_bands, template if settings.template_permille else None):
        digest.update(b"none" if raster is None else b"raster")
        if raster is not None:
            for row in range(0, len(raster), STRIP):
                checkpoint()
                digest.update(raster[row : row + STRIP].tobytes())
    return digest.hexdigest()


def code_identity() -> str:
    """SHA-256 of the generator's code as it is installed: every module and the native library.

    A release keeps one identity; in a working copy any change of the code is a new one, so no
    entry made by earlier code is read. Computed once per process.
    """
    if _CODE:
        return _CODE[0]
    root = Path(rnw.__file__).parent
    digest = hashlib.sha256(__version__.encode("ascii"))
    files = sorted(
        item
        for item in root.rglob("*")
        if item.suffix in CODE_SUFFIXES and "__pycache__" not in item.parts and item.is_file()
    )
    for item in files:
        digest.update(item.relative_to(root).as_posix().encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(item.read_bytes()).digest())
    _CODE.append(digest.hexdigest())
    return _CODE[0]


def canvas_key(game_map: Eu5Map, band_px: int, *, expanded: bool) -> str:
    """The identity of a canvas: the digests of the map's files, the two settings and the code."""
    spec = (2, code_identity(), tuple(game_map.inputs), len(game_map.keys), band_px, expanded)
    return hashlib.sha256(repr(spec).encode("utf-8")).hexdigest()


def get_canvas(cache: Path | None, game_map: Eu5Map, band_px: int, *, expanded: bool) -> Canvas:
    """``select_canvas`` of the map, read from the cache when it was selected before."""
    if cache is None:
        return select_canvas(game_map, band_px, expanded=expanded)
    target = cache / CANVASES / f"{canvas_key(game_map, band_px, expanded=expanded)}{CANVAS_SUFFIX}"
    if target.exists():
        canvas = _read_canvas(target)
        _touch(target)
        return canvas
    canvas = select_canvas(game_map, band_px, expanded=expanded)
    _write_canvas(target, canvas)
    prune(cache)
    return canvas


def _flat(
    parts: Sequence[NDArray[np.integer]], dtype: type[np.integer], width: int = 0
) -> tuple[NDArray[np.integer], NDArray[np.int64]]:
    """Arrays of one kind joined, with the length of each."""
    counts = np.array([len(part) for part in parts], dtype=np.int64)
    shape = (0, width) if width else (0,)
    joined: NDArray[np.integer] = np.concatenate(parts) if parts else np.zeros(shape, dtype=dtype)
    return joined.astype(dtype, copy=False), counts


def _split(joined: NDArray[np.integer], counts: NDArray[np.int64]) -> list[NDArray[np.integer]]:
    ends = np.cumsum(counts)
    return [
        joined[int(end) - int(count) : int(end)]
        for end, count in zip(ends.tolist(), counts.tolist(), strict=True)
    ]


def _write_canvas(target: Path, canvas: Canvas) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    runs, run_counts = _flat([part.runs for part in canvas.ocean_parts], np.int64, 3)
    rows, footprint_counts = _flat([item.rows for item in canvas.footprints], np.int32)
    columns, _ = _flat([item.columns for item in canvas.footprints], np.int32)
    locations, location_counts = _flat(
        [np.array(group.locations, dtype=np.int64) for group in canvas.groups], np.int64
    )
    zones, zone_counts = _flat(
        [np.array(group.zones, dtype=np.int64) for group in canvas.groups], np.int64
    )
    arrays: dict[str, NDArray[np.generic]] = {
        "scalars": np.array(
            [canvas.roll, canvas.col0, *canvas.shape, int(canvas.expanded), *canvas.mask.shape],
            dtype=np.int64,
        ),
        "mask": np.packbits(canvas.mask, axis=None),
        "has_template": np.array([canvas.template is not None]),
        "template": np.packbits(canvas.template, axis=None)
        if canvas.template is not None
        else np.zeros(0, dtype=np.uint8),
        "removed": canvas.removed,
        "trimmed": canvas.trimmed,
        "has_opened": np.array([canvas.opened is not None]),
        "opened": canvas.opened if canvas.opened is not None else np.zeros(0, dtype=np.bool_),
        "ocean_sources": np.array([part.source for part in canvas.ocean_parts], dtype=np.int64),
        "ocean_pixels": np.array([part.pixels for part in canvas.ocean_parts], dtype=np.int64),
        "ocean_runs": runs,
        "ocean_run_counts": run_counts,
        "group_locations": locations,
        "group_location_counts": location_counts,
        "group_zones": zones,
        "group_zone_counts": zone_counts,
        "footprint_rows": rows,
        "footprint_columns": columns,
        "footprint_counts": footprint_counts,
        "moves": np.array(canvas.moves, dtype=np.int64).reshape(-1, 2),
    }
    with NamedTemporaryFile(
        dir=target.parent, prefix=".canvas-", suffix=".npz", delete=False
    ) as handle:
        np.savez(handle, **arrays)  # pyright: ignore[reportArgumentType]
        temporary = Path(handle.name)
    _ = temporary.replace(target)


def _read_canvas(target: Path) -> Canvas:
    try:
        with np.load(target, allow_pickle=False) as data:
            found = {name: data[name] for name in data.files}
        roll, col0, rows, width, expanded, mask_rows, mask_columns = (
            int(value) for value in found["scalars"].tolist()
        )
        mask = np.unpackbits(found["mask"], count=mask_rows * mask_columns).astype(np.bool_)
        template = (
            np.unpackbits(found["template"], count=mask_rows * mask_columns)
            .astype(np.bool_)
            .reshape(mask_rows, mask_columns)
            if bool(found["has_template"][0])
            else None
        )
        footprint_rows = _split(found["footprint_rows"], found["footprint_counts"])
        footprint_columns = _split(found["footprint_columns"], found["footprint_counts"])
        locations = _split(found["group_locations"], found["group_location_counts"])
        zones = _split(found["group_zones"], found["group_zone_counts"])
        runs = _split(found["ocean_runs"], found["ocean_run_counts"])
        return Canvas(
            roll=roll,
            col0=col0,
            mask=mask.reshape(mask_rows, mask_columns),
            shape=(rows, width),
            removed=found["removed"].astype(np.bool_),
            trimmed=found["trimmed"].astype(np.bool_),
            ocean_parts=tuple(
                OceanRemainder(int(source), part.astype(np.int64).reshape(-1, 3), int(pixels))
                for source, part, pixels in zip(
                    found["ocean_sources"].tolist(),
                    runs,
                    found["ocean_pixels"].tolist(),
                    strict=True,
                )
            ),
            groups=tuple(
                IslandGroup(
                    tuple(int(item) for item in place.tolist()),
                    tuple(int(item) for item in zone.tolist()),
                )
                for place, zone in zip(locations, zones, strict=True)
            ),
            footprints=tuple(
                Footprint(row.astype(np.int32), column.astype(np.int32))
                for row, column in zip(footprint_rows, footprint_columns, strict=True)
            ),
            moves=tuple((int(down), int(across)) for down, across in found["moves"].tolist()),
            opened=found["opened"].astype(np.bool_) if bool(found["has_opened"][0]) else None,
            expanded=bool(expanded),
            template=template,
        )
    except (
        OSError,
        EOFError,
        zipfile.BadZipFile,
        ValueError,
        KeyError,
        TypeError,
        IndexError,
    ) as error:
        message = f"Land cache {target} is damaged; remove this entry and retry: {error}"
        raise CacheError(message) from error


def domain_digest(domain: NDArray[np.bool_], template: NDArray[np.bool_] | None = None) -> str:
    """SHA-256 of a canvas mask and its shape, read in strips; with the Americas' template (the
    land stage of Omerika reads it) the template's raster follows."""
    digest = hashlib.sha256(repr(domain.shape).encode("ascii"))
    for raster in (domain, template):
        if raster is None:
            continue
        for row in range(0, len(raster), STRIP):
            checkpoint()
            digest.update(raster[row : row + STRIP].tobytes())
    return digest.hexdigest()


def stage_key(digest: str, seed: int, settings: NewWorldSettings) -> str:
    """The identity of a land stage: the canvas (``domain_digest``), the seed and the settings.

    The land stage reads nothing else (``rnw.newworld.land_stage``): neither the sea bands nor
    the island groups, which the cells are built round afterwards. The generator's code is part
    of it (``code_identity``), as a change of the code can change the land within an epoch.
    """
    spec = (1, epoch.CURRENT, code_identity(), seed, replace(settings, precious_permille=0), digest)
    return hashlib.sha256(repr(spec).encode("ascii")).hexdigest()


def stage_path(cache: Path, key: str) -> Path:
    return cache / STAGES / f"{key}{STAGE_SUFFIX}"


def keep_stage(cache: Path, key: str, stage: LandStage) -> None:
    """Write a land stage, packed and compressed, under ``key``; an existing one stays."""
    target = stage_path(cache, key)
    if target.exists():
        _touch(target)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shape = stage[0].shape
    header = f"{shape[0]} {shape[1]}\n".encode("ascii")
    parts = [zlib.compress(np.packbits(mask, axis=None).tobytes(), 1) for mask in stage]
    sizes = " ".join(str(len(part)) for part in parts).encode("ascii") + b"\n"
    with NamedTemporaryFile(dir=target.parent, prefix=".stage-", delete=False) as handle:
        _ = handle.write(header + sizes + b"".join(parts))
        temporary = Path(handle.name)
    _ = temporary.replace(target)


def read_stage(cache: Path, key: str, shape: tuple[int, int]) -> LandStage | None:
    """The land stage kept under ``key``, or None if there is none; a damaged one fails."""
    target = stage_path(cache, key)
    try:
        data = target.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as error:
        message = f"Land cache {target} cannot be read; remove this entry and retry: {error}"
        raise CacheError(message) from error
    try:
        header, sizes, body = data.split(b"\n", 2)
        rows, columns = (int(value) for value in header.split())
        lengths = [int(value) for value in sizes.split()]
        if (
            (rows, columns) != shape
            or len(lengths) != len(STAGE_MASKS)
            or sum(lengths) != len(body)
        ):
            raise CacheError(target)
        masks: list[NDArray[np.bool_]] = []
        start = 0
        for length in lengths:
            packed = np.frombuffer(zlib.decompress(body[start : start + length]), dtype=np.uint8)
            start += length
            mask = np.unpackbits(packed, count=rows * columns).astype(np.bool_)
            masks.append(mask.reshape(shape))
    except (ValueError, zlib.error) as error:
        message = f"Land cache {target} is damaged; remove this entry and retry: {error}"
        raise CacheError(message) from error
    _touch(target)
    return masks[0], masks[1], masks[2]


def prune(cache: Path) -> None:
    """Keep the most recently used entries of each kind and remove the others.

    An entry counts as used when it is written or read. Entries used within the last hour
    stay; nothing outside the cache's own names is touched.
    """
    now = time.time()
    worlds = [item for item in _entries(cache) if item.is_dir() and ENTRY.fullmatch(item.name)]
    stages = [
        item
        for item in _entries(cache / STAGES)
        if item.suffix == STAGE_SUFFIX and ENTRY.fullmatch(item.stem)
    ]
    canvases = [
        item
        for item in _entries(cache / CANVASES)
        if item.name.endswith(CANVAS_SUFFIX)
        and ENTRY.fullmatch(item.name.removesuffix(CANVAS_SUFFIX))
    ]
    for found, kept in ((worlds, KEPT_WORLDS), (stages, KEPT_STAGES), (canvases, KEPT_CANVASES)):
        dated = sorted(((_used(item), item) for item in found), reverse=True)
        for used, item in dated[kept:]:
            if now - used < RECENT_SECONDS:
                continue
            with contextlib.suppress(OSError):
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()


def _entries(folder: Path) -> list[Path]:
    try:
        return list(folder.iterdir())
    except OSError:
        return []


def _used(item: Path) -> float:
    try:
        return item.stat().st_mtime
    except OSError:
        return 0.0


def _touch(item: Path) -> None:
    with contextlib.suppress(OSError):
        os.utime(item)


def get_world(  # noqa: PLR0913 - the cache key includes each independent geography input.
    cache: Path | None,
    domain: NDArray[np.bool_],
    *,
    seed: int,
    settings: NewWorldSettings,
    drawn: NDArray[np.bool_] | None,
    sea_bands: NDArray[np.bool_] | None = None,
    groups: Sequence[Footprint] = (),
    template: NDArray[np.bool_] | None = None,
) -> NewWorld:
    """The cells and relief of the continent, read from the cache when it was made before.

    A world not yet made starts from the land stage of its sketch when one is kept.
    ``template`` is the Americas on the canvas (``Canvas.template``) that Omerika reads.
    """
    key = (
        None
        if cache is None
        else cache_key(domain, seed, settings, drawn, sea_bands, groups, template)
    )
    target = None if cache is None or key is None else cache / key
    if target is not None and target.exists():
        world = _read(target, domain.shape)
        _touch(target)
        return world
    stage = None
    if cache is not None and drawn is None:
        shape = (int(domain.shape[0]), int(domain.shape[1]))
        digest = domain_digest(domain, template if settings.template_permille else None)
        stage = read_stage(cache, stage_key(digest, seed, settings), shape)
    world = seal_pockets(
        generate_new_world(
            domain.copy(),
            seed=seed,
            settings=settings,
            drawn=drawn,
            sea_bands=sea_bands,
            groups=groups,
            stage=stage,
            template=template,
        )
    )
    if target is not None and cache is not None:
        _write(target, world)
        prune(cache)
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
        "moves": world.moves,
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
            moves=_i64(target, "moves", ((target / "moves").stat().st_size // 16, 2)),
        )
    except (OSError, ValueError, TypeError, KeyError, IndexError) as error:
        message = f"Land cache {target} is damaged; remove this entry and retry: {error}"
        raise CacheError(message) from error
