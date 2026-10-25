"""Regenerate EU5 1.4.1 visual terrain under a generated New World.

Height and material decal layers that overlap the visual coast footprint are rebuilt. Heights follow
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
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass, field, replace
from itertools import pairwise
from typing import TYPE_CHECKING, Final, cast

import numpy as np

from rnw import _native
from rnw.eu5_slots import LEVELS, REACH, SlotTables, level_counts, synthesize
from rnw.noise import NOISE_SCALE
from rnw.parallel import band_rows, worker_count
from rnw.progress import checkpoint
from rnw.relief import COAST_HEIGHT
from rnw.rng import derive_seed
from rnw.terrain_tiles import LayerFormat, parse_info, read_level0, write_layer
from rnw.topology import distance_from

if TYPE_CHECKING:
    from collections.abc import Buffer, Callable, MutableMapping
    from pathlib import Path

    from numpy.typing import NDArray

TERRAIN: Final[str] = "game/in_game/gfx/terrain2"
DECAL_CACHE: Final[str] = f"{TERRAIN}/terrain_cache/ingame_decals.json"
LOCATION_UNITS: Final[int] = 4
# Location pixels of periodic source data beyond each primary map edge. On the
# installed 65536-unit terrain this covers coarse page borders and normal samples
# (C313). Primary placements keep their centres and most of their bounds in-world.
WRAP_PADDING: Final[int] = 512
HEIGHTMAP: Final[re.Pattern[str]] = re.compile(r"heightmap_\d+_\d+")
OUTSIDE: Final[int] = -1
DECAL_THREADS: Final[int] = 8
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


def _padded_decal(decal: Decal, width: int) -> Decal:
    left = WRAP_PADDING if decal.column0 == 0 else 0
    right = WRAP_PADDING if decal.column0 + decal.columns == width else 0
    return replace(decal, column0=decal.column0 - left, columns=decal.columns + left + right)


def _decal_layer(
    store: DecalStore, decal: Decal, kind: str
) -> tuple[LayerFormat, NDArray[np.uint16] | NDArray[np.uint8]]:
    """Initial samples of a primary placement, with periodic source support if needed."""
    layer, image = store.layer(decal.name, kind)
    if image.shape == (decal.rows * 2, decal.columns * 2):
        return layer, image
    original = next(item for item in store.decals if item.name == decal.name)
    if decal != _padded_decal(original, store.map_shape[1]) or image.shape != (
        original.rows * 2,
        original.columns * 2,
    ):
        message = f"Unexpected padded heightmap geometry for {decal.name}"
        raise TerrainRangeError(message)
    left = original.column0 - decal.column0
    right = decal.columns - original.columns - left
    pieces: list[NDArray[np.uint16] | NDArray[np.uint8]] = []
    for padding, is_left in ((left, True), (right, False)):
        if not padding:
            continue
        peers = [
            item
            for item in store.decals
            if item.row0 == original.row0
            and item.rows == original.rows
            and (
                item.column0 + item.columns == store.map_shape[1] if is_left else item.column0 == 0
            )
        ]
        if len(peers) != 1 or padding > peers[0].columns:
            message = f"Expected one opposite-edge heightmap for {decal.name}"
            raise TerrainRangeError(message)
        _, peer = store.layer(peers[0].name, kind)
        piece = peer[:, -padding * 2 :] if is_left else peer[:, : padding * 2]
        pieces.append(piece.copy())
        del peer
    if left:
        pieces.insert(1, image)
    else:
        pieces.insert(0, image)
    combined = cast("NDArray[np.uint16] | NDArray[np.uint8]", np.concatenate(pieces, axis=1))
    return replace(layer, width=decal.columns * 2), combined


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
    """Reads vanilla decal layers; a layer takes about 30 ms to decode, so none is kept.

    Holding the sixteen decoded heights and materials would take two gigabytes of the
    export's memory for under a second of decoding [V-EXEC C102].
    """

    game_dir: Path
    map_shape: tuple[int, int]
    cache: list[dict[str, object]] = field(init=False)
    decals: list[Decal] = field(init=False)

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

    def layer(
        self, decal: str, kind: str
    ) -> tuple[LayerFormat, NDArray[np.uint16] | NDArray[np.uint8]]:
        """Vanilla layer ``kind`` ("height" or "materials") of a decal, north-up, 16 or 8 bit."""
        _, info_path, bin_path = self.paths(decal, kind)
        layer, spans = parse_info(info_path.read_text(encoding="utf-8-sig"))
        image = read_level0(layer, spans, bin_path.read_bytes())
        if kind == "height":
            return layer, image.astype(np.uint16, copy=False)
        return layer, image.astype(np.uint8, copy=False)

    def world_heights(self) -> NDArray[np.uint16]:
        """Vanilla height at location resolution (one decal sample per location pixel)."""
        out = np.zeros(self.map_shape, dtype=np.uint16)
        for decal in self.decals:
            checkpoint()
            _, image = self.layer(decal.name, "height")
            out[
                decal.row0 : decal.row0 + decal.rows, decal.column0 : decal.column0 + decal.columns
            ] = image[1::2, 1::2]
        return out

    def world_materials(self) -> NDArray[np.uint8]:
        """All vanilla material layers on one grid with two pixels per location pixel."""
        out = np.full((self.map_shape[0] * 2, self.map_shape[1] * 2), 255, dtype=np.uint8)
        for decal in self.decals:
            checkpoint()
            _, image = self.layer(decal.name, "materials")
            out[
                decal.row0 * 2 : (decal.row0 + decal.rows) * 2,
                decal.column0 * 2 : (decal.column0 + decal.columns) * 2,
            ] = image
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
# The visual coast reaches beyond the location-colour boundary. Include the support
# of the shelf and materials (decal samples), plus height smoothing, in location pixels.
COAST_APRON: Final[int] = (max(REACH, WATER_PROFILE[-1][0] + COAST_SMOOTH + 2) + 1) // 2
# A decal is rebuilt in bands of whole location rows. Each band is computed in a window
# that reaches BAND_HALO rows past it: a height depends on locations at most CAP_REACH
# rows away (the coast cap), plus a row for the bilinear step and one for the blur, and
# the material rules look 17 decal pixels away, so no row of a band depends on the band
# size or on where its neighbours begin [V-EXEC C102].
BAND_HALO: Final[int] = CAP_REACH + 8
BAND_ROWS: Final[int] = 128
MIN_BAND_ROWS: Final[int] = 16
# Working memory of a band per location pixel of its window [V-EXEC C102].
BAND_BYTES: Final[int] = 600


@dataclass(frozen=True, slots=True, eq=False)
class Window:
    """A decal plus margin, in location pixels, and the decal's offset inside it."""

    row0: int
    row1: int
    column0: int
    column1: int
    inner_row: int
    inner_column: int


def decal_heights(  # noqa: PLR0913 - a window, its seed and origin, and the core to compute.
    codes: NDArray[np.int8],
    vanilla_water: NDArray[np.bool_],
    relief: NDArray[np.int32] | NDArray[np.int64],
    *,
    seed: int,
    origin: tuple[int, int],
    core: tuple[slice, slice] | None = None,
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.int64]]:
    """Land mask of a decal window and canvas mask and generated heights of its core.

    The inputs are at location resolution, the results at decal resolution. Heights are
    relief plus detail under a coastal cap, so beaches are low and ranges rise from them
    without a terrace; water follows the vanilla shelf profile. ``core`` (row and column
    slices of the decal-resolution window, all of it by default) limits the canvas mask and
    the heights, and with them the noise and the per-pixel rules, to those pixels; the
    distance fields always cover the window. The kernel is Rust (ADR 0005), its NumPy
    specification is ``tests/reference/terrain.py``.
    """
    rows, columns = core if core is not None else (slice(None), slice(None))
    row0, row1, _ = rows.indices(int(codes.shape[0]) * 2)
    column0, column1, _ = columns.indices(int(codes.shape[1]) * 2)
    params = {
        "coast_smooth": COAST_SMOOTH,
        "cap_reach": CAP_REACH,
        "eighths": EIGHTHS,
        "coast_height": COAST_HEIGHT,
        "detail_period": DETAIL_PERIOD,
        "crest_period": CREST_PERIOD,
        "noise_scale": NOISE_SCALE,
        "detail_base": DETAIL_BASE,
        "detail_permille": DETAIL_PERMILLE,
        "crest_full": CREST_FULL,
        "crest_height": CREST_HEIGHT,
        "shore_height": SHORE_HEIGHT,
        "cap_slope": CAP_SLOPE,
    }
    return _native.decal_heights(
        np.ascontiguousarray(codes, dtype=np.int8),
        np.ascontiguousarray(vanilla_water, dtype=np.bool_),
        np.ascontiguousarray(relief, dtype=np.int64),
        (derive_seed(seed, "terrain_detail"), derive_seed(seed, "terrain_crests")),
        origin,
        list(WATER_PROFILE),
        WATER_PROFILE[-1][0] + 1,
        params,
        (row0, row1 - row0, column0, column1 - column0),
    )


def level_shares(
    store: DecalStore, labels: NDArray[np.int32], group: NDArray[np.int64], groups: int
) -> NDArray[np.int64]:
    """Interior variation-level counts per label group over every vanilla decal."""
    counts = np.zeros((groups, LEVELS), dtype=np.int64)
    for decal in store.decals:
        checkpoint()
        _, materials = store.layer(decal.name, "materials")
        crop = labels[
            decal.row0 : decal.row0 + decal.rows, decal.column0 : decal.column0 + decal.columns
        ]
        counts += level_counts(materials, crop, group, groups)
    return counts


@dataclass(frozen=True, slots=True, eq=False)
class TerrainInputs:
    """World-sized rasters that drive the rebuilt decals (location resolution).

    ``relief(rows, columns)`` gives the generated relief of a window of the world, zero off
    the canvas; the rest are whole-world rasters.
    """

    codes: NDArray[np.int8]
    vanilla_water: NDArray[np.bool_]
    relief: Callable[[slice, slice], NDArray[np.int32]]
    labels: NDArray[np.int32]
    rivers: NDArray[np.bool_]
    noise_roll: int = 0


class TerrainRangeError(ValueError):
    """A generated sample does not fit the decal layer it is written to."""


def coast_codes(codes: NDArray[np.int8], vanilla_water: NDArray[np.bool_]) -> NDArray[np.int8]:
    """The visual footprint of changed shores, including adjacent original water.

    Location colours do not describe the whole original shelf. Replacing an island
    without its offshore height/material samples leaves a raised rim on that boundary.
    This window-sized input mask includes the coast's support before synthesis; it
    never changes retained land or location identities. Horizontal halos are supplied
    by the caller, exactly as for coast distances and material sampling.
    """
    changed = (codes != OUTSIDE) & ((codes == WATER_CODE) != vanilla_water)
    if not np.any(changed):
        return codes
    near = distance_from(changed, COAST_APRON + 1, octagonal=True) <= COAST_APRON
    result = codes.copy()
    result[(codes == OUTSIDE) & vanilla_water & near] = WATER_CODE
    return result


def _band_window(decal: Decal, shape: tuple[int, int], first: int, last: int) -> Window:
    """The window that computes rows ``first`` to ``last`` (of the decal) of one decal."""
    row0 = max(0, decal.row0 + first - BAND_HALO)
    column0 = decal.column0 - MARGIN
    return Window(
        row0,
        min(shape[0], decal.row0 + last + BAND_HALO),
        column0,
        decal.column0 + decal.columns + MARGIN,
        (decal.row0 + first - row0) * 2,
        (decal.column0 - column0) * 2,
    )


def _write_where(
    target: NDArray[np.uint16] | NDArray[np.uint8],
    values: NDArray[np.integer],
    mask: NDArray[np.bool_],
) -> None:
    """Copy ``values`` into ``target`` where ``mask`` holds, refusing values that do not fit."""
    limit = int(np.iinfo(target.dtype).max)
    chosen = values[mask]
    if chosen.size and (int(chosen.min()) < 0 or int(chosen.max()) > limit):
        message = f"generated samples {chosen.min()}..{chosen.max()} do not fit {target.dtype}"
        raise TerrainRangeError(message)
    np.copyto(target, values, where=mask, casting="unsafe")


def _rebuild_band(  # noqa: PLR0913 - a band reads the decal, its rows, the inputs and the images.
    decal: Decal,
    *,
    first: int,
    last: int,
    inputs: TerrainInputs,
    tables: SlotTables,
    seed: int,
    images: tuple[NDArray[np.uint16], NDArray[np.uint8]],
) -> None:
    """Heights and material slots of rows ``first`` to ``last`` of a decal, into ``images``."""
    codes = inputs.codes
    window = _band_window(decal, (int(codes.shape[0]), int(codes.shape[1])), first, last)
    rows = slice(window.row0, window.row1)
    width = int(codes.shape[1])
    columns = np.arange(window.column0, window.column1, dtype=np.int64) % width
    local_water = inputs.vanilla_water[rows][:, columns]
    local_codes = coast_codes(codes[rows][:, columns], local_water)
    relief = inputs.relief(rows, slice(window.column0, window.column1))
    labels = np.repeat(np.repeat(inputs.labels[rows][:, columns], 2, axis=0), 2, axis=1)
    rivers = np.repeat(np.repeat(inputs.rivers[rows][:, columns], 2, axis=0), 2, axis=1)
    # The noise lives in the same rolled coordinates as the land. Its cut is at
    # the canvas's outside edge, not the world seam. Split a decal at that cut so
    # neither a sampling window nor a noise origin restarts at the world wrap.
    cut = (-inputs.noise_roll) % width
    breaks = [0, decal.columns]
    breaks.extend(
        cut + shift - decal.column0
        for shift in (-width, 0, width)
        if decal.column0 < cut + shift < decal.column0 + decal.columns
    )
    breaks.sort()
    for left, right in pairwise(breaks):
        core = (
            slice(window.inner_row, window.inner_row + (last - first) * 2),
            slice(window.inner_column + left * 2, window.inner_column + right * 2),
        )
        origin = (
            ((decal.column0 + left + inputs.noise_roll) % width) * 2
            - (window.inner_column + left * 2),
            window.row0 * 2,
        )
        land, inside, heights = decal_heights(
            local_codes, local_water, relief, seed=seed, origin=origin, core=core
        )
        target = (slice(first * 2, last * 2), slice(left * 2, right * 2))
        height_image, material_image = images
        _write_where(height_image[target], heights, inside)
        del heights
        slots = synthesize(labels, land, rivers, tables, seed=seed, origin=origin, core=core)
        _write_where(material_image[target], slots, inside)


def _rebuild_decal(  # noqa: PLR0913 - a decal reads the store, the inputs, the tables and the bands.
    decal: Decal,
    store: DecalStore,
    inputs: TerrainInputs,
    tables: SlotTables,
    *,
    seed: int,
    pool: ThreadPoolExecutor,
    band: int,
) -> tuple[dict[str, bytes], NDArray[np.uint8]]:
    """The mod files and the material image of one decal over the canvas.

    The decal is cut into bands of ``band`` location rows that run on ``pool``; the files
    are the same for any band size.
    """
    height_layer, vanilla_height = _decal_layer(store, decal, "height")
    material_layer, vanilla_materials = _decal_layer(store, decal, "materials")
    height_image = np.array(vanilla_height, dtype=np.uint16)
    material_image = np.array(vanilla_materials, dtype=np.uint8)
    rows = decal.rows
    spans = [(first, min(rows, first + band)) for first in range(0, rows, band)]

    def rebuild(span: tuple[int, int]) -> None:
        checkpoint()
        _rebuild_band(
            decal,
            first=span[0],
            last=span[1],
            inputs=inputs,
            tables=tables,
            seed=seed,
            images=(height_image, material_image),
        )

    for _ in pool.map(rebuild, spans):
        pass
    outputs: dict[str, bytes] = {}
    for kind, image, layer in (
        ("height", height_image, height_layer),
        ("materials", material_image, material_layer),
    ):
        stem, _, _ = store.paths(decal.name, kind)
        info, data = write_layer(image, layer)
        outputs[f"{stem}.info"] = info.encode("utf-8")
        outputs[f"{stem}.bin"] = data
    return outputs, material_image


def terrain_outputs(
    store: DecalStore,
    inputs: TerrainInputs,
    tables: SlotTables,
    seed: int,
    sink: MutableMapping[str, Buffer],
) -> tuple[NDArray[np.uint8], dict[str, object]]:
    """Mod files for every decal layer touched by the canvas, plus decal disabling.

    ``inputs.codes`` is -1 outside the location canvas, 0 for water and 1 for land.
    Changed shores also include their original offshore visual support. The files go
    into ``sink`` as each decal is done, so they do not pile up in memory; returns the
    final material raster (two pixels per location pixel) and statistics. Each decal is
    rebuilt in bands on a few threads, sized to the cores and to the free memory; the
    files and the raster are the same for any size and any number.
    """
    codes = inputs.codes
    materials_world = store.world_materials()
    plans = [_padded_decal(decal, store.map_shape[1]) for decal in store.decals]
    touched = [
        plan
        for plan, original in zip(plans, store.decals, strict=True)
        if plan != original or _touches_coast(plan, codes)
    ]
    columns = max((decal.columns for decal in touched), default=0) + 2 * MARGIN
    thin = BAND_BYTES * columns * (2 * BAND_HALO + MIN_BAND_ROWS)
    workers = worker_count(DECAL_THREADS, bytes_each=thin)
    window = band_rows(
        BAND_BYTES * columns,
        workers=workers,
        floor=2 * BAND_HALO + MIN_BAND_ROWS,
        ceiling=2 * BAND_HALO + BAND_ROWS,
    )
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for decal in touched:
            checkpoint()
            files, image = _rebuild_decal(
                decal, store, inputs, tables, seed=seed, pool=pool, band=window - 2 * BAND_HALO
            )
            sink.update(files)
            del files
            left, right = (
                max(0, decal.column0),
                min(store.map_shape[1], decal.column0 + decal.columns),
            )
            materials_world[
                decal.row0 * 2 : (decal.row0 + decal.rows) * 2, left * 2 : right * 2
            ] = image[:, (left - decal.column0) * 2 : (right - decal.column0) * 2]
    disabled, cache_out = _disable_decals(store, codes)
    sink.update(disabled)
    sink["in_game/gfx/terrain2/terrain_cache/ingame_decals.json"] = cache_out
    padded = sum(plan != original for plan, original in zip(plans, store.decals, strict=True))
    stats: dict[str, object] = {
        "decals_rebuilt": [decal.name for decal in touched],
        "mountain_decals_disabled": len(disabled) - padded,
        "periodic_heightmap_instances": 0,
        "padded_heightmaps": padded,
    }
    return materials_world, stats


def _touches_coast(decal: Decal, codes: NDArray[np.int8]) -> bool:
    """A neighbouring decal can contain the offshore support of a replaced coast."""
    rows, columns = codes.shape
    row0 = max(0, decal.row0 - COAST_APRON)
    row1 = min(rows, decal.row0 + decal.rows + COAST_APRON)
    for shift in (-columns, 0, columns):
        left = max(0, decal.column0 - COAST_APRON + shift)
        right = min(columns, decal.column0 + decal.columns + COAST_APRON + shift)
        if left < right and np.any(codes[row0:row1, left:right] != OUTSIDE):
            return True
    return False


def _inside(codes: NDArray[np.int8], x: float, y: float) -> bool:
    rows, columns = codes.shape
    column = int(x) // LOCATION_UNITS
    row = rows - 1 - int(y) // LOCATION_UNITS
    return 0 <= row < rows and 0 <= column < columns and bool(codes[row, column] != OUTSIDE)


def _wrapped_heightmaps(store: DecalStore) -> tuple[dict[str, dict[str, object]], dict[str, bytes]]:
    """Extend primary edge bounds over periodic source pixels, including cache rebuilds.

    These placements overlap the map's edge grid cells, while their outside support
    contains the opposite edge's actual terrain. No extra outside-only placement is
    needed. Cache geometry and the existing active editor instance stay identical.
    """
    width = store.map_shape[1] * LOCATION_UNITS
    entries: dict[str, dict[str, object]] = {}
    files: dict[str, bytes] = {}
    for entry in store.cache:
        name = str(entry["decal_name"])
        if not HEIGHTMAP.fullmatch(name):
            continue
        transform = cast("dict[str, object]", entry["decal_transform"])
        position = cast("dict[str, float]", transform["position"])
        scale = cast("dict[str, float]", transform["scale"])
        size = cast("dict[str, int]", entry["decal_size"])
        half = size["x"] * scale["x"] / 2
        left = WRAP_PADDING if position["x"] - half == 0 else 0
        right = WRAP_PADDING if position["x"] + half == width else 0
        if not (left or right):
            continue
        folder = store.game_dir / TERRAIN / "decals" / name / "instances"
        instances = [
            (path, json.loads(path.read_text(encoding="utf-8-sig")))
            for path in sorted(folder.glob("*.json"))
        ]
        active = [(path, item) for path, item in instances if item.get("disabled") is False]
        if len(active) != 1 or transform.get("rotation") != 0 or scale["x"] != 2:  # noqa: PLR2004
            message = f"Expected one unrotated edge heightmap instance at scale 2 for {name}"
            raise TerrainRangeError(message)
        path, raw_instance = active[0]
        instance = cast("dict[str, object]", raw_instance)
        geometry = {
            "position.x": position["x"],
            "position.y": position["y"],
            "scale.x": scale["x"],
            "scale.y": scale["y"],
            "rotation": 0,
        }
        if any(instance.get(key) != value for key, value in geometry.items()):
            message = f"Heightmap instance and cached geometry disagree for {name}"
            raise TerrainRangeError(message)
        moved = deepcopy(entry)
        moved_transform = cast("dict[str, object]", moved["decal_transform"])
        shift = (right - left) * LOCATION_UNITS / 2
        cast("dict[str, float]", moved_transform["position"])["x"] += shift
        cast("dict[str, int]", moved["decal_size"])["x"] += (left + right) * LOCATION_UNITS // 2
        entries[name] = moved
        moved_instance = instance | {"position.x": position["x"] + shift}
        relative = f"in_game/gfx/terrain2/decals/{name}/instances/{path.name}"
        files[relative] = ("\ufeff" + json.dumps(moved_instance, indent="\t") + "\n").encode(
            "utf-8"
        )
    if not entries:
        message = "No edge heightmaps were found for periodic source support"
        raise TerrainRangeError(message)
    return entries, files


def _disable_decals(store: DecalStore, codes: NDArray[np.int8]) -> tuple[dict[str, bytes], bytes]:
    """Extend primary heightmaps and disable obsolete mountains in instances and cache."""
    kept: list[dict[str, object]] = []
    wrapped, files = _wrapped_heightmaps(store)
    for entry in store.cache:
        name = str(entry["decal_name"])
        position = cast("dict[str, dict[str, float]]", entry["decal_transform"])["position"]
        if HEIGHTMAP.fullmatch(name) or not _inside(codes, position["x"], position["y"]):
            kept.append(wrapped.get(name, entry))
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
