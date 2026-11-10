"""Known lands: cut the outline of famous fantasy and science-fiction lands out of map pictures.

Each land has its own recipe, because each map is drawn in its own way (a colour for the sea,
lettering and roads over both, a red sea). The recipes are tuned by eye against the pictures named
in ``README.md``; running them on those pictures gives ``src/rnw/lands/*.png``.

    uv run python experiments/070-known-lands/build_lands.py --maps DIR --out src/rnw/lands

``DIR`` holds the pictures as ``tamriel.png``, ``westeros.png``, ``kalimdor.png`` and
``ansalon.png``. A land is a grey picture of kinds: 0 sea, 1 land, 5 lake (``rnw.landmask``).
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from rnw.topology import distance_from, label_components

Image.MAX_IMAGE_PIXELS = None
SEA, LAND, LAKE = 0, 1, 5
WORK = 1800


def load(path: str, work: int = WORK) -> tuple[np.ndarray, np.ndarray]:
    """RGB (uint8) and a mask of transparent pixels, shrunk so the long side is ``work``."""
    im = Image.open(path)
    im.load()
    im = im.convert("RGBA")
    scale = work / max(im.size)
    if scale < 1:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.BOX)
    a = np.asarray(im)
    return a[:, :, :3].copy(), a[:, :, 3] < 128


def near(rgb: np.ndarray, color: tuple[int, int, int], tol: int) -> np.ndarray:
    d = np.abs(rgb.astype(np.int16) - np.array(color, dtype=np.int16))
    return d.max(axis=2) <= tol


def dilate(m: np.ndarray, r: int) -> np.ndarray:
    return distance_from(m, r + 1, octagonal=True) <= r if r > 0 else m


def erode(m: np.ndarray, r: int) -> np.ndarray:
    return ~dilate(~m, r) if r > 0 else m


def opening(m: np.ndarray, r: int) -> np.ndarray:
    return dilate(erode(m, r), r)


def closing(m: np.ndarray, r: int) -> np.ndarray:
    return erode(dilate(m, r), r)


def parts(m: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    lab = label_components(m.astype(np.int32))
    return lab, np.bincount(lab.ravel())


def drop_small(m: np.ndarray, min_px: int) -> np.ndarray:
    """Remove pieces of ``m`` smaller than ``min_px``."""
    lab, sizes = parts(m)
    return m & (sizes >= min_px)[lab]


def finish(
    land: np.ndarray,
    *,
    speck: float = 0.0004,
    lake_min: float = 0.002,
    maxside: int = 1000,
) -> np.ndarray:
    """Clean ``land`` (bool), mark the enclosed water bodies of size as lakes, crop and shrink."""
    total = land.size
    lab, sizes = parts(land)
    comp_is_land = np.zeros(sizes.shape, dtype=bool)
    comp_is_land[lab[land]] = True
    keep = comp_is_land & (
        np.bincount(lab.ravel(), minlength=sizes.size) >= max(8, int(speck * total))
    )
    land = land & keep[lab]
    water = ~land
    wl, ws = parts(water)
    ws = np.bincount(wl.ravel(), minlength=ws.size)
    border = np.zeros(ws.size, dtype=bool)
    border[np.unique(np.concatenate([wl[0], wl[-1], wl[:, 0], wl[:, -1]]))] = True
    is_water = np.zeros(ws.size, dtype=bool)
    is_water[wl[water]] = True
    lake_comp = is_water & ~border & (ws >= max(8, int(lake_min * total)))
    pit_comp = is_water & ~border & ~lake_comp
    kinds = np.zeros(land.shape, dtype=np.uint8)
    kinds[land] = LAND
    kinds[pit_comp[wl]] = LAND
    kinds[lake_comp[wl]] = LAKE
    rows, cols = np.nonzero(kinds)
    kinds = kinds[rows.min() : rows.max() + 1, cols.min() : cols.max() + 1]
    h, w = kinds.shape
    scale = maxside / max(h, w)
    if scale < 1:
        nh, nw = round(h * scale), round(w * scale)
        landf = Image.fromarray(((kinds == LAND) | (kinds == LAKE)).astype(np.uint8) * 255).resize(
            (nw, nh), Image.BOX
        )
        lakef = Image.fromarray((kinds == LAKE).astype(np.uint8) * 255).resize((nw, nh), Image.BOX)
        landb = np.asarray(landf) >= 128
        lakeb = np.asarray(lakef) >= 160
        kinds = np.zeros((nh, nw), dtype=np.uint8)
        kinds[landb] = LAND
        kinds[lakeb & landb] = LAKE
    return kinds


def preview(kinds: np.ndarray, path: str, scale: float = 1.0) -> None:
    pal = np.array(
        [(28, 58, 98), (150, 170, 110), (0, 0, 0), (0, 0, 0), (0, 0, 0), (90, 170, 220)],
        dtype=np.uint8,
    )
    im = Image.fromarray(pal[kinds])
    if scale != 1.0:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.NEAREST)
    im.save(path)


def save_kinds(kinds: np.ndarray, path: str) -> None:
    Image.fromarray(kinds, mode="L").save(path, optimize=True)


def tamriel(maps: Path, work: Path) -> np.ndarray:
    rgb, _ = load(str(maps / "tamriel.png"))
    return drop_small(~near(rgb, (203, 227, 251), 14), 400)


def westeros(maps: Path, work: Path) -> np.ndarray:
    """A road-map style Westeros: the sea is light blue, the land white and grey; lettering (black
    with a white halo), the boxes of the roads and the rivers lie on both."""
    rgb, _ = load(str(maps / "westeros.png"), 2000)
    h, w, _ = rgb.shape
    r, g, b = (rgb[:, :, i].astype(int) for i in range(3))
    high, low = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    saturation = (high - low) / np.maximum(high, 1)
    sea_colour = (b - r >= 25) & (b >= g - 2) & (high >= 200) & (saturation <= 0.30)
    # What is not plainly sea or land (black letters, their white halo, the dark blue boxes of the
    # roads, the orange roads) takes the side that its surroundings are on, grown a pixel at a time.
    box = (b - r >= 25) & (high < 200) & (saturation > 0.2)
    unknown = dilate(high < 100, 4) | dilate(box, 4) | ((high >= 250) & (saturation <= 0.05))
    sea = sea_colour & ~unknown
    land = (high >= 190) & (saturation <= 0.16) & ~sea_colour & ~unknown
    unknown = ~(sea | land)
    for _ in range(16):
        grow_sea, grow_land = dilate(sea, 1) & unknown, dilate(land, 1) & unknown
        sea, land = sea | (grow_sea & ~grow_land), land | grow_land
        unknown = ~(sea | land)
    land |= unknown
    # The map has Essos on its right; the north is cut by the frame, where the lands run on.
    inside = np.zeros_like(land)
    inside[:, : int(0.815 * w)] = True
    return drop_small(opening(land & inside, 3), 120)


def kalimdor(maps: Path, work: Path) -> np.ndarray:
    """A hypsometric map: land in greens, yellows and reds, water in blues, paper round it."""
    rgb, _ = load(str(maps / "kalimdor.png"), 2000)
    h, w, _ = rgb.shape
    # The map sits in a frame with a legend under it.
    top, bottom, left, right = int(0.028 * h), int(0.893 * h), int(0.037 * w), int(0.965 * w)
    r, g, b = (rgb[:, :, i].astype(float) / 255 for i in range(3))
    high, low = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    saturation = (high - low) / np.maximum(high, 1e-6)
    # Hue in degrees, for the ranges that matter (red to green): blue and cyan come out above 150.
    delta = np.maximum(high - low, 1e-6)
    hue = np.where(
        high == r,
        60 * (((g - b) / delta) % 6),
        np.where(high == g, 60 * ((b - r) / delta + 2), 60 * ((r - g) / delta + 4)),
    )
    ground = (saturation > 0.22) & (hue < 150) & (hue >= 0)
    inside = np.zeros_like(ground)
    inside[top:bottom, left:right] = True
    ground &= inside
    # Routes and lettering are thin: what is not near a body of land goes.
    thick = opening(ground, 2)
    land = closing(ground & (thick | dilate(thick, 3)), 2)
    # A piece of another continent is cut by the frame: only the lands of the map stay.
    labels, _ = parts(land)
    edge = np.zeros_like(land)
    edge[top : top + 3, :] = edge[bottom - 3 : bottom, :] = True
    edge[:, left : left + 3] = edge[:, right - 3 : right] = True
    for c in np.unique(labels[land & edge]):
        land &= labels != c
    return land


def ansalon(maps: Path, work: Path) -> np.ndarray:
    """A painted map of Ansalon: the sea is dark blue-grey, the Blood Sea of Istar red, the land
    olive, green, grey and, at the south, the white Icewall; lettering and the legend are thin."""
    rgb, _ = load(str(maps / "ansalon.png"), 2000)
    r, g, b = (rgb[:, :, i].astype(int) for i in range(3))
    high, low = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    saturation = (high - low) / np.maximum(high, 1)
    # Dark and bluish (a forest is dark too, but green); the red of the Blood Sea, its swirl closed.
    blue = (b - r >= 6) & (b >= g - 3) & (high <= 135) & (saturation >= 0.08)
    red = (r - g >= 40) & (r - b >= 30) & (g <= 90)
    sea = opening(blue | closing(red, 12), 3)
    # Lettering on the sea and the legend are thin; rivers and roads in the land are thin water.
    land = opening(~sea, 3)
    h, w = land.shape
    land[int(0.89 * h) :, int(0.95 * w) :] = False  # the legend
    return drop_small(land, 600)


# id -> (recipe, finish() options, source file(s))
RECIPES = {
    "westeros": (westeros, {"speck": 0.00004, "lake_min": 0.0007, "maxside": 1200}),
    "tamriel": (tamriel, {}),
    "kalimdor": (kalimdor, {"speck": 0.00006, "lake_min": 0.0006, "maxside": 1100}),
    "ansalon": (ansalon, {"speck": 0.00002, "lake_min": 0.001, "maxside": 1400}),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("only", nargs="*")
    arguments = parser.parse_args()
    arguments.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        for name, (recipe, options) in RECIPES.items():
            if arguments.only and name not in arguments.only:
                continue
            kinds = finish(recipe(arguments.maps, Path(folder)), **options)
            save_kinds(kinds, str(arguments.out / f"{name}.png"))
            print(name, kinds.shape, f"{100 * np.count_nonzero(kinds) / kinds.size:.0f}% land")


if __name__ == "__main__":
    main()
