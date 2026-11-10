"""Connect installed calibration and physical society construction to history.

This is the sole normal native-start constructor. The private native helpers own
calibrated identities, names and population; no static political selector runs.
"""

# NumPy scalar conversions and the native adapter's internal bootstrap helpers.
# pyright: reportAny=false, reportPrivateUsage=false
# ruff: noqa: SLF001

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from rnw import eu5_natives as native
from rnw.epoch import CURRENT
from rnw.eu5_history import BootstrapInputs, bootstrap_history, installed_rules
from rnw.eu5_history_plan import ProjectionInputs, project_start
from rnw.history_engine import simulate
from rnw.history_routes import PhysicalMap, physical_routes, routed_graph
from rnw.parallel import collector_paused
from rnw.progress import checkpoint
from rnw.societies import bootstrap_societies

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

    from rnw.eu5_biomes import CellBiomes
    from rnw.eu5_newworld import Plan
    from rnw.eu5_start import FinalStartPlan
    from rnw.loc_keys import KeySpace
    from rnw.newworld import NewWorld
    from rnw.settings import NativeSettings


def build_history_start(  # noqa: PLR0913 - the bridge needs the complete generated physical world.
    *,
    world: NewWorld,
    plan: Plan,
    biomes: CellBiomes,
    river_pixels: NDArray[np.int64],
    vanilla: native.VanillaNatives,
    settings: NativeSettings,
    seed: int,
    loc_keys: KeySpace,
    algorithm: int = CURRENT,
) -> FinalStartPlan:
    # Societies, the simulation, its causal replay and the projection build millions of
    # acyclic records; the cyclic collector would only walk them again (C506).
    with collector_paused():
        return _build_history_start(
            world=world,
            plan=plan,
            biomes=biomes,
            river_pixels=river_pixels,
            vanilla=vanilla,
            settings=settings,
            seed=seed,
            loc_keys=loc_keys,
            algorithm=algorithm,
        )


def _build_history_start(  # noqa: PLR0913 - as build_history_start
    *,
    world: NewWorld,
    plan: Plan,
    biomes: CellBiomes,
    river_pixels: NDArray[np.int64],
    vanilla: native.VanillaNatives,
    settings: NativeSettings,
    seed: int,
    loc_keys: KeySpace,
    algorithm: int = CURRENT,
) -> FinalStartPlan:
    graph, cells = native.land_graph(world, biomes, river_pixels, vanilla)
    cells = replace(
        cells,
        family=[
            vanilla.families.of(plan.cells[cell].region, plan.cells[cell].area)
            for cell in cells.cells
        ],
    )
    keys = tuple(plan.cells[cell].key for cell in cells.cells)
    # D24: a great realm holds at least four mean states directly, never fewer than
    # the installed empire floor.
    rules = installed_rules(vanilla)
    rules = replace(
        rules, empire_locations=max(rules.empire_locations, 4 * settings.state_locations)
    )
    routes = physical_routes(
        PhysicalMap(
            keys,
            tuple(cells.cells),
            tuple(int(cost) for cost in graph.cost),
            world.classes,
            world.edges,
        ),
        max_sea_steps=rules.max_sea_steps,
        checkpoint=checkpoint,
    )
    graph = routed_graph(graph, keys, routes)
    societies = bootstrap_societies(
        graph,
        settings,
        seed=seed,
        target=vanilla.population_per_location * len(keys),
        state_floor=vanilla.state_floor,
    )
    religions, cultures, state = native._identities(societies, cells, vanilla, seed)
    namer = native.PlaceNamer(vanilla, seed)
    names = native._place_names(
        world, plan, cells, [cultures[int(zone)] for zone in societies.culture], namer
    )
    pops = native._pop_cohorts(societies, list(keys), religions, cultures)
    for where, rows in native.diaspora(
        societies,
        list(keys),
        zones=native._zone_homelands(societies.culture, cells, societies, state),
        state=state,
        religions=religions,
        cultures=cultures,
        vanilla=vanilla,
        seed=seed,
    ).items():
        pops.setdefault(where, []).extend(rows)
    levels = native._state_levels(societies, [keys[p.capital] for p in societies.polities], vanilla)
    technology: dict[str, int] = {}
    for number, polity in enumerate(societies.polities):
        include = native._include(
            vanilla,
            cultures[polity.culture],
            level=levels.get(number),
            coastal=any(cells.coastal[node] for node in polity.members),
        )
        technology[keys[polity.capital]] = (
            levels[number] if number in levels else vanilla.levels.get(include, 0)
        )
    holy = native._place_holy_sites(vanilla, religions, societies, list(keys))
    root = bootstrap_history(
        BootstrapInputs(
            graph,
            societies,
            keys,
            {keys[node]: plan.cells[cell].region for node, cell in enumerate(cells.cells)},
            pops,
            technology,
            routes,
            rules,
            highland=tuple(
                keys[node]
                for node, topography in enumerate(cells.topography)
                if topography in native.HIGHLAND_TOPOGRAPHIES
            ),
            sacred=tuple(sorted(set(holy.values()))),
        ),
        seed=seed,
        empire_permille=settings.empire_permille,
        turbulence=settings.turbulence_permille,
        checkpoint=checkpoint,
    )
    history = simulate(root.history, checkpoint=checkpoint)
    return project_start(
        ProjectionInputs(
            root,
            history,
            graph,
            societies,
            keys,
            {keys[node]: plan.cells[cell].area for node, cell in enumerate(cells.cells)},
            names,
            vanilla,
            vanilla.history_positions,
            loc_keys,
            holy,
            reach_steps=settings.hearth_reach_steps,
            coastal_areas={
                keys[node]: tuple(sorted({plan.cells[sea].area for sea in cells.seas[node]}))
                for node in range(len(keys))
            },
            algorithm=algorithm,
        ),
        checkpoint=checkpoint,
    )
