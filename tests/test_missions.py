"""Missions on the road to a formable (history plan §22.4): seat, land, proclamation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw import wording
from rnw.colonial_names import TRADITIONS
from rnw.content import (
    NEW_WORLD_EMPIRE,
    POSTCOLONIAL_FEDERATION,
    REGIONAL_REALM,
    RIVER_UNION,
    Formation,
)
from rnw.eu5_formation import Identity, block, geography, identities, key_of
from rnw.eu5_formation import texts as formation_texts
from rnw.eu5_missions import (
    ICONS,
    ICONS_DIR,
    ILLUSTRATION,
    ILLUSTRATIONS_DIR,
    MissionError,
    check_installation,
    key,
    missions,
    roads,
    texts,
)
from rnw.eu5_naming import namings
from rnw.game_texts import localize
from rnw.loc_keys import KeySpace, key_hash
from rnw.pdx import parse
from rnw.wording import Phrase

if TYPE_CHECKING:
    from pathlib import Path


def _identity(tag: str, stem: str, word: str) -> Identity:
    return Identity(
        tag, Phrase(wording.FORMATION + stem, word), wording.adjective(word), (1, 2, 3), ("a", "b")
    )


REALM = Formation(
    REGIONAL_REALM,
    0,
    tuple(f"p{n}" for n in range(40)),
    ("p0",),
    ("ABC",),
    "p0",
    region="east_region",
    throne="p0",
)
UNION = Formation(RIVER_UNION, 0, tuple(f"q{n}" for n in range(30)), ("q0",), ("ABC",), "q0")
EMPIRE = Formation(NEW_WORLD_EMPIRE, 0, ("p0",), (), (), "p0", continent="america")


def test_each_formable_smaller_than_the_continent_has_its_road() -> None:
    """Seat, then half of what the formation asks for, then the proclamation, in order."""
    found = roads(
        [REALM, UNION, EMPIRE],
        [
            _identity("REA", "realm", "Laltsu"),
            _identity("UNI", "union", "Kaira"),
            _identity("EMP", "realm", "Toqa"),
        ],
    )
    assert [road.tag for road in found] == ["REA", "UNI"]
    assert [road.half for road in found] == [8, 9]  # 40% of 40 halved; 60% of 30 halved
    script = parse(missions(found))
    mission = script.block(key(found[0]))
    assert mission is not None
    assert mission.block("visible") is not None
    abort = mission.block("abort")
    assert abort is not None
    seat = mission.block(f"{key(found[0])}_seat", "enabled")
    assert seat is not None
    owns = seat.first("owns")
    assert owns is not None
    assert owns.value == "location:p0"
    land = mission.block(f"{key(found[0])}_land")
    assert land is not None
    text = missions(found)
    assert f"scripted_geography:{geography(key_of(REALM))}" in text
    assert "count >= 8 owner ?= root" in text
    proclaim = mission.block(f"{key(found[0])}_proclaim")
    assert proclaim is not None
    final = proclaim.first("final")
    assert final is not None
    assert final.value == "yes"


def test_the_road_is_named_after_its_formable_in_every_language() -> None:
    """The mission and its last task carry the formable's name."""
    found = roads([UNION], [_identity("UNI", "union", "Kaira")])
    english = localize(texts(found), "english")
    assert english[key(found[0])] == "Road to Kaira Union"
    russian = localize(texts(found), "russian")
    assert "Кайрский союз" in russian[f"{key(found[0])}_proclaim_desc"]
    assert russian[f"{key(found[0])}_seat"] == "Взять престол"


def test_a_picture_the_game_lacks_stops_the_export(tmp_path: Path) -> None:
    """The mission's illustration and the tasks' icons come from the installation."""
    pictures = [tmp_path / ILLUSTRATIONS_DIR / f"{ILLUSTRATION}.dds"]
    pictures += [tmp_path / ICONS_DIR / f"{icon}.dds" for icon in ICONS.values()]
    for picture in pictures:
        picture.parent.mkdir(parents=True, exist_ok=True)
        _ = picture.write_bytes(b"DDS ")
    check_installation(tmp_path)
    pictures[-1].unlink()
    with pytest.raises(MissionError, match=pictures[-1].name):
        check_installation(tmp_path)


def test_a_world_hands_out_every_formable_key_through_its_key_space() -> None:
    """A mission, a second name, a nation name and a formable key whose hash is taken are passed
    over for the next free one, all keys of a group together (``loc_keys``)."""
    taken = {
        key_hash(key)
        for key in ("rnw_road_1_land", "rnw_naming.1.b", "UNI_other1", "rnw_union_1_f_desc")
    }
    keys = KeySpace(taken)
    found = roads([UNION], [_identity("UNI", "union", "Kaira")], keys)
    assert key(found[0]) == "rnw_road_2"
    home = Formation(RIVER_UNION, 0, ("q0",), ("q0",), ("ABC",), "q0", home="east_region")
    chosen = namings(
        [(home, "UNI", Phrase(wording.FORMATION + "union", "Kaira"))],
        {"q0": "Kaira"},
        {"east_region": "Laltsu"},
        keys,
    )
    assert chosen["UNI"].event == "rnw_naming.2"
    assert chosen["UNI"].key == "UNI_other2"
    nation = Formation(POSTCOLONIAL_FEDERATION, 0, ("q0",), (), (), "q0", named_by="east_region")
    union, federation = identities(
        [home, nation],
        {"q0": "Kaira"},
        ["UNI", "NAT"],
        5,
        frozenset(),
        regions={"east_region": "Laltsu"},
        keys=keys,
    )
    assert union.key == "rnw_union_2_f"
    assert block(home, union).startswith("rnw_union_2_f = {")
    assert "rnw_union_2_f_desc" in formation_texts([home], [union])
    assert dict(federation.nations) == {t.name: f"NAT_{t.name}_1" for t in TRADITIONS}
    assert "change_country_name = NAT_spanish_1" in block(nation, federation)
