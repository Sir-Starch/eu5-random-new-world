"""The formable families: eligible territories, rejected ones, the specs and their files."""

from __future__ import annotations

from itertools import chain
from typing import TYPE_CHECKING

import pytest

from rnw.content import (
    CULTURAL_UNION,
    FORMABLE_FAMILIES,
    HIGHLAND_CONFEDERATION,
    HIGHLAND_RELIEF,
    MARITIME_LEAGUE,
    REGIONAL_REALM,
    RIVER_UNION,
    RULES,
    Facts,
    Formation,
    Place,
    State,
    formations,
    plan_content,
)
from rnw.eu5_formation import (
    EMBLEM_DIR,
    FORMABLES_FILE,
    FormationError,
    Identity,
    block,
    check_installation,
    files,
    key_of,
    texts,
)
from rnw.formations import BY_FAMILY, SPECS
from rnw.pdx import parse

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

SEED = 4242
BROAD = "broad_group"


def _chain(  # noqa: PLR0913 - a synthetic world is these few knobs
    count: int = 40,
    states: int = 4,
    *,
    relief: Callable[[int], str] = lambda _: "",
    culture: Callable[[int], str] = lambda _: "c0",
    seas: Callable[[int], tuple[str, ...]] = lambda _: (),
    river: int = 0,
    breaks: tuple[int, ...] = (),
    groups: dict[str, frozenset[str]] | None = None,
) -> Facts:
    """Places along a line, split among states, with the knobs a family reads."""
    per_state = count // states
    places: dict[str, Place] = {}
    for index in range(count):
        owner = f"S{min(index // per_state, states - 1)}"
        places[f"p{index:03d}"] = Place(
            f"p{index:03d}",
            100 + (index % 7) * 10,
            river,
            "city" if index % 9 == 4 else "",
            "faith",
            owner,
            relief(index),
            culture(index),
            frozenset(seas(index)),
        )
    table = {f"S{n}": State(f"S{n}", f"p{n * per_state:03d}", "faith") for n in range(states)}
    links = frozenset((f"p{i:03d}", f"p{i + 1:03d}") for i in range(count - 1) if i not in breaks)
    return Facts(places, table, frozenset(), links, groups or {})


def _hills(index: int) -> str:
    return "mountains" if index % 2 == 0 else "hills"


def _connected(facts: Facts, formation: Formation) -> bool:
    members = set(formation.places)
    reached = {formation.seat}
    frontier = [formation.seat]
    while frontier:
        here = frontier.pop()
        for first, second in facts.links:
            for a, b in ((first, second), (second, first)):
                if a == here and b in members and b not in reached:
                    reached.add(b)
                    frontier.append(b)
    return reached == members


def test_every_formable_family_has_exactly_one_spec_and_one_rule() -> None:
    """The model and the files agree on which families there are."""
    assert [spec.family for spec in SPECS] == list(FORMABLE_FAMILIES)
    assert set(RULES) == set(FORMABLE_FAMILIES)
    assert set(BY_FAMILY) == set(FORMABLE_FAMILIES)


def test_the_specs_do_not_share_names_pictures_or_modifiers() -> None:
    """Each family is its own tag stem, name suffix, emblem and founding modifier."""
    for field in ("stem", "suffix", "emblem"):
        values = [getattr(spec, field) for spec in SPECS]
        assert len(values) == len(set(values)), field
    names = [spec.modifier.name for spec in SPECS]
    assert len(names) == len(set(names))
    assert all(name.startswith("rnw_") for name in names)
    assert all("{name}" in spec.description for spec in SPECS)
    assert all(spec.modifier.category == "country" for spec in SPECS)


def test_levels_run_up_with_the_families_so_no_chain_can_circle() -> None:
    """A level is a rank level, and the realm stands above the kingdoms above the duchies."""
    levels = {spec.family: spec.level for spec in SPECS}
    assert all(1 <= level <= 4 for level in levels.values())
    assert levels[HIGHLAND_CONFEDERATION] == levels[MARITIME_LEAGUE] < levels[RIVER_UNION]
    assert levels[RIVER_UNION] == levels[CULTURAL_UNION] < levels[REGIONAL_REALM]
    ranks = {"rank_county": 1, "rank_duchy": 2, "rank_kingdom": 3, "rank_empire": 4}
    assert all(ranks[spec.rank] == spec.level for spec in SPECS)


def test_a_range_of_hills_with_high_ground_is_a_confederation() -> None:
    """Connected highland places with enough mountains or plateau under several states."""
    facts = _chain(relief=_hills)
    found, _ = formations(facts, SEED, HIGHLAND_CONFEDERATION)
    assert found
    for formation in found:
        assert _connected(facts, formation)
        assert all(facts.places[key].relief in HIGHLAND_RELIEF for key in formation.places)
        assert len(formation.states) >= RULES[HIGHLAND_CONFEDERATION].states


def test_highlands_without_high_ground_or_cut_by_a_plain_give_no_confederation() -> None:
    """Low hills alone are not a range; a lowland gap splits a range into small valleys."""
    flat_hills = _chain(relief=lambda _: "hills")
    found, reason = formations(flat_hills, SEED, HIGHLAND_CONFEDERATION)
    assert not found
    assert "high ground" in reason
    plateau, _ = formations(_chain(relief=lambda _: "plateau"), SEED, HIGHLAND_CONFEDERATION)
    assert plateau, "an upland plateau is high ground too"
    gap = _chain(relief=lambda index: "flatland" if index % 8 == 7 else _hills(index))
    split, why = formations(gap, SEED, HIGHLAND_CONFEDERATION)
    assert not split
    assert "joins enough populated places" in why
    plain, _ = formations(_chain(), SEED, HIGHLAND_CONFEDERATION)
    assert not plain


def test_a_coast_with_ports_is_a_league_even_across_a_bay() -> None:
    """Ports that share a sea are joined where the land is not; inland places stay out."""
    # two shores of a bay, p000-p019 and p020-p039, with no land link between them
    facts = _chain(
        seas=lambda index: ("bay",) if index in range(10, 30) else (),
        breaks=(19,),
    )
    found, _ = formations(facts, SEED, MARITIME_LEAGUE)
    assert found
    for formation in found:
        assert all(facts.places[key].seas for key in formation.places)
        assert len(formation.places) >= RULES[MARITIME_LEAGUE].places
    joined = [f for f in found if {"p015", "p025"} <= set(f.places)]
    assert joined, "the two shores of the bay form one league"


def test_inland_places_and_unconnected_coasts_give_no_league() -> None:
    """No sea, no league; coasts that share neither a sea nor a land contact stay apart."""
    inland, reason = formations(_chain(), SEED, MARITIME_LEAGUE)
    assert not inland
    assert "stretch of coast" in reason
    apart = _chain(
        seas=lambda index: (f"sea{index // 4}",),
        breaks=tuple(range(3, 39, 4)),
    )
    small, _ = formations(apart, SEED, MARITIME_LEAGUE)
    assert not small


def test_a_people_of_one_group_is_a_cultural_union_on_its_narrowest_group() -> None:
    """The territory is made of places whose main culture is in the seat culture's narrow group."""
    groups = {
        "north": frozenset({"north_group", BROAD}),
        "south": frozenset({"south_group", BROAD}),
    }
    facts = _chain(
        culture=lambda index: "north" if index < 20 else "south",
        groups=groups,
    )
    found, _ = formations(facts, SEED, CULTURAL_UNION)
    assert found
    for formation in found:
        assert formation.basis in {"north_group", "south_group"}
        assert _connected(facts, formation)
        culture = "north" if formation.basis == "north_group" else "south"
        assert all(facts.places[key].culture == culture for key in formation.places)


def test_a_narrow_group_that_is_too_thin_falls_back_on_the_broad_one() -> None:
    """Related peoples join when no single people has the places, and a lone people may not."""
    groups = {f"people{n}": frozenset({f"people{n}_group", BROAD}) for n in range(10)}
    facts = _chain(culture=lambda index: f"people{index // 4}", groups=groups)
    found, _ = formations(facts, SEED, CULTURAL_UNION)
    assert found
    assert {formation.basis for formation in found} == {BROAD}
    lone, reason = formations(_chain(culture=lambda index: f"p{index}"), SEED, CULTURAL_UNION)
    assert not lone
    assert "culture group" in reason


def test_a_scattering_of_another_people_gives_no_eligibility() -> None:
    """Places of a main culture outside the group are not part of its union, however near."""
    groups = {"a": frozenset({"a_group"}), "b": frozenset({"b_group"})}
    facts = _chain(
        culture=lambda index: "b" if index % 5 == 2 else "a",
        groups=groups,
    )
    found, _ = formations(facts, SEED, CULTURAL_UNION)
    for formation in found:
        assert formation.basis == "a_group"
        assert all(facts.places[key].culture == "a" for key in formation.places)


def test_a_realm_needs_a_large_region_with_several_centres_and_states() -> None:
    """Big, connected, under three states or more; too few places or too few states give none."""
    facts = _chain(count=60, states=5)
    found, _ = formations(facts, SEED, REGIONAL_REALM)
    assert len(found) == 1
    realm = found[0]
    assert RULES[REGIONAL_REALM].places <= len(realm.places) <= RULES[REGIONAL_REALM].territory
    assert len(realm.states) >= RULES[REGIONAL_REALM].states
    assert _connected(facts, realm)
    small, reason = formations(_chain(count=20, states=4), SEED, REGIONAL_REALM)
    assert not small
    assert "region" in reason
    two, why = formations(_chain(count=60, states=2), SEED, REGIONAL_REALM)
    assert not two
    assert "3 states" in why


def test_the_territories_of_one_family_do_not_overlap_but_other_families_may() -> None:
    """Within a family each place is in one territory; across families the land is shared."""
    facts = _chain(count=120, states=12, river=1, relief=_hills, seas=lambda _: ("sea",))
    plan = plan_content(facts, SEED)
    by_family: dict[str, list[set[str]]] = {}
    for formation in plan.formations:
        by_family.setdefault(formation.family, []).append(set(formation.places))
    assert set(by_family) == set(FORMABLE_FAMILIES) - {CULTURAL_UNION}
    for family, territories in by_family.items():
        assert len(territories) <= RULES[family].limit
        for number, first in enumerate(territories):
            for second in territories[number + 1 :]:
                assert not first & second
    lands = [set(chain.from_iterable(found)) for found in by_family.values()]
    assert lands[0].intersection(*lands[1:]), "the families share land"


def test_a_family_added_to_the_world_moves_no_other() -> None:
    """Coasts and mountains appear; the river unions stay where they were."""
    bare = plan_content(_chain(count=80, states=8, river=1), SEED)
    rich = plan_content(
        _chain(count=80, states=8, river=1, relief=_hills, seas=lambda _: ("sea",)), SEED
    )
    assert [f for f in rich.formations if f.family == RIVER_UNION] == [
        f for f in bare.formations if f.family == RIVER_UNION
    ]
    assert len(rich.formations) > len(bare.formations)


def test_the_bearers_are_the_states_with_their_capital_in_the_territory() -> None:
    """A state that holds places of the territory without its capital there is not offered it."""
    facts = _chain(count=60, states=5)
    for family in FORMABLE_FAMILIES:
        for formation in formations(facts, SEED, family)[0]:
            for tag in formation.states:
                assert facts.states[tag].capital in formation.places


def _installation(root: Path, *, ranks: str, drop: str = "") -> Path:
    for directory, names in (
        (EMBLEM_DIR, [spec.emblem for spec in SPECS]),
        ("game/main_menu/gfx/coat_of_arms/patterns", ["pattern_solid.dds"]),
    ):
        for name in names:
            if name == drop:
                continue
            picture = root / directory / name
            picture.parent.mkdir(parents=True, exist_ok=True)
            _ = picture.write_bytes(b"DDS ")
    path = root / "game/in_game/common/country_ranks/00_default.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(ranks, encoding="utf-8")
    return root


RANKS = (
    "rank_county = { level = 1 }\nrank_duchy = { level = 2 }\n"
    "rank_kingdom = { level = 3 }\nrank_empire = { level = 4 }\n"
)


def test_a_rank_or_a_picture_the_game_lacks_stops_the_export(tmp_path: Path) -> None:
    """The levels and emblems are checked against the installation, nothing is replaced."""
    check_installation(_installation(tmp_path / "ok", ranks=RANKS), SPECS)
    wrong = RANKS.replace("rank_empire = { level = 4 }", "rank_empire = { level = 5 }")
    with pytest.raises(FormationError, match="rank_empire"):
        check_installation(_installation(tmp_path / "rank", ranks=wrong), SPECS)
    with pytest.raises(FormationError, match=BY_FAMILY[MARITIME_LEAGUE].emblem):
        check_installation(
            _installation(tmp_path / "pic", ranks=RANKS, drop=BY_FAMILY[MARITIME_LEAGUE].emblem),
            SPECS,
        )


def _formation(family: str, index: int = 0) -> Formation:
    return Formation(family, index, ("loc_a", "loc_b"), ("loc_a",), ("ABC", "DEF"), "loc_a")


def test_every_family_writes_a_formable_of_its_own_level_rank_and_modifier() -> None:
    """The entry carries the family's level, fraction, allow, rank change and founding modifier."""
    for spec in SPECS:
        formation = _formation(spec.family)
        identity = Identity("XYZ", "Alto X", "Alto", (1, 2, 3), ("green", "white"))
        text = block(formation, identity)
        entry = parse(text).block(key_of(formation))
        assert entry is not None
        assert key_of(formation) == f"rnw_{spec.stem}_1_f"
        first = entry.first("level")
        assert first is not None
        assert first.value == str(spec.level)
        assert f"required_locations_fraction = {spec.fraction}" in text
        assert f"country_rank_level < {spec.level}" in text
        assert f"country_rank:{spec.rank}" in text
        assert f"modifier = {spec.modifier.name}" in text
        assert f"years = {spec.years}" in text
        for line in spec.allow:
            assert line in text


def test_the_league_asks_for_ports_and_nobody_else_asks_for_anything_more() -> None:
    """Only the league names a capability in its allow block; the others keep it empty."""
    asks = {spec.family: spec.allow for spec in SPECS}
    assert asks[MARITIME_LEAGUE] == ("num_of_ports >= 3",)
    assert all(not allow for family, allow in asks.items() if family != MARITIME_LEAGUE)


def test_files_and_texts_cover_every_formation_with_its_family_emblem() -> None:
    """One flag, arms, colour and four keys per formation; the arms use the family's emblem."""
    made = [_formation(spec.family, 0) for spec in SPECS]
    who = [
        Identity(f"X{n}Z", f"Name{n}", f"Adj{n}", (n, n, n), ("green", "white"))
        for n in range(len(made))
    ]
    written = files(made, who)
    arms = written["main_menu/common/coat_of_arms/coat_of_arms/rnw_formations.txt"]
    for spec in SPECS:
        assert spec.emblem in arms
    assert FORMABLES_FILE in written
    keys = texts(made, who)
    for formation, identity in zip(made, who, strict=True):
        assert identity.tag in keys
        assert f"{identity.tag}_ADJ" in keys
        assert keys[key_of(formation)] == f"${identity.tag}$"
        assert "{name}" not in keys[f"{key_of(formation)}_desc"]
        assert identity.name in keys[f"{key_of(formation)}_desc"]
