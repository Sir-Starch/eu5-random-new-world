"""Seeded generation of new land, sea, lakes and cells on a synthetic fixture world.

The fixture has a fixed protected "Old World" strip on the east with two ocean anchor
seas. Everything west of it is generated from the seed: a fractal elevation field,
coast cleanup, connected land/sea/lake cells, a five-level hierarchy and unique
colours. No game data is involved.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.model import Cell, CellClass, Parents, World
from rnw.noise import NOISE_SCALE, fractal_noise
from rnw.rng import SplitMix64, derive_seed, hash_grid
from rnw.topology import adjacency_pairs, label_components, unpack_pairs

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.settings import GeographySettings, Settings, SyntheticSettings

PERMILLE: Final[int] = 1000
COLOR_BITS: Final[int] = 24
OLD_CONTINENT: Final[Parents] = Parents(
    "old_province", "old_area", "old_region", "old_core", "old_world"
)
OLD_OCEAN: Final[Parents] = Parents(
    "old_sea_province", "old_sea_area", "old_sea_region", "old_waters", "old_world"
)
PLACEHOLDER: Final[Cell] = Cell(
    "rnw_unassigned",
    0x010101,
    CellClass.SEA,
    Parents("rnw_unassigned_p", "rnw_unassigned_a", "rnw_unassigned_r", "rnw_open", "rnw_open"),
)
NEIGHBOURS: Final[tuple[tuple[int, int], ...]] = ((-1, 0), (0, -1), (0, 1), (1, 0))


class UnassignedPixelError(RuntimeError):
    """Generation left domain pixels without a cell; this is a generator bug."""

    def __init__(self, count: int) -> None:
        super().__init__(f"Generator left {count} pixels unassigned")


def synthetic_base(canvas: SyntheticSettings) -> World:
    """Build the fixed protected fixture: six old land cells and two anchor seas."""
    width, height, old = canvas.width, canvas.height, canvas.old_world_columns
    start = width - old
    labels = np.full((height, width), 8, dtype=np.int32)
    labels[: height // 2, start:] = 6
    labels[height // 2 :, start:] = 7
    x0, x1 = start + old // 4, width - old // 8
    y0, y1 = height // 6, height - height // 6
    xs = np.linspace(x0, x1, 3).astype(np.int64)
    ys = np.linspace(y0, y1, 4).astype(np.int64)
    for row in range(3):
        for column in range(2):
            labels[ys[row] : ys[row + 1], xs[column] : xs[column + 1]] = row * 2 + column
    old_land = (
        Cell(
            f"old_land_{index}",
            0xA00000 + index * 0x1111,
            CellClass.LAND,
            OLD_CONTINENT,
            protected=True,
        )
        for index in range(6)
    )
    cells = (
        *old_land,
        Cell("old_sea_north", 0x0000A0, CellClass.SEA, OLD_OCEAN, protected=True),
        Cell("old_sea_south", 0x0000B0, CellClass.SEA, OLD_OCEAN, protected=True),
        PLACEHOLDER,
    )
    return World(labels, cells, anchors=frozenset({6, 7}))


def _shifted(values: NDArray[np.int32], dy: int, dx: int) -> NDArray[np.int32]:
    """Value of the neighbour at (y + dy, x + dx); -1 outside the raster."""
    out = np.full(values.shape, -1, dtype=np.int32)
    height, width = values.shape
    out[max(0, -dy) : height - max(0, dy), max(0, -dx) : width - max(0, dx)] = values[
        max(0, dy) : height - max(0, -dy), max(0, dx) : width - max(0, -dx)
    ]
    return out


def grow_regions(mask: NDArray[np.bool_], seeds: NDArray[np.int32]) -> NDArray[np.int32]:
    """Grow seed labels through ``mask`` one 4-neighbour step per round.

    A pixel adopts the label of an already labelled neighbour in N, W, E, S order, so
    every grown region stays 4-connected to its seed. Unreachable pixels remain -1.
    """
    labels = np.where(mask, seeds, -1).astype(np.int32)
    while True:
        grown = labels.copy()
        for dy, dx in NEIGHBOURS:
            source = _shifted(labels, dy, dx)
            take = mask & (grown < 0) & (source >= 0)
            grown[take] = source[take]
        if np.array_equal(grown, labels):
            return labels
        labels = grown


def _first_pixels(components: NDArray[np.int64]) -> NDArray[np.int64]:
    _, first = np.unique(components.ravel(), return_index=True)
    return first.astype(np.int64)


def _sites(key: int, mask: NDArray[np.bool_], spacing: int) -> NDArray[np.int32]:
    """Jittered-grid seeds inside ``mask``; each mask component gets at least one."""
    height, width = mask.shape
    gx = np.arange((width + spacing - 1) // spacing, dtype=np.int64)
    gy = np.arange((height + spacing - 1) // spacing, dtype=np.int64)
    hashed = hash_grid(key, gx[np.newaxis, :], gy[:, np.newaxis])
    sx = gx[np.newaxis, :] * spacing + (hashed & np.uint64(0xFFFF)).astype(np.int64) % spacing
    sy = (
        gy[:, np.newaxis] * spacing
        + ((hashed >> np.uint64(16)) & np.uint64(0xFFFF)).astype(np.int64) % spacing
    )
    inside = (sx < width) & (sy < height)
    flat = (sy * width + sx)[inside]
    flat = flat[mask.ravel()[flat]]
    components = label_components(mask.astype(np.int32))
    covered = np.zeros(int(components.max()) + 1, dtype=bool)
    covered[components.ravel()[flat]] = True
    firsts = _first_pixels(components)
    extra = firsts[mask.ravel()[firsts] & ~covered[components.ravel()[firsts]]]
    seeds = np.full(mask.size, -1, dtype=np.int32)
    ordered = np.concatenate([flat, extra])
    seeds[ordered] = np.arange(ordered.size, dtype=np.int32)
    return seeds.reshape(mask.shape)


def _renumber(labels: NDArray[np.int32]) -> NDArray[np.int32]:
    """Number non-negative labels by first appearance in raster order."""
    flat = labels.ravel()
    valid = flat >= 0
    present, first = np.unique(flat[valid], return_index=True)
    order = np.argsort(first, kind="stable")
    mapping = np.full(int(present.max()) + 1 if present.size else 1, -1, dtype=np.int32)
    mapping[present[order]] = np.arange(present.size, dtype=np.int32)
    out = np.full(flat.shape, -1, dtype=np.int32)
    out[valid] = mapping[flat[valid]]
    return out.reshape(labels.shape)


def _merge_small(labels: NDArray[np.int32], minimum: int) -> NDArray[np.int32]:
    """Merge cells smaller than ``minimum`` into their longest-border neighbour."""
    count = int(labels.max()) + 1
    sizes = np.bincount(labels[labels >= 0], minlength=count).astype(np.int64)
    pairs: dict[int, dict[int, int]] = {}
    for a, b in (
        (labels[:, :-1], labels[:, 1:]),
        (labels[:-1], labels[1:]),
    ):
        touching = (a != b) & (a >= 0) & (b >= 0)
        packed = a[touching].astype(np.int64) * count + b[touching]
        values, shared = np.unique(packed, return_counts=True)
        for value, length in zip(values.tolist(), shared.tolist(), strict=True):
            first, second = divmod(value, count)
            pairs.setdefault(first, {})[second] = (
                pairs.setdefault(first, {}).get(second, 0) + length
            )
            pairs.setdefault(second, {})[first] = (
                pairs.setdefault(second, {}).get(first, 0) + length
            )
    target = list(range(count))

    def resolve(item: int) -> int:
        while target[item] != item:
            item = target[item]
        return item

    for cell in range(count):
        if sizes[cell] >= minimum or not pairs.get(cell):
            continue
        best = min(pairs[cell].items(), key=lambda item: (-item[1], item[0]))[0]
        root = resolve(best)
        if root != cell:
            target[cell] = root
            sizes[root] += sizes[cell]
    mapping = np.array([resolve(item) for item in range(count)], dtype=np.int32)
    return np.where(labels >= 0, mapping[np.maximum(labels, 0)], -1).astype(np.int32)


def _land_mask(seed: int, geo: GeographySettings, width: int, height: int) -> NDArray[np.bool_]:
    elevation = fractal_noise(
        derive_seed(seed, "elevation"),
        0,
        0,
        width,
        height,
        period=geo.feature_px,
        octaves=geo.octaves,
        persistence_permille=geo.persistence_permille,
    )
    ys, xs = np.indices((height, width), dtype=np.int64)
    edge = np.minimum(np.minimum(xs, ys), np.minimum(width - 1 - xs, height - 1 - ys))
    ramp = 4 * geo.coast_margin_px
    elevation -= np.maximum(0, ramp - edge) * NOISE_SCALE * 2 // ramp
    interior = edge >= geo.coast_margin_px
    values = np.sort(elevation[interior], kind="stable")
    land_count = max(1, values.size * geo.land_permille // PERMILLE)
    threshold = values[values.size - land_count]
    land = interior & (elevation >= threshold)
    components = label_components(land.astype(np.int32))
    sizes = np.bincount(components.ravel())
    land &= sizes[components] >= geo.min_island_px
    water_parts = label_components(land.astype(np.int32))
    ocean = water_parts == water_parts[0, 0]
    enclosed = ~land & ~ocean
    small_lake = enclosed & (np.bincount(water_parts.ravel())[water_parts] < geo.min_lake_px)
    return land | small_lake


def _group(members: list[int], neighbours: dict[int, set[int]], size: int) -> list[list[int]]:
    """Greedy breadth-first grouping of adjacent members in ascending order."""
    allowed = set(members)
    assigned: set[int] = set()
    groups: list[list[int]] = []
    for start in members:
        if start in assigned:
            continue
        group = [start]
        assigned.add(start)
        queue = deque([start])
        while queue and len(group) < size:
            for neighbour in sorted(neighbours.get(queue.popleft(), set())):
                if neighbour in allowed and neighbour not in assigned and len(group) < size:
                    assigned.add(neighbour)
                    group.append(neighbour)
                    queue.append(neighbour)
        groups.append(group)
    return groups


def _lift(groups: list[list[int]], neighbours: dict[int, set[int]]) -> dict[int, set[int]]:
    owner = {member: index for index, group in enumerate(groups) for member in group}
    lifted: dict[int, set[int]] = {}
    for member, adjacent in neighbours.items():
        for other in adjacent:
            if member in owner and other in owner and owner[member] != owner[other]:
                lifted.setdefault(owner[member], set()).add(owner[other])
    return lifted


def _hierarchy(
    classes: list[CellClass],
    labels: NDArray[np.int32],
    group_size: int,
) -> list[Parents]:
    """Assign province, area, region, subcontinent and continent names."""
    neighbours: dict[int, set[int]] = {}
    for first, second in unpack_pairs(adjacency_pairs(labels)):
        neighbours.setdefault(first, set()).add(second)
        neighbours.setdefault(second, set()).add(first)
    rows = np.indices(labels.shape, dtype=np.int64)[0].ravel()
    row_sum = np.zeros(len(classes), dtype=np.int64)
    np.add.at(row_sum, labels.ravel(), rows)
    pixels = np.bincount(labels.ravel(), minlength=len(classes)).astype(np.int64)
    parents: list[Parents | None] = [None] * len(classes)
    counters = [0, 0, 0]
    for kind in (CellClass.LAND, CellClass.SEA, CellClass.LAKE):
        members = [index for index, item in enumerate(classes) if item is kind]
        provinces = _group(members, neighbours, group_size)
        province_links = _lift(provinces, neighbours)
        areas = _group(list(range(len(provinces))), province_links, group_size)
        regions = _group(list(range(len(areas))), _lift(areas, province_links), group_size)
        for region in regions:
            counters[2] += 1
            region_cells = [cell for area in region for p in areas[area] for cell in provinces[p]]
            weight = int(pixels[region_cells].sum())
            north = 2 * int(row_sum[region_cells].sum()) < labels.shape[0] * weight
            subcontinent = "rnw_north" if north else "rnw_south"
            for area in region:
                counters[1] += 1
                for province in areas[area]:
                    counters[0] += 1
                    for cell in provinces[province]:
                        parents[cell] = Parents(
                            f"rnw_prov_{counters[0]:04d}",
                            f"rnw_area_{counters[1]:03d}",
                            f"rnw_region_{counters[2]:02d}",
                            subcontinent,
                            "rnw_new_world",
                        )
    return [item if item is not None else PLACEHOLDER.parents for item in parents]


def _colors(seed: int, count: int, used: set[int]) -> list[int]:
    rng = SplitMix64(derive_seed(seed, "colors"))
    taken = set(used) | {0}
    colors: list[int] = []
    while len(colors) < count:
        color = rng.next_u64() >> (64 - COLOR_BITS)
        if color not in taken:
            taken.add(color)
            colors.append(color)
    return colors


def generate_world(seed: int, settings: Settings) -> World:
    """Generate a complete synthetic world for ``seed`` and ``settings``."""
    base = synthetic_base(settings.synthetic)
    geo = settings.geography
    width = settings.synthetic.width - settings.synthetic.old_world_columns
    height = settings.synthetic.height
    land = _land_mask(seed, geo, width, height)
    water_parts = label_components(land.astype(np.int32))
    ocean = water_parts == water_parts[0, 0]
    lakes = ~land & ~ocean
    land_cells = _merge_small(
        grow_regions(land, _sites(derive_seed(seed, "land_sites"), land, geo.location_px)),
        geo.min_cell_px,
    )
    sea_cells = grow_regions(ocean, _sites(derive_seed(seed, "sea_sites"), ocean, geo.sea_zone_px))
    lake_cells = np.where(lakes, water_parts, -1).astype(np.int32)
    offset = 0
    domain = np.full((height, width), -1, dtype=np.int32)
    classes: list[CellClass] = []
    for kind, part in (
        (CellClass.LAND, land_cells),
        (CellClass.SEA, sea_cells),
        (CellClass.LAKE, lake_cells),
    ):
        numbered = _renumber(part)
        present = int(numbered.max()) + 1 if np.any(numbered >= 0) else 0
        domain[numbered >= 0] = numbered[numbered >= 0] + offset
        classes.extend([kind] * present)
        offset += present
    if np.any(domain < 0):
        raise UnassignedPixelError(int(np.count_nonzero(domain < 0)))
    parents = _hierarchy(classes, domain, geo.group_size)
    protected = [cell for cell in base.cells if cell.protected]
    colors = _colors(seed, len(classes), {cell.color for cell in protected})
    serial = {CellClass.LAND: 0, CellClass.SEA: 0, CellClass.LAKE: 0}
    generated: list[Cell] = []
    for index, kind in enumerate(classes):
        serial[kind] += 1
        key = f"rnw_{kind.value}_{serial[kind]:04d}"
        generated.append(Cell(key, colors[index], kind, parents[index]))
    labels = base.labels.copy()
    labels[:, :width] = domain + len(protected)
    return World(labels, (*protected, *generated), base.anchors, wrap_x=False)
