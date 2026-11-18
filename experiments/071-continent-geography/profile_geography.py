"""Time shared geography on real inputs without producing or installing a game mod."""

# ruff: noqa: INP001
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING

import numpy as np

from rnw.continent_domains import CONTINENTS, plan_domains
from rnw.eu5_biomes import (
    Generated,
    MaterialRegion,
    assign_biomes,
    climate_grid,
    size_model,
    template_attributes,
    vanilla_locations,
)
from rnw.eu5_canvas import NEW_WORLD, place_islands
from rnw.eu5_islands import moved_pixels_of
from rnw.eu5_map import load_map
from rnw.eu5_nw_export import TEMPLATES
from rnw.eu5_seas import current_bands, read_waters
from rnw.eu5_terrain import DecalStore
from rnw.model import CellClass
from rnw.newworld import generate_new_world
from rnw.parallel import configure, stage_workers
from rnw.rng import derive_seed
from rnw.timing import peak_gib, timed
from rnw.topology import LOW_BITS, PAIR_SHIFT, adjacency_pairs

if TYPE_CHECKING:
    from collections.abc import Mapping

    from numpy.typing import NDArray

    from rnw.continent_domains import Domain
    from rnw.newworld import NewWorld


def _place(
    domain: Domain,
    world: NewWorld,
    labels: NDArray[np.int32],
    height: NDArray[np.int32],
    start: int,
) -> None:
    for local, global_ in domain.spans():
        for top in range(0, world.labels.shape[0], 256):
            rows = slice(top, min(top + 256, world.labels.shape[0]))
            original = slice(domain.first_row + rows.start, domain.first_row + rows.stop)
            cells = world.labels[rows, local]
            mask = cells >= 0
            np.copyto(labels[original, global_], cells + start, where=mask)
            np.copyto(height[original, global_], world.elevation[rows, local], where=mask)


def _composed_cells(
    kinds: list[CellClass],
    retained: int,
    contacts: NDArray[np.int64],
    samples: list[tuple[NDArray[np.int64], NDArray[np.int64], NDArray[np.int64]]],
) -> Generated:
    points, height, spread = zip(*samples, strict=True)
    pairs = np.stack((contacts >> PAIR_SHIFT, contacts & LOW_BITS), axis=1)
    sea = np.array([kind is CellClass.SEA for kind in kinds], dtype=bool)
    coastal = np.zeros(len(kinds), dtype=bool)
    for land, water in (pairs.T, pairs.T[::-1]):
        coastal[land[sea[water]]] = True
    return Generated(
        kinds=tuple(kinds[retained:]),
        points=np.concatenate(points),
        mean_height=np.concatenate(height),
        spread=np.concatenate(spread),
        edges=tuple((int(a) - retained, int(b) - retained) for a, b in pairs if a >= retained),
        coastal=coastal[retained:],
    )


def profile(  # noqa: PLR0915 - the prototype records each phase.
    game_dir: Path,
    presets: Mapping[str, str | None],
    seed: int,
    *,
    materials: bool = False,
) -> dict[str, object]:
    started = perf_counter()
    threads = configure()
    game = timed("load map", lambda: load_map(game_dir))
    settings = {key: CONTINENTS[key].geography(preset) for key, preset in presets.items()}
    domains = timed("plan continent domains", lambda: plan_domains(game, settings))
    text = (game_dir / TEMPLATES).read_text(encoding="utf-8-sig")
    templates = template_attributes(text)
    store = DecalStore(game_dir, game.labels.shape)
    original_heights = timed("read heights", store.world_heights)
    sizes = timed(
        "calibrate sizes",
        lambda: size_model(game, templates, original_heights),  # noqa: F821
    )
    training = None
    if materials:
        training = (
            timed(
                "vanilla location statistics",
                lambda: vanilla_locations(game.labels, original_heights),  # noqa: F821
            ),
            timed(
                "vanilla climate for biomes",
                lambda: climate_grid(
                    np.array([kind is CellClass.SEA for kind in game.classes], dtype=bool)[
                        game.labels
                    ],
                    original_heights,  # noqa: F821
                    seasonal=True,
                ),
            ),
        )
    labels = game.labels.copy()
    height = original_heights.astype(np.int32)
    del original_heights
    kinds = list(game.classes)
    regions: dict[str, dict[str, object]] = {}
    samples: list[tuple[NDArray[np.int64], NDArray[np.int64], NDArray[np.int64]]] = []
    rolls: dict[str, MaterialRegion] = {}
    retained = len(kinds)
    for domain in domains:
        key = domain.continent.key
        canvas = domain.legacy_canvas
        bands = None if canvas is None else current_bands(game, canvas, read_waters(text))
        start = perf_counter()
        world = generate_new_world(
            domain.mask,
            seed=seed if key == NEW_WORLD else derive_seed(seed, "continent", key),
            settings=settings[key],
            template=domain.footprint,
            groups=() if canvas is None else canvas.footprints,
            seam=domain.seam,
            sizes=sizes,
            map_rows=(domain.first_row, game.labels.shape[0]),
            sea_bands=bands,
            outside_land=domain.contact_land,
        )
        if canvas is not None:
            moved = moved_pixels_of(place_islands(game, canvas, world.moves))
            if moved is not None:
                labels[moved.new_rows, moved.new_columns] = game.labels[moved.rows, moved.columns]
                height[moved.new_rows, moved.new_columns] = height[moved.rows, moved.columns]
        _place(domain, world, labels, height, len(kinds))
        if materials:
            rolls[key] = MaterialRegion(
                range(len(kinds) - retained, len(kinds) - retained + len(world.classes)),
                derive_seed(seed, "materials", key),
            )
            points = world.centroids.copy()
            points[:, 0] += domain.first_row
            points[:, 1] = (points[:, 1] + domain.first_column) % domain.map_width
            samples.append((points, world.mean_elevation, world.spread))
        kinds.extend(world.classes)
        land = [
            index
            for index, kind in enumerate(world.classes)
            if kind in {CellClass.LAND, CellClass.WASTELAND}
        ]
        regions[key] = {
            "preset": presets[key] or domain.continent.preset,
            "seconds": round(perf_counter() - start, 3),
            "domain_pixels": int(np.count_nonzero(domain.mask)),
            "footprint_pixels": int(np.count_nonzero(domain.footprint)),
            "replace_pixels": int(world.pixels.sum()),
            "domain_width": domain.mask.shape[1],
            "domain_height": domain.mask.shape[0],
            "land_cells": len(land),
            "land_pixels": int(world.pixels[land].sum()),
            "sea_cells": world.classes.count(CellClass.SEA),
            "wraps": domain.seam is not None,
        }
        if domain.land_interface is not None:
            passable = np.array([kind is CellClass.LAND for kind in world.classes] + [False])
            regions[key]["passable_border_pixels"] = int(
                np.count_nonzero(domain.land_interface & passable[world.labels])
            )
        del world, bands
    sea = np.array([kind is CellClass.SEA for kind in kinds], dtype=bool)
    climate = timed(
        "shared world climate", lambda: climate_grid(sea[labels], height, seasonal=True)
    )
    contacts = timed("shared map contacts", lambda: adjacency_pairs(labels, wrap_x=True))
    active_locations = np.zeros(len(kinds), dtype=bool)
    protected = np.array(
        [
            continent not in presets and kind is not CellClass.SEA
            for continent, kind in zip(game.continents, game.classes, strict=True)
        ],
        dtype=bool,
    )
    changed_protected = 0
    for top in range(0, labels.shape[0], 256):
        rows = slice(top, top + 256)
        active_locations[labels[rows]] = True
        changed_protected += int(
            np.count_nonzero((labels[rows] != game.labels[rows]) & protected[game.labels[rows]])
        )
    if training is not None:
        cells = _composed_cells(kinds, retained, contacts, samples)
        before = perf_counter()
        biomes, _ = assign_biomes(
            game_map=game,
            templates=templates,
            vanilla=training[0],
            vanilla_grid=training[1],
            final_grid=climate,
            cells=cells,
            seed=seed,
            open_climate=True,
            pooled_resources=True,
            regional_resources=rolls,
        )
        for key, region in rolls.items():
            counts = Counter(
                biomes.raw_material[cell] for cell in region.cells if biomes.raw_material[cell]
            )
            regions[key]["raw_materials"] = dict(counts.most_common())
        materials_seconds = round(perf_counter() - before, 3)
    else:
        materials_seconds = None
    return {
        "seconds": round(perf_counter() - started, 3),
        "peak": peak_gib().removeprefix(", peak "),
        "threads": threads,
        "stage_slots": stage_workers(),
        "seed": seed,
        "regions": regions,
        "populated_location_ids": int(np.count_nonzero(active_locations)),
        "retained_non_marine_pixels_changed": changed_protected,
        "biomes_and_materials_seconds": materials_seconds,
        "climate_blocks": climate.rain.size,
        "location_contacts": contacts.size,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game_dir", type=Path)
    parser.add_argument("continents", nargs="+", choices=tuple(CONTINENTS))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--materials", action="store_true")
    parser.add_argument("--preset", action="append", default=[], metavar="CONTINENT=PRESET")
    args = parser.parse_args()
    presets = dict.fromkeys(args.continents)
    for value in args.preset:
        continent, equals, preset = value.partition("=")
        if not equals or continent not in presets or not preset:
            parser.error(
                f"Expected --preset CONTINENT=PRESET for a selected continent, got {value}"
            )
        if presets[continent] is not None:
            parser.error(f"More than one preset specified for {continent}")
        presets[continent] = preset
    print(
        json.dumps(profile(args.game_dir, presets, args.seed, materials=args.materials), indent=2)
    )


if __name__ == "__main__":
    main()
