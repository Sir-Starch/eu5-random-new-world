"""Plan connected ocean identities before serializing an expanded world's map.

The physical generator keeps its own cells. Closed water can share one final vanilla
identity across the canvas boundary; separated remainders get new identities with the
same localized name. Row runs describe the only permitted recolouring outside the
geography canvas. No game files or exported output are repaired.
"""

# NumPy stubs type array indexing and tolist() as Any.
# pyright: reportAny=false
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw.eu5_canvas import OCEANS
from rnw.eu5_newworld import OceanPlan, PlannedCell
from rnw.model import CellClass
from rnw.wording import reference

if TYPE_CHECKING:
    from rnw.eu5_canvas import Canvas, OceanRemainder
    from rnw.eu5_map import Eu5Map
    from rnw.eu5_newworld import Plan
    from rnw.geography import Location
    from rnw.loc_keys import KeySpace
    from rnw.newworld import NewWorld


def emitted_cells(plan: Plan) -> list[PlannedCell]:
    """Each new identity once, excluding identities already declared by vanilla."""
    held: set[str] = plan.oceans.retained if plan.oceans is not None else set()
    cells = [*plan.cells, *(plan.oceans.extra if plan.oceans is not None else [])]
    return list({cell.key: cell for cell in cells if cell.key not in held}.values())


def _neighbours(part: OceanRemainder, canvas: Canvas, world: NewWorld) -> set[int]:
    """Generated cells touching a connected remainder, without a whole-map label pass."""
    found: set[int] = set()
    height, width = world.labels.shape
    for row, start, stop in part.runs.tolist():
        left, right = start - canvas.col0, stop - canvas.col0
        low, high = max(0, left), min(width, right)
        if low < high:
            for other_row in (row - 1, row + 1):
                if 0 <= other_row < height:
                    found.update(np.unique(world.labels[other_row, low:high]).tolist())
        for column in (left - 1, right):
            if 0 <= column < width:
                found.add(int(world.labels[row, column]))
    found.discard(-1)
    return found


def _overlap(game_map: Eu5Map, canvas: Canvas, world: NewWorld, cells: set[int]) -> dict[int, int]:
    """Dominant installed closed-ocean location under each eligible generated zone."""
    count = len(game_map.keys)
    eligible = np.zeros(len(world.classes) + 1, dtype=bool)
    eligible[list(cells)] = True
    closed = game_map.ambiguous & np.array(
        [
            kind is CellClass.SEA and name in OCEANS
            for kind, name in zip(game_map.classes, game_map.continents, strict=True)
        ],
        dtype=bool,
    )
    tallies: dict[int, dict[int, int]] = {}
    for first in range(0, world.labels.shape[0], 256):
        rows = slice(first, first + 256)
        old = canvas.rolled(game_map.labels, rows)[
            :, canvas.col0 : canvas.col0 + canvas.mask.shape[1]
        ]
        new = world.labels[rows]
        keep = eligible[new] & closed[old]
        packed, sizes = np.unique(
            new[keep].astype(np.int64) * count + old[keep], return_counts=True
        )
        for value, size in zip(packed.tolist(), sizes.tolist(), strict=True):
            cell, source = divmod(value, count)
            values = tallies.setdefault(cell, {})
            values[source] = values.get(source, 0) + size
    return {
        cell: min(values, key=lambda source: (-values[source], source))
        for cell, values in tallies.items()
    }


class _Components:
    def __init__(self, count: int) -> None:
        self.parents: list[int] = list(range(count))

    def root(self, node: int) -> int:
        while self.parents[node] != node:
            self.parents[node] = self.parents[self.parents[node]]
            node = self.parents[node]
        return node

    def join(self, first: int, second: int) -> None:
        first, second = self.root(first), self.root(second)
        self.parents[max(first, second)] = min(first, second)


def _groups(
    canvas: Canvas, world: NewWorld, owners: dict[int, int], candidates: set[int]
) -> dict[int, dict[int, list[int]]]:
    """Connected final components, treating retained water as graph nodes."""
    touching = [_neighbours(part, canvas, world) & candidates for part in canvas.ocean_parts]
    # A source reached at the boundary takes precedence over positional naming.
    boundary: dict[int, set[int]] = {}
    for part, cells in zip(canvas.ocean_parts, touching, strict=True):
        for cell in cells:
            boundary.setdefault(cell, set()).add(part.source)
    for cell, sources in boundary.items():
        if owners.get(cell) not in sources:
            owners[cell] = min(sources)
    count = len(world.classes)
    components = _Components(count + len(canvas.ocean_parts))
    for first, second in world.edges:
        if first in owners and second in owners and owners[first] == owners[second]:
            components.join(first, second)
    for number, (part, cells) in enumerate(zip(canvas.ocean_parts, touching, strict=True)):
        for cell in cells:
            if owners.get(cell) == part.source:
                components.join(count + number, cell)
    groups: dict[int, dict[int, list[int]]] = {}
    for cell, source in sorted(owners.items()):
        groups.setdefault(source, {}).setdefault(components.root(cell), []).append(cell)
    for number, part in enumerate(canvas.ocean_parts):
        groups.setdefault(part.source, {}).setdefault(components.root(count + number), []).append(
            count + number
        )
    return groups


def _apply_component(  # noqa: PLR0913, PLR0917 - one identity and its geometric members.
    result: OceanPlan,
    plan: Plan,
    canvas: Canvas,
    world: NewWorld,
    identity: PlannedCell,
    nodes: list[int],
    original_color: int,
) -> None:
    """Emit one graph component, its bounded pixel runs and a valid locator."""
    count = len(world.classes)
    generated = [node for node in nodes if node < count]
    for cell in generated:
        plan.cells[cell] = identity
    if not generated and identity.key not in result.retained:
        result.extra.append(identity)
    for node in nodes:
        if node >= count:
            part = canvas.ocean_parts[node - count]
            if identity.color != original_color:
                result.patches.append((part, identity.color))
    if generated:
        anchor = max(generated, key=lambda cell: (int(world.pixels[cell]), -cell))
        row, column = world.interior[anchor].tolist()
        result.anchors[identity.key] = (row, int(canvas.world_column(column)))
    else:
        part = canvas.ocean_parts[nodes[0] - count]
        row, left, right = max(part.runs.tolist(), key=lambda run: run[2] - run[1])
        result.anchors[identity.key] = (
            row,
            (int(left + right) // 2 - canvas.roll) % canvas.shape[1],
        )


def plan_oceans(  # noqa: PLR0913, PLR0917 - planning reads the map and generated world.
    game_map: Eu5Map,
    canvas: Canvas,
    world: NewWorld,
    plan: Plan,
    hierarchy: dict[str, Location],
    closed: frozenset[int],
    keys: KeySpace,
) -> OceanPlan:
    """Join connected closed water by source name; preserve every other final component."""
    result = OceanPlan()
    candidates = {cell for cell in closed if plan.cells[cell].continent in OCEANS}
    owners = _overlap(game_map, canvas, world, candidates)
    groups = _groups(canvas, world, owners, candidates)
    count = len(world.classes)
    used = {int(value) for value in game_map.colors.tolist()} | {cell.color for cell in plan.cells}
    color_cursor = 1
    for source, components in sorted(groups.items()):
        original = game_map.keys[source]
        location = hierarchy[original]

        def weight(nodes: list[int]) -> tuple[int, int]:
            rest = sum(canvas.ocean_parts[n - count].pixels for n in nodes if n >= count)
            generated = sum(int(world.pixels[n]) for n in nodes if n < count)
            return rest, generated

        ordered = sorted(
            components.values(), key=lambda nodes: (*(-v for v in weight(nodes)), min(nodes))
        )
        for number, nodes in enumerate(ordered):
            if number == 0:
                name, color, province = original, int(game_map.colors[source]), location.province
                result.retained.add(name)
            else:
                name = keys.next("rnw_ocean_", 5)
                province = keys.next("rnw_prov_", 5)
                while color_cursor in used:
                    color_cursor += 1
                color = color_cursor
                used.add(color)
            identity = PlannedCell(
                name,
                reference(original),
                color,
                CellClass.SEA,
                province,
                location.area,
                location.region,
                location.subcontinent,
                location.continent,
            )
            result.sources[name] = original
            if number:
                plan.province_names[province] = reference(original)
            _apply_component(
                result, plan, canvas, world, identity, nodes, int(game_map.colors[source])
            )
    # Remove obsolete generated province bookkeeping after the final water identities
    # have been planned. No serialized content exists at this point.
    present = {cell.province for cell in plan.cells} | {cell.province for cell in result.extra}
    plan.new_areas = {
        area: [p for p in provinces if p in present]
        for area, provinces in plan.new_areas.items()
        if any(p in present for p in provinces)
    }
    plan.province_names = {
        key: value for key, value in plan.province_names.items() if key in present
    }
    result.stats = {
        "named_ocean_sources": len(groups),
        "shared_ocean_locations": len(result.retained),
        "ocean_remainder_fragments": len(canvas.ocean_parts),
        "ocean_identity_recolours": sum(part.pixels for part, _ in result.patches),
    }
    return result
