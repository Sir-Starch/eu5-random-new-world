"""Read-only adapter for the EU5 1.4.1 map contract.

Turns installed game files into game-independent tables: a label raster indexed by
named-colour declaration order, per-label classes and continents, the river layer and
fixed map points (locators, ports, strait endpoints). Nothing here writes files.
Conventions marked [V-EXEC] were checked against build 25905365; see the claims ledger.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, override

import numpy as np
from PIL import Image

from rnw.contract import FileFingerprint
from rnw.geography import read_locations, read_named_colors
from rnw.model import CellClass
from rnw.png import read_chunks

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

MAP_DATA: Final[str] = "game/in_game/map_data"
LOCATIONS: Final[str] = f"{MAP_DATA}/locations.png"
RIVERS: Final[str] = f"{MAP_DATA}/rivers.png"
DEFINITIONS: Final[str] = f"{MAP_DATA}/definitions.txt"
NAMED_COLORS: Final[str] = f"{MAP_DATA}/named_locations/00_default.txt"
DEFAULT_MAP: Final[str] = f"{MAP_DATA}/default.map"
PORTS: Final[str] = f"{MAP_DATA}/ports.csv"
ADJACENCIES: Final[str] = f"{MAP_DATA}/adjacencies.csv"
MAP_OBJECTS: Final[str] = "game/in_game/gfx/map/map_objects"
LOCATOR_FILES: Final[tuple[str, ...]] = (
    f"{MAP_OBJECTS}/generated_locators_city.txt",
    f"{MAP_OBJECTS}/generated_map_object_locators_unit_stack.txt",
    f"{MAP_OBJECTS}/generated_map_object_locators_combat.txt",
    f"{MAP_OBJECTS}/generated_map_object_locators_dock.txt",
    f"{MAP_OBJECTS}/generated_locators_vfx.txt",
    f"{MAP_OBJECTS}/generated_map_object_locators_volcano_eruption.txt",
    f"{MAP_DATA}/generated_locators_port.txt",
)
LOCATOR_OVERRIDE: Final[str] = "game/in_game/gfx/map/locators_override/locators_override.txt"
MAX_PIXELS: Final[int] = 16384 * 8192
RIVER_WATER: Final[int] = 254
RIVER_LAND: Final[int] = 255
CLASS_LISTS: Final[tuple[tuple[str, CellClass], ...]] = (
    ("sea_zones", CellClass.SEA),
    ("lakes", CellClass.LAKE),
    ("impassable_mountains", CellClass.WASTELAND),
    ("non_ownable", CellClass.NON_OWNABLE),
)
COMMENT: Final[re.Pattern[str]] = re.compile(r"#[^\n]*")
LIST_BLOCK: Final[re.Pattern[str]] = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{([^{}]*)\}")
NUMBER: Final[str] = r"(-?\d+(?:\.\d+)?)"
POSITION: Final[str] = rf"position\s*=\s*\{{\s*{NUMBER}\s+{NUMBER}\s+{NUMBER}\s*\}}"
LOCATOR: Final[re.Pattern[str]] = re.compile(rf"\bid\s*=\s*([A-Za-z0-9_]+)\s+{POSITION}")
OVERRIDE: Final[re.Pattern[str]] = re.compile(rf"{POSITION}\s+province\s*=\s*([A-Za-z0-9_]+)")
COLOR_SPACE: Final[int] = 1 << 24


class Eu5ContractError(ValueError):
    """Installed files do not match the observed EU5 1.4.1 map contract."""


@dataclass(frozen=True, slots=True)
class UndeclaredColorError(Eu5ContractError):
    """The location raster uses colours absent from the named-colour file."""

    pixels: int

    @override
    def __str__(self) -> str:
        return f"locations.png has {self.pixels} pixels with undeclared colours"


@dataclass(frozen=True, slots=True)
class MapPoint:
    """A fixed map position in raster coordinates (row 0 is the north edge)."""

    source: str
    key: str
    x: int
    y: int


@dataclass(frozen=True, slots=True, eq=False)
class Eu5Map:
    """Game-independent tables derived from one installation."""

    keys: tuple[str, ...]
    colors: NDArray[np.int64]
    classes: tuple[CellClass, ...]
    ambiguous: NDArray[np.bool_]
    continents: tuple[str, ...]
    rgb: NDArray[np.uint8]
    labels: NDArray[np.int32]
    rivers: NDArray[np.uint8]
    locations_chunks: tuple[tuple[bytes, bytes], ...]
    rivers_chunks: tuple[tuple[bytes, bytes], ...]
    points: tuple[MapPoint, ...]
    inputs: tuple[FileFingerprint, ...]


def _hash(game_dir: Path, relative: str) -> FileFingerprint:
    source = game_dir / relative
    with source.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return FileFingerprint(relative, source.stat().st_size, digest)


def class_lists(text: str) -> dict[str, list[str]]:
    """The location tokens of the class lists in the text of a ``default.map``."""
    text = COMMENT.sub("", text)
    found: dict[str, list[str]] = {name: [] for name, _ in CLASS_LISTS}
    for match in LIST_BLOCK.finditer(text):
        if match.group(1) in found:
            found[match.group(1)].extend(match.group(2).split())
    return found


def read_class_lists(path: Path) -> dict[str, list[str]]:
    """Read the location tokens of the class lists in ``default.map``."""
    return class_lists(path.read_text(encoding="utf-8-sig"))


def flip_row(z: float, height: int) -> int:
    """Convert a locator's world Z to a raster row. [V-EXEC] 21,046/21,046 cities."""
    return height - 1 - math.floor(z)


def read_locators(path: Path, source: str, height: int) -> list[MapPoint]:
    """Read ``id``/``position`` instances from a generated locator file."""
    text = COMMENT.sub("", path.read_text(encoding="utf-8-sig"))
    return [
        MapPoint(source, key, math.floor(float(x)), flip_row(float(z), height))
        for key, x, _, z in LOCATOR.findall(text)
    ]


def read_override_locators(path: Path, source: str, height: int) -> list[MapPoint]:
    """Read ``position``/``province`` blocks from the locator override file."""
    text = COMMENT.sub("", path.read_text(encoding="utf-8-sig"))
    return [
        MapPoint(source, key, math.floor(float(x)), flip_row(float(z), height))
        for x, _, z, key in OVERRIDE.findall(text)
    ]


def read_csv_points(
    path: Path, source: str, columns: tuple[tuple[int, int], ...], height: int
) -> list[MapPoint]:
    """Read integer x/y pairs from a semicolon CSV with a header row.

    Rows are flipped like locators; [V-EXEC] this matched 1,993 of the first 2,000 ports.
    Negative or malformed coordinates are skipped.
    """
    points: list[MapPoint] = []
    lines = path.read_text(encoding="utf-8-sig").splitlines()[1:]
    for line in lines:
        fields = line.split(";")
        for x_column, y_column in columns:
            if len(fields) <= y_column:
                continue
            x_text, y_text = fields[x_column].strip(), fields[y_column].strip()
            if not (x_text.isdigit() and y_text.isdigit()):
                continue
            row = height - 1 - int(y_text)
            points.append(MapPoint(source, fields[0].strip(), int(x_text), row))
    return points


def open_png(path: Path, mode: str, size: tuple[int, int] | None = None) -> NDArray[np.uint8]:
    """Decode a PNG of an expected mode (and size) into a writable array."""
    previous = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        with Image.open(path) as image:
            if image.mode != mode or (size is not None and image.size != size):
                message = f"{path.name}: expected mode {mode} and size {size}"
                raise Eu5ContractError(message)
            return np.array(image, dtype=np.uint8)
    finally:
        Image.MAX_IMAGE_PIXELS = previous


def pack_rgb(rgb: NDArray[np.uint8]) -> NDArray[np.int64]:
    """Pack an RGB array into 24-bit integers."""
    return (
        (rgb[..., 0].astype(np.int64) << 16)
        | (rgb[..., 1].astype(np.int64) << 8)
        | rgb[..., 2].astype(np.int64)
    )


def labels_from_rgb(rgb: NDArray[np.uint8], colors: NDArray[np.int64]) -> NDArray[np.int32]:
    """Map raster colours to declaration indices, refusing undeclared colours."""
    lookup = np.full(COLOR_SPACE, -1, dtype=np.int32)
    lookup[colors] = np.arange(colors.size, dtype=np.int32)
    labels = lookup[pack_rgb(rgb)]
    missing = int(np.count_nonzero(labels < 0))
    if missing:
        raise UndeclaredColorError(missing)
    return labels


def load_map(game_dir: Path) -> Eu5Map:
    """Read every map input needed by the T2 exporter, hashing each file read."""
    pairs = read_named_colors(game_dir / NAMED_COLORS)
    keys = tuple(key for key, _ in pairs)
    index = {key: position for position, key in enumerate(keys)}
    colors = np.array([color for _, color in pairs], dtype=np.int64)
    continent = dict.fromkeys(keys, "")
    for location in read_locations(game_dir / DEFINITIONS):
        continent[location.key] = location.continent
    lists = read_class_lists(game_dir / DEFAULT_MAP)
    membership: dict[str, list[CellClass]] = {}
    for name, kind in CLASS_LISTS:
        for token in dict.fromkeys(lists[name]):
            membership.setdefault(token, []).append(kind)
    classes = tuple(membership.get(key, [CellClass.LAND])[0] for key in keys)
    ambiguous = np.array([len(membership.get(key, [])) > 1 for key in keys], dtype=bool)
    rgb = open_png(game_dir / LOCATIONS, "RGB")
    height, width = int(rgb.shape[0]), int(rgb.shape[1])
    points: list[MapPoint] = []
    for relative in LOCATOR_FILES:
        points.extend(read_locators(game_dir / relative, relative, height))
    points.extend(read_override_locators(game_dir / LOCATOR_OVERRIDE, LOCATOR_OVERRIDE, height))
    points.extend(read_csv_points(game_dir / PORTS, PORTS, ((2, 3),), height))
    points.extend(read_csv_points(game_dir / ADJACENCIES, ADJACENCIES, ((4, 5), (6, 7)), height))
    files = (
        NAMED_COLORS,
        DEFINITIONS,
        DEFAULT_MAP,
        LOCATIONS,
        RIVERS,
        PORTS,
        ADJACENCIES,
        *LOCATOR_FILES,
        LOCATOR_OVERRIDE,
    )
    return Eu5Map(
        keys=keys,
        colors=colors,
        classes=classes,
        ambiguous=ambiguous,
        continents=tuple(continent[key] for key in keys),
        rgb=rgb,
        labels=labels_from_rgb(rgb, colors),
        rivers=open_png(game_dir / RIVERS, "P", (width, height)),
        locations_chunks=read_chunks(game_dir / LOCATIONS),
        rivers_chunks=read_chunks(game_dir / RIVERS),
        points=tuple(point for point in points if point.key in index),
        inputs=tuple(_hash(game_dir, relative) for relative in files),
    )
