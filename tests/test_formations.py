"""The formable families: eligible territories, rejected ones, the specs and their files."""

from __future__ import annotations

from itertools import chain
from typing import TYPE_CHECKING

import pytest

from rnw import wording
from rnw.colonial_names import TRADITIONS
from rnw.content import (
    CULTURAL_UNION,
    EMPIRE_REALMS,
    FORMABLE_FAMILIES,
    HIGHLAND_CONFEDERATION,
    HIGHLAND_RELIEF,
    LOWER_FAMILIES,
    MARITIME_LEAGUE,
    NEW_WORLD_EMPIRE,
    POSTCOLONIAL_FEDERATION,
    REALM_CENTRES,
    REALM_STATES,
    REGIONAL_REALM,
    RESTORATION,
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
    geographies,
    geography,
    identities,
    key_of,
    nation_key,
    texts,
)
from rnw.formations import BY_FAMILY, CORES_TOOLTIP, EMPIRE_ADJECTIVE, SPECS, TOP_RANK_LEVEL
from rnw.game_texts import Text, localize
from rnw.pdx import Block, parse
from rnw.wording import Phrase, render

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
    region: Callable[[int], str] = lambda _: "",
) -> Facts:
    """Places along a line, split among states, with the knobs a family reads; ``region`` puts
    each place in a generated region of the continent ``america``."""
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
            region(index),
            "america" if region(index) else "",
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
    """Each family is its own tag stem (which names it in every language), emblem and modifier;
    the empire takes the continent's own name, so its stem names only its key."""
    named = {spec.stem for spec in SPECS if spec.family != NEW_WORLD_EMPIRE}
    assert named == set(wording.FORMATIONS)
    for field in ("stem", "emblem"):
        values = [getattr(spec, field) for spec in SPECS]
        assert len(values) == len(set(values)), field
    names = [spec.modifier.name for spec in SPECS]
    assert len(names) == len(set(names))
    assert all(name.startswith("rnw_") for name in names)
    assert all("{name}" in spec.description for spec in SPECS)
    assert all(spec.modifier.category == "country" for spec in SPECS)


def test_levels_run_up_with_the_families_so_no_chain_can_circle() -> None:
    """A level is a rank level, and the realm stands above the kingdoms above the duchies; the
    empire of the New World stands above every rank, as vanilla's EUR_f, and keeps the empire's."""
    levels = {spec.family: spec.level for spec in SPECS}
    assert all(1 <= level <= TOP_RANK_LEVEL + 1 for level in levels.values())
    assert levels[HIGHLAND_CONFEDERATION] == levels[MARITIME_LEAGUE] < levels[RIVER_UNION]
    assert levels[RIVER_UNION] == levels[CULTURAL_UNION] < levels[REGIONAL_REALM]
    assert levels[REGIONAL_REALM] < levels[NEW_WORLD_EMPIRE] == TOP_RANK_LEVEL + 1
    ranks = {"rank_county": 1, "rank_duchy": 2, "rank_kingdom": 3, "rank_empire": 4}
    assert all(ranks[spec.rank] == min(spec.level, TOP_RANK_LEVEL) for spec in SPECS)
    assert {spec.rule for spec in SPECS} == {"plausible", "fantasy"}
    assert [spec.family for spec in SPECS if spec.rule == "fantasy"] == [NEW_WORLD_EMPIRE]


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


def _halves(index: int) -> str:
    return "east_region" if index < 60 else "west_region"


def test_a_realm_is_a_whole_region_under_several_states_with_its_greatest_centre_as_throne() -> (
    None
):
    """Every place of the region; the throne is its most populous centre; claimants are seated."""
    facts = _chain(count=120, states=10, region=_halves)
    found, _ = formations(facts, SEED, REGIONAL_REALM)
    assert [realm.region for realm in found] == ["east_region", "west_region"]
    for realm in found:
        members = {key for key, place in facts.places.items() if place.region == realm.region}
        assert set(realm.places) == members
        assert realm.throne == realm.seat
        assert realm.throne in realm.centres
        throne = facts.places[realm.throne]
        assert throne.owner in facts.states
        assert throne.population == max(facts.places[key].population for key in realm.centres)
        assert len(realm.states) >= REALM_STATES
        assert all(facts.states[tag].capital in members for tag in realm.states)
    assert len(found[0].centres) >= REALM_CENTRES


def test_a_region_without_several_seated_states_or_regions_unknown_give_no_realm() -> None:
    """Two states make no realm on their own; a world without regions has none to offer."""
    two, why = formations(_chain(count=60, states=2, region=_halves), SEED, REGIONAL_REALM)
    assert not two
    assert f"{REALM_STATES} states" in why
    bare, reason = formations(_chain(count=60, states=5), SEED, REGIONAL_REALM)
    assert not bare
    assert "region" in reason


def test_every_lower_goal_has_a_realm_above_it() -> None:
    """N-C1: the seat of every union, confederation, league and commonwealth lies in a realm,
    even where its region alone would hold too few states (history plan §22.3)."""
    facts = _chain(
        count=120,
        states=12,
        river=1,
        relief=_hills,
        seas=lambda _: ("sea",),
        region=lambda index: f"r{index // 20}",
    )
    plan = plan_content(facts, SEED)
    above = {realm.region for realm in plan.formations if realm.family == REGIONAL_REALM}
    lower = [formation for formation in plan.formations if formation.family in LOWER_FAMILIES]
    assert lower
    for formation in lower:
        assert facts.places[formation.seat].region in above, formation.ident


def test_the_empire_stands_over_the_realms_of_one_continent() -> None:
    """The whole continent of the realms, once it holds the realms of enough regions."""
    facts = _chain(count=120, states=10, region=_halves)
    found, _ = formations(facts, SEED, NEW_WORLD_EMPIRE)
    assert len(found) == 1
    empire = found[0]
    assert empire.continent == "america"
    assert set(empire.places) == set(facts.places)
    assert empire.states == ()
    one, why = formations(
        _chain(count=60, states=5, region=lambda _: "only_region"), SEED, NEW_WORLD_EMPIRE
    )
    assert not one
    assert f"{EMPIRE_REALMS} regions" in why


def test_the_territories_of_one_family_do_not_overlap_but_other_families_may() -> None:
    """Within a family each place is in one territory; across families the land is shared."""
    facts = _chain(
        count=120, states=12, river=1, relief=_hills, seas=lambda _: ("sea",), region=_halves
    )
    plan = plan_content(facts, SEED)
    by_family: dict[str, list[set[str]]] = {}
    for formation in plan.formations:
        by_family.setdefault(formation.family, []).append(set(formation.places))
    assert set(by_family) == set(FORMABLE_FAMILIES) - {CULTURAL_UNION, RESTORATION}
    for family, territories in by_family.items():
        assert family == REGIONAL_REALM or len(territories) <= RULES[family].limit
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
    for relative, source in (
        ("game/in_game/common/biases/00_opinions.txt", OPINIONS),
        ("game/main_menu/common/script_values/00_values.txt", VALUES),
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_text(source.replace(drop, "something_else") if drop else source)
    return root


OPINIONS = "opinion_good_relations = { value = 50 }\nopinion_refused_claim = { value = -30 }\n"
VALUES = "prestige_weak_penalty = -5\nprestige_weak_bonus = 5\n"


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
    with pytest.raises(FormationError, match="opinion_refused_claim"):
        check_installation(
            _installation(tmp_path / "opinion", ranks=RANKS, drop="opinion_refused_claim"), SPECS
        )
    without = [spec for spec in SPECS if not spec.heirs]
    check_installation(
        _installation(tmp_path / "none", ranks=RANKS, drop="opinion_refused_claim"), without
    )


def _formation(family: str, index: int = 0) -> Formation:
    return Formation(family, index, ("loc_a", "loc_b"), ("loc_a",), ("ABC", "DEF"), "loc_a")


def test_every_family_writes_a_formable_of_its_own_level_rank_and_modifier() -> None:
    """The entry carries the family's level, fraction, rule, allow, rank change, founding modifier
    and, but for the empire, the cores on the rest of its territory (N-C3)."""
    for spec in SPECS:
        formation = _formation(spec.family)
        identity = Identity(
            "XYZ",
            Phrase(wording.FORMATION + spec.stem, "Alto"),
            wording.adjective("Alto"),
            (1, 2, 3),
            ("green", "white"),
        )
        text = block(formation, identity)
        entry = parse(text).block(key_of(formation))
        assert entry is not None
        assert key_of(formation) == f"rnw_{spec.stem}_1_f"
        first = entry.first("level")
        assert first is not None
        assert first.value == str(spec.level)
        assert f"required_locations_fraction = {spec.fraction}" in text
        assert f"rule = {spec.rule}" in text
        assert f"country_rank_level < {spec.rank_level}" in text
        assert f"country_rank:{spec.rank}" in text
        assert f"modifier = {spec.modifier.name}" in text
        assert f"years = {spec.years}" in text
        for line in spec.allow:
            assert line in text
        effect = entry.block("form_effect")
        assert effect is not None
        cores = effect.block("hidden_effect")
        assert (cores is not None) == spec.cores
        if cores is not None:
            assert f"custom_tooltip = {CORES_TOOLTIP}" in text
            over = cores.block(f"scripted_geography:{geography(formation)}")
            assert over is not None
            assert over.block("every_location_in_scripted_geography") is not None
            assert "add_core = root" in text
            territory = parse(geographies([formation])).block(geography(formation), "location")
            assert territory is not None
            assert [word.value for word in territory.words()] == list(formation.places)


def test_the_league_asks_for_ports_the_empire_for_hegemony_and_a_realm_for_its_throne() -> None:
    """The league, the empire and the federation name a capability; a realm asks for its throne."""
    asks = {spec.family: spec.allow for spec in SPECS}
    assert asks[MARITIME_LEAGUE] == ("num_of_ports >= 3",)
    assert asks[NEW_WORLD_EMPIRE] == ("is_hegemon = yes", "country_rank = country_rank:rank_empire")
    assert "is_subject = no" in asks[POSTCOLONIAL_FEDERATION][0]
    others = set(asks) - {MARITIME_LEAGUE, NEW_WORLD_EMPIRE, POSTCOLONIAL_FEDERATION}
    assert all(not asks[family] for family in others)
    realm = Formation(
        REGIONAL_REALM, 0, ("a", "b"), ("a",), ("ABC",), "a", region="east_region", throne="a"
    )
    text = block(realm, _identity(REGIONAL_REALM))
    entry = parse(text).block(key_of(realm))
    assert entry is not None
    allow = entry.block("allow")
    assert allow is not None
    owns = allow.first("owns")
    assert owns is not None
    assert owns.value == "location:a"
    regions = entry.block("regions")
    assert regions is not None
    assert [word.value for word in regions.words()] == ["east_region"]
    assert entry.block("locations") is None
    territory = parse(geographies([realm])).block(geography(realm), "region")
    assert territory is not None
    assert [word.value for word in territory.words()] == ["east_region"]
    assert f"scripted_geography:{geography(realm)}" in text


def _identity(family: str) -> Identity:
    return Identity(
        "XYZ",
        Phrase(wording.FORMATION + BY_FAMILY[family].stem, "Alto"),
        wording.adjective("Alto"),
        (1, 2, 3),
        ("red", "blue"),
    )


def test_who_may_form_it_is_decided_in_play() -> None:
    """N-C2: a holder of the land may form it; a commonwealth also opens to its people's culture
    group and the empire to a court on its continent; no family is closed to a list of tags."""
    river = Formation(RIVER_UNION, 0, ("a", "b"), ("a",), ("ABC", "DEF"), "a")
    entry = parse(block(river, _identity(RIVER_UNION))).block(key_of(river))
    assert entry is not None
    potential = entry.block("potential")
    assert potential is not None
    assert not potential.entries
    people = Formation(CULTURAL_UNION, 0, ("a", "b"), ("a",), ("ABC",), "a", basis="tupi_group")
    text = block(people, _identity(CULTURAL_UNION))
    assert "tag = ABC" in text
    assert "culture ?= { has_culture_group = culture_group:tupi_group }" in text
    empire = Formation(NEW_WORLD_EMPIRE, 0, ("a", "b"), (), (), "a", continent="america")
    text = block(empire, _identity(NEW_WORLD_EMPIRE))
    assert "capital.continent = continent:america" in text
    assert "continents = {\n\t\tamerica\n\t}" in text
    assert "rule = fantasy" in text
    assert "hidden_effect" not in text


def test_files_and_texts_cover_every_formation_with_its_family_emblem() -> None:
    """One flag, arms, colour and four keys per formation; the arms use the family's emblem."""
    made = [_formation(spec.family, 0) for spec in SPECS]
    seats = ("Kaira", "Tolan", "Ingari", "Mekapisk", "Huande", "Saumqeir", "Toqa", "Pucara")
    who = [
        Identity(
            f"X{n}Z",
            wording.reference("america"),
            Text(EMPIRE_ADJECTIVE),
            (n, n, n),
            ("red", "blue"),
        )
        if spec.family == NEW_WORLD_EMPIRE
        else Identity(
            f"X{n}Z",
            Phrase(wording.FORMATION + spec.stem, seats[n]),
            wording.adjective(seats[n]),
            (n, n, n),
            ("green", "white"),
        )
        for n, spec in enumerate(SPECS)
    ]
    written = files(made, who)
    arms = written["main_menu/common/coat_of_arms/coat_of_arms/rnw_formations.txt"]
    for spec in SPECS:
        assert spec.emblem in arms
    assert FORMABLES_FILE in written
    keys = texts(made, who)
    for language in ("english", "russian", "japanese"):
        written_keys = localize(keys, language)
        for formation, identity in zip(made, who, strict=True):
            assert written_keys[identity.tag] == render(identity.name, language)
            if isinstance(identity.adjective, Text):
                assert written_keys[f"{identity.tag}_ADJ"]
                continue
            assert written_keys[f"{identity.tag}_ADJ"] == render(identity.adjective, language)
            assert written_keys[key_of(formation)] == f"${identity.tag}$"
            description = written_keys[f"{key_of(formation)}_desc"]
            assert "{name}" not in description
            assert render(identity.name, language) in description
    assert localize(keys, "russian")[who[0].tag] == "Кайрский союз"
    assert localize(keys, "german")[who[0].tag] == "Kairanische Union"
    assert localize(keys, "russian")["X6Z"] == "$america$"
    assert localize(keys, "russian")["X6Z_ADJ"] == "Американск"
    assert CORES_TOOLTIP in keys


def test_a_colonial_shore_needs_a_coast_not_a_state() -> None:
    """The federation's territory is coast, wherever it is settled; no state is offered it."""
    facts = _chain(count=60, states=2, seas=lambda index: ("bay",) if index < 50 else ())
    found, _ = formations(facts, SEED, POSTCOLONIAL_FEDERATION)
    assert found
    shore = RULES[POSTCOLONIAL_FEDERATION]
    for formation in found:
        assert shore.places <= len(formation.places) <= shore.territory
        assert formation.states == ()
        assert all(facts.places[key].seas for key in formation.places)
    inland, reason = formations(_chain(count=60), SEED, POSTCOLONIAL_FEDERATION)
    assert not inland
    assert "colonial shore" in reason


def test_the_federation_is_a_nation_of_settlers_independent_or_leading_their_federation() -> None:
    """Its potential names settlers or a Christian people, never tags (as MEX_f admits a Christian
    native people); it asks for independence or the lead of a colonial federation."""
    spec = BY_FAMILY[POSTCOLONIAL_FEDERATION]
    assert spec.potential == (
        (
            "OR = { culture ?= { is_culture_native_american = no } "
            "religion.group = religion_group:christian }"
        ),
    )
    formation = Formation(
        POSTCOLONIAL_FEDERATION, 0, ("loc_a", "loc_b"), (), (), "loc_a", named_by="east_region"
    )
    alto = Identity(
        "XYZ",
        Phrase(wording.FORMATION + "federation", "Alto"),
        wording.adjective("Alto"),
        (1, 2, 3),
        ("red", "blue"),
    )
    text = block(formation, alto)
    entry = parse(text).block(key_of(formation))
    assert entry is not None
    allow = entry.block("allow", "OR")
    assert allow is not None
    assert allow.first("is_subject") is not None
    leads = allow.block("is_leader_of_international_organization_of_type")
    assert leads is not None
    kind = leads.first("type")
    assert kind is not None
    assert kind.value == "colonial_federation"
    assert "tag = " not in text.replace("\ttag = XYZ", "")
    assert "capital_required = yes" in text
    assert spec.level == 3
    assert float(spec.fraction) < min(float(other.fraction) for other in SPECS if other is not spec)


def test_the_federation_takes_the_name_of_its_founders_tradition() -> None:
    """The region names it; a founder of each tradition takes that tradition's name for it."""
    formation = Formation(
        POSTCOLONIAL_FEDERATION, 0, ("loc_a",), (), (), "loc_a", named_by="east_region"
    )
    [identity] = identities(
        [formation],
        {"loc_a": "Seatname"},
        ["XYZ"],
        SEED,
        frozenset(),
        regions={"east_region": "Laltsu"},
    )
    assert identity.name == Phrase(wording.FORMATION + "federation", "Laltsu")
    text = block(formation, identity)
    effect = parse(text).block(key_of(formation), "form_effect")
    assert effect is not None
    renames = [
        branch.value.first("change_country_name")
        for branch in effect.entries
        if branch.key in {"if", "else_if"} and isinstance(branch.value, Block)
    ]
    keys = [entry.value for entry in renames if entry is not None]
    assert keys == [nation_key("XYZ", tradition.name) for tradition in TRADITIONS]
    assert "culture.language = language:spanish_language" in text
    written = localize(texts([formation], [identity]), "english")
    assert written["XYZ"] == "Laltsu Federation"
    assert written["XYZ_spanish"] == "United Provinces of Laltsu"
    assert written["XYZ_dutch"] == "Generality of Laltsu"
    russian = localize(texts([formation], [identity]), "russian")
    assert russian["XYZ_english"] == "Соединённые колонии Лалцу"
    assert (
        localize(texts([formation], [identity]), "french")["XYZ_french"] == "État libre de Laltsu"
    )


def test_two_federations_of_one_region_are_not_both_named_after_it() -> None:
    """The second federation of a region keeps its seat's name."""
    facts = _chain(
        count=120,
        states=2,
        seas=lambda index: ("bay",) if index % 60 < 50 else (),
        breaks=(59,),
        region=lambda _: "one_region",
    )
    found, _ = formations(facts, SEED, POSTCOLONIAL_FEDERATION)
    assert len(found) == 2
    assert [formation.named_by for formation in found] == ["one_region", ""]


def test_every_family_but_the_empire_opens_a_reform_of_its_own() -> None:
    """A formation unlocks its family's reform, a vanilla payload under the mod's own name."""
    reforms = [spec.reform for spec in SPECS if spec.reform is not None]
    assert [spec.family for spec in SPECS if spec.reform is None] == [NEW_WORLD_EMPIRE]
    names = [reform.name for reform in reforms]
    assert len(names) == len(set(names))
    assert all(name.startswith("rnw_reform_") for name in names)
    assert len({reform.source.name for reform in reforms}) == len(reforms)
    for spec in SPECS:
        text = block(_formation(spec.family), _identity(spec.family))
        if spec.reform is None:
            assert "unlock_government_reform_effect" not in text
        else:
            assert f"unlock_government_reform_effect = {{ type = {spec.reform.name} }}" in text
