"""Regenerate EU5 1.4.1 visual terrain under a generated New World.

Height and material decal layers that overlap the canvas are rebuilt: water is the
observed sea floor (2234), land starts above the observed minimum land height and rises
inland with integer noise relief, wastelands carry ridged mountains, and new land takes
the material of the nearest vanilla land pixel of the same decal. Mountain and volcano
decals inside the canvas are disabled both in their instance files and in the decal
cache. Values marked [V-EXEC] were measured on build 25905365.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, cast

import numpy as np

from rnw.noise import NOISE_SCALE, fractal_noise
from rnw.rng import derive_seed
from rnw.synth import grow_regions
from rnw.terrain_tiles import parse_info, read_level0, write_layer
from rnw.topology import distance_from

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

TERRAIN: Final[str] = "game/in_game/gfx/terrain2"
DECAL_CACHE: Final[str] = f"{TERRAIN}/terrain_cache/ingame_decals.json"
SEA_FLOOR: Final[int] = 2234
LAND_BASE: Final[int] = 5600
INLAND_STEP: Final[int] = 18
INLAND_LIMIT: Final[int] = 300
RELIEF: Final[int] = 2200
RELIEF_RAMP: Final[int] = 40
RIDGE_HEIGHT: Final[int] = 15000
RIDGE_RAMP: Final[int] = 60
NO_MATERIAL: Final[int] = 255
LOCATION_UNITS: Final[int] = 4
HEIGHTMAP: Final[re.Pattern[str]] = re.compile(r"heightmap_\d+_\d+")
OUTSIDE: Final[int] = -1
WATER_CODE: Final[int] = 0
WASTE_CODE: Final[int] = 2
RELIEF_CODES: Final[dict[str, int]] = {
    "wetlands": 1,
    "flatland": 1,
    "hills": 3,
    "plateau": 4,
    "mountains": 5,
}
# Per relief code: (noise amplitude, height offset, ridge weight in permille).
RELIEF_SHAPE: Final[dict[int, tuple[int, int, int]]] = {
    1: (700, 0, 0),
    2: (3000, 3500, 1000),
    3: (2600, 900, 0),
    4: (1400, 3200, 0),
    5: (4200, 2500, 450),
}
SMOOTH_RADIUS: Final[int] = 48


@dataclass(frozen=True, slots=True)
class Decal:
    """A height/material decal placed on the terrain."""

    name: str
    row0: int
    column0: int
    rows: int
    columns: int


def heightmap_decals(cache: list[dict[str, object]], map_rows: int) -> list[Decal]:
    """Location-raster footprint of every heightmap decal in the decal cache."""
    found: list[Decal] = []
    for entry in cache:
        name = str(entry["decal_name"])
        if not HEIGHTMAP.fullmatch(name):
            continue
        transform = cast("dict[str, dict[str, float]]", entry["decal_transform"])
        size = cast("dict[str, int]", entry["decal_size"])
        width = int(size["x"] * transform["scale"]["x"]) // LOCATION_UNITS
        height = int(size["y"] * transform["scale"]["y"]) // LOCATION_UNITS
        x = int(transform["position"]["x"]) // LOCATION_UNITS - width // 2
        top = int(transform["position"]["y"]) // LOCATION_UNITS + height // 2
        found.append(Decal(name, map_rows - top, x, height, width))
    return found


def _upsample(values: NDArray[np.int64] | NDArray[np.int8], factor: int) -> NDArray[np.int64]:
    return np.repeat(np.repeat(values.astype(np.int64), factor, axis=0), factor, axis=1)


def _noise(  # noqa: PLR0913 - a strip-computed field needs origin, size and octaves.
    key: int, x0: int, y0: int, width: int, height: int, *, period: int
) -> NDArray[np.int64]:
    out = np.empty((height, width), dtype=np.int64)
    for row in range(0, height, 1024):
        rows = min(1024, height - row)
        out[row : row + rows] = fractal_noise(
            key, x0, y0 + row, width, rows, period=period, octaves=5, persistence_permille=520
        )
    return out


def _box_blur(values: NDArray[np.int64], radius: int) -> NDArray[np.int64]:
    """Separable integer box blur with edge replication."""
    out = values
    for axis in (0, 1):
        padded = np.pad(
            out, [(radius + 1, radius) if a == axis else (0, 0) for a in (0, 1)], mode="edge"
        )
        summed = np.cumsum(padded, axis=axis, dtype=np.int64)
        size = 2 * radius + 1
        if axis == 0:
            out = (summed[size:] - summed[:-size]) // size
        else:
            out = (summed[:, size:] - summed[:, :-size]) // size
    return out


def _heights(
    codes: NDArray[np.int64], vanilla: NDArray[np.int64], seed: int, x0: int, y0: int
) -> NDArray[np.int64]:
    canvas = codes != OUTSIDE
    land = canvas & (codes != WATER_CODE)
    height, width = codes.shape
    table = np.zeros((3, 8), dtype=np.int64)
    for code, (amplitude, offset, ridge) in RELIEF_SHAPE.items():
        table[:, code] = (amplitude, offset, ridge)
    index = np.where(land, codes, 0)
    amplitude = _box_blur(table[0][index], SMOOTH_RADIUS)
    offset = _box_blur(table[1][index], SMOOTH_RADIUS)
    ridge_weight = _box_blur(table[2][index], SMOOTH_RADIUS)
    coast = np.minimum(
        distance_from(canvas & ~land, RELIEF_RAMP * 3 + 1, octagonal=True), RELIEF_RAMP * 3
    )
    coast = coast.astype(np.int64)
    ramp = np.minimum(coast, RELIEF_RAMP) * 1000 // RELIEF_RAMP
    broad = _noise(derive_seed(seed, "terrain_broad"), x0, y0, width, height, period=3000)
    relief = _noise(derive_seed(seed, "terrain_relief"), x0, y0, width, height, period=500)
    ridges = NOISE_SCALE - np.abs(
        _noise(derive_seed(seed, "terrain_ridges"), x0, y0, width, height, period=260)
    )
    ridge_height = (ridges * ridges // NOISE_SCALE) * RIDGE_HEIGHT // NOISE_SCALE
    land_height = (
        LAND_BASE
        + coast * INLAND_STEP
        + (broad + NOISE_SCALE) * 2500 // (2 * NOISE_SCALE)
        + (offset + relief * amplitude // NOISE_SCALE + ridge_height * ridge_weight // 1000)
        * ramp
        // 1000
    )
    land_height = np.maximum(land_height, LAND_BASE)
    out = vanilla.copy()
    out[canvas] = np.where(land[canvas], land_height[canvas], SEA_FLOOR)
    return out


def _materials(codes: NDArray[np.int64], vanilla: NDArray[np.int64]) -> NDArray[np.int64]:
    canvas = codes != OUTSIDE
    land = canvas & (codes != WATER_CODE)
    known = vanilla != NO_MATERIAL
    targets = canvas & land & ~known
    seeds = np.where(known, vanilla, -1).astype(np.int32)
    grown = grow_regions(known | targets, seeds).astype(np.int64)
    present = vanilla[known]
    fallback = int(np.bincount(present).argmax()) if present.size else 0
    out = vanilla.copy()
    out[canvas & ~land] = NO_MATERIAL
    filled = np.where(grown >= 0, grown, fallback)
    out[targets] = filled[targets]
    return out


def _layer(game_dir: Path, decal: str, kind: str) -> tuple[str, Path, Path]:
    folder = game_dir / TERRAIN / "decals" / decal
    return (
        f"in_game/gfx/terrain2/decals/{decal}/{decal}_{kind}",
        folder / f"{decal}_{kind}.info",
        folder / f"{decal}_{kind}.bin",
    )


def terrain_outputs(
    game_dir: Path, codes: NDArray[np.int8], seed: int
) -> tuple[dict[str, bytes], dict[str, object]]:
    """Mod files for every decal layer touched by the canvas, plus decal disabling.

    ``codes`` is the world-sized class map: -1 outside the canvas, 0 water, 1 land,
    2 wasteland.
    """
    cache_text = (game_dir / DECAL_CACHE).read_text(encoding="utf-8-sig")
    cache = cast("list[dict[str, object]]", json.loads(cache_text))
    outputs: dict[str, bytes] = {}
    touched: list[str] = []
    for decal in heightmap_decals(cache, codes.shape[0]):
        window = codes[
            decal.row0 : decal.row0 + decal.rows, decal.column0 : decal.column0 + decal.columns
        ]
        if not np.any(window != OUTSIDE):
            continue
        touched.append(decal.name)
        factor = 2
        local = _upsample(window, factor)
        for kind in ("height", "materials"):
            stem, info_path, bin_path = _layer(game_dir, decal.name, kind)
            layer, spans = parse_info(info_path.read_text(encoding="utf-8-sig"))
            vanilla = read_level0(layer, spans, bin_path.read_bytes())
            if kind == "height":
                image = _heights(local, vanilla, seed, decal.column0 * factor, decal.row0 * factor)
            else:
                image = _materials(local, vanilla)
            info, data = write_layer(image, layer)
            outputs[f"{stem}.info"] = info.encode("utf-8")
            outputs[f"{stem}.bin"] = data
    disabled, cache_out = _disable_decals(game_dir, cache, codes)
    outputs.update(disabled)
    outputs["in_game/gfx/terrain2/terrain_cache/ingame_decals.json"] = cache_out
    stats: dict[str, object] = {
        "decals_rebuilt": touched,
        "mountain_decals_disabled": len(disabled),
    }
    return outputs, stats


def _inside(codes: NDArray[np.int8], x: float, y: float) -> bool:
    rows, columns = codes.shape
    column = int(x) // LOCATION_UNITS
    row = rows - 1 - int(y) // LOCATION_UNITS
    return 0 <= row < rows and 0 <= column < columns and bool(codes[row, column] != OUTSIDE)


def _disable_decals(
    game_dir: Path, cache: list[dict[str, object]], codes: NDArray[np.int8]
) -> tuple[dict[str, bytes], bytes]:
    """Disable mountain/volcano decals over the canvas in instances and in the cache."""
    kept: list[dict[str, object]] = []
    for entry in cache:
        name = str(entry["decal_name"])
        position = cast("dict[str, dict[str, float]]", entry["decal_transform"])["position"]
        if HEIGHTMAP.fullmatch(name) or not _inside(codes, position["x"], position["y"]):
            kept.append(entry)
    files: dict[str, bytes] = {}
    decals = game_dir / TERRAIN / "decals"
    for folder in sorted(path for path in decals.iterdir() if path.is_dir()):
        if HEIGHTMAP.fullmatch(folder.name) or not (folder / "instances").is_dir():
            continue
        for instance in sorted((folder / "instances").glob("*.json")):
            raw = instance.read_bytes()
            data = cast("dict[str, object]", json.loads(raw.decode("utf-8-sig")))
            x = cast("float", data["position.x"])
            y = cast("float", data["position.y"])
            if data.get("disabled") is False and _inside(codes, x, y):
                text = raw.decode("utf-8-sig").replace('"disabled":\tfalse', '"disabled":\ttrue')
                prefix = "﻿" if raw.startswith(b"\xef\xbb\xbf") else ""
                relative = f"in_game/gfx/terrain2/decals/{folder.name}/instances/{instance.name}"
                files[relative] = (prefix + text).encode("utf-8")
    cache_out = ("﻿" + json.dumps(kept, indent="\t", ensure_ascii=False) + "\n").encode("utf-8")
    return files, cache_out
