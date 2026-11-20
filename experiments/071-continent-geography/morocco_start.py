"""Exercise regional country setup on an existing prototype geography."""

# ruff: noqa: INP001
from __future__ import annotations

from typing import TYPE_CHECKING

from rnw.content_inventory import DEFINITIONS, SETUP_DIR
from rnw.eu5_africa_start import (
    COUNTRIES_BLOCK,
    COUNTRIES_FILE,
    IBERIAN_HOLDINGS,
    algeciras,
    apply_morocco_start,
    plan_morocco,
    reserve_morocco,
)
from rnw.eu5_natives import COUNTRY_DIR, vanilla_colors
from rnw.eu5_newworld import Plan, PlannedCell
from rnw.eu5_nw_export import vanilla_localization_keys
from rnw.eu5_oceans import emitted_cells
from rnw.eu5_remap import RemapAccess, build_remap
from rnw.eu5_rewrite import PERSONAL_PLACES, owned_locations, retained_capitals
from rnw.geography import read_locations
from rnw.loc_keys import KeySpace, key_hashes
from rnw.model import CellClass
from rnw.pdx import Block, parse
from rnw.settings import MoroccoPolicy

if TYPE_CHECKING:
    from pathlib import Path

    from rnw.continent_domains import Domain
    from rnw.eu5_biomes import VanillaLocations
    from rnw.eu5_map import Eu5Map
    from rnw.eu5_newworld import VanillaGeometry
    from rnw.eu5_remap import GeographicRemap
    from rnw.eu5_start import Country
    from rnw.newworld import NewWorld


def _personal_locations(texts: dict[str, str], removed: set[str]) -> set[str]:
    sources: set[str] = set()
    for name, manager, field in PERSONAL_PLACES:
        holder = parse(texts[name]).block(manager)
        if holder is None:
            message = f"Missing {manager}"
            raise ValueError(message)
        for record in holder.entries:
            value = record.value.first(field) if isinstance(record.value, Block) else None
            if value is not None and isinstance(value.value, str) and value.value in removed:
                sources.add(value.value)
    return sources


def _algeciras(game_dir: Path, seed: int, keys: KeySpace | None = None) -> Country:
    reserved = frozenset(
        entry.key
        for path in sorted((game_dir / COUNTRY_DIR).glob("*.txt"))
        for entry in parse(path.read_text(encoding="utf-8-sig")).entries
        if entry.key
    )
    if keys is None:
        keys = KeySpace(key_hashes(vanilla_localization_keys(game_dir)))
    return algeciras(seed, reserved, keys, vanilla_colors(game_dir))


def _recipient(text: str, africa: set[str], *, retired: bool) -> dict[str, object]:
    countries = parse(text).block(*COUNTRIES_BLOCK)
    if countries is not None:
        for entry in countries.entries:
            if entry.key and isinstance(entry.value, Block):
                holdings = owned_locations(entry.value)
                if holdings.issuperset(IBERIAN_HOLDINGS):
                    capital = entry.value.first("capital")
                    return {
                        "recipient": entry.key,
                        "capital": None if capital is None else capital.value,
                        "african_holdings": len(holdings & africa),
                        "iberian_holdings": list(IBERIAN_HOLDINGS),
                        "morocco_retired": retired,
                    }
    message = "Missing projected holder of the four Iberian holdings"
    raise ValueError(message)


def morocco_trials(  # noqa: PLR0913 - installed data and the generated African domain.
    game_dir: Path,
    game: Eu5Map,
    vanilla: VanillaLocations,
    domain: Domain,
    world: NewWorld,
    *,
    seed: int,
    policies: tuple[MoroccoPolicy, ...],
) -> dict[str, dict[str, object]]:
    locations = read_locations(game_dir / DEFINITIONS)
    removed = {
        key
        for place in locations
        if place.continent == "africa"
        for key in (place.key, place.province)
    }
    texts = {
        path.name: path.read_text(encoding="utf-8-sig")
        for path in sorted((game_dir / SETUP_DIR).glob("*.txt"))
    }
    sources = _personal_locations(texts, removed)
    index = {key: number for number, key in enumerate(game.keys)}
    original = {
        key: (int(vanilla.points[index[key], 0]), int(vanilla.points[index[key], 1]))
        for key in sources | {*IBERIAN_HOLDINGS, "fez"}
    }
    nodes = [
        PlannedCell(f"prototype_africa_{i}", "", 0, kind, "", "", "", "", "africa")
        for i, kind in enumerate(world.classes)
    ]
    remap = build_remap(
        [
            (
                key,
                CellClass.LAND,
                original[key][0] - domain.first_row,
                (original[key][1] - domain.first_column) % domain.map_width,
            )
            for key in sorted(sources)
        ],
        Plan(nodes),
        world.centroids,
        {},
        access=RemapAccess(),
    )
    africa = {
        node.key: (
            int(row) + domain.first_row,
            (int(column) + domain.first_column) % domain.map_width,
        )
        for (row, column), node in zip(world.centroids, nodes, strict=True)
        if node.kind is CellClass.LAND
    }
    african_keys = set(africa)
    final = (set(game.keys) - removed) | african_keys
    emirate = _algeciras(game_dir, seed) if MoroccoPolicy.EMIRATE in policies else None
    results: dict[str, dict[str, object]] = {}
    for policy in policies:
        start = plan_morocco(africa, original, domain.map_width, policy)
        result = apply_morocco_start(
            start,
            texts,
            removed,
            {},
            location_replacements=remap.locations,
            replacement_capitals={"MAM": "damascus"},
            final_locations=final,
            emirate=emirate if policy is MoroccoPolicy.EMIRATE else None,
        )
        results[policy] = _recipient(
            result.texts[COUNTRIES_FILE], african_keys, retired="MOR" in result.removed_ids
        )
    return results


def map_morocco_trials(  # noqa: PLR0913 - each policy reads the same completed map and setup.
    game_dir: Path,
    game: Eu5Map,
    plan: Plan,
    world: NewWorld,
    *,
    geometry: VanillaGeometry,
    removed: set[str],
    remap: GeographicRemap,
    keys: KeySpace,
    seed: int,
    policies: tuple[MoroccoPolicy, ...],
) -> dict[str, dict[str, object]]:
    """Check the actual identities chosen by final map and coast planning."""
    texts = {
        path.name: path.read_text(encoding="utf-8-sig")
        for path in sorted((game_dir / SETUP_DIR).glob("*.txt"))
    }
    original = {
        key: (int(geometry.rows[i]), int(geometry.columns[i])) for i, key in enumerate(game.keys)
    }
    africa = {cell.key for cell in plan.cells if cell.continent == "africa"}
    final = (set(game.keys) - removed) | {cell.key for cell in emitted_cells(plan)}
    discarded = removed | remap.provinces.keys() | remap.areas.keys()
    capitals = retained_capitals(
        texts[COUNTRIES_FILE],
        discarded,
        original,
        game.labels.shape[1],
        preferred={"MAM": "damascus"},
    )
    original_tags = _country_tags(texts[COUNTRIES_FILE])
    emirate = _algeciras(game_dir, seed, keys) if MoroccoPolicy.EMIRATE in policies else None
    out: dict[str, dict[str, object]] = {}
    for policy in policies:
        result = apply_morocco_start(
            reserve_morocco(plan, world, original, policy),
            texts,
            discarded,
            {},
            location_replacements=remap.locations,
            replacement_capitals=capitals,
            final_locations=final,
            emirate=emirate if policy is MoroccoPolicy.EMIRATE else None,
        )
        out[policy] = _recipient(
            result.texts[COUNTRIES_FILE], africa, retired="MOR" in result.removed_ids
        )
        out[policy]["retired_country_tags"] = len(
            original_tags - _country_tags(result.texts[COUNTRIES_FILE])
        )
    return out


def _country_tags(text: str) -> set[str]:
    countries = parse(text).block(*COUNTRIES_BLOCK)
    return {entry.key for entry in countries.entries if entry.key} if countries else set()
