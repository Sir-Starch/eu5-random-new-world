"""Generated names in the scripts of the game's languages, as its translators write American names.

The expected spellings below are the game's own for these names [V-LOCAL 1.4.3, C270]: the
transcription reproduces them exactly. Over all 4,107 one-word American names it agrees exactly
with the game for about half of them (Russian 51 %, Japanese 49 %, Korean 58 %, Chinese 49 %;
C273), the rest being names whose spelling follows another language.
"""

from __future__ import annotations

import pytest

from rnw.translit import cyrillic, hangul, hanzi, katakana, sounds

GAME_SPELLINGS = [
    # name, Russian, Japanese, Korean, Chinese
    ("Tenochtitlan", "Теночтитлан", "テノチティトラン", "테노치티틀란", "特诺奇蒂特兰"),
    ("Teotihuacan", "Теотиуакан", "テオティワカン", "테오티와칸", "特奥蒂瓦坎"),
    ("Wapikisko", "Вапикиско", "ワピキスコ", "와피키스코", "瓦皮基斯科"),
    ("Cabimas", "Кабимас", "カビマス", "카비마스", "卡比马斯"),
    ("Mekapisk", "Мекаписк", "メカピスク", "메카피스크", "梅卡皮斯克"),
    ("Aruni", "Аруни", "アルニ", "아루니", "阿鲁尼"),
]


@pytest.mark.parametrize(("name", "russian", "japanese", "korean", "chinese"), GAME_SPELLINGS)
def test_names_are_written_as_the_game_writes_them(
    name: str, russian: str, japanese: str, korean: str, chinese: str
) -> None:
    assert (cyrillic(name), katakana(name), hangul(name), hanzi(name)) == (
        russian,
        japanese,
        korean,
        chinese,
    )


def test_the_reading_knows_the_american_digraphs() -> None:
    values = [sound.value for sound in sounds("Tzintzuntzan")]
    assert values == ["ts", "i", "n", "ts", "u", "n", "ts", "a", "n"]
    assert [sound.value for sound in sounds("Quechua")][:2] == ["k", "e"]
    assert [sound.value for sound in sounds("Huaxtepec")][:3] == ["hw", "a", "sh"]
    assert [sound.value for sound in sounds("Kwakiutl")][-1] == "tl"


def test_a_doubled_or_marked_vowel_is_long_and_marks_and_apostrophes_drop() -> None:
    long = [sound.long for sound in sounds("Kuujjuaq") if sound.vowel]
    assert long == [True, False, False]
    assert [sound.long for sound in sounds("Ahná:wate") if sound.vowel] == [
        False,
        True,
        False,
        False,
    ]
    assert cyrillic("Ksit'a'í") == cyrillic("Ksitai")


def test_a_final_y_and_c_are_read_at_the_end_of_a_word() -> None:
    assert cyrillic("Jeguaty") == "Джегвати"
    assert cyrillic("Xochitepec") == "Шочитепек"


def test_words_keep_their_separators_and_their_case() -> None:
    assert cyrillic("Sacha-p-qulla") == "Сача-п-кулла"
    assert cyrillic("Urupampu Apu") == "Урупампу Апу"
    assert katakana("Urupampu Apu") == "ウルパンプ・アプ"
    assert hangul("Urupampu Apu") == "우루팜푸 아푸"
    assert hanzi("Urupampu Apu") == "乌鲁帕姆普阿普"


def test_every_letter_of_the_generated_names_is_read() -> None:
    """Names carry letters of many orthographies; none may stop the writing."""
    for name in ("Ggaaleł Taaneo", "Kenatʉka No'", "Süchitki", "Ñaupahuasi", "Ch'ínílį́", "Ƀox"):
        for write in (cyrillic, katakana, hangul, hanzi):
            assert write(name), (name, write.__name__)
