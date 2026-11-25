"""The area of the map that a New World fills, as a picture to draw land on (ADR 0010, G4).

Choosing the area reads and decodes the installed game's whole map (about twelve seconds), yet
the area depends only on the map's files, two settings and this code. So it is kept in the
land cache (``rnw.landcache``) under a key made from the files' fingerprints, read without
decoding anything; the second look at the area takes a fraction of a second, and so does the
template saved for a painter and the sheet the window's editor draws on.

Three layers are kept, at a quarter of the map's resolution: the area itself, the installed
game's own Americas inside it (a guide to draw round, or a land to start from) and the Old
World's island groups that the area covers (they stay where there is room and move to free
water when new land reaches them). They are cut from the player's installed game and stay on
the player's machine, as every picture of the game's map does (docs/legal.md).
"""

# NumPy stubs type array shapes and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import landcache
from rnw.continent_domains import CONTINENTS, retired_atlantic_islands
from rnw.eu5_map import input_fingerprints, load_map
from rnw.eu5_nw_export import TEMPLATES, CompositionInputs, retained_facts
from rnw.model import CellClass
from rnw.png import COLOR_GRAY, encode_png
from rnw.progress import run_stage
from rnw.settings import AMERICA

if TYPE_CHECKING:
    from collections.abc import Collection

    from numpy.typing import NDArray

    from rnw.continent_domains import Domain
    from rnw.eu5_canvas import Canvas
    from rnw.eu5_map import Eu5Map
    from rnw.settings import Settings


# The area is kept every fourth pixel of the canvas; the editor draws on every eighth.
TEMPLATE_STEP: Final[int] = 4
EDITOR_STEP: Final[int] = 8
# Greys of the template picture. All are below the land threshold of ``rnw.landmask``: a
# template painted over in an editor that keeps its greys draws no land by itself.
OUTSIDE_GREY: Final[int] = 20
AREA_GREY: Final[int] = 90
ISLANDS_GREY: Final[int] = 62
AMERICAS_GREY: Final[int] = 118
# The first number of a key is the layout of the entry; a change of it keeps an older entry
# from being read.
LAYOUT: Final[int] = 2
# The whole map is kept every sixteenth pixel, for the editor's view of where its sheet lies.
WORLD_STEP: Final[int] = 16


@dataclass(frozen=True, slots=True)
class DomainPlan:
    """What the plan of a world of several continents reads that shapes the area of one of them
    (``rnw.continent_domains.plan_domains``): the continent, the world's seed (the shared ocean's
    drift, Africa's landing and strait follow it), what each continent made has of its shore
    (its key, the ocean band, whether the ocean is expanded, The Wall, Omerika's share) and
    whether Africa must meet Asia. The other settings of a continent do not move its area."""

    continent: str
    seed: int
    shapes: tuple[tuple[str, int, bool, bool, int], ...]
    join_asia: bool
    iberia: str = "off"


@dataclass(frozen=True, slots=True)
class AreaInputs:
    """What an area is cut for: the game, and America's canvas alone (the ocean band, whether it
    is expanded) or a continent's area in a world of several (``plan``)."""

    game_dir: Path
    band_px: int
    expanded: bool
    plan: DomainPlan | None = None


def area_inputs(
    game_dir: Path, settings: Settings, continent: str = AMERICA, seed: int = 0
) -> AreaInputs:
    """The inputs of the area of ``continent`` in the world ``settings`` and ``seed`` make."""
    shape = settings.new_world
    expanded = bool(shape.expand_oceans or shape.landform)
    if not settings.continents.regions:
        return AreaInputs(game_dir, shape.ocean_band_px, expanded)
    shapes: list[tuple[str, int, bool, bool, int]] = []
    if settings.continents.america and not shape.keep_geography:
        shapes.append(
            (
                AMERICA,
                shape.ocean_band_px,
                bool(shape.expand_oceans),
                bool(shape.landform),
                shape.template_permille,
            )
        )
    shapes.extend(
        (one.key, one.new_world.ocean_band_px, False, False, 0)
        for one in settings.continents.regions
    )
    asia = any(one.require_asia_connection for one in settings.continents.regions)
    iberia = next(
        (one.iberia_connection for one in settings.continents.regions if one.key == "africa"), "off"
    )
    return AreaInputs(
        game_dir,
        shape.ocean_band_px,
        expanded,
        DomainPlan(continent, seed, tuple(shapes), asia, iberia),
    )


@dataclass(frozen=True, slots=True, eq=False)
class LandArea:
    """The area of the canvas, the game's Americas and the island groups, every ``STEP``th pixel."""

    shape: tuple[int, int]
    area: NDArray[np.bool_]
    americas: NDArray[np.bool_]
    islands: NDArray[np.bool_]
    # Where the sheet lies on the game's map: the map's row and column of its first pixel and the
    # map's height and width (columns wrap); and the whole map's land every ``WORLD_STEP``th
    # pixel. For the editor's view of the world; None when not known.
    origin: tuple[int, int, int, int] | None = None
    world: NDArray[np.bool_] | None = None
    # The same map's pixels that the other continents of a world of several are generated on
    # (their areas, not the sheet's), for the editor's view of the world; None for one continent.
    others: NDArray[np.bool_] | None = None

    @property
    def picture_shape(self) -> tuple[int, int]:
        """Rows and columns of the layers."""
        rows, columns = self.area.shape
        return int(rows), int(columns)

    def at(self, step: int) -> LandArea:
        """The layers every ``step``th pixel of the canvas; ``step`` is a multiple of
        ``TEMPLATE_STEP``, and the result is what cutting the canvas at ``step`` gives."""
        if step % TEMPLATE_STEP:
            message = f"The area is kept at steps that are multiples of {TEMPLATE_STEP}"
            raise ValueError(message)
        every = step // TEMPLATE_STEP
        return LandArea(
            self.shape,
            np.ascontiguousarray(self.area[::every, ::every]),
            np.ascontiguousarray(self.americas[::every, ::every]),
            np.ascontiguousarray(self.islands[::every, ::every]),
            self.origin,
            self.world,
            self.others,
        )

    def picture(self) -> NDArray[np.uint8]:
        """The grey picture a painter draws land on: dark for outside, lighter for the area,
        lighter again for the game's Americas and darker for the island groups."""
        grey = np.full(self.area.shape, OUTSIDE_GREY, dtype=np.uint8)
        grey[self.area] = AREA_GREY
        grey[self.americas & self.area] = AMERICAS_GREY
        grey[self.islands & self.area] = ISLANDS_GREY
        return grey

    def png(self) -> bytes:
        """``picture`` as a grey PNG."""
        return encode_png(self.picture(), color_type=COLOR_GRAY, compression="zlib")


def from_canvas(canvas: Canvas) -> LandArea:
    """The layers of a canvas, cut every ``TEMPLATE_STEP``th pixel."""
    step = TEMPLATE_STEP
    area = np.ascontiguousarray(canvas.mask[::step, ::step])
    americas = (
        np.ascontiguousarray(canvas.template[::step, ::step])
        if canvas.template is not None
        else np.zeros(area.shape, dtype=np.bool_)
    )
    islands = np.zeros(area.shape, dtype=np.bool_)
    for footprint in canvas.footprints:
        rows, columns = footprint.rows.astype(np.int64), footprint.columns.astype(np.int64)
        on_grid = (rows % step == 0) & (columns % step == 0)
        islands[rows[on_grid] // step, columns[on_grid] // step] = True
    return LandArea((int(canvas.mask.shape[0]), int(canvas.mask.shape[1])), area, americas, islands)


def area_key(
    game_dir: Path, band_px: int, *, expanded: bool, plan: DomainPlan | None = None
) -> str:
    """The identity of an area: the fingerprints of the map's files, the two settings and the
    code; of an area in a world of several continents also its plan and the file of the game's
    waters that the plan reads. Only the files are read, not decoded."""
    spec: tuple[object, ...] = (
        LAYOUT,
        landcache.code_identity(),
        tuple(input_fingerprints(game_dir)),
        band_px,
        expanded,
    )
    if plan is not None:
        spec = (*spec, plan, _file_digest(game_dir / TEMPLATES))
    return hashlib.sha256(repr(spec).encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def get_area(
    cache: Path | None,
    game_dir: Path,
    band_px: int,
    *,
    expanded: bool,
    plan: DomainPlan | None = None,
) -> LandArea:
    """The area of the installed game's map for ``band_px`` of ocean (or, with ``plan``, the area
    of a continent in a world of several), from the cache when it was chosen before (a fraction
    of a second), else chosen now (seconds) and kept."""
    target = None
    if cache is not None:
        key = area_key(game_dir, band_px, expanded=expanded, plan=plan)
        target = cache / landcache.AREAS / f"{key}{landcache.AREA_SUFFIX}"
    if target is not None and target.exists():
        area = read_area(target)
        if area is not None:
            landcache.touch(target)
            return area
    game_map = run_stage("load map", lambda: load_map(game_dir))
    height, width = (int(size) for size in game_map.labels.shape)
    others = None
    generated: tuple[str, ...] = ()
    if plan is not None:
        domains = run_stage("select canvas", lambda: planned_domains(game_dir, game_map, plan))
        generated = tuple(one.continent.key for one in domains)
        domain = next(one for one in domains if one.continent.key == plan.continent)
        area = replace(
            from_domain(domain),
            origin=(domain.first_row, domain.first_column, height, domain.map_width),
        )
        others = world_areas([one for one in domains if one is not domain], (height, width))
    else:
        canvas = run_stage(
            "select canvas",
            lambda: landcache.get_canvas(cache, game_map, band_px, expanded=expanded),
        )
        area = replace(
            from_canvas(canvas), origin=(0, (canvas.col0 - canvas.roll) % width, height, width)
        )
    # The map is let go on return.
    area = replace(area, world=world_land(game_map, generated), others=others)
    if target is not None and cache is not None:
        write_area(target, area)
        landcache.prune(cache)
    return area


def from_domain(domain: Domain) -> LandArea:
    """The American drawing sheet within the shared continent footprints."""
    area = np.ascontiguousarray(domain.mask[::TEMPLATE_STEP, ::TEMPLATE_STEP])
    americas = np.ascontiguousarray(domain.footprint[::TEMPLATE_STEP, ::TEMPLATE_STEP])
    rows, columns = domain.mask.shape
    return LandArea((int(rows), int(columns)), area, americas, np.zeros_like(area))


def planned_domains(game_dir: Path, game_map: Eu5Map, plan: DomainPlan) -> tuple[Domain, ...]:
    """The domains of the world's continents, planned as the export plans them for the plan's
    seed."""
    geography = {
        key: replace(
            CONTINENTS[key].geography(),
            ocean_band_px=band,
            expand_oceans=int(expanded),
            landform=int(landform),
            template_permille=template,
        )
        for key, band, expanded, landform, template in plan.shapes
    }
    tolls, closed = retained_facts(game_dir)
    composition = CompositionInputs(
        geography, plan.join_asia, tolls, closed, sea_circuit=False, iberia_connection=plan.iberia
    )
    return composition.plan(game_map, plan.seed)


def world_areas(domains: Collection[Domain], shape: tuple[int, int]) -> NDArray[np.bool_]:
    """The map's pixels, every ``WORLD_STEP``th one, that lie in the area of any of ``domains``."""
    height, width = shape
    found = np.zeros((-(-height // WORLD_STEP), -(-width // WORLD_STEP)), dtype=np.bool_)
    for domain in domains:
        rows, columns = domain.mask.shape
        down = np.arange(found.shape[0]) * WORLD_STEP - domain.first_row
        across = (np.arange(found.shape[1]) * WORLD_STEP - domain.first_column) % domain.map_width
        inside_rows, inside_columns = (
            np.flatnonzero((down >= 0) & (down < rows)),
            np.flatnonzero(across < columns),
        )
        found[np.ix_(inside_rows, inside_columns)] |= domain.mask[
            np.ix_(down[inside_rows], across[inside_columns])
        ]
    return found


def world_land(game_map: Eu5Map, generated: Collection[str] = ()) -> NDArray[np.bool_]:
    """The retained geography behind the editor, at every ``WORLD_STEP``th pixel."""
    water = np.array(
        [kind in {CellClass.SEA, CellClass.LAKE} for kind in game_map.classes], dtype=np.bool_
    )
    land = ~(water | retired_atlantic_islands(game_map, generated))
    return np.ascontiguousarray(land[game_map.labels[::WORLD_STEP, ::WORLD_STEP]])


def write_area(target: Path, area: LandArea) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    world = area.world if area.world is not None else np.zeros((0, 0), dtype=np.bool_)
    others = area.others if area.others is not None else np.zeros((0, 0), dtype=np.bool_)
    arrays = {
        "shape": np.array([*area.shape, *area.picture_shape], dtype=np.int64),
        "area": np.packbits(area.area, axis=None),
        "americas": np.packbits(area.americas, axis=None),
        "islands": np.packbits(area.islands, axis=None),
        "origin": np.array(area.origin or (), dtype=np.int64),
        "world_shape": np.array(world.shape, dtype=np.int64),
        "world": np.packbits(world, axis=None),
        "others_shape": np.array(others.shape, dtype=np.int64),
        "others": np.packbits(others, axis=None),
    }
    with NamedTemporaryFile(dir=target.parent, prefix=".area-", suffix=".npz", delete=False) as out:
        np.savez(out, **arrays)  # pyright: ignore[reportArgumentType]
        temporary = Path(out.name)
    _ = temporary.replace(target)


def read_area(target: Path) -> LandArea | None:
    """The area kept at ``target``, or None when the entry cannot be read (it is made again)."""
    try:
        with np.load(target, allow_pickle=False) as data:
            rows, columns, picture_rows, picture_columns = (
                int(value) for value in data["shape"].tolist()
            )
            count = picture_rows * picture_columns
            layers = [
                np.unpackbits(data[name], count=count)
                .astype(np.bool_)
                .reshape(picture_rows, picture_columns)
                for name in ("area", "americas", "islands")
            ]
            placed = tuple(int(value) for value in data["origin"].tolist())
            world_rows, world_columns = (int(value) for value in data["world_shape"].tolist())
            world = (
                np.unpackbits(data["world"], count=world_rows * world_columns)
                .astype(np.bool_)
                .reshape(world_rows, world_columns)
            )
            # An entry kept before the other continents' areas were kept has none.
            other_rows, other_columns = (
                (int(value) for value in data["others_shape"].tolist())
                if "others_shape" in data
                else (0, 0)
            )
            others = (
                np.unpackbits(data["others"], count=other_rows * other_columns)
                .astype(np.bool_)
                .reshape(other_rows, other_columns)
                if other_rows
                else None
            )
    except (OSError, ValueError, KeyError):
        return None
    origin = (placed[0], placed[1], placed[2], placed[3]) if len(placed) == 4 else None  # noqa: PLR2004
    return LandArea(
        (rows, columns),
        layers[0],
        layers[1],
        layers[2],
        origin,
        world if world.size else None,
        others,
    )
