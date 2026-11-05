"""Plan D22-D27: aims, scaled administration, breakaways, chronicles and the start's shape."""

from __future__ import annotations

# pyright: reportPrivateUsage=false
from dataclasses import replace

import pytest

from rnw import eu5_history
from rnw.eu5_history import traditions
from rnw.eu5_history_plan import project_start
from rnw.history_acceptance import Sweep, World, evaluate
from rnw.history_actions import OPPORTUNITY, eligible
from rnw.history_context import Context
from rnw.history_engine import advance, create, validate_history
from rnw.history_metrics import AimOutcome, Observation, RegionClass, Structure
from rnw.history_model import (
    Action,
    Authority,
    Cohort,
    District,
    Factor,
    Founding,
    Geography,
    History,
    Outcome,
    Partition,
    Proposal,
    Reason,
    Route,
    Rules,
    Society,
    Strategy,
    Tenure,
    TrajectoryKind,
)
from rnw.history_text import chronicles, source_keys
from rnw.history_trajectories import interpolate, political_regions, realizations

from .history_fixtures import court
from .test_history_plan import inputs_for, quiet
from .test_history_societies import _trajectory_world


def _grid(size: int = 5, *, big: int = 0) -> tuple[Geography, tuple[Founding, ...]]:
    """A size x size landed region; the first ``big`` columns form one large polity."""
    places = tuple(
        District(f"{x}_{y}", "plain", Tenure.LAND, (Cohort("c", "r", 1000, 600),))
        for x in range(size)
        for y in range(size)
    )
    routes = [
        Route(f"{x}_{y}", f"{x + dx}_{y + dy}")
        for x in range(size)
        for y in range(size)
        for dx, dy in ((1, 0), (0, 1))
        if x + dx < size and y + dy < size
    ]
    foundings: list[Founding] = []
    if big:
        foundings.append(
            Founding(
                "big",
                Tenure.LAND,
                tuple(f"{x}_{y}" for x in range(big) for y in range(size)),
                "0_0",
                technology=2,
            )
        )
    foundings.extend(
        Founding(f"p{x}_{y}", Tenure.LAND, (f"{x}_{y}",), f"{x}_{y}", technology=2)
        for x in range(big, size)
        for y in range(size)
    )
    return Geography(places, tuple(routes), Rules()), tuple(foundings)


def _seeded(kind: TrajectoryKind, *, big: int, turbulence: int = 500) -> History:
    geography, foundings = _grid(big=big)
    for seed in range(200):
        history = create(geography, foundings, seed=seed, empire_permille=0, turbulence=turbulence)
        if any(item.kind is kind for item in history.state.trajectories):
            return history
    message = f"No seed draws {kind}"
    raise AssertionError(message)


def test_capacity_keeps_the_ordinary_limit_and_scales_with_administration() -> None:
    history = court(
        {"plain": (1000, 500, 0, False), "realm": (1000, 500, 0, False)},
        {
            "plain": Society(authority=Authority.RULER),
            "realm": Society(centralization=900, integration=900, authority=Authority.RULER),
        },
    )
    context = Context(history, lambda: None)
    assert context.capacity("plain") == 1000
    # Three and a half doublings above the threshold at level-2 technology: 1000 + 11000 * 1.5.
    assert context.capacity("realm") == 17_500
    assert context.unrest("realm") == 17_500 * 825 // 1000
    assert context.limit("realm") == context.capacity("realm")


def test_turbulence_interpolates_the_design_tables() -> None:
    assert [interpolate((300, 400, 500), level) for level in (0, 200, 350, 500, 800, 1000)] == [
        300,
        300,
        350,
        400,
        500,
        500,
    ]


def test_a_political_region_draws_a_recorded_setting_with_a_strategy() -> None:
    history = _seeded(TrajectoryKind.REGIONAL_POWER, big=0)
    context = Context(history, lambda: None)
    assert political_regions(context) == {"plain": tuple(sorted(f.key for f in history.foundings))}
    aims = [item for item in history.state.trajectories if item.region]
    assert aims
    assert all(item.kind is TrajectoryKind.REGIONAL_POWER and not item.hearth for item in aims)
    assert all(item.strategy in set(Strategy) for item in aims)
    event = next(e for e in history.events if e.key == aims[0].cause)
    assert event.kind is Action.TRAJECTORY
    assert event.reason is Reason.AMBITION
    holder = context.index.actors[aims[0].members[0]]
    assert holder.society.centralization >= 750
    assert holder.society.integration >= 700
    assert not event.effects.transfers
    assert not event.effects.bonds
    validate_history(history)
    again = create(history.geography, history.foundings, seed=history.seed, empire_permille=0)
    assert again.state.trajectories == history.state.trajectories


def test_a_paramount_is_seeded_only_where_connected_state_land_allows_it() -> None:
    history = _seeded(TrajectoryKind.PARAMOUNT, big=2)
    paramount = next(i for i in history.state.trajectories if i.kind is TrajectoryKind.PARAMOUNT)
    assert paramount.members == ("big",)
    final = quiet(history)
    found = realizations(Context(final, lambda: None))
    # The paramount holds 10 of 25 state locations, five times any other bloc.
    assert any(item.kind is TrajectoryKind.PARAMOUNT and item.members == ("big",) for item in found)


def test_overreach_doubles_the_conquest_limit_only_for_its_holder() -> None:
    history = _seeded(TrajectoryKind.REGIONAL_POWER, big=0)
    item = next(i for i in history.state.trajectories if i.region)
    holder = item.members[0]
    reckless = replace(
        history.state,
        trajectories=tuple(
            replace(each, strategy=Strategy.OVERREACHING) if each == item else each
            for each in history.state.trajectories
        ),
    )
    context = Context(replace(history, state=reckless), lambda: None)
    assert context.limit(holder) == 2 * context.capacity(holder)
    others = [a.key for a in history.state.actors if a.key not in context.aims]
    assert all(context.limit(key) == context.capacity(key) for key in others)


def _province_world() -> History:
    """A realm that has conquered a province and is now beyond its unrest threshold."""
    places = (
        District("r0", "plain", Tenure.LAND, (Cohort("c", "r", 9000, 5000),)),
        District("r1", "plain", Tenure.LAND, (Cohort("c", "r", 600, 400),)),
        District("v0", "plain", Tenure.LAND, (Cohort("c", "r", 900, 500),)),
        District("v1", "plain", Tenure.LAND, (Cohort("c", "r", 900, 500),)),
        District("w0", "plain", Tenure.LAND, (Cohort("c", "r", 600, 400),)),
    )
    routes = (
        Route("r0", "r1"),
        Route("r1", "v0"),
        Route("v0", "v1"),
        Route("r0", "w0"),
        Route("w0", "v1"),
    )
    realm = Society(centralization=500, integration=300, authority=Authority.RULER)
    history = create(
        Geography(places, routes, Rules(minimum_peasants=300, minimum_share=100)),
        (
            Founding("realm", Tenure.LAND, ("r0", "r1"), "r0", Authority.RULER, 2, realm),
            Founding("vassal", Tenure.LAND, ("v0", "v1"), "v0", Authority.CUSTOMARY, 1),
            Founding("west", Tenure.LAND, ("w0",), "w0", Authority.CUSTOMARY, 1),
        ),
        seed=42,
        empire_permille=0,
        turbulence=800,
    )
    for proposal in (
        Proposal(Action.CONTACT, "realm", "vassal"),
        Proposal(Action.CONTACT, "realm", "west"),
        Proposal(Action.CONFLICT, "realm", "vassal", ("v0", "v1")),
    ):
        history = advance(history, (proposal,))
    assert history.events[-1].outcome is Outcome.ACCEPTED
    return history


def _secession() -> Proposal:
    return Proposal(
        Action.SECESSION,
        "realm",
        partitions=(
            Partition(("r0", "r1"), "r0", Authority.RULER),
            Partition(("v0", "v1"), "v0", Authority.CUSTOMARY),
        ),
    )


def test_a_conquered_province_breaks_away_beyond_the_unrest_threshold() -> None:
    history = _province_world()
    context = Context(history, lambda: None)
    assert context.burden("realm") > context.unrest("realm")
    result = advance(history, (_secession(),))
    event = result.events[-1]
    assert event.outcome is Outcome.ACCEPTED
    assert event.reason is Reason.CAPACITY
    created = event.effects.created[0]
    assert created.homeland == ("v0", "v1")
    assert created.seat == "v0"
    assert not created.parents
    assert {(t.district, t.after) for t in event.effects.transfers} == {
        ("v0", created.key),
        ("v1", created.key),
    }
    assert any(
        m.factor is Factor.GRIEVANCE and m.first == created.key for m in event.effects.memories
    )
    after = Context(result, lambda: None)
    assert after.index.members["realm"] == {"r0", "r1"}
    validate_history(result)


def test_a_seceding_realm_cannot_also_lose_that_land_in_a_contest() -> None:
    history = _province_world()
    history = advance(history, (Proposal(Action.CONTACT, "west", "realm"),))
    attack = Proposal(Action.CONFLICT, "west", "realm", ("v1",))
    result = advance(history, (_secession(), attack))
    outcomes = {event.kind: event for event in result.events[-2:]}
    assert outcomes[Action.SECESSION].outcome is Outcome.ACCEPTED
    assert outcomes[Action.CONFLICT].outcome is Outcome.REFUSED
    assert outcomes[Action.CONFLICT].reason is Reason.COMMITTED
    validate_history(result)


def test_a_founders_own_land_never_secedes() -> None:
    history = _province_world()
    proposal = Proposal(
        Action.SECESSION,
        "realm",
        partitions=(
            Partition(("r0", "v0", "v1"), "r0", Authority.RULER),
            Partition(("r1",), "r1", Authority.RULER),
        ),
    )
    assert advance(history, (proposal,)).events[-1].reason is Reason.INELIGIBLE


def test_league_members_bargain_a_pact_without_a_third_party() -> None:
    history = _trajectory_world(TrajectoryKind.SEA_LEAGUE)
    league = next(i for i in history.state.trajectories if i.kind is TrajectoryKind.SEA_LEAGUE)
    first, second = league.members[:2]
    for proposal in (
        Proposal(Action.CONTACT, first, second),
        Proposal(Action.EXCHANGE, first, second),
    ):
        history = advance(history, (proposal,))
    result = advance(history, (Proposal(Action.PACT, first, second),))
    event = result.events[-1]
    assert event.outcome is Outcome.ACCEPTED
    assert league.cause in event.causes
    validate_history(result)


def test_chronicles_skip_renewed_exchanges_contacts_and_internal_reforms() -> None:
    history = _province_world()
    for _ in range(4):
        history = advance(history, (Proposal(Action.EXCHANGE, "realm", "west"),))
        while (history.state.year - 1037) % 15:
            history = advance(history, ())
    plan = project_start(inputs_for(quiet(history)))
    for chronicle in chronicles(plan).values():
        families = [row.family for row in chronicle.rows]
        assert Action.CONTACT not in families
        assert families.count(Action.EXCHANGE) <= 1


def test_regional_traditions_are_deterministic_and_have_a_dominant_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    geography, _ = _grid()
    districts = geography.districts
    first = traditions(districts, seed=7)
    assert first == traditions(tuple(reversed(districts)), seed=7)
    dominant = eu5_history.DOMINANT_TRADITION
    monkeypatch.setattr(eu5_history, "DOMINANT_TRADITION", 1)
    plain = traditions(districts, seed=7)
    changed = [
        (dominant, ordinary)
        for dominant, ordinary in zip(first["plain"], plain["plain"], strict=True)
        if dominant != ordinary
    ]
    assert len(changed) == 1
    assert changed[0][0] == dominant * changed[0][1]


def _observation(  # noqa: PLR0913 - one synthetic start
    regions: tuple[str, ...],
    *,
    recent: int = 10,
    republics: int = 15,
    size: int = 3,
    state: int = 100,
    great: int = 1,
) -> Observation:
    structure = Structure(
        regions=tuple(RegionClass(f"r{n}", 10, kind, 10, 3, 30) for n, kind in enumerate(regions)),
        state_locations=state,
        changed_locations=30,
        recent_locations=recent,
        aims=(
            AimOutcome(
                TrajectoryKind.REGIONAL_POWER,
                "prudent",
                realized=True,
                peak=20,
                final=20,
                successors=False,
            ),
            AimOutcome(
                TrajectoryKind.PARAMOUNT,
                "overreaching",
                realized=False,
                peak=30,
                final=10,
                successors=True,
            ),
            *(
                AimOutcome(
                    TrajectoryKind.GREAT_EMPIRE,
                    "prudent",
                    realized=True,
                    peak=60,
                    final=60,
                    successors=False,
                )
                for _ in range(great)
            ),
        ),
        subjects=12,
        scaled_subjects=12,
        alliances=6,
        states=100,
        republics=republics,
        government_types=3,
        assortativity=300,
        chronicle_families=(("conflict", 30), ("exchange", 15), ("foundation", 30), ("union", 25)),
        chronicle_distinct=(3, 4, 5),
        great_blocs=(60,) * great,
    )
    return Observation(
        100,
        50,
        20,
        10,
        5,
        5,
        1,
        landed_countries=100,
        continuous_countries=80,
        projected_relationship_countries=70,
        treaty_countries=40,
        chronicle_lengths=(1, 2, 5, 6, 8),
        ordinary_sizes=(size,),
        government_combinations=50,
        great_seeded=great,
        great_realized=great,
        domination=(),
        archive_bytes=1000,
        digest="0" * 64,
        structure=structure,
    )


VARIED_REGIONS = ("patchwork", "rival_powers", "paramount", "fractured", "great_realm")


def _sweep(pair: str, control: str, level: int) -> Sweep:
    if control == "state_locations":
        row = _observation(VARIED_REGIONS, size=2 + level)
    elif control == "state_share_permille":
        row = _observation(VARIED_REGIONS, state=100 + 10 * level)
    elif control == "turbulence":
        row = _observation(VARIED_REGIONS, recent=10 + 5 * level)
    else:
        row = _observation(VARIED_REGIONS, great=level)
    return Sweep(pair, control, level, row, baseline_empires=(70,))


@pytest.mark.parametrize("broken", [None, "Q1", "Q3", "Q5", "Q11"])
def test_acceptance_applies_the_frozen_thresholds_mechanically(broken: str | None) -> None:
    calm = ("paramount", "paramount", "rival_powers", "patchwork", "great_realm")
    turbulent = ("patchwork", "fractured", "patchwork", "rival_powers", "fractured")
    varied = ("patchwork",) * 5 if broken == "Q1" else VARIED_REGIONS
    recent = {200: 10, 500: 15, 800: 10 if broken == "Q3" else 20}
    worlds = [
        World(
            f"case{n}",
            level,
            _observation(
                {200: calm, 500: varied, 800: turbulent}[level],
                recent=recent[level],
                republics=40 if broken == "Q11" else 5 + 5 * n,
            ),
            baseline_ordinary=3,
            baseline_empires=(70,),
        )
        for n in range(4)
        for level in (200, 500, 800)
    ]
    controls = ("state_locations", "state_share_permille", "turbulence", "empire_permille")
    sweeps = [
        _sweep(f"pair{n}", control, level)
        for n in range(4)
        for control in controls
        for level in (0, 1, 2)
        if not (broken == "Q5" and control == "turbulence" and level == 2)
    ]
    checks = evaluate(worlds, sweeps)
    failed = {key for key, check in checks.items() if not check.passed}
    # Regions of a single class also leave no variety within any world (Q2).
    expected = {"Q1": {"Q1", "Q2"}}.get(broken or "", {broken} if broken else set())
    assert failed == expected


def test_a_breakaway_and_its_aim_survive_the_portable_record() -> None:
    from rnw import atlas  # noqa: PLC0415 - only this test reads the atlas
    from rnw.history_archive_checks import validate  # noqa: PLC0415
    from rnw.history_presenter import Reader  # noqa: PLC0415

    from .test_history_archive import history_atlas  # noqa: PLC0415

    history = advance(_province_world(), (_secession(),))
    plan = project_start(inputs_for(quiet(history)))
    built = history_atlas(plan)
    assert built.history is not None
    validate(built.history, atlas.history_links(built))
    created = next(e for e in history.events if e.kind is Action.SECESSION).effects.created[0]
    rows = chronicles(plan)[plan.history_tags[created.key]].rows
    assert rows[0].family is Action.SECESSION
    assert any(key.startswith("rnw_history_secession_") for key in source_keys(rows[0].text))
    region = Reader(built, "english", lambda key: key).region("region")
    assert region
    aims = _seeded(TrajectoryKind.REGIONAL_POWER, big=0)
    aimed = history_atlas(project_start(inputs_for(quiet(aims))))
    assert aimed.history is not None
    assert aimed.history.aims
    validate(aimed.history, atlas.history_links(aimed))
    sections = Reader(aimed, "english", lambda key: key).region("region")
    assert any(section.title == "Ambitions" for section in sections)


def test_partners_of_one_seeded_league_never_unite() -> None:
    league = advance(
        _trajectory_world(TrajectoryKind.SEA_LEAGUE),
        (Proposal(Action.CONTACT, "0", "1"),),
    )
    ordinary = advance(
        _trajectory_world(TrajectoryKind.SEA_LEAGUE, chance=0),
        (Proposal(Action.CONTACT, "0", "1"),),
    )
    union = Proposal(Action.UNION, "0", "1")
    assert eligible(Context(league, lambda: None), union) is Reason.INELIGIBLE
    assert eligible(Context(ordinary, lambda: None), union) is not Reason.INELIGIBLE


def _confederacy() -> History:
    history = _trajectory_world(TrajectoryKind.HIGHLAND_CONFEDERATION)
    for proposals in (
        (Proposal(Action.CONTACT, "0", "1"), Proposal(Action.CONTACT, "0", "2")),
        (Proposal(Action.EXCHANGE, "0", "1"), Proposal(Action.EXCHANGE, "0", "2")),
    ):
        history = advance(history, proposals)
    return history


def test_confederates_bargain_on_trust_and_a_pact_network_is_recognized() -> None:
    history = _confederacy()
    context = Context(history, lambda: None)
    assert not context.afraid
    pacts = tuple(Proposal(Action.PACT, "0", key) for key in ("1", "2"))
    assert all(eligible(context, pact) is None for pact in pacts)
    assert not [
        item for item in realizations(context) if item.kind is TrajectoryKind.HIGHLAND_CONFEDERATION
    ]
    history = advance(history, pacts)
    (found,) = [
        item
        for item in realizations(Context(history, lambda: None))
        if item.kind is TrajectoryKind.HIGHLAND_CONFEDERATION
    ]
    assert set(found.members) == {"0", "1", "2"}
    # A stranger without trust and without fear gets no common defence.
    plain = advance(
        _trajectory_world(TrajectoryKind.HIGHLAND_CONFEDERATION, chance=0),
        (Proposal(Action.CONTACT, "0", "1"),),
    )
    assert eligible(Context(plain, lambda: None), Proposal(Action.PACT, "0", "1")) is not None


def test_the_contest_margin_widens_in_calm_and_closes_in_turbulence() -> None:
    assert [interpolate(OPPORTUNITY, level) for level in (200, 500, 800)] == [5, 3, 2]
