"""Write a tiny EU5-shaped installation from a synthetic world; no game data is used."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.artifacts import color_raster
from rnw.contract import CONTRACT_FILES, aggregate_digest, fingerprint
from rnw.eu5_map import (
    ADJACENCIES,
    DEFAULT_MAP,
    DEFINITIONS,
    LOCATIONS,
    LOCATOR_FILES,
    LOCATOR_OVERRIDE,
    NAMED_COLORS,
    PORTS,
    RIVER_LAND,
    RIVER_WATER,
    RIVERS,
)
from rnw.model import Cell, CellClass, Parents, World
from rnw.png import COLOR_PALETTE, COLOR_RGB, encode_png
from rnw.settings import Settings, build_settings
from rnw.synth import generate_world

if TYPE_CHECKING:
    from pathlib import Path

CONTINENTS: Final[dict[str, str]] = {"rnw_new_world": "america", "old_world": "europe"}
RIVER_INDEX: Final[int] = 4
FRAME: Final[int] = 3
FRAME_CELL: Final[Cell] = Cell(
    "frame_ocean",
    0x000060,
    CellClass.SEA,
    Parents("frame_p", "frame_a", "frame_r", "frame_s", "rnw_new_world"),
    protected=True,
)
UNUSED_COLOR_KEY: Final[str] = "unused_extra"
ADJACENCY_CSV: Final[bytes] = (
    b"From;To;Type;Through;start_x;start_y;stop_x;stop_y;Comment\n"
    b"old_land_0;old_land_1;sea;old_sea_north;-1;-1;-1;-1;xxx\n"
)
FIXTURE_OVERRIDES: Final[dict[str, object]] = {
    "synthetic": {"width": 192, "height": 96, "old_world_columns": 48},
    "geography": {"feature_px": 48, "location_px": 8, "sea_zone_px": 20},
    "coast": {"window": [1, 1, 197, 101], "feature_px": 12, "locator_radius_px": 1},
}


def fixture_settings(preset: str = "continents") -> Settings:
    """Small canvas whose window includes Old World anchor seas."""
    return build_settings(preset, FIXTURE_OVERRIDES)


def _definitions(world: World) -> str:
    tree: dict[str, dict[str, dict[str, dict[str, dict[str, list[str]]]]]] = {}
    for cell in world.cells:
        province, area, region, subcontinent, continent = cell.parents.chain()
        branch = tree.setdefault(CONTINENTS.get(continent, continent), {})
        branch = branch.setdefault(subcontinent, {}).setdefault(region, {}).setdefault(area, {})
        branch.setdefault(province, []).append(cell.key)
    lines: list[str] = []
    for continent, subcontinents in tree.items():
        lines.append(f"{continent} = {{")
        for subcontinent, regions in subcontinents.items():
            lines.append(f"\t{subcontinent} = {{")
            for region, areas in regions.items():
                lines.append(f"\t\t{region} = {{")
                for area, provinces in areas.items():
                    lines.append(f"\t\t\t{area} = {{")
                    lines.extend(
                        f"\t\t\t\t{province} = {{ {' '.join(keys)} }}"
                        for province, keys in provinces.items()
                    )
                    lines.append("\t\t\t}")
                lines.append("\t\t}")
            lines.append("\t}")
        lines.append("}")
    return "\n".join(lines) + "\n"


def _default_map(world: World) -> str:
    def keys(kind: CellClass) -> str:
        return " ".join(cell.key for cell in world.cells if cell.cell_class is kind)

    return (
        'provinces = "locations.png"\nwrap_x = no\n\n'
        f"sea_zones = {{ # seas\n\t{keys(CellClass.SEA)}\n}}\n"
        f"lakes = {{\n\t{keys(CellClass.LAKE)}\n}}\n"
        "impassable_mountains = {\n}\nnon_ownable = {\n}\n"
    )


def _rivers(world: World) -> np.ndarray[tuple[int, int], np.dtype[np.uint8]]:
    water = world.water_table()[world.labels]
    rivers = np.where(water, RIVER_WATER, RIVER_LAND).astype(np.uint8)
    land = np.flatnonzero(~water[:, : world.width // 2].ravel())
    row, column = divmod(int(land[land.size // 2]), world.width // 2)
    segment = ~water[row, column : column + 4]
    rivers[row, column : column + 4][segment] = RIVER_INDEX
    return rivers


def _palette() -> bytes:
    colors = [(index, index, index) for index in range(256)]
    colors[RIVER_WATER] = (255, 0, 128)
    colors[RIVER_LAND] = (255, 255, 255)
    return bytes(channel for color in colors for channel in color)


def _first_pixels(world: World) -> dict[int, tuple[int, int]]:
    _, first = np.unique(world.labels.ravel(), return_index=True)
    return {label: divmod(int(index), world.width) for label, index in enumerate(first.tolist())}


def _coastal_pair(world: World) -> tuple[str, str, int, int]:
    """First land pixel with an eastern sea neighbour: (land, sea, x, y)."""
    land = world.class_table(CellClass.LAND)[world.labels]
    sea = world.class_table(CellClass.SEA)[world.labels]
    rows, columns = np.nonzero(land[:, :-1] & sea[:, 1:])
    row, column = int(rows[0]), int(columns[0])
    return (
        world.cells[int(world.labels[row, column])].key,
        world.cells[int(world.labels[row, column + 1])].key,
        column,
        row,
    )


def _locators(world: World) -> str:
    height = world.height
    blocks: list[str] = []
    for label, (row, column) in sorted(_first_pixels(world).items()):
        cell = world.cells[label]
        if cell.cell_class is CellClass.LAND:
            z = height - 1 - row
            position = f"position={{ {column}.500000 0.000000 {z}.500000 }}"
            blocks.append(f"\t\t{{\n\t\t\tid={cell.key}\n\t\t\t{position}\n\t\t}}")
    body = "\n".join(blocks)
    return f'game_object_locator={{\n\tname="city"\n\tinstances={{\n{body}\n\t}}\n}}\n'


def build_install(root: Path, world: World) -> str:
    """Write the synthetic installation and return its map-contract digest."""

    def write(relative: str, data: bytes) -> None:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_bytes(data)

    for relative in CONTRACT_FILES:
        write(relative, f"synthetic placeholder {relative}\n".encode())
    write(LOCATIONS, encode_png(color_raster(world), color_type=COLOR_RGB, compression="zlib"))
    write(
        RIVERS,
        encode_png(
            _rivers(world),
            color_type=COLOR_PALETTE,
            compression="zlib",
            extra_chunks=((b"PLTE", _palette()),),
        ),
    )
    colors = "".join(f"{cell.key} = {cell.color:06x}\n" for cell in world.cells)
    write(
        NAMED_COLORS,
        f"# synthetic\n{colors}{UNUSED_COLOR_KEY} = 123457 # unused\n".encode("utf-8-sig"),
    )
    write(DEFINITIONS, _definitions(world).encode("utf-8-sig"))
    write(DEFAULT_MAP, _default_map(world).encode())
    land_key, sea_key, column, row = _coastal_pair(world)
    flipped = world.height - 1 - row
    write(PORTS, f"LandProvince;SeaZone;x;y;\n{land_key};{sea_key};{column};{flipped};x\n".encode())
    write(ADJACENCIES, ADJACENCY_CSV)
    write(LOCATOR_FILES[0], _locators(world).encode("utf-8-sig"))
    for relative in LOCATOR_FILES[1:]:
        write(relative, b'game_object_locator={\n\tname="empty"\n\tinstances={\n\t}\n}\n')
    write(LOCATOR_OVERRIDE, b"#1 = {\n#\tposition = {1.0 2.0 3.0}\n#\tprovince = x\n#}\n")
    return aggregate_digest(fingerprint(root))


def framed(world: World) -> World:
    """Surround a world with a protected American ocean that crosses any window edge."""
    labels = np.pad(world.labels, FRAME, constant_values=len(world.cells))
    return World(labels, (*world.cells, FRAME_CELL), world.anchors, wrap_x=False)


def make_install(root: Path, seed: int = 11) -> tuple[World, str]:
    """Generate a framed fixture world and write it as a synthetic installation."""
    world = framed(generate_world(seed, fixture_settings()))
    return world, build_install(root, world)
