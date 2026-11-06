"""N5: choose American land keys by place and physical similarity, before writing identities.

A region key goes to the generated part that lies where the key lies in its vanilla
subcontinent, and among parts in comparable places to the one most like the key's installed
land. An area key goes to the part most like its land, and place breaks ties. Places are
compared as standardized point clouds: every vanilla key and every generated part is one
point, measured from its cloud's mean in its cloud's standard deviations on each axis, so a
tall generated continent still has its west coast in the west and its Alaska in the
north-west, whatever the sizes of the parts. Only compact per-location tables and the biome
model's existing contact pairs are read. No peoples, resources, random stream or extra
raster pass enters the matching. Regions compete within their subcontinent; areas within
their original region, preserving the installed parent tree. Sea areas retain the shore
and remainder rules of eu5_newworld.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final, cast

from rnw.eu5_canvas import NEW_WORLD
from rnw.model import CellClass
from rnw.progress import checkpoint

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from rnw.eu5_biomes import CellBiomes
    from rnw.eu5_map import Eu5Map
    from rnw.geography import Location
    from rnw.newworld import NewWorld

PERMILLE: Final[int] = 1000
LAND: Final[frozenset[CellClass]] = frozenset({CellClass.LAND, CellClass.WASTELAND, CellClass.LAKE})
WEIGHTS: Final[tuple[int, ...]] = (4, 3, 2, 1)
# Regions: one standard deviation of displacement (1000 permille) costs 8000, twice a complete
# climate mismatch (4 x 1000), so place decides and physical similarity chooses among parts in
# comparable places. On four captured worlds every region key was the same for weights 8 to
# 16; 2 and 4 changed one subcontinent of one world. Areas: their layout inside a region is
# seen nowhere (the world names them) while scripts read their land, so physical similarity
# decides and place only breaks ties; weight 8 there cost a third more physical difference
# (2026-11-06, docs/research/n5-region-keys.md).
REGION_PLACE_WEIGHT: Final[int] = 8
AREA_PLACE_WEIGHT: Final[int] = 0
TOPOGRAPHY: Final[dict[str, str]] = {
    "mountain_wasteland": "mountains",
    "mesa_wasteland": "plateau",
    "high_lakes": "lakes",
}


class RegionKeyError(ValueError):
    """A physical template or a complete one-to-one key assignment is missing."""


@dataclass(frozen=True, slots=True)
class Trait:
    """The physical template of one location, weighted by its pixel area."""

    climate: str
    topography: str
    pixels: int
    coastal: bool

    def __post_init__(self) -> None:
        if not self.climate or not self.topography or self.pixels <= 0:
            message = f"Incomplete physical template: {self}"
            raise RegionKeyError(message)


@dataclass(frozen=True, slots=True)
class Profile:
    """Pixel-weighted climate, relief, coastal share and size of one part."""

    climate: dict[str, int]
    topography: dict[str, int]
    coast: int
    pixels: int

    def summary(self) -> dict[str, object]:
        """Small, inspectable evidence; no game text or raster is retained."""
        return {
            "climate": self.climate,
            "topography": self.topography,
            "coast_permille": self.coast,
            "pixels": self.pixels,
        }


def profile(traits: Iterable[Trait]) -> Profile:
    """Aggregate physical shares in integers, independent of location order."""
    climate: Counter[str] = Counter()
    topography: Counter[str] = Counter()
    pixels = coast = 0
    for trait in traits:
        pixels += trait.pixels
        coast += trait.pixels * trait.coastal
        climate[trait.climate] += trait.pixels
        relief = TOPOGRAPHY.get(trait.topography, trait.topography.removesuffix("_wasteland"))
        topography[relief] += trait.pixels
    if not pixels:
        message = "An empty part has no physical profile"
        raise RegionKeyError(message)
    return Profile(
        {name: weight * PERMILLE // pixels for name, weight in sorted(climate.items())},
        {name: weight * PERMILLE // pixels for name, weight in sorted(topography.items())},
        coast * PERMILLE // pixels,
        pixels,
    )


def _difference(first: dict[str, int], second: dict[str, int]) -> int:
    return sum(abs(first.get(key, 0) - second.get(key, 0)) for key in first.keys() | second) // 2


def frame(points: Sequence[tuple[int, int]]) -> tuple[tuple[int, int], tuple[int, int]]:
    """The (row, column) mean of a nonempty point cloud and its standard deviation on each
    axis, in integers (at least 1), so the result is the same on every machine."""
    if not points:
        message = "An empty point cloud has no frame"
        raise RegionKeyError(message)

    def axis(values: list[int]) -> tuple[int, int]:
        mean = sum(values) // len(values)
        return mean, max(1, math.isqrt(sum((v - mean) ** 2 for v in values) // len(values)))

    (mean_row, spread_row) = axis([row for row, _ in points])
    (mean_column, spread_column) = axis([column for _, column in points])
    return (mean_row, mean_column), (spread_row, spread_column)


def standard(points: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    """Each (row, column) point in permille of its cloud's standard deviation from its mean;
    an axis without spread puts every point at zero on it."""
    if not points:
        return []
    (mean_row, mean_column), (spread_row, spread_column) = frame(points)
    return [
        (
            (row - mean_row) * PERMILLE // spread_row,
            (column - mean_column) * PERMILLE // spread_column,
        )
        for row, column in points
    ]


def unstandard(point: tuple[int, int], points: Sequence[tuple[int, int]]) -> tuple[int, int]:
    """The standardized ``point`` placed in the frame of the cloud ``points``."""
    (mean_row, mean_column), (spread_row, spread_column) = frame(points)
    return (
        mean_row + point[0] * spread_row // PERMILLE,
        mean_column + point[1] * spread_column // PERMILLE,
    )


def place_distance(first: tuple[int, int], second: tuple[int, int]) -> int:
    """The distance of two standardized points, in permille of a standard deviation."""
    return math.isqrt((first[0] - second[0]) ** 2 + (first[1] - second[1]) ** 2)


def distance(first: Profile, second: Profile, totals: tuple[int, int]) -> tuple[int, ...]:
    """Four differences in permille: climate, relief, coast, parent-relative size."""
    return (
        _difference(first.climate, second.climate),
        _difference(first.topography, second.topography),
        abs(first.coast - second.coast),
        abs(first.pixels * PERMILLE // totals[0] - second.pixels * PERMILLE // totals[1]),
    )


def minimum_assignment(  # noqa: C901, PLR0912 - one Hungarian augmenting-path search.
    costs: Sequence[Sequence[int]],
) -> list[int]:
    """Exact rectangular Hungarian assignment: one distinct column per row.

    Integer potentials and ascending row/column tie breaks are portable. Rows are
    vanilla keys (sorted); columns are generated parts in their stable partition order.
    The algorithm is implemented here, with no new numerical dependency.
    """
    count = len(costs)
    width = len(costs[0]) if count else 0
    if width < count or any(len(row) != width for row in costs):
        message = "Key assignment needs a rectangular matrix with at least one part per key"
        raise RegionKeyError(message)
    row_potential, column_potential = [0] * (count + 1), [0] * (width + 1)
    holder, previous = [0] * (width + 1), [0] * (width + 1)
    for row in range(1, count + 1):
        checkpoint()
        holder[0] = row
        column = 0
        gaps: list[int | None] = [None] * (width + 1)
        used = [False] * (width + 1)
        while True:
            used[column] = True
            current = holder[column]
            step: int | None = None
            next_column = 0
            for candidate in range(1, width + 1):
                if used[candidate]:
                    continue
                gap = costs[current - 1][candidate - 1] - row_potential[current]
                gap -= column_potential[candidate]
                old = gaps[candidate]
                if old is None or gap < old:
                    gaps[candidate] = gap
                    previous[candidate] = column
                best = gaps[candidate]
                if best is not None and (step is None or best < step):
                    step, next_column = best, candidate
            if step is None:
                message = "Key assignment has no augmenting path"
                raise RegionKeyError(message)
            for candidate in range(width + 1):
                if used[candidate]:
                    row_potential[holder[candidate]] += step
                    column_potential[candidate] -= step
                else:
                    gap = gaps[candidate]
                    if gap is not None:
                        gaps[candidate] = gap - step
            column = next_column
            if not holder[column]:
                break
        while column:
            prior = previous[column]
            holder[column] = holder[prior]
            column = prior
    chosen = [-1] * count
    for column in range(1, width + 1):
        if holder[column]:
            chosen[holder[column] - 1] = column - 1
    return chosen


@dataclass(slots=True)
class KeyMatcher:
    """Physical templates and the audit of keys chosen during hierarchy construction."""

    vanilla: dict[str, Profile]
    generated: dict[int, Trait]
    assignments: list[dict[str, object]] = field(default_factory=list)

    def pair(  # noqa: PLR0913 - the parts, their keys, where each lies and how much that counts.
        self,
        parts: list[list[int]],
        keys: list[str],
        *,
        centres: Sequence[tuple[int, int]],
        places: Sequence[tuple[int, int]],
        place_weight: int,
        minimum: dict[str, int] | None = None,
    ) -> list[int]:
        """Return a key index per part (-1 for extra areas), minimizing the total cost.

        ``centres`` are the parts' centres and ``places`` the vanilla keys' centres; each
        cloud is standardized on its own (``standard``). A cost is the physical difference
        plus ``place_weight`` times the distance of the two standardized points; between
        assignments of equal total cost the smaller total distance wins. Part boundaries
        are final before matching: no later balancing can invalidate the scored profile.
        """
        if not keys or keys != sorted(set(keys)):
            message = "Physical matching requires nonempty, sorted, unique vanilla keys"
            raise RegionKeyError(message)
        if len(centres) != len(parts) or len(places) != len(keys):
            message = "Every part needs a centre and every vanilla key a place"
            raise RegionKeyError(message)
        missing = set(keys) - self.vanilla.keys()
        if missing:
            message = f"No physical template for vanilla keys {sorted(missing)}"
            raise RegionKeyError(message)
        targets = [self.vanilla[key] for key in keys]
        found = [profile(self.generated[cell] for cell in part) for part in parts]
        totals = (sum(part.pixels for part in found), sum(part.pixels for part in targets))
        differences = [[distance(part, target, totals) for part in found] for target in targets]
        physical = [
            [sum(a * b for a, b in zip(delta, WEIGHTS, strict=True)) for delta in row]
            for row in differences
        ]
        here, there = standard(centres), standard(places)
        apart = [[place_distance(spot, point) for point in here] for spot in there]
        costs = [
            [cost + place_weight * gap for cost, gap in zip(row, gaps, strict=True)]
            for row, gaps in zip(physical, apart, strict=True)
        ]
        # The distance breaks ties: scaled past any total of distances, it cannot outweigh
        # a unit of cost.
        scale = 1 + len(keys) * max(max(row) for row in apart)
        ranked = [
            [cost * scale + gap for cost, gap in zip(row, gaps, strict=True)]
            for row, gaps in zip(costs, apart, strict=True)
        ]
        needs = minimum or dict.fromkeys(keys, 1)
        # A region must have room for every original child area. Forbid an impossible
        # placement in the same assignment, rather than repair a hierarchy afterwards.
        forbidden = 1 + sum(max(row) for row in ranked)
        chosen = minimum_assignment(
            [
                [
                    cost if len(parts[p]) >= needs[keys[k]] else forbidden
                    for p, cost in enumerate(row)
                ]
                for k, row in enumerate(ranked)
            ]
        )
        if any(len(parts[p]) < needs[keys[k]] for k, p in enumerate(chosen)):
            message = "Generated parts cannot hold every vanilla key and its child areas"
            raise RegionKeyError(message)
        pairing = [-1] * len(parts)
        for key, part in enumerate(chosen):
            pairing[part] = key
            self.assignments.append(
                {
                    "key": keys[key],
                    "cost": costs[key][part],
                    "physical_cost": physical[key][part],
                    "place_permille": apart[key][part],
                    "place_weight": place_weight,
                    "difference": list(differences[key][part]),
                    "vanilla": targets[key].summary(),
                    "generated": found[part].summary(),
                }
            )
        return pairing


def physical_keys(  # noqa: PLR0913 - the two physical models and their installed hierarchy.
    game_map: Eu5Map,
    hierarchy: dict[str, Location],
    attributes: dict[str, dict[str, str]],
    pairs: Iterable[tuple[int, int]],
    *,
    world: NewWorld,
    biomes: CellBiomes,
    pixels: Sequence[int],
) -> KeyMatcher:
    """Templates from the installed Americas and the finished, resource-free biome fields.

    Pixel counts come from existing tables. Coastal means a contact with sea (not lake).
    Lake templates have a lake relief rather than the biome model's empty land field.
    """
    vanilla_coast = _coastal(game_map.classes, pairs)
    generated_coast = _coastal(world.classes, world.edges)
    members: dict[str, list[Trait]] = {}
    for label, key in enumerate(game_map.keys):
        location = hierarchy.get(key)
        if (
            location is None
            or location.continent != NEW_WORLD
            or game_map.classes[label] not in LAND
        ):
            continue
        values = attributes.get(key, {})
        try:
            trait = Trait(
                values["climate"], values["topography"], pixels[label], label in vanilla_coast
            )
        except KeyError as error:
            message = f"Vanilla location {key} has no {error.args[0]} physical template"
            raise RegionKeyError(message) from error
        for name in (location.region, location.area):
            members.setdefault(name, []).append(trait)
    generated_pixels = cast("list[int]", world.pixels.tolist())
    generated = {
        cell: Trait(
            biomes.climate[cell],
            "lakes" if kind is CellClass.LAKE else biomes.topography[cell],
            generated_pixels[cell],
            cell in generated_coast,
        )
        for cell, kind in enumerate(world.classes)
        if kind in LAND
    }
    return KeyMatcher({key: profile(traits) for key, traits in sorted(members.items())}, generated)


def _coastal(classes: Sequence[CellClass], pairs: Iterable[tuple[int, int]]) -> set[int]:
    return {
        land
        for first, second in pairs
        for land, water in ((first, second), (second, first))
        if classes[land] in LAND and classes[water] is CellClass.SEA
    }
