"""The atlas of a world: its generated New World as data a viewer can draw (ADR 0010, B, H).

An export writes, beside the mod, ``atlas.json`` (one record per generated location, the
countries, and the vocabularies of cultures, religions, materials and climates) and
``atlas_labels.png`` (the New World's box at a fraction of the map's size, each pixel the number
of the location it lies in, plus one; 0 is outside). Everything here is **ours**: the locations,
names, colours and numbers the generator made, with identifiers (keys) of game objects as names.
No game raster or text is in it, so it can travel with a world file and be opened where the game
is not (``rnw.record``, H).

The pictures are drawn from the atlas, not stored: ``render`` paints one layer (land, countries,
cultures, religions, resources, development, population, climate, terrain, areas) from palettes by
integer arithmetic, so the same atlas gives the same bytes on every machine; ``lens`` gives a
layer's colour, legend entry and border value per location, for a viewer that paints the box
itself; ``describe`` answers what lies at a pixel; ``find`` locates a country, culture, religion,
material or place by name. This module reads no game file and imports no game reader.
"""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import hashlib
import io
import json
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, cast

import numpy as np
from PIL import Image

from rnw.png import COLOR_RGB, encode_png
from rnw.wording import Name, Phrase, english

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from numpy.typing import NDArray

# Format 2 keeps names as phrases (``wording``), written in the viewer's language; format 1 kept
# them as English text and is still read.
FORMAT: Final[int] = 2
READS: Final[frozenset[int]] = frozenset({1, 2})
JSON_FILE: Final[str] = "atlas.json"
LABELS_FILE: Final[str] = "atlas_labels.png"
LAYERS: Final[tuple[str, ...]] = (
    "land",
    "countries",
    "cultures",
    "religions",
    "resources",
    "development",
    "population",
    "climate",
    "terrain",
    "areas",
)
# Layers whose colours run along a ramp rather than naming one thing per colour.
RAMPS: Final[frozenset[str]] = frozenset({"development", "population"})
# Layers that draw lines where their value changes between two land locations.
BORDERED: Final[frozenset[str]] = frozenset({"countries", "cultures", "religions", "areas"})
KINDS: Final[tuple[str, ...]] = ("land", "wasteland", "sea", "lake")
OUTSIDE: Final[tuple[int, int, int]] = (14, 20, 30)
SEA: Final[tuple[int, int, int]] = (30, 58, 110)
LAKE: Final[tuple[int, int, int]] = (70, 120, 190)
WASTELAND: Final[tuple[int, int, int]] = (120, 118, 112)
UNCLAIMED: Final[tuple[int, int, int]] = (92, 96, 84)
BORDER: Final[tuple[int, int, int]] = (16, 16, 16)
CAPITAL: Final[tuple[int, int, int]] = (250, 250, 250)
PRECIOUS: Final[frozenset[str]] = frozenset({"goods_gold", "silver", "gems", "pearls"})
# The land layer: the colour of each vegetation, tinted by climate and shaded by topography.
VEGETATION_COLOURS: Final[dict[str, tuple[int, int, int]]] = {
    "desert": (214, 190, 120),
    "sparse": (176, 168, 104),
    "grasslands": (150, 186, 90),
    "woods": (84, 150, 76),
    "forest": (44, 112, 60),
    "jungle": (20, 96, 52),
}
# How far each climate pulls the land toward a colour, in hundredths.
CLIMATE_TINTS: Final[dict[str, tuple[tuple[int, int, int], int]]] = {
    "arctic": ((236, 242, 250), 70),
    "subpolar": ((220, 230, 240), 38),
    "cold_arid": ((200, 196, 180), 28),
    "cold_semi_arid": ((200, 196, 180), 18),
    "tropical": ((255, 220, 120), 12),
}
HIGHLIGHT: Final[tuple[int, int, int]] = (255, 235, 59)
# Development: the ramp from the lowest to the highest complexity, dark to bright.
RAMP: Final[tuple[tuple[int, int, int], ...]] = (
    (40, 28, 60),
    (100, 40, 110),
    (170, 60, 100),
    (230, 120, 70),
    (250, 220, 110),
)
# Population: the ramp from the fewest people to the most, by the square root of the count.
POPULATION_RAMP: Final[tuple[tuple[int, int, int], ...]] = (
    (32, 44, 72),
    (36, 92, 120),
    (52, 148, 132),
    (150, 196, 98),
    (246, 230, 120),
)
CLIMATE_COLOURS: Final[dict[str, tuple[int, int, int]]] = {
    "arctic": (226, 236, 246),
    "subpolar": (168, 196, 214),
    "cold_arid": (176, 160, 136),
    "cold_semi_arid": (192, 182, 140),
    "continental": (110, 162, 120),
    "oceanic": (84, 170, 160),
    "mediterranean": (196, 176, 84),
    "hot_semi_arid": (214, 158, 92),
    "arid": (228, 196, 128),
    "tropical": (52, 150, 82),
}
TERRAIN_COLOURS: Final[dict[str, tuple[int, int, int]]] = {
    "flatland": (164, 196, 120),
    "plateau": (200, 178, 120),
    "hills": (164, 142, 92),
    "mountains": (128, 104, 84),
    "wetlands": (88, 150, 140),
    "hills_wasteland": (140, 132, 118),
    "mountain_wasteland": (108, 102, 98),
}
MAX_PIXELS: Final[int] = 64_000_000
MAX_CELLS: Final[int] = 1 << 24
SHADES: Final[tuple[tuple[str, int], ...]] = (
    ("mountain", 62),
    ("hill", 80),
    ("plateau", 80),
    ("wetland", 90),
    ("flat", 108),
)


class AtlasError(ValueError):
    """An atlas that is damaged, too large, or not one."""


@dataclass(frozen=True, slots=True)
class Country:
    """A generated country as the atlas knows it."""

    tag: str
    name: Name
    kind: str
    color: tuple[int, int, int]
    capital: int
    culture: int
    religion: int
    locations: int


@dataclass(frozen=True, slots=True)
class Facts:
    """What the atlas says of one location."""

    key: str
    name: Name
    kind: str
    area: Name
    region: Name
    country: Country | None
    culture: str
    religion: str
    material: str
    climate: str
    vegetation: str
    topography: str
    settlement: str
    population: int
    complexity: int


@dataclass(frozen=True, slots=True)
class Match:
    """A thing found by name and the locations it covers."""

    kind: str
    label: str
    cells: tuple[int, ...]


@dataclass(frozen=True, slots=True, eq=False)
class Atlas:
    """The generated New World of one world: its box of locations and what is known of each."""

    scale: int
    labels: NDArray[np.int32]
    keys: tuple[str, ...]
    names: tuple[Name, ...]
    kinds: NDArray[np.uint8]
    areas: tuple[Name, ...]
    regions: tuple[Name, ...]
    owner: NDArray[np.int32]
    culture: NDArray[np.int32]
    religion: NDArray[np.int32]
    material: NDArray[np.int32]
    climate: NDArray[np.int32]
    vegetation: NDArray[np.int32]
    topography: NDArray[np.int32]
    settlement: NDArray[np.int32]
    population: NDArray[np.int64]
    complexity: NDArray[np.int64]
    centre: NDArray[np.int32]
    countries: tuple[Country, ...]
    vocabulary: dict[str, tuple[str, ...]]

    @property
    def size(self) -> tuple[int, int]:
        """Height and width of the box, in pixels."""
        height, width = cast("tuple[int, int]", self.labels.shape)
        return height, width

    @property
    def cells(self) -> int:
        """How many locations the atlas has."""
        return len(self.keys)

    def word(self, field: str, index: int) -> str:
        """The vocabulary entry ``index`` of ``field``, or an empty string for none (-1)."""
        return self.vocabulary[field][index] if index >= 0 else ""


def pretty(key: str) -> str:
    """A readable name for an identifier: underscores to spaces, capitals to words."""
    return key.removeprefix("goods_").replace("_", " ").strip().title()


# The atlas's own words in the legends, in English; a viewer gives its own (``Words``).
LABELS: Final[dict[str, str]] = {
    "sea": "Sea",
    "lake": "Lake",
    "wasteland": "Wasteland",
    "no_country": "No country",
    "none": "None",
    "uninhabited": "Uninhabited",
    "lowest": "Lowest",
    "middle": "Middle",
    "highest": "Highest",
}
STEPS: Final[tuple[tuple[int, str], ...]] = ((100, "lowest"), (500, "middle"), (900, "highest"))


def _label(key: str) -> str:
    return LABELS[key]


@dataclass(frozen=True, slots=True)
class Words:
    """How a viewer writes what the atlas holds: its own legend words, the game's identifiers
    (cultures, religions, materials) and the names of the world, which are phrases."""

    label: Callable[[str], str] = _label
    key: Callable[[str], str] = pretty
    name: Callable[[Name], str] = english


ENGLISH: Final[Words] = Words()
# Layers that colour one vocabulary of the atlas, and the field each reads.
VOCABULARY_LAYERS: Final[dict[str, str]] = {
    "cultures": "culture",
    "religions": "religion",
    "resources": "material",
    "land": "vegetation",
    "climate": "climate",
    "terrain": "topography",
}
PALETTES: Final[dict[str, dict[str, tuple[int, int, int]]]] = {
    "land": VEGETATION_COLOURS,
    "climate": CLIMATE_COLOURS,
    "terrain": TERRAIN_COLOURS,
}


def colour_of(key: str) -> tuple[int, int, int]:
    """A stable colour for an identifier: its hash picks the hue, by integer arithmetic."""
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    hue = int.from_bytes(digest[:2], "big") % 360
    saturation = 55 + digest[2] % 30
    value = 150 + digest[3] % 80
    return _hsv(hue, saturation, value)


def _hsv(hue: int, saturation: int, value: int) -> tuple[int, int, int]:
    """Integer HSV (hue in degrees, saturation and value of 100 and 255) to RGB."""
    sector, rest = divmod(hue % 360, 60)
    top = value
    bottom = value * (100 - saturation) // 100
    falling = value * (100 - saturation * rest // 60) // 100
    rising = value * (100 - saturation * (60 - rest) // 60) // 100
    return (
        (top, rising, bottom),
        (falling, top, bottom),
        (bottom, top, rising),
        (bottom, falling, top),
        (rising, bottom, top),
        (top, bottom, falling),
    )[sector]


def ramp(share: int, colours: tuple[tuple[int, int, int], ...] = RAMP) -> tuple[int, int, int]:
    """The ramp ``colours`` (development's by default) at ``share`` of 0 to 1000."""
    span = len(colours) - 1
    scaled = max(0, min(1000, share)) * span
    low, rest = divmod(scaled, 1000)
    if low >= span:
        return colours[span]
    first, second = colours[low], colours[low + 1]
    return cast(
        "tuple[int, int, int]",
        tuple((a * (1000 - rest) + b * rest) // 1000 for a, b in zip(first, second, strict=True)),
    )


@dataclass(frozen=True, slots=True, eq=False)
class Lens:
    """One layer as a viewer paints it: per location a colour, the legend entry it belongs to
    (-1 on a ramp) and the value whose change draws a border; the legend, largest first."""

    layer: str
    colours: NDArray[np.uint8]
    classes: NDArray[np.int32]
    values: NDArray[np.int32]
    legend: tuple[tuple[str, tuple[int, int, int], int], ...]
    ramp: tuple[tuple[int, int, int], ...]


def _paint(
    atlas: Atlas, layer: str, words: Words
) -> tuple[NDArray[np.uint8], NDArray[np.int32], list[tuple[str, tuple[int, int, int], int]]]:
    """Colour and legend entry of every location for ``layer``, and the legend entries in the
    order they were first painted: label, colour, locations."""
    count = atlas.cells
    colours = np.zeros((count, 3), dtype=np.uint8)
    classes = np.full(count, -1, dtype=np.int32)
    kinds = atlas.kinds
    legend: dict[str, tuple[int, tuple[int, int, int], int]] = {}

    def paint(cell_mask: NDArray[np.bool_], colour: tuple[int, int, int], label: str) -> None:
        colours[cell_mask] = colour
        total = int(np.count_nonzero(cell_mask))
        if total:
            number, _, old = legend.get(label, (len(legend), colour, 0))
            legend[label] = (number, colour, old + total)
            classes[cell_mask] = number

    paint(kinds == KINDS.index("sea"), SEA, words.label("sea"))
    paint(kinds == KINDS.index("lake"), LAKE, words.label("lake"))
    paint(kinds == KINDS.index("wasteland"), WASTELAND, words.label("wasteland"))
    land = kinds == KINDS.index("land")
    if layer == "countries":
        paint(land & (atlas.owner < 0), UNCLAIMED, words.label("no_country"))
        for number, country in enumerate(atlas.countries):
            name = words.name(country.name) if country.name else country.tag
            paint(land & (atlas.owner == number), country.color, name)
    elif layer == "areas":
        areas, names = _area_index(atlas)
        for number, name in enumerate(names):
            label = words.name(name) if name else words.label("none")
            paint(land & (areas == number), colour_of(english(name) or "-"), label)
    elif layer in VOCABULARY_LAYERS:
        field = VOCABULARY_LAYERS[layer]
        palette = PALETTES.get(layer, {})
        values = cast("NDArray[np.int32]", getattr(atlas, field))
        paint(land & (values < 0), UNCLAIMED, words.label("none"))
        for index, key in enumerate(atlas.vocabulary[field]):
            colour = (250, 200, 40) if layer == "resources" and key in PRECIOUS else colour_of(key)
            colour = palette.get(key, colour)
            paint(land & (values == index), colour, words.key(key))
        if layer == "land":
            _tint(colours, atlas, land)
            _shade(colours, atlas, land)
    else:
        source, ramp_colours = (
            (atlas.complexity, RAMP)
            if layer == "development"
            else (atlas.population, POPULATION_RAMP)
        )
        inhabited = land & (source > 0) if layer == "population" else land
        top = int(source[inhabited].max()) if inhabited.any() else 1
        root = math.isqrt(max(1, top))
        for cell in np.flatnonzero(inhabited):
            value = int(source[cell])
            share = (
                value * 1000 // max(1, top)
                if layer == "development"
                else math.isqrt(value) * 1000 // root
            )
            colours[cell] = ramp(share, ramp_colours)
        paint(land & (source <= 0), UNCLAIMED, words.label("uninhabited"))
        for step, label in STEPS:
            _ = legend.setdefault(words.label(label), (len(legend), ramp(step, ramp_colours), 0))
    entries = sorted(legend.items(), key=lambda item: item[1][0])
    return colours, classes, [(label, colour, total) for label, (_, colour, total) in entries]


def _table(
    atlas: Atlas, layer: str, words: Words
) -> tuple[NDArray[np.uint8], list[tuple[str, tuple[int, int, int], int]]]:
    """Colour of every location for ``layer`` and the legend: label, colour, locations."""
    colours, _, entries = _paint(atlas, layer, words)
    return colours, entries


def _area_index(atlas: Atlas) -> tuple[NDArray[np.int32], list[Name]]:
    """Each location's area as a number, and the areas' names in order of first appearance."""
    numbers: dict[str, int] = {}
    names: list[Name] = []
    areas = np.empty(atlas.cells, dtype=np.int32)
    for cell, name in enumerate(atlas.areas):
        key = json.dumps(_write_name(name))
        if key not in numbers:
            numbers[key] = len(names)
            names.append(name)
        areas[cell] = numbers[key]
    return areas, names


def _tint(colours: NDArray[np.uint8], atlas: Atlas, land: NDArray[np.bool_]) -> None:
    """Pull the land toward the colour of its climate: snow in the cold, warmth in the tropics."""
    for index, key in enumerate(atlas.vocabulary["climate"]):
        tint = CLIMATE_TINTS.get(key)
        if tint is not None:
            colour, share = tint
            cells = land & (atlas.climate == index)
            mixed = (
                colours[cells].astype(np.int32) * (100 - share)
                + np.array(colour, dtype=np.int32) * share
            ) // 100
            colours[cells] = mixed.astype(np.uint8)


def _shade(colours: NDArray[np.uint8], atlas: Atlas, land: NDArray[np.bool_]) -> None:
    """Darken mountains and brighten plains a little, so the land layer reads as relief."""
    for index, key in enumerate(atlas.vocabulary["topography"]):
        factor = next((value for word, value in SHADES if word in key), 100)
        if factor != 100:  # noqa: PLR2004 - 100 is no change
            cells = land & (atlas.topography == index)
            shaded = colours[cells].astype(np.int32) * factor // 100
            colours[cells] = np.clip(shaded, 0, 255).astype(np.uint8)


def totals(atlas: Atlas) -> dict[str, int]:
    """What the world holds, counted: countries (states, tribes), cultures, religions, locations."""
    states = sum(1 for country in atlas.countries if country.kind == "state")
    return {
        "countries": len(atlas.countries),
        "states": states,
        "tribes": len(atlas.countries) - states,
        "cultures": len(atlas.vocabulary["culture"]),
        "religions": len(atlas.vocabulary["religion"]),
        "locations": atlas.cells,
        "land": int(np.count_nonzero(atlas.kinds == KINDS.index("land"))),
    }


def legend(
    atlas: Atlas, layer: str, words: Words = ENGLISH
) -> list[tuple[str, tuple[int, int, int], int]]:
    """The legend of a layer: what each colour is and how many locations have it, largest first."""
    return list(lens(atlas, layer, words).legend)


def lens(atlas: Atlas, layer: str, words: Words = ENGLISH) -> Lens:
    """``layer`` as a viewer paints it: colours, legend entries (as ``legend`` orders them),
    border values and, for a ramp, its colours from lowest to highest."""
    _check_layer(layer)
    colours, classes, entries = _paint(atlas, layer, words)
    steps = {words.label(label) for _, label in STEPS}
    fixed = [number for number, entry in enumerate(entries) if entry[0] in steps]
    rest = sorted(
        (number for number in range(len(entries)) if number not in fixed),
        key=lambda number: (-entries[number][2], entries[number][0]),
    )
    order = [*rest, *fixed]
    position = np.full(len(entries) + 1, -1, dtype=np.int32)
    position[np.array(order, dtype=np.int64)] = np.arange(len(order), dtype=np.int32)
    remapped = np.where(classes >= 0, position[classes], -1).astype(np.int32)
    ramp_colours = (RAMP if layer == "development" else POPULATION_RAMP) if layer in RAMPS else ()
    return Lens(
        layer=layer,
        colours=colours,
        classes=remapped,
        values=_value_map(atlas, layer),
        legend=tuple(entries[number] for number in order),
        ramp=ramp_colours,
    )


def _check_layer(layer: str) -> None:
    if layer not in LAYERS:
        message = f"Unknown layer {layer!r}; choose one of {', '.join(LAYERS)}"
        raise AtlasError(message)


def _value_map(atlas: Atlas, layer: str) -> NDArray[np.int32]:
    """What each location is, in the layer's own terms, for drawing borders where it changes."""
    if layer == "countries":
        return atlas.owner
    if layer in {"cultures", "religions"}:
        return getattr(atlas, "culture" if layer == "cultures" else "religion")
    if layer == "areas":
        return _area_index(atlas)[0]
    if layer in VOCABULARY_LAYERS and layer != "land":
        return cast("NDArray[np.int32]", getattr(atlas, VOCABULARY_LAYERS[layer]))
    return np.arange(atlas.cells, dtype=np.int32)


def render(
    atlas: Atlas, layer: str, *, highlight: Sequence[int] = (), borders: bool = True
) -> NDArray[np.uint8]:
    """The picture of ``layer``: height x width x 3, the box of the New World.

    Borders are drawn between countries, cultures and religions in their layers, and capitals
    are marked in the countries layer. ``highlight`` locations are outlined, for a search.
    """
    _check_layer(layer)
    colours, _ = _table(atlas, layer, ENGLISH)
    labels = atlas.labels
    background = np.array(OUTSIDE, dtype=np.uint8)
    table = np.concatenate([background[np.newaxis], colours])
    picture = table[labels]
    if borders and layer in BORDERED:
        values = np.concatenate([np.array([-2], dtype=np.int32), _value_map(atlas, layer)])[labels]
        land = np.concatenate([np.array([False]), atlas.kinds == KINDS.index("land")])[labels]
        edge = np.zeros(labels.shape, dtype=bool)
        edge[:, :-1] |= (values[:, :-1] != values[:, 1:]) & land[:, :-1] & land[:, 1:]
        edge[:-1, :] |= (values[:-1, :] != values[1:, :]) & land[:-1, :] & land[1:, :]
        picture[edge] = BORDER
    if layer == "countries":
        _capitals(picture, atlas)
    if len(highlight):
        _outline(picture, labels, np.array(sorted(set(highlight)), dtype=np.int64) + 1)
    return picture


def _capitals(picture: NDArray[np.uint8], atlas: Atlas) -> None:
    height, width = atlas.size
    for country in atlas.countries:
        if country.capital < 0:
            continue
        row, column = (int(value) for value in atlas.centre[country.capital])
        picture[
            max(0, row - 1) : min(height, row + 2), max(0, column - 1) : min(width, column + 2)
        ] = CAPITAL


def _outline(
    picture: NDArray[np.uint8], labels: NDArray[np.int32], wanted: NDArray[np.int64]
) -> None:
    inside = np.isin(labels, wanted)
    edge = inside.copy()
    edge[1:-1, 1:-1] &= ~(
        inside[:-2, 1:-1] & inside[2:, 1:-1] & inside[1:-1, :-2] & inside[1:-1, 2:]
    )
    picture[edge] = HIGHLIGHT


def cell_at(atlas: Atlas, row: int, column: int) -> int:
    """The location at a pixel of the box, or -1 outside the New World or the picture."""
    height, width = atlas.size
    if not (0 <= row < height and 0 <= column < width):
        return -1
    return int(atlas.labels[row, column]) - 1


def describe(atlas: Atlas, cell: int) -> Facts | None:
    """What the atlas says of location ``cell`` (None for -1)."""
    if not 0 <= cell < atlas.cells:
        return None
    owner = int(atlas.owner[cell])
    return Facts(
        key=atlas.keys[cell],
        name=atlas.names[cell],
        kind=KINDS[int(atlas.kinds[cell])],
        area=atlas.areas[cell],
        region=atlas.regions[cell],
        country=atlas.countries[owner] if owner >= 0 else None,
        culture=atlas.word("culture", int(atlas.culture[cell])),
        religion=atlas.word("religion", int(atlas.religion[cell])),
        material=atlas.word("material", int(atlas.material[cell])),
        climate=atlas.word("climate", int(atlas.climate[cell])),
        vegetation=atlas.word("vegetation", int(atlas.vegetation[cell])),
        topography=atlas.word("topography", int(atlas.topography[cell])),
        settlement=atlas.word("settlement", int(atlas.settlement[cell])),
        population=int(atlas.population[cell]),
        complexity=int(atlas.complexity[cell]),
    )


def find(atlas: Atlas, query: str, *, limit: int = 40, words: Words = ENGLISH) -> list[Match]:
    """Countries, cultures, religions, materials and places whose name contains ``query``, as
    ``words`` write them (an identifier or a tag is found as well)."""
    needle = query.strip().casefold()
    if not needle:
        return []
    found: list[Match] = []
    for number, country in enumerate(atlas.countries):
        label = words.name(country.name) if country.name else country.tag
        if needle in label.casefold() or needle == country.tag.casefold():
            cells = np.flatnonzero(atlas.owner == number)
            found.append(Match("country", f"{label} ({country.tag})", tuple(int(c) for c in cells)))
    for field, kind in (
        ("culture", "culture"),
        ("religion", "religion"),
        ("material", "material"),
    ):
        values = cast("NDArray[np.int32]", getattr(atlas, field))
        for index, key in enumerate(atlas.vocabulary[field]):
            label = words.key(key)
            if needle in label.casefold() or needle in key.casefold():
                cells = np.flatnonzero(values == index)
                found.append(Match(kind, label, tuple(int(c) for c in cells)))
    for cell, name in enumerate(atlas.names):
        written = words.name(name) if name else ""
        if written and needle in written.casefold() and atlas.kinds[cell] != KINDS.index("sea"):
            found.append(Match("place", written, (cell,)))
    return found[:limit]


def to_files(atlas: Atlas) -> tuple[bytes, bytes]:
    """The atlas as the two files an export writes: ``atlas.json`` and ``atlas_labels.png``."""
    labels = atlas.labels.astype(np.uint32)
    raster = np.stack([(labels >> 16) & 0xFF, (labels >> 8) & 0xFF, labels & 0xFF], axis=-1).astype(
        np.uint8
    )
    png = encode_png(raster, color_type=COLOR_RGB, compression="zlib")
    document: dict[str, object] = {
        "format": FORMAT,
        "scale": atlas.scale,
        "size": list(atlas.size),
        "vocabulary": {name: list(words) for name, words in atlas.vocabulary.items()},
        "countries": [
            {
                "tag": c.tag,
                "name": _write_name(c.name),
                "kind": c.kind,
                "color": list(c.color),
                "capital": c.capital,
                "culture": c.culture,
                "religion": c.religion,
                "locations": c.locations,
            }
            for c in atlas.countries
        ],
        "locations": {
            "key": list(atlas.keys),
            "name": [_write_name(name) for name in atlas.names],
            "kind": atlas.kinds.tolist(),
            "area": [_write_name(name) for name in atlas.areas],
            "region": [_write_name(name) for name in atlas.regions],
            "owner": atlas.owner.tolist(),
            "culture": atlas.culture.tolist(),
            "religion": atlas.religion.tolist(),
            "material": atlas.material.tolist(),
            "climate": atlas.climate.tolist(),
            "vegetation": atlas.vegetation.tolist(),
            "topography": atlas.topography.tolist(),
            "settlement": atlas.settlement.tolist(),
            "population": atlas.population.tolist(),
            "complexity": atlas.complexity.tolist(),
            "centre": atlas.centre.tolist(),
        },
    }
    text = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    return text.encode("ascii"), png


def from_files(document: bytes, labels_png: bytes) -> Atlas:
    """Read an atlas from its two files; raises ``AtlasError`` when they are damaged or too big."""
    try:
        return _parse(document, labels_png)
    except AtlasError:
        raise
    except (KeyError, TypeError, ValueError, OSError, UnicodeDecodeError) as error:
        message = f"The atlas is damaged: {error!r}"
        raise AtlasError(message) from error


def _parse(document: bytes, labels_png: bytes) -> Atlas:
    data = cast("dict[str, object]", json.loads(document.decode("utf-8")))
    if data.get("format") not in READS:
        message = f"The atlas has format {data.get('format')!r}; this generator reads {FORMAT}"
        raise AtlasError(message)
    with Image.open(io.BytesIO(labels_png)) as image:
        if image.width * image.height > MAX_PIXELS:
            message = "The atlas picture is too large"
            raise AtlasError(message)
        raster = np.asarray(image.convert("RGB")).astype(np.uint32)
    labels = ((raster[..., 0] << 16) | (raster[..., 1] << 8) | raster[..., 2]).astype(np.int32)
    columns = cast("dict[str, list[object]]", data["locations"])
    count = len(columns["key"])
    if count > MAX_CELLS or int(labels.max(initial=0)) > count:
        message = "The atlas picture names locations the atlas does not have"
        raise AtlasError(message)
    if any(len(values) != count for values in columns.values()):
        message = "The columns of the atlas differ in length"
        raise AtlasError(message)
    countries = tuple(_country(item) for item in cast("list[dict[str, object]]", data["countries"]))
    vocabulary = {
        name: tuple(str(word) for word in words)
        for name, words in cast("dict[str, list[object]]", data["vocabulary"]).items()
    }
    return Atlas(
        scale=_int(data["scale"]),
        labels=labels,
        keys=tuple(str(v) for v in columns["key"]),
        names=tuple(_read_name(v) for v in columns["name"]),
        kinds=np.array(columns["kind"], dtype=np.uint8),
        areas=tuple(_read_name(v) for v in columns["area"]),
        regions=tuple(_read_name(v) for v in columns["region"]),
        owner=_int32(columns["owner"]),
        culture=_int32(columns["culture"]),
        religion=_int32(columns["religion"]),
        material=_int32(columns["material"]),
        climate=_int32(columns["climate"]),
        vegetation=_int32(columns["vegetation"]),
        topography=_int32(columns["topography"]),
        settlement=_int32(columns["settlement"]),
        population=_int64(columns["population"]),
        complexity=_int64(columns["complexity"]),
        centre=np.array(columns["centre"], dtype=np.int32).reshape(count, 2),
        countries=countries,
        vocabulary=vocabulary,
    )


def _write_name(name: Name) -> object:
    """A name in the atlas: a proper word as text, a phrase as [term, word, compass points...]."""
    return name if isinstance(name, str) else [name.term, name.word, *name.sectors]


def _read_name(value: object) -> Name:
    if isinstance(value, str):
        return value
    parts = [str(part) for part in cast("list[object]", value)] if isinstance(value, list) else []
    if len(parts) < 2:  # noqa: PLR2004 - a phrase is a term and a word, then its compass points
        message = f"Expected a name, found {value!r}"
        raise TypeError(message)
    return Phrase(parts[0], parts[1], tuple(parts[2:]))


def _int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        message = f"Expected a whole number, found {value!r}"
        raise TypeError(message)
    return value


def _int32(values: list[object]) -> NDArray[np.int32]:
    return np.array([_int(value) for value in values], dtype=np.int32)


def _int64(values: list[object]) -> NDArray[np.int64]:
    return np.array([_int(value) for value in values], dtype=np.int64)


def _country(item: dict[str, object]) -> Country:
    color = cast("list[object]", item["color"])
    return Country(
        tag=str(item["tag"]),
        name=_read_name(item["name"]),
        kind=str(item["kind"]),
        color=(_int(color[0]), _int(color[1]), _int(color[2])),
        capital=_int(item["capital"]),
        culture=_int(item["culture"]),
        religion=_int(item["religion"]),
        locations=_int(item["locations"]),
    )
