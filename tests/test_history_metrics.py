"""Acceptance counters follow factual events, physical land and actual engine relations."""

from __future__ import annotations

from dataclasses import replace

from rnw.eu5_history_plan import project_start
from rnw.history_engine import advance, create
from rnw.history_metrics import government_combinations, landmasses, measure
from rnw.history_model import Action, Proposal
from rnw.model import CellClass
from tests.fakes import synthetic_world

from .history_fixtures import divided_valley, valley
from .test_history_plan import inputs_for, quiet


def test_divided_valley_counts_actual_transfers_and_independent_continuity() -> None:
    inputs = inputs_for(divided_valley())
    start = project_start(inputs)
    found = measure(
        start,
        keys=inputs.keys,
        masses=dict.fromkeys(inputs.keys, 0),
        inherited=inputs.vanilla.history_governments,
        positions=tuple(inputs.positions),
    )
    assert found.bootstrap_states == 3
    assert found.bootstrap_tribes == found.bootstrap_communities == 0
    assert found.conflicts == 1
    assert found.ownership_events == 4
    assert found.ownership_locations == 17
    assert found.separations == 1
    assert found.continuous_countries == found.landed_countries == 3
    assert found.projected_relationship_countries == 3
    assert found.treaty_countries == 2
    assert found.ordinary_sizes == (1, 2, 3)
    assert found.chronicle_lengths == (8, 7, 7)
    assert found.domination[0].largest_bloc == 3
    assert found.domination[0].state_locations == 6
    assert found.archive_bytes > 0


def test_physical_landmass_includes_wasteland_and_wrap_but_not_water() -> None:
    world = synthetic_world()[0]
    world = replace(
        world,
        classes=(
            CellClass.LAND,
            CellClass.WASTELAND,
            CellClass.LAND,
            CellClass.SEA,
            CellClass.LAND,
            CellClass.LAND,
        ),
        edges=((0, 1), (1, 2), (2, 3), (3, 4), (4, 5)),
    )
    keys = tuple(str(i) for i in range(6))
    separate = landmasses(world, keys)
    assert separate["0"] == separate["2"]
    assert separate["4"] != separate["2"]
    assert "3" not in separate
    seam = landmasses(replace(world, edges=(*world.edges, (0, 5))), keys)
    assert len(set(seam.values())) == 1


def test_government_variety_resolves_defaults_and_ignores_unrelated_fields() -> None:
    country = project_start(inputs_for(divided_valley())).countries[0]
    inherited = {"base": (("type", "monarchy"), ("position", "10"), ("heir_selection", "one"))}
    first = replace(country, include="base", government=())
    same = replace(first, government=(("heir_selection", "other"),))
    moved = replace(first, government=(("position", "20"),))
    republic = replace(first, government=(("type", "republic"),))
    assert government_combinations((first, same), inherited, ("position",)) == 1
    assert government_combinations((first, same, moved, republic), inherited, ("position",)) == 3


def test_domination_counts_a_subjects_land_without_transferring_it() -> None:
    original = valley()
    history = create(
        original.geography, tuple(replace(f, technology=2) for f in original.foundings), seed=42
    )
    history = advance(history, (Proposal(Action.CONTACT, "upstream", "downstream"),))
    # D25: the submission answers a recorded defeat, which moved one district.
    history = advance(history, (Proposal(Action.CONFLICT, "downstream", "upstream", ("u1",)),))
    history = advance(history, (Proposal(Action.DEPENDENCY, "upstream", "downstream"),))
    inputs = inputs_for(quiet(history))
    start = project_start(inputs)
    assert len(start.vassals) == 1
    found = measure(
        start,
        keys=inputs.keys,
        masses=dict.fromkeys(inputs.keys, 0),
        inherited=inputs.vanilla.history_governments,
        positions=tuple(inputs.positions),
    )
    assert found.ordinary_sizes == (1, 2, 3)
    assert found.domination[0].largest_bloc == 4
    assert found.domination[0].state_locations == 6
    assert found.ownership_events == 1
    assert found.projected_relationship_countries == 2
    structure = found.structure
    assert structure is not None
    assert (structure.subjects, structure.scaled_subjects) == (1, 1)
    assert structure.changed_locations == 1
