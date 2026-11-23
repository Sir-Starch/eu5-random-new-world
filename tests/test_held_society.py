"""A restored country's African holdings carry the society they had in the installed start."""

from __future__ import annotations

import pytest

from rnw.eu5_held_society import (
    EMPTY,
    HeldSocietyError,
    building_lines,
    carry_society,
    institution_lines,
    pair_holdings,
    read_donors,
)
from rnw.pdx import parse

TEXTS = {
    "03_markets.txt": "market_manager = {\n\tadd_market = lisbon\n\tadd_market = alexandria\n}\n",
    "06_pops.txt": """locations={
cairo = {
\tdefine_pop = {\ttype = nobles\tsize = 0.010\tculture = egyptian\treligion = sunni }
\tdefine_pop = {\ttype = peasants\tsize = 90.000\tculture = egyptian\treligion = sunni }
\tdefine_pop = {\ttype = slaves\tsize = 30.000\tculture = egyptian\treligion = sunni }
}
alexandria = {
\tdefine_pop = {\ttype = peasants\tsize = 40.500\tculture = egyptian\treligion = sunni }
\tdefine_pop = {\ttype = burghers\tsize = 1.250\tculture = egyptian\treligion = sunni }
}
siwa = {
\tdefine_pop = {\ttype = tribesmen\tsize = 2.000\tculture = berber\treligion = ibadi }
}
elsewhere = {
\tdefine_pop = {\ttype = peasants\tsize = 5.000\tculture = french\treligion = catholic }
}
}
""",
    "07_cities_and_buildings.txt": """locations={
\tcairo = { rank = megalopolis \ttown_setup = cairo_city }
\talexandria = { rank = city \ttown_setup\t = egyptian_city }
\telsewhere = { rank = town town_setup = french_town }
}
building_manager = {
\tmamluk_barracks = { tag = MAM level = 3 location = cairo }
\tmamluk_barracks = { tag = MAM level = 2 location = alexandria }
\tmonument_qalawun = { tag = MAM level = 1 location = cairo }
\ttrade_office = { tag = VEN level = 1 location = alexandria }
\tmadrasa = { tag = MAM level = 1 location = elsewhere }
}
""",
    "08_institutions.txt": """locations={
cairo = {
\tfeudalism = yes
\tlegalism = yes
}
siwa = {
\tfeudalism = yes
}
}
""",
}


def test_each_donor_reads_its_pops_town_market_institutions_and_own_buildings() -> None:
    donors = read_donors(TEXTS, {"cairo", "alexandria", "siwa"}, "MAM")
    cairo, alexandria, siwa = donors["cairo"], donors["alexandria"], donors["siwa"]
    assert [pop.kind for pop in cairo.pops] == ["nobles", "peasants", "slaves"]
    assert cairo.population == 120_010
    assert cairo.rank == ("megalopolis", "cairo_city")
    assert not cairo.market
    assert cairo.institutions == (("feudalism", "yes"), ("legalism", "yes"))
    # Monuments stay with their place; another country's trade office is not the owner's.
    assert cairo.buildings == (("mamluk_barracks", 3),)
    assert alexandria.market
    assert alexandria.rank == ("city", "egyptian_city")
    assert alexandria.buildings == (("mamluk_barracks", 2),)
    assert siwa.rank is None
    assert siwa.complexity == 0
    assert cairo.complexity == 1000
    assert 0 < alexandria.complexity <= 1000


def test_a_donor_without_population_is_refused() -> None:
    with pytest.raises(HeldSocietyError, match="no population for gone"):
        _ = read_donors(TEXTS, {"cairo", "gone"}, "MAM")


def test_the_capital_takes_the_capital_and_size_follows_the_ground() -> None:
    donors = read_donors(TEXTS, {"cairo", "alexandria", "siwa"}, "MAM")
    holdings = ["a", "b", "c"]
    potential = {"a": 100, "b": 900, "c": 500}
    pairs = pair_holdings(donors, "cairo", holdings, "a", potential)
    assert pairs == {"a": "cairo", "b": "alexandria", "c": "siwa"}
    # The same inputs in another order pair the same way.
    assert pair_holdings(donors, "cairo", holdings[::-1], "a", potential) == pairs


def test_pairing_needs_one_donor_for_each_holding_and_the_capitals() -> None:
    donors = read_donors(TEXTS, {"cairo", "alexandria"}, "MAM")
    with pytest.raises(HeldSocietyError, match="pair one to one"):
        _ = pair_holdings(donors, "cairo", ["a", "b", "c"], "a", {})
    with pytest.raises(HeldSocietyError, match="pair one to one"):
        _ = pair_holdings(donors, "cairo", ["a", "b"], "z", {})
    with pytest.raises(HeldSocietyError, match="pair one to one"):
        _ = pair_holdings(donors, "fez", ["a", "b"], "a", {})


def test_the_society_is_written_under_the_holdings_own_keys() -> None:
    donors = read_donors(TEXTS, {"cairo", "alexandria", "siwa"}, "MAM")
    society = carry_society(donors, {"a": "cairo", "b": "alexandria", "c": "siwa"}, "MAM")
    assert set(society.pops) == {"a", "b", "c"}
    assert society.ranks == {"a": ("megalopolis", "cairo_city"), "b": ("city", "egyptian_city")}
    assert society.markets == ("b",)
    assert society.complexity["c"] == 0
    assert society.buildings == (
        ("mamluk_barracks", "MAM", 3, "a"),
        ("mamluk_barracks", "MAM", 2, "b"),
    )
    institutions = parse("locations = {" + institution_lines(society) + "}").block("locations")
    assert institutions is not None
    assert [entry.key for entry in institutions.entries] == ["a", "c"]
    buildings = parse("building_manager = {" + building_lines(society) + "}").block(
        "building_manager"
    )
    assert buildings is not None
    assert [entry.key for entry in buildings.entries] == ["mamluk_barracks", "mamluk_barracks"]


def test_nothing_to_carry_writes_nothing() -> None:
    assert institution_lines(EMPTY) == ""
    assert building_lines(EMPTY) == ""


def test_two_donors_cannot_share_a_holding() -> None:
    donors = read_donors(TEXTS, {"cairo"}, "MAM")
    society = carry_society(donors, {"a": "cairo"}, "MAM")
    with pytest.raises(HeldSocietyError, match="two donors"):
        _ = society.merge(society)


def test_a_coastal_town_goes_to_the_shore_before_the_best_ground() -> None:
    texts = TEXTS | {
        "07_cities_and_buildings.txt": TEXTS["07_cities_and_buildings.txt"].replace(
            "rank = city \ttown_setup\t = egyptian_city",
            "rank = city town_setup = maghreb_coastal_city",
        )
    }
    donors = read_donors(texts, {"cairo", "alexandria", "siwa"}, "MAM")
    assert donors["alexandria"].coastal
    assert not donors["cairo"].coastal
    holdings = ["a", "b", "c"]
    potential = {"a": 100, "b": 900, "c": 500}
    inland = pair_holdings(donors, "cairo", holdings, "a", potential)
    assert inland["b"] == "alexandria"
    shore = pair_holdings(donors, "cairo", holdings, "a", potential, {"c"})
    assert shore == {"a": "cairo", "c": "alexandria", "b": "siwa"}
    # With no shore to give, the town still has a place.
    assert pair_holdings(donors, "cairo", holdings, "a", potential, {"a"}) == inland
