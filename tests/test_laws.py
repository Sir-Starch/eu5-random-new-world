"""Every law a generated state sees at the start holds a policy (``eu5_laws``)."""

from __future__ import annotations

import pytest

from rnw.eu5_laws import Facts as LawFacts
from rnw.eu5_laws import LawError, complete, read_book, shown
from rnw.history_values import SHOWN

LAWS = """
royal_court_customs_law = {
\tlaw_category = administrative
\tpotential = { government_type = government_type:monarchy }
\taristocratic_court_policy = { country_modifier = { monthly_towards_aristocracy = 1 } }
\tbalanced_court_policy = { }
\tcourt_of_culture_policy = { country_modifier = { monthly_towards_innovative = 1 } }
}
cultural_traditions_law = {
\tmartial_society = { country_modifier = { monthly_towards_belligerent = 1 } }
\tcivil_society = { country_modifier = { monthly_towards_conciliatory = 1 } }
}
legal_code_law = {
\tpotential = { OR = { has_tribal_government = no religion = religion:mystery } }
\ttraditional_law_policy = { }
\tsharia_law_policy = { potential = { religion.group = religion_group:muslim } }
}
theocratic_leadership = {
\tpotential = { government_type = government_type:theocracy }
\tclerical_state = { }
}
divine_cause_law = {
\tpotential = { government_type = government_type:theocracy }
\tpursuit_of_knowledge_policy = { country_modifier = { monthly_towards_innovative = 1 } }
\tcombat_heresy_policy = { country_modifier = { monthly_towards_belligerent = 1 } }
}
slave_conversion = {
\tpotential = {
\t\tOR = {
\t\t\tpop_type_population_in_country = { pop_type = pop_type:slaves value > 0 }
\t\t\thas_law = slave_conversion
\t\t}
\t}
\tallow_slave_religion = { }
}
precious_metal_distribution_law = {
\tpotential = { produced_in_country:goods_gold > 0 }
\tgold_export_ban = { }
}
renaissance_law = { only_policy = { } }
alliance_law = { type = international_organization member_policy = { } }
"""
ADVANCES = """
written_alphabet = { age = age_1_traditions starting_technology_level = 2 }
cultural_traditions_law_advance = {
\tage = age_1_traditions
\trequires = written_alphabet
\tunlock_law = cultural_traditions_law
}
monarchy_royal_court_advance = {
\tage = age_1_traditions
\trequires = written_alphabet
\tunlock_law = royal_court_customs_law
}
theocracy_divine_cause_law_advance = {
\tage = age_1_traditions
\tunlock_law = divine_cause_law
}
university_advance = { age = age_2_renaissance unlock_law = renaissance_law }
"""
TEMPLATES = {
    "amerindian_monarchy": (
        "starting_technology_level = 0\n"
        "government = { type = monarchy laws = { legal_code_law = traditional_law_policy } }\n"
    ),
    "amerindian_advanced_monarchy_not_nahuatl": (
        "starting_technology_level = 2\n"
        "government = {\n\ttype = monarchy\n\taristocracy_vs_plutocracy = -60\n"
        "\tbelligerent_vs_conciliatory = 30\n"
        "\tlaws = { legal_code_law = traditional_law_policy }\n}\n"
    ),
    "amerindian_tribe": "government = { type = tribe }\n",
    "republic_t": "government = { type = republic }\n",
    "noble": 'include = "amerindian_monarchy"\n',
}
# Vanilla's 1337 holders: monarchies hold the aristocratic court 60 times, the balanced one 39
# and the court of culture once; martial and civil society half each; the theocracy one each.
MONARCHY = """\t\tM{n:02d} = {{ include = "noble" government = {{ laws = {{
\t\t\troyal_court_customs_law = {court} cultural_traditions_law = {society}
\t\t\tslave_conversion = allow_slave_religion
\t\t}} }} }}
"""
THEOCRACY = """\t\tTHE = { government = { type = theocracy laws = {
\t\t\ttheocratic_leadership = clerical_state divine_cause_law = pursuit_of_knowledge_policy
\t\t\tcultural_traditions_law = civil_society legal_code_law = traditional_law_policy
\t\t} } }
"""
SETUP = (
    "countries = {\n\tcountries = {\n"
    + "".join(
        MONARCHY.format(n=n, court=court, society="martial_society" if n % 2 else "civil_society")
        for n, court in enumerate(
            ["aristocratic_court_policy"] * 60
            + ["balanced_court_policy"] * 39
            + ["court_of_culture_policy"]
        )
    )
    + THEOCRACY
    + '\t\tPOP = { type = pop include = "amerindian_tribe" }\n'
    + "\t}\n}\n"
)
# Every value the game defines, in its order (``history_values.SHOWN`` and the gated ones).
VALUES = "".join(
    f"{axis} = {{ }}\n"
    for axis in (
        *SHOWN,
        "mercantilism_vs_free_trade",
        "outward_vs_inward",
        "mysticism_vs_jurisprudence",
    )
)
LAW_BOOK = read_book(
    law_texts=[LAWS],
    advance_texts=[ADVANCES],
    templates=TEMPLATES,
    setup_text=SETUP,
    value_texts=[VALUES],
)


def _complete(include: str, level: int, fields: tuple[tuple[str, str], ...] = ()) -> dict[str, str]:
    return dict(
        complete(
            LAW_BOOK,
            include=include,
            fields=fields,
            laws=(),
            level=level,
            religion="mystery",
            culture="people",
        )
    )


def test_a_state_of_the_advanced_template_gets_the_laws_its_template_leaves_empty() -> None:
    """The template sets its legal code; the court and the traditions follow its values: it
    leans to aristocracy and to conciliation."""
    laws = _complete("amerindian_advanced_monarchy_not_nahuatl", 2)
    assert laws == {
        "royal_court_customs_law": "aristocratic_court_policy",
        "cultural_traditions_law": "civil_society",
        "slave_conversion": "allow_slave_religion",
    }


def test_the_countrys_own_values_choose_among_the_mainstream_policies() -> None:
    """A belligerent plutocracy keeps a martial society and the balanced court; the court of
    culture, held once in a hundred, is no choice even for an innovative country."""
    fields = (
        ("aristocracy_vs_plutocracy", "40"),
        ("belligerent_vs_conciliatory", "-20"),
        ("traditionalist_vs_innovative", "80"),
    )
    laws = _complete("amerindian_advanced_monarchy_not_nahuatl", 2, fields)
    assert laws["royal_court_customs_law"] == "balanced_court_policy"
    assert laws["cultural_traditions_law"] == "martial_society"


def test_a_law_unlocked_by_an_advance_above_the_level_stays_hidden() -> None:
    """At level 1 writing is not known, so neither the court nor the traditions are shown; a law
    no advance unlocks is shown by its potential alone."""
    laws = _complete("noble", 1)
    assert "royal_court_customs_law" not in laws
    assert "cultural_traditions_law" not in laws
    assert laws == {"slave_conversion": "allow_slave_religion"}


def test_a_theocracy_without_a_template_gets_its_own_laws() -> None:
    """Only what vanilla's theocracies hold: none holds slave conversion, so it stays empty."""
    laws = _complete("", 2, (("type", "theocracy"),))
    assert laws == {
        "legal_code_law": "traditional_law_policy",
        "theocratic_leadership": "clerical_state",
        "divine_cause_law": "pursuit_of_knowledge_policy",
        "cultural_traditions_law": "civil_society",
    }


def test_an_undecided_potential_and_an_organization_law_are_left_out() -> None:
    facts = LawFacts("monarchy", 3, "mystery", "people", {}, {})
    seen = shown(LAW_BOOK, facts)
    assert "precious_metal_distribution_law" not in seen
    assert "alliance_law" not in seen
    assert "renaissance_law" not in seen
    assert "legal_code_law" in seen


def test_written_laws_come_first_and_stay() -> None:
    written = complete(
        LAW_BOOK,
        include="amerindian_advanced_monarchy_not_nahuatl",
        fields=(),
        laws=(("royal_court_customs_law", "balanced_court_policy"),),
        level=2,
        religion="mystery",
        culture="people",
    )
    assert written[0] == ("royal_court_customs_law", "balanced_court_policy")
    assert [law for law, _ in written].count("royal_court_customs_law") == 1


def test_an_unknown_template_is_refused() -> None:
    with pytest.raises(LawError, match="not installed"):
        _ = _complete("missing_template", 2)
