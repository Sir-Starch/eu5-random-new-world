"""Names for generated water: one sea, one name; bays, straits and capes as in the game's own map.

Game-independent. The game's own map names its water the way geography does: all the zones of
the Black Sea are called the Black Sea, a bay is a bay, a strait a strait, a cape a cape, and a
coast the coast of some land [V-LOCAL 1.4.3, C234]. The first generated worlds called every sea
cell ``<random word> Sea``, so a single gulf of forty cells had forty names. Here a name belongs
to a stretch of water that ``seas.analyse`` found:

* a narrow **passage** is a strait, a channel or a sound;
* an enclosed **body** is a sea, a gulf or a bay by its size, and its cells are one name (a sea's
  coastal cells keep the coast's names below);
* a coastal cell is a cape, a bay, the water of an island or a plain coast, each connected group
  of one kind within one province being one named place;
* a zone of impassable ocean in coastal water is an ocean of its own, as the game's great zones
  are named after the ocean they fill;
* every other cell takes the name of its area, as the open zones of the game's ocean areas do
  (an area of the game's own oceans keeps the game's name, referred to by its key so that every
  language shows its own; an area of coastal water is a sea, a coast or an ocean by what it
  holds, or the sea that fills most of it).

A province is named after the name most of its cells share, or after its area. Names are
phrases (``wording.Phrase``): a kind of water, a word and, for a part of a body, its compass
points; each of the game's languages writes them by its own grammar when the files are written
(roadmap L1).
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from rnw import wording
from rnw.names import NameGenerator
from rnw.seas import DEEP_HOPS, PassageKind, Shape, Topography
from rnw.wording import Name, Phrase

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from rnw.newworld import NewWorld
    from rnw.seas import Waters

SHARED: Final[int] = 2
# Bodies of at least this many cells are seas, of at least ``GULF_CELLS`` gulfs, others bays.
SEA_CELLS: Final[int] = 24
GULF_CELLS: Final[int] = 6
# An area is named for the body that holds at least this share (permille) of its cells.
BODY_PERMILLE: Final[int] = 500
# A coastal-water area with this share of coastal cells is a coast; with this share of deep
# ocean, an ocean; otherwise a sea.
COAST_PERMILLE: Final[int] = 400
OCEAN_PERMILLE: Final[int] = 700
PERMILLE: Final[int] = 1000
# An island group of this many islands is an archipelago, of more than one a set of islands.
ARCHIPELAGO_ISLANDS: Final[int] = 4
# The slope of the edge between a sector of the compass and the next, tan 22.5 degrees, in 1/1000.
AXIS_SLOPE: Final[int] = 414
AXIS_SCALE: Final[int] = 1000


class Kind(StrEnum):
    """A kind of named water; ``wording`` holds its words in every language."""

    SEA = "sea"
    OCEAN = "ocean"
    GULF = "gulf"
    BAY = "bay"
    STRAIT = "strait"
    CHANNEL = "channel"
    SOUND = "sound"
    COAST = "coast"
    CAPE = "cape"
    ISLAND = "island"
    ISLANDS = "islands"
    ARCHIPELAGO = "archipelago"


# Eight points of the compass (east first, then counter-clockwise), then the middle of a body.
SECTORS: Final[tuple[str, ...]] = wording.SECTORS
CENTRAL: Final[str] = wording.CENTRAL
FAR: Final[str] = wording.FAR
PASSAGES: Final[dict[PassageKind, Kind]] = {
    PassageKind.STRAIT: Kind.STRAIT,
    PassageKind.CHANNEL: Kind.CHANNEL,
    PassageKind.INLET: Kind.SOUND,
}
FEATURES: Final[dict[int, Kind]] = {
    Shape.COAST: Kind.COAST,
    Shape.CAPE: Kind.CAPE,
    Shape.BAY: Kind.BAY,
}


@dataclass(frozen=True, slots=True)
class Placement:
    """Where a sea cell stands in the hierarchy: its province and area, and whether the area is
    one of the game's own ocean areas (named by the game, in every language)."""

    province: str
    area: str
    ocean: bool


@dataclass(frozen=True, slots=True)
class SeaNames:
    """Names of the cells, provinces and areas of generated water, keyed by cell number and key.

    A name may be the game's own text under a key (``wording.reference``).
    """

    cells: dict[int, Name]
    provinces: dict[str, Name]
    areas: dict[str, Name]


def reference(key: str) -> Phrase:
    """The name that shows another key's text, in whichever language the game is in."""
    return wording.reference(key)


def _name(kind: Kind, word: str) -> Phrase:
    return Phrase(kind.value, word)


def _neighbours(world: NewWorld) -> list[list[int]]:
    found: list[list[int]] = [[] for _ in world.classes]
    for first, second in world.edges:
        found[first].append(second)
        found[second].append(first)
    return [sorted(others) for others in found]


def _groups(
    cells: Sequence[int], key: Mapping[int, object], links: Mapping[int, Sequence[int]]
) -> list[list[int]]:
    """Connected groups of ``cells`` that share a ``key``, in order of their lowest cell."""
    inside = set(cells)
    seen: set[int] = set()
    groups: list[list[int]] = []
    for start in sorted(inside):
        if start in seen:
            continue
        seen.add(start)
        group, stack = [start], [start]
        while stack:
            for other in links[stack.pop()]:
                if other in inside and other not in seen and key[other] == key[start]:
                    seen.add(other)
                    group.append(other)
                    stack.append(other)
        groups.append(sorted(group))
    return groups


def _body_kind(size: int) -> Kind:
    if size >= SEA_CELLS:
        return Kind.SEA
    return Kind.GULF if size >= GULF_CELLS else Kind.BAY


def _sector(rows: int, columns: int) -> int:
    """The compass sector of an offset (rows grow southwards): 0 east, then counter-clockwise.

    Integer arithmetic only: a sector is 45 degrees wide and an axis is within tan 22.5 (0.414).
    """
    east, north = columns, -rows
    wide, high = abs(east), abs(north)
    if high * AXIS_SCALE <= wide * AXIS_SLOPE:
        return 0 if east >= 0 else 4
    if wide * AXIS_SCALE <= high * AXIS_SLOPE:
        return 2 if north >= 0 else 6
    if east >= 0:
        return 1 if north >= 0 else 7
    return 3 if north >= 0 else 5


def name_waters(
    world: NewWorld,
    waters: Waters,
    placed: Sequence[Placement | None],
    *,
    seed: int,
) -> SeaNames:
    """Names for every sea cell, and for the provinces and areas of coastal water."""
    sea = set(waters.sea())
    neighbours = _neighbours(world)
    links = {cell: [other for other in neighbours[cell] if other in sea] for cell in sorted(sea)}
    words = NameGenerator(seed, "seas")
    names: dict[int, Name] = {}
    for passage in waters.passages:
        text = _name(PASSAGES[passage.kind], words.next())
        names.update(dict.fromkeys(passage.cells, text))
    body_text: dict[int, Phrase] = {}
    for index, cells in enumerate(waters.bodies):
        kind = _body_kind(len(cells))
        body_text[index] = _name(kind, words.next())
        for cell in cells:
            if cell not in names and (kind is not Kind.SEA or waters.hop[cell] > 0):
                names[cell] = body_text[index]
    _name_coasts(waters, placed, (neighbours, links), words, names)
    area_text = _name_areas(world, waters, placed, body_text, words)
    for cell in sorted(sea):
        placement = placed[cell]
        if placement is None:  # pragma: no cover - every sea cell is placed
            message = f"Sea cell {cell} has no province or area"
            raise ValueError(message)
        if (
            cell not in names
            and waters.topography[cell] is Topography.OCEAN_WASTELAND
            and not placement.ocean
        ):
            names[cell] = _name(Kind.OCEAN, words.next())
        _ = names.setdefault(cell, area_text[placement.area])
    provinces = _name_provinces(sea, placed, names, area_text)
    return SeaNames(names, provinces, _own_areas(area_text, placed))


def _name_coasts(
    waters: Waters,
    placed: Sequence[Placement | None],
    graph: tuple[Sequence[Sequence[int]], Mapping[int, Sequence[int]]],
    words: NameGenerator,
    names: dict[int, Name],
) -> None:
    """Capes, bays, coasts and island waters: one name for each group.

    A group of capes, bays or coast is a connected run of one kind in one province; the water of
    a small island, which the cells round it reach only by their corners, is one place with the
    island's name whatever provinces it crosses.
    """
    neighbours, links = graph
    shore = [
        cell
        for cell in sorted(links)
        if waters.hop[cell] == 0 and cell not in names and waters.shape[cell] != Shape.OPEN
    ]
    islands: dict[tuple[int, ...], list[int]] = {}
    key: dict[int, object] = {}
    for cell in shore:
        placement = placed[cell]
        assert placement is not None  # noqa: S101 - a sea cell is placed
        if waters.shape[cell] == Shape.ISLE:
            masses = {int(waters.landmass[o]) for o in neighbours[cell] if waters.landmass[o] >= 0}
            islands.setdefault(tuple(sorted(masses)), []).append(cell)
        else:
            key[cell] = (int(waters.shape[cell]), placement.province, int(waters.body[cell]))
    groups = [
        (FEATURES[int(waters.shape[group[0]])], group) for group in _groups(list(key), key, links)
    ]
    for masses, group in sorted(islands.items(), key=lambda item: item[1][0]):
        kind = Kind.ISLAND if len(masses) <= 1 else Kind.ISLANDS
        if len(masses) >= ARCHIPELAGO_ISLANDS:
            kind = Kind.ARCHIPELAGO
        groups.append((kind, group))
    for kind, group in sorted(groups, key=lambda item: item[1][0]):
        names.update(dict.fromkeys(group, _name(kind, words.next())))


def _name_areas(
    world: NewWorld,
    waters: Waters,
    placed: Sequence[Placement | None],
    body_text: Mapping[int, Phrase],
    words: NameGenerator,
) -> dict[str, Name]:
    """A text for every area of water: the game's for its oceans, ours for the coastal water."""
    cells_of: dict[str, list[int]] = {}
    ocean: dict[str, bool] = {}
    for cell in waters.sea():
        placement = placed[cell]
        assert placement is not None  # noqa: S101 - a sea cell is placed
        cells_of.setdefault(placement.area, []).append(cell)
        ocean[placement.area] = placement.ocean
    text: dict[str, Name] = {}
    dominated: dict[int, list[str]] = {}
    for area in sorted(cells_of):
        cells = cells_of[area]
        if ocean[area]:
            text[area] = reference(area)
            continue
        counts = Counter(int(waters.body[cell]) for cell in cells if waters.body[cell] >= 0)
        if counts:
            body, size = max(counts.items(), key=lambda item: (item[1], -item[0]))
            if PERMILLE * size >= BODY_PERMILLE * len(cells):
                dominated.setdefault(body, []).append(area)
                continue
        coast = sum(1 for cell in cells if waters.hop[cell] == 0)
        deep = sum(1 for cell in cells if waters.hop[cell] >= DEEP_HOPS)
        if PERMILLE * coast >= COAST_PERMILLE * len(cells):
            kind = Kind.COAST
        elif PERMILLE * deep >= OCEAN_PERMILLE * len(cells):
            kind = Kind.OCEAN
        else:
            kind = Kind.SEA
        text[area] = _name(kind, words.next())
    for body, areas in sorted(dominated.items()):
        text.update(_share_body(world, waters, body, areas, cells_of, body_text[body]))
    return text


def _share_body(  # noqa: PLR0913, PLR0917 - areas of one body are told apart by their place in it.
    world: NewWorld,
    waters: Waters,
    body: int,
    areas: Sequence[str],
    cells_of: Mapping[str, Sequence[int]],
    name: Phrase,
) -> dict[str, Name]:
    """Areas that are mostly one body: its name, and a compass point when it has several."""
    if len(areas) == 1:
        return {areas[0]: name}
    members = list(waters.bodies[body])
    centre = world.centroids[members].sum(axis=0) // len(members)
    spots: dict[str, tuple[int, int]] = {}
    for area in areas:
        inside = [cell for cell in cells_of[area] if waters.body[cell] == body]
        row, column = (
            int(value) for value in world.centroids[inside].sum(axis=0) // len(inside) - centre
        )
        spots[area] = (math.isqrt(row * row + column * column), _sector(row, column))
    texts: dict[str, Name] = {}
    taken: set[tuple[str, ...]] = set()
    nearest = min(areas, key=lambda area: (spots[area][0], area))
    for area in sorted(areas, key=lambda area: (spots[area][0], area)):
        sectors = (CENTRAL if area == nearest else SECTORS[spots[area][1]],)
        while sectors in taken:
            sectors = (FAR, *sectors)
        taken.add(sectors)
        texts[area] = replace(name, sectors=sectors)
    return texts


def _own_areas(
    area_text: Mapping[str, Name], placed: Sequence[Placement | None]
) -> dict[str, Name]:
    """The names of the areas that are not the game's ocean areas."""
    own = {placement.area for placement in placed if placement is not None and not placement.ocean}
    return {area: text for area, text in area_text.items() if area in own}


def _name_provinces(
    sea: set[int],
    placed: Sequence[Placement | None],
    names: Mapping[int, Name],
    area_text: Mapping[str, Name],
) -> dict[str, Name]:
    """A province takes the name that at least two of its cells share, else its area's."""
    cells_of: dict[str, list[int]] = {}
    for cell in sorted(sea):
        placement = placed[cell]
        assert placement is not None  # noqa: S101 - a sea cell is placed
        cells_of.setdefault(placement.province, []).append(cell)
    provinces: dict[str, Name] = {}
    for province, cells in cells_of.items():
        counts = Counter(names[cell] for cell in cells)
        shared = [
            text for text in dict.fromkeys(names[cell] for cell in cells) if counts[text] >= SHARED
        ]
        area = placed[cells[0]]
        assert area is not None  # noqa: S101 - a sea cell is placed
        provinces[province] = (
            max(shared, key=lambda text: counts[text]) if shared else area_text[area.area]
        )
    return provinces
