"""Vegetation and ground-clutter instances for generated land (EU5 1.4.1).

Trees, grass, reeds and small ground decals are pre-generated instance lists: binary
files of 40-byte records (x, y, z, rotation quaternion, uniform scale; x and z in
location pixels with z up, y 0) or inline ``transform`` blocks of the same ten numbers
[V-LOCAL C52]. Instances inside the canvas belong to the removed Americas and are
dropped. New ones are sampled per material pixel with the Old World density of the
pixel's class (vegetation, climate, topography and material slot), so forest trees
stand on forest variation slots and avoid coasts, rivers and border bands as in vanilla
[V-EXEC C52]. Each new instance copies rotation and scale from a vanilla record of the
same file, so no floating-point trigonometry is involved and output is deterministic.
Densities are scaled down together when the generated land would carry more instances
than the removed Americas did, because the engine caps the objects of a game (C95).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import _native
from rnw.parallel import band_rows
from rnw.progress import checkpoint
from rnw.rng import MASK64, derive_seed

if TYPE_CHECKING:
    from collections.abc import Buffer, MutableMapping
    from pathlib import Path

    from numpy.typing import NDArray

MAP_OBJECTS: Final[str] = "game/in_game/gfx/map/map_objects"
RECORD_FLOATS: Final[int] = 10
SLOT_CLASSES: Final[int] = 18
NO_SLOT: Final[int] = 17
DENSITY_BITS: Final[int] = 24
# EU5 refuses a game with more than 2**24 mesh map objects and drops the objects loaded
# last, which left the combat and unit-stack locators incomplete [V-GAME 1.4.2, C95].
# Vanilla stays below that cap, so the new vegetation may not outnumber the instances
# of the removed Americas; one percent stays unused.
BUDGET_PERMILLE: Final[int] = 990
PERMILLE: Final[int] = 1000
MIN_PIXELS: Final[int] = 20_000
# The canvas pixels are read a strip of location rows at a time: four 32-bit values for each
# of the four material pixels of a location pixel, doubled for the copies in flight.
PIXEL_ROW_BYTES: Final[int] = 4 * 16 * 2
STRIP_FLOOR: Final[int] = 8
STRIP_CEILING: Final[int] = 256
INLINE: Final[re.Pattern[str]] = re.compile(
    r'(object=\{[^{}]*?name="([^"]+)"[^{}]*?count=)(\d+)(\s*transform=")([^"]*)("\})', re.DOTALL
)
BIN_REFERENCE: Final[re.Pattern[str]] = re.compile(
    r'transform_bin_file="gfx/map/map_objects/([^"]+\.bin)"'
)
GENERATOR: Final[re.Pattern[str]] = re.compile(r"_generator_|^woods_cherry_")


class ObjectBudgetError(ValueError):
    """New instances that outnumber the instances they replace."""


@dataclass(frozen=True, slots=True, eq=False)
class InstanceSet:
    """One object's instances: where they come from and their records."""

    path: str
    name: str
    records: NDArray[np.float32]


def _bin_sets(game_dir: Path) -> list[InstanceSet]:
    root = game_dir / MAP_OBJECTS
    names: set[str] = set()
    for text_path in [*sorted(root.glob("*.txt")), *sorted((root / "generated").glob("*.txt"))]:
        names.update(BIN_REFERENCE.findall(text_path.read_text(encoding="utf-8-sig")))
    sets: list[InstanceSet] = []
    for name in sorted(names):
        if not GENERATOR.search(name) or not (root / name).is_file():
            continue
        data = np.frombuffer((root / name).read_bytes(), dtype="<f4")
        sets.append(
            InstanceSet(f"{MAP_OBJECTS}/{name}", name, data.reshape(-1, RECORD_FLOATS).copy())
        )
    return sets


def _inline_sets(game_dir: Path) -> list[InstanceSet]:
    sets: list[InstanceSet] = []
    for path in sorted((game_dir / MAP_OBJECTS / "generated").glob("*.txt")):
        text = path.read_text(encoding="utf-8-sig")
        relative = f"{MAP_OBJECTS}/generated/{path.name}"
        for match in INLINE.finditer(text):
            values = np.array(match.group(5).split(), dtype=np.float64)
            sets.append(
                InstanceSet(
                    relative, match.group(2), values.reshape(-1, RECORD_FLOATS).astype(np.float32)
                )
            )
    return sets


def _pixels(
    records: NDArray[np.float32], rows: int, columns: int
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Material-raster (two per location pixel) row and column of each record."""
    x = records[:, 0].astype(np.float64)
    z = records[:, 2].astype(np.float64)
    column = np.clip(np.floor(x * 2).astype(np.int64), 0, columns * 2 - 1)
    row = np.clip(np.floor((rows - z) * 2).astype(np.int64), 0, rows * 2 - 1)
    return row, column


@dataclass(frozen=True, slots=True, eq=False)
class PixelClasses:
    """Class per label and the label/material rasters that define pixel classes."""

    labels: NDArray[np.int32]
    materials: NDArray[np.uint8]
    label_class: NDArray[np.int64]
    label_coarse: NDArray[np.int64]
    calibrate: NDArray[np.bool_]


def _slot_class(materials: NDArray[np.uint8]) -> NDArray[np.int64]:
    slots = materials.astype(np.int64)
    return np.where(slots >= NO_SLOT, NO_SLOT, slots)


def pixel_counts(
    classes: PixelClasses, table: NDArray[np.int64], keys: int, mask: NDArray[np.bool_]
) -> NDArray[np.int64]:
    """Material pixels per key among labels where ``mask`` is true."""
    return _native.pixel_counts(
        np.ascontiguousarray(classes.labels, dtype=np.int32),
        np.ascontiguousarray(classes.materials, dtype=np.uint8),
        np.ascontiguousarray(table, dtype=np.int64),
        np.ascontiguousarray(mask, dtype=np.bool_),
        keys * SLOT_CLASSES,
    )


def _densities(
    instance: InstanceSet,
    classes: PixelClasses,
    fine_pixels: NDArray[np.int64],
    coarse_pixels: NDArray[np.int64],
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Instances per material pixel (fixed point) for fine and coarse keys."""
    rows, columns = classes.labels.shape
    row, column = _pixels(instance.records, rows, columns)
    label = classes.labels[row // 2, column // 2]
    keep = classes.calibrate[label]
    slot = _slot_class(classes.materials[row[keep], column[keep]])
    out: list[NDArray[np.int64]] = []
    for table, pixels in (
        (classes.label_class, fine_pixels),
        (classes.label_coarse, coarse_pixels),
    ):
        key = table[label[keep]] * SLOT_CLASSES + slot
        counts = np.bincount(key, minlength=pixels.size).astype(np.int64)
        out.append((counts << DENSITY_BITS) // np.maximum(pixels, 1))
    return out[0], out[1]


def budget_scale(
    tables: list[tuple[NDArray[np.int64], NDArray[np.int64]]],
    fine_count: NDArray[np.int64],
    coarse_count: NDArray[np.int64],
    budget: int,
) -> int:
    """Fixed-point factor (at most one) that keeps the expected new instances in ``budget``.

    ``fine_count`` and ``coarse_count`` count the canvas pixels sampled with each key's
    density, so the expected instances of a file are ``sum(count * density)``.
    """
    wanted = sum(int(fine_count @ fine) + int(coarse_count @ coarse) for fine, coarse in tables)
    wanted >>= DENSITY_BITS
    return min(1 << DENSITY_BITS, (budget << DENSITY_BITS) // max(wanted, 1))


def sample_instances(  # noqa: PLR0913 - sampling needs pixels, densities, donors and seed.
    pixels: tuple[NDArray[np.uint32], NDArray[np.uint32], NDArray[np.uint32], NDArray[np.uint32]],
    *,
    use_fine: NDArray[np.bool_],
    densities: tuple[NDArray[np.int64], NDArray[np.int64]],
    source: NDArray[np.float32],
    rows: int,
    key: int,
) -> NDArray[np.float32]:
    """Records for canvas pixels with fixed-point densities (expected count = density).

    ``pixels`` holds the rows, columns, fine keys and coarse keys of the pixels; a pixel
    with a fine key in ``use_fine`` takes the fine density, else its coarse key's.
    """
    return _native.sample_instances(
        *pixels,
        use_fine,
        *densities,
        np.ascontiguousarray(source, dtype=np.float32),
        key & MASK64,
        rows,
    )


def canvas_pixels(
    classes: PixelClasses, canvas: NDArray[np.bool_], first: int = 0, last: int | None = None
) -> tuple[NDArray[np.uint32], NDArray[np.uint32], NDArray[np.uint32], NDArray[np.uint32]]:
    """Row, column, fine key and coarse key of every material pixel of the canvas to fill.

    Only the location rows ``first`` to ``last`` are read; the rows returned are material
    rows of the whole raster, so the pixels of consecutive row ranges join into the pixels
    of the whole canvas.
    """
    start, stop, _ = slice(first, last).indices(int(classes.labels.shape[0]))
    rows, columns, fine, coarse = _native.canvas_pixels(
        np.ascontiguousarray(classes.labels[start:stop], dtype=np.int32),
        np.ascontiguousarray(classes.materials[start * 2 : stop * 2], dtype=np.uint8),
        np.ascontiguousarray(canvas[start:stop], dtype=np.bool_),
        np.ascontiguousarray(classes.label_class, dtype=np.int64),
        np.ascontiguousarray(classes.label_coarse, dtype=np.int64),
    )
    rows += np.uint32(start * 2)
    return rows, columns, fine, coarse


def _strips(classes: PixelClasses) -> list[tuple[int, int]]:
    """Location row ranges whose canvas pixels fit the memory budget one range at a time."""
    rows, columns = (int(size) for size in classes.labels.shape)
    height = band_rows(
        columns * PIXEL_ROW_BYTES, workers=1, floor=STRIP_FLOOR, ceiling=min(STRIP_CEILING, rows)
    )
    return [(first, min(rows, first + height)) for first in range(0, rows, height)]


def object_outputs(  # noqa: PLR0913 - one pass over every instance file.
    game_dir: Path,
    *,
    classes: PixelClasses,
    canvas: NDArray[np.bool_],
    class_count: int,
    coarse_count: int,
    seed: int,
    sink: MutableMapping[str, Buffer],
) -> dict[str, object]:
    """Rewrite the instance files that have instances in the canvas into ``sink``.

    ``canvas`` marks replaced location pixels; ``classes.calibrate`` marks the labels
    whose pixels calibrate densities (Old World land). Returns statistics.
    """
    rows, columns = classes.labels.shape
    sets = _bin_sets(game_dir) + _inline_sets(game_dir)
    affected: list[tuple[InstanceSet, NDArray[np.bool_]]] = []
    for instance in sets:
        row, column = _pixels(instance.records, rows, columns)
        inside = canvas[row // 2, column // 2]
        if np.any(inside):
            affected.append((instance, inside))
    if not affected:
        return {"instance_files": 0}
    fine_pixels = pixel_counts(classes, classes.label_class, class_count, classes.calibrate)
    coarse_pixels = pixel_counts(classes, classes.label_coarse, coarse_count, classes.calibrate)
    use_fine = fine_pixels >= MIN_PIXELS
    tables = [_densities(instance, classes, fine_pixels, coarse_pixels) for instance, _ in affected]
    removed = sum(int(np.count_nonzero(inside)) for _, inside in affected)
    strips = _strips(classes)
    fine_count = np.zeros(fine_pixels.size, dtype=np.int64)
    coarse_count_pixels = np.zeros(coarse_pixels.size, dtype=np.int64)
    for first, last in strips:
        _, _, fine_key, coarse_key = canvas_pixels(classes, canvas, first, last)
        fine_chosen = use_fine[fine_key]
        fine_count += np.bincount(fine_key, minlength=fine_pixels.size) * use_fine
        coarse_count_pixels += np.bincount(coarse_key[~fine_chosen], minlength=coarse_pixels.size)
    scale = budget_scale(
        tables, fine_count, coarse_count_pixels, removed * BUDGET_PERMILLE // PERMILLE
    )
    scaled = [
        ((fine_table * scale) >> DENSITY_BITS, (coarse_table * scale) >> DENSITY_BITS)
        for fine_table, coarse_table in tables
    ]
    kept_records = [instance.records[~inside] for instance, inside in affected]
    fresh: list[list[NDArray[np.float32]]] = [[] for _ in affected]
    for first, last in strips:
        checkpoint()
        pixels = canvas_pixels(classes, canvas, first, last)
        for index, (instance, _) in enumerate(affected):
            fresh[index].append(
                sample_instances(
                    pixels,
                    use_fine=use_fine,
                    densities=scaled[index],
                    source=kept_records[index],
                    rows=rows,
                    key=derive_seed(seed, "objects", instance.name),
                )
            )
    added = sum(int(part.shape[0]) for parts in fresh for part in parts)
    if added > removed:
        message = f"{added} new map object instances outnumber the {removed} they replace"
        raise ObjectBudgetError(message)
    inline: dict[str, dict[str, NDArray[np.float32]]] = {}
    files = 0
    for index, (instance, _) in enumerate(affected):
        values = np.concatenate([kept_records[index], *fresh[index]])
        kept_records[index] = np.empty((0, RECORD_FLOATS), dtype=np.float32)
        fresh[index] = []
        relative = instance.path.removeprefix("game/")
        if instance.path.endswith(".bin"):
            sink[relative] = np.ascontiguousarray(values, dtype="<f4")
            files += 1
        else:
            inline.setdefault(instance.path, {})[instance.name] = values
    for path, replaced in inline.items():
        sink[path.removeprefix("game/")] = rewrite_inline(game_dir / path, replaced)
        files += 1
    return {
        "instance_files": files,
        "instances_removed": removed,
        "instances_added": added,
        "density_scale_permille": scale * PERMILLE >> DENSITY_BITS,
    }


def _format(values: NDArray[np.float32]) -> str:
    rows = [" ".join(f"{float(v):.6f}" for v in row) for row in values.tolist()]
    return "".join(f"{row}\n" for row in rows)


def rewrite_inline(path: Path, replaced: dict[str, NDArray[np.float32]]) -> bytes:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")

    def swap(match: re.Match[str]) -> str:
        values = replaced.get(match.group(2))
        if values is None:
            return match.group(0)
        return f"{match.group(1)}{values.shape[0]}{match.group(4)}{_format(values)}{match.group(6)}"

    out = INLINE.sub(swap, text)
    prefix = "﻿" if raw.startswith(b"\xef\xbb\xbf") else ""
    return (prefix + out).encode("utf-8")
