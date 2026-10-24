"""Make the atlas of a world from what the export holds when its peoples are founded.

The export knows, for every generated location, its identity (``Plan``), its climate, vegetation,
topography and raw material (``CellBiomes``) and what its peoples are (``NativeWorld``: owner,
culture, religion, population, society complexity, settlement). This gathers them into the
``rnw.atlas.Atlas`` the viewer draws, with the New World's box of the map at a fraction of its size
(NOT GAME VALIDATED; ADR 0010, B).
"""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.atlas import KINDS, Atlas, Country
from rnw.wording import english

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.eu5_biomes import CellBiomes
    from rnw.eu5_natives import NativeWorld
    from rnw.eu5_newworld import Plan
    from rnw.newworld import NewWorld

STEP: Final[int] = 4
# Sea farther than this many pixels of the atlas from any land is left out of the picture: the
# box shows the world and its coasts, not the outline of the canvas it was cut from.
SEA_MARGIN: Final[int] = 40
POP: Final[re.Pattern[str]] = re.compile(r"size = ([0-9.]+)\s+culture = (\S+)\s+religion = (\S+)")


def _vocabulary(values: list[str]) -> tuple[tuple[str, ...], dict[str, int]]:
    words = tuple(sorted({value for value in values if value}))
    return words, {word: index for index, word in enumerate(words)}


def _main_pop(rows: list[str]) -> tuple[str, str]:
    """The culture and religion of the largest pop of a location ('' where it has none)."""
    best, culture, religion = -1.0, "", ""
    for row in rows:
        match = POP.search(row)
        if match is not None and float(match.group(1)) > best:
            best, culture, religion = float(match.group(1)), match.group(2), match.group(3)
    return culture, religion


def grown_mask(mask: NDArray[np.bool_], radius: int) -> NDArray[np.bool_]:
    """``mask`` widened by at least ``radius`` pixels in every direction, by doubling steps."""
    grown = mask.copy()
    reach = 0
    while reach < radius:
        step = min(max(1, reach + 1), radius - reach)
        shifted = grown.copy()
        shifted[step:, :] |= grown[:-step, :]
        shifted[:-step, :] |= grown[step:, :]
        wide = shifted.copy()
        wide[:, step:] |= shifted[:, :-step]
        wide[:, :-step] |= shifted[:, step:]
        grown, reach = wide, reach + step
    return grown


def _trim(labels: NDArray[np.int32]) -> NDArray[np.int32]:
    rows, columns = np.nonzero(labels)
    if not rows.size:
        return labels
    return labels[rows.min() : rows.max() + 1, columns.min() : columns.max() + 1]


def _centres(labels: NDArray[np.int32], count: int) -> NDArray[np.int32]:
    """The middle of every location in the box, as (row, column); 0, 0 for one with no pixel."""
    flat = labels.ravel().astype(np.int64)
    rows, columns = np.divmod(np.arange(flat.size, dtype=np.int64), labels.shape[1])
    total = np.bincount(flat, minlength=count + 1)[1:]
    centre = np.zeros((count, 2), dtype=np.int32)
    for axis, index in enumerate((rows, columns)):
        sums = np.bincount(flat, weights=index.astype(np.float64), minlength=count + 1)[1:]
        centre[:, axis] = np.where(total > 0, sums // np.maximum(total, 1), 0).astype(np.int32)
    return centre


def build_atlas(  # noqa: PLR0913 - the atlas gathers what the export holds
    *,
    world: NewWorld,
    plan: Plan,
    biomes: CellBiomes,
    natives: NativeWorld,
    mask: NDArray[np.bool_],
    step: int = STEP,
    margin: int = SEA_MARGIN,
) -> Atlas:
    """The atlas of the generated New World.

    ``mask`` is the canvas in the crop's coordinates; ``world.labels`` is in the same. The box is
    the canvas at ``1/step`` of the map's size, trimmed to where it has pixels.
    """
    count = len(world.classes)
    if world.labels.shape != mask.shape:
        message = f"The labels {world.labels.shape} and the canvas {mask.shape} differ in shape"
        raise ValueError(message)
    shrunk = np.where(mask[::step, ::step], world.labels[::step, ::step] + 1, 0).astype(np.int32)
    kind_of = {name: number for number, name in enumerate(KINDS)}
    kinds = np.array([kind_of.get(kind.value, 0) for kind in world.classes], dtype=np.uint8)
    solid = np.concatenate([np.array([False]), kinds != KINDS.index("sea")])[shrunk]
    labels = _trim(np.where(grown_mask(solid, margin), shrunk, 0).astype(np.int32))
    keys = tuple(cell.key for cell in plan.cells)
    names = tuple(
        english(natives.names.get(cell.key) or plan.display_overrides.get(cell.key) or cell.name)
        for cell in plan.cells
    )
    areas = tuple(english(natives.names.get(cell.area, cell.area)) for cell in plan.cells)
    regions = tuple(english(natives.names.get(cell.region, cell.region)) for cell in plan.cells)
    index_of = {key: number for number, key in enumerate(keys)}
    pops = [_main_pop(natives.pops.get(key, [])) for key in keys]
    cultures, culture_of = _vocabulary([culture for culture, _ in pops])
    religions, religion_of = _vocabulary([religion for _, religion in pops])
    materials, material_of = _vocabulary(list(biomes.raw_material))
    climates, climate_of = _vocabulary(list(biomes.climate))
    vegetations, vegetation_of = _vocabulary(list(biomes.vegetation))
    topographies, topography_of = _vocabulary(list(biomes.topography))
    ranks = {key: rank[0] for key, rank in natives.ranks.items()}
    settlements, settlement_of = _vocabulary(list(ranks.values()))

    def column(values: list[str], table: dict[str, int]) -> NDArray[np.int32]:
        return np.array([table.get(value, -1) for value in values], dtype=np.int32)

    owner = np.full(count, -1, dtype=np.int32)
    countries: list[Country] = []
    for number, country in enumerate(natives.countries):
        for member in country.members:
            if member in index_of:
                owner[index_of[member]] = number
        culture, religion = (
            culture_of.get(country.culture, -1),
            religion_of.get(country.religion, -1),
        )
        countries.append(
            Country(
                tag=country.tag,
                name=country.name,
                kind=country.kind,
                color=country.color,
                capital=index_of.get(country.capital, -1),
                culture=culture,
                religion=religion,
                locations=len(country.members),
            )
        )
    population = np.array([natives.population.get(key, 0) for key in keys], dtype=np.int64)
    complexity = np.array([natives.complexity.get(key, 0) for key in keys], dtype=np.int64)
    return Atlas(
        scale=step,
        labels=labels,
        keys=keys,
        names=names,
        kinds=kinds,
        areas=areas,
        regions=regions,
        owner=owner,
        culture=column([culture for culture, _ in pops], culture_of),
        religion=column([religion for _, religion in pops], religion_of),
        material=column(list(biomes.raw_material), material_of),
        climate=column(list(biomes.climate), climate_of),
        vegetation=column(list(biomes.vegetation), vegetation_of),
        topography=column(list(biomes.topography), topography_of),
        settlement=column([ranks.get(key, "") for key in keys], settlement_of),
        population=population,
        complexity=complexity,
        centre=_centres(labels, count),
        countries=tuple(countries),
        vocabulary={
            "culture": cultures,
            "religion": religions,
            "material": materials,
            "climate": climates,
            "vegetation": vegetations,
            "topography": topographies,
            "settlement": settlements,
        },
    )
