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
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.rng import derive_seed, hash_grid

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

MAP_OBJECTS: Final[str] = "game/in_game/gfx/map/map_objects"
RECORD_FLOATS: Final[int] = 10
SLOT_CLASSES: Final[int] = 18
NO_SLOT: Final[int] = 17
DENSITY_BITS: Final[int] = 24
MIN_PIXELS: Final[int] = 20_000
CHUNK_ROWS: Final[int] = 1024
INLINE: Final[re.Pattern[str]] = re.compile(
    r'(object=\{[^{}]*?name="([^"]+)"[^{}]*?count=)(\d+)(\s*transform=")([^"]*)("\})', re.DOTALL
)
BIN_REFERENCE: Final[re.Pattern[str]] = re.compile(
    r'transform_bin_file="gfx/map/map_objects/([^"]+\.bin)"'
)
GENERATOR: Final[re.Pattern[str]] = re.compile(r"_generator_|^woods_cherry_")


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


def _pixel_keys(
    classes: PixelClasses, table: NDArray[np.int64], row0: int, row1: int
) -> NDArray[np.int64]:
    """Key (class x slot) of every material pixel in even material rows ``row0:row1``."""
    labels = classes.labels[row0 // 2 : row1 // 2]
    expanded = np.repeat(np.repeat(table[labels], 2, axis=0), 2, axis=1)
    return expanded * SLOT_CLASSES + _slot_class(classes.materials[row0:row1])


def _pixel_counts(
    classes: PixelClasses, table: NDArray[np.int64], keys: int, mask: NDArray[np.bool_]
) -> NDArray[np.int64]:
    """Material pixels per key among labels where ``mask`` is true."""
    counts = np.zeros(keys * SLOT_CLASSES, dtype=np.int64)
    rows = classes.materials.shape[0]
    for start in range(0, rows, CHUNK_ROWS):
        stop = min(rows, start + CHUNK_ROWS)
        key = _pixel_keys(classes, table, start, stop)
        labels = np.repeat(np.repeat(classes.labels[start // 2 : stop // 2], 2, axis=0), 2, axis=1)
        chosen = mask[labels]
        counts += np.bincount(key[chosen], minlength=counts.size)
    return counts


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


def sample_instances(  # noqa: PLR0913 - sampling needs pixels, densities, source records and seed.
    pixel_rows: NDArray[np.int64],
    pixel_columns: NDArray[np.int64],
    *,
    density: NDArray[np.int64],
    source: NDArray[np.float32],
    rows: int,
    key: int,
) -> NDArray[np.float32]:
    """Records for pixels with fixed-point densities (expected count = density)."""
    first = hash_grid(key, pixel_columns, pixel_rows)
    fraction = (first & np.uint64((1 << DENSITY_BITS) - 1)).astype(np.int64)
    count = (density + fraction) >> DENSITY_BITS
    picked = np.flatnonzero(count)
    if not picked.size or not source.size:
        return np.zeros((0, RECORD_FLOATS), dtype=np.float32)
    repeat = count[picked]
    index = np.repeat(picked, repeat)
    copy = np.arange(index.size, dtype=np.int64) - np.repeat(np.cumsum(repeat) - repeat, repeat)
    second = hash_grid(key ^ 0x5EED, pixel_columns[index] * 8 + copy, pixel_rows[index])
    dx = (second & np.uint64(0xFFFF)).astype(np.int64)
    dz = ((second >> np.uint64(16)) & np.uint64(0xFFFF)).astype(np.int64)
    donor = ((second >> np.uint64(32)) % np.uint64(source.shape[0])).astype(np.int64)
    out = source[donor].copy()
    out[:, 0] = ((pixel_columns[index] * 65536 + dx) / 131072.0).astype(np.float32)
    out[:, 1] = 0.0
    out[:, 2] = (rows - (pixel_rows[index] * 65536 + dz) / 131072.0).astype(np.float32)
    return out


def object_outputs(  # noqa: PLR0913 - one pass over every instance file.
    game_dir: Path,
    *,
    classes: PixelClasses,
    canvas: NDArray[np.bool_],
    class_count: int,
    coarse_count: int,
    seed: int,
) -> tuple[dict[str, bytes], dict[str, object]]:
    """Rewritten instance files for every file that has instances in the canvas.

    ``canvas`` marks replaced location pixels; ``classes.calibrate`` marks the labels
    whose pixels calibrate densities (Old World land).
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
        return {}, {"instance_files": 0}
    fine_pixels = _pixel_counts(classes, classes.label_class, class_count, classes.calibrate)
    coarse_pixels = _pixel_counts(classes, classes.label_coarse, coarse_count, classes.calibrate)
    canvas_rows: list[NDArray[np.int64]] = []
    canvas_columns: list[NDArray[np.int64]] = []
    fine_keys: list[NDArray[np.int64]] = []
    coarse_keys: list[NDArray[np.int64]] = []
    for start in range(0, rows * 2, CHUNK_ROWS):
        stop = min(rows * 2, start + CHUNK_ROWS)
        labels = np.repeat(np.repeat(classes.labels[start // 2 : stop // 2], 2, axis=0), 2, axis=1)
        inside = np.repeat(np.repeat(canvas[start // 2 : stop // 2], 2, axis=0), 2, axis=1)
        inside &= classes.label_class[labels] >= 0
        local_rows, local_columns = np.nonzero(inside)
        canvas_rows.append(local_rows + start)
        canvas_columns.append(local_columns)
        fine_keys.append(_pixel_keys(classes, classes.label_class, start, stop)[inside])
        coarse_keys.append(_pixel_keys(classes, classes.label_coarse, start, stop)[inside])
    pixel_rows = np.concatenate(canvas_rows)
    pixel_columns = np.concatenate(canvas_columns)
    fine_key = np.concatenate(fine_keys)
    coarse_key = np.concatenate(coarse_keys)
    use_fine = fine_pixels[fine_key] >= MIN_PIXELS
    records: dict[str, list[tuple[InstanceSet, NDArray[np.float32]]]] = {}
    removed = 0
    added = 0
    for instance, inside in affected:
        fine, coarse = _densities(instance, classes, fine_pixels, coarse_pixels)
        density = np.where(use_fine, fine[fine_key], coarse[coarse_key])
        wanted = density > 0
        donors = instance.records[~inside]
        stream = derive_seed(seed, "objects", instance.name)
        fresh = sample_instances(
            pixel_rows[wanted],
            pixel_columns[wanted],
            density=density[wanted],
            source=donors,
            rows=rows,
            key=stream,
        )
        kept = instance.records[~inside]
        removed += int(np.count_nonzero(inside))
        added += int(fresh.shape[0])
        records.setdefault(instance.path, []).append((instance, np.concatenate([kept, fresh])))
    outputs: dict[str, bytes] = {}
    for path, parts in records.items():
        relative = path.removeprefix("game/")
        if path.endswith(".bin"):
            outputs[relative] = parts[0][1].astype("<f4").tobytes()
        else:
            replaced = {instance.name: values for instance, values in parts}
            outputs[relative] = rewrite_inline(game_dir / path, replaced)
    stats: dict[str, object] = {
        "instance_files": len(outputs),
        "instances_removed": removed,
        "instances_added": added,
    }
    return outputs, stats


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
