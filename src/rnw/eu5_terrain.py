"""Regenerate EU5 1.4.1 visual terrain under a generated New World.

Height and material decal layers that overlap the visual coast footprint are rebuilt. Heights follow
the vanilla coast profile at the shore and the continuous relief field inland (the same
field that set cell topography), with fine detail noise whose amplitude grows with
height and overlapping vanilla mountain height detail on the generated ranges. Materials
are biome slots rebuilt from the location data by the vanilla rules
(``eu5_slots.py``), so each location's biome, coast, borders and rivers render the way
vanilla does; on the mountains the stamps' own slots lay the eroded pattern of their valleys
over the variations (``_lay_stamp_slots``). Mountain and volcano decals inside the canvas are
disabled in their instance files and in the decal cache. Values marked [V-EXEC] were measured
on build 25905365.
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
from typing import TYPE_CHECKING, Final, cast, override

import numpy as np

from rnw import _native
from rnw.eu5_mountains import CAP, FULL, LOW
from rnw.eu5_slots import (
    CLIMATE_BORDER,
    COAST_TRANSITION,
    LEVELS,
    NO_MATERIAL,
    REACH,
    TOPOGRAPHY_BORDER,
    VARIATION,
    SlotTables,
    level_counts,
    slot_remap,
    synthesize,
)
from rnw.fields import PERMILLE
from rnw.land_contact import MATERIAL_REACH, soften_rim
from rnw.noise import NOISE_SCALE, fractal_noise
from rnw.parallel import band_rows, worker_count
from rnw.progress import checkpoint
from rnw.relief import COAST_HEIGHT
from rnw.rng import derive_seed
from rnw.terrain_tiles import LayerFormat, parse_info, read_level0, write_layer
from rnw.timing import measured
from rnw.topology import distance_from

if TYPE_CHECKING:
    from collections.abc import Buffer, Callable, MutableMapping
    from pathlib import Path

    from numpy.typing import NDArray

    from rnw.eu5_islands import Moved
    from rnw.eu5_mountains import MountainRelief
    from rnw.land_contact import ContactBlend

TERRAIN: Final[str] = "game/in_game/gfx/terrain2"
DECAL_CACHE: Final[str] = f"{TERRAIN}/terrain_cache/ingame_decals.json"
LOCATION_UNITS: Final[int] = 4
# Location pixels of periodic source data beyond each primary map edge. On the
# installed 65536-unit terrain this covers coarse page borders and normal samples
# (C313). Primary placements keep their centres and most of their bounds in-world.
WRAP_PADDING: Final[int] = 512
HEIGHTMAP: Final[re.Pattern[str]] = re.compile(r"heightmap_\d+_\d+")
OUTSIDE: Final[int] = -1
DECAL_THREADS: Final[int] = 4
WATER_CODE: Final[int] = 0
LAND_CODE: Final[int] = 1
# Fine grain of the ground: a fractal from 64 down to 4 decal pixels whose octaves fall by
# a quarter each, the roughness exponent of the installed heightmaps (their mean height
# difference grows with distance to a power of about 0.4--0.6), with an amplitude that grows
# with height above the coast up to ``DETAIL_REACH`` units [V-EXEC 2026-10-30].
DETAIL_PERIOD: Final[int] = 64
DETAIL_OCTAVES: Final[int] = 5
DETAIL_PERSISTENCE: Final[int] = 750
DETAIL_BASE: Final[int] = 600
DETAIL_PERMILLE: Final[int] = 600
DETAIL_REACH: Final[int] = 7500
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

    def height_window(self, rows: slice, columns: NDArray[np.int64]) -> NDArray[np.uint16]:
        """Read only the primary decals intersecting a retained land boundary."""
        out = np.zeros((rows.stop - rows.start, columns.size), dtype=np.uint16)
        for decal in self.decals:
            top = max(rows.start, decal.row0)
            bottom = min(rows.stop, decal.row0 + decal.rows)
            within = (columns >= decal.column0) & (columns < decal.column0 + decal.columns)
            if top < bottom and within.any():
                checkpoint()
                _, image = self.layer(decal.name, "height")
                vertical = slice(2 * (top - decal.row0) + 1, 2 * (bottom - decal.row0), 2)
                horizontal = (columns[within] - decal.column0) * 2 + 1
                out[top - rows.start : bottom - rows.start, within] = image[vertical, horizontal]
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


@dataclass(eq=False)
class ShiftedStore(DecalStore):
    """A decal store whose layers show the moved island groups where they now stand.

    The height and material pixels of a moved group are copied to its new place, two decal
    pixels to each location pixel; the old place keeps what it had, because it lies inside
    the canvas and is generated over.
    """

    moved: Moved | None = None

    @override
    def layer(
        self, decal: str, kind: str
    ) -> tuple[LayerFormat, NDArray[np.uint16] | NDArray[np.uint8]]:
        """Vanilla layer ``kind`` of a decal, with the moved groups' pixels at their new places."""
        layer, image = super().layer(decal, kind)
        if self.moved is None:
            return layer, image
        placed = next((item for item in self.decals if item.name == decal), None)
        if placed is None:
            return layer, image
        moved = self.moved
        rows, columns = moved.new_rows, moved.new_columns
        here = (
            (rows >= placed.row0)
            & (rows < placed.row0 + placed.rows)
            & (columns >= placed.column0)
            & (columns < placed.column0 + placed.columns)
        )
        if not here.any():
            return layer, image
        # A placement's membership and coordinates do not depend on the four
        # subpixels. Read one original layer at a time, and retain the original
        # placement/duplicate-write order for each independent subpixel.
        source_rows, source_columns = moved.rows[here], moved.columns[here]
        target_rows = 2 * (rows[here] - placed.row0)
        target_columns = 2 * (columns[here] - placed.column0)
        for origin in self.decals:
            inside = (
                (source_rows >= origin.row0)
                & (source_rows < origin.row0 + origin.rows)
                & (source_columns >= origin.column0)
                & (source_columns < origin.column0 + origin.columns)
            )
            if not inside.any():
                continue
            original = DecalStore.layer(self, origin.name, kind)[1]
            sy = 2 * (source_rows[inside] - origin.row0)
            sx = 2 * (source_columns[inside] - origin.column0)
            ty, tx = target_rows[inside], target_columns[inside]
            for sub_row in range(2):
                for sub_column in range(2):
                    image[ty + sub_row, tx + sub_column] = original[sy + sub_row, sx + sub_column]
        return layer, image


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
BAND_ROWS: Final[int] = 256
MIN_BAND_ROWS: Final[int] = 16
# Working memory per location pixel of a band window: the original 600-byte
# allowance (C102), plus distance, gain and sampled mountain-detail arrays.
BAND_BYTES: Final[int] = 800


@dataclass(frozen=True, slots=True, eq=False)
class Window:
    """A decal plus margin, in location pixels, and the decal's offset inside it."""

    row0: int
    row1: int
    column0: int
    column1: int
    inner_row: int
    inner_column: int


@measured
def decal_heights(  # noqa: PLR0913 - a window, its seed and origin, and the core to compute.
    codes: NDArray[np.int8],
    vanilla_water: NDArray[np.bool_],
    relief: NDArray[np.int32] | NDArray[np.int64],
    *,
    seed: int,
    origin: tuple[int, int],
    core: tuple[slice, slice] | None = None,
    sampled: bool = False,
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.int64]]:
    """Land mask of a decal window and canvas mask and generated heights of its core.

    The inputs are at location resolution, the results at decal resolution. Heights are
    relief plus detail under a coastal cap, so beaches are low and ranges rise from them
    without a terrace; water follows the vanilla shelf profile. ``core`` (row and column
    slices of the decal-resolution window, all of it by default) limits the canvas mask and
    the heights, and with them the noise and the per-pixel rules, to those pixels; the
    distance fields always cover the window. ``sampled`` evaluates only the odd rows and
    columns consumed by the ground survey; it is identical to slicing the full result
    with ``[1::2, 1::2]``. The kernel is Rust (ADR 0005), its NumPy
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
        "detail_octaves": DETAIL_OCTAVES,
        "detail_persistence": DETAIL_PERSISTENCE,
        "detail_reach": DETAIL_REACH,
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
        sampled,
    )


# The ground of the land is voted on the height its decals show (epoch 64, ``epoch.ROUGH_HILLS``):
# vanilla's locations are read from its primary heightmaps, which hold no mountain stamps (those
# are decals of their own), so the generated land is read from the primary height the decals write,
# its relief, detail and coastal cap, without the stamps baked into them. On the relief alone hill
# country read three times smoother than vanilla's and only 82 permille of the land of world
# t2f5i5zcnr was hills; on the written primary heights 140 (vanilla 217) [V-EXEC 2026-11-14].
SURFACE_COLUMNS: Final[int] = 2048  # core columns of one window of ``surface_heights``


@measured
def surface_heights(
    codes: NDArray[np.int8],
    vanilla_water: NDArray[np.bool_],
    relief: NDArray[np.int32],
    *,
    seed: int,
) -> NDArray[np.uint16]:
    """The primary height the decals write over a canvas, one sample per location pixel.

    The rasters are in the canvas's rolled coordinates, where the decals lay their detail noise
    at twice the column and the row (``TerrainInputs.noise_roll``). ``codes`` (``OUTSIDE``,
    ``WATER_CODE``, ``LAND_CODE``) and ``vanilla_water`` carry ``MARGIN`` columns of the map on
    either side of the canvas, which ``relief`` (zero off the land) spans. The samples are those
    ``_rebuild_band`` writes before the mountain stamps (``decal_heights``: relief plus detail
    under the coastal cap), at the odd decal pixels, as ``DecalStore.world_heights`` reads
    vanilla's; zero off the canvas. Computed in the windows of the decals, bands of rows and
    ``SURFACE_COLUMNS`` columns on a few threads; the result is the same for any.
    """
    rows, span = (int(size) for size in relief.shape)
    if codes.shape != (rows, span + 2 * MARGIN) or vanilla_water.shape != codes.shape:
        message = "The canvas codes do not reach the margin on either side of its relief"
        raise ValueError(message)
    out = np.zeros((rows, span), dtype=np.uint16)
    chunk = max(1, min(span, SURFACE_COLUMNS))
    columns = chunk + 2 * MARGIN
    workers = worker_count(
        DECAL_THREADS, bytes_each=BAND_BYTES * columns * (2 * BAND_HALO + MIN_BAND_ROWS)
    )
    band = (
        band_rows(
            BAND_BYTES * columns,
            workers=workers,
            floor=2 * BAND_HALO + MIN_BAND_ROWS,
            ceiling=2 * BAND_HALO + BAND_ROWS,
        )
        - 2 * BAND_HALO
    )
    limit = int(np.iinfo(np.uint16).max)

    def run(piece: tuple[int, int, int, int]) -> None:
        checkpoint()
        first, last, left, right = piece
        row0, row1 = max(0, first - BAND_HALO), min(rows, last + BAND_HALO)
        window = (slice(row0, row1), slice(left, right + 2 * MARGIN))
        # The relief of the window's canvas columns; its margins matter only to the bilinear
        # step at the canvas's edge, where the map is not generated.
        height = np.zeros((row1 - row0, right - left + 2 * MARGIN), dtype=np.int32)
        low, high = max(0, left - MARGIN), min(span, right + MARGIN)
        height[:, low - left + MARGIN : high - left + MARGIN] = relief[row0:row1, low:high]
        water = vanilla_water[window]
        core = (
            slice((first - row0) * 2, (last - row0) * 2),
            slice(2 * MARGIN, 2 * (MARGIN + right - left)),
        )
        _, inside, heights = decal_heights(
            coast_codes(codes[window], water),
            water,
            height,
            seed=seed,
            origin=(2 * (left - MARGIN), 2 * row0),
            core=core,
            sampled=True,
        )
        samples = heights
        shown = inside
        chosen = samples[shown]
        if chosen.size and (int(chosen.min()) < 0 or int(chosen.max()) > limit):
            message = f"primary heights {chosen.min()}..{chosen.max()} do not fit the layer"
            raise TerrainRangeError(message)
        out[first:last, left:right] = np.where(shown, samples, 0)

    pieces = [
        (first, min(rows, first + band), left, min(span, left + chunk))
        for first in range(0, rows, band)
        for left in range(0, span, chunk)
    ]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for _ in pool.map(run, pieces):
            pass
    return out


def land_surface(
    land: NDArray[np.bool_], relief: NDArray[np.int32], *, seed: int
) -> NDArray[np.uint16]:
    """``surface_heights`` of a generated land before it lies on the map (its rolled canvas
    coordinates): what is not land is the decals' water, and nothing lies beyond its edges."""
    codes = np.pad(
        np.where(land, LAND_CODE, WATER_CODE).astype(np.int8),
        ((0, 0), (MARGIN, MARGIN)),
        constant_values=OUTSIDE,
    )
    return surface_heights(codes, codes == WATER_CODE, relief, seed=seed)


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
    mountains: MountainRelief | None = None
    moved: Moved | None = None
    contact: ContactBlend | None = None


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


@measured
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


@measured
def _lay_stamp_slots(
    slots: NDArray[np.uint8],
    stamped: NDArray[np.uint8],
    labels: NDArray[np.int32],
    tables: SlotTables,
) -> NDArray[np.uint8]:
    """Blend the mountain stamps' slots in as vanilla's ``min`` mode does: the lower slot wins.

    Coasts, rivers and borders (slots 0--9) stay; the stamps turn the variations into their
    eroded pattern of valleys and crests. A biome that lists fewer materials than the slot needs
    takes the slot its list can hold, as every written slot does, and one that lists no
    variation at all keeps what it has.
    """
    return _native.stamp_slots(
        np.ascontiguousarray(slots),
        np.ascontiguousarray(stamped),
        np.ascontiguousarray(labels),
        np.ascontiguousarray(tables.materials),
        np.ascontiguousarray(slot_remap()).ravel(),
    )


def _contact_window(
    contact: ContactBlend, shape: tuple[int, ...], *, first: int, column: int, width: int
) -> tuple[tuple[NDArray[np.int64], NDArray[np.int64]], slice, NDArray[np.int64]] | None:
    """The contact box's location pixels within a ``shape`` (decal pixels) window of the map.

    The window's top row is location row ``first`` and its left column ``column``, wrapping at
    ``width``. Returns the box's index grid over those pixels, the decal rows they cover and
    the decal columns (two for each location pixel); None when the window misses the box.
    """
    rows, columns = contact.box
    top = max(first, rows.start)
    bottom = min(first + shape[0] // 2, rows.stop)
    if top >= bottom:
        return None
    across = np.arange(column, column + shape[1] // 2, dtype=np.int64)
    across = (across - int(columns.start)) % width
    local = np.flatnonzero(across < columns.stop - columns.start)
    if not local.size:
        return None
    indices = np.ix_(
        np.arange(top - int(rows.start), bottom - int(rows.start), dtype=np.int64), across[local]
    )
    return (
        indices,
        slice(2 * (top - first), 2 * (bottom - first)),
        (2 * local[:, None] + np.arange(2)).ravel(),
    )


def _fine_at(
    fine: NDArray[np.generic], indices: tuple[NDArray[np.int64], NDArray[np.int64]]
) -> NDArray[np.int64]:
    """The decal-resolution samples of a contact array at the pixels of an index grid."""
    rows, columns = (2 * grid.reshape(-1)[:, None] + np.arange(2) for grid in indices)
    return fine[np.ix_(rows.reshape(-1), columns.reshape(-1))].astype(np.int64)


def _contact_columns(
    contact: ContactBlend | None, decal: Decal, first: int, last: int, width: int
) -> NDArray[np.bool_]:
    active = np.zeros(decal.columns, dtype=bool)
    if contact is not None:
        window = _contact_window(
            contact,
            ((last - first) * 2, decal.columns * 2),
            first=decal.row0 + first,
            column=decal.column0,
            width=width,
        )
        if window is not None:
            indices, _, columns = window
            active[columns[::2] // 2] = contact.retouch[indices].any(axis=0)
    return active


def _contact_decals(
    contact: ContactBlend,
    image: NDArray[np.uint16],
    *,
    first: int,
    column: int,
    width: int,
) -> None:
    """Blend the generated and retained heights to one surface along the join."""
    window = _contact_window(contact, image.shape, first=first, column=column, width=width)
    if window is None:
        return
    indices, decal_rows, decal_cols = window
    weight = _fine_at(contact.fine_weight, indices)
    target = _fine_at(contact.fine_target, indices)
    samples = image[decal_rows, decal_cols].astype(np.int64)
    image[decal_rows, decal_cols] = (
        (samples * (PERMILLE - weight) + target * weight) // PERMILLE
    ).astype(np.uint16)


def _contact_materials(  # noqa: PLR0913 - join, decal window, biome slots and absolute noise.
    contact: ContactBlend,
    image: NDArray[np.uint8],
    labels: NDArray[np.int32],
    tables: SlotTables,
    *,
    first: int,
    column: int,
    width: int,
    seed: int,
) -> None:
    """Feather out the biome-border stripe and remnants of the old beach on dry ground."""
    window = _contact_window(contact, image.shape, first=first, column=column, width=width)
    if window is None:
        return
    indices, rows, columns = window
    distance = np.repeat(np.repeat(contact.distance[indices], 2, axis=0), 2, axis=1)
    near = distance <= MATERIAL_REACH + 4
    if not near.any():
        return
    weight = _fine_at(contact.fine_weight, indices)
    samples = image[rows, columns]
    boundary = (samples >= TOPOGRAPHY_BORDER) & (samples <= CLIMATE_BORDER)
    retained = np.repeat(np.repeat(contact.retained[indices], 2, axis=0), 2, axis=1)
    old_beach = retained & (samples <= COAST_TRANSITION)
    noise = fractal_noise(
        derive_seed(seed, "junction_materials"),
        2 * column,
        2 * first + rows.start,
        image.shape[1],
        rows.stop - rows.start,
        period=24,
        octaves=2,
        persistence_permille=500,
    )[:, columns]
    edit = near & (weight > PERMILLE // 2) & (boundary | old_beach)
    edit &= distance <= MATERIAL_REACH + noise * 8 // NOISE_SCALE
    variations = VARIATION + (noise[edit] + NOISE_SCALE) * 6 // (2 * NOISE_SCALE)
    number = tables.materials[labels[rows, columns][edit]]
    samples[edit] = slot_remap()[number.clip(0, slot_remap().shape[0] - 1), variations]
    image[rows, columns] = samples


def _contact_rim(
    contact: ContactBlend,
    image: NDArray[np.uint16],
    *,
    first: int,
    column: int,
    width: int,
) -> None:
    """Take the cliffs the generated sea cut out of the retained shore in the written heights."""
    window = _contact_window(contact, image.shape, first=first, column=column, width=width)
    if window is None:
        return
    indices, decal_rows, decal_cols = window
    samples = image[decal_rows, decal_cols].astype(np.int64)
    image[decal_rows, decal_cols] = soften_rim(samples, _fine_at(contact.fine_rim, indices)).astype(
        np.uint16
    )


@measured
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
    # Take whole rows in memory order; advanced column indexing stores this large
    # gather in column-major order and makes the native kernel copy it back again.
    local_water = np.take(inputs.vanilla_water[rows], columns, axis=1)
    local_codes = coast_codes(np.take(codes[rows], columns, axis=1), local_water)
    # Nothing is written outside this exact mask. Keep the normal halo around its
    # horizontal bounding box, so every retained distance/noise sample is unchanged.
    core_row = window.inner_row // 2
    core_column = window.inner_column // 2
    written = (
        local_codes[
            core_row : core_row + last - first,
            core_column : core_column + decal.columns,
        ]
        != OUTSIDE
    )
    active = np.flatnonzero(
        written.any(axis=0) | _contact_columns(inputs.contact, decal, first, last, width)
    )
    if not active.size:
        return
    left, right = int(active[0]), int(active[-1]) + 1
    if left or right < decal.columns:
        narrowed = replace(decal, column0=decal.column0 + left, columns=right - left)
        _rebuild_band(
            narrowed,
            first=first,
            last=last,
            inputs=inputs,
            tables=tables,
            seed=seed,
            images=(images[0][:, left * 2 : right * 2], images[1][:, left * 2 : right * 2]),
        )
        return
    relief = inputs.relief(rows, slice(window.column0, window.column1))
    labels = np.repeat(
        np.repeat(np.take(inputs.labels[rows], columns, axis=1), 2, axis=0), 2, axis=1
    )
    rivers = np.repeat(
        np.repeat(np.take(inputs.rivers[rows], columns, axis=1), 2, axis=0), 2, axis=1
    )
    river_reach = (
        distance_from(rivers, 12, octagonal=True) if inputs.mountains is not None else None
    )
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
        stamped = None
        if inputs.mountains is not None and river_reach is not None:
            window_origin = (origin[0] + core[1].start, origin[1] + core[0].start)
            detail, laid = inputs.mountains.stamp(window_origin, heights.shape)
            # The stamps' own slots show where their heights do: on the mountains.
            try:
                heights, stamped = _native.blend_mountains(
                    np.ascontiguousarray(heights),
                    np.ascontiguousarray(inside),
                    np.ascontiguousarray(detail),
                    np.ascontiguousarray(laid),
                    np.ascontiguousarray(river_reach[core]),
                    (LOW, FULL, CAP),
                    NO_MATERIAL,
                )
            except _native.TerrainRangeError as error:
                raise TerrainRangeError(str(error)) from error
        target = (slice(first * 2, last * 2), slice(left * 2, right * 2))
        height_image, material_image = images
        _write_where(height_image[target], heights, inside)
        del heights
        if inputs.contact is not None:
            _contact_decals(
                inputs.contact,
                height_image[target],
                first=decal.row0 + first,
                column=decal.column0 + left,
                width=width,
            )
            _contact_rim(
                inputs.contact,
                height_image[target],
                first=decal.row0 + first,
                column=decal.column0 + left,
                width=width,
            )
        slots = synthesize(labels, land, rivers, tables, seed=seed, origin=origin, core=core)
        if stamped is not None:
            slots = _lay_stamp_slots(slots, stamped, labels[core], tables)
        _write_where(material_image[target], slots, inside)
        if inputs.contact is not None:
            _contact_materials(
                inputs.contact,
                material_image[target],
                labels[core],
                tables,
                first=decal.row0 + first,
                column=decal.column0 + left,
                width=width,
                seed=seed,
            )


@measured
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
        if plan != original
        or _touches_coast(plan, codes)
        or _contact_columns(inputs.contact, plan, 0, plan.rows, codes.shape[1]).any()
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
    disabled, cache_out = disable_decals(store, codes, inputs.moved)
    sink.update(disabled)
    sink["in_game/gfx/terrain2/terrain_cache/ingame_decals.json"] = cache_out
    padded = sum(plan != original for plan, original in zip(plans, store.decals, strict=True))
    stats: dict[str, object] = {
        "decals_rebuilt": [decal.name for decal in touched],
        "mountain_decals_disabled": len(disabled) - padded,
        "periodic_heightmap_instances": 0,
        "padded_heightmaps": padded,
        "mountain_height_stamps": len(inputs.mountains.placements) if inputs.mountains else 0,
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


def _shift_stamp(raw: str, down: int, across: int, width: int) -> str:
    """The text of a mountain stamp instance moved by ``down`` rows and ``across`` columns."""

    def number(key: str, text: str, change: int, limit: int | None) -> str:
        found = re.search(rf'("{re.escape(key)}":\s*)(-?[\d.]+)', text)
        if found is None:
            message = f"Mountain stamp instance without {key}"
            raise TerrainRangeError(message)
        value = float(found.group(2)) + change * LOCATION_UNITS
        if limit is not None:
            value %= limit * LOCATION_UNITS
        shown = str(int(value)) if value == int(value) else repr(value)
        return text[: found.start(2)] + shown + text[found.end(2) :]

    return number("position.y", number("position.x", raw, across, width), -down, None)


def _moved_steps(
    moved: Moved | None, rows: int, points: list[tuple[float, float]]
) -> list[tuple[int, int] | None]:
    """The step of each point's pixel if it lies on a moved group, asked in one call: a call
    each would wait for the interpreter thousands of times beside other stages."""
    if moved is None or not points:
        return [None] * len(points)
    found, down, across = moved.find(
        np.array([rows - 1 - int(y) // LOCATION_UNITS for _, y in points], dtype=np.int64),
        np.array([int(x) // LOCATION_UNITS for x, _ in points], dtype=np.int64),
    )
    return [
        (int(step), int(side)) if hit else None
        for hit, step, side in zip(found.tolist(), down.tolist(), across.tolist(), strict=True)
    ]


def _kept_cache(
    store: DecalStore,
    codes: NDArray[np.int8],
    wrapped: dict[str, dict[str, object]],
    moved: Moved | None,
) -> list[dict[str, object]]:
    """The decal cache's entries that stay: heightmaps (extended where wrapped), mountains off
    the canvas, and the mountains of moved groups at their new places."""
    rows, width = store.map_shape
    positions = [
        cast("dict[str, dict[str, float]]", entry["decal_transform"])["position"]
        for entry in store.cache
    ]
    names = [str(entry["decal_name"]) for entry in store.cache]
    asked = [
        (index, (position["x"], position["y"]))
        for index, (name, position) in enumerate(zip(names, positions, strict=True))
        if not HEIGHTMAP.fullmatch(name)
    ]
    steps: list[tuple[int, int] | None] = [None] * len(store.cache)
    for (index, _), step in zip(
        asked, _moved_steps(moved, rows, [point for _, point in asked]), strict=True
    ):
        steps[index] = step
    kept: list[dict[str, object]] = []
    for entry, name, position, step in zip(store.cache, names, positions, steps, strict=True):
        if step is not None:
            shifted = deepcopy(entry)
            place = cast("dict[str, dict[str, float]]", shifted["decal_transform"])["position"]
            place["x"] = (place["x"] + step[1] * LOCATION_UNITS) % (width * LOCATION_UNITS)
            place["y"] = place["y"] - step[0] * LOCATION_UNITS
            kept.append(shifted)
        elif HEIGHTMAP.fullmatch(name) or not _inside(codes, position["x"], position["y"]):
            kept.append(wrapped.get(name, entry))
    return kept


def _instance_files(
    store: DecalStore, codes: NDArray[np.int8], moved: Moved | None
) -> dict[str, bytes]:
    """Mountain instances on the canvas disabled, and those of moved groups moved with them."""
    rows, width = store.map_shape
    decals = store.game_dir / TERRAIN / "decals"
    instances: list[tuple[str, bytes, dict[str, object]]] = []
    for folder in sorted(path for path in decals.iterdir() if path.is_dir()):
        if HEIGHTMAP.fullmatch(folder.name) or not (folder / "instances").is_dir():
            continue
        for instance in sorted((folder / "instances").glob("*.json")):
            raw = instance.read_bytes()
            data = cast("dict[str, object]", json.loads(raw.decode("utf-8-sig")))
            relative = f"in_game/gfx/terrain2/decals/{folder.name}/instances/{instance.name}"
            instances.append((relative, raw, data))
    enabled = [
        index for index, (_, _, data) in enumerate(instances) if data.get("disabled") is False
    ]
    points = [
        (cast("float", instances[i][2]["position.x"]), cast("float", instances[i][2]["position.y"]))
        for i in enabled
    ]
    shifts = dict(zip(enabled, _moved_steps(moved, rows, points), strict=True))
    files: dict[str, bytes] = {}
    for index, (relative, raw, data) in enumerate(instances):
        step = shifts.get(index)
        prefix = "\ufeff" if raw.startswith(b"\xef\xbb\xbf") else ""
        if step is not None:
            text = _shift_stamp(raw.decode("utf-8-sig"), step[0], step[1], width)
            files[relative] = (prefix + text).encode("utf-8")
        elif data.get("disabled") is False and _inside(
            codes, cast("float", data["position.x"]), cast("float", data["position.y"])
        ):
            text = raw.decode("utf-8-sig").replace('"disabled":\tfalse', '"disabled":\ttrue')
            files[relative] = (prefix + text).encode("utf-8")
    return files


def disable_decals(
    store: DecalStore, codes: NDArray[np.int8], moved: Moved | None = None
) -> tuple[dict[str, bytes], bytes]:
    """Extend primary heightmaps and disable obsolete mountains in instances and cache.

    A mountain on a moved island group moves with it instead: its instance and its cache entry
    take the new position, and it stays enabled.
    """
    wrapped, files = _wrapped_heightmaps(store)
    kept = _kept_cache(store, codes, wrapped, moved)
    files.update(_instance_files(store, codes, moved))
    cache_out = ("\ufeff" + json.dumps(kept, indent="\t", ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    return files, cache_out
