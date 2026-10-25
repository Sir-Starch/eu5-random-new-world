"""Tordesillas on the New World's continuous longitude axis.

The installed east-of predicate compares canonical raster columns, including at the
seam. The generated continent has one continuous axis already: the canvas columns.
Expose those immutable coordinates through vanilla scripted geographies/values, and
use them in this situation's comparisons and final province allocation. No variables,
startup repair, engine changes, new raster pass or treaty-balance changes are needed.
"""

# NumPy stubs type scalar indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rnw.geography import parse_locations
from rnw.model import CellClass
from rnw.pdx import Block, Edits, Entry, parse

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from rnw.eu5_canvas import Canvas
    from rnw.eu5_map import Eu5Map
    from rnw.eu5_newworld import Plan, VanillaGeometry
    from rnw.newworld import NewWorld

PREFIX = "in_game/common/"
SITUATION = PREFIX + "situations/treaty_of_tordesillas.txt"
EVENTS = "in_game/events/situations/treaty_of_tordesillas.txt"
ACTIONS = PREFIX + "generic_actions/treaty_of_tordesillas.txt"
EFFECTS = PREFIX + "scripted_effects/situation_effects.txt"
LOCATION = "rnw_treaty_location_longitude"
PROVINCE = "rnw_treaty_province_longitude"
TRIGGER = "rnw_treaty_is_east_of"


class TreatyError(ValueError):
    """A changed vanilla anchor or incomplete longitude table."""


@dataclass(frozen=True)
class Longitudes:
    """Integer pixel coordinates on one axis, cut in the Pacific before the canvas."""

    width: int
    locations: Mapping[str, int]
    provinces: Mapping[str, int]

    def __post_init__(self) -> None:
        if self.width <= 1 or not self.locations or not self.provinces:
            message = "Incomplete treaty longitude tables"
            raise TreatyError(message)
        for values in (self.locations, self.provinces):
            if any(not 0 <= value < self.width for value in values.values()):
                message = "Treaty longitude outside the continuous map axis"
                raise TreatyError(message)


def coordinates(  # noqa: PLR0913 - already-built physical and identity tables, no raster read.
    game_map: Eu5Map,
    *,
    canvas: Canvas,
    world: NewWorld,
    plan: Plan,
    geometry: VanillaGeometry,
    definitions: str,
) -> Longitudes:
    """Dry-land centroids on the continuous axis; no water can be a treaty origin.

    The adapted comparisons are all gated to land/colonies. Province distribution
    likewise requires land; its coordinates aggregate that province's dry land.
    Water-only identities, including partially retained ocean fragments, need no
    made-up coordinate and are deliberately absent from these tables.
    """
    dry = {CellClass.LAND, CellClass.WASTELAND, CellClass.NON_OWNABLE}
    kinds = dict(zip(game_map.keys, game_map.classes, strict=True))
    kinds.update({cell.key: cell.kind for cell in plan.cells})
    if plan.oceans is not None:
        kinds.update({cell.key: cell.kind for cell in plan.oceans.extra})
    all_locations = parse_locations(definitions)
    if any(loc.key not in kinds for loc in all_locations):
        message = "Final treaty geography has an unknown location class"
        raise TreatyError(message)
    final = tuple(loc for loc in all_locations if kinds[loc.key] in dry)
    present = {loc.key for loc in final}
    weights: dict[str, int] = defaultdict(int)
    sums: dict[str, int] = defaultdict(int)
    for i, cell in enumerate(plan.cells):
        if cell.key not in present:
            continue
        weight = int(world.pixels[i])
        if weight <= 0:
            message = "A generated treaty location has no pixels"
            raise TreatyError(message)
        weights[cell.key] += weight
        sums[cell.key] += weight * int(world.centroids[i, 1])
    # Coordinates in vanilla_geometry are rolled. Subtracting col0 puts both
    # retained and generated points on the canvas's continuous west-to-east axis.
    for i, key in enumerate(game_map.keys):
        if key in present and key not in weights:
            weight = int(geometry.pixels[i])
            weights[key] = weight
            sums[key] = weight * ((int(geometry.columns[i]) - canvas.col0) % canvas.shape[1])
    if set(weights) != present:
        message = "A final land location has no physical treaty coordinate"
        raise TreatyError(message)
    province_weights: dict[str, int] = defaultdict(int)
    province_sums: dict[str, int] = defaultdict(int)
    for loc in final:
        province_weights[loc.province] += weights[loc.key]
        province_sums[loc.province] += sums[loc.key]
    return Longitudes(
        canvas.shape[1],
        {key: sums[key] // weights[key] for key in sorted(weights)},
        {key: province_sums[key] // province_weights[key] for key in sorted(province_weights)},
    )


def metadata(axis: Longitudes) -> dict[str, bytes]:
    """Readonly coordinates encoded in O(log(width)) native geography memberships.

    Location and province bits are separate: listing a province in a geography
    also includes its locations, which must not contaminate location coordinates.
    No mutable per-location variables or campaign initialization are involved.
    """
    geographies: list[str] = []
    values: list[str] = []
    for name, kind, positions in (
        (LOCATION, "location", axis.locations),
        (PROVINCE, "province_definition", axis.provinces),
    ):
        additions: list[str] = []
        for bit in range((axis.width - 1).bit_length()):
            keys = sorted(key for key, value in positions.items() if value & (1 << bit))
            if not keys:
                continue
            geography = f"{name}_bit_{bit}"
            rows = [" ".join(keys[i : i + 8]) for i in range(0, len(keys), 8)]
            geographies.append(
                f"{geography} = {{\n\t{kind} = {{\n"
                + "".join(f"\t\t{row}\n" for row in rows)
                + "\t}\n}\n"
            )
            condition = f"is_in_scripted_geography = scripted_geography:{geography}"
            additions.append(
                f"\tif = {{\n\t\tlimit = {{ {condition} }}\n\t\tadd = {1 << bit}\n\t}}\n"
            )
        values.append(f"{name} = {{\n\tvalue = 0\n{''.join(additions)}}}\n")
    trigger = (
        f'{TRIGGER} = {{\n\thidden_trigger = {{\n\t\t{LOCATION} > "$target$.{LOCATION}"\n\t}}\n}}\n'
    )
    return {
        PREFIX + "scripted_geography/rnw_treaty_longitudes.txt": "\n".join(geographies).encode(),
        PREFIX + "script_values/rnw_treaty_longitudes.txt": "\n".join(values).encode(),
        PREFIX + "scripted_triggers/rnw_treaty_longitudes.txt": trigger.encode(),
    }


def _entries(block: Block) -> list[Entry]:
    result: list[Entry] = []
    for entry in block.entries:
        result.append(entry)
        if isinstance(entry.value, Block):
            result.extend(_entries(entry.value))
    return result


def replace_comparisons(text: str, expected: int) -> str:
    """Rewrite parsed predicates, never comments or strings, with exact-count guards."""
    entries = [entry for entry in _entries(parse(text)) if entry.key == "is_east_of"]
    if len(entries) != expected:
        message = f"Expected {expected} treaty east predicates, found {len(entries)}"
        raise TreatyError(message)
    edits = Edits()
    for entry in entries:
        if not isinstance(entry.value, str) or entry.op != "=":
            message = "Treaty east predicate changed shape"
            raise TreatyError(message)
        edits.delete(entry)
        edits.insert(entry.start, f"{TRIGGER} = {{ target = {entry.value} }}")
    return edits.apply(text)


def replace_distribution(text: str) -> str:
    """Keep vanilla claim gates/effects, replace the two raster-ordered iterators.

    Equality stays unassigned, including the line province, as with vanilla's
    strict east/west traversal. Existing claims and ownership keep their gates.
    """
    root = parse(text).block("distribute_world", "situation:treaty_of_tordesillas")
    line = root.block("var:var_line_location.province_definition") if root else None
    if line is None:
        message = "Missing treaty distribution line-province anchor"
        raise TreatyError(message)
    expected = {"every_east_of_province_definition": ">", "every_west_of_province_definition": "<"}
    if [entry.key for entry in line.entries] != list(expected):
        message = "Treaty province distribution changed shape"
        raise TreatyError(message)
    edits = Edits()
    for entry, operator in zip(line.entries, expected.values(), strict=True):
        if not isinstance(entry.value, Block) or (limit := entry.value.block("limit")) is None:
            message = "Missing treaty distribution limit"
            raise TreatyError(message)
        start = text.index("{", entry.start, entry.end)
        edits.deletions.append((entry.start, start))
        edits.insert(entry.start, "every_province_definition = ")
        target = (
            f"situation:treaty_of_tordesillas.var:var_line_location.province_definition.{PROVINCE}"
        )
        edits.insert(
            limit.open + 1,
            f'\n\t\t\t\t\t{PROVINCE} {operator} "{target}"\n',
        )
    return edits.apply(text)


def adapt(game_dir: Path, outputs: dict[str, bytes], axis: Longitudes) -> dict[str, int]:
    """Build the world's treaty scripts from installed/remapped sources, once."""
    for path, count in ((SITUATION, 4), (EVENTS, 4), (ACTIONS, 4)):
        source = outputs.get(path)
        text = (
            source.decode("utf-8-sig")
            if source is not None
            else (game_dir / "game" / path).read_bytes().decode("utf-8-sig")
        )
        outputs[path] = replace_comparisons(text, count).encode("utf-8-sig")
    source = outputs.get(EFFECTS)
    text = (
        source.decode("utf-8-sig")
        if source is not None
        else (game_dir / "game" / EFFECTS).read_bytes().decode("utf-8-sig")
    )
    outputs[EFFECTS] = replace_distribution(text).encode("utf-8-sig")
    outputs.update(metadata(axis))
    return {
        "location_coordinates": len(axis.locations),
        "province_coordinates": len(axis.provinces),
        "east_predicates": 12,
        "province_iterators": 2,
    }
