"""Mechanical application of the plan's §18 statistical criteria (D28) to observations.

The thresholds are fixed design targets; this module never selects worlds, drops
outliers or adjusts a value. S8-S10 (time, memory, cancellation) are measured by
the delivery harness, not here. Inputs are raw observations of complete starts:
one per world and turbulence level, plus the three-level control sweeps.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from rnw.history_metrics import FRACTURED, PARAMOUNT, PATCHWORK, RIVALS
from rnw.history_model import EXPANSION, TrajectoryKind

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping, Sequence

    from rnw.history_metrics import AimOutcome, Observation, Structure

CALM: Final[int] = 200
VARIED: Final[int] = 500
TURBULENT: Final[int] = 800
LEVELS: Final[tuple[int, int, int]] = (CALM, VARIED, TURBULENT)
GROUP_KINDS: Final[tuple[TrajectoryKind, ...]] = (
    TrajectoryKind.SEA_LEAGUE,
    TrajectoryKind.HIGHLAND_CONFEDERATION,
    TrajectoryKind.SACRED_CENTRE,
)
# The sweep's declared statistic per control (Q5).
CONTROLS: Final[tuple[str, ...]] = (
    "state_locations",
    "empire_permille",
    "state_share_permille",
    "turbulence",
)
MAX_ARCHIVE: Final[int] = 8 * 1024 * 1024
LOW, DEFAULT, HIGH = 0, 1, 2

# Frozen design targets of §18 (2026-11-05). Revise only by a recorded decision
# made before a held-out run.
ORDINARY_CLASS_MIN: Final[float] = 0.10
FRACTURED_MIN: Final[float] = 0.03
CLASS_MAX: Final[float] = 0.50
DIVERSE_REGIONS: Final[int] = 4
DIVERSE_CLASSES: Final[int] = 3
CHANGED_RATIO: Final[float] = 1.5
RISING_WORLDS: Final[float] = 0.75
CONTINUITY: Final[float] = 0.40
PRUDENT_REALIZED: Final[float] = 0.70
OVERREACH_ENDED: Final[float] = 0.50
OVERREACH_KEPT: Final[tuple[int, int]] = (3, 4)
GROUP_REALIZED: Final[float] = 0.50
SCALE: Final[tuple[float, float]] = (0.5, 1.5)
HIGH_WORLDS: Final[int] = 3
ORDINARY_VARIED: Final[tuple[float, float]] = (0.75, 1.25)
ORDINARY_EXTREME: Final[tuple[float, float]] = (0.60, 1.40)
CONTINENT: Final[int] = 60
LANDMASS: Final[int] = 20
DOMINANT: Final[float] = 0.50
DOMINATED_SHARE: Final[float] = 0.20
NEVER_DOMINANT: Final[float] = 0.85
SUBJECTS: Final[tuple[float, float]] = (8, 40)
SCALED_SUBJECTS: Final[float] = 0.90
ALLIANCES: Final[tuple[float, float]] = (4, 30)
REPUBLICS: Final[float] = 0.25
REPUBLIC_SPREAD: Final[float] = 0.05
TYPED_WORLD: Final[int] = 20
GOVERNMENT_TYPES: Final[int] = 2
ASSORTATIVITY: Final[float] = 0.2
FAMILY_MAX: Final[float] = 0.35
ROUTINE_MAX: Final[float] = 0.20
LONG_CHRONICLE_FAMILIES: Final[int] = 3
SHORT_CHRONICLE: Final[int] = 3
SHORT_SHARE: Final[float] = 0.10
CHRONICLE_MAX: Final[int] = 8
VISIBLE: Final[float] = 0.5


@dataclass(frozen=True, slots=True)
class World:
    """One seed-set world at one turbulence level, with its pinned 1.1.0 pair."""

    case: str
    turbulence: int
    observation: Observation
    baseline_ordinary: float
    baseline_empires: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class Sweep:
    """One control at one level (0 low, 1 default, 2 high) of one preset/seed pair."""

    pair: str
    control: str
    level: int
    observation: Observation
    baseline_empires: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class Check:
    passed: bool
    values: dict[str, object] = field(default_factory=dict)


def _structure(observation: Observation) -> Structure:
    found = observation.structure
    if found is None:
        message = "Acceptance needs the structural observation of every start"
        raise ValueError(message)
    return found


def _median(values: Iterable[float]) -> float:
    found = list(values)
    return statistics.median(found) if found else 0.0


def _quartiles(values: Sequence[float]) -> tuple[float, float]:
    if len(values) < 2:  # noqa: PLR2004 - a spread needs two observations
        return (values[0], values[0]) if values else (0.0, 0.0)
    q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return q1, q3


def _share(part: float, whole: float) -> float:
    return part / whole if whole else 0.0


def _ordinary(observation: Observation) -> float:
    return _median(observation.ordinary_sizes)


def _state_locations(observation: Observation) -> float:
    return _structure(observation).state_locations


def _changed(observation: Observation) -> float:
    found = _structure(observation)
    return _share(found.recent_locations, found.state_locations)


def _extraordinary(observation: Observation) -> float:
    return sum(
        aim.realized
        for aim in _structure(observation).aims
        if aim.kind is TrajectoryKind.GREAT_EMPIRE or aim.kind in GROUP_KINDS
    )


def _extraordinary_seeded(observation: Observation) -> int:
    return sum(
        aim.kind is TrajectoryKind.GREAT_EMPIRE or aim.kind in GROUP_KINDS
        for aim in _structure(observation).aims
    )


STATISTIC: Final[dict[str, Callable[[Observation], float]]] = {
    "state_locations": _ordinary,
    "empire_permille": _extraordinary,
    "state_share_permille": _state_locations,
    "turbulence": _changed,
}


def _classes(worlds: Sequence[World]) -> Counter[str]:
    return Counter(
        region.kind for world in worlds for region in _structure(world.observation).regions
    )


def _q1(varied: Sequence[World]) -> Check:
    counts = _classes(varied)
    total = sum(counts.values())
    shares = {kind: _share(count, total) for kind, count in counts.items()}
    passed = (
        total > 0
        and all(
            shares.get(kind, 0.0) >= ORDINARY_CLASS_MIN for kind in (PATCHWORK, RIVALS, PARAMOUNT)
        )
        and shares.get(FRACTURED, 0.0) >= FRACTURED_MIN
        and max(shares.values(), default=1.0) <= CLASS_MAX
    )
    return Check(passed, {"regions": total, "shares": shares})


def _q2(varied: Sequence[World]) -> Check:
    distinct = [
        len({region.kind for region in _structure(world.observation).regions})
        for world in varied
        if len(_structure(world.observation).regions) >= DIVERSE_REGIONS
    ]
    median = _median(distinct)
    return Check(
        bool(distinct) and median >= DIVERSE_CLASSES, {"worlds": len(distinct), "median": median}
    )


def _q3(by_level: Mapping[int, Sequence[World]]) -> Check:
    calm = {world.case: world for world in by_level[CALM]}
    turbulent = {world.case: world for world in by_level[TURBULENT]}
    paired = sorted(calm.keys() & turbulent.keys())

    def pooled(worlds: Iterable[World]) -> float:
        found = [_structure(world.observation) for world in worlds]
        return _share(
            sum(item.recent_locations for item in found),
            sum(item.state_locations for item in found),
        )

    ratio = _share(pooled(turbulent.values()), pooled(calm.values()))
    rising = _share(
        sum(
            _changed(turbulent[key].observation) > _changed(calm[key].observation) for key in paired
        ),
        len(paired),
    )

    def class_share(worlds: Sequence[World], kinds: set[str]) -> float:
        counts = _classes(worlds)
        return _share(sum(counts[kind] for kind in kinds), sum(counts.values()))

    unsettled = {FRACTURED, PATCHWORK}
    continuity = _median(
        _share(world.observation.continuous_countries, world.observation.landed_countries)
        for world in by_level[VARIED]
    )
    passed = (
        ratio >= CHANGED_RATIO
        and rising >= RISING_WORLDS
        and class_share(by_level[TURBULENT], unsettled) > class_share(by_level[CALM], unsettled)
        and class_share(by_level[CALM], {PARAMOUNT}) > class_share(by_level[TURBULENT], {PARAMOUNT})
        and continuity >= CONTINUITY
    )
    return Check(
        passed,
        {
            "changed_ratio": ratio,
            "rising_worlds": rising,
            "unsettled_calm": class_share(by_level[CALM], unsettled),
            "unsettled_turbulent": class_share(by_level[TURBULENT], unsettled),
            "paramount_calm": class_share(by_level[CALM], {PARAMOUNT}),
            "paramount_turbulent": class_share(by_level[TURBULENT], {PARAMOUNT}),
            "continuity": continuity,
        },
    )


def _q4(aims: Sequence[AimOutcome]) -> Check:
    prudent = [aim for aim in aims if aim.kind in EXPANSION and aim.strategy == "prudent"]
    reckless = [aim for aim in aims if aim.kind in EXPANSION and aim.strategy != "prudent"]
    prudent_rate = _share(sum(aim.realized for aim in prudent), len(prudent))
    reckless_rate = _share(
        sum(
            aim.successors or OVERREACH_KEPT[1] * aim.final <= OVERREACH_KEPT[0] * aim.peak
            for aim in reckless
        ),
        len(reckless),
    )
    groups = {
        kind.value: _share(
            sum(aim.realized for aim in aims if aim.kind is kind),
            sum(aim.kind is kind for aim in aims),
        )
        for kind in GROUP_KINDS
        if any(aim.kind is kind for aim in aims)
    }
    passed = (
        (not prudent or prudent_rate >= PRUDENT_REALIZED)
        and (not reckless or reckless_rate >= OVERREACH_ENDED)
        and all(rate >= GROUP_REALIZED for rate in groups.values())
    )
    return Check(
        passed,
        {
            "prudent": (len(prudent), prudent_rate),
            "overreaching": (len(reckless), reckless_rate),
            "groups": groups,
        },
    )


def _q5(sweeps: Sequence[Sweep]) -> Check:
    rows: dict[tuple[str, str], dict[int, Observation]] = defaultdict(dict)
    for sweep in sweeps:
        rows[sweep.control, sweep.pair][sweep.level] = sweep.observation
    failures: list[str] = []
    for control in CONTROLS:
        statistic = STATISTIC[control]
        pairs = [pair for name, pair in rows if name == control]
        if not pairs:
            failures.append(f"{control}: no sweep")
        for pair in pairs:
            levels = rows[control, pair]
            if set(levels) != {LOW, DEFAULT, HIGH}:
                failures.append(f"{control}/{pair}: incomplete levels")
                continue
            if control == "empire_permille" and not _extraordinary_seeded(levels[HIGH]):
                continue  # no eligible domain in this world
            low, default, high = (statistic(levels[level]) for level in (LOW, DEFAULT, HIGH))
            if not (low <= default <= high and high > low):
                failures.append(f"{control}/{pair}: {low} {default} {high}")
    return Check(not failures, {"failures": failures})


def _q6(varied: Sequence[World], sweeps: Sequence[Sweep]) -> Check:
    high = [s for s in sweeps if s.control == "empire_permille" and s.level == HIGH]
    realized = [
        size
        for row in (*(w.observation for w in varied), *(s.observation for s in high))
        for size in _structure(row).great_blocs
    ]
    baseline = [size for row in (*varied, *high) for size in row.baseline_empires]
    ratio = _share(_median(realized), _median(baseline))
    worlds = sum(_extraordinary(s.observation) > 0 for s in high)
    passed = (
        bool(realized) and SCALE[0] <= ratio <= SCALE[1] and worlds >= min(HIGH_WORLDS, len(high))
    )
    return Check(passed, {"realized": len(realized), "ratio": ratio, "high_worlds": worlds})


def _q7(by_level: Mapping[int, Sequence[World]]) -> Check:
    ratios = {
        level: _median(
            _ordinary(world.observation) / world.baseline_ordinary
            for world in worlds
            if world.baseline_ordinary
        )
        for level, worlds in by_level.items()
    }
    passed = ORDINARY_VARIED[0] <= ratios.get(VARIED, 0) <= ORDINARY_VARIED[1] and all(
        ORDINARY_EXTREME[0] <= ratios.get(level, 0) <= ORDINARY_EXTREME[1]
        for level in (CALM, TURBULENT)
    )
    return Check(passed, {"ratios": ratios})


def _q8(worlds: Sequence[World]) -> Check:
    failures: list[str] = []
    for level in LEVELS:
        middle: list[float] = []
        for world in worlds:
            if world.turbulence != level:
                continue
            for mass in world.observation.domination:
                share = _share(mass.largest_bloc, mass.state_locations)
                if mass.founding_states >= CONTINENT and share > DOMINANT:
                    failures.append(f"{world.case}@{level}: continent {share:.3f}")
                elif LANDMASS <= mass.founding_states < CONTINENT:
                    middle.append(share)
                    if share > NEVER_DOMINANT:
                        failures.append(f"{world.case}@{level}: landmass {share:.3f}")
        if (
            middle
            and _share(sum(value > DOMINANT for value in middle), len(middle)) > DOMINATED_SHARE
        ):
            failures.append(f"{level}: too many dominated landmasses")
    return Check(not failures, {"failures": failures})


def _q9_to_q13(varied: Sequence[World], all_worlds: Sequence[World]) -> dict[str, Check]:
    found = [_structure(world.observation) for world in varied]
    subjects = _median(item.subjects for item in found)
    scaled = _share(
        sum(item.scaled_subjects for item in found), sum(item.subjects for item in found)
    )
    alliances = _median(item.alliances for item in found)
    republics = sorted(_share(item.republics, item.states) for item in found)
    q1, q3 = _quartiles(republics)
    types = all(
        item.government_types >= GOVERNMENT_TYPES for item in found if item.states >= TYPED_WORLD
    )
    assortativity = _median(item.assortativity for item in found) / 1000
    families: Counter[str] = Counter()
    for item in found:
        families.update(dict(item.chronicle_families))
    entries = sum(families.values())
    largest = max((_share(count, entries) for count in families.values()), default=1.0)
    routine = _share(families["exchange"] + families["contact"], entries)
    distinct = _median(value for item in found for value in item.chronicle_distinct)
    lengths = [length for world in varied for length in world.observation.chronicle_lengths]
    short = _share(sum(length <= SHORT_CHRONICLE for length in lengths), len(lengths))
    visible = _median(
        _share(
            world.observation.projected_relationship_countries,
            world.observation.landed_countries,
        )
        for world in varied
    )
    return {
        "Q9": Check(
            SUBJECTS[0] <= subjects <= SUBJECTS[1] and scaled >= SCALED_SUBJECTS,
            {"median_subjects": subjects, "scaled": scaled},
        ),
        "Q10": Check(ALLIANCES[0] <= alliances <= ALLIANCES[1], {"median_alliances": alliances}),
        "Q11": Check(
            _median(republics) <= REPUBLICS
            and q3 - q1 >= REPUBLIC_SPREAD
            and types
            and assortativity >= ASSORTATIVITY,
            {
                "republic_median": _median(republics),
                "republic_iqr": q3 - q1,
                "types": types,
                "assortativity": assortativity,
            },
        ),
        "Q12": Check(
            largest <= FAMILY_MAX
            and routine <= ROUTINE_MAX
            and distinct >= LONG_CHRONICLE_FAMILIES
            and short >= SHORT_SHARE
            and max(lengths, default=0) <= CHRONICLE_MAX,
            {"largest": largest, "routine": routine, "distinct": distinct, "short": short},
        ),
        "Q13": Check(visible >= VISIBLE, {"median": visible}),
        "S11": Check(
            all(world.observation.archive_bytes <= MAX_ARCHIVE for world in all_worlds),
            {"largest": max((w.observation.archive_bytes for w in all_worlds), default=0)},
        ),
    }


def evaluate(worlds: Sequence[World], sweeps: Sequence[Sweep]) -> dict[str, Check]:
    """Every statistical criterion of one seed set; nothing is dropped or tuned."""
    by_level: dict[int, list[World]] = {level: [] for level in LEVELS}
    for world in worlds:
        if world.turbulence in by_level:
            by_level[world.turbulence].append(world)
    varied = by_level[VARIED]
    high = [s for s in sweeps if s.control == "empire_permille" and s.level == HIGH]
    aims = [
        aim
        for row in (*(w.observation for w in varied), *(s.observation for s in high))
        for aim in _structure(row).aims
    ]
    checks = {
        "Q1": _q1(varied),
        "Q2": _q2(varied),
        "Q3": _q3(by_level),
        "Q4": _q4(aims),
        "Q5": _q5(sweeps),
        "Q6": _q6(varied, sweeps),
        "Q7": _q7(by_level),
        "Q8": _q8(worlds),
    }
    checks.update(_q9_to_q13(varied, worlds))
    checks["S11"] = Check(
        checks["S11"].passed and all(s.observation.archive_bytes <= MAX_ARCHIVE for s in sweeps),
        checks["S11"].values,
    )
    return checks
