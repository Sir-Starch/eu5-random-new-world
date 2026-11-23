"""Generate a complete New World inside an arbitrary domain mask (T3, game-independent).

The domain is the set of pixels that may be replaced. Ocean margins protect the surrounding
Old World and the longitudinal canvas borders; land may reach the polar map edges. The map wrap is
inside this continuous crop and imposes no coast or land budget. Land carries a
continuous relief field (``relief.py``); the highest cells become wastelands. Everything
is integer arithmetic driven by named SplitMix64 streams, so equal inputs give equal
outputs.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import dataclass, field, replace
from functools import partial
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import _native, epoch, omerika, wall
from rnw.basins import shape_relief
from rnw.eu5_biomes import coastal_offsets, ground_field
from rnw.eu5_terrain import land_surface
from rnw.fields import SUBPIXEL, fractal_at, upsample, warped_noise
from rnw.gulfs import carve_inland_seas
from rnw.islands import carve, place
from rnw.isthmuses import raise_isthmuses
from rnw.lakes import carve_lakes
from rnw.land_bridge import NoRouteError, Winding, lattice, paint, route, smooth, swell, trace, wind
from rnw.landmask import LandMaskError
from rnw.messages import say
from rnw.model import CellClass
from rnw.noise import NOISE_SCALE, fractal_noise
from rnw.parallel import Stages, stage_workers
from rnw.progress import checkpoint
from rnw.relief import ReliefHints, generate_relief
from rnw.rivers import RiverGenerationError
from rnw.rng import SplitMix64, derive_seed, mix64
from rnw.sea_corridors import (
    CLEAR_PERMILLE,
    clear_of_corridors,
    corridor_paths,
    corridor_sites,
)
from rnw.straits import pinch
from rnw.synth import grow_regions, merge_slivers, merge_small, renumber, seed_sites
from rnw.timing import measured
from rnw.topology import (
    adjacency_pairs,
    distance_from,
    euclidean_distance,
    label_components,
    unpack_pairs,
)
from rnw.watersheds import (
    DENSITY_STEP,
    MAX_LAND_PX,
    DrainagePlan,
    border_rivers,
    cell_spacing_grid,
    domain_climate,
    domain_rivers,
    plan_drainage,
    river_cells,
    spacing_grid,
    withdrawn_drainage,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Sequence

    from numpy.typing import NDArray

    from rnw.eu5_biomes import SizeModel
    from rnw.islands import Footprint
    from rnw.land_contact import ContactBlend, ContactTerrain
    from rnw.settings import NewWorldSettings

PERMILLE: Final[int] = 1000
STRAIT_LANDING: Final[int] = 2
# A land bridge (``_land_approach``) is a ridge of land along a bent axis, measured in locations
# (``location_px``): it never narrows below two locations, its body swells from 1.2 to 2.4 of them
# in half-width along the way, flares to 1.7 times that where it meets land, and its edge swings
# by a third of its width with the noise of every coast. The axis is the cheapest route over a
# noisy landscape that stays clear of the edges of its room, on blocks of ``BRIDGE_BLOCK`` pixels.
BRIDGE_BLOCK: Final[int] = 16
BRIDGE_CORE: Final[int] = 1000  # permille of a location: radius of the land that is never cut
BRIDGE_BODY: Final[tuple[int, int]] = (1200, 2400)  # permille of a location: the body's radius
BRIDGE_FLARE: Final[int] = 700  # extra permille of the radius at either end
BRIDGE_FLARE_LENGTH: Final[int] = 4000  # permille of a location: how far the flare reaches
BRIDGE_EDGE: Final[int] = 700  # roughness_permille of the edge noise
BRIDGE_SWELL_PERIOD: Final[int] = 6000  # permille of a location: along the axis
BRIDGE_MEANDER: Final[int] = 1800  # extra thousandths of a block a noisy block costs, at most
BRIDGE_TRIES: Final[int] = 12
BRIDGE_WIND_SPACING: Final[int] = 4000  # permille of a location: between the winding's waypoints
BRIDGE_WIND_AMPLITUDE: Final[tuple[int, int]] = (1200, 3000)  # permille of a location: sideways
BRIDGE_LANDING_SCALE: Final[int] = 700  # permille: the bridge to a strait's landing is slighter
# The centre control lifts the land density by up to CENTRE_LIFT elevation units in the middle of
# the canvas, rising over the distance from its edge (to the deepest interior, but at most
# CENTRE_REACH_PX); the land share does not change, only where the land lies.
CENTRE_REACH_PX: Final[int] = 2400
CENTRE_LIFT: Final[int] = NOISE_SCALE
CENTRE_STEP: Final[int] = 4
WOBBLE_PX: Final[int] = 16
WOBBLE_PERIOD: Final[int] = 48
WOBBLE_PASSES: Final[int] = 64
WOBBLE_REPAIRS: Final[int] = 16
STRIP_ROWS: Final[int] = 1024
FIELD_ORIGIN_LIMIT: Final[int] = 1 << 24
INTERIOR_LIMIT: Final[int] = 512
SHORE_LIMIT: Final[int] = 64
# Land keeps clear of the domain edge. Elevation
# falls over a ramp of EDGE_RAMP_MARGINS coast margins whose start moves inland by up to
# EDGE_SHIFT_RAMPS ramps of warped noise with a period of EDGE_SHIFT_PERIOD_PERMILLE of the
# ramp, so coasts neither trace the canvas
# nor run as a straight canal along a strait axis. The ramp does not grow with the feature size:
# a wide ramp leaves only the canvas core for the land budget, and every seed then fills
# the same outline [V-EXEC C64].
EDGE_RAMP_MARGINS: Final[int] = 4
# Along the canvas's boundary with the game's own map (the Old World and the waters kept whole)
# no land lies within this share of the canvas's width: a band of open water wide enough, about
# two and a half sea cells on the installed canvas, for ordinary cells and a lane between the
# land and the waters of the game, instead of a thin row of cells squeezed against the join.
# The land share is kept; the land moves inland.
EDGE_WATER_PERMILLE: Final[int] = 30
EDGE_SHIFT_RAMPS: Final[int] = 2
EDGE_SHIFT_PERIOD_PERMILLE: Final[int] = 2500
MAX_STRAITS: Final[int] = 16
# The least land beside The Wall, as a share of the water beside it, when the barrier takes
# nearly all of the world's land: a few headlands and islands still lie off its coasts.
WALL_SIDE_MIN_PERMILLE: Final[int] = 10
# The land density bends its own coordinates by this share of its feature size, with a
# warp as broad as the feature. Plain fractal noise thresholded gives rounded blobs; bent
# coordinates turn them into peninsulas, hooked capes and gulfs with narrow mouths (compared
# on four seeds with the unbent field: more narrow-mouthed water and more necks). A stronger
# bend (0.8) draws thin marbled slivers, which no coast does.
COAST_WARP_PERMILLE: Final[int] = 450
# Inland seas keep the proportions of a continent-sized world: smaller feature sizes (islands)
# do not shrink them, so a sea needs a landmass that holds it, and larger ones do not
# swell them.
SEA_SCALE_MIN_PX: Final[int] = 1000
SEA_SCALE_MAX_PX: Final[int] = 1600
WARP_STEP: Final[int] = 2
WARP_OCTAVES: Final[int] = 3
OUTSIDE: Final[int] = 2
LAND_KINDS: Final[frozenset[CellClass]] = frozenset(
    {CellClass.LAND, CellClass.WASTELAND, CellClass.NON_OWNABLE}
)


@dataclass(frozen=True, slots=True, eq=False)
class NewWorld:
    """Generated cells for one domain; arrays are in domain-crop coordinates."""

    labels: NDArray[np.int32]
    classes: tuple[CellClass, ...]
    elevation: NDArray[np.int32]
    pixels: NDArray[np.int64]
    centroids: NDArray[np.int64]
    interior: NDArray[np.int64]
    mean_elevation: NDArray[np.int64]
    spread: NDArray[np.int64]
    edges: tuple[tuple[int, int], ...]
    moves: NDArray[np.int64] = field(default_factory=lambda: np.zeros((0, 2), dtype=np.int64))
    # The cells the Wall's guaranteed land core runs through, one chain from the north edge to
    # the south, in ascending order (empty for any other world): the barrier itself, which the
    # wasteland plan keeps impassable (``rnw.barrens``). ``rnw.ports.relabel`` renumbers it.
    barrier: NDArray[np.int64] = field(default_factory=lambda: np.zeros(0, dtype=np.int64))
    # Playable cells along a generated overland contact with retained land.
    land_link: NDArray[np.int64] = field(default_factory=lambda: np.zeros(0, dtype=np.int64))
    strait_landing: tuple[int, int] | None = None
    # How the land drains (epoch 64, ``epoch.RIVERS_FIRST``): the plan its rivers were drawn along
    # when the cells were grown, which the export draws them along again; None before.
    drainage: DrainagePlan | None = None
    # A composed raster uses the game's full longitude, with adjacency across its cut.
    wrap_x: bool = False


def _field(  # noqa: PLR0913 - a field is defined by its stream, shape, octaves and warp.
    seed: int,
    stream: str,
    *,
    shape: tuple[int, int],
    period: int,
    octaves: int,
    persistence_permille: int,
    warp_permille: int = 0,
) -> NDArray[np.int32]:
    """Fractal noise on a seed-positioned lattice, in memory-bounded row strips.

    A fixed lattice gives the same pixels high variance in every world: its nodes
    vary much more than the spaces between them. In a narrow part of the canvas
    (such as the old Alaska) that favours the same island outline. Draw the phase
    across many periods so no position in the canvas owns a lattice node, and
    changing feature size does not keep sampling the same few nodes. The origin
    belongs to the whole field, including both sides of the map seam, not a strip
    or a connected part of the domain. Coordinates stay well inside integer limits.

    With ``warp_permille`` the coordinates are first displaced by two smooth noises of
    that share of ``period`` (see ``_warped_rows``); the field is then still a function
    of the pixel alone, so any strip height gives the same values.
    """
    height, width = shape
    key = derive_seed(seed, stream)
    origin = SplitMix64(derive_seed(seed, stream, "origin"))
    x0, y0 = origin.below(FIELD_ORIGIN_LIMIT), origin.below(FIELD_ORIGIN_LIMIT)
    out = np.empty(shape, dtype=np.int32)
    for row in range(0, height, STRIP_ROWS):
        rows = min(STRIP_ROWS, height - row)
        if warp_permille:
            out[row : row + rows] = _warped_rows(
                key,
                (x0, y0, row),
                (rows, width),
                period=period,
                octaves=octaves,
                persistence_permille=persistence_permille,
                warp_permille=warp_permille,
            )
            continue
        out[row : row + rows] = fractal_noise(
            key,
            x0,
            y0 + row,
            width,
            rows,
            period=period,
            octaves=octaves,
            persistence_permille=persistence_permille,
        )
    return out


def _warped_rows(  # noqa: PLR0913 - the strip, its field and the warp are all inputs.
    key: int,
    origin: tuple[int, int, int],
    shape: tuple[int, int],
    *,
    period: int,
    octaves: int,
    persistence_permille: int,
    warp_permille: int,
) -> NDArray[np.int64]:
    """Rows ``origin[2]`` onwards of a domain-warped rotated fractal field.

    The field is sampled on a lattice every ``WARP_STEP`` pixels of the whole raster and
    interpolated, so a strip may start on any row: it reads the lattice rows that surround
    it and drops the pixels above its first row.
    """
    x0, y0, first = origin
    rows, width = shape
    lattice = first // WARP_STEP
    skip = first - lattice * WARP_STEP
    ys = (np.arange((skip + rows) // WARP_STEP + 2, dtype=np.int64) + lattice) * WARP_STEP + y0
    xs = np.arange(width // WARP_STEP + 2, dtype=np.int64) * WARP_STEP + x0
    ys, xs = np.broadcast_arrays((ys * SUBPIXEL)[:, np.newaxis], (xs * SUBPIXEL)[np.newaxis, :])
    amplitude = period * warp_permille // PERMILLE * SUBPIXEL
    dx = fractal_at(
        mix64(key ^ 0x57A1), xs, ys, period=period, octaves=WARP_OCTAVES, persistence_permille=500
    )
    dy = fractal_at(
        mix64(key ^ 0x57A2), xs, ys, period=period, octaves=WARP_OCTAVES, persistence_permille=500
    )
    coarse = fractal_at(
        key,
        xs + dx * amplitude // NOISE_SCALE,
        ys + dy * amplitude // NOISE_SCALE,
        period=period,
        octaves=octaves,
        persistence_permille=persistence_permille,
    )
    return upsample(coarse, WARP_STEP, (skip + rows, width))[skip:]


def _edge_offset(
    seed: int,
    wobble: NDArray[np.int32],
    *,
    ramp: int,
    shift_px: int,
    shift_period: int,
) -> NDArray[np.int32]:
    """Where the coast ramp starts, per pixel: wobble minus the inland shift.

    The shift noise is built in strips of ``STRIP_ROWS`` rows (a multiple of the noise
    step); the offset is a few ramps wide, so a 32-bit raster holds it.
    """
    height, width = (int(size) for size in wobble.shape)
    key = derive_seed(seed, "new_world_edge_shift")
    offset = np.empty((height, width), dtype=np.int32)
    for first in range(0, height, STRIP_ROWS):
        rows = min(STRIP_ROWS, height - first)
        shift = warped_noise(
            key,
            (rows, width),
            step=8,
            period=shift_period,
            octaves=4,
            warp_px=shift_period // 4,
            row0=first,
        )
        # Warped noise mostly stays within +-0.4 of NOISE_SCALE; stretch it over the shift.
        inland = (
            shift_px * np.clip(NOISE_SCALE // 2 + shift * 5 // 4, 0, NOISE_SCALE) // NOISE_SCALE
        )
        offset[first : first + rows] = (
            wobble[first : first + rows].astype(np.int64) * ramp // (3 * NOISE_SCALE) - inland
        )
    return offset


PERCENT: Final[int] = 100
# Of the land a drawing asks for inside the area, the least that must stay after the margin.
MIN_KEPT_PERCENT: Final[int] = 50


def land_stage(
    domain: NDArray[np.bool_],
    seed: int,
    settings: NewWorldSettings,
    template: NDArray[np.bool_] | None = None,
    *,
    outside_land: NDArray[np.bool_] | None = None,
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_], NDArray[np.int32]]:
    """Return land, ocean, lake masks and the shaped elevation.

    With ``settings.template_permille`` (Omerika, ``rnw.omerika``) the density field also holds the
    low-frequency template of the installed game's Americas, ``template``, on the domain.
    """
    if settings.landform:
        return _wall_land(domain, seed, settings)
    relief = _field(
        seed,
        "new_world_elevation",
        shape=domain.shape,
        period=settings.feature_px,
        octaves=settings.octaves,
        persistence_permille=settings.persistence_permille,
        warp_permille=COAST_WARP_PERMILLE,
    )
    shape = None
    if settings.template_permille:
        shape = _template(domain, seed, settings, template)
        omerika.add_to(relief, shape)
    land, ocean, lakes, elevation = _natural_land(
        domain, seed, settings, relief, outside_land=outside_land
    )
    if shape is not None:
        omerika.check_joined(land, shape)
    return land, ocean, lakes, elevation


def _template(
    domain: NDArray[np.bool_],
    seed: int,
    settings: NewWorldSettings,
    template: NDArray[np.bool_] | None,
) -> omerika.Template:
    """The prepared template of the Americas for this domain, seed and settings."""
    if template is None or template.shape != domain.shape:
        message = "Omerika needs the Americas' template of the canvas, and the template given "
        message += "is missing or does not fit the canvas"
        raise omerika.OmerikaError(message)
    return omerika.prepare(template, seed, settings)


def _natural_land(  # noqa: PLR0913 - the density field, the land budget and the canvas's boundary.
    domain: NDArray[np.bool_],
    seed: int,
    settings: NewWorldSettings,
    relief: NDArray[np.int32],
    *,
    budget_px: int | None = None,
    outside: NDArray[np.bool_] | None = None,
    outside_land: NDArray[np.bool_] | None = None,
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_], NDArray[np.int32]]:
    """Construct natural coasts from a density field, preserving the requested land budget.

    The budget is the land share of ``settings``, or ``budget_px`` pixels when a caller has
    already spent part of it elsewhere (The Wall). ``outside`` is what lies beyond the canvas's
    boundary with the game's map (what is not ``domain`` by default; The Wall clears its own
    course from the domain and says what the canvas's boundary is).
    """
    margin = settings.coast_margin_px
    ramp = EDGE_RAMP_MARGINS * margin
    shift_px = EDGE_SHIFT_RAMPS * ramp
    shift_period = max(8, ramp * EDGE_SHIFT_PERIOD_PERMILLE // PERMILLE)
    water = _outer_water(domain, outside_land)
    guard = water.copy()
    guard[:, [0, -1]] = True
    share = _widen_boundary(guard, domain, water if outside is None else outside, settings)
    del water
    if budget_px is None and share != settings.land_permille:
        settings = replace(settings, land_permille=share)
    _guard_polar_edges(guard, domain, relief, settings)
    contact = (
        None if outside_land is None else distance_from(outside_land, ramp + 1, octagonal=True)
    )
    wobble = _field(
        seed,
        "new_world_edge",
        shape=domain.shape,
        period=max(8, ramp // 2),
        octaves=3,
        persistence_permille=500,
    )
    offset = _edge_offset(seed, wobble, ramp=ramp, shift_px=shift_px, shift_period=shift_period)
    del wobble
    open_shore = (
        distance_from(open_sea(domain, outside_land=outside_land), margin, octagonal=True) < margin
    )
    # A sea cut off from open water (around a protected islet) gets a strait: its shortest
    # path to open water joins the guard and the coasts are drawn again, so the strait has
    # the same ragged shores as every other coast instead of a straight canal [V-EXEC C64].
    land, shore, elevation = _coasts(
        domain,
        guard,
        relief,
        offset,
        ramp=ramp,
        settings=settings,
        budget_px=budget_px,
        contact=contact,
    )
    for _ in range(MAX_STRAITS):
        checkpoint()
        path = stray_strait(domain, land, shore=shore, open_shore=open_shore)
        if path is None:
            break
        guard |= path
        land, shore, elevation = _coasts(
            domain,
            guard,
            relief,
            offset,
            ramp=ramp,
            settings=settings,
            budget_px=budget_px,
            contact=contact,
        )
    del relief, offset, guard, open_shore, contact
    # Isthmuses, inland seas and then lakes are made before islands are counted, so none
    # leaves a speck behind.
    ocean = _ocean(domain, land, shore)[1]
    scale = max(SEA_SCALE_MIN_PX, min(settings.feature_px, SEA_SCALE_MAX_PX))
    land |= raise_isthmuses(land, ocean, domain & ~shore, seed, scale_px=scale)
    ocean = _ocean(domain, land, shore)[1]
    land &= ~carve_inland_seas(
        land,
        ocean,
        seed,
        scale_px=max(SEA_SCALE_MIN_PX, min(settings.feature_px, SEA_SCALE_MAX_PX)),
    )
    del ocean
    land &= ~carve_lakes(
        land, seed, smallest=settings.min_lake_px, largest=settings.max_lake_px * 9 // 10
    )
    land &= _large_parts(land, settings.min_island_px)
    return (*_classify(domain, land, shore, settings), elevation)


def _widen_boundary(
    guard: NDArray[np.bool_],
    domain: NDArray[np.bool_],
    outside: NDArray[np.bool_],
    settings: NewWorldSettings,
) -> int:
    """Keep the land ``EDGE_WATER_PERMILLE`` of the canvas's width from its boundary.

    The band along the boundary joins ``guard``, so the coast ramp starts at its inner edge. The
    polar edges are not a join with the game's map and get no band. Returns the land share (permille
    of the interior that is left) that holds as much land as the settings' share holds without the
    band.
    """
    width = max(0, int(domain.shape[1]) * EDGE_WATER_PERMILLE // PERMILLE)
    margin = settings.coast_margin_px
    if width <= margin:
        return settings.land_permille
    source = outside.copy()
    source[:, [0, -1]] = True
    before = int(
        np.count_nonzero(domain & (distance_from(guard, margin, octagonal=True) >= margin))
    )
    guard |= distance_from(source, width, octagonal=True) < width
    after = int(np.count_nonzero(domain & (distance_from(guard, margin, octagonal=True) >= margin)))
    return min(PERMILLE, -(-settings.land_permille * before // max(1, after)))


def _guard_polar_edges(
    guard: NDArray[np.bool_],
    domain: NDArray[np.bool_],
    relief: NDArray[np.int32],
    settings: NewWorldSettings,
) -> None:
    """Leave one narrow, seed-dependent land approach at each polar edge.

    The ordinary coast ramp then shapes the approach; the rest of the polar
    boundary behaves like an ocean-facing canvas boundary. Choose the opening
    where the density field is strongest just inland, so it can join a continent.
    """
    height, width = domain.shape
    ramp = EDGE_RAMP_MARGINS * settings.coast_margin_px
    opening = min(width, max(8 * settings.location_px, 4 * ramp + 1))
    if opening >= width:
        return
    for edge, sample in (
        (0, min(height - 1, 2 * ramp)),
        (height - 1, max(0, height - 1 - 2 * ramp)),
    ):
        eligible = domain[edge] & domain[sample]
        if not np.any(eligible):
            guard[edge] = True
            continue
        score = np.where(eligible, relief[sample], -10 * NOISE_SCALE).astype(np.int64)
        # A full-width window avoids selecting an isolated high pixel beside protected water.
        sums = np.convolve(score, np.ones(opening, dtype=np.int64), mode="valid")
        start = int(np.argmax(sums))
        guard[edge] = True
        guard[edge, start : start + opening] = ~domain[edge, start : start + opening]


def _wall_land(
    domain: NDArray[np.bool_], seed: int, settings: NewWorldSettings
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_], NDArray[np.int32]]:
    """Build the barrier and seed both continental placement and local coasts beside it.

    Splitting the canvas leaves broad northern and southern pockets. Local coast
    noise alone scatters land through each pocket, repeating that composition even
    on different seeds. A longer wavelength lets whole regions become ocean or
    continent; the original field supplies bays, peninsulas and islands. Both
    scales follow feature size, with one sea level for all the side land.

    The barrier takes its land first out of the world's land share, so a wider Wall leaves
    less for the continents beside it: when it needs all of the share, only the small
    ``WALL_SIDE_MIN_PERMILLE`` remains there. A Wall wider than the share allows keeps its land.
    """
    course = wall.route(domain, settings)
    barrier = wall.coast(domain, seed, settings)
    off_limits = _off_limits(domain, settings)
    budget = settings.land_permille * int(np.count_nonzero(domain & ~off_limits)) // PERMILLE
    budget -= int(np.count_nonzero(barrier))
    sides = domain.copy()
    wall.keep_clear(
        sides, course, course.half + max(2 * settings.coast_margin_px, settings.sea_zone_px)
    )
    relief = _field(
        seed,
        "wall_continents",
        shape=domain.shape,
        period=4 * settings.feature_px,
        octaves=settings.octaves,
        persistence_permille=settings.persistence_permille,
    )
    detail = _field(
        seed,
        "new_world_elevation",
        shape=domain.shape,
        period=settings.feature_px,
        octaves=settings.octaves,
        persistence_permille=settings.persistence_permille,
        warp_permille=COAST_WARP_PERMILLE,
    )
    relief *= 2
    relief += detail
    relief //= 3
    del detail
    land, _, _, elevation = _natural_land(
        sides, seed, settings, relief, budget_px=max(0, budget), outside=~domain
    )
    land |= barrier
    return (*_classify(domain, land, off_limits, settings), elevation)


def _ocean(
    domain: NDArray[np.bool_], land: NDArray[np.bool_], shore: NDArray[np.bool_]
) -> tuple[NDArray[np.int32], NDArray[np.bool_]]:
    """Labelled parts of the domain (land and water apart) and the water that reaches the shore."""
    coded = np.where(domain, land.astype(np.int32), OUTSIDE).astype(np.int32, copy=False)
    parts = label_components(coded)
    del coded
    water = domain & ~land
    ocean_part = np.zeros(int(parts.max()) + 1, dtype=bool)
    ocean_part[np.unique(parts[water & shore])] = True
    return parts, water & ocean_part[parts]


def inland_sea_min_area(settings: NewWorldSettings) -> int:
    """A closed sea holds at least four typical sea zones and exceeds the drawn lake size."""
    return max(
        settings.max_lake_px + 1,
        settings.min_lake_px,
        4 * max(settings.sea_zone_px**2, settings.min_sea_cell_px),
    )


def _classify(
    domain: NDArray[np.bool_],
    land: NDArray[np.bool_],
    shore: NDArray[np.bool_],
    settings: NewWorldSettings,
    marked: NDArray[np.bool_] | None = None,
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_]]:
    """Classify physical water before cells, relief or ports are constructed.

    Returns land, ocean and lake masks. Water that reaches the shore is ocean; water enclosed
    by land is a lake below ``inland_sea_min_area``, and a navigable inland sea above it.
    Only water smaller than ``min_lake_px`` fills with land. The lake-size setting controls
    drawn lakes; a natural basin can exceed it without being large enough to be a sea.

    ``marked`` are the pixels a drawing marks as lakes: an enclosed water that is mostly marked
    is a lake whatever its size, neither filled nor made a sea.
    """
    parts, ocean = _ocean(domain, land, shore)
    water = domain & ~land
    sizes = np.bincount(parts.ravel())
    enclosed = water & ~ocean
    small = enclosed & (sizes < settings.min_lake_px)[parts]
    inland = enclosed & (sizes >= inland_sea_min_area(settings))[parts]
    if marked is not None:
        painted = np.bincount(parts[marked & enclosed], minlength=len(sizes))
        kept = (painted * 2 >= sizes)[parts]
        small &= ~kept
        inland &= ~kept
    return land | small, ocean | inland, enclosed & ~small & ~inland


def _lakes_open(
    domain: NDArray[np.bool_],
    land: NDArray[np.bool_],
    shore: NDArray[np.bool_],
    marked: NDArray[np.bool_],
) -> None:
    """Refuse a drawing whose marked lakes open to the sea: a lake is water that land encloses,
    and one that does not would be a bay, not what the drawing says."""
    _, ocean = _ocean(domain, land, shore)
    leaking = marked & ocean & domain
    if not leaking.any():
        return
    rows, columns = np.nonzero(leaking)
    message = say(
        "mask.lake_open",
        left=int(columns.mean()) * 100 // domain.shape[1],
        top=int(rows.mean()) * 100 // domain.shape[0],
    )
    raise LandMaskError(message)


def _land_from_mask(
    domain: NDArray[np.bool_],
    drawn: NDArray[np.bool_],
    settings: NewWorldSettings,
    lakes: NDArray[np.bool_] | None = None,
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_]]:
    """Land, ocean and lakes of a land that is drawn, not generated (``rnw.landmask``).

    ``lakes`` are the pixels the drawing marks as lakes; they stay lakes, and a marked lake
    that land does not enclose is refused.

    The land keeps off the canvas's edge, as generated land does (the coast margin from what
    lies outside the domain and the border); specks under
    ``min_island_px`` go. A drawing that loses most of its land to that is refused, since it
    asks for land where the New World cannot be.
    """
    margin = settings.coast_margin_px
    guard = ~domain
    guard[:, [0, -1]] = True
    shore = distance_from(guard, margin, octagonal=True) < margin
    del guard
    wanted = drawn & domain
    land = wanted & ~shore
    asked, kept = int(np.count_nonzero(wanted)), int(np.count_nonzero(land))
    if not asked or kept * PERCENT < asked * MIN_KEPT_PERCENT:
        share = kept * PERCENT // max(1, asked)
        message = (
            f"Most of the land drawn lies where the New World cannot be: {share} % of it is "
            f"inside the area and away from its edge ({margin} pixels of coast margin). "
            "Draw the continents well inside the picture and inside the area"
        )
        raise LandMaskError(message)
    land &= _large_parts(land, settings.min_island_px)
    open_shore = distance_from(open_sea(domain), margin, octagonal=True) < margin
    for _ in range(MAX_STRAITS):
        checkpoint()
        path = stray_strait(domain, land, shore=shore, open_shore=open_shore)
        if path is None:
            break
        # A sea that the drawing cuts off from open water gets a strait, a coast margin wide,
        # as generated land does (C64): no sea zone may be left without a way to the sea.
        land &= distance_from(path, margin, octagonal=True) >= margin
        land &= _large_parts(land, settings.min_island_px)
    if not land.any():
        message = (
            f"No land is left once parts under {settings.min_island_px} pixels are taken out: "
            "draw larger continents"
        )
        raise LandMaskError(message)
    if lakes is not None:
        _lakes_open(domain, land, shore, lakes)
    return _classify(domain, land, shore, settings, lakes)


def _outer_water(
    domain: NDArray[np.bool_], outside_land: NDArray[np.bool_] | None
) -> NDArray[np.bool_]:
    outside = ~domain
    if outside_land is not None:
        outside &= ~outside_land
    return outside


def _off_limits(
    domain: NDArray[np.bool_],
    settings: NewWorldSettings,
    outside_land: NDArray[np.bool_] | None = None,
) -> NDArray[np.bool_]:
    """Pixels where no land may be added after the coasts are drawn: a coast margin from what
    lies outside the domain and from the longitudinal borders."""
    guard = _outer_water(domain, outside_land)
    guard[:, [0, -1]] = True
    margin = settings.coast_margin_px
    shore = distance_from(guard, margin, octagonal=True) < margin
    if outside_land is not None:
        contact = distance_from(outside_land, margin + 1, octagonal=True)
        shore &= contact > margin
        shore |= ~domain
    return shore


def _large_parts(mask: NDArray[np.bool_], minimum: int) -> NDArray[np.bool_]:
    """Pixels of ``mask`` that sit in a 4-connected part of the labelling of at least ``minimum``.

    The labelling is of the mask as a 0/1 raster, so the parts are land and water alike;
    callers intersect the result with the side they mean.
    """
    parts = label_components(mask.astype(np.int32))
    return (np.bincount(parts.ravel()) >= minimum)[parts]


def _centre_lift(guard: NDArray[np.bool_], permille: int) -> NDArray[np.int32] | None:
    """Elevation lift by the distance from the guard, on blocks of ``CENTRE_STEP`` pixels.

    None for no lift. The distance is Euclidean and rises smoothly (a smoothstep), so no
    contour of it shows in the coasts; the deepest interior gets the whole lift.
    """
    if permille <= 0:
        return None
    height, width = guard.shape
    rows, columns = -(-height // CENTRE_STEP), -(-width // CENTRE_STEP)
    padded = np.ones((rows * CENTRE_STEP, columns * CENTRE_STEP), dtype=bool)
    padded[:height, :width] = guard
    pooled = padded.reshape(rows, CENTRE_STEP, columns, CENTRE_STEP).any(axis=(1, 3))
    del padded
    limit = CENTRE_REACH_PX // CENTRE_STEP
    distance = euclidean_distance(pooled, limit)
    deepest = max(1, int(distance.max()))
    unit = np.minimum(distance, deepest) * PERMILLE // deepest
    smooth = unit * unit * (3 * PERMILLE - 2 * unit) // (PERMILLE * PERMILLE)
    return (smooth * CENTRE_LIFT * permille // (PERMILLE * PERMILLE)).astype(np.int32)


def _coasts(  # noqa: PLR0913 - the coast model needs the guard, both fields and the ramp.
    domain: NDArray[np.bool_],
    guard: NDArray[np.bool_],
    relief: NDArray[np.int32],
    offset: NDArray[np.int32],
    *,
    ramp: int,
    settings: NewWorldSettings,
    budget_px: int | None = None,
    contact: NDArray[np.int32] | None = None,
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.int32]]:
    """Lower the relief over a ramp from the guard and keep the land budget.

    Returns land, shore (no land within a coast margin of the guard) and the elevation.
    The per-pixel arithmetic runs in strips; only the two distance fields are whole-raster.
    With ``budget_px`` the land is that many pixels of the interior (at least
    ``WALL_SIDE_MIN_PERMILLE`` of it) instead of the settings' land share.
    """
    # The cap must exceed every reach, or the wobble would dent the interior too.
    edge = distance_from(guard, ramp - int(offset.min()) + 2, octagonal=True)
    # No land in slivers of the domain too thin to hold a full ramp.
    opened = distance_from(edge >= ramp, ramp + 1, octagonal=True) <= ramp
    shore = edge < settings.coast_margin_px
    if contact is not None:
        shore &= contact > settings.coast_margin_px
    height, width = (int(size) for size in edge.shape)
    elevation = np.empty((height, width), dtype=np.int32)
    lift = _centre_lift(guard, settings.centre_permille)
    for first in range(0, height, STRIP_ROWS):
        rows = slice(first, min(height, first + STRIP_ROWS))
        reach = edge[rows].astype(np.int64) + offset[rows]
        penalty = (ramp - reach) * NOISE_SCALE * 3 // ramp
        penalty = np.where(opened[rows], penalty, 3 * NOISE_SCALE)
        if contact is not None:
            # The coast ramp is half strength where dry ground continues into the
            # retained terrain. The same density field still decides if it reaches.
            fade = np.minimum(contact[rows] - 1, ramp).clip(0)
            penalty = penalty * (ramp + fade) // (2 * ramp)
        elevation[rows] = (relief[rows] - np.maximum(0, penalty)).astype(np.int32)
        if lift is not None:
            blocks = lift[first // CENTRE_STEP : -(-rows.stop // CENTRE_STEP)]
            spread = np.repeat(np.repeat(blocks, CENTRE_STEP, axis=0), CENTRE_STEP, axis=1)
            elevation[rows] += spread[: rows.stop - first, :width]
    del edge, opened
    interior = domain & ~shore
    share = settings.land_permille
    if budget_px is not None:
        share = min(
            PERMILLE,
            max(
                WALL_SIDE_MIN_PERMILLE,
                budget_px * PERMILLE // max(1, int(np.count_nonzero(interior))),
            ),
        )
    threshold = _threshold(elevation, interior, share)
    return interior & (elevation >= threshold), shore, elevation


def _threshold(values: NDArray[np.int32], mask: NDArray[np.bool_], permille: int) -> int:
    """The value that ``permille`` of the masked values (rounded down) reach or pass.

    Equal to ``np.partition(values[mask], n - keep)[n - keep]`` with ``keep = n * permille
    // 1000``, found by counting the values instead of copying and partitioning them.
    """
    height = int(values.shape[0])
    lows: list[int] = []
    highs: list[int] = []
    for first in range(0, height, STRIP_ROWS):
        strip = values[first : first + STRIP_ROWS][mask[first : first + STRIP_ROWS]]
        if strip.size:
            lows.append(int(strip.min()))
            highs.append(int(strip.max()))
    if not lows:
        message = "no pixel can hold land"
        raise ValueError(message)
    low, high = min(lows), max(highs)
    counts = np.zeros(high - low + 1, dtype=np.int64)
    for first in range(0, height, STRIP_ROWS):
        strip = values[first : first + STRIP_ROWS][mask[first : first + STRIP_ROWS]]
        counts += np.bincount(strip.astype(np.int64) - low, minlength=counts.size)
    total = int(counts.sum())
    keep = total * permille // PERMILLE
    if keep < 1:
        message = f"a land share of {permille} permille keeps no pixel of {total}"
        raise ValueError(message)
    return low + int(np.searchsorted(np.cumsum(counts), total - keep, side="right"))


def open_sea(
    domain: NDArray[np.bool_], *, outside_land: NDArray[np.bool_] | None = None
) -> NDArray[np.bool_]:
    """Pixels outside the domain that reach the raster border, and the border itself.

    Holes in the domain (protected islands or seas inside it) are not open sea.
    """
    outside = _outer_water(domain, outside_land)
    parts = label_components(outside.astype(np.int32))
    border = np.zeros(domain.shape, dtype=bool)
    border[[0, -1], :] = True
    border[:, [0, -1]] = True
    if outside_land is not None:
        border &= ~outside_land
    reaching = np.unique(parts[border & outside])
    return border | (outside & np.isin(parts, reaching))


def _path(
    start: NDArray[np.bool_], target: NDArray[np.bool_], passable: NDArray[np.bool_]
) -> NDArray[np.bool_]:
    """Shortest 4-connected path over ``passable`` pixels from ``start`` to ``target``.

    Breadth-first; ties go to the lowest-index neighbour. Empty if unreachable.
    """
    height, width = start.shape
    previous = np.full(start.size, -1, dtype=np.int32)
    seen = start.ravel() | ~passable.ravel()
    goal = target.ravel()
    frontier = np.flatnonzero(start.ravel())
    end = -1
    while frontier.size and end < 0:
        column = frontier % width
        origins = [
            frontier[frontier >= width],
            frontier[frontier < (height - 1) * width],
            frontier[column != 0],
            frontier[column != width - 1],
        ]
        source = np.concatenate(origins)
        reached = np.concatenate(
            [origins[0] - width, origins[1] + width, origins[2] - 1, origins[3] + 1]
        )
        fresh = ~seen[reached]
        source, reached = source[fresh], reached[fresh]
        order = np.lexsort((source, reached))
        source, reached = source[order], reached[order]
        first = np.concatenate([[True], reached[1:] != reached[:-1]]) if reached.size else reached
        source, reached = source[first], reached[first]
        previous[reached] = source
        seen[reached] = True
        hits = reached[goal[reached]]
        end = int(hits.min()) if hits.size else -1
        frontier = reached
    path = np.zeros(start.size, dtype=bool)
    node = end
    while node >= 0:
        path[node] = True
        node = int(previous[node])
    return path.reshape(height, width)


@dataclass(frozen=True, slots=True, eq=False)
class Approach:
    """The section of generated land that connects the chosen shore to the interior."""

    box: tuple[slice, slice]
    path: NDArray[np.bool_]
    point: tuple[int, int]


def _land_approach(  # noqa: PLR0913 - the terrain, its boundaries and the seed define the coast.
    land: NDArray[np.bool_],
    domain: NDArray[np.bool_],
    shore: NDArray[np.bool_],
    interface: NDArray[np.bool_],
    *,
    outside_land: NDArray[np.bool_] | None,
    settings: NewWorldSettings,
    seed: int,
    scale: int = PERMILLE,
    whole: NDArray[np.bool_] | None = None,
    keep_seas: bool = False,
) -> Approach | None:
    """Raise a land bridge from a seeded shore to the continent: a bent, swelling ridge of land.

    ``scale`` is the permille of the usual width of its body. A bridge never cuts a sea off from
    the open sea (``whole`` is the domain with the water reserved for a strait): a ridge that
    closes round the water of a protected islet is not made. With ``keep_seas`` it does not
    divide the open water into pieces that hold a sea cell either, as a bridge to a strait's
    landing would across the Mediterranean and leave a bay no generated sea leads out of.

    The sites of ``interface`` are tried in the order of their distance from the continent
    (the largest land) and a seeded jitter; the first whose bridge joins both is made. None when
    none does.
    """
    step = max(8, settings.location_px // 2)
    sites = np.argwhere(interface & domain)
    parts = label_components(land.astype(np.int32))
    sizes = np.bincount(parts.ravel())
    sizes[~np.isin(np.arange(len(sizes)), parts[land])] = 0
    continent = land & (sizes[parts] * 2 >= sizes.max())
    del parts
    core = np.argwhere(continent[::step, ::step]) * step
    if sites.size == 0 or core.size == 0:
        return None
    _, unique = np.unique(sites // (step * 4), axis=0, return_index=True)
    sites = sites[unique]
    nearest = core[
        _native.nearest_rows(np.ascontiguousarray(core), np.ascontiguousarray(sites), 1)[:, 0]
    ]
    distance = np.max(np.abs(nearest - sites), axis=1)
    key = derive_seed(seed, "africa_land_approach")
    candidates = sorted(
        range(len(sites)),
        key=lambda i: (
            int(distance[i])
            + mix64(key ^ (int(sites[i, 0]) << 32) ^ int(sites[i, 1])) % (12 * step),
            i,
        ),
    )
    ground = _BridgeGround(land, domain, shore, interface, continent, outside_land, settings, scale)
    if whole is not None:
        open_water = _touching_open_sea(whole, outside_land)
        seas = _sea_state(whole, land, shore, open_water, settings.min_sea_cell_px)
        ground = replace(ground, whole=whole, open_water=open_water, seas=seas, keep_seas=keep_seas)
    for index in candidates[:BRIDGE_TRIES]:
        checkpoint()
        approach = _bridge(
            ground,
            (int(sites[index, 0]), int(sites[index, 1])),
            int(distance[index]),
            derive_seed(seed, "land_bridge", str(index)),
        )
        if approach is not None:
            return approach
    return None


@dataclass(frozen=True)
class _BridgeGround:
    """The ground a land bridge is made on: the land, its limits and what sizes the bridge."""

    land: NDArray[np.bool_]
    domain: NDArray[np.bool_]
    shore: NDArray[np.bool_]
    interface: NDArray[np.bool_]
    continent: NDArray[np.bool_]
    outside_land: NDArray[np.bool_] | None
    settings: NewWorldSettings
    scale: int
    # The whole domain and the pixels open to the sea outside it, when a bridge must not cut a
    # sea off from them (``seas`` is how many seas land has cut off and, with ``keep_seas``,
    # how many large ones reach open water before the bridge, which it may not change).
    whole: NDArray[np.bool_] | None = None
    open_water: NDArray[np.bool_] | None = None
    seas: tuple[int, int] = (0, 0)
    keep_seas: bool = False

    def width(self, value: int) -> int:
        """``value`` thousandths of a location, at the bridge's scale, in pixels."""
        return value * self.settings.location_px * self.scale // (PERMILLE * PERMILLE)


def _bridge_axis(
    ground: _BridgeGround, window: tuple[slice, slice], here: tuple[int, int], seed: int
) -> tuple[NDArray[np.int64], NDArray[np.bool_]] | None:
    """The axis of a bridge from ``here`` to the continent within ``window``, and where land may
    lie there: the domain beyond its coast margin and the neighbourhood of ``here`` (its limits
    come from what is outside the domain). The axis is the cheapest route over coarse blocks of
    a noisy landscape that keeps clear of the limits, smoothed; None when no route reaches."""
    location = ground.settings.location_px
    body = ground.width(BRIDGE_BODY[1])
    rows, columns = window
    near = np.zeros(ground.land[window].shape, dtype=bool)
    near[here] = True
    reach_near = ground.settings.coast_margin_px + location
    near = distance_from(near, reach_near, octagonal=True) <= reach_near
    allowed = ground.domain[window] & (~ground.shore[window] | near)
    del near
    start_mask = np.zeros(allowed.shape, dtype=bool)
    start_mask[here] = True
    block = BRIDGE_BLOCK
    coarse_rows, coarse_columns = (-(-size // block) for size in allowed.shape)

    def pooled(mask: NDArray[np.bool_], reduce: str) -> NDArray[np.bool_]:
        padded = np.zeros((coarse_rows * block, coarse_columns * block), dtype=bool)
        padded[: mask.shape[0], : mask.shape[1]] = mask
        grid = padded.reshape(coarse_rows, block, coarse_columns, block)
        return grid.all(axis=(1, 3)) if reduce == "all" else grid.any(axis=(1, 3))

    clearance = euclidean_distance(~pooled(allowed, "all"), 64 * block) // 8
    comfort = max(1, (body + ground.settings.coast_margin_px) // block)
    needed = max(2, BRIDGE_CORE * location // PERMILLE // block + 1)
    in_start_zone = pooled(distance_from(start_mask, 2 * body, octagonal=True) <= 2 * body, "any")
    passable = (clearance >= needed) | (in_start_zone & pooled(allowed, "any"))
    noise = _field(
        seed,
        "land_bridge_route",
        shape=(coarse_rows, coarse_columns),
        period=max(4, BRIDGE_SWELL_PERIOD * location // PERMILLE // block),
        octaves=2,
        persistence_permille=500,
    ).astype(np.int64)
    cost = (
        PERMILLE
        + BRIDGE_MEANDER * (noise + NOISE_SCALE // 2) // NOISE_SCALE
        + 2 * PERMILLE * np.clip(comfort - clearance, 0, comfort) // comfort
    ).astype(np.int32)
    start = (here[0] // block, here[1] // block)
    goal = pooled(ground.continent[rows, columns], "any")
    try:
        blocks = route(cost, passable, start, goal)
    except NoRouteError:
        return None
    low, high = (max(1, value * location // PERMILLE // block) for value in BRIDGE_WIND_AMPLITUDE)
    spacing = max(2, BRIDGE_WIND_SPACING * location // PERMILLE // block)
    blocks = wind(
        blocks,
        cost,
        passable,
        goal,
        Winding(spacing, low, high, derive_seed(seed, "land_bridge_wind")),
    )
    centres = [(r * block + block // 2, c * block + block // 2) for r, c in blocks]
    centres[0] = here
    return trace(smooth(centres)), allowed


def _bridge_ridge(
    ground: _BridgeGround,
    window: tuple[slice, slice],
    allowed: NDArray[np.bool_],
    axis: NDArray[np.int64],
    seed: int,
) -> tuple[tuple[slice, slice], NDArray[np.bool_]]:
    """The body of a bridge along ``axis`` (rows of row, column, distance within ``window``) and
    the box it lies in: a ridge that swells and narrows, flares at both ends, has the irregular
    edge of every other coast and narrows to the room beside the domain's coast margin."""
    location = ground.settings.location_px
    rows, columns = window
    length = int(axis[-1, 2])
    pad = 3 * ground.width(BRIDGE_BODY[1]) + ground.settings.coast_margin_px
    low = np.min(axis[:, :2], axis=0) - pad
    high = np.max(axis[:, :2], axis=0) + pad + 1
    top, left = max(0, int(low[0])), max(0, int(low[1]))
    bottom, right = (
        min(rows.stop - rows.start, int(high[0])),
        min(columns.stop - columns.start, int(high[1])),
    )
    box = (
        slice(rows.start + top, rows.start + bottom),
        slice(columns.start + left, columns.start + right),
    )
    local_axis = axis - np.array([top, left, 0], dtype=np.int64)
    local = (bottom - top, right - left)
    swelling = lattice(
        derive_seed(seed, "land_bridge_swell"), length, BRIDGE_SWELL_PERIOD * location // PERMILLE
    )
    flare = swell(length, BRIDGE_FLARE_LENGTH * location // PERMILLE)
    low_body, high_body = (ground.width(value) for value in BRIDGE_BODY)
    wide = low_body + (high_body - low_body) * swelling // NOISE_SCALE
    reach = wide * (PERMILLE + BRIDGE_FLARE * flare // NOISE_SCALE) // PERMILLE
    spine = np.full(length + 1, BRIDGE_CORE * location // PERMILLE, dtype=np.int64)
    # Beside the edges of its room (the coast margin of the domain, not retained land, whose
    # shore is a real one) the body narrows to the room instead of being cut straight by it.
    margin_edge = ground.shore[window]
    if ground.outside_land is not None:
        margin_edge = margin_edge & ~ground.outside_land[window]
    room = euclidean_distance(margin_edge, 8 * (ground.width(BRIDGE_BODY[1]) + location))
    room_at = np.zeros(length + 1, dtype=np.int64)
    room_at[axis[:, 2]] = room[axis[:, 0], axis[:, 1]] // 8
    reach = np.maximum(spine, np.minimum(reach, room_at * 3 // 4))
    edge = _field(
        seed,
        "land_bridge_coast",
        shape=local,
        period=3 * location,
        octaves=4,
        persistence_permille=550,
    )
    every = max(1, location // 8)
    ridge = paint(local_axis, reach, edge, roughness_permille=BRIDGE_EDGE, every=every)
    ridge |= paint(local_axis, spine, edge, roughness_permille=0, every=every)
    ridge &= allowed[top:bottom, left:right]
    return box, ridge


def _bridge(
    ground: _BridgeGround, site: tuple[int, int], distance: int, seed: int
) -> Approach | None:
    """The land bridge from ``site`` to the continent, added to the land; None if none fits.

    It is valid when it touches the retained land along enough of its edge, joins the continent
    and covers the site itself; the caller tries the next site otherwise.
    """
    location = ground.settings.location_px
    height, width = ground.land.shape
    radius = 2 * distance + 12 * location
    window = (
        slice(max(0, site[0] - radius), min(height, site[0] + radius + 1)),
        slice(max(0, site[1] - radius), min(width, site[1] + radius + 1)),
    )
    here = (site[0] - window[0].start, site[1] - window[1].start)
    found = _bridge_axis(ground, window, here, seed)
    if found is None:
        return None
    axis, allowed = found
    # The axis lies in the window; the body is painted in a box round it.
    box, ridge = _bridge_ridge(ground, window, allowed, axis, seed)
    contact = int(np.count_nonzero(ridge & ground.interface[box]))
    joined = label_components((ground.land[box] | ridge).astype(np.int32))
    reaches = np.unique(joined[ridge & ground.continent[box]])
    origin = (box[0].start - window[0].start, box[1].start - window[1].start)
    if (
        contact < max(8, location // 2)
        or reaches.size == 0
        or not ridge[here[0] - origin[0], here[1] - origin[1]]
    ):
        return None
    fresh = ridge & ~ground.land[box]
    ground.land[box] |= ridge
    if ground.whole is not None and ground.open_water is not None:
        floor = ground.settings.min_sea_cell_px
        shut, reaching = _sea_state(
            ground.whole, ground.land, ground.shore, ground.open_water, floor
        )
        if shut > ground.seas[0] or (ground.keep_seas and reaching > ground.seas[1]):
            ground.land[box] &= ~fresh
            return None
    ground.shore[box] &= ~ridge
    path = np.zeros(ridge.shape, dtype=bool)
    path[axis[:, 0] - origin[0], axis[:, 1] - origin[1]] = True
    return Approach(box, path, site)


def _link_cells(labels: NDArray[np.int32], approaches: tuple[Approach, ...]) -> NDArray[np.int64]:
    return np.unique(
        np.concatenate([np.empty(0, dtype=np.int32), *(labels[a.box][a.path] for a in approaches)])
    ).astype(np.int64)


def _ocean_islands(
    land: NDArray[np.bool_],
    domain: NDArray[np.bool_],
    shore: NDArray[np.bool_],
    sites: Sequence[tuple[int, int, int]],
    seed: int,
) -> None:
    """Raise irregular grouped islands within the reserved Pacific water windows."""
    for number, (row, col, step) in enumerate(sites):
        if not domain[row, col] or shore[row, col]:
            continue
        radius = 6 * step
        box = (
            slice(max(0, row - radius), min(len(land), row + radius + 1)),
            slice(max(0, col - radius), min(land.shape[1], col + radius + 1)),
        )
        y, x = np.ogrid[
            box[0].start - row : box[0].stop - row, box[1].start - col : box[1].stop - col
        ]
        key = derive_seed(seed, "pacific_island_group", str(number))
        tilt = 1 if key & 1 else -1
        outline = _field(
            key,
            "island_coasts",
            shape=land[box].shape,
            period=step * 3,
            octaves=4,
            persistence_permille=550,
        )
        raised = np.zeros(outline.shape, dtype=bool)
        for dy, dx, size in (
            (0, 0, 2 * step),
            (tilt * 2 * step, 3 * step, step),
            (-tilt * step, -3 * step, step),
        ):
            distance = (y - dy) ** 2 + (x - dx) ** 2
            raised |= distance * NOISE_SCALE < size**2 * (NOISE_SCALE + outline)
        land[box] |= raised & domain[box] & ~shore[box]


def _regional_approaches(  # noqa: PLR0913 - coastal construction inputs.
    land: NDArray[np.bool_],
    ocean: NDArray[np.bool_],
    domain: NDArray[np.bool_],
    shore: NDArray[np.bool_],
    *,
    interface: NDArray[np.bool_] | None,
    strait: NDArray[np.uint8] | None,
    outside_land: NDArray[np.bool_] | None,
    settings: NewWorldSettings,
    seed: int,
) -> tuple[tuple[Approach, ...], tuple[int, int] | None]:
    links: list[Approach] = []
    if interface is not None:
        approach = _land_approach(
            land,
            domain,
            shore,
            interface,
            outside_land=outside_land,
            settings=settings,
            seed=seed,
            whole=domain,
        )
        if approach is None:
            message = "The African canvas has no continuous approach to a passable Asian location"
            raise ValueError(message)
        links.append(approach)
    landing = None
    if strait is not None:
        reserved_sea = strait == 1
        shore |= reserved_sea
        approach = _land_approach(
            land,
            domain & ~reserved_sea,
            shore,
            strait == STRAIT_LANDING,
            outside_land=outside_land,
            settings=settings,
            seed=derive_seed(seed, "mediterranean_approach"),
            scale=BRIDGE_LANDING_SCALE,
            whole=domain,
            keep_seas=True,
        )
        if approach is not None:
            links.append(approach)
            landing = approach.point
    if links:
        ocean &= ~land
    return tuple(links), landing


def stray_strait(
    domain: NDArray[np.bool_],
    land: NDArray[np.bool_],
    *,
    shore: NDArray[np.bool_],
    open_shore: NDArray[np.bool_],
) -> NDArray[np.bool_] | None:
    """Shortest path from a sea that land cuts off from open water to open water.

    Water around a hole in the domain (a protected island or sea) counts as sea, so no sea
    zone and no protected coast may be cut off. None when every sea that touches ``shore``
    reaches ``open_shore``, or when no path through the domain exists.
    """
    water, parts, open_parts, stray = _strays(domain, land, shore, open_shore)
    if not stray.size:
        return None
    path = _path(water & (parts == stray[0]), water & np.isin(parts, open_parts), domain)
    return path if np.any(path) else None


def _strays(
    domain: NDArray[np.bool_],
    land: NDArray[np.bool_],
    shore: NDArray[np.bool_],
    open_shore: NDArray[np.bool_],
) -> tuple[NDArray[np.bool_], NDArray[np.int32], NDArray[np.int32], NDArray[np.int32]]:
    """The water, its parts, the parts that reach ``open_shore`` and those that touch ``shore``
    without reaching it: the seas that land has cut off from open water."""
    coded = np.where(domain, land.astype(np.int32), OUTSIDE).astype(np.int32)
    parts = label_components(coded)
    water = domain & ~land
    open_parts = np.unique(parts[water & open_shore])
    return water, parts, open_parts, np.setdiff1d(np.unique(parts[water & shore]), open_parts)


def _sea_state(
    whole: NDArray[np.bool_],
    land: NDArray[np.bool_],
    shore: NDArray[np.bool_],
    open_water: NDArray[np.bool_],
    floor: int,
) -> tuple[int, int]:
    """How many seas land has cut off from open water, and how many pieces of at least ``floor``
    pixels touch it."""
    water, parts, open_parts, stray = _strays(whole, land, shore, open_water)
    del water
    sizes = np.bincount(parts.ravel(), minlength=int(parts.max()) + 1)
    return len(stray), int(np.count_nonzero(sizes[open_parts] >= floor))


def _touching_open_sea(
    domain: NDArray[np.bool_], outside_land: NDArray[np.bool_] | None
) -> NDArray[np.bool_]:
    """The pixels that touch the open sea beyond ``domain`` (:func:`open_sea`), and its own."""
    sea = open_sea(domain, outside_land=outside_land)
    touching = sea.copy()
    touching[1:] |= sea[:-1]
    touching[:-1] |= sea[1:]
    touching[:, 1:] |= sea[:, :-1]
    touching[:, :-1] |= sea[:, 1:]
    return touching


def _interior_points(
    labels: NDArray[np.int32], count: int, land: NDArray[np.bool_]
) -> NDArray[np.int64]:
    """Per cell, the first pixel (raster order) with the best interior score.

    Water cells take the pixel farthest from the cell boundary. Land cells (``land`` per
    cell) hold city models, which are square and can reach past a near shore, so their
    score is ``min(2 * d_border, d_shore)`` in octagonal distance, ties going to the
    larger ``d_border``: the point moves inland until it is twice as far from water as
    from the cell's other borders. The kernel is Rust (ADR 0005), its NumPy specification
    is ``tests/reference/points.py``.
    """
    del count
    return _native.interior_points(
        np.ascontiguousarray(labels, dtype=np.int32),
        np.ascontiguousarray(land, dtype=np.bool_),
        INTERIOR_LIMIT,
        SHORE_LIMIT,
    )


def _absorb_orphans(
    labels: NDArray[np.int32], orphan: NDArray[np.bool_], kind: NDArray[np.int64]
) -> NDArray[np.bool_]:
    """Give orphan pixels the label of a non-orphan 4-neighbour of the same class.

    Works inwards from the edges of orphan patches, N, W, E, S first, touching only
    orphan pixels; returns the pixels that found no such neighbour.
    """
    height, width = labels.shape
    flat = labels.reshape(-1)
    is_orphan = orphan.reshape(-1).copy()
    pending = np.flatnonzero(is_orphan)
    for _ in range(WOBBLE_PASSES):
        if not pending.size:
            break
        for offset in (-width, -1, 1, width):
            column = pending % width
            if offset == -width:
                inside = pending >= width
            elif offset == width:
                inside = pending < (height - 1) * width
            elif offset == -1:
                inside = column != 0
            else:
                inside = column != width - 1
            here = pending[inside & is_orphan[pending]]
            there = here + offset
            ok = (
                ~is_orphan[there]
                & (flat[there] >= 0)
                & (kind[np.maximum(flat[there], 0)] == kind[np.maximum(flat[here], 0)])
            )
            flat[here[ok]] = flat[there[ok]]
            is_orphan[here[ok]] = False
        pending = pending[is_orphan[pending]]
    return is_orphan.reshape(height, width)


def wobble_borders(  # noqa: PLR0913 - the cells, their classes, the seed and what stays.
    labels: NDArray[np.int32],
    kinds: list[CellClass],
    seed: int,
    *,
    fixed_sea: bool = False,
    fixed: NDArray[np.bool_] | None = None,
    scale: NDArray[np.int64] | None = None,
) -> NDArray[np.int32]:
    """Bend straight cell borders into curves; classes, coasts and cell count are kept.

    Each pixel takes the label found a smooth noise displacement away when that pixel
    has the same class. Pieces cut off from their cell's largest part are absorbed by a
    neighbouring cell of the same class. A cell that would vanish or split gets its
    original pixels back, and so do the pixels it took, until every cell is one piece;
    one bad cell no longer undoes the wobble of the whole world (C71). Pixels in ``fixed``
    (beside the rivers that are borders) keep their label. With ``scale`` (epoch 64, the
    seed spacing of every ``watersheds.DENSITY_STEP`` block in permille of the uniform one) a
    land pixel is displaced in proportion to a spacing below the uniform one, so the smallest
    cells bend as much as the others for their width instead of losing pieces to them.
    """
    shape = (int(labels.shape[0]), int(labels.shape[1]))
    kind = np.array([list(CellClass).index(value) for value in kinds], dtype=np.int64)
    offsets = _wobble_offsets(labels, kind, seed, scale)
    rows = np.clip(np.arange(shape[0])[:, np.newaxis] + offsets[0], 0, shape[0] - 1)
    columns = np.clip(np.arange(shape[1])[np.newaxis, :] + offsets[1], 0, shape[1] - 1)
    source = labels[rows, columns]
    del rows, columns, offsets
    valid = (labels >= 0) & (source >= 0)
    same = valid & (kind[np.maximum(source, 0)] == kind[np.maximum(labels, 0)])
    if fixed_sea:
        sea_kind = list(CellClass).index(CellClass.SEA)
        for start in range(0, shape[0], STRIP_ROWS):
            rows = slice(start, min(shape[0], start + STRIP_ROWS))
            same[rows] &= kind[np.maximum(labels[rows], 0)] != sea_kind
    if fixed is not None:
        same &= ~fixed
    moved = np.where(same, source, labels).astype(np.int32)
    del source, same, valid
    counts = np.bincount(moved[moved >= 0], minlength=len(kinds))
    vanished = np.flatnonzero(counts == 0)
    if vanished.size:
        restore = np.isin(labels, vanished)
        moved[restore] = labels[restore]
    parts = label_components(moved)
    owner = np.full(int(parts.max()) + 1, -1, dtype=np.int64)
    owner[parts.ravel()] = moved.ravel()
    sizes = np.bincount(parts.ravel())
    best = np.full(len(kinds), -1, dtype=np.int64)
    order = np.lexsort((np.arange(sizes.size), -sizes))
    for part in order.tolist():
        cell = int(owner[part])
        if cell >= 0 and best[cell] < 0:
            best[cell] = part
    if np.any(best < 0):
        return labels
    keep = np.zeros(sizes.size, dtype=bool)
    keep[best] = True
    orphan = (moved >= 0) & ~keep[parts]
    del parts
    left = _absorb_orphans(moved, orphan, kind)
    moved[left] = labels[left]
    for _ in range(WOBBLE_REPAIRS):
        check = label_components(moved)
        pieces = np.zeros(int(check.max()) + 1, dtype=np.int64) - 1
        pieces[check.ravel()] = moved.ravel()
        per_cell = np.bincount(pieces[pieces >= 0], minlength=len(kinds))
        bad = np.flatnonzero(per_cell != 1)
        if not bad.size:
            return moved
        revert = np.isin(labels, bad) | np.isin(moved, bad)
        moved[revert] = labels[revert]
    return labels


def _wobble_offsets(
    labels: NDArray[np.int32], kind: NDArray[np.int64], seed: int, scale: NDArray[np.int64] | None
) -> list[NDArray[np.int64]]:
    """The row and column displacement of every pixel (``wobble_borders``), in pixels."""
    shape = (int(labels.shape[0]), int(labels.shape[1]))
    noises = [
        warped_noise(
            derive_seed(seed, stream), shape, step=4, period=WOBBLE_PERIOD, octaves=3, warp_px=0
        )
        for stream in ("nw_wobble_rows", "nw_wobble_columns")
    ]
    if scale is None:
        return [noise * WOBBLE_PX // NOISE_SCALE for noise in noises]
    _scale_wobble(noises, labels, kind, scale)
    return noises


def _scale_wobble(
    offsets: list[NDArray[np.int64]],
    labels: NDArray[np.int32],
    kind: NDArray[np.int64],
    scale: NDArray[np.int64],
) -> None:
    """Turn the wobble noise ``offsets`` into pixels in place, a strip at a time: ``WOBBLE_PX``
    at the noise's full scale, times the ``scale`` of the block (permille, at most one) for the
    pixels of land cells."""
    land = list(CellClass).index(CellClass.LAND)
    width = int(labels.shape[1])
    block_columns = np.minimum(np.arange(width) // DENSITY_STEP, int(scale.shape[1]) - 1)
    capped = np.minimum(scale, PERMILLE)
    for start in range(0, int(labels.shape[0]), STRIP_ROWS):
        window = slice(start, min(int(labels.shape[0]), start + STRIP_ROWS))
        block_rows = np.minimum(
            np.arange(window.start, window.stop) // DENSITY_STEP, int(scale.shape[0]) - 1
        )
        cell = labels[window]
        on_land = (cell >= 0) & (kind[np.maximum(cell, 0)] == land)
        factor = np.where(on_land, capped[block_rows][:, block_columns], PERMILLE)
        for offset in offsets:
            offset[window] = offset[window] * WOBBLE_PX * factor // (NOISE_SCALE * PERMILLE)


@measured
def _cells(mask: NDArray[np.bool_], *, key: int, spacing: int, smallest: int) -> NDArray[np.int32]:
    """Grow land cells, with larger seed spacing toward both polar edges."""
    sites = seed_sites(key, mask, spacing)
    height = mask.shape[0]
    band = min(height // 4, 6 * spacing)
    if band:
        polar = np.zeros(mask.shape, dtype=np.bool_)
        polar[:band] = mask[:band]
        polar[-band:] = mask[-band:]
        coarse = seed_sites(key, polar, 3 * spacing)
        sites[polar] = coarse[polar]
        # The two seed sets have independent numbering; make every seed unique.
        positions = np.flatnonzero(sites >= 0)
        sites.ravel()[positions] = np.arange(len(positions), dtype=np.int32)
    return merge_small(grow_regions(mask, sites), smallest)


@measured
def _river_cells(  # noqa: PLR0913 - the land, lakes and relief, the seed, settings and seam.
    land: NDArray[np.bool_],
    lakes: NDArray[np.bool_],
    relief: NDArray[np.int32],
    *,
    seed: int,
    settings: NewWorldSettings,
    seam: int | None,
    sizes: SizeModel | None,
    map_rows: tuple[int, int] | None = None,
    hints: ReliefHints | None = None,
    spread: NDArray[np.int16] | None = None,
    algorithm: int = epoch.CURRENT,
    outside_land: NDArray[np.bool_] | None = None,
    contact: ContactBlend | None = None,
) -> tuple[NDArray[np.int32], NDArray[np.bool_], DrainagePlan, NDArray[np.int64]]:
    """Land cells grown after the rivers (epoch 64, ``epoch.RIVERS_FIRST``), the river pixels
    that are their borders, the drainage plan the rivers run down and the seed spacing of every
    ``watersheds.DENSITY_STEP`` block (``watersheds.cell_spacing_grid``): the relief's drainage is
    planned (``rnw.watersheds``), the relief is worn down along it in place (``epoch.BASINS``,
    ``rnw.basins``; ``hints`` keep painted mountains) and its hill country roughened by
    ``spread`` outside the rivers' valley floors (``epoch.ROUGH_HILLS``), and the rain of the
    relief runs down the plan; the seeds are spaced by the vanilla sizes of the land's classes
    (``sizes``), the polar bands keep three times the spacing, and the larger rivers are walls
    the cells grow up to. The seeds are spaced on the height the decals will show
    (``epoch.ROUGH_HILLS``)."""
    if sizes is None:
        message = (
            "Cells of this epoch are spaced by the game's locations; the size model is missing"
        )
        raise ValueError(message)
    row0, map_height = (0, land.shape[0]) if map_rows is None else map_rows
    try:
        plan = plan_drainage(
            land, relief, lakes=lakes, seam=seam, seed=seed, outside_land=outside_land
        )
        if algorithm >= epoch.BASINS:
            shape_relief(relief, land, plan, seed=seed, hints=hints, spread=spread)
        if contact is not None:
            contact.keep_shore(relief)
        climate = domain_climate(land, lakes, relief, row0=row0, outside_land=outside_land)
        rivers = domain_rivers(
            land, plan, lakes=lakes, rain=climate.rain, seed=seed, outside_land=outside_land
        )
    except RiverGenerationError as error:
        raise ValueError(str(error)) from error
    walls = border_rivers(rivers)
    del rivers
    spacing = settings.location_px
    band = min(map_height // 4, 6 * spacing)
    polar = (max(0, band - row0), max(0, band - (map_height - row0 - land.shape[0])))
    # The sizes are voted on the height the decals will show (epoch 64, ``epoch.ROUGH_HILLS``), as
    # the ground of the cells will be (``eu5_terrain.surface_heights``).
    surface = land_surface(land, relief, seed=seed) if algorithm >= epoch.ROUGH_HILLS else relief
    sea = ~(land | lakes)
    if outside_land is not None:
        sea &= ~outside_land
    # The ground is voted once over the land, a block at a time, and every cell takes that of the
    # land it covers (``eu5_biomes.ground_field``), the first cells as the final ones.
    ground = ground_field(sizes, land, surface, climate)
    first = river_cells(
        land,
        walls,
        key=derive_seed(seed, "nw_land_sites_first"),
        spacing=spacing,
        grid=spacing_grid(
            land,
            surface,
            climate,
            sea=sea,
            polar_rows=polar,
            sizes=sizes,
            ground=ground,
            spacing=spacing,
        ),
        smallest=settings.min_cell_px,
    )
    # The first cells are voted as the final ones will be; each sizes the land it lies on by its
    # own class, ground and coast (``watersheds.cell_spacing_grid``).
    grid = cell_spacing_grid(
        first,
        surface,
        climate,
        sea=sea,
        polar_rows=polar,
        sizes=sizes,
        ground=ground,
        key=derive_seed(seed, "nw_land_density"),
        spacing=spacing,
    )
    del first
    # The final cells beside the sea grow as large as their plan at the density of the inland
    # cells round them, moved by vanilla's offset of their ground on the coast, read on the cells
    # as they grow; the inland ones within a band of theirs (``watersheds._density_gains``).
    cells = river_cells(
        land,
        walls,
        key=derive_seed(seed, "nw_land_sites"),
        spacing=spacing,
        grid=grid,
        smallest=settings.min_cell_px,
        coast=partial(coastal_offsets, sizes, height=surface, grid=climate, sea=sea, ground=ground),
        limit=MAX_LAND_PX if algorithm >= epoch.BOUNDED_CELLS else None,
        edges=(row0 == 0, row0 + land.shape[0] == map_height),
    )
    del climate, surface, sea, ground
    return cells, walls, plan, grid


# Pixels this near a border river (within the wobble's reach and its diagonal) keep their cell.
RIVER_HOLD: Final[int] = WOBBLE_PX * 3 // 2

# A sea cell thinner than a fifth of the sea-cell spacing (twice its area over its perimeter), whose
# perimeter is at least 40 % other sea cells, is a needle or a crescent between cells and joins the
# neighbour it shares most with. A strait, bordered by land, stays.
SLIVER_DIVISOR: Final[int] = 5
SLIVER_PERMILLE: Final[int] = 400


def _sea_cells(  # noqa: PLR0913 - partition inputs and the physical replacement domain.
    ocean: NDArray[np.bool_],
    *,
    key: int,
    spacing: int,
    smallest: int,
    bands: NDArray[np.bool_] | None,
    domain: NDArray[np.bool_] | None = None,
) -> NDArray[np.int32]:
    """Partition actual ocean routes separately from ordinary water."""

    def sea_part(mask: NDArray[np.bool_]) -> NDArray[np.int32]:
        sites = seed_sites(key, mask, spacing)
        nearest = _native.sea_voronoi(np.ascontiguousarray(mask), sites)
        # A coast or a current band may cut a Voronoi cell into separate pieces.
        # They are distinct cells before small connected pieces are merged.
        parts = label_components(nearest)
        return merge_small(np.where(mask, parts, -1).astype(np.int32), smallest)

    if bands is None:
        return merge_slivers(
            sea_part(ocean), spacing / SLIVER_DIVISOR, SLIVER_PERMILLE, _world_edge(ocean, domain)
        )
    if bands.shape != ocean.shape:
        message = "Current bands do not fit the world"
        raise ValueError(message)
    # A crossing is a chain of ordinary cells: the water is partitioned once, the sites of the
    # ordinary cells keep clear of each crossing's centre line, and the crossing's own sites lie
    # along it. Its cells then have the same irregular borders as any other cell, not the ruled
    # edges of a band that was cut out of the water and partitioned alone.
    paths = corridor_paths(ocean, bands, spacing, domain=domain)
    sites = seed_sites(key, ocean, spacing)
    rows, columns = np.nonzero(sites >= 0)
    clear = clear_of_corridors(
        rows.astype(np.int64),
        columns.astype(np.int64),
        paths,
        spacing * CLEAR_PERMILLE / PERMILLE,
    )
    chain_rows, chain_columns = corridor_sites(paths, ocean, spacing, key)
    after = int(sites.max()) + 1
    sites[rows[~clear], columns[~clear]] = -1
    sites[chain_rows, chain_columns] = np.arange(after, after + chain_rows.size, dtype=np.int32)
    del rows, columns, clear
    nearest = _native.sea_voronoi(np.ascontiguousarray(ocean), sites)
    del sites
    parts = label_components(nearest)
    del nearest
    cells = merge_small(np.where(ocean, parts, -1).astype(np.int32), smallest)
    return merge_slivers(
        cells, spacing / SLIVER_DIVISOR, SLIVER_PERMILLE, _world_edge(ocean, domain)
    )


def _world_edge(
    ocean: NDArray[np.bool_], domain: NDArray[np.bool_] | None
) -> NDArray[np.bool_] | None:
    """The ocean pixels that touch the outside of the generated domain (None without one)."""
    if domain is None:
        return None
    inner = domain.copy()
    inner[1:] &= domain[:-1]
    inner[:-1] &= domain[1:]
    inner[:, 1:] &= domain[:, :-1]
    inner[:, :-1] &= domain[:, 1:]
    return ocean & ~inner


def _first_land(  # noqa: PLR0913, PLR0917 - the domain, seed, settings and the three ways to have land.
    domain: NDArray[np.bool_],
    seed: int,
    settings: NewWorldSettings,
    drawn: NDArray[np.bool_] | None,
    stage: tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_]] | None,
    template: NDArray[np.bool_] | None = None,
    lakes: NDArray[np.bool_] | None = None,
    *,
    outside_land: NDArray[np.bool_] | None = None,
) -> tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_]]:
    """Land, ocean and lake masks of the domain: drawn, kept from a sketch or made now."""
    if outside_land is not None and (
        outside_land.shape != domain.shape or np.any(outside_land & domain)
    ):
        message = "Retained land must fit the generation window and lie outside its domain"
        raise ValueError(message)
    if drawn is None and lakes is not None:
        message = "Marked lakes belong to a drawn land, and none was given"
        raise ValueError(message)
    if drawn is not None:
        if settings.landform:
            message = "The Wall cannot be combined with a drawn land mask"
            raise LandMaskError(message)
        if settings.template_permille:
            message = "Omerika cannot be combined with a drawn land mask"
            raise LandMaskError(message)
        return _land_from_mask(domain, drawn, settings, lakes)
    if stage is not None:
        if any(mask.shape != domain.shape for mask in stage):
            message = "The kept land stage does not fit the domain"
            raise ValueError(message)
        return stage
    land, ocean, lakes, _ = land_stage(domain, seed, settings, template, outside_land=outside_land)
    return land, ocean, lakes


@dataclass(frozen=True, slots=True)
class FinishedLand:
    """The land of a domain with its coasts finished, before any cell, relief or river.

    ``whole`` is the domain as given and ``domain`` what is left of it once the island groups
    it covers have moved (``moves``, one per group) and become its holes. ``approaches`` are the
    land connection and the strait crossing made toward retained land, and ``landing`` where a
    strait lands; none without them.
    """

    whole: NDArray[np.bool_]
    domain: NDArray[np.bool_]
    land: NDArray[np.bool_]
    ocean: NDArray[np.bool_]
    lakes: NDArray[np.bool_]
    moves: tuple[tuple[int, int], ...]
    approaches: tuple[Approach, ...]
    landing: tuple[int, int] | None


def finished_land(  # noqa: PLR0913 - the coastal inputs of ``generate_new_world``.
    domain: NDArray[np.bool_],
    *,
    seed: int,
    settings: NewWorldSettings,
    drawn: NDArray[np.bool_] | None = None,
    groups: Sequence[Footprint] = (),
    stage: tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_]] | None = None,
    template: NDArray[np.bool_] | None = None,
    lakes_drawn: NDArray[np.bool_] | None = None,
    outside_land: NDArray[np.bool_] | None = None,
    land_interface: NDArray[np.bool_] | None = None,
    strait: NDArray[np.uint8] | None = None,
    island_sites: tuple[tuple[int, int, int], ...] = (),
    reserve_north: int = 0,
    on_placed: Callable[[tuple[tuple[int, int], ...]], None] | None = None,
) -> FinishedLand:
    """The land, sea and lakes of ``generate_new_world`` with the same inputs, and no more: the
    first land, the island groups placed, the ocean islands, the regional approaches, the
    narrowed straits and the classified coasts. A sketch of several continents draws exactly
    this, so it shows the coasts the world will have, but for the few pixels the cells' borders
    move them."""
    land_domain = domain
    if reserve_north:
        land_domain = domain.copy()
        land_domain[:reserve_north] = False
    land, ocean, lakes = _first_land(
        land_domain, seed, settings, drawn, stage, template, lakes_drawn, outside_land=outside_land
    )
    del land_domain
    whole = domain
    # Retained ocean islands stay in the open ocean, never in a new inland sea.
    placement_ocean = (
        _ocean(domain, land | lakes, _off_limits(domain, settings))[1] if groups else ocean
    )
    moves = place(whole, land, placement_ocean, groups, margin=settings.coast_margin_px)
    del placement_ocean
    if on_placed is not None:
        on_placed(tuple((int(row), int(column)) for row, column in moves))
    domain = carve(whole, groups, moves)
    land &= domain
    ocean &= domain
    lakes &= domain
    shore = _off_limits(domain, settings, outside_land)
    shore[:reserve_north] = True
    _ocean_islands(land, domain, shore, island_sites, seed)
    if island_sites:
        ocean &= ~land
    approaches, landing = _regional_approaches(
        land,
        ocean,
        domain,
        shore,
        interface=land_interface,
        strait=strait,
        outside_land=outside_land,
        settings=settings,
        seed=seed,
    )
    land, ocean, _ = pinch(land, ocean, shore)
    # Narrowing can detach a small pocket from the ocean. Classify the finished coasts,
    # including existing lakes, before any cell, port or relief field gives it an identity.
    land, ocean, lakes = _classify(domain, land, shore, settings, lakes_drawn)
    del shore
    if settings.template_permille:
        omerika.check_joined(land, _template(domain, seed, settings, template))
    return FinishedLand(whole, domain, land, ocean, lakes, moves, approaches, landing)


@measured
def generate_new_world(  # noqa: PLR0913, PLR0915 - staged world construction.
    domain: NDArray[np.bool_],
    *,
    seed: int,
    settings: NewWorldSettings,
    drawn: NDArray[np.bool_] | None = None,
    sea_bands: NDArray[np.bool_] | None = None,
    groups: Sequence[Footprint] = (),
    stage: tuple[NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_]] | None = None,
    template: NDArray[np.bool_] | None = None,
    lakes_drawn: NDArray[np.bool_] | None = None,
    hints: ReliefHints | None = None,
    algorithm: int = epoch.CURRENT,
    seam: int | None = None,
    sizes: SizeModel | None = None,
    map_rows: tuple[int, int] | None = None,
    outside_land: NDArray[np.bool_] | None = None,
    land_interface: NDArray[np.bool_] | None = None,
    strait: NDArray[np.uint8] | None = None,
    contact_terrain: ContactTerrain | None = None,
    island_sites: tuple[tuple[int, int, int], ...] = (),
    reserve_north: int = 0,
    on_placed: Callable[[tuple[tuple[int, int], ...]], None] | None = None,
) -> NewWorld:
    """Fill ``domain`` with generated land, sea and lake cells.

    With ``drawn`` (a land mask fitted to the domain, ``rnw.landmask``) the land is the
    drawing's and the generator makes the rest on it. A drawing may also mark lakes
    (``lakes_drawn``, which stay lakes) and the relief it asks for (``hints``: painted
    mountains, highlands and lowlands, ``rnw.relief``).

    ``stage`` is the land, ocean and lake masks that ``land_stage`` made of this domain, seed
    and settings before (a sketched continent, ``rnw.landcache``), so they are not made again;
    the arrays are consumed.

    ``groups`` are island groups that the domain covers. The land is made on the whole domain; a
    group that it leaves room stays, and one it touches moves to free ocean (``rnw.islands``).
    The groups are then holes of the domain, and the cells are made on what is left.
    ``NewWorld.moves`` has the translation of each group. ``on_placed`` receives the same
    immutable translations as soon as placement is fixed, before relief and cell work.

    Cells belong to this continuous canvas. Projecting it across the game's raster
    boundary must retain each cell's identity on both sides, just as vanilla does.
    ``map_rows`` is the first global row and the height of the global raster when
    the domain is vertically cropped. Latitude and the polar bands use the map's rows.
    ``outside_land`` marks retained land against which an ordinary coastline may become
    an inland contact. The routing and river mouths treat it as a closed boundary.

    The land cells, the sea cells and the relief depend only on the masks, so they are
    built beside each other when the machine has the cores and the memory for it.

    ``template`` is the installed game's Americas on the domain (``Canvas.template``), which the
    land of Omerika is made on (``settings.template_permille``, ``rnw.omerika``); the finished land
    must still join the landmasses that the template joins.

    ``algorithm`` is the epoch the world is made by. From ``epoch.CORDILLERAS`` the relief raises
    the active coasts' cordilleras; from ``epoch.RIVERS_FIRST`` the land cells wait for the relief:
    its rivers are drawn first (``rnw.watersheds``, in watershed domains split at ``seam``, the
    domain column the game's map starts at), the cells are seeded as far apart as vanilla's
    locations of the class the climate vote will choose (``sizes``, read from the game:
    ``eu5_biomes.size_model``; required from that epoch) and grown with the larger rivers as
    borders, and the wobble leaves those borders on their rivers.
    """
    row0, map_height = (0, domain.shape[0]) if map_rows is None else map_rows
    if not 0 <= row0 < row0 + domain.shape[0] <= map_height:
        message = "The generation domain rows are outside the map"
        raise ValueError(message)
    coasts = finished_land(
        domain,
        seed=seed,
        settings=settings,
        drawn=drawn,
        groups=groups,
        stage=stage,
        template=template,
        lakes_drawn=lakes_drawn,
        outside_land=outside_land,
        land_interface=land_interface,
        strait=strait,
        island_sites=island_sites,
        reserve_north=reserve_north,
        on_placed=on_placed,
    )
    whole, domain, moves = coasts.whole, coasts.domain, coasts.moves
    land, ocean, lakes = coasts.land, coasts.ocean, coasts.lakes
    approaches, landing = coasts.approaches, coasts.landing
    del coasts
    contact = (
        contact_terrain.blend(land, outside_land)
        if contact_terrain is not None and outside_land is not None
        else None
    )
    rivers_first = algorithm >= epoch.RIVERS_FIRST
    walls: NDArray[np.bool_] | None = None
    drainage: DrainagePlan | None = None
    cell_spacing: NDArray[np.int64] | None = None
    with Stages(stage_workers()) as stages:
        land_job = (
            None
            if rivers_first
            else stages.submit(
                "land cells",
                partial(
                    _cells,
                    land,
                    key=derive_seed(seed, "nw_land_sites"),
                    spacing=settings.location_px,
                    smallest=settings.min_cell_px,
                ),
            )
        )
        sea_job = stages.submit(
            "sea cells",
            partial(
                _sea_cells,
                ocean,
                key=derive_seed(seed, "nw_sea_sites"),
                spacing=settings.sea_zone_px,
                smallest=settings.min_sea_cell_px,
                bands=sea_bands,
                domain=domain,
            ),
        )
        # The hill country roughens once the drainage is planned (epoch 64, ``epoch.ROUGH_HILLS``).
        spread = (
            np.zeros(land.shape, dtype=np.int16)
            if rivers_first and algorithm >= epoch.ROUGH_HILLS
            else None
        )
        relief_job = stages.submit(
            "relief",
            partial(
                generate_relief,
                land,
                seed=seed,
                lakes=lakes,
                hints=hints,
                margins=algorithm >= epoch.CORDILLERAS,
                spread=spread,
                tablelands=algorithm >= epoch.TABLELANDS,
                outside_land=outside_land,
            ),
        )
        lake_cells = np.where(lakes, label_components(np.where(lakes, 1, 0).astype(np.int32)), -1)
        relief = relief_job.result()
        if contact is not None:
            contact.condition(relief)
        if land_job is None:
            if settings.landform:
                wall.add_relief(relief, land, whole, seed, settings)
            land_cells, walls, drainage, cell_spacing = stages.submit(
                "land cells",
                partial(
                    _river_cells,
                    land,
                    lakes,
                    relief,
                    seed=seed,
                    settings=settings,
                    seam=seam,
                    sizes=sizes,
                    map_rows=(row0, map_height),
                    hints=hints,
                    spread=spread,
                    algorithm=algorithm,
                    outside_land=outside_land,
                    contact=contact,
                ),
            ).result()
            del spread
        else:
            land_cells = land_job.result()
        sea_cells = sea_job.result()
    if settings.landform and not rivers_first:
        wall.add_relief(relief, land, whole, seed, settings)
    del ocean, lakes, land
    labels = np.full(domain.shape, -1, dtype=np.int32)
    kinds: list[CellClass] = []
    for kind, part in (
        (CellClass.LAND, land_cells),
        (CellClass.SEA, sea_cells),
        (CellClass.LAKE, lake_cells.astype(np.int32)),
    ):
        numbered = renumber(part)
        present = int(numbered.max()) + 1 if np.any(numbered >= 0) else 0
        labels[numbered >= 0] = numbered[numbered >= 0] + len(kinds)
        kinds.extend([kind] * present)
        del numbered
    del land_cells, sea_cells, lake_cells
    fixed = None
    if walls is not None:
        fixed = euclidean_distance(walls, RIVER_HOLD + 1) <= RIVER_HOLD * 8
        del walls
    labels = wobble_borders(
        labels, kinds, seed, fixed_sea=sea_bands is not None, fixed=fixed, scale=cell_spacing
    )
    del cell_spacing
    del fixed
    count = len(kinds)
    pixels, _, _, total, _ = _cell_sums(labels, relief, count)
    mean_relief = total // np.maximum(1, pixels)
    land_ids = [index for index, kind in enumerate(kinds) if kind is CellClass.LAND]
    linked = _link_cells(labels, approaches)
    wasteland = len(land_ids) * settings.wasteland_permille // PERMILLE
    protected = set(linked.tolist())
    ranked = sorted(
        (index for index in land_ids if index not in protected),
        key=lambda index: (-int(mean_relief[index]), index),
    )
    for index in ranked[:wasteland]:
        kinds[index] = CellClass.WASTELAND
    # Every land location touching a polar map edge is impassable, including
    # drawn worlds and the Wall. The shelves remain playable.
    polar_edges = [
        edge
        for edge, at_pole in ((0, row0 == 0), (-1, row0 + labels.shape[0] == map_height))
        if at_pole
    ]
    polar = np.unique(labels[polar_edges, :])
    for index in polar.tolist():
        if index >= 0 and kinds[index] is CellClass.LAND:
            kinds[index] = CellClass.WASTELAND
    barrier = _wall_cells(labels, kinds, whole, seed, settings) if settings.landform else None
    world = derive_world(labels, tuple(kinds), relief)
    return replace(
        world,
        moves=np.array(moves, dtype=np.int64).reshape(-1, 2),
        drainage=drainage,
        land_link=linked,
        strait_landing=landing,
        **({} if barrier is None else {"barrier": barrier}),
    )


def _wall_cells(
    labels: NDArray[np.int32],
    kinds: list[CellClass],
    whole: NDArray[np.bool_],
    seed: int,
    settings: NewWorldSettings,
) -> NDArray[np.int64]:
    """The land cells the Wall's guaranteed core runs through, in ascending order.

    Without gaps every row of the core must lie on land, or the Wall lost its barrier.
    """
    middle = wall.spine(whole, seed, settings)
    along = labels[np.arange(len(middle)), middle]
    on_land = np.isin(along, [i for i, kind in enumerate(kinds) if kind in LAND_KINDS])
    if not settings.wall_allow_gaps and not on_land.all():
        message = "The Wall lost its continuous land barrier during cell construction"
        raise ValueError(message)
    return np.unique(along[on_land]).astype(np.int64)


def _cell_sums(
    labels: NDArray[np.int32], elevation: NDArray[np.int32], count: int
) -> tuple[NDArray[np.int64], ...]:
    """Pixels, row sum, column sum, elevation sum and elevation square sum per cell.

    The sums are exact 64-bit integers, added in parallel bands of rows, so the result does
    not depend on the band height. The kernel is Rust (ADR 0005); its NumPy specification is
    ``cell_sums`` of ``tests/reference/newworld.py``.
    """
    if elevation.dtype != np.int32 and elevation.size:
        low, high = int(elevation.min()), int(elevation.max())
        if low < np.iinfo(np.int32).min or high > np.iinfo(np.int32).max:
            message = f"Elevation {low}..{high} does not fit the 32-bit cell sums"
            raise ValueError(message)
    sums = _native.cell_sums(
        np.ascontiguousarray(labels, dtype=np.int32),
        np.ascontiguousarray(elevation, dtype=np.int32),
        count,
    )
    return tuple(sums[index] for index in range(5))


def derive_world(
    labels: NDArray[np.int32],
    kinds: tuple[CellClass, ...],
    elevation: NDArray[np.int32],
    *,
    wrap_x: bool = False,
) -> NewWorld:
    """Compute sizes, centres, interior points and contacts for a labelled world."""
    count = len(kinds)
    pixels, rows, columns, total, square_total = _cell_sums(labels, elevation, count)
    mean_elevation = total // np.maximum(1, pixels)
    square = square_total // np.maximum(1, pixels)
    variance = np.maximum(0, square - mean_elevation * mean_elevation)
    spread = np.floor(np.sqrt(variance.astype(np.float64))).astype(np.int64)
    centroids = np.stack([rows // np.maximum(1, pixels), columns // np.maximum(1, pixels)], axis=1)
    if wrap_x:
        _wrap_centres(labels, centroids, pixels)
    edges = tuple(
        (first, second)
        for first, second in unpack_pairs(adjacency_pairs(labels, wrap_x=wrap_x))
        if first >= 0 and second >= 0
    )
    return NewWorld(
        labels=labels,
        classes=kinds,
        elevation=elevation,
        pixels=pixels,
        centroids=centroids,
        interior=_interior_points(
            labels, count, np.array([kind in LAND_KINDS for kind in kinds], dtype=bool)
        ),
        mean_elevation=mean_elevation,
        spread=spread,
        edges=edges,
        wrap_x=wrap_x,
    )


def turned_to_sea(world: NewWorld, cells: Collection[int]) -> NewWorld:
    """``world`` with ``cells`` turned into sea: their relief is level, and their sizes, centres
    and interior points are those of water. Nothing else of the world changes."""
    kinds = list(world.classes)
    for cell in cells:
        kinds[cell] = CellClass.SEA
    elevation = world.elevation.copy()
    elevation[np.isin(world.labels, np.fromiter(cells, dtype=np.int32))] = 0
    drainage = world.drainage
    if drainage is not None:
        # The rivers keep their plan: what ran into the cells ends in them as at a mouth.
        dry = np.array([kind in {CellClass.LAND, CellClass.WASTELAND} for kind in kinds] + [False])[
            world.labels
        ]
        lakes = np.array([kind is CellClass.LAKE for kind in kinds] + [False])[world.labels]
        drainage = withdrawn_drainage(drainage, dry, lakes)
    return replace(
        derive_world(world.labels, tuple(kinds), elevation, wrap_x=world.wrap_x),
        moves=world.moves,
        barrier=world.barrier,
        land_link=world.land_link,
        strait_landing=world.strait_landing,
        drainage=drainage,
    )


def _wrap_centres(
    labels: NDArray[np.int32], centroids: NDArray[np.int64], pixels: NDArray[np.int64]
) -> None:
    """Measure spanning cells in the opposite frame so they do not centre mid-ocean."""
    linked = (labels[:, 0] >= 0) & (labels[:, 0] == labels[:, -1])
    keys = np.unique(labels[:, 0][linked])
    if not keys.size:
        return
    width = int(labels.shape[1])
    half = width // 2
    chosen = np.zeros(pixels.size + 1, dtype=bool)
    chosen[keys] = True
    sums = np.zeros(pixels.size, dtype=np.int64)
    for first in range(0, labels.shape[0], 256):
        rows = labels[first : first + 256]
        r, c = np.nonzero(chosen[rows])
        sums += np.bincount(rows[r, c], weights=(c + half) % width, minlength=pixels.size).astype(
            np.int64
        )
    centroids[keys, 1] = (sums[keys] // pixels[keys] - half) % width


def unported_cells(world: NewWorld, anchored: Collection[int] = ()) -> list[int]:
    """Land cells that reach no coast without crossing wasteland, lakes or the sea.

    EU5 logs a location as "isolated from all ports by impassable terrain" when walling
    wasteland leaves it no way to a port [V-GAME 1.4.2, C95]; every coastal land cell has
    a port, so the cells to find are the land components that touch no sea cell. A cell of
    ``anchored``, one that touches the passable land of a retained location, reaches that
    land's ports (the wasteland plan counts a land link the same way).
    """
    parent = list(range(len(world.classes)))

    def find(item: int) -> int:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    coastal: set[int] = set()
    for first, second in world.edges:
        kinds = (world.classes[first], world.classes[second])
        if kinds == (CellClass.LAND, CellClass.LAND):
            parent[find(first)] = find(second)
        elif kinds == (CellClass.LAND, CellClass.SEA):
            coastal.add(find(first))
        elif kinds == (CellClass.SEA, CellClass.LAND):
            coastal.add(find(second))
    coastal.update(find(item) for item in anchored if world.classes[item] is CellClass.LAND)
    reached = {find(item) for item in coastal}
    return [
        index
        for index, kind in enumerate(world.classes)
        if kind is CellClass.LAND and find(index) not in reached
    ]


def seal_pockets(world: NewWorld) -> NewWorld:
    """``world`` with its unported land turned into wasteland (mountains no port reaches)."""
    cells = unported_cells(world)
    if not cells:
        return world
    kinds = list(world.classes)
    for index in cells:
        kinds[index] = CellClass.WASTELAND
    return replace(world, classes=tuple(kinds))
