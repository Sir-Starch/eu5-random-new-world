"""Build regional histories from one physical route network and local starting societies."""

# NumPy stubs type array indexing and conversions as Any.
# pyright: reportAny=false
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import numpy as np

from rnw.eu5_history import BootstrapInputs, bootstrap_history
from rnw.eu5_history_plan import ProjectionInputs, project_start
from rnw.eu5_natives import HIGHLAND_TOPOGRAPHIES, PlaceNamer, land_travel_cost
from rnw.eu5_natives import _place_names as place_names  # pyright: ignore[reportPrivateUsage]
from rnw.eu5_technology import state_levels
from rnw.history_engine import simulate
from rnw.history_model import HistoryError
from rnw.history_routes import PhysicalMap, physical_routes, routed_graph
from rnw.model import CellClass
from rnw.parallel import collector_paused
from rnw.progress import checkpoint
from rnw.societies import EMPIRE_FLOOR, STATE, LandGraph, Societies

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence

    from rnw.eu5_biomes import CellBiomes
    from rnw.eu5_history import HistoryBootstrap
    from rnw.eu5_natives import RegionalPopulation, RegionalSocieties, VanillaNatives
    from rnw.eu5_newworld import Plan
    from rnw.eu5_start import FinalStartPlan
    from rnw.history_model import History, Route, Rules
    from rnw.loc_keys import KeySpace
    from rnw.newworld import NewWorld
    from rnw.settings import NativeSettings


def shared_routes(
    world: NewWorld, plan: Plan, biomes: CellBiomes, *, max_sea_steps: int
) -> tuple[Route, ...]:
    """Measure routes once on the final land and seas, including continent boundaries."""
    land = tuple(i for i, kind in enumerate(world.classes) if kind is CellClass.LAND)
    keys = tuple(plan.cells[i].key for i in land)
    costs = tuple(land_travel_cost(biomes.topography[i], biomes.vegetation[i]) for i in land)
    return physical_routes(
        PhysicalMap(keys, land, costs, world.classes, world.edges),
        max_sea_steps=max_sea_steps,
        checkpoint=checkpoint,
    )


@dataclass(frozen=True, slots=True, eq=False)
class _Region:
    keys: tuple[str, ...]
    physical: tuple[int, ...]
    graph: LandGraph
    societies: Societies
    retained: tuple[str, ...]


@dataclass(frozen=True, slots=True, eq=False)
class RegionalHistory:
    root: HistoryBootstrap
    history: History
    region: _Region


def _historical_region(
    boot: RegionalSocieties,
    plan: Plan,
    routes: Sequence[Route],
    reserved: Collection[str],
) -> _Region:
    """Exclude fixed 1337 holdings from changing hands during simulated history."""
    physical = tuple(boot.cells.cells)
    all_keys = [plan.cells[i].key for i in physical]
    chosen = [i for i, key in enumerate(all_keys) if key not in reserved]
    keys = tuple(all_keys[i] for i in chosen)
    positions = {old: new for new, old in enumerate(chosen)}
    included = set(keys)
    graph = boot.graph
    regional_routes = tuple(
        route for route in routes if route.first in included and route.second in included
    )
    edges = np.array(
        [
            (positions[a], positions[b])
            for a, b in graph.edges.tolist()
            if a in positions and b in positions
        ],
        dtype=np.int64,
    ).reshape(-1, 2)
    graph = routed_graph(
        replace(
            graph,
            capacity=graph.capacity[chosen],
            potential=graph.potential[chosen],
            cost=graph.cost[chosen],
            edges=edges,
            coastal=None if graph.coastal is None else graph.coastal[chosen],
        ),
        keys,
        regional_routes,
    )
    societies = boot.societies
    local = replace(
        societies,
        complexity=societies.complexity[chosen],
        population=societies.population[chosen],
        peasants=societies.peasants[chosen],
        culture=societies.culture[chosen],
        religion=societies.religion[chosen],
        hearths=tuple(positions[node] for node in societies.hearths if node in positions),
        polities=tuple(
            replace(
                polity,
                members=tuple(positions[node] for node in polity.members),
                capital=positions[polity.capital],
            )
            for polity in societies.polities
        ),
        ranks={
            positions[node]: rank for node, rank in societies.ranks.items() if node in positions
        },
        markets=tuple(positions[node] for node in societies.markets if node in positions),
    )
    return _Region(
        keys,
        tuple(physical[i] for i in chosen),
        graph,
        local,
        tuple(key for key in all_keys if key in reserved),
    )


def _technologies(
    region: _Region, cultures: Sequence[str], vanilla: RegionalPopulation
) -> dict[str, int]:
    societies = region.societies
    states = [polity.capital for polity in societies.polities if polity.kind == STATE]
    ordered = [
        (int(societies.complexity[seat]), int(societies.population[seat]), region.keys[seat])
        for seat in states
    ]
    technology = dict(
        zip(
            (region.keys[seat] for seat in states),
            state_levels(ordered, vanilla.state_levels),
            strict=True,
        )
    )
    for polity in societies.polities:
        if polity.kind == STATE:
            continue
        include = vanilla.cultures[cultures[polity.culture]].tribe_include
        technology[region.keys[polity.capital]] = vanilla.template_levels.get(include, 0)
    return technology


def simulate_region(  # noqa: PLR0913 - local calibration, physical routes and the bootstrap.
    plan: Plan,
    boot: RegionalSocieties,
    routes: tuple[Route, ...],
    *,
    vanilla: RegionalPopulation,
    settings: NativeSettings,
    rules: Rules,
    seed: int,
    reserved: Collection[str] = (),
    sacred: Collection[str] = (),
) -> RegionalHistory:
    """Simulate one starting society with local population, technology and land support."""
    with collector_paused():
        region = _historical_region(boot, plan, routes, reserved)
        floor = vanilla.state_floor
        if floor is None:
            message = "Missing regional agrarian baseline"
            raise HistoryError(message)
        keys = set(region.keys)
        geography = {
            key: plan.cells[i].region for key, i in zip(region.keys, region.physical, strict=True)
        }
        highlands = tuple(
            plan.cells[cell].key
            for cell, terrain in zip(boot.cells.cells, boot.cells.topography, strict=True)
            if terrain in HIGHLAND_TOPOGRAPHIES and plan.cells[cell].key in keys
        )
        root = bootstrap_history(
            BootstrapInputs(
                region.graph,
                region.societies,
                region.keys,
                geography,
                {key: rows for key, rows in boot.pops.items() if key in keys},
                _technologies(region, boot.cultures, vanilla),
                tuple(route for route in routes if route.first in keys and route.second in keys),
                replace(
                    rules,
                    minimum_peasants=floor.peasants,
                    minimum_share=floor.share,
                    empire_locations=max(EMPIRE_FLOOR, 4 * settings.state_locations),
                ),
                highland=highlands,
                sacred=keys.intersection(sacred),
            ),
            seed=seed,
            empire_permille=settings.empire_permille,
            turbulence=settings.turbulence_permille,
            checkpoint=checkpoint,
        )
        return RegionalHistory(root, simulate(root.history, checkpoint=checkpoint), region)


def project_regional_start(  # noqa: PLR0913 - historical roots, map, naming and installed templates.
    world: NewWorld,
    plan: Plan,
    boot: RegionalSocieties,
    simulation: RegionalHistory,
    *,
    vanilla: VanillaNatives,
    settings: NativeSettings,
    holy_sites: Mapping[str, str],
    loc_keys: KeySpace,
) -> FinalStartPlan:
    """Project a completed local history through the normal game-start adapter."""
    history = simulation.history
    region = simulation.region
    cells = boot.cells
    names = place_names(
        world,
        plan,
        cells,
        [boot.cultures[int(zone)] for zone in boot.societies.culture],
        PlaceNamer(vanilla, history.seed),
    )
    coastal = {
        plan.cells[index].key: tuple(sorted({plan.cells[water].area for water in seas}))
        for index, seas in zip(cells.cells, cells.seas, strict=True)
    }
    places = set(region.keys)
    with collector_paused():
        start = project_start(
            ProjectionInputs(
                simulation.root,
                history,
                region.graph,
                region.societies,
                region.keys,
                {plan.cells[i].key: plan.cells[i].area for i in region.physical},
                names,
                vanilla,
                vanilla.history_positions,
                loc_keys,
                {name: where for name, where in holy_sites.items() if where in places},
                reach_steps=settings.hearth_reach_steps,
                coastal_areas=coastal,
            ),
            checkpoint=checkpoint,
        )
    if not region.retained:
        return start
    pops = {key: tuple(boot.pops[key]) for key in region.retained}
    population = {key: sum(pop.amount for pop in rows) for key, rows in pops.items()}
    if min(population.values()) <= 0:
        message = "A retained holding has no regional population"
        raise HistoryError(message)
    return replace(
        start,
        pops=start.pops | pops,
        population=start.population | population,
        stats=start.stats
        | {
            "land_locations": len(start.population) + len(pops),
            "inhabited_locations": len(start.pops) + len(pops),
            "population_milli": sum(start.population.values()) + sum(population.values()),
            "retained_territory_population_milli": sum(population.values()),
        },
    )
