"""Historical plans pass the real setup verifiers without static placement rules."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from rnw.eu5_archetypes import alliance_lines, confederation_lines, rival_lines
from rnw.eu5_biomes import CellBiomes
from rnw.eu5_empires import opinion_lines, road_lines
from rnw.eu5_history_build import build_history_start
from rnw.eu5_history_plan import project_start
from rnw.eu5_history_text import guarantee_lines
from rnw.eu5_natives import DEFAULT_TRIBE, country_records, homeland, vassal_lines
from rnw.eu5_newworld import Plan, PlannedCell
from rnw.eu5_nw_export import (
    SETUP_DIR,
    NewWorldExportError,
    verify_archetypes,
    verify_empires,
    verify_technology,
)
from rnw.history_actions import eligible
from rnw.history_context import Context
from rnw.history_engine import (
    _local_choices,  # pyright: ignore[reportPrivateUsage]
    advance,
)
from rnw.history_model import Action, HistoryError, Proposal, TrajectoryKind
from rnw.history_output_checks import verify_diplomacy
from rnw.loc_keys import KeySpace
from rnw.model import CellClass
from rnw.newworld import NewWorld
from rnw.settings import NATIVES

from .history_fixtures import divided_valley, valley, valley_policy
from .test_history_plan import inputs_for, realized_network


@pytest.mark.parametrize("case", ["quiet", "threatened"])
def test_threat_candidate_index_matches_exhaustive_reachable_triples(case: str) -> None:
    history = valley()
    history = advance(history, valley_policy(Context(history, lambda: None)))
    if case == "threatened":
        history = realized_network(TrajectoryKind.SEA_LEAGUE)
    context = Context(history, lambda: None)
    for actor in history.state.actors:
        if not actor.living:
            continue
        expected = {
            proposal
            for other in context.reach.get(actor.key, {})
            for threat in context.reach.get(actor.key, {}).keys()
            & context.reach.get(other, {}).keys() - {actor.key, other}
            for kind in (Action.PACT, Action.PROTECTION)
            if eligible(context, proposal := Proposal(kind, actor.key, other, threat=threat))
            is None
        }
        actual = {
            proposal
            for proposal in _local_choices(context, actor)
            if proposal.kind in {Action.PACT, Action.PROTECTION}
        }
        assert actual == expected


@pytest.mark.parametrize("case", ["valley", "sea", "confederation"])
def test_historical_setup_passes_engine_prerequisites_and_written_plan_checks(case: str) -> None:
    history = (
        divided_valley()
        if case == "valley"
        else realized_network(
            TrajectoryKind.SEA_LEAGUE if case == "sea" else TrajectoryKind.HIGHLAND_CONFEDERATION,
            overlap=case == "confederation",
        )
    )
    inputs = inputs_for(history)
    natives = project_start(inputs)
    context = Context(history, lambda: None)
    assert context.pact_participants == {
        key
        for bond in history.state.bonds
        if bond.kind is Action.PACT
        for key in (bond.first, bond.second)
    }
    assert context.recent_exchanges == {
        tuple(sorted((bond.first, bond.second)))
        for bond in history.state.bonds
        if bond.kind is Action.EXCHANGE
        and context.event_years[bond.cause] > history.state.year - 15
    }
    if case == "sea":
        assert context.pact_participants
    vanilla = replace(inputs.vanilla, history_positions=dict(inputs.positions))
    keys = inputs.keys
    plan = Plan(
        cells=[
            PlannedCell(
                key=key,
                name=key,
                color=number + 1,
                kind=CellClass.LAND,
                province="p",
                area=inputs.areas[key],
                region="r",
                subcontinent="s",
                continent="america",
            )
            for number, key in enumerate(keys)
        ]
    )
    world = NewWorld(
        labels=np.zeros((1, len(keys)), dtype=np.int32),
        classes=(CellClass.LAND,) * len(keys),
        elevation=np.zeros((1, len(keys)), dtype=np.int32),
        pixels=np.ones(len(keys), dtype=np.int64),
        centroids=np.zeros((len(keys), 2), dtype=np.int64),
        interior=np.zeros((len(keys), 2), dtype=np.int64),
        mean_elevation=np.zeros(len(keys), dtype=np.int64),
        spread=np.zeros(len(keys), dtype=np.int64),
        edges=tuple(
            (keys.index(route.first), keys.index(route.second))
            for route in history.geography.routes
            if not route.sea_steps
        ),
    )
    originals = {
        "10_countries.txt": "countries = { countries = {} }",
        "12_diplomacy.txt": "diplomacy_manager = {}",
        "15_international_organizations.txt": "international_organization_manager = {}",
        "20_rivals.txt": "diplomacy_manager = {}",
        "09_roads.txt": "road_network = {}",
        "18_opinions.txt": "diplomacy_manager = {}",
    }
    texts = {
        "10_countries.txt": "countries = { countries = {"
        + country_records(natives.countries)
        + "} }",
        "12_diplomacy.txt": "diplomacy_manager = {"
        + vassal_lines(natives.vassals)
        + alliance_lines(natives.alliances)
        + guarantee_lines(natives.protections)
        + "}",
        "15_international_organizations.txt": "international_organization_manager = {"
        + confederation_lines(natives.confederation_date, natives.confederations)
        + "}",
        "20_rivals.txt": "diplomacy_manager = {" + rival_lines(natives.rivals) + "}",
        "09_roads.txt": "road_network = {" + road_lines(natives.roads) + "}",
        "18_opinions.txt": "diplomacy_manager = {" + opinion_lines(natives.opinions) + "}",
    }
    outputs = {
        f"{SETUP_DIR.removeprefix('game/')}/{name}": text.encode("utf-8-sig")
        for name, text in texts.items()
    }
    _ = verify_technology(outputs, natives, vanilla)
    _ = verify_empires(outputs, natives, plan, world, vanilla, originals, set())
    _ = verify_archetypes(outputs, natives, plan, vanilla, originals, set())
    verify_diplomacy(natives, texts["12_diplomacy.txt"], originals["12_diplomacy.txt"], set())
    # A fabricated road remains invalid even when its written list agrees with a
    # tampered plan: the surviving history is checked again at the output boundary.
    if case == "sea":
        changed = replace(natives, roads=((keys[0], keys[-1]),))
        with pytest.raises(HistoryError):
            _ = verify_empires(outputs, changed, plan, world, vanilla, originals, set())
    changed_outputs = dict(outputs)
    country_path = f"{SETUP_DIR.removeprefix('game/')}/10_countries.txt"
    changed_outputs[country_path] = (
        texts["10_countries.txt"].replace("capital =", "wrong_capital =", 1).encode()
    )
    with pytest.raises(NewWorldExportError):
        _ = verify_archetypes(changed_outputs, natives, plan, vanilla, originals, set())


@pytest.mark.parametrize("kind", ["guarantee", "vassal"])
@pytest.mark.parametrize("defect", ["direction", "missing", "duplicate", "old_world"])
def test_written_guarantees_keep_direction_counts_and_old_world(defect: str, kind: str) -> None:
    plan = replace(project_start(inputs_for(divided_valley())), protections=(("AAA", "BBB"),))
    # Use the real living tags while retaining a deliberately independent vanilla pair.
    first, second = (country.tag for country in plan.countries[:2])
    plan = replace(
        plan,
        protections=((first, second),) if kind == "guarantee" else (),
        vassals=((first, second),) if kind == "vassal" else (),
    )
    key, field = (
        ("scripted_oneway", "type") if kind == "guarantee" else ("dependency", "subject_type")
    )
    original = f"diplomacy_manager = {{ {key} = {{ first = OLD second = EUR {field} = {kind} }} }}"
    writer = guarantee_lines if kind == "guarantee" else vassal_lines
    added = writer(((first, second),))
    if defect == "direction":
        added = writer(((second, first),))
    elif defect == "missing":
        added = ""
    elif defect == "duplicate":
        added += added
    text = original[:-1] + added + "}"
    if defect == "old_world":
        text = text.replace("second = EUR", "second = OTHER")
    with pytest.raises(HistoryError):
        verify_diplomacy(plan, text, original, set())


@pytest.mark.parametrize("state_share", [0, 600])
def test_complete_physical_bootstrap_history_and_projection_ignore_resource_roll(
    state_share: int,
) -> None:
    count = 64
    world = NewWorld(
        labels=np.arange(count, dtype=np.int32).reshape(8, 8),
        classes=(CellClass.LAND,) * count,
        elevation=np.zeros((8, 8), dtype=np.int32),
        pixels=np.full(count, 10000, dtype=np.int64),
        centroids=np.array([(4839, number * 10) for number in range(count)], dtype=np.int64),
        interior=np.zeros((count, 2), dtype=np.int64),
        mean_elevation=np.zeros(count, dtype=np.int64),
        spread=np.zeros(count, dtype=np.int64),
        edges=tuple(
            (number, neighbour)
            for number in range(count)
            for neighbour in (number + 1, number + 8)
            if neighbour < count and (neighbour != number + 1 or number % 8 != 7)
        ),
    )
    plan = Plan(
        cells=[
            PlannedCell(
                key=f"loc_{number}",
                name=f"Place {number}",
                color=number + 1,
                kind=CellClass.LAND,
                province="p",
                area="a",
                region="r",
                subcontinent="s",
                continent="america",
            )
            for number in range(count)
        ]
    )
    base = inputs_for(divided_valley()).vanilla
    vector = homeland(
        ["tropical"], ["grasslands"], ["flatland"], [100], [False], [False], [1], [""]
    )
    vanilla = replace(
        base,
        density={"tropical": 1000},
        population_per_location=10000,
        cultures={key: replace(info, homeland=vector) for key, info in base.cultures.items()},
        religions=dict.fromkeys(base.religions, (vector, 1000)),
        levels={key: level for key, level in base.levels.items() if key != DEFAULT_TRIBE},
    )
    biomes = CellBiomes(
        ("tropical",) * count, ("grasslands",) * count, ("flatland",) * count, ("maize",) * count
    )
    settings = replace(NATIVES, state_share_permille=state_share, hearths_per_10k=300)
    first = build_history_start(
        world=world,
        plan=plan,
        biomes=biomes,
        river_pixels=np.zeros(count, dtype=np.int64),
        vanilla=vanilla,
        settings=settings,
        seed=42,
        loc_keys=KeySpace(set()),
    )
    second = build_history_start(
        world=world,
        plan=plan,
        biomes=replace(biomes, raw_material=("fish",) * count),
        river_pixels=np.zeros(count, dtype=np.int64),
        vanilla=vanilla,
        settings=settings,
        seed=42,
        loc_keys=KeySpace(set()),
    )
    assert first.history is not None
    assert first.history.state.year == 1337
    assert len(first.history.rounds) == 60
    assert first.history == second.history
    assert first.countries == second.countries
    assert first.pops == second.pops
    assert first.stats["calibrated_population_milli"] == sum(
        pop.amount for rows in first.pops.values() for pop in rows
    )
