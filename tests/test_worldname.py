"""How a world is called: the game's title, the window's name, the tag and its bitmap font."""

from __future__ import annotations

import json
from typing import cast

import pytest

from rnw import tagfont, worldname
from rnw.eu5_nw_export import mod_metadata
from rnw.settings import TITLES, WORLD_TYPES


@pytest.mark.parametrize("preset", WORLD_TYPES)
def test_a_default_title_fits_the_game_list_for_every_world_type(preset: str) -> None:
    """``RNW: <Type> <TAG>`` is at most 30 characters and says the type and the tag."""
    title = worldname.label(preset, "7K3Q").title
    assert title == f"RNW: {TITLES[preset]} 7K3Q"
    assert len(title) <= worldname.MAX_TITLE


def test_the_players_name_replaces_the_default_and_is_cut_to_fit() -> None:
    """A name is one line of single spaces; the title never passes the limit; blank is default."""
    assert worldname.label("islands", "AB23", "  My\tAtlantis \n").title == "RNW: My Atlantis"
    long = worldname.label("islands", "AB23", "x" * 80)
    assert len(long.title) == worldname.MAX_TITLE
    assert worldname.display_name("islands", "AB23", "   ") == "Scattered islands AB23"
    assert worldname.clean_name("a" * 24 + " " + "b" * 10) == "a" * 24


def test_the_tag_comes_from_the_id_and_the_fallback_is_stable() -> None:
    """Four capitals of the id; an export without a library derives one from its source."""
    assert worldname.tag_of("k7m2q9abcd") == "K7M2"
    assert worldname.fallback_tag("RNW1-X") == worldname.fallback_tag("RNW1-X")
    assert worldname.fallback_tag("RNW1-X") != worldname.fallback_tag("RNW1-Y")
    assert len(worldname.fallback_tag("anything")) == worldname.TAG_LENGTH


def test_every_glyph_is_five_by_seven_and_what_it_cannot_draw_is_refused() -> None:
    """The table holds the capitals and digits a tag can have, each seven rows of five cells."""
    letters = {chr(code) for code in range(ord("A"), ord("Z") + 1)}
    assert set(tagfont.GLYPHS) == letters | set("0123456789")
    for glyph in tagfont.GLYPHS.values():
        rows = glyph.split("/")
        assert len(rows) == tagfont.HEIGHT
        assert all(len(row) == tagfont.WIDTH for row in rows)
    assert tagfont.text_mask("7K3Q").shape == (tagfont.HEIGHT, 4 * 6 - 1)
    with pytest.raises(ValueError, match="no glyph"):
        _ = tagfont.text_mask("a-1")
    with pytest.raises(ValueError, match="Nothing"):
        _ = tagfont.text_mask("")


def test_the_mods_metadata_carries_the_title_and_the_world_code() -> None:
    """The name is the label's title, with no seed; the code and the status are in the text."""
    data = mod_metadata("rnw_exp_world_x", "RNW: Islands 7K3Q", "RNW1-CODE")
    assert data.startswith(b"\xef\xbb\xbf")
    document = cast("dict[str, str]", json.loads(data.decode("utf-8-sig")))
    assert document["name"] == "RNW: Islands 7K3Q"
    assert document["id"] == "rnw_exp_world_x"
    assert "RNW1-CODE" in document["short_description"]
    assert "NOT GAME VALIDATED" in document["short_description"]
    assert "seed" not in document["name"]
