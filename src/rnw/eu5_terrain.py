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
from itertools import pairwise
from typing import TYPE_CHECKING, Final, cast

import numpy as np

from rnw.noise import NOISE_SCALE, fractal_noise
from rnw.rng import derive_seed
from rnw.terrain_materials import (
    HIGHLAND,
    LOWLAND,
    NONE,
    coastal_palette,
    pick,
    site_field,
    site_offset,
)
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


def box_blur(values: NDArray[np.int64], radius: int) -> NDArray[np.int64]:
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


# Median vanilla coast profile measured on decal heightmap_6_16 [V-EXEC]: height by
# step distance (decal pixels) into water and into land from the coastline.
WATER_PROFILE: Final[tuple[tuple[int, int], ...]] = (
    (1, 5292), (2, 4636), (3, 4028), (4, 3470), (5, 2940), (6, 2416), (7, 2300), (8, 2234),
)  # fmt: skip
LAND_PROFILE: Final[tuple[tuple[int, int], ...]] = (
    (1, 5708), (2, 5914), (3, 5998), (4, 6084), (6, 6266), (10, 6496), (20, 6936),
    (40, 7568), (60, 8508), (120, 9800),
)  # fmt: skip
MARGIN: Final[int] = 128
COAST_SMOOTH: Final[int] = 3
SHELF_BAND: Final[int] = 6
BEACH_BAND: Final[int] = 4


def _profile(distance: NDArray[np.int64], table: tuple[tuple[int, int], ...]) -> NDArray[np.int64]:
    """Integer piecewise-linear interpolation of a (distance, height) table."""
    out = np.full(distance.shape, table[-1][1], dtype=np.int64)
    out[distance <= table[0][0]] = table[0][1]
    for (d0, h0), (d1, h1) in pairwise(table):
        inside = (distance > d0) & (distance <= d1)
        out[inside] = h0 + (distance[inside] - d0) * (h1 - h0) // (d1 - d0)
    return out


@dataclass(frozen=True, slots=True, eq=False)
class Window:
    """A decal plus margin, in location pixels, and the decal's offset inside it."""

    row0: int
    row1: int
    column0: int
    column1: int
    inner_row: int
    inner_column: int


def _window(decal: Decal, shape: tuple[int, int]) -> Window:
    row0 = max(0, decal.row0 - MARGIN)
    column0 = max(0, decal.column0 - MARGIN)
    return Window(
        row0,
        min(shape[0], decal.row0 + decal.rows + MARGIN),
        column0,
        min(shape[1], decal.column0 + decal.columns + MARGIN),
        (decal.row0 - row0) * 2,
        (decal.column0 - column0) * 2,
    )


def _land_and_distances(
    codes: NDArray[np.int64], vanilla_water: NDArray[np.bool_]
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.int64], NDArray[np.int64]]:
    """Smoothed land mask (new coast inside the canvas), canvas mask and coast distances."""
    canvas = codes != OUTSIDE
    raw = np.where(canvas, codes != WATER_CODE, ~vanilla_water)
    smooth = box_blur(raw.astype(np.int64) * 1000, COAST_SMOOTH) >= 500  # noqa: PLR2004 - half
    land = np.where(canvas, smooth, raw)
    inland = distance_from(~land, LAND_PROFILE[-1][0] + 1, octagonal=True).astype(np.int64)
    offshore = distance_from(land, WATER_PROFILE[-1][0] + 1, octagonal=True).astype(np.int64)
    inland = np.where(land, np.maximum(box_blur(inland * 8, 4) // 8, 1), 0)
    offshore = np.where(land, 0, np.maximum(box_blur(offshore * 8, 2) // 8, 1))
    return land, canvas, inland, offshore


def _heights(  # noqa: PLR0913 - one window's height needs codes, coast, origin and seed.
    codes: NDArray[np.int64],
    *,
    land: NDArray[np.bool_],
    inland: NDArray[np.int64],
    offshore: NDArray[np.int64],
    seed: int,
    origin: tuple[int, int],
) -> NDArray[np.int64]:
    """Generated heights for a window: vanilla coast profile plus relief by topography."""
    height, width = codes.shape
    x0, y0 = origin
    table = np.zeros((3, 8), dtype=np.int64)
    for code, (amplitude, offset, ridge) in RELIEF_SHAPE.items():
        table[:, code] = (amplitude, offset, ridge)
    index = np.where(land & (codes != OUTSIDE), np.maximum(codes, 0), 0)
    amplitude = box_blur(table[0][index], SMOOTH_RADIUS)
    offset = box_blur(table[1][index], SMOOTH_RADIUS)
    ridge_weight = box_blur(table[2][index], SMOOTH_RADIUS)
    ramp = np.minimum(inland, RELIEF_RAMP) * 1000 // RELIEF_RAMP
    broad = _noise(derive_seed(seed, "terrain_broad"), x0, y0, width, height, period=3000)
    relief = _noise(derive_seed(seed, "terrain_relief"), x0, y0, width, height, period=500)
    ridges = NOISE_SCALE - np.abs(
        _noise(derive_seed(seed, "terrain_ridges"), x0, y0, width, height, period=260)
    )
    ridge_height = (ridges * ridges // NOISE_SCALE) * RIDGE_HEIGHT // NOISE_SCALE
    raised = (
        (broad + NOISE_SCALE) * 2500 // (2 * NOISE_SCALE)
        + offset
        + relief * amplitude // NOISE_SCALE
        + ridge_height * ridge_weight // 1000
    )
    land_height = _profile(inland, LAND_PROFILE) + np.maximum(0, raised) * ramp // 1000
    water_height = _profile(offshore, WATER_PROFILE)
    return np.where(land, land_height, water_height)


def _bands(
    land: NDArray[np.bool_], inland: NDArray[np.int64], offshore: NDArray[np.int64]
) -> NDArray[np.int8]:
    """0 deep water, 1 shelf, 2 beach, 3 inland."""
    band = np.zeros(land.shape, dtype=np.int8)
    band[~land & (offshore <= SHELF_BAND)] = 1
    band[land & (inland <= BEACH_BAND)] = 2
    band[land & (inland > BEACH_BAND)] = 3
    return band


def _patch_materials(  # noqa: PLR0913 - patch transfer needs both worlds and the window.
    seed: int,
    *,
    window: Window,
    codes: NDArray[np.int64],
    bands: tuple[NDArray[np.int8], NDArray[np.int8]],
    canvas: NDArray[np.bool_],
    local: NDArray[np.int64],
    world_materials: NDArray[np.uint8],
    categories: NDArray[np.int8],
) -> NDArray[np.int64]:
    """Shelf/beach slots by noise; inland copies vanilla patches of the same category."""
    new_band, vanilla_band = bands
    height, width = codes.shape
    x0, y0 = window.column0 * 2, window.row0 * 2
    out = local.copy()
    out[canvas & (new_band == 0)] = NO_MATERIAL
    for band in (1, 2):
        targets = canvas & (new_band == band)
        if np.any(targets):
            palette = coastal_palette(local[vanilla_band == band])
            noise = _noise(
                derive_seed(seed, f"material_band_{band}"), x0, y0, width, height, period=40
            )
            out[targets] = pick(palette, noise)[targets]
    targets = canvas & (new_band == 3)  # noqa: PLR2004 - inland band
    if not np.any(targets):
        return out
    cell_x, cell_y = site_field(seed, window.column0, window.row0, width // 2, height // 2)
    cell_x = _upsample(cell_x, 2)
    cell_y = _upsample(cell_y, 2)
    wanted = np.where(
        (codes == WASTE_CODE) | (codes == RELIEF_CODES["mountains"]), HIGHLAND, LOWLAND
    )
    keys = np.stack([cell_x[targets], cell_y[targets], wanted[targets]], axis=1)
    unique, inverse = np.unique(keys, axis=0, return_inverse=True)
    offsets = np.array(
        [site_offset(seed, int(x), int(y), int(c), categories) for x, y, c in unique.tolist()],
        dtype=np.int64,
    )
    rows, columns = np.nonzero(targets)
    world_rows, world_columns = world_materials.shape
    source_rows = np.clip(rows + y0 + 2 * offsets[inverse.ravel(), 1], 0, world_rows - 1)
    source_columns = (columns + x0 + 2 * offsets[inverse.ravel(), 0]) % world_columns
    sampled = world_materials[source_rows, source_columns].astype(np.int64)
    fallback_palette = coastal_palette(local[vanilla_band == 3])  # noqa: PLR2004 - inland band
    fallback = pick(
        fallback_palette,
        _noise(derive_seed(seed, "material_fallback"), x0, y0, width, height, period=60),
    )[rows, columns]
    out[rows, columns] = np.where(sampled == NO_MATERIAL, fallback, sampled)
    return out


def vanilla_categories(
    labels: NDArray[np.int32], water: NDArray[np.bool_], highland: NDArray[np.bool_]
) -> NDArray[np.int8]:
    """Location-raster map: 0 water or coast, 1 lowland inland, 2 highland inland."""
    land = ~water[labels]
    inland = distance_from(~land, 4) >= 3  # noqa: PLR2004 - three location pixels
    out = np.where(highland[labels], HIGHLAND, LOWLAND).astype(np.int8)
    out[~(land & inland)] = NONE
    return out


def _layer(game_dir: Path, decal: str, kind: str) -> tuple[str, Path, Path]:
    folder = game_dir / TERRAIN / "decals" / decal
    return (
        f"in_game/gfx/terrain2/decals/{decal}/{decal}_{kind}",
        folder / f"{decal}_{kind}.info",
        folder / f"{decal}_{kind}.bin",
    )


def _world_materials(
    game_dir: Path, decals: list[Decal], shape: tuple[int, int]
) -> NDArray[np.uint8]:
    """All vanilla material layers on one 2x world grid (for margins across seams)."""
    world = np.full((shape[0] * 2, shape[1] * 2), NO_MATERIAL, dtype=np.uint8)
    for decal in decals:
        _, info_path, bin_path = _layer(game_dir, decal.name, "materials")
        layer, spans = parse_info(info_path.read_text(encoding="utf-8-sig"))
        image = read_level0(layer, spans, bin_path.read_bytes())
        world[
            decal.row0 * 2 : (decal.row0 + decal.rows) * 2,
            decal.column0 * 2 : (decal.column0 + decal.columns) * 2,
        ] = image.astype(np.uint8)
    return world


def terrain_outputs(
    game_dir: Path,
    codes: NDArray[np.int8],
    vanilla_water: NDArray[np.bool_],
    categories: NDArray[np.int8],
    seed: int,
) -> tuple[dict[str, bytes], dict[str, object]]:
    """Mod files for every decal layer touched by the canvas, plus decal disabling.

    ``codes`` is the world-sized relief-code map (-1 outside the canvas, 0 water) and
    ``vanilla_water`` the vanilla water mask, both at location resolution.
    """
    cache_text = (game_dir / DECAL_CACHE).read_text(encoding="utf-8-sig")
    cache = cast("list[dict[str, object]]", json.loads(cache_text))
    decals = heightmap_decals(cache, codes.shape[0])
    outputs: dict[str, bytes] = {}
    touched: list[str] = []
    world_materials: NDArray[np.uint8] | None = None
    for decal in decals:
        inner = codes[
            decal.row0 : decal.row0 + decal.rows, decal.column0 : decal.column0 + decal.columns
        ]
        if not np.any(inner != OUTSIDE):
            continue
        if world_materials is None:
            world_materials = _world_materials(game_dir, decals, (codes.shape[0], codes.shape[1]))
        touched.append(decal.name)
        window = _window(decal, (codes.shape[0], codes.shape[1]))
        rows = slice(window.row0, window.row1)
        columns = slice(window.column0, window.column1)
        local = _upsample(codes[rows, columns], 2)
        water = _upsample(vanilla_water[rows, columns].astype(np.int8), 2).astype(bool)
        land, canvas, inland, offshore = _land_and_distances(local, water)
        crop = (
            slice(window.inner_row, window.inner_row + decal.rows * 2),
            slice(window.inner_column, window.inner_column + decal.columns * 2),
        )
        for kind in ("height", "materials"):
            stem, info_path, bin_path = _layer(game_dir, decal.name, kind)
            layer, spans = parse_info(info_path.read_text(encoding="utf-8-sig"))
            vanilla = read_level0(layer, spans, bin_path.read_bytes())
            if kind == "height":
                generated = _heights(
                    local,
                    land=land,
                    inland=inland,
                    offshore=offshore,
                    seed=seed,
                    origin=(window.column0 * 2, window.row0 * 2),
                )[crop]
            else:
                vanilla_land = ~water
                v_inland = distance_from(water, BEACH_BAND + 2, octagonal=True).astype(np.int64)
                v_offshore = distance_from(vanilla_land, SHELF_BAND + 2, octagonal=True).astype(
                    np.int64
                )
                window_materials = world_materials[
                    window.row0 * 2 : window.row1 * 2, window.column0 * 2 : window.column1 * 2
                ].astype(np.int64)
                generated = _patch_materials(
                    seed,
                    window=window,
                    codes=local,
                    bands=(
                        _bands(land, inland, offshore),
                        _bands(vanilla_land, v_inland, v_offshore),
                    ),
                    canvas=canvas,
                    local=window_materials,
                    world_materials=world_materials,
                    categories=categories,
                )[crop]
            image = np.where(canvas[crop], generated, vanilla)
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
