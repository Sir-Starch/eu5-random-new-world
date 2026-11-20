"""Time shared geography on real inputs without producing or installing a game mod."""

# ruff: noqa: INP001
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import replace
from functools import partial
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING

import numpy as np
from morocco_start import map_morocco_trials, morocco_trials

from rnw.continent_domains import CONTINENTS, plan_domains
from rnw.continent_world import WorldRegion, compose_regions
from rnw.eu5_africa_start import algeciras
from rnw.eu5_biomes import (
    CellBiomes,
    Generated,
    MaterialRegion,
    assign_biomes,
    climate_grid,
    size_model,
    template_attributes,
    vanilla_locations,
)
from rnw.eu5_canvas import NEW_WORLD, place_islands
from rnw.eu5_history import installed_rules
from rnw.eu5_history_build import build_history_start
from rnw.eu5_islands import moved_pixels_of
from rnw.eu5_map import DEFAULT_MAP, DEFINITIONS, PORTS, load_map
from rnw.eu5_natives import (
    regional_populations,
    regional_projection_inputs,
    regional_societies,
    vanilla_natives,
)
from rnw.eu5_newworld import plan_composed_identities, plan_regional_land, vanilla_geometry
from rnw.eu5_nw_export import (
    RIVER_CLASSES,
    TEMPLATES,
    ComposedStart,
    VanillaClimate,
    _final_labels,
    _plan_development,
    _text_outputs,
    _verify_natives,
    calibrate_development,
    check_composed_map,
    check_composed_rasters,
    composed_bindings,
    composed_land_character,
    composed_rivers,
    missing_area_keys,
    reserve_african_countries,
    settled_biomes,
    vanilla_localization_keys,
    verify_country_tags,
    verify_localization,
    verify_map_texts,
)
from rnw.eu5_oceans import emitted_cells, plan_oceans
from rnw.eu5_regional_history import project_regional_start, shared_routes, simulate_region
from rnw.eu5_rewrite import sound_toll_locations
from rnw.eu5_seas import current_bands, read_ports, read_waters, settle_coast, shape_water
from rnw.eu5_start import combine_starts
from rnw.eu5_terrain import DecalStore
from rnw.geography import read_locations
from rnw.loc_keys import KeySpace, key_hashes
from rnw.model import CellClass
from rnw.newworld import generate_new_world
from rnw.parallel import configure, stage_workers
from rnw.rng import derive_seed
from rnw.settings import DEFAULT_MOROCCO_POLICY, MoroccoPolicy, build_settings
from rnw.societies import STATE, TRIBE
from rnw.timing import peak_gib, timed
from rnw.topology import LOW_BITS, PAIR_SHIFT, adjacency_pairs, unpack_pairs

if TYPE_CHECKING:
    from collections.abc import Mapping

    from numpy.typing import NDArray

    from rnw.continent_domains import Domain
    from rnw.eu5_biomes import SizeModel, VanillaLocations
    from rnw.eu5_canvas import Canvas
    from rnw.eu5_map import Eu5Map
    from rnw.eu5_newworld import Plan, RegionalLand, VanillaGeometry
    from rnw.eu5_remap import GeographicRemap
    from rnw.eu5_seas import Water
    from rnw.eu5_start import FinalStartPlan
    from rnw.geography import Location
    from rnw.newworld import NewWorld
    from rnw.settings import NativeSettings, NewWorldSettings


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


def _land_identities(  # noqa: PLR0913 - prototype inputs and the common biome vote.
    game: Eu5Map,
    attributes: dict[str, dict[str, str]],
    vanilla: VanillaLocations,
    *,
    biomes: CellBiomes,
    parts: list[tuple[Domain, NewWorld, range, NewWorldSettings]],
    hierarchy: dict[str, Location],
    keys: KeySpace,
) -> dict[str, tuple[RegionalLand, tuple[str, ...]]]:
    result: dict[str, tuple[RegionalLand, tuple[str, ...]]] = {}
    pairs = unpack_pairs(vanilla.pairs)
    for domain, world, owned, settings in parts:
        window = slice(owned.start, owned.stop)
        local = CellBiomes(
            biomes.climate[window],
            biomes.vegetation[window],
            biomes.topography[window],
            biomes.raw_material[window],
        )
        land = plan_regional_land(
            game,
            domain,
            world,
            hierarchy,
            attributes=attributes,
            pairs=pairs,
            biomes=local,
            settings=settings,
            keys=keys,
        )
        result[domain.continent.key] = land, local.topography
    return result


def _society_trials(  # noqa: PLR0913 - calibration, map and selected regional settings.
    game_dir: Path,
    game: Eu5Map,
    plan: Plan,
    world: NewWorld,
    *,
    geometry: VanillaGeometry,
    attributes: dict[str, dict[str, str]],
    vanilla: VanillaLocations,
    biomes: CellBiomes,
    river_counts: NDArray[np.int64],
    seed: int,
    morocco: tuple[MoroccoPolicy, ...],
    native_options: Mapping[str, NativeSettings],
    hierarchy: dict[str, Location],
    remap: GeographicRemap,
    run_history: bool,
    loc_keys: KeySpace,
) -> tuple[dict[str, dict[str, int]], ComposedStart | None]:
    source = regional_populations(
        game_dir,
        game,
        vanilla,
        attributes,
        native_options.keys() - {NEW_WORLD},
    )
    original = {
        key: (int(geometry.rows[i]), int(geometry.columns[i])) for i, key in enumerate(game.keys)
    }
    africa_settings = None
    if "africa" in native_options:
        policy = (morocco or (DEFAULT_MOROCCO_POLICY,))[0]
        settings = build_settings("continents", {"continents": {"africa": {"morocco": policy}}})
        africa_settings = settings.continents.regions[0]
    moroccan_start, mamluks, remap = reserve_african_countries(
        game_dir, plan, world, original, hierarchy, africa_settings, remap
    )
    moroccan_land = () if moroccan_start is None else moroccan_start.africa
    mamluk_land = () if mamluks is None else mamluks.africa
    reserved = moroccan_land + mamluk_land
    base = vanilla_natives(game_dir, game, geometry, attributes, hierarchy) if run_history else None
    rules = installed_rules(base) if base is not None else None
    routes = (
        shared_routes(world, plan, biomes, max_sea_steps=rules.max_sea_steps)
        if rules is not None
        else ()
    )
    populations: dict[str, dict[str, int]] = {}
    starts: list[FinalStartPlan] = []
    if base is not None and (american := native_options.get(NEW_WORLD)) is not None:
        start = timed(
            "america history and projection",
            partial(
                build_history_start,
                world=world,
                plan=plan,
                biomes=biomes,
                river_pixels=river_counts,
                vanilla=base,
                settings=american,
                seed=seed,
                loc_keys=loc_keys,
                selection={i for i, cell in enumerate(plan.cells) if cell.continent == NEW_WORLD},
                routes=routes,
            ),
        )
        starts.append(start)
        base = replace(
            base,
            reserved_tags=base.reserved_tags | {country.tag for country in start.countries},
            colors=base.colors | {country.color for country in start.countries},
        )
        populations[NEW_WORLD] = {
            "starting_countries": len(start.countries),
            "starting_markets": len(start.markets),
            "populated_locations": len(start.pops),
        }
    for name, knobs in native_options.items():
        if name == NEW_WORLD:
            continue
        held = reserved if name == "africa" else ()
        boot = regional_societies(
            world,
            plan,
            biomes,
            river_counts,
            continent=name,
            vanilla=source[name],
            settings=knobs,
            seed=derive_seed(seed, "peoples", name),
            reserved=held,
            routes=routes if run_history else None,
        )
        groups = Counter(polity.kind for polity in boot.societies.polities)
        populations[name] = {
            "population_milli": int(boot.societies.population.sum()),
            "populated_locations": len(boot.pops),
            "cultures": len(set(boot.cultures)),
            "religions": len(set(boot.religions)),
            "state_territories": groups[STATE],
            "tribal_territories": groups[TRIBE],
            "inhabited_moroccan_locations": len(boot.pops.keys() & set(moroccan_land)),
            "inhabited_mamluk_locations": len(boot.pops.keys() & set(mamluk_land)),
        }
        if rules is not None and base is not None:
            sacred = {
                site.name: remap.locations[site.location]
                for site in base.holy_sites
                if site.location in remap.locations and hierarchy[site.location].continent == name
            }
            calibration = regional_projection_inputs(base, source[name], name)
            simulated = timed(
                f"{name} history",
                lambda name=name, boot=boot, knobs=knobs, sacred=sacred, held=held: simulate_region(
                    plan,
                    boot,
                    routes,
                    vanilla=source[name],
                    settings=knobs,
                    rules=rules,
                    seed=derive_seed(seed, "history", name),
                    reserved=held,
                    sacred=sacred.values(),
                ),
            )
            history = simulated.history
            start = timed(
                f"{name} history projection",
                partial(
                    project_regional_start,
                    world,
                    plan,
                    boot,
                    simulated,
                    vanilla=calibration,
                    settings=knobs,
                    holy_sites=sacred,
                    loc_keys=loc_keys,
                ),
            )
            base = replace(
                base,
                reserved_tags=base.reserved_tags | {country.tag for country in start.countries},
                colors=base.colors | {country.color for country in start.countries},
            )
            starts.append(start)
            populations[name].update(
                historical_routes=len(history.geography.routes),
                historical_events=len(history.events),
                historical_actors=sum(actor.living for actor in history.state.actors),
                starting_countries=len(start.countries),
                starting_markets=len(start.markets),
            )
    if not starts or base is None:
        return populations, None
    emirate = (
        algeciras(seed, base.reserved_tags, loc_keys, base.colors)
        if moroccan_start is not None and moroccan_start.policy is MoroccoPolicy.EMIRATE
        else None
    )
    return populations, ComposedStart(
        tuple(starts), remap, moroccan_start, emirate, mamluks=mamluks
    )


def _write_start_trial(  # noqa: PLR0913 - exercise the final writer with the finished shared map.
    game_dir: Path,
    game: Eu5Map,
    canvas: Canvas,
    plan: Plan,
    start: ComposedStart,
    *,
    keys: KeySpace,
    hierarchy: dict[str, Location],
    geometry: VanillaGeometry,
    removed: set[str],
    water: Water,
    river_codes: NDArray[np.uint8],
    biomes: CellBiomes,
    ports: tuple[list[str], dict[int, tuple[int, int]]],
    seed: int,
) -> dict[str, object]:
    world = water.coast.world
    natives = combine_starts(start.histories)
    development = _plan_development(
        calibrate_development(game_dir, game, hierarchy),
        game_map=game,
        world=world,
        plan=plan,
        biomes=biomes,
        natives=natives,
        labels=_final_labels(game, canvas, world),
        docks=ports[1],
        river_codes=river_codes,
    )
    outputs, stats = _text_outputs(
        game_dir,
        game_map=game,
        canvas=canvas,
        world=world,
        plan=plan,
        hierarchy=hierarchy,
        removed=removed,
        geometry=geometry,
        biomes=biomes,
        natives=natives,
        loc_keys=keys,
        development=development,
        ports=ports,
        coast=water.coast,
        water=water,
        new_world_keys=set(),
        resources_seed=seed,
        area_replacements=start.remap.areas,
        composed=start,
    )
    return {
        "files": len(outputs),
        "population_locations": len(natives.pops),
        "setup_identifiers_removed": stats["setup_identifiers_removed"],
        **verify_map_texts(outputs, plan, canvas, water, removed),
        **_verify_natives(natives, plan),
        **verify_country_tags(game_dir, outputs),
        **verify_localization(
            outputs, key_hashes(vanilla_localization_keys(game_dir)), game_dir=game_dir
        ),
    }


def _shared_water(  # noqa: PLR0913, PLR0915 - measure the stages from coast through written start.
    game_dir: Path,
    game: Eu5Map,
    templates: str,
    regions: list[WorldRegion],
    *,
    land: dict[str, tuple[RegionalLand, tuple[str, ...]]],
    hierarchy: dict[str, Location],
    keys: KeySpace,
    seed: int,
    land_inputs: tuple[VanillaClimate, SizeModel, Mapping[str, NewWorldSettings]] | None,
    morocco: tuple[MoroccoPolicy, ...],
    native_options: Mapping[str, NativeSettings],
    run_history: bool,
) -> dict[str, object]:
    shared = timed("compose final coast", lambda: compose_regions(game, regions))
    wasteland = 0
    biomes: CellBiomes | None = None
    if land_inputs is not None:
        training, sizes, geography = land_inputs
        attributes = template_attributes(templates)
        shared, biomes, _ = timed(
            "shared land character",
            lambda: composed_land_character(
                game,
                shared,
                regions,
                geography=geography,
                resources={},
                vanilla=training,
                attributes=attributes,
                game_dir=game_dir,
                seed=seed,
                material_seed=seed,
                sizes=sizes,
            ),
        )
        wasteland = shared.world.classes.count(CellClass.WASTELAND)
        pairs = unpack_pairs(training.locations.pairs)
        for region in regions:
            domain, local = region.domain, region.world
            name = domain.continent.key
            numbers = shared.cell_ids[name].tolist()
            local = replace(local, classes=tuple(shared.world.classes[cell] for cell in numbers))

            def field(values: tuple[str, ...], numbers: list[int] = numbers) -> tuple[str, ...]:
                return tuple(values[cell] if cell < len(values) else "" for cell in numbers)

            local_biomes = CellBiomes(
                field(biomes.climate),
                field(biomes.vegetation),
                field(biomes.topography),
                field(biomes.raw_material),
            )
            land[name] = (
                plan_regional_land(
                    game,
                    domain,
                    local,
                    hierarchy,
                    attributes=attributes,
                    pairs=pairs,
                    biomes=local_biomes,
                    settings=geography[name],
                    keys=keys,
                ),
                local_biomes.topography,
            )
    canvas = shared.canvas
    removed = {game.keys[i] for i in np.flatnonzero(canvas.removed).tolist()}
    ports = read_ports((game_dir / PORTS).read_text(encoding="utf-8-sig"))
    coast = timed(
        "shared ports",
        lambda: settle_coast(
            game, canvas, shared.world, ports=ports, vanilla=read_waters(templates), removed=removed
        ),
    )
    water = timed("shared water shapes", lambda: shape_water(coast))
    river_codes, valleys, _ = timed(
        "composed rivers", lambda: composed_rivers(canvas.shape, regions, seed)
    )
    drawn = int(np.count_nonzero(river_codes < RIVER_CLASSES))
    river_counts = np.bincount(
        water.coast.world.labels[river_codes < RIVER_CLASSES],
        minlength=len(water.coast.world.classes),
    )
    del valleys
    report: dict[str, object] = {
        "natural_wasteland_cells": wasteland,
        "river_pixels": drawn,
        "sea_cells": water.coast.world.classes.count(CellClass.SEA),
        "trimmed_vanilla_locations": int(np.count_nonzero(canvas.trimmed)),
        "merged_sea_cells": coast.merged,
        "sea_lanes": len(water.lanes),
        "relinked_vanilla_ports": len(coast.foreign.free),
        "straits": len(water.crossings),
    }
    if land:
        world = water.coast.world
        geometry = timed(
            "wrapped vanilla geometry",
            lambda: vanilla_geometry(game, canvas, hierarchy, wrap_x=True),
        )
        topology = [""] * len(world.classes)
        numbered = {}
        for name, (region, grounds) in land.items():
            local = [water.coast.source_cells[cell] for cell in shared.cell_ids[name].tolist()]
            for cell, ground in zip(local, grounds, strict=True):
                topology[cell] = ground
            numbered[name] = region, local
        plan = timed(
            "shared map identities",
            lambda: plan_composed_identities(
                game,
                canvas,
                world,
                hierarchy,
                geometry=geometry,
                regions=numbered,
                topography=topology,
                seed=seed,
                keys=keys,
                waters=water.waters,
            ),
        )
        ocean_plan = timed(
            "connected ocean remainders",
            lambda: plan_oceans(game, canvas, world, plan, hierarchy, water.zones, keys),
        )
        plan.oceans = ocean_plan
        plan.dropped_areas = missing_area_keys(hierarchy, removed - ocean_plan.retained, plan)
        report.update(ocean_plan.stats)
        report["final_location_ids"] = (
            len(game.keys) - len(removed - ocean_plan.retained) + len(emitted_cells(plan))
        )
        report["shared_water_areas"] = len(
            {cell.area for cell in plan.cells if cell.kind is CellClass.SEA}
        )
        port_rows, remap = timed(
            "geographical bindings",
            lambda: composed_bindings(
                game,
                canvas,
                water,
                plan,
                hierarchy,
                geometry=geometry,
                removed=removed - ocean_plan.retained,
                vanilla_ports=ports,
            ),
        )
        report["generated_ports"] = len(port_rows[1])
        report["remapped_locations"] = len(remap.locations)
        if land_inputs is not None:
            report["map_checks"] = timed(
                "check the combined map",
                lambda: check_composed_map(game, canvas, plan, water, land_inputs[2]),
            )
            report["raster_checks"] = timed(
                "check painted rasters",
                lambda: check_composed_rasters(
                    game_dir, game, canvas, water, plan, river_codes=river_codes
                ),
            )
        if morocco:
            report["morocco"] = timed(
                "Morocco on the common map",
                lambda: map_morocco_trials(
                    game_dir,
                    game,
                    plan,
                    world,
                    geometry=geometry,
                    removed=removed - ocean_plan.retained,
                    remap=remap,
                    keys=keys,
                    seed=seed,
                    policies=morocco,
                ),
            )
        if biomes is not None and native_options and land_inputs is not None:
            biomes = settled_biomes(biomes, shared.world, water.coast)
            projected, start = timed(
                "regional societies",
                lambda: _society_trials(
                    game_dir,
                    game,
                    plan,
                    world,
                    geometry=geometry,
                    attributes=template_attributes(templates),
                    vanilla=land_inputs[0].locations,
                    biomes=biomes,
                    river_counts=river_counts,
                    seed=seed,
                    morocco=morocco,
                    native_options=native_options,
                    hierarchy=hierarchy,
                    remap=remap,
                    run_history=run_history,
                    loc_keys=keys,
                ),
            )
            report["societies"] = projected
            if start is not None:
                report["shared_start"] = timed(
                    "write the shared start",
                    partial(
                        _write_start_trial,
                        game_dir,
                        game,
                        canvas,
                        plan,
                        start,
                        keys=keys,
                        hierarchy=hierarchy,
                        geometry=geometry,
                        removed=removed - ocean_plan.retained,
                        water=water,
                        river_codes=river_codes,
                        biomes=biomes,
                        ports=port_rows,
                        seed=seed,
                    ),
                )
    return report


def profile(  # noqa: C901, PLR0912, PLR0913, PLR0915 - the prototype records each phase.
    game_dir: Path,
    presets: Mapping[str, str | None],
    seed: int,
    *,
    materials: bool = False,
    morocco: tuple[MoroccoPolicy, ...] = (),
    identities: bool = False,
    seas: bool = False,
    game_land: bool = False,
    societies: bool = False,
    histories: bool = False,
) -> dict[str, object]:
    started = perf_counter()
    threads = configure()
    game = timed("load map", lambda: load_map(game_dir))
    settings = {key: CONTINENTS[key].geography(preset) for key, preset in presets.items()}
    native_options = (
        {
            region.key: region.natives
            for region in build_settings(
                presets.get(NEW_WORLD) or "continents",
                {
                    "continents": {
                        "america": NEW_WORLD in presets,
                        **{
                            key: {"preset": name or CONTINENTS[key].preset}
                            for key, name in presets.items()
                            if key != NEW_WORLD
                        },
                    }
                },
            ).continents.regions
        }
        if societies
        else {}
    )
    if societies and NEW_WORLD in presets:
        native_options[NEW_WORLD] = build_settings(presets[NEW_WORLD] or "continents").natives
    tolls = sound_toll_locations((game_dir / DEFAULT_MAP).read_text(encoding="utf-8-sig"))
    domains = timed(
        "plan continent domains",
        lambda: plan_domains(game, settings, seed=seed, retained_tolls=tolls),
    )
    text = (game_dir / TEMPLATES).read_text(encoding="utf-8-sig")
    templates = template_attributes(text)
    store = DecalStore(game_dir, game.labels.shape)
    original_heights = timed("read heights", store.world_heights)
    sizes = timed(
        "calibrate sizes",
        lambda: size_model(game, templates, original_heights),  # noqa: F821
    )
    vanilla = None
    if materials or morocco:
        vanilla = timed(
            "vanilla location statistics",
            lambda: vanilla_locations(game.labels, original_heights),  # noqa: F821
        )
    training = None
    if materials:
        training = timed(
            "vanilla climate for biomes",
            lambda: climate_grid(
                np.array([kind is CellClass.SEA for kind in game.classes], dtype=bool)[game.labels],
                original_heights,  # noqa: F821
                seasonal=True,
            ),
        )
    land_inputs = (
        (VanillaClimate(original_heights, vanilla, training), sizes, settings)
        if game_land and vanilla is not None and training is not None
        else None
    )
    labels = game.labels.copy()
    height = original_heights.astype(np.int32)
    del original_heights
    kinds = list(game.classes)
    regions: dict[str, dict[str, object]] = {}
    samples: list[tuple[NDArray[np.int64], NDArray[np.int64], NDArray[np.int64]]] = []
    rolls: dict[str, MaterialRegion] = {}
    parts: list[tuple[Domain, NewWorld, range, NewWorldSettings]] = []
    coasts: list[WorldRegion] = []
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
            seam=domain.watershed_seam,
            sizes=sizes,
            map_rows=(domain.first_row, game.labels.shape[0]),
            sea_bands=bands,
            outside_land=domain.contact_land,
            land_interface=domain.land_interface if domain.join_asia else None,
            strait=domain.strait,
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
            if identities:
                parts.append((domain, world, rolls[key].cells, settings[key]))
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
        if key == "africa" and morocco and vanilla is not None and not game_land:
            regions[key]["morocco"] = timed(
                "Morocco startup options",
                partial(
                    morocco_trials,
                    game_dir,
                    game,
                    vanilla,
                    domain,
                    world,
                    seed=seed,
                    policies=morocco,
                ),
            )
        if seas:
            coasts.append(WorldRegion(domain, world))
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
    need_keys = bool(parts or land_inputs is not None)
    hierarchy = (
        {place.key: place for place in read_locations(game_dir / DEFINITIONS)} if need_keys else {}
    )
    keys = KeySpace(key_hashes(vanilla_localization_keys(game_dir)) if need_keys else set())
    land_plans: dict[str, tuple[RegionalLand, tuple[str, ...]]] = {}
    if training is not None and vanilla is not None:
        cells = _composed_cells(kinds, retained, contacts, samples)
        before = perf_counter()
        biomes, _ = assign_biomes(
            game_map=game,
            templates=templates,
            vanilla=vanilla,
            vanilla_grid=training,
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
        if parts and land_inputs is None:
            land_plans = timed(
                "regional land identity plans",
                lambda: _land_identities(
                    game,
                    templates,
                    vanilla,
                    biomes=biomes,
                    parts=parts,
                    hierarchy=hierarchy,
                    keys=keys,
                ),
            )
            for key, (land, _) in land_plans.items():
                regions[key]["land_identities"] = {
                    "subcontinents": len({area.parents[1] for area in land.areas}),
                    "regions": len({area.parents[0] for area in land.areas}),
                    "matched_areas": sum(not area.new for area in land.areas),
                    "new_areas": sum(area.new for area in land.areas),
                    "provinces": sum(len(area.provinces) for area in land.areas),
                }
    else:
        materials_seconds = None
    water = (
        _shared_water(
            game_dir,
            game,
            text,
            coasts,
            land=land_plans,
            hierarchy=hierarchy,
            keys=keys,
            seed=seed,
            land_inputs=land_inputs,
            morocco=morocco if game_land else (),
            native_options=native_options,
            run_history=histories,
        )
        if coasts
        else None
    )
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
        "water": water,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game_dir", type=Path)
    parser.add_argument("continents", nargs="+", choices=tuple(CONTINENTS))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--materials", action="store_true")
    parser.add_argument("--identities", action="store_true")
    parser.add_argument("--seas", action="store_true")
    parser.add_argument("--societies", action="store_true")
    parser.add_argument("--histories", action="store_true")
    parser.add_argument(
        "--game-land",
        action="store_true",
        help="exercise the exporter's common ground, vegetation and wasteland vote",
    )
    parser.add_argument("--preset", action="append", default=[], metavar="CONTINENT=PRESET")
    parser.add_argument(
        "--morocco", action="append", choices=tuple(MoroccoPolicy), type=MoroccoPolicy
    )
    args = parser.parse_args()
    presets = dict.fromkeys(args.continents)
    if args.morocco and "africa" not in presets:
        parser.error("--morocco requires Africa to be selected")
    if args.seas and not (presets.keys() & {"africa", "oceania"}):
        parser.error("--seas requires Africa or Oceania")
    if args.game_land and not args.seas:
        parser.error("--game-land requires --seas")
    if args.societies and not args.game_land:
        parser.error("--societies requires --game-land")
    if args.histories and not args.societies:
        parser.error("--histories requires --societies")
    morocco = tuple(args.morocco or ([DEFAULT_MOROCCO_POLICY] if "africa" in presets else []))
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
        json.dumps(
            profile(
                args.game_dir,
                presets,
                args.seed,
                materials=args.materials or args.identities or args.game_land,
                morocco=morocco,
                identities=args.identities,
                seas=args.seas,
                game_land=args.game_land,
                societies=args.societies,
                histories=args.histories,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
