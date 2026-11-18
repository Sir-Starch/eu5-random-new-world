"""Time shared geography on real inputs without producing or installing a game mod."""

# ruff: noqa: INP001
from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING

import numpy as np

from rnw.continent_domains import CONTINENTS, plan_domains
from rnw.eu5_biomes import climate_grid, size_model, template_attributes
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
from rnw.topology import adjacency_pairs

if TYPE_CHECKING:
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


def profile(game_dir: Path, names: list[str], seed: int) -> dict[str, object]:
    started = perf_counter()
    threads = configure()
    game = timed("load map", lambda: load_map(game_dir))
    settings = {key: CONTINENTS[key].geography() for key in names}
    domains = timed("plan continent domains", lambda: plan_domains(game, settings))
    templates = (game_dir / TEMPLATES).read_text(encoding="utf-8-sig")
    store = DecalStore(game_dir, game.labels.shape)
    original_heights = timed("read heights", store.world_heights)
    sizes = timed(
        "calibrate sizes",
        lambda: size_model(game, template_attributes(templates), original_heights),  # noqa: F821
    )
    labels = game.labels.copy()
    height = original_heights.astype(np.int32)
    del original_heights
    kinds = list(game.classes)
    regions: dict[str, object] = {}
    for domain in domains:
        key = domain.continent.key
        canvas = domain.legacy_canvas
        bands = None if canvas is None else current_bands(game, canvas, read_waters(templates))
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
        )
        if canvas is not None:
            moved = moved_pixels_of(place_islands(game, canvas, world.moves))
            if moved is not None:
                labels[moved.new_rows, moved.new_columns] = game.labels[moved.rows, moved.columns]
                height[moved.new_rows, moved.new_columns] = height[moved.rows, moved.columns]
        _place(domain, world, labels, height, len(kinds))
        kinds.extend(world.classes)
        regions[key] = {
            "seconds": round(perf_counter() - start, 3),
            "domain_pixels": int(np.count_nonzero(domain.mask)),
            "footprint_pixels": int(np.count_nonzero(domain.footprint)),
            "replace_pixels": int(world.pixels.sum()),
            "domain_width": domain.mask.shape[1],
            "domain_height": domain.mask.shape[0],
            "land_cells": world.classes.count(CellClass.LAND)
            + world.classes.count(CellClass.WASTELAND),
            "sea_cells": world.classes.count(CellClass.SEA),
            "wraps": domain.seam is not None,
        }
        del world, bands
    sea = np.array([kind is CellClass.SEA for kind in kinds], dtype=bool)
    climate = timed(
        "shared world climate", lambda: climate_grid(sea[labels], height, seasonal=True)
    )
    contacts = timed("shared map contacts", lambda: adjacency_pairs(labels, wrap_x=True))
    return {
        "seconds": round(perf_counter() - started, 3),
        "peak": peak_gib().removeprefix(", peak "),
        "threads": threads,
        "stage_slots": stage_workers(),
        "seed": seed,
        "regions": regions,
        "climate_blocks": climate.rain.size,
        "location_contacts": contacts.size,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game_dir", type=Path)
    parser.add_argument("continents", nargs="+", choices=tuple(CONTINENTS))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(json.dumps(profile(args.game_dir, args.continents, args.seed), indent=2))


if __name__ == "__main__":
    main()
