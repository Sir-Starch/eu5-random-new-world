"""Inspect the local 1337 inputs for each generated continent on one read of the map."""

# ruff: noqa: INP001
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from rnw.continent_domains import CONTINENTS
from rnw.eu5_biomes import material_frequencies, template_attributes, vanilla_locations
from rnw.eu5_map import load_map
from rnw.eu5_natives import regional_populations
from rnw.eu5_nw_export import TEMPLATES
from rnw.parallel import configure
from rnw.timing import timed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game_dir", type=Path)
    args = parser.parse_args()
    root: Path = args.game_dir
    _ = configure()
    game = timed("load map", lambda: load_map(root))
    templates = template_attributes((root / TEMPLATES).read_text(encoding="utf-8-sig"))
    # Population and resource inputs use locations and their contacts, with no height dependency.
    geometry = timed(
        "vanilla geometry",
        lambda: vanilla_locations(game.labels, np.zeros(game.labels.shape, dtype=np.uint16)),
    )
    populations = timed(
        "shared 1337 population inputs",
        lambda: regional_populations(root, game, geometry, templates, CONTINENTS.keys()),
    )
    result = {}
    for name, profile in populations.items():
        materials = material_frequencies(game, templates, geometry, name)
        result[name] = {
            "land": profile.land_locations,
            "land_owned": profile.owned_locations,
            "population_milli": profile.population,
            "population_per_location_milli": profile.population_per_location,
            "cultures": len(profile.cultures),
            "languages": len({language for language, _ in profile.languages.values() if language}),
            "place_names": len(profile.places),
            "religions": dict(
                sorted(
                    ((religion, values[1]) for religion, values in profile.religions.items()),
                    key=lambda row: (-row[1], row[0]),
                )
            ),
            "settled_climate_density": profile.density,
            "landed_templates": sorted(
                {culture.state_include for culture in profile.cultures.values()} - {""}
            ),
            "tribal_templates": sorted(
                {culture.tribe_include for culture in profile.cultures.values()} - {""}
            ),
            "resources": {shore: dict(counts.most_common()) for shore, counts in materials.items()},
        }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
