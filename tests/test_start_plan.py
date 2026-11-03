"""H1's population boundary: original bytes and two deliberately distinct identity views."""

# NumPy stubs type scalar indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace

import numpy as np

from rnw.eu5_atlas import build_atlas
from rnw.eu5_content import Place, cohort_places, places
from rnw.eu5_natives import _pop_cohorts, pop_lines  # pyright: ignore[reportPrivateUsage]
from rnw.eu5_start import PopCohort
from rnw.societies import STATE, Polity, Societies

from .fakes import synthetic_world


def test_pop_construction_keeps_the_existing_budget_and_serialization() -> None:
    """A town capital splits its budget among elites, burghers, farmers and tribesmen."""
    societies = Societies(
        complexity=np.array([1000, 0], dtype=np.int64),
        population=np.array([10_000, 0], dtype=np.int64),
        peasants=np.array([5000, 0], dtype=np.int64),
        religion=np.array([0, 0], dtype=np.int64),
        culture=np.array([0, 0], dtype=np.int64),
        hearths=(0,),
        polities=(Polity(STATE, (0,), 0, 0),),
        ranks={0: "town"},
        markets=(0,),
    )
    cohorts = _pop_cohorts(societies, ["seat", "empty"], ["faith"], ["c"])
    assert sum(pop.amount for pop in cohorts["seat"]) == 10_000
    assert pop_lines(cohorts) == {
        "seat": [
            "\tdefine_pop = {\ttype = nobles\tsize = 0.015\tculture = c\treligion = faith }",
            "\tdefine_pop = {\ttype = clergy\tsize = 0.030\tculture = c\treligion = faith }",
            "\tdefine_pop = {\ttype = burghers\tsize = 0.400\tculture = c\treligion = faith }",
            "\tdefine_pop = {\ttype = peasants\tsize = 5.000\tculture = c\treligion = faith }",
            "\tdefine_pop = {\ttype = tribesmen\tsize = 4.555\tculture = c\treligion = faith }",
        ]
    }


def test_content_and_atlas_read_cohorts_with_their_existing_identity_rules() -> None:
    """Content aggregates identity pairs; the atlas takes the largest single pop, first on ties."""
    world, plan, biomes, start, mask = synthetic_world()
    start = replace(
        start,
        pops={
            "rnw_loc_1": (
                PopCohort("peasants", 5000, "a", "faith_a"),
                PopCohort("tribesmen", 5000, "b", "faith_b"),
                PopCohort("clergy", 1000, "b", "faith_b"),
            ),
            "rnw_loc_2": (
                PopCohort("tribesmen", 50, "c", "faith_c"),
                PopCohort("peasants", 50, "d", "faith_d"),
            ),
        },
    )
    assert cohort_places(start.pops) == [
        Place("rnw_loc_1", "b", "faith_b", 11_000),
        Place("rnw_loc_2", "d", "faith_d", 100),
    ]
    # Independent legacy parser establishes the old content interpretation of these bytes.
    assert cohort_places(start.pops) == places(pop_lines(start.pops))
    atlas = build_atlas(world=world, plan=plan, biomes=biomes, natives=start, mask=mask)
    assert atlas.vocabulary["culture"][int(atlas.culture[1])] == "a"
    assert atlas.vocabulary["religion"][int(atlas.religion[1])] == "faith_a"
    assert atlas.vocabulary["culture"][int(atlas.culture[2])] == "c"
    assert atlas.vocabulary["religion"][int(atlas.religion[2])] == "faith_c"
    assert atlas.culture[0] == -1
    assert atlas.religion[0] == -1


def test_empty_plan_populations_need_no_serialized_placeholder() -> None:
    assert pop_lines({}) == {}
    assert cohort_places({}) == []
