"""Land drawn in an image: read, hashed, fitted to the canvas, and built on."""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import io
from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np
import pytest
from PIL import Image

from rnw import epoch, landmask
from rnw.app import library, service
from rnw.app.worldcode import decode, encode, new_code
from rnw.fields import box_blur
from rnw.landmask import LandMask, LandMaskError
from rnw.newworld import generate_new_world
from rnw.settings import PRESETS
from tests.fakes import build_game, build_world

if TYPE_CHECKING:
    from pathlib import Path


def _picture(land: np.ndarray, mode: str = "L") -> bytes:
    grey = np.where(land, 255, 0).astype(np.uint8)
    buffer = io.BytesIO()
    Image.fromarray(grey).convert(mode).save(buffer, format="PNG")
    return buffer.getvalue()


def _blob(height: int = 96, width: int = 88, *, hole: bool = False) -> np.ndarray:
    land = np.zeros((height, width), dtype=bool)
    land[height // 4 : 3 * height // 4, width // 4 : 3 * width // 4] = True
    if hole:
        land[height // 2 - 3 : height // 2 + 3, width // 2 - 3 : width // 2 + 3] = False
    return land


def test_a_picture_of_land_is_read_hashed_and_written_back_the_same() -> None:
    """White is land; the id is of the land, so another file of it has the same id."""
    land = _blob()
    mask = landmask.from_bytes(_picture(land))
    assert mask.size == (96, 88)
    assert 100 < mask.share < 600
    assert (
        mask.id
        == landmask.from_bytes(_picture(land, "RGB")).id
        == landmask.from_bytes(mask.png()).id
    )
    assert mask.id < 1 << 48
    assert mask.sha256 == landmask.from_bytes(mask.png()).sha256
    other = landmask.from_bytes(_picture(_blob(hole=True)))
    assert other.id != mask.id
    transparent = Image.new("RGBA", (96, 96), (255, 255, 255, 0))
    solid = Image.new("RGBA", (96, 96), (255, 255, 255, 255))
    solid.paste(transparent.crop((0, 0, 96, 40)), (0, 0))
    buffer = io.BytesIO()
    solid.save(buffer, format="PNG")
    assert landmask.from_bytes(buffer.getvalue()).share < 700


def test_a_picture_that_cannot_be_land_is_refused_with_the_reason() -> None:
    """Unreadable, too small, all sea, all land."""
    with pytest.raises(LandMaskError, match="cannot be read"):
        _ = landmask.from_bytes(b"not a picture")
    with pytest.raises(LandMaskError, match="at least"):
        _ = landmask.from_bytes(_picture(np.ones((10, 200), dtype=bool)))
    with pytest.raises(LandMaskError, match="land; a world needs"):
        _ = landmask.from_bytes(_picture(np.zeros((100, 100), dtype=bool)))
    with pytest.raises(LandMaskError, match="land; a world needs"):
        _ = landmask.from_bytes(_picture(np.ones((100, 100), dtype=bool)))


def test_a_file_is_read_from_disk(tmp_path: Path) -> None:
    """The reader names a missing file plainly."""
    path = tmp_path / "land.png"
    _ = path.write_bytes(_picture(_blob()))
    assert landmask.read(path).size == (96, 88)
    with pytest.raises(LandMaskError, match="cannot be read"):
        _ = landmask.read(tmp_path / "missing.png")


def test_the_picture_is_fitted_to_the_canvas_and_a_wrong_shape_says_what_is_right() -> None:
    """Whole-pixel stretch with a smoothed edge when it grows; proportions within a tenth."""
    mask = landmask.from_bytes(_picture(_blob(96, 88)))
    fitted = landmask.fit(mask, (480, 440))
    assert fitted.shape == (480, 440)
    assert fitted[240, 220]
    assert not fitted[5, 5]
    assert np.array_equal(fitted, landmask.fit(mask, (480, 440)))
    share = fitted.sum() / fitted.size
    assert abs(share - mask.land.sum() / mask.land.size) < 0.02
    same = landmask.fit(mask, (96, 88))
    assert np.array_equal(same, mask.land)
    with pytest.raises(LandMaskError, match="Draw it in that proportion"):
        _ = landmask.fit(mask, (480, 880))


def _stretch(drawn: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """The drawing's land on a canvas of ``shape`` (``fit`` demands the picture's proportions,
    which these tests keep within a tenth)."""
    return landmask.fit(LandMask(drawn), shape)


def _edge(land: np.ndarray) -> np.ndarray:
    """The first land pixel of every row."""
    return np.argmax(land, axis=1).astype(float)


def test_a_stretched_staircase_becomes_a_smooth_coast() -> None:
    """A coast drawn one pixel in four steps lies on its line, not on a staircase of eight-pixel
    steps; a straight coast stays exactly where it was drawn."""
    rows, columns = 96, 88
    drawn = np.zeros((rows, columns), dtype=bool)
    for row in range(rows):
        drawn[row, 30 + row // 4 :] = True
    stretched = _stretch(drawn, (768, 704))
    whole = np.arange(768) * rows // 768, np.arange(704) * columns // 704
    pixels = drawn[np.ix_(*whole)]
    deviations: list[float] = []
    for land in (stretched, pixels):
        edge, row = _edge(land)[100:600], np.arange(100, 600)
        deviations.append(float(np.abs(edge - np.polyval(np.polyfit(row, edge, 1), row)).max()))
    assert deviations[0] < 1.5  # a curve, within a pixel and a half of its line
    assert deviations[1] > 3  # what stretching by whole pixels leaves
    block = np.zeros((rows, columns), dtype=bool)
    block[24:72, 22:66] = True
    straight = _stretch(block, (768, 704))
    assert set(_edge(straight)[300:400]) == {22.0 * 8}
    assert abs(int(straight.sum()) - int(block.sum()) * 64) < 64 * 8


def test_an_epoch_before_the_spline_stretches_a_drawing_by_blocks_as_it_did() -> None:
    """Epochs 61 and 62 (``SMOOTH_DRAWN_COASTS`` is 63) stretch by whole pixels and smooth with a
    box blur; the reference below is that algorithm as 1.2.1 wrote it."""
    rows, columns, shape = 96, 88, (768, 704)
    drawn = np.zeros((rows, columns), dtype=bool)
    for row in range(rows):
        drawn[row, 30 + row // 4 :] = True
    drawn[20:40, 5:15] = True
    height, width = shape
    wanted = drawn[np.ix_(np.arange(height) * rows // height, np.arange(width) * columns // width)]
    scale = min(height // rows, width // columns)
    assert scale > landmask.SMOOTH_ABOVE
    wanted = box_blur(wanted.astype(np.int64) * landmask.PERMILLE, scale // 2) >= 500
    mask = LandMask(drawn)
    for number in range(epoch.OLDEST_SELECTABLE, epoch.SMOOTH_DRAWN_COASTS):
        assert np.array_equal(landmask.fit(mask, shape, number), wanted)
        assert np.array_equal(landmask.fit_drawing(mask, shape, number).land, wanted)
    smooth = landmask.fit(mask, shape, epoch.SMOOTH_DRAWN_COASTS)
    assert not np.array_equal(smooth, wanted)
    assert np.array_equal(landmask.fit(mask, shape), smooth)
    assert np.array_equal(landmask.fit_drawing(mask, shape).land, smooth)


def test_a_stretched_drawing_is_the_same_whatever_the_strips_and_mirrors_itself(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The strips of canvas rows only bound the memory, and the arithmetic is exact: a drawing
    that is symmetric makes land that is, at a scale that is not a whole number too."""
    block = np.zeros((96, 88), dtype=bool)
    block[24:72, 22:66] = True
    block[40:50, 30:36] = False
    block[:, 60:64] = block[:, 22:26]
    whole = _stretch(block, (700, 642))
    monkeypatch.setattr(landmask, "STRIP_ROWS", 37)
    assert np.array_equal(_stretch(block, (700, 642)), whole)
    plain = np.zeros((96, 88), dtype=bool)
    plain[24:72, 22:66] = True
    even = _stretch(plain, (700, 642))
    assert np.array_equal(even, even[:, ::-1])
    assert np.array_equal(even, even[::-1])


def test_a_stretched_drawing_is_a_blur_read_through_a_cubic_spline() -> None:
    """The integer arithmetic agrees with the same stretch done plainly, in floating point."""
    rng = np.random.default_rng(3)
    drawn = np.zeros((40, 36), dtype=bool)
    drawn[8:30, 6:28] = True
    drawn[rng.random(drawn.shape) < 0.04] ^= True
    height, width = 213, 191

    def spline(source: int, canvas: int) -> np.ndarray:
        position = (np.arange(canvas) + 0.5) * source / canvas - 0.5
        first = np.floor(position).astype(int)
        t = position - first
        weights = np.stack(
            [
                (1 - t) ** 3 / 6,
                (3 * t**3 - 6 * t**2 + 4) / 6,
                (-3 * t**3 + 3 * t**2 + 3 * t + 1) / 6,
                t**3 / 6,
            ]
        )
        matrix = np.zeros((canvas, source))
        for tap in range(4):
            index = np.clip(first + tap - 1, 0, source - 1)
            np.add.at(matrix, (np.arange(canvas), index), weights[tap])
        return matrix

    taps = np.array(landmask.BLUR_TAPS, dtype=float) / landmask.BLUR_UNIT
    blurred = drawn.astype(float)
    for axis in (0, 1):
        along = np.arange(blurred.shape[axis])
        blurred = np.sum(
            [
                taps[k] * blurred.take(along + k - len(taps) // 2, axis=axis, mode="clip")
                for k in range(len(taps))
            ],
            axis=0,
        )
    plain = spline(40, height) @ blurred @ spline(36, width).T >= 0.5
    stretched = _stretch(drawn, (height, width))
    assert np.count_nonzero(stretched != plain) <= 2


def _domain(height: int = 420, width: int = 380) -> np.ndarray:
    domain = np.zeros((height, width), dtype=bool)
    domain[20:-20, 20:-20] = True
    return domain


def test_a_world_is_made_on_the_drawn_land_and_keeps_off_the_edge() -> None:
    """The cells follow the picture: land where it is drawn, sea where it is not."""
    settings = PRESETS["small_continents"].new_world
    domain = _domain()
    drawn = np.zeros(domain.shape, dtype=bool)
    drawn[120:300, 100:280] = True
    world = generate_new_world(domain, seed=5, settings=settings, drawn=drawn)
    land_pixels = np.isin(
        world.labels,
        [i for i, kind in enumerate(world.classes) if kind.value in {"land", "wasteland"}],
    )
    inside = land_pixels[130:290, 110:270].mean()
    assert inside > 0.6
    assert not land_pixels[:60].any()
    assert not land_pixels[:, :60].any()
    again = generate_new_world(domain, seed=5, settings=settings, drawn=drawn)
    assert np.array_equal(world.labels, again.labels)
    other_seed = generate_new_world(domain, seed=6, settings=settings, drawn=drawn)
    land_a = np.isin(world.labels, [i for i, k in enumerate(world.classes) if k.value == "land"])
    land_b = np.isin(
        other_seed.labels, [i for i, k in enumerate(other_seed.classes) if k.value == "land"]
    )
    assert (land_a & land_b).sum() > 0.5 * land_a.sum()


def test_land_drawn_where_the_world_cannot_be_is_refused() -> None:
    """A drawing outside the area, or only in the margin, or only specks, asks for nothing."""
    settings = PRESETS["small_continents"].new_world
    domain = _domain()
    outside = np.zeros(domain.shape, dtype=bool)
    outside[0:15, :] = True
    edge = np.zeros(domain.shape, dtype=bool)
    edge[22:30, 22:360] = True
    for drawn in (outside, edge):
        with pytest.raises(LandMaskError, match="cannot be"):
            _ = generate_new_world(domain, seed=1, settings=settings, drawn=drawn)
    specks = np.zeros(domain.shape, dtype=bool)
    specks[200:202, 200:202] = True
    with pytest.raises(LandMaskError, match="larger continents"):
        _ = generate_new_world(domain, seed=1, settings=settings, drawn=specks)


def test_the_code_holds_the_pictures_id_and_a_world_needs_the_picture_to_be_made_again(
    tmp_path: Path,
) -> None:
    """The id travels in the code; the picture is kept in the world's folder and found again."""
    mask = landmask.from_bytes(_picture(_blob()))
    code = new_code("continents", 7, {"mask": {"id": mask.id}})
    assert decode(encode(code)).settings().mask.id == mask.id
    game = build_game(tmp_path / "game")
    data = tmp_path / "data"
    plain = build_world(data, game)
    assert service.required_land_mask(data, plain) is None
    drawn_world = replace(plain, code=encode(code))
    with pytest.raises(service.LandImageError, match="no longer has"):
        _ = service.required_land_mask(data, drawn_world)
    image = library.folder(data, drawn_world) / library.LAND_MASK
    _ = image.write_bytes(mask.png())
    found = service.required_land_mask(data, drawn_world)
    assert found is not None
    assert found.id == mask.id
    _ = image.write_bytes(landmask.from_bytes(_picture(_blob(hole=True))).png())
    with pytest.raises(service.LandImageError):
        _ = service.required_land_mask(data, drawn_world)
    assert isinstance(mask, LandMask)
