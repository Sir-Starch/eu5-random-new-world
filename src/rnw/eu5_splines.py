"""Roads for a generated New World: the spline network of the mod (R7d).

NOT GAME VALIDATED. EU5 draws a road between two locations along a strip baked into
``in_game/gfx/map/spline_network/spline_network.splnet``, for the vanilla locations only, and logs
``Could not find spline network strip of type 0 between anchors a and b`` thousands of times a
minute for a road without one: the generated royal roads and the roads built in play alike
[V-GAME owner C161]. Vanilla has a strip for every land-land contact (C162), so the mod's file does
too. It is made from the installed game's file at generation time and never committed (the legal
notes keep derived map files out of anything shared): the vanilla strips of locations that are still
there, renumbered by the order of the mod's ``definitions.txt``, and a strip for every land contact
of a generated location, drawn through the middle of the shared border.

Pure on keys and arrays, like ``eu5_development``; the game's file and the final raster come in as
arguments. All arithmetic is IEEE addition, subtraction, multiplication and division of float64
rounded once to float32, so the bytes are the same on every machine.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.model import CellClass
from rnw.splnet import (
    NewStrip,
    SplineError,
    SplineNetwork,
    parse,
    polyline,
    rebuild,
    serialize,
    strip_ends,
    strip_id,
)

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from numpy.typing import NDArray

    from rnw.eu5_canvas import Canvas
    from rnw.eu5_map import Eu5Map
    from rnw.eu5_newworld import Plan
    from rnw.newworld import NewWorld

GAME_FILE: Final[str] = "game/in_game/gfx/map/spline_network/spline_network.splnet"
MOD_FILE: Final[str] = "in_game/gfx/map/spline_network/spline_network.splnet"
# Vanilla's points lie 2.4 pixels apart at the median and 2.9 on average [V-EXEC C162].
SPACING: Final[float] = 3.0
# Rows of the map raster whose contacts are found at a time, to keep the temporaries small.
BAND: Final[int] = 512
type Point = tuple[float, float]


def land_contacts(
    labels: NDArray[np.int32],
    land: NDArray[np.bool_],
    generated: NDArray[np.bool_],
) -> dict[tuple[int, int], Point]:
    """The border point of each land contact that involves a generated location.

    ``labels`` is the raster of the finished map, ``land`` and ``generated`` say per label whether
    it is land and whether it is new. A contact is two 4-neighbouring pixels of different land
    labels; the point is the contact pixel pair nearest to the mean of the pairs (so it lies on the
    border), in map pixels with x from the left and y from the bottom. A contact across the map's
    seam is refused: nothing here knows how to draw it.
    """
    height = labels.shape[0]
    if np.any(_wanted(labels[:, -1], labels[:, 0], land, generated)):
        message = "A land contact of a generated location crosses the seam of the map"
        raise SplineError(message)
    codes: list[NDArray[np.int64]] = []
    xs: list[NDArray[np.float64]] = []
    ys: list[NDArray[np.float64]] = []
    for top in range(0, height, BAND):
        band = labels[top : top + BAND + 1]
        sideways = band if top + BAND >= height else band[:-1]
        for first, second, shift in (
            (sideways[:, :-1], sideways[:, 1:], (1.0, 0.5)),
            (band[:-1], band[1:], (0.5, 1.0)),
        ):
            rows, columns = np.nonzero(_wanted(first, second, land, generated))
            low = np.minimum(first[rows, columns], second[rows, columns]).astype(np.int64)
            high = np.maximum(first[rows, columns], second[rows, columns]).astype(np.int64)
            codes.append((low << 32) | high)
            xs.append((columns + shift[0]).astype(np.float64))
            ys.append((height - (top + rows + shift[1])).astype(np.float64))
    code, x, y = np.concatenate(codes), np.concatenate(xs), np.concatenate(ys)
    unique, inverse = np.unique(code, return_inverse=True)
    count = np.maximum(np.bincount(inverse, minlength=len(unique)), 1)
    mean_x = np.bincount(inverse, weights=x, minlength=len(unique)) / count
    mean_y = np.bincount(inverse, weights=y, minlength=len(unique)) / count
    away = (x - mean_x[inverse]) ** 2 + (y - mean_y[inverse]) ** 2
    order = np.lexsort((np.arange(len(code)), away, inverse))
    chosen = order[np.searchsorted(inverse[order], np.arange(len(unique)))]
    mask = (1 << 32) - 1
    return {
        (int(pair >> 32), int(pair & mask)): (float(x[i]), float(y[i]))
        for pair, i in zip(unique.tolist(), chosen.tolist(), strict=True)
    }


def _wanted(
    first: NDArray[np.int32],
    second: NDArray[np.int32],
    land: NDArray[np.bool_],
    generated: NDArray[np.bool_],
) -> NDArray[np.bool_]:
    """Pixel pairs of different land labels, at least one of them generated."""
    return (first != second) & land[first] & land[second] & (generated[first] | generated[second])


def road_path(start: Point, border: Point, end: Point) -> NDArray[np.float32]:
    """A smooth road from ``start`` to ``end`` through ``border``, a point every ``SPACING`` pixels.

    A quadratic curve whose middle is the border point, cut into equal steps along its length. Its
    ends are exactly the two anchors.
    """
    first, middle, last = (np.array(point, dtype=np.float64) for point in (start, border, end))
    control = 2.0 * middle - (first + last) / 2.0
    rough = max(2, math.ceil((np.hypot(*(middle - first)) + np.hypot(*(last - middle))) / SPACING))
    t = (np.arange(8 * rough + 1, dtype=np.float64) / (8 * rough))[:, None]
    curve = (1.0 - t) ** 2 * first + 2.0 * (1.0 - t) * t * control + t**2 * last
    along = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(curve, axis=0).T))])
    steps = max(2, math.ceil(float(along[-1]) / SPACING))
    at = np.arange(steps + 1, dtype=np.float64) * (float(along[-1]) / steps)
    path = np.stack([np.interp(at, along, curve[:, 0]), np.interp(at, along, curve[:, 1])], axis=1)
    path = path.astype(np.float32)
    path[0], path[-1] = np.array(start, dtype=np.float32), np.array(end, dtype=np.float32)
    return path


def build_splines(
    vanilla: bytes,
    *,
    vanilla_keys: Sequence[str],
    mod_keys: Sequence[str],
    contacts: Mapping[tuple[str, str], Point],
    anchors: Mapping[str, Point],
) -> tuple[bytes, dict[str, object]]:
    """The mod's spline network from the game's.

    ``vanilla_keys`` and ``mod_keys`` are the locations in the order of the two ``definitions.txt``
    (an anchor is a location's index from 1). ``contacts`` maps the pair of keys of every land
    contact that involves a generated location to its border point, ``anchors`` the keys of the
    generated locations to the position of their anchor. Vanilla strips of locations that are gone
    leave, the others are kept and renumbered, and every contact gets a strip.
    """
    network = parse(vanilla)
    new_index = {key: number + 1 for number, key in enumerate(mod_keys)}
    mapping = {
        number + 1: new_index[key] for number, key in enumerate(vanilla_keys) if key in new_index
    }
    old_anchors = {int(a) for a in network.anchors.tolist()}
    kept_anchors = {mapping[a] for a in old_anchors if a in mapping}
    wanted = {key for pair in contacts for key in pair}
    unknown = sorted(key for key in wanted if key not in new_index)
    if unknown:
        message = f"A land contact names {unknown[0]}, which is no location of the mod"
        raise SplineError(message)
    fresh_anchors = {
        new_index[key]: anchors[key]
        for key in sorted(wanted, key=lambda name: new_index[name])
        if key in anchors and new_index[key] not in kept_anchors
    }
    missing = sorted(
        key
        for key in wanted
        if new_index[key] not in kept_anchors and new_index[key] not in fresh_anchors
    )
    if missing:
        message = f"Location {missing[0]} has land contacts but no anchor and no position for one"
        raise SplineError(message)
    positions = _positions(network, mapping, fresh_anchors)
    strips: list[NewStrip] = []
    for (first, second), border in sorted(contacts.items()):
        low, high = sorted((new_index[first], new_index[second]))
        path = road_path(positions[low], border, positions[high])
        strips.append(NewStrip(low, high, path))
    result = rebuild(network, mapping, fresh_anchors, strips)
    stats: dict[str, object] = {
        "vanilla_anchors": len(network.anchors),
        "vanilla_strips": len(network.strips),
        "anchors": len(result.anchors),
        "strips": len(result.strips),
        "strips_added": len(strips),
        "anchors_added": len(fresh_anchors),
        "segments": len(result.segments),
        "points": len(result.anchors) + len(result.point_xy),
    }
    return serialize(result), stats


def _positions(
    network: SplineNetwork, mapping: Mapping[int, int], fresh: Mapping[int, Point]
) -> dict[int, Point]:
    positions = {
        mapping[int(old)]: (float(x), float(y))
        for old, (x, y) in zip(network.anchors.tolist(), network.anchor_xy.tolist(), strict=True)
        if old in mapping
    }
    return positions | dict(fresh)


def spline_problems(  # noqa: PLR0913 - the file, the game's, the keys and what must be there.
    data: bytes,
    vanilla: bytes,
    *,
    vanilla_keys: Sequence[str],
    mod_keys: Sequence[str],
    contacts: Collection[tuple[str, str]],
    roads: Collection[tuple[str, str]],
) -> list[str]:
    """What is wrong with the mod's spline network, checked against the game's and the map.

    Besides the format (``parse``): every strip joins two locations of the mod; the vanilla strips
    of locations that are still there are unchanged in geometry; every land contact of a generated
    location and every road of ``09_roads.txt`` has a strip; and no strip is left that is neither
    one of those nor vanilla's.
    """
    try:
        network = parse(data)
    except SplineError as error:
        return [str(error)]
    old = parse(vanilla)
    index = {key: number + 1 for number, key in enumerate(mod_keys)}
    mapping = {number + 1: index[key] for number, key in enumerate(vanilla_keys) if key in index}
    problems: list[str] = []
    if len(network.anchors) and int(network.anchors[-1]) > len(mod_keys):
        problems.append("An anchor is beyond the last location of the mod")
    wanted = {strip_id(index[a], index[b]) for a, b in contacts}
    for a, b in roads:
        if a in index and b in index and strip_id(index[a], index[b]) not in network.strips:
            problems.append(f"The road {a} = {b} has no strip")
    problems += [
        f"The land contact {a} and {b} has no strip"
        for a, b in sorted(contacts)
        if strip_id(index[a], index[b]) not in network.strips
    ]
    carried = {
        strip_id(mapping[low], mapping[high]): ident
        for ident in old.strips
        for low, high in (strip_ends(ident),)
        if low in mapping and high in mapping
    }
    for ident in network.strips:
        if ident in carried:
            if not np.array_equal(polyline(network, ident), polyline(old, carried[ident])):
                problems.append(f"The vanilla strip {ident} changed its geometry")
        elif ident not in wanted:
            problems.append(f"The strip {ident} is neither vanilla's nor a land contact")
    absent = len(carried.keys() - network.strips.keys())
    if absent:
        problems.append(f"{absent} vanilla strips of locations that are still there were lost")
    return problems


def world_contacts(
    game_map: Eu5Map, plan: Plan, world: NewWorld, final: NDArray[np.int32]
) -> dict[tuple[str, str], Point]:
    """Land contacts of the generated locations of the finished map, by key, with border points."""
    classes = [*game_map.classes, *world.classes]
    keys = [*game_map.keys, *(cell.key for cell in plan.cells)]
    land = np.array([kind is CellClass.LAND for kind in classes], dtype=bool)
    generated = np.arange(len(classes)) >= len(game_map.keys)
    return {
        (keys[low], keys[high]): point
        for (low, high), point in land_contacts(final, land, generated).items()
    }


def world_anchors(
    game_map: Eu5Map,
    plan: Plan,
    world: NewWorld,
    canvas: Canvas,
    final: NDArray[np.int32],
) -> dict[str, Point]:
    """The anchor of every generated land location: the city's place, its interior point.

    Map pixels, x from the left and y from the bottom, as the locators. An interior point that is
    not in its own location on the finished map stops the build.
    """
    height = canvas.shape[0]
    anchors: dict[str, Point] = {}
    for index, cell in enumerate(plan.cells):
        if cell.kind is not CellClass.LAND:
            continue
        row = int(world.interior[index, 0])
        column = int(canvas.world_column(int(world.interior[index, 1])))
        if int(final[row, column]) != len(game_map.keys) + index:
            message = f"The interior point of {cell.key} is not inside it on the finished map"
            raise SplineError(message)
        anchors[cell.key] = (column + 0.5, height - row - 0.5)
    return anchors
