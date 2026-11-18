"""Shared ownership plan for the geography of a world with selected continents."""

# NumPy stubs type boolean indexing and reductions as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.eu5_canvas import NEW_WORLD, CanvasError, roll_for, select_canvas
from rnw.model import CellClass
from rnw.progress import checkpoint
from rnw.settings import PRESETS, NewWorldSettings
from rnw.topology import distance_from, label_components
from rnw.watersheds import DENSITY_STEP

if TYPE_CHECKING:
    from collections.abc import Mapping

    from numpy.typing import NDArray

    from rnw.eu5_canvas import Canvas
    from rnw.eu5_map import Eu5Map

REFERENCE_WIDTH: Final[int] = 16_384
BAND_ROWS: Final[int] = 256
RETAINED_SHORE_PX: Final[int] = 160
CONTINENTAL_SHORE_AREA_PX: Final[int] = 131_072


@dataclass(frozen=True, slots=True)
class Continent:
    key: str
    preset: str
    ocean_band_px: int | None = None
    land_neighbor: str | None = None
    island_band_px: int = 224

    def geography(self, preset: str | None = None) -> NewWorldSettings:
        """A supported preset expressed at this continent's shore scale."""
        name = self.preset if preset is None else preset
        if name not in PRESETS:
            message = f"Unknown land preset {name}"
            raise CanvasError(message)
        settings = PRESETS[name].new_world
        _validate_geography(self, settings)
        if self.ocean_band_px is None:
            return settings
        return replace(settings, ocean_band_px=self.ocean_band_px, expand_oceans=0)


CONTINENTS: Final[Mapping[str, Continent]] = MappingProxyType(
    {
        region.key: region
        for region in (
            Continent(NEW_WORLD, "continents"),
            Continent("africa", "supercontinent", ocean_band_px=820, land_neighbor="asia"),
            Continent("oceania", "archipelago", ocean_band_px=560),
        )
    }
)


def _validate_geography(continent: Continent, settings: NewWorldSettings) -> None:
    if continent.key != NEW_WORLD and (
        settings.landform or settings.template_permille or settings.keep_geography
    ):
        message = "The Wall, Omerika and keeping vanilla geography are American options"
        raise CanvasError(message)


@dataclass(frozen=True, slots=True, eq=False)
class Domain:
    """A wrapped window with exclusive replacement pixels in its part of the map."""

    continent: Continent
    first_column: int
    map_width: int
    mask: NDArray[np.bool_]
    footprint: NDArray[np.bool_]
    first_row: int = 0
    # Local pixels where generated land can meet passable retained terrain.
    land_interface: NDArray[np.bool_] | None = None
    # Dry land of the eligible retained neighbor throughout the regional window.
    contact_land: NDArray[np.bool_] | None = None
    legacy_canvas: Canvas | None = None

    def spans(self) -> tuple[tuple[slice, slice], ...]:
        """Regional and world column spans in west-to-east order."""
        width = int(self.mask.shape[1])
        first = min(width, self.map_width - self.first_column)
        initial = (slice(0, first), slice(self.first_column, self.first_column + first))
        if first == width:
            return (initial,)
        return (initial, (slice(first, width), slice(0, width - first)))

    @property
    def rows(self) -> slice:
        return slice(self.first_row, self.first_row + self.mask.shape[0])

    @property
    def seam(self) -> int | None:
        """Local column of the global wrap, when it lies inside the strip."""
        column = self.map_width - self.first_column
        return column if column < self.mask.shape[1] else None


def _membership(game_map: Eu5Map, continent: str) -> NDArray[np.bool_]:
    return np.fromiter((name == continent for name in game_map.continents), dtype=bool)


def _legacy_domain(game_map: Eu5Map, settings: NewWorldSettings) -> Domain:
    canvas = select_canvas(
        game_map,
        settings.ocean_band_px,
        expanded=bool(settings.expand_oceans or settings.landform),
    )
    if canvas.template is None:
        message = "The American canvas has no vanilla footprint"
        raise CanvasError(message)
    return Domain(
        CONTINENTS[NEW_WORLD],
        int(canvas.world_column(0)),
        int(game_map.labels.shape[1]),
        canvas.mask,
        canvas.template,
        legacy_canvas=canvas,
    )


def _extent(used: NDArray[np.bool_], reach: int) -> tuple[int, int]:
    """Find the shortest wrapped column interval with enough padding for the shore."""
    roll = roll_for(used)
    columns = np.flatnonzero(np.roll(used, roll))
    if not columns.size:
        message = "A selected continent has no land footprint"
        raise CanvasError(message)
    first = max(0, int(columns[0]) - reach)
    stop = min(used.size, int(columns[-1]) + reach + 1)
    if stop - first >= used.size:
        message = "A selected continent leaves no open cut for its geography strip"
        raise CanvasError(message)
    return (first - roll) % used.size, stop - first


def _read(labels: NDArray[np.int32], first: int, width: int) -> NDArray[np.int32]:
    """Borrow an unwrapped window or copy only the two required pieces across the seam."""
    stop = first + width
    if stop <= labels.shape[1]:
        return labels[:, first:stop]
    return np.concatenate((labels[:, first:], labels[:, : stop - labels.shape[1]]), axis=1)


def _interface(inside: NDArray[np.bool_], neighbor: NDArray[np.bool_]) -> NDArray[np.bool_]:
    """Original solid land contacts in the continuous regional window."""
    touching = np.zeros(inside.shape, dtype=bool)
    touching[1:] = neighbor[:-1]
    touching[:-1] |= neighbor[1:]
    touching[:, 1:] |= neighbor[:, :-1]
    touching[:, :-1] |= neighbor[:, 1:]
    return inside & touching


def _coastal_waters(
    footprint: NDArray[np.bool_],
    marine: NDArray[np.bool_],
    reach: int,
    island_reach: int,
    continental_area: int,
) -> NDArray[np.bool_]:
    """Use the wide coastal band around large landmasses and a local band around islands."""
    if island_reach >= reach:
        return marine & (distance_from(footprint, reach + 1, octagonal=True) <= reach)
    parts = label_components(footprint.astype(np.int32))
    sizes = np.zeros(int(parts.max()) + 1, dtype=np.int64)
    land_parts, counts = np.unique(parts[footprint], return_counts=True)
    sizes[land_parts] = counts
    shelves = (sizes >= continental_area)[parts]
    del parts
    claim = distance_from(footprint, island_reach + 1, octagonal=True) <= island_reach
    if shelves.any():
        claim |= distance_from(shelves, reach + 1, octagonal=True) <= reach
    return marine & claim


def _claim(  # noqa: PLR0913 - map, continent, settings and common ownership are independent inputs.
    game_map: Eu5Map,
    continent: Continent,
    settings: NewWorldSettings,
    occupied: NDArray[np.bool_],
    *,
    sea: NDArray[np.bool_],
    solid: NDArray[np.bool_],
) -> Domain:
    labels = game_map.labels
    map_height, map_width = labels.shape
    reach = settings.ocean_band_px * map_width // REFERENCE_WIDTH
    member = _membership(game_map, continent.key) & ~sea
    source = member[labels]
    first, width = _extent(source.any(axis=0), reach + 1)
    active_rows = np.flatnonzero(source.any(axis=1))
    del source
    # Keep the regional density grid aligned to map rows, and leave a halo past
    # the last possible sea pixel. The world rows still determine the latitude.
    top = max(0, (int(active_rows[0]) - reach - 1) // DENSITY_STEP * DENSITY_STEP)
    end = min(map_height, -(-(int(active_rows[-1]) + reach + 2) // DENSITY_STEP) * DENSITY_STEP)
    local = _read(labels[top:end], first, width)
    footprint = member[local]
    marine = sea[local]
    claim = _coastal_waters(
        footprint,
        marine,
        reach,
        continent.island_band_px * map_width // REFERENCE_WIDTH,
        max(1, CONTINENTAL_SHORE_AREA_PX * map_width**2 // REFERENCE_WIDTH**2),
    )
    # The original footprint has priority over sea claims. Keep ocean room around
    # other land, including the islands of continental shelves and adjacent Asia.
    guard = max(1, RETAINED_SHORE_PX * map_width // REFERENCE_WIDTH)
    # A halo around the window sees land just outside its edges.
    protected = solid & ~member
    low, high = max(0, top - guard), min(map_height, end + guard)
    halo_rows = slice(top - low, end - low)
    if width + 2 * guard < map_width:
        around = _read(labels[low:high], (first - guard) % map_width, width + 2 * guard)
        near = distance_from(protected[around], guard + 1, octagonal=True)[
            halo_rows, guard : guard + width
        ]
    else:
        near = _read(
            distance_from(protected[labels[low:high]], guard + 1, octagonal=True, wrap_x=True)[
                halo_rows
            ],
            first,
            width,
        )
    claim &= near > guard
    del near
    neighbor = (
        None
        if continent.land_neighbor is None
        else (_membership(game_map, continent.land_neighbor) & solid)[local]
    )
    interface = None
    if neighbor is not None:
        passable = np.fromiter((kind is CellClass.LAND for kind in game_map.classes), dtype=bool)
        interface = _interface(footprint & solid[local], neighbor & passable[local])
    domain = Domain(
        continent,
        first,
        map_width,
        footprint | claim,
        footprint,
        first_row=top,
        land_interface=interface,
        contact_land=neighbor,
    )
    for columns, original in domain.spans():
        domain.mask[:, columns] &= ~occupied[domain.rows, original]
        occupied[domain.rows, original] |= domain.mask[:, columns]
    return domain


def plan_domains(game_map: Eu5Map, selected: Mapping[str, NewWorldSettings]) -> tuple[Domain, ...]:
    """Plan selected regions once, giving new regional shores priority over wide American seas.

    Preserve the legacy canvas for America on its own. In a combined world, each region
    exclusively owns its vanilla land footprint and the unclaimed coastal water placed in its
    domain. The sea planner can later join the resulting waters using their real contacts.
    """
    if not selected or set(selected) - CONTINENTS.keys():
        message = "Choose at least one supported continent"
        raise CanvasError(message)
    for key, settings in selected.items():
        _validate_geography(CONTINENTS[key], settings)
    if tuple(selected) == (NEW_WORLD,):
        return (_legacy_domain(game_map, selected[NEW_WORLD]),)

    sea = np.fromiter((kind is CellClass.SEA for kind in game_map.classes), dtype=bool)
    solid = np.fromiter(
        (kind not in {CellClass.SEA, CellClass.LAKE} for kind in game_map.classes), dtype=bool
    )
    occupied = np.zeros(game_map.labels.shape, dtype=bool)
    planned: dict[str, Domain] = {}
    for key, continent in CONTINENTS.items():
        if key != NEW_WORLD and key in selected:
            checkpoint()
            planned[key] = _claim(
                game_map, continent, selected[key], occupied, sea=sea, solid=solid
            )
    if NEW_WORLD in selected:
        source = _legacy_domain(game_map, selected[NEW_WORLD])
        mask = source.mask.copy()
        for columns, original in source.spans():
            for top in range(0, mask.shape[0], BAND_ROWS):
                rows = slice(top, top + BAND_ROWS)
                labels = game_map.labels[rows, original]
                allowed = source.footprint[rows, columns] | sea[labels]
                mask[rows, columns] &= allowed & ~occupied[rows, original]
        planned[NEW_WORLD] = Domain(
            source.continent, source.first_column, source.map_width, mask, source.footprint
        )
    return tuple(planned[key] for key in CONTINENTS if key in planned)
