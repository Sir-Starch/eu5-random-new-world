"""Composed names in each of the game's languages, by the patterns of its own geography (L1)."""

from __future__ import annotations

import pytest

from rnw import wording
from rnw.wording import Phrase, WordingError, adjective, english, reference, render

GULF = Phrase("gulf", "Akaira", ("north",))
FAR_BAY = Phrase("bay", "Kaira", ("far", "south_west"))
ISLANDS = Phrase("islands", "Ggaaleł Taaneo", ("west",))

EXPECTED = {
    "english": ("Northern Gulf of Akaira", "Far South Western Kaira Bay", "Kaira Union"),
    "russian": (
        "Северная часть залива Акайра",
        "Дальняя юго-западная часть бухты Кайра",
        "Кайрский союз",
    ),
    "german": (
        "Nördlicher Golf von Akaira",
        "Äußere Südwestliche Kaira-Bucht",
        "Kairanische Union",
    ),
    "french": ("Golfe d'Akaira du Nord", "Baie de Kaira de l'Extrême-Sud-Ouest", "Union de Kaira"),
    "spanish": (
        "Golfo de Akaira Septentrional",
        "Bahía de Kaira Suroccidental Exterior",
        "Unión de Kaira",
    ),
    "braz_por": ("Golfo de Akaira Norte", "Baía de Kaira Sudoeste Exterior", "União de Kaira"),
    "polish": (
        "Północna Zatoka Akaira",
        "Daleka Południowo-Zachodnia Zatoka Kaira",
        "Unia Kairańska",
    ),
    "turkish": ("Kuzey Akaira Körfezi", "Uzak Güneybatı Kaira Koyu", "Kaira Birliği"),
    "japanese": ("アカイラ湾北部", "カイラ湾最南西部", "カイラ連合"),
    "korean": ("북부 아카이라만", "외곽 남서부 카이라만", "카이라 연합"),
    "simp_chinese": ("阿凯拉湾北部", "凯拉湾极西南部", "凯拉联合"),
}


@pytest.mark.parametrize("language", sorted(EXPECTED))
def test_each_language_writes_parts_of_a_sea_and_a_formable_its_own_way(language: str) -> None:
    union = Phrase(wording.FORMATION + "union", "Kaira")
    assert (render(GULF, language), render(FAR_BAY, language), render(union, language)) == (
        EXPECTED[language]
    )


def test_every_language_knows_every_term_family_and_tradition() -> None:
    for language in wording.LANGUAGES:
        for term in (*wording.WATERS, wording.HIGHLANDS, wording.LAKE):
            assert render(Phrase(term, "Kaira"), language)
            for sector in (*wording.SECTORS, wording.CENTRAL):
                assert render(Phrase(term, "Kaira", (wording.FAR, sector)), language)
        for family in wording.FORMATIONS:
            assert render(Phrase(wording.FORMATION + family, "Kaira"), language)
        for tradition in wording.TRADITIONS:
            assert render(Phrase(wording.COLONY + tradition, "Kaira"), language)


def test_spanish_compass_words_agree_with_a_plural_and_portuguese_ones_do_not() -> None:
    assert render(ISLANDS, "spanish") == "Islas Ggaaleł Taaneo Occidentales"
    assert render(ISLANDS, "braz_por") == "Ilhas Ggaaleł Taaneo Oeste"
    assert render(ISLANDS, "german") == "Westliche Ggaaleł-Taaneo-Inseln"
    assert render(ISLANDS, "polish") == "Zachodnie Wyspy Ggaaleł Taaneo"


def test_french_elides_before_a_vowel_but_not_before_an_h() -> None:
    assert render(Phrase("sea", "Akaira"), "french") == "Mer d'Akaira"
    assert render(Phrase("highlands", "Huande"), "french") == "Hautes Terres de Huande"


def test_country_adjectives_take_the_form_the_games_texts_complete() -> None:
    """Russian and Polish stems, German -isch adjectives, the name elsewhere (C272)."""
    cases = {
        "russian": ("Закатланск", "Шиллукск", "Мийск", "Тоанск", "Осакивакийск"),
        "polish": ("Zacatlańs", "Shilluc", "Miyańs", "Toańs", "Osaakiiwakińs"),
        "german": ("Zacatlanisch", "Shillukisch", "Miyanisch", "Toanisch", "Osaakiiwakisch"),
        "french": ("Zacatlan", "Shilluk", "Miya", "Toa", "Osaakiiwaki"),
    }
    words = ("Zacatlan", "Shilluk", "Miya", "Toa", "Osaakiiwaki")
    for language, forms in cases.items():
        assert tuple(render(adjective(word), language) for word in words) == forms, language


def test_colonies_are_new_in_each_language() -> None:
    spanish = Phrase(wording.COLONY + "spanish", "Taku")
    dutch = Phrase(wording.COLONY + "dutch", "Kaira")
    assert [render(spanish, language) for language in ("english", "russian", "spanish")] == [
        "Nueva Taku",
        "Новый Таку",
        "Nueva Taku",
    ]
    assert render(Phrase(wording.COLONY + "spanish", "Tolo"), "spanish") == "Nuevo Tolo"
    assert render(dutch, "russian") == "Новая Кайра"
    assert render(dutch, "japanese") == "ニーウ・カイラ"
    assert render(dutch, "simp_chinese") == "新凯拉"


def test_references_and_unknown_languages_and_terms() -> None:
    assert {render(reference("pacific_area"), language) for language in wording.LANGUAGES} == {
        "$pacific_area$"
    }
    assert render(GULF, "klingon") == english(GULF)
    assert render("Kaira", "russian") == "Кайра"
    with pytest.raises(WordingError):
        _ = render(Phrase("volcano", "Kaira"), "english")
