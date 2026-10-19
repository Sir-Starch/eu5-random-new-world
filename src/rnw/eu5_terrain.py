"""Regenerate EU5 1.4.1 visual terrain under a generated New World.

Height and material decal layers that overlap the canvas are rebuilt. Heights follow
the vanilla coast profile at the shore and the continuous relief field inland (the same
field that set cell topography), with fine detail noise whose amplitude grows with
height. Materials are biome slots rebuilt from the location data by the vanilla rules
(``eu5_slots.py``), so each location's biome, coast, borders and rivers render the way
vanilla does. Mountain and volcano decals inside the canvas are disabled in their
instance files and in the decal cache. Values marked [V-EXEC] were measured on build
25905365.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from itertools import pairwise
from typing import TYPE_CHECKING, Final, cast

import numpy as np

from rnw.eu5_slots import LEVELS, SlotTables, level_counts, synthesize
from rnw.fields import PERMILLE, box_blur, upsample
from rnw.noise import NOISE_SCALE, fractal_noise
from rnw.relief import COAST_HEIGHT
from rnw.rng import derive_seed
from rnw.terrain_tiles import LayerFormat, parse_info, read_level0, write_layer
from rnw.topology import distance_from, euclidean_distance

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

TERRAIN: Final[str] = "game/in_game/gfx/terrain2"
DECAL_CACHE: Final[str] = f"{TERRAIN}/terrain_cache/ingame_decals.json"
LOCATION_UNITS: Final[int] = 4
HEIGHTMAP: Final[re.Pattern[str]] = re.compile(r"heightmap_\d+_\d+")
OUTSIDE: Final[int] = -1
WATER_CODE: Final[int] = 0
LAND_CODE: Final[int] = 1
DETAIL_PERIOD: Final[int] = 64
DETAIL_BASE: Final[int] = 250
DETAIL_PERMILLE: Final[int] = 60
CREST_PERIOD: Final[int] = 48
CREST_FULL: Final[int] = 16000
CREST_HEIGHT: Final[int] = 2600


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


@dataclass(eq=False)
class DecalStore:
    """Reads vanilla decal layers once and keeps them in compact form."""

    game_dir: Path
    map_shape: tuple[int, int]
    cache: list[dict[str, object]] = field(init=False)
    decals: list[Decal] = field(init=False)
    _layers: dict[tuple[str, str], tuple[LayerFormat, NDArray[np.uint16] | NDArray[np.uint8]]] = (
        field(init=False, default_factory=dict)
    )

    def __post_init__(self) -> None:
        """Load the decal cache and the heightmap decal footprints."""
        text = (self.game_dir / DECAL_CACHE).read_text(encoding="utf-8-sig")
        self.cache = cast("list[dict[str, object]]", json.loads(text))
        self.decals = heightmap_decals(self.cache, self.map_shape[0])

    def paths(self, decal: str, kind: str) -> tuple[str, Path, Path]:
        """Mod-relative stem and the vanilla .info and .bin paths of one layer."""
        folder = self.game_dir / TERRAIN / "decals" / decal
        return (
            f"in_game/gfx/terrain2/decals/{decal}/{decal}_{kind}",
            folder / f"{decal}_{kind}.info",
            folder / f"{decal}_{kind}.bin",
        )

    def layer(self, decal: str, kind: str) -> tuple[LayerFormat, NDArray[np.int64]]:
        """Vanilla layer ``kind`` ("height" or "materials") of a decal, north-up."""
        key = (decal, kind)
        if key not in self._layers:
            _, info_path, bin_path = self.paths(decal, kind)
            layer, spans = parse_info(info_path.read_text(encoding="utf-8-sig"))
            image = read_level0(layer, spans, bin_path.read_bytes())
            compact: NDArray[np.uint16] | NDArray[np.uint8] = (
                image.astype(np.uint16) if kind == "height" else image.astype(np.uint8)
            )
            self._layers[key] = (layer, compact)
        layer, compact = self._layers[key]
        return layer, compact.astype(np.int64)

    def world_heights(self) -> NDArray[np.uint16]:
        """Vanilla height at location resolution (one decal sample per location pixel)."""
        out = np.zeros(self.map_shape, dtype=np.uint16)
        for decal in self.decals:
            _, image = self.layer(decal.name, "height")
            out[
                decal.row0 : decal.row0 + decal.rows, decal.column0 : decal.column0 + decal.columns
            ] = image[1::2, 1::2]
        return out

    def world_materials(self) -> NDArray[np.uint8]:
        """All vanilla material layers on one grid with two pixels per location pixel."""
        out = np.full((self.map_shape[0] * 2, self.map_shape[1] * 2), 255, dtype=np.uint8)
        for decal in self.decals:
            _, image = self.layer(decal.name, "materials")
            out[
                decal.row0 * 2 : (decal.row0 + decal.rows) * 2,
                decal.column0 * 2 : (decal.column0 + decal.columns) * 2,
            ] = image
        return out


def _upsample(values: NDArray[np.generic], factor: int) -> NDArray[np.int64]:
    return np.repeat(np.repeat(values.astype(np.int64), factor, axis=0), factor, axis=1)


def _noise(  # noqa: PLR0913 - a strip-computed field needs origin, size and octaves.
    key: int, x0: int, y0: int, width: int, height: int, *, period: int
) -> NDArray[np.int64]:
    out = np.empty((height, width), dtype=np.int64)
    for row in range(0, height, 1024):
        rows = min(1024, height - row)
        out[row : row + rows] = fractal_noise(
            key, x0, y0 + row, width, rows, period=period, octaves=3, persistence_permille=500
        )
    return out


# Median vanilla shelf profile measured on decal heightmap_6_16 [V-EXEC]: height by step
# distance (decal pixels) into water from the coastline; land starts at 5708.
WATER_PROFILE: Final[tuple[tuple[int, int], ...]] = (
    (1, 5292), (2, 4636), (3, 4028), (4, 3470), (5, 2940), (6, 2416), (7, 2300), (8, 2234),
)  # fmt: skip
SHORE_HEIGHT: Final[int] = 5708
CAP_SLOPE: Final[int] = 300
CAP_REACH: Final[int] = 64
EIGHTHS: Final[int] = 8
MARGIN: Final[int] = 128
COAST_SMOOTH: Final[int] = 3


def _profile(
    distance: NDArray[np.int64], table: tuple[tuple[int, int], ...], unit: int = 1
) -> NDArray[np.int64]:
    """Integer piecewise-linear interpolation of a (distance, height) table.

    ``distance`` is in ``1 / unit`` pixels.
    """
    out = np.full(distance.shape, table[-1][1], dtype=np.int64)
    out[distance <= table[0][0] * unit] = table[0][1]
    for (d0, h0), (d1, h1) in pairwise(table):
        inside = (distance > d0 * unit) & (distance <= d1 * unit)
        out[inside] = h0 + (distance[inside] - d0 * unit) * (h1 - h0) // ((d1 - d0) * unit)
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
    """Smoothed land mask, canvas mask and coast distances at decal resolution.

    Inputs are at location resolution. Distances are in eighths of a decal pixel; the
    inland one is Euclidean (computed per location pixel and interpolated), so slopes
    built on it have no metric artefacts.
    """
    canvas_location = codes != OUTSIDE
    land_location = np.where(canvas_location, codes != WATER_CODE, ~vanilla_water)
    canvas = _upsample(canvas_location.astype(np.int8), 2).astype(bool)
    raw = _upsample(land_location.astype(np.int8), 2).astype(bool)
    smooth = box_blur(raw.astype(np.int64) * 1000, COAST_SMOOTH) >= 500  # noqa: PLR2004 - half
    land = np.where(canvas, smooth, raw)
    shape = (int(land.shape[0]), int(land.shape[1]))
    reach = euclidean_distance(~land_location, CAP_REACH) * 2
    inland = box_blur(upsample(np.pad(reach, ((0, 1), (0, 1)), mode="edge"), 2, shape), 2)
    offshore = distance_from(land, WATER_PROFILE[-1][0] + 1, octagonal=True).astype(np.int64)
    offshore = box_blur(offshore * EIGHTHS, 2)
    inland = np.where(land, np.maximum(inland, EIGHTHS), 0)
    offshore = np.where(land, 0, np.maximum(offshore, EIGHTHS))
    return land, canvas, inland, offshore


def _heights(  # noqa: PLR0913 - one window's height needs relief, coast, origin and seed.
    relief: NDArray[np.int64],
    *,
    land: NDArray[np.bool_],
    inland: NDArray[np.int64],
    offshore: NDArray[np.int64],
    seed: int,
    origin: tuple[int, int],
) -> NDArray[np.int64]:
    """Generated heights for a window: relief plus detail under a coastal cap.

    ``relief`` is at location resolution; the result is at decal resolution. Near the
    shore the height is capped by a ramp that starts at the lowest vanilla land height,
    so beaches are low and ranges rise from them without a terrace. Water follows the
    vanilla shelf profile. Distances are in eighths of a pixel.
    """
    filled = np.pad(np.where(relief > 0, relief, COAST_HEIGHT), ((0, 1), (0, 1)), mode="edge")
    shape = (int(land.shape[0]), int(land.shape[1]))
    smooth = upsample(filled, 2, shape)
    x0, y0 = origin
    detail = _noise(derive_seed(seed, "terrain_detail"), x0, y0, shape[1], shape[0],
                    period=DETAIL_PERIOD)  # fmt: skip
    raised = np.maximum(0, smooth - COAST_HEIGHT)
    amplitude = DETAIL_BASE + raised * DETAIL_PERMILLE // PERMILLE
    crest = NOISE_SCALE - np.minimum(
        np.abs(_noise(derive_seed(seed, "terrain_crests"), x0, y0, shape[1], shape[0],
                      period=CREST_PERIOD)),
        NOISE_SCALE,
    )  # fmt: skip
    crests = (crest * crest // NOISE_SCALE) * np.minimum(raised, CREST_FULL) // CREST_FULL
    inner = smooth + detail * amplitude // NOISE_SCALE + crests * CREST_HEIGHT // NOISE_SCALE
    cap = SHORE_HEIGHT + (inland - EIGHTHS) * CAP_SLOPE // EIGHTHS
    land_height = np.maximum(np.minimum(inner, cap), SHORE_HEIGHT)
    water_height = _profile(offshore, WATER_PROFILE, EIGHTHS)
    return np.where(land, land_height, water_height)


def level_shares(
    store: DecalStore, labels: NDArray[np.int32], group: NDArray[np.int64], groups: int
) -> NDArray[np.int64]:
    """Interior variation-level counts per label group over every vanilla decal."""
    counts = np.zeros((groups, LEVELS), dtype=np.int64)
    for decal in store.decals:
        _, materials = store.layer(decal.name, "materials")
        crop = labels[
            decal.row0 : decal.row0 + decal.rows, decal.column0 : decal.column0 + decal.columns
        ]
        counts += level_counts(materials, crop, group, groups)
    return counts


@dataclass(frozen=True, slots=True, eq=False)
class TerrainInputs:
    """World-sized rasters that drive the rebuilt decals (location resolution)."""

    codes: NDArray[np.int8]
    vanilla_water: NDArray[np.bool_]
    relief: NDArray[np.int32]
    labels: NDArray[np.int32]
    rivers: NDArray[np.bool_]


def terrain_outputs(
    store: DecalStore, inputs: TerrainInputs, tables: SlotTables, seed: int
) -> tuple[dict[str, bytes], NDArray[np.uint8], dict[str, object]]:
    """Mod files for every decal layer touched by the canvas, plus decal disabling.

    ``inputs.codes`` is -1 outside the canvas, 0 for water and 1 for land. Returns the
    files, the final material raster (two pixels per location pixel) and statistics.
    """
    codes = inputs.codes
    shape = (int(codes.shape[0]), int(codes.shape[1]))
    outputs: dict[str, bytes] = {}
    touched: list[str] = []
    materials_world = store.world_materials()
    for decal in store.decals:
        inner = codes[
            decal.row0 : decal.row0 + decal.rows, decal.column0 : decal.column0 + decal.columns
        ]
        if not np.any(inner != OUTSIDE):
            continue
        touched.append(decal.name)
        window = _window(decal, shape)
        rows = slice(window.row0, window.row1)
        columns = slice(window.column0, window.column1)
        land, canvas, inland, offshore = _land_and_distances(
            codes[rows, columns].astype(np.int64), inputs.vanilla_water[rows, columns]
        )
        crop = (
            slice(window.inner_row, window.inner_row + decal.rows * 2),
            slice(window.inner_column, window.inner_column + decal.columns * 2),
        )
        origin = (window.column0 * 2, window.row0 * 2)
        height_layer, vanilla_height = store.layer(decal.name, "height")
        generated = _heights(
            inputs.relief[rows, columns].astype(np.int64),
            land=land,
            inland=inland,
            offshore=offshore,
            seed=seed,
            origin=origin,
        )[crop]
        stem, _, _ = store.paths(decal.name, "height")
        info, data = write_layer(np.where(canvas[crop], generated, vanilla_height), height_layer)
        outputs[f"{stem}.info"] = info.encode("utf-8")
        outputs[f"{stem}.bin"] = data
        material_layer, vanilla_materials = store.layer(decal.name, "materials")
        labels = np.repeat(np.repeat(inputs.labels[rows, columns], 2, axis=0), 2, axis=1)
        rivers = _upsample(inputs.rivers[rows, columns].astype(np.int8), 2).astype(bool)
        slots = synthesize(labels, land, rivers, tables, seed=seed, origin=origin)[crop]
        image = np.where(canvas[crop], slots, vanilla_materials)
        stem, _, _ = store.paths(decal.name, "materials")
        info, data = write_layer(image, material_layer)
        outputs[f"{stem}.info"] = info.encode("utf-8")
        outputs[f"{stem}.bin"] = data
        materials_world[
            decal.row0 * 2 : (decal.row0 + decal.rows) * 2,
            decal.column0 * 2 : (decal.column0 + decal.columns) * 2,
        ] = image.astype(np.uint8)
    disabled, cache_out = _disable_decals(store, codes)
    outputs.update(disabled)
    outputs["in_game/gfx/terrain2/terrain_cache/ingame_decals.json"] = cache_out
    stats: dict[str, object] = {
        "decals_rebuilt": touched,
        "mountain_decals_disabled": len(disabled),
    }
    return outputs, materials_world, stats


def _inside(codes: NDArray[np.int8], x: float, y: float) -> bool:
    rows, columns = codes.shape
    column = int(x) // LOCATION_UNITS
    row = rows - 1 - int(y) // LOCATION_UNITS
    return 0 <= row < rows and 0 <= column < columns and bool(codes[row, column] != OUTSIDE)


def _disable_decals(store: DecalStore, codes: NDArray[np.int8]) -> tuple[dict[str, bytes], bytes]:
    """Disable mountain/volcano decals over the canvas in instances and in the cache."""
    kept: list[dict[str, object]] = []
    for entry in store.cache:
        name = str(entry["decal_name"])
        position = cast("dict[str, dict[str, float]]", entry["decal_transform"])["position"]
        if HEIGHTMAP.fullmatch(name) or not _inside(codes, position["x"], position["y"]):
            kept.append(entry)
    files: dict[str, bytes] = {}
    decals = store.game_dir / TERRAIN / "decals"
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
