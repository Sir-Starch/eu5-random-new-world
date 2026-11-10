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
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import landcache
from rnw.eu5_map import input_fingerprints, load_map
from rnw.png import COLOR_GRAY, encode_png
from rnw.progress import run_stage

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from rnw.eu5_canvas import Canvas

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
LAYOUT: Final[int] = 1


@dataclass(frozen=True, slots=True, eq=False)
class LandArea:
    """The area of the canvas, the game's Americas and the island groups, every ``STEP``th pixel."""

    shape: tuple[int, int]
    area: NDArray[np.bool_]
    americas: NDArray[np.bool_]
    islands: NDArray[np.bool_]

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


def area_key(game_dir: Path, band_px: int, *, expanded: bool) -> str:
    """The identity of an area: the fingerprints of the map's files, the two settings and the
    code. Only the files are read, not decoded."""
    spec = (
        LAYOUT,
        landcache.code_identity(),
        tuple(input_fingerprints(game_dir)),
        band_px,
        expanded,
    )
    return hashlib.sha256(repr(spec).encode("utf-8")).hexdigest()


def get_area(cache: Path | None, game_dir: Path, band_px: int, *, expanded: bool) -> LandArea:
    """The area of the installed game's map for ``band_px`` of ocean, from the cache when it was
    chosen before (a fraction of a second), else chosen now (seconds) and kept."""
    target = (
        None
        if cache is None
        else cache
        / landcache.AREAS
        / f"{area_key(game_dir, band_px, expanded=expanded)}{landcache.AREA_SUFFIX}"
    )
    if target is not None and target.exists():
        area = _read(target)
        if area is not None:
            landcache.touch(target)
            return area
    canvas = _canvas(cache, game_dir, band_px, expanded=expanded)
    area = from_canvas(canvas)
    if target is not None and cache is not None:
        _write(target, area)
        landcache.prune(cache)
    return area


def _canvas(cache: Path | None, game_dir: Path, band_px: int, *, expanded: bool) -> Canvas:
    """The canvas of the installed map; the map is let go on return."""
    game_map = run_stage("load map", lambda: load_map(game_dir))
    return run_stage(
        "select canvas",
        lambda: landcache.get_canvas(cache, game_map, band_px, expanded=expanded),
    )


def _write(target: Path, area: LandArea) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    arrays = {
        "shape": np.array([*area.shape, *area.picture_shape], dtype=np.int64),
        "area": np.packbits(area.area, axis=None),
        "americas": np.packbits(area.americas, axis=None),
        "islands": np.packbits(area.islands, axis=None),
    }
    with NamedTemporaryFile(dir=target.parent, prefix=".area-", suffix=".npz", delete=False) as out:
        np.savez(out, **arrays)  # pyright: ignore[reportArgumentType]
        temporary = Path(out.name)
    _ = temporary.replace(target)


def _read(target: Path) -> LandArea | None:
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
    except (OSError, ValueError, KeyError):
        return None
    return LandArea((rows, columns), layers[0], layers[1], layers[2])
