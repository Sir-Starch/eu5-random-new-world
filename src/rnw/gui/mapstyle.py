"""A world's map as the classic window draws it, as the Tauri window does (ADR 0011).

Every lens lies over the physical map: the land's colour from its vegetation and climate,
softened across the edges of locations; a relief shade from a height each location's
topography suggests, smoothed and roughened into ridges where it is mountainous; the water by
its distance from the shore, darkening into the open ocean. A thematic lens covers the land with
its colours as strongly as its profile says; land that holds nothing of the lens shows the
physical map faded. Countries colours states only, as the game's political map does, unless
tribes are asked for. The palettes and profiles are ``lenses.json``, which the Tauri window
reads too; the arithmetic is that of ``desktop/src/lib/relief.ts`` and ``lenses.ts``.

Nothing here imports Qt: ``picture`` gives pixels, ``names`` and ``places`` what is written and
marked over them, and the window paints those at its own zoom. The atlas holds no heightmap, so
the relief is drawn from what it holds rather than measured.
"""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal, cast

import numpy as np

from rnw import atlas as atlas_module
from rnw.gui.text import grouped
from rnw.topology import euclidean_distance

if TYPE_CHECKING:
    from collections.abc import Iterable

    from numpy.typing import NDArray

    from rnw.atlas import Atlas, Words

RGB = tuple[int, int, int]
STYLE: Final[dict[str, object]] = cast(
    "dict[str, object]",
    json.loads(Path(__file__).with_name("lenses.json").read_text(encoding="utf-8")),
)
# The physical fields are at half the atlas's resolution, sampled at the centre of each 2 x 2.
STEP: Final[int] = 2
LAND: Final[int] = atlas_module.KINDS.index("land")
WASTELAND: Final[int] = atlas_module.KINDS.index("wasteland")
SEA: Final[int] = atlas_module.KINDS.index("sea")
LAKE: Final[int] = atlas_module.KINDS.index("lake")
# The ink of lines and the colour that marks what is isolated, as the dark map draws them.
INK: Final[tuple[float, float, float]] = (8 / 255, 10 / 255, 14 / 255)
ACCENT: Final[tuple[float, float, float]] = (1.0, 213 / 255, 74 / 255)
FOAM: Final[tuple[float, float, float]] = (0.86, 0.93, 1.0)
LIGHT: Final[tuple[float, float, float]] = (-0.55, -0.62, 0.56)
RELIEF_Z: Final[float] = 9.0
# Land rougher than this gets ridges; land softened to less than this share is no land; a colour
# less opaque than this does not cover the physical map.
ROUGH: Final[float] = 0.01
SOME_LAND: Final[float] = 0.001
SOME_COVER: Final[float] = 0.004
# Fields kept for atlases looked at last (the physical map at full resolution is larger).
KEPT_RELIEFS: Final[int] = 4
KEPT_GROUNDS: Final[int] = 2


def hex_rgb(colour: str) -> RGB:
    """``#rrggbb`` as three numbers."""
    value = int(colour.removeprefix("#"), 16)
    return (value >> 16) & 255, (value >> 8) & 255, value & 255


def rgb_hex(colour: Iterable[float]) -> str:
    """Three numbers as ``#rrggbb``, rounded as the Tauri window rounds them."""
    return "#" + "".join(f"{_round(value):02x}" for value in colour)


def _round(value: float) -> int:
    """JavaScript's ``Math.round``: halves go up."""
    return math.floor(value + 0.5)


def _section(name: str) -> dict[str, object]:
    return cast("dict[str, object]", STYLE[name])


def _palette(source: object) -> dict[str, RGB]:
    return {key: hex_rgb(str(value)) for key, value in cast("dict[str, str]", source).items()}


@dataclass(frozen=True, slots=True)
class Profile:
    """How a lens looks: see ``lenses.json``."""

    physical: bool
    shade: float
    borders: float
    political: float
    names: Literal["regions", "countries", "classes", "none"]
    spots: Literal["resource", "population", "development"] | None
    opacity: int


PROFILES: Final[dict[str, Profile]] = {
    layer: Profile(**cast("dict[str, object]", values))  # pyright: ignore[reportArgumentType]
    for layer, values in _section("profiles").items()
}
QUALITATIVE: Final[tuple[RGB, ...]] = tuple(
    hex_rgb(colour) for colour in cast("list[str]", STYLE["qualitative"])
)
PALETTE: Final[int] = len(QUALITATIVE)
PALETTES: Final[dict[str, dict[str, RGB]]] = {
    name: _palette(values) for name, values in _section("palettes").items()
}
PRECIOUS: Final[dict[str, RGB]] = _palette(STYLE["precious"])
VEGETATION: Final[dict[str, RGB]] = _palette(STYLE["vegetation"])
CLIMATE_TINTS: Final[dict[str, tuple[RGB, float]]] = {
    key: (hex_rgb(str(value[0])), float(cast("float", value[1])))
    for key, value in cast("dict[str, list[object]]", STYLE["climate_tints"]).items()
}
TOPOGRAPHY: Final[dict[str, dict[str, float]]] = cast(
    "dict[str, dict[str, float]]", STYLE["topography"]
)
COLOURS: Final[dict[str, RGB]] = _palette(STYLE["colours"])
COAST_DEPTH: Final[float] = float(cast("float", STYLE["coast_depth"]))
TRIBE_OPACITY: Final[int] = int(cast("int", STYLE["tribe_opacity"]))
RAMP_OPACITY: Final[tuple[int, int]] = cast("tuple[int, int]", tuple(STYLE["ramp_opacity"]))  # pyright: ignore[reportArgumentType]
# Lenses whose classes need only differ from their neighbours, coloured from QUALITATIVE.
NEIGHBOURLY: Final[dict[str, str]] = {"cultures": "culture", "religions": "religion", "areas": ""}
# Lenses whose classes are a vocabulary with a palette of its own.
PALETTED: Final[dict[str, tuple[str, str]]] = {
    "resources": ("material", "resources"),
    "climate": ("climate", "climate"),
    "terrain": ("topography", "terrain"),
}


def profile(layer: str) -> Profile:
    """The look of ``layer``."""
    return PROFILES.get(layer, PROFILES["cultures"])


# -- the physical map ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, eq=False)
class Relief:
    """The physical map at half the atlas's resolution: the land's colour (0..255), its shade
    (1 is level ground) and the water's distance from the land, in field pixels."""

    land: NDArray[np.float32]
    shade: NDArray[np.float32]
    depth: NDArray[np.float32]


def _mix(a: NDArray[np.float32], b: RGB, share: float | NDArray[np.float32]) -> NDArray[np.float32]:
    colour = np.asarray(b, dtype=np.float32)
    return (a + (colour - a) * np.asarray(share, dtype=np.float32)).astype(np.float32)


def physical_colours(atlas: Atlas) -> NDArray[np.float32]:
    """Each location's land on the physical map, before softening and shade (cells x 3)."""
    words = atlas.vocabulary
    colours = np.zeros((atlas.cells, 3), dtype=np.float32)
    for cell in range(atlas.cells):
        vegetation = (
            atlas.word("vegetation", int(atlas.vegetation[cell])) if "vegetation" in words else ""
        )
        climate = atlas.word("climate", int(atlas.climate[cell])) if "climate" in words else ""
        topography = (
            atlas.word("topography", int(atlas.topography[cell])) if "topography" in words else ""
        )
        rgb = np.asarray(VEGETATION.get(vegetation, VEGETATION["grasslands"]), dtype=np.float32)
        tint = CLIMATE_TINTS.get(climate)
        if tint is not None:
            rgb = _mix(rgb, tint[0], tint[1])
        if topography == "wetlands":
            rgb = _mix(rgb, COLOURS["wetland"], 0.32)
        rock = TOPOGRAPHY.get(topography, {}).get("rock", 0.0)
        barren = 0.55 if int(atlas.kinds[cell]) == WASTELAND else rock
        if barren > 0:
            rgb = _mix(rgb, COLOURS["rock"], barren)
        cold = climate in {"arctic", "subpolar", "cold_arid"}
        if cold and (int(atlas.kinds[cell]) == WASTELAND or topography == "mountains"):
            rgb = _mix(rgb, COLOURS["snow"], 0.45)
        colours[cell] = rgb
    return colours


def blur(values: NDArray[np.float32], radius: int, passes: int = 2) -> NDArray[np.float32]:
    """A box blur along rows then columns, ``passes`` times, edges repeated: near a gaussian."""
    out = values.astype(np.float32)
    span = 2 * radius + 1
    for _ in range(passes):
        for axis in (1, 0):
            padded = np.pad(
                out, [(radius, radius) if a == axis else (0, 0) for a in range(2)], mode="edge"
            )
            summed = np.cumsum(padded, axis=axis, dtype=np.float64)
            summed = np.concatenate(
                [np.zeros_like(np.take(summed, [0], axis=axis)), summed], axis=axis
            )
            length = int(summed.shape[axis])
            ahead = np.take(summed, np.arange(span, length), axis=axis)
            behind = np.take(summed, np.arange(0, length - span), axis=axis)
            out = ((ahead - behind) / span).astype(np.float32)
    return out


def _lattice(x: NDArray[np.int64], y: NDArray[np.int64]) -> NDArray[np.float32]:
    """Hashed lattice values in -1..1, bit for bit those of relief.ts."""
    with np.errstate(over="ignore"):
        h = x.astype(np.uint32) * np.uint32(374761393) + y.astype(np.uint32) * np.uint32(668265263)
        h = (h ^ (h >> np.uint32(13))) * np.uint32(1274126177)
    return ((h ^ (h >> np.uint32(16))) & np.uint32(0xFFFF)).astype(np.float32) / 32767.5 - 1


def _noise(x: NDArray[np.float32], y: NDArray[np.float32]) -> NDArray[np.float32]:
    x0 = np.floor(x)
    y0 = np.floor(y)
    fx = x - x0
    fy = y - y0
    sx = fx * fx * (3 - 2 * fx)
    sy = fy * fy * (3 - 2 * fy)
    ix = x0.astype(np.int64)
    iy = y0.astype(np.int64)
    top = _lattice(ix, iy) + (_lattice(ix + 1, iy) - _lattice(ix, iy)) * sx
    bottom = _lattice(ix, iy + 1) + (_lattice(ix + 1, iy + 1) - _lattice(ix, iy + 1)) * sx
    return (top + (bottom - top) * sy).astype(np.float32)


def _ridges(x: NDArray[np.float32], y: NDArray[np.float32]) -> NDArray[np.float32]:
    total = np.zeros(x.shape, dtype=np.float32)
    amplitude = 0.5
    frequency = 1 / 9
    for _ in range(3):
        total += amplitude * (1 - np.abs(_noise(x * frequency, y * frequency)))
        amplitude *= 0.5
        frequency *= 2.1
    return total / 0.875


def _lake_heights(
    sample: NDArray[np.int64],
    solid: NDArray[np.bool_],
    lake: NDArray[np.bool_],
    high: NDArray[np.float32],
) -> NDArray[np.float32]:
    """The height of every lake pixel: the mean height of the land its location touches.

    Each lake location takes the mean over its pixels' land neighbours (up, down, left and
    right) of those neighbours' heights; one that touches no land takes flatland's.
    """
    cells = len(high)
    total = np.zeros(cells, dtype=np.float64)
    count = np.zeros(cells, dtype=np.float64)
    for here, there in (
        (np.s_[1:, :], np.s_[:-1, :]),
        (np.s_[:-1, :], np.s_[1:, :]),
        (np.s_[:, 1:], np.s_[:, :-1]),
        (np.s_[:, :-1], np.s_[:, 1:]),
    ):
        meeting = lake[here] & solid[there]
        owner = sample[here][meeting]
        total += np.bincount(owner, weights=high[sample[there][meeting]], minlength=cells)
        count += np.bincount(owner, minlength=cells)
    flat = TOPOGRAPHY["flatland"]["height"]
    mean = np.where(count > 0, total / np.maximum(count, 1), flat).astype(np.float32)
    return mean[np.maximum(sample, 0)]


_RELIEFS: dict[int, tuple[Atlas, Relief]] = {}


def relief(atlas: Atlas) -> Relief:
    """The physical fields of ``atlas``, worked out once (the last few are kept)."""
    known = _RELIEFS.get(id(atlas))
    if known is not None and known[0] is atlas:
        return known[1]
    labels = atlas.labels.astype(np.int64) - 1
    sample = labels[1::STEP, 1::STEP] if min(atlas.size) > 1 else labels
    height, width = sample.shape
    kinds = atlas.kinds.astype(np.int64)
    kind = np.where(sample >= 0, kinds[np.maximum(sample, 0)], SEA)
    solid = (kind == LAND) | (kind == WASTELAND)
    lake = kind == LAKE
    water = ~solid
    mask = solid.astype(np.float32)
    colours = physical_colours(atlas)
    cell = np.maximum(sample, 0)
    high = np.zeros(atlas.cells, dtype=np.float32)
    rough = np.zeros(atlas.cells, dtype=np.float32)
    for index in range(atlas.cells):
        topography = atlas.word("topography", int(atlas.topography[index]))
        found = TOPOGRAPHY.get(topography, TOPOGRAPHY["flatland"])
        if int(atlas.kinds[index]) == WASTELAND:
            found = TOPOGRAPHY["mountain_wasteland"]
        high[index], rough[index] = found["height"], found["rough"]
    share = blur(mask, 2)
    soft = [
        blur(np.where(solid, colours[cell, channel], 0).astype(np.float32), 2)
        for channel in range(3)
    ]
    heights = np.where(solid, high[cell], 0).astype(np.float32)
    # A lake lies in the land: its surface is as high as the land that meets it, not a pit
    # whose walls the shade would draw as a crater, and only the sea is a shore.
    heights = np.where(lake, _lake_heights(sample, solid, lake, high), heights)
    base = blur(heights, 6, 3)
    grain = blur(np.where(solid, rough[cell], 0).astype(np.float32), 3)
    shore = euclidean_distance(water & ~lake, 8 * 64).astype(np.float32) / 8
    coast = np.minimum(1, shore / 6)
    rows, columns = np.mgrid[0:height, 0:width].astype(np.float32)
    ridged = np.where(grain > ROUGH, grain * 0.2 * _ridges(columns, rows), 0)
    lift = np.where(solid | lake, (base + ridged) * coast, 0).astype(np.float32)
    left = np.concatenate([lift[:, :1], lift[:, :-1]], axis=1)
    right = np.concatenate([lift[:, 1:], lift[:, -1:]], axis=1)
    up = np.concatenate([lift[:1], lift[:-1]], axis=0)
    down = np.concatenate([lift[1:], lift[-1:]], axis=0)
    nx = (left - right) * RELIEF_Z
    ny = (up - down) * RELIEF_Z
    lit = (nx * LIGHT[0] + ny * LIGHT[1] + LIGHT[2]) / np.sqrt(nx * nx + ny * ny + 1)
    shade = (np.clip(np.floor(lit / LIGHT[2] * 128 + 0.5), 0, 255) / 128).astype(np.float32)
    variation = 1 + 0.035 * _noise(columns / 3.1, rows / 3.1)
    weight = np.maximum(share, 1e-6)
    land = np.stack(
        [np.clip(np.floor(s / weight * variation + 0.5), 0, 255) for s in soft], axis=-1
    )
    land = np.where((share > SOME_LAND)[..., None], land, 0).astype(np.float32)
    depth = np.minimum(255, euclidean_distance(solid, 8 * 255).astype(np.float32) / 8)
    found = Relief(land=land, shade=shade, depth=np.where(water, depth, 0).astype(np.float32))
    while len(_RELIEFS) >= KEPT_RELIEFS:
        del _RELIEFS[next(iter(_RELIEFS))]
    _RELIEFS[id(atlas)] = (atlas, found)
    return found


def _axis(size: int, n: int) -> tuple[NDArray[np.int64], NDArray[np.int64], NDArray[np.float32]]:
    """For each of ``size`` atlas pixels, the two field samples around it and the share of the
    second: bilinear filtering of a field sampled at the centre of every 2 x 2 block."""
    position = (np.arange(size, dtype=np.float32) + 0.5) / STEP - 0.5
    low = np.floor(position)
    share = (position - low).astype(np.float32)
    first = np.clip(low.astype(np.int64), 0, n - 1)
    return first, np.clip(first + 1, 0, n - 1), share


def _band(field: NDArray[np.float32], rows: slice, width: int) -> NDArray[np.float32]:
    """Rows ``rows`` of a field brought to the atlas's resolution."""
    height = int(rows.stop - rows.start)
    top, bottom, down = _axis(rows.stop, field.shape[0])
    top, bottom, down = top[rows], bottom[rows], down[rows]
    left, right, across = _axis(width, field.shape[1])
    tail = (1,) * (field.ndim - 2)
    vertical = field[top] + (field[bottom] - field[top]) * down.reshape((height, 1, *tail))
    wide = vertical[:, left] + (vertical[:, right] - vertical[:, left]) * across.reshape(
        (1, width, *tail)
    )
    return wide.astype(np.float32)


# -- the lenses ---------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, eq=False)
class StyledLens:
    """A lens as it is drawn: per location its colour, how strongly that covers the physical
    map (0: the map faded), its legend entry and the value whose change draws a line; the
    legend, largest first, as label, colour and locations."""

    layer: str
    colours: NDArray[np.uint8]
    opacity: NDArray[np.uint8]
    classes: NDArray[np.int32]
    values: NDArray[np.int32]
    legend: tuple[tuple[str, RGB, int], ...]
    ramp: tuple[RGB, ...]


def _hashed(key: str) -> RGB:
    """FNV-1a over the key's UTF-16 units, as lenses.ts picks a colour for an unknown key."""
    h = 2166136261
    for unit in _units(key):
        h = ((h ^ unit) * 16777619) & 0xFFFFFFFF
    return QUALITATIVE[h % len(QUALITATIVE)]


def _units(key: str) -> list[int]:
    raw = key.encode("utf-16-le")
    return [raw[i] | raw[i + 1] << 8 for i in range(0, len(raw), 2)]


def _nudge(colour: RGB, key: int) -> tuple[float, float, float]:
    """A colour a little lighter or darker by ``key``, so neighbours of one hue differ."""
    factor = 1 + (((key * 2654435761) % 2**32) % 7 - 3) * 0.035
    return (
        min(255, colour[0] * factor),
        min(255, colour[1] * factor),
        min(255, colour[2] * factor),
    )


def neighbours(atlas: Atlas, class_of: NDArray[np.int32], classes: int) -> list[set[int]]:
    """For each class, the classes that touch it across the land."""
    labels = atlas.labels.astype(np.int64) - 1
    kinds = np.concatenate([atlas.kinds.astype(np.int64), np.array([-1])])
    owner = np.concatenate([class_of.astype(np.int64), np.array([-1])])
    out: list[set[int]] = [set() for _ in range(classes)]
    found: list[list[int]] = []
    for a, b in ((labels[:, :-1], labels[:, 1:]), (labels[:-1, :], labels[1:, :])):
        ka, kb = kinds[a], kinds[b]
        ca, cb = owner[a], owner[b]
        pick = (a != b) & (ka == LAND) & (kb == LAND) & (ca >= 0) & (cb >= 0) & (ca != cb)
        pairs = np.unique(np.stack([ca[pick], cb[pick]], axis=1), axis=0)
        found.extend(cast("list[list[int]]", pairs.tolist()))
    for first, second in found:
        out[first].add(second)
        out[second].add(first)
    return out


def colour_classes(
    adjacent: list[set[int]], sizes: list[float], palette: int = PALETTE
) -> list[int]:
    """Colours for classes so that no two neighbours share one, largest classes first."""
    order = sorted(range(len(sizes)), key=lambda k: (-sizes[k], k))
    colours = [-1] * len(sizes)
    use = [0] * palette
    for k in order:
        taken = {colours[n] for n in adjacent[k] if colours[n] >= 0}
        best = -1
        for step in range(palette):
            candidate = (k * 7 + step) % palette
            if candidate in taken:
                continue
            if best < 0 or use[candidate] < use[best]:
                best = candidate
        if best < 0:
            best = k % palette
        colours[k] = best
        use[best] += 1
    return colours


@dataclass(slots=True, eq=False)
class _Draft:
    """A lens being styled: its colours, opacity, classes and legend, changed in place."""

    atlas: Atlas
    look: Profile
    land: NDArray[np.bool_]
    colours: NDArray[np.uint8]
    opacity: NDArray[np.uint8]
    classes: NDArray[np.int32]
    legend: list[tuple[str, RGB, int]]

    def first_word(self, column: NDArray[np.int32], field: str) -> list[str | None]:
        """For each legend entry, the word of ``field`` at its first land location."""
        found: list[str | None] = [None] * len(self.legend)
        for cell in np.flatnonzero(self.land & (self.classes >= 0) & (column >= 0)):
            k = int(self.classes[cell])
            if found[k] is None:
                found[k] = self.atlas.word(field, int(column[cell]))
        return found

    def recolour(self, colour_of: list[RGB | tuple[float, float, float] | None]) -> None:
        """New colours for legend entries (None keeps one) and for their land locations."""
        for k, colour in enumerate(colour_of):
            if colour is not None:
                label, _, count = self.legend[k]
                self.legend[k] = (label, hex_rgb(rgb_hex(colour)), count)
        table = np.array([entry[1] for entry in self.legend] + [(0, 0, 0)], dtype=np.uint8)
        painted = self.land & (self.classes >= 0)
        self.colours[painted] = table[self.classes[painted]]


def _countries(draft: _Draft, *, tribes: bool, tribes_label: str) -> None:
    """States coloured; tribes too, more lightly, when asked for, else under one entry."""
    atlas = draft.atlas
    tribal = np.array([country.kind != "state" for country in atlas.countries] + [False])
    owner = atlas.owner.astype(np.int64)
    is_tribe = tribal[np.where(owner >= 0, owner, len(atlas.countries))]
    classes, legend = draft.classes, draft.legend
    entries = sorted({int(k) for k in classes[(owner >= 0) & is_tribe & (classes >= 0)]})
    if not tribes and entries:
        kept = [k for k in range(len(legend)) if k not in set(entries)]
        count = sum(legend[k][2] for k in entries)
        merged = [legend[k] for k in kept] + [(tribes_label, COLOURS["tribal"], count)]
        order = sorted(range(len(merged)), key=lambda k: (-merged[k][2], k))
        position = np.empty(len(merged), dtype=np.int32)
        position[np.array(order)] = np.arange(len(order), dtype=np.int32)
        remap = np.full(len(legend), -1, dtype=np.int32)
        for n, k in enumerate(kept):
            remap[k] = position[n]
        for k in entries:
            remap[k] = position[len(kept)]
        draft.classes = np.where(classes >= 0, remap[np.maximum(classes, 0)], -1).astype(np.int32)
        draft.legend = [merged[k] for k in order]
    draft.opacity[draft.land & (owner >= 0) & ~is_tribe] = draft.look.opacity
    if tribes:
        draft.opacity[draft.land & (owner >= 0) & is_tribe] = TRIBE_OPACITY


def _neighbourly(draft: _Draft, field: str) -> None:
    """Classes that only need to differ from their neighbours: cultures, religions, areas."""
    atlas = draft.atlas
    column = (
        cast("NDArray[np.int32]", getattr(atlas, field))
        if field
        else np.zeros(atlas.cells, dtype=np.int32)
    )
    pixels = np.bincount(atlas.labels.ravel(), minlength=atlas.cells + 1)[1:].astype(np.float64)
    own = np.where(draft.land & (column >= 0) & (draft.classes >= 0), draft.classes, -1)
    own = own.astype(np.int32)
    entries = len(draft.legend)
    sizes = np.bincount(own[own >= 0], weights=pixels[own >= 0], minlength=entries).tolist()
    picked = colour_classes(neighbours(atlas, own, entries), sizes)
    draft.recolour(
        [_nudge(QUALITATIVE[picked[k]], k) if sizes[k] > 0 else None for k in range(entries)]
    )
    draft.opacity[own >= 0] = draft.look.opacity


def _paletted(draft: _Draft, field: str, palette: dict[str, RGB]) -> None:
    """A vocabulary with a palette of its own: resources, climate, terrain."""
    column = cast("NDArray[np.int32]", getattr(draft.atlas, field))
    found = draft.first_word(column, field)
    draft.recolour([None if word is None else palette.get(word, _hashed(word)) for word in found])
    draft.opacity[draft.land & (column >= 0)] = draft.look.opacity


def _ramp(draft: _Draft, layer: str) -> None:
    """A ramp fades into the physical map at its low end."""
    atlas, land = draft.atlas, draft.land
    source = (atlas.complexity if layer == "development" else atlas.population).astype(np.float64)
    top = max(1.0, float(source[land].max()) if land.any() else 1.0)
    inhabited = land & (source > 0)
    share = source / top if layer == "development" else np.sqrt(source / top)
    values = np.floor(RAMP_OPACITY[0] + RAMP_OPACITY[1] * share + 0.5)
    draft.opacity[inhabited] = values[inhabited].astype(np.uint8)


def style(atlas: Atlas, layer: str, words: Words, *, tribes: bool, tribes_label: str) -> StyledLens:
    """``layer`` as it is drawn (``lenses.ts``'s ``style``)."""
    lens = atlas_module.lens(atlas, layer, words)
    draft = _Draft(
        atlas=atlas,
        look=profile(layer),
        land=atlas.kinds.astype(np.int64) == LAND,
        colours=lens.colours.copy(),
        opacity=np.zeros(atlas.cells, dtype=np.uint8),
        classes=lens.classes.copy(),
        legend=list(lens.legend),
    )
    if layer == "countries":
        _countries(draft, tribes=tribes, tribes_label=tribes_label)
    elif layer in NEIGHBOURLY:
        _neighbourly(draft, NEIGHBOURLY[layer])
    elif layer in PALETTED:
        field, palette = PALETTED[layer]
        _paletted(draft, field, PALETTES[palette])
    elif layer == "land":
        for k, word in enumerate(draft.first_word(atlas.vegetation, "vegetation")):
            if word is not None and word in VEGETATION:
                draft.legend[k] = (draft.legend[k][0], VEGETATION[word], draft.legend[k][2])
    elif layer in {"development", "population"}:
        _ramp(draft, layer)
    unclaimed = COLOURS["unclaimed"]
    legend = tuple(
        (label, COLOURS["faded"] if colour == unclaimed else colour, count)
        for label, colour, count in draft.legend
    )
    return StyledLens(
        layer=layer,
        colours=draft.colours,
        opacity=draft.opacity,
        classes=draft.classes,
        values=lens.values.astype(np.int32),
        legend=legend,
        ramp=lens.ramp,
    )


# -- the picture --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Overlays:
    """What is drawn over a lens: lines where it changes, country borders, location borders and
    the coasts."""

    lens_borders: bool = True
    political: bool = True
    locations: bool = False
    coast: bool = True


def _smooth(edge0: float, edge1: float, value: NDArray[np.float32]) -> NDArray[np.float32]:
    t = np.clip((value - edge0) / (edge1 - edge0), 0, 1)
    return (t * t * (3 - 2 * t)).astype(np.float32)


def lines(
    atlas: Atlas, lens: StyledLens, *, tribes: bool, overlays: Overlays
) -> tuple[NDArray[np.float32], NDArray[np.bool_]]:
    """How strongly each pixel takes the ink of a line (lens borders, country borders, location
    borders, coasts), and where the sea foams against the land."""
    look = profile(lens.layer)
    labels = atlas.labels.astype(np.int64) - 1
    inside = labels >= 0
    cell = np.maximum(labels, 0)
    kinds = np.where(inside, atlas.kinds.astype(np.int64)[cell], SEA)
    solid = (kinds == LAND) | (kinds == WASTELAND)
    on_land = kinds == LAND
    owner = atlas.owner.astype(np.int64)
    states = np.array([country.kind == "state" for country in atlas.countries] + [False])
    shown = np.where((owner >= 0) & (tribes | states[np.where(owner >= 0, owner, -1)]), owner, -1)
    country = np.where(inside, shown[cell], -1)
    value = np.where(inside, lens.values.astype(np.int64)[cell], -(2**40))
    shape = atlas.size
    lens_line = np.zeros(shape, dtype=bool)
    border = np.zeros(shape, dtype=bool)
    locations = np.zeros(shape, dtype=bool)
    shore = np.zeros(shape, dtype=bool)
    foam = np.zeros(shape, dtype=bool)
    for here, there in _NEIGHBOURS:
        both = on_land[here] & on_land[there] & (labels[here] != labels[there])
        lens_line[here] |= both & (value[here] != value[there])
        claimed = (country[here] >= 0) | (country[there] >= 0)
        border[here] |= both & claimed & (country[here] != country[there])
        locations[here] |= both
        shore[here] |= solid[here] & ~solid[there]
        foam[here] |= ~solid[here] & solid[there]
    kept = np.ones(shape, dtype=np.float32)
    for mask, share, wanted in (
        (locations, 0.16, overlays.locations),
        (lens_line, look.borders, overlays.lens_borders),
        (border, look.political, overlays.political),
        (shore, 0.3, overlays.coast),
    ):
        if wanted and share > 0:
            kept[mask] *= 1 - share
    return 1 - kept, foam & overlays.coast


_NEIGHBOURS: Final = (
    ((slice(None), slice(None, -1)), (slice(None), slice(1, None))),
    ((slice(None), slice(1, None)), (slice(None), slice(None, -1))),
    ((slice(None, -1), slice(None)), (slice(1, None), slice(None))),
    ((slice(1, None), slice(None)), (slice(None, -1), slice(None))),
)
BAND: Final[int] = 128


@dataclass(frozen=True, slots=True, eq=False)
class Ground:
    """The physical map at the atlas's resolution, the same under every lens: the water's
    colour, the land's colour and its shade (128 is level ground)."""

    water: NDArray[np.uint8]
    land: NDArray[np.uint8]
    shade: NDArray[np.uint8]


_GROUNDS: dict[int, tuple[Atlas, Ground]] = {}


def ground(atlas: Atlas) -> Ground:
    """The physical map of ``atlas`` at its own resolution, worked out once (the last few are
    kept): the half-resolution fields filtered up, as the GPU filters them."""
    known = _GROUNDS.get(id(atlas))
    if known is not None and known[0] is atlas:
        return known[1]
    field = relief(atlas)
    height, width = atlas.size
    labels = atlas.labels
    t = _smooth(0, COAST_DEPTH, field.depth)[..., None]
    far = _smooth(COAST_DEPTH, COAST_DEPTH * 3, field.depth)[..., None]
    colour = {name: np.array(COLOURS[name], np.float32) for name in COLOURS}
    sea = colour["shallow"] + (colour["deep"] - colour["shallow"]) * t
    sea = (sea + (colour["ocean"] - sea) * far).astype(np.float32)
    lake = (colour["lake_shallow"] + (colour["lake_deep"] - colour["lake_shallow"]) * t).astype(
        np.float32
    )
    lakes = np.concatenate([[False], atlas.kinds == LAKE])
    water = np.empty((height, width, 3), dtype=np.uint8)
    land = np.empty((height, width, 3), dtype=np.uint8)
    shade = np.empty((height, width), dtype=np.uint8)
    for start in range(0, height, BAND):
        rows = slice(start, min(height, start + BAND))
        is_lake = lakes[labels[rows]][..., None]
        water[rows] = np.clip(
            np.where(is_lake, _band(lake, rows, width), _band(sea, rows, width)) + 0.5, 0, 255
        ).astype(np.uint8)
        land[rows] = np.clip(_band(field.land, rows, width) + 0.5, 0, 255).astype(np.uint8)
        shade[rows] = np.clip(_band(field.shade, rows, width) * 128 + 0.5, 0, 255).astype(np.uint8)
    found = Ground(water=water, land=land, shade=shade)
    while len(_GROUNDS) >= KEPT_GROUNDS:
        del _GROUNDS[next(iter(_GROUNDS))]
    _GROUNDS[id(atlas)] = (atlas, found)
    return found


def picture(
    atlas: Atlas,
    lens: StyledLens,
    *,
    tribes: bool,
    overlays: Overlays | None = None,
    isolated: Iterable[int] | None = None,
) -> NDArray[np.uint8]:
    """The map of ``lens``: height x width x 3, one pixel per atlas pixel, drawn in bands of
    rows so that its memory stays small. ``isolated`` locations keep their colours and are
    outlined; the rest fades (``isolate``)."""
    look = profile(lens.layer)
    physical = ground(atlas)
    height, width = atlas.size
    labels = atlas.labels.astype(np.int64) - 1
    ink_share, foam = lines(atlas, lens, tribes=tribes, overlays=overlays or Overlays())
    kinds_of = atlas.kinds.astype(np.int64)
    own_colours = lens.colours.astype(np.float32)
    cover_of = lens.opacity.astype(np.float32) / 255
    ink = np.array(INK, np.float32) * 255
    foam_colour = np.array(FOAM, np.float32) * 255
    weights = np.array([0.299, 0.587, 0.114], np.float32)
    out = np.empty((height, width, 3), dtype=np.uint8)
    for start in range(0, height, BAND):
        rows = slice(start, min(height, start + BAND))
        band = labels[rows]
        cell = np.maximum(band, 0)
        kinds = np.where(band >= 0, kinds_of[cell], SEA)
        solid = ((kinds == LAND) | (kinds == WASTELAND))[..., None]
        soil = physical.land[rows].astype(np.float32)
        if not look.physical:
            cover = cover_of[cell][..., None]
            grey = (soil @ weights)[..., None]
            faded = (
                soil + (grey * np.array([1.02, 1.0, 0.94], np.float32) - soil) * 0.62
            ) * 0.93 + 10
            soil = np.where(cover > SOME_COVER, soil + (own_colours[cell] - soil) * cover, faded)
        lit = 1 + (physical.shade[rows].astype(np.float32) / 128 - 1) * look.shade
        rgb = np.where(solid, soil * lit[..., None], physical.water[rows].astype(np.float32))
        rgb = rgb + (ink - rgb) * ink_share[rows][..., None]
        rgb = np.where(foam[rows][..., None], rgb + (foam_colour - rgb) * 0.13, rgb)
        out[rows] = np.clip(rgb + 0.5, 0, 255).astype(np.uint8)
    return out if isolated is None else isolate(atlas, out, isolated)


def isolate(atlas: Atlas, drawn: NDArray[np.uint8], cells: Iterable[int]) -> NDArray[np.uint8]:
    """``drawn`` with only ``cells`` in their colours, outlined; the rest fades."""
    height, width = atlas.size
    labels = atlas.labels.astype(np.int64) - 1
    match = np.zeros(atlas.cells + 1, dtype=bool)
    chosen = np.fromiter(cells, dtype=np.int64)
    match[chosen[(chosen >= 0) & (chosen < atlas.cells)]] = True
    matched = match[np.where(labels >= 0, labels, atlas.cells)]
    outline = np.zeros((height, width), dtype=bool)
    for here, there in _NEIGHBOURS:
        outline[here] |= matched[here] & ~matched[there]
    accent = np.array(ACCENT, np.float32) * 255
    weights = np.array([0.299, 0.587, 0.114], np.float32)
    out = np.empty_like(drawn)
    for start in range(0, height, BAND):
        rows = slice(start, min(height, start + BAND))
        rgb = drawn[rows].astype(np.float32)
        grey = (rgb @ weights)[..., None]
        rgb = np.where(matched[rows][..., None], rgb, (rgb + (grey - rgb) * 0.7) * 0.42)
        rgb = np.where(outline[rows][..., None], rgb + (accent - rgb) * 0.95, rgb)
        out[rows] = np.clip(rgb + 0.5, 0, 255).astype(np.uint8)
    return out


# -- what is written and marked -----------------------------------------------------------------

LabelKind = Literal["country", "tribe", "class", "region", "sea"]


@dataclass(frozen=True, slots=True)
class Label:
    """A name written large: where (atlas pixels), how much it names (pixels), how far its point
    lies from the edge of what it names (pixels) and what kind of name it is."""

    text: str
    x: float
    y: float
    weight: float
    room: float
    kind: LabelKind


@dataclass(frozen=True, slots=True)
class Place:
    """A mark on the map: a city or town, a capital, or riches."""

    cell: int
    x: float
    y: float
    kind: Literal["city", "town", "capital", "riches"]
    name: str
    colour: RGB = (0, 0, 0)


def poles(
    atlas: Atlas, class_of: NDArray[np.int64], classes: int
) -> list[tuple[float, float, float, float]]:
    """For each class, the point deepest inside it (x, y), how deep (atlas pixels) and how many
    pixels it has; a class's deepest point lies in its largest, roundest part. Worked out at the
    physical map's resolution."""
    labels = atlas.labels.astype(np.int64) - 1
    sample = labels[1::STEP, 1::STEP] if min(atlas.size) > 1 else labels
    pixel = np.where(
        sample >= 0,
        np.concatenate([class_of, [-1]])[np.where(sample >= 0, sample, len(class_of))],
        -1,
    )
    edge = pixel < 0
    padded = np.pad(pixel, 1, mode="constant", constant_values=-1)
    centre = padded[1:-1, 1:-1]
    for neighbour in (padded[:-2, 1:-1], padded[2:, 1:-1], padded[1:-1, :-2], padded[1:-1, 2:]):
        edge |= neighbour != centre
    depth = euclidean_distance(edge, 8 * 4096).astype(np.float64) / 8
    flat = pixel.ravel()
    valid = np.flatnonzero(flat >= 0)
    out: list[tuple[float, float, float, float]] = [(0.0, 0.0, -1.0, 0.0)] * classes
    if not valid.size:
        return out
    owners = flat[valid]
    deep = depth.ravel()[valid]
    order = np.lexsort((-deep, owners))
    first = np.ones(order.size, dtype=bool)
    first[1:] = owners[order][1:] != owners[order][:-1]
    counts = np.bincount(owners, minlength=classes)
    width = pixel.shape[1]
    for position in order[first]:
        index = int(valid[position])
        k = int(flat[index])
        if 0 <= k < classes:
            row, column = divmod(index, width)
            out[k] = (
                (column + 0.5) * STEP,
                (row + 0.5) * STEP,
                float(depth.ravel()[index]) * STEP,
                float(counts[k]) * STEP * STEP,
            )
    return out


def _country_names(atlas: Atlas, words: Words, *, tribes: bool) -> list[Label]:
    kinds = atlas.kinds.astype(np.int64)
    owner = atlas.owner.astype(np.int64)
    states = np.array([country.kind == "state" for country in atlas.countries] + [False])
    shown = (kinds == LAND) & (owner >= 0) & (tribes | states[np.where(owner >= 0, owner, -1)])
    found: list[Label] = []
    for k, (x, y, room, area) in enumerate(
        poles(atlas, np.where(shown, owner, -1), len(atlas.countries))
    ):
        if area > 0:
            country = atlas.countries[k]
            written = words.name(country.name) if country.name else country.tag
            kind: LabelKind = "country" if country.kind == "state" else "tribe"
            found.append(Label(written, x, y, area, room, kind))
    return found


def _region_names(atlas: Atlas, words: Words) -> list[Label]:
    kinds = atlas.kinds.astype(np.int64)
    found: list[Label] = []
    for wanted, kind in (((LAND, WASTELAND), "region"), ((SEA,), "sea")):
        titles: dict[str, int] = {}
        class_of = np.full(atlas.cells, -1, dtype=np.int64)
        for cell in np.flatnonzero(np.isin(kinds, wanted)):
            source = atlas.regions[cell] if kind == "region" else atlas.names[cell]
            title = written(source, words)
            if title:
                class_of[cell] = titles.setdefault(title, len(titles))
        ordered = list(titles)
        for k, (x, y, room, area) in enumerate(poles(atlas, class_of, len(ordered))):
            if area > 0:
                found.append(Label(ordered[k], x, y, area, room, cast("LabelKind", kind)))
    return found


def names(atlas: Atlas, lens: StyledLens, words: Words, *, tribes: bool) -> list[Label]:
    """The names ``lens`` writes large, largest first."""
    look = profile(lens.layer)
    found: list[Label] = []
    if look.names == "countries":
        found = _country_names(atlas, words, tribes=tribes)
    elif look.names == "classes":
        own = np.where((atlas.kinds == LAND) & (lens.opacity > 0), lens.classes, -1)
        for k, (x, y, room, area) in enumerate(
            poles(atlas, own.astype(np.int64), len(lens.legend))
        ):
            if area > 0:
                found.append(Label(lens.legend[k][0], x, y, area, room, "class"))
    elif look.names == "regions":
        found = _region_names(atlas, words)
    found.sort(key=lambda label: -label.weight)
    return found


def written(value: object, words: Words) -> str:
    """A name of the atlas as the window writes it: a generated name in its language, an
    identifier of the game (a region, an area, a ``$key$`` sea) by the game's name for it."""
    if isinstance(value, str):
        key = value.strip("$")
        return words.key(key) if key != value or ("_" in key and " " not in key) else value
    return words.name(value) if value else ""  # pyright: ignore[reportArgumentType]


def identifiers(atlas: Atlas) -> frozenset[str]:
    """The game's identifiers among the atlas's names, regions and areas: what ``written``
    asks the game to name."""
    found = {word for words in atlas.vocabulary.values() for word in words}
    for value in (*atlas.regions, *atlas.areas, *atlas.names):
        if isinstance(value, str) and value:
            key = value.strip("$")
            if key != value or ("_" in key and " " not in key):
                found.add(key)
    return frozenset(found)


def centres(atlas: Atlas) -> NDArray[np.float64]:
    """Each location's centre in atlas pixels (x, y): the mean of its pixels."""
    labels = atlas.labels.ravel().astype(np.int64)
    width = atlas.size[1]
    index = np.arange(labels.size, dtype=np.int64)
    count = np.bincount(labels, minlength=atlas.cells + 1)[1:].astype(np.float64)
    x = np.bincount(labels, weights=(index % width) + 0.5, minlength=atlas.cells + 1)[1:]
    y = np.bincount(labels, weights=(index // width) + 0.5, minlength=atlas.cells + 1)[1:]
    count = np.maximum(count, 1)
    return np.stack([x / count, y / count], axis=1)


def places(atlas: Atlas, layer: str, words: Words, *, tribes: bool) -> list[Place]:
    """What ``layer`` marks: cities and towns on the physical and political maps, capitals on
    the political one, riches on the resources lens."""
    found: list[Place] = []
    middle = centres(atlas)
    land = atlas.kinds == LAND
    if layer in {"land", "countries"}:
        for cell in np.flatnonzero(land & (atlas.settlement >= 0)):
            word = atlas.word("settlement", int(atlas.settlement[cell]))
            name = written(atlas.names[int(cell)], words) or atlas.keys[int(cell)]
            x, y = middle[cell]
            found.append(
                Place(int(cell), float(x), float(y), "city" if word == "city" else "town", name)
            )
    if layer == "countries":
        for country in atlas.countries:
            if country.capital >= 0 and (tribes or country.kind == "state"):
                x, y = middle[country.capital]
                title = words.name(country.name) if country.name else country.tag
                found.append(Place(country.capital, float(x), float(y), "capital", title))
    if layer == "resources":
        for cell in np.flatnonzero(land & (atlas.material >= 0)):
            material = atlas.word("material", int(atlas.material[cell]))
            if material in PRECIOUS:
                x, y = middle[cell]
                found.append(
                    Place(
                        int(cell),
                        float(x),
                        float(y),
                        "riches",
                        words.key(material),
                        PRECIOUS[material],
                    )
                )
    return found


def spot(atlas: Atlas, layer: str, cell: int, words: Words) -> str:
    """What ``layer`` writes in location ``cell`` seen up close; empty for nothing."""
    look = profile(layer)
    if look.spots is None or int(atlas.kinds[cell]) != LAND:
        return ""
    if look.spots == "resource":
        material = atlas.word("material", int(atlas.material[cell]))
        return words.key(material) if material else ""
    if int(atlas.population[cell]) <= 0:
        return ""
    if look.spots == "population":
        return grouped(int(atlas.population[cell]))
    return str(int(atlas.complexity[cell]))
