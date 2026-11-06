"""Colonial overseas eligibility, read from the files a world writes (read-only).

EU5 builds a continent's list of neighbouring subcontinents from the passable locations that
touch in ``locations.png``, and a capital cannot found a colonial nation in a subcontinent on
the list of its own continent [C453]. The export's first check
(``eu5_nw_export._check_overseas_contacts``) judges the labels and the hierarchy the generator
holds in memory. The game reads three written files instead: ``locations.png``,
``definitions.txt`` and ``default.map``. They differ from the held labels where the generator
recolours pixels only in the file (the closed-ocean remainders that join a neighbouring sea,
W4). This module reads those files as written, in bands, so no whole-map pair list is built.
"""

# NumPy stubs type array comparisons, indexing and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.eu5_canvas import NEW_WORLD, OCEANS

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from numpy.typing import NDArray

    from rnw.geography import Location

BAND_ROWS: Final[int] = 256
AMERICAN: Final[int] = 1
OLD_WORLD: Final[int] = 2


def overseas_flags(
    keys: Sequence[str],
    hierarchy: Mapping[str, Location],
    impassable: Collection[str],
    exempt: Collection[str] = (),
) -> NDArray[np.uint8]:
    """Per location: 1 for a passable American one, 2 for a passable Old World one, else 0.

    The ocean continents are not the Old World, nor are the ``exempt`` keys (the waters the
    canvas took over and counts as ocean, ``eu5_canvas.open_map``). A location that the
    hierarchy does not list takes no part.
    """
    flags = np.zeros(len(keys), dtype=np.uint8)
    for number, key in enumerate(keys):
        location = hierarchy.get(key)
        if location is None or key in impassable or key in exempt:
            continue
        if location.continent == NEW_WORLD:
            flags[number] = AMERICAN
        elif location.continent not in OCEANS:
            flags[number] = OLD_WORLD
    return flags


def passable_contacts(
    labels: NDArray[np.int32], flags: NDArray[np.uint8], *, band: int = BAND_ROWS
) -> list[tuple[int, int]]:
    """Touching (American, Old World) label pairs of a raster, with the horizontal wrap.

    Contacts are 4-neighbour, as in ``topology.adjacency_pairs``. The raster is read in bands
    of ``band`` rows (plus the row below, for the vertical contacts), so the work stays small.
    """
    found: set[tuple[int, int]] = set()

    def compare(first: NDArray[np.int32], second: NDArray[np.int32]) -> None:
        one, two = flags[first], flags[second]
        hit = (one != two) & (one > 0) & (two > 0)
        if not hit.any():
            return
        left, right = first[hit], second[hit]
        american = one[hit] == AMERICAN
        found.update(
            zip(
                np.where(american, left, right).tolist(),
                np.where(american, right, left).tolist(),
                strict=True,
            )
        )

    height = int(labels.shape[0])
    for top in range(0, height, band):
        rows = labels[top : min(height, top + band + 1)]
        compare(rows[:, :-1], rows[:, 1:])
        compare(rows[:, -1], rows[:, 0])
        compare(rows[:-1], rows[1:])
    return sorted(found)
