"""Generated names written in the scripts of the game's languages (roadmap L1).

The game writes the American place names it ships in Cyrillic for Russian, in katakana for
Japanese, in hangul for Korean and in characters chosen for their sound for Chinese, and keeps
their Latin spelling in its other languages [V-LOCAL 1.4.3, C270]. The generator's names are drawn
from those same names (``eu5_natives.PlaceNamer``) or built from syllables of the same kind
(``names.NameGenerator``), so they are written the same way: a name is read into sounds once
(``sounds``), and each script writes the sounds by its own conventions, the ones the game's own
translators use (``docs/localization.md`` §2.3).

The reading is a practical transcription, not a phonology: digraphs of the American
orthographies (``tl``, ``tz``, ``ch``, ``sh``, ``qu``, ``hu`` before a vowel, ``kw``, ``ny``), a
doubled vowel or a long mark read as one long vowel, apostrophes and glottal marks dropped, ``x``
read as *sh* as in Nahuatl. Pure functions of the name: the same name is always written alike.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Final

VOWELS: Final[str] = "aeiou"
# Letters that are not decomposed by Unicode into a base letter and a mark.
LETTERS: Final[dict[str, str]] = {
    "ł": "l",
    "ʉ": "u",
    "ı": "i",
    "ɨ": "i",
    "đ": "d",
    "ɖ": "d",
    "ß": "ss",
    "æ": "ae",
    "ø": "o",
    "œ": "oe",
    "ŋ": "ng",
    "ç": "s",
}
LONG_MARKS: Final[frozenset[str]] = frozenset({"̄", "́", "̂"})
# Graphemes, longest first: (spelling, sound, condition on the next letter).
DIGRAPHS: Final[tuple[tuple[str, str], ...]] = (
    ("tch", "ch"),
    ("sch", "sh"),
    ("tsh", "ch"),
    ("tz", "ts"),
    ("ts", "ts"),
    ("dz", "dz"),
    ("tl", "tl"),
    ("sh", "sh"),
    ("zh", "zh"),
    ("ch", "ch"),
    ("kh", "h"),
    ("gh", "g"),
    ("th", "t"),
    ("ph", "f"),
    ("dh", "d"),
    ("ck", "k"),
    ("kw", "kw"),
    ("gw", "gw"),
    ("hw", "w"),
    ("ny", "ny"),
    ("ñ", "ny"),
    ("ng", "ng"),
)
SINGLE: Final[dict[str, str]] = {
    "b": "b",
    "d": "d",
    "f": "f",
    "g": "g",
    "h": "h",
    "j": "j",
    "k": "k",
    "l": "l",
    "m": "m",
    "n": "n",
    "p": "p",
    "q": "k",
    "r": "r",
    "s": "s",
    "t": "t",
    "v": "v",
    "x": "sh",
    "z": "z",
}


@dataclass(frozen=True, slots=True)
class Sound:
    """One sound of a name: a consonant or a vowel, a long vowel, a doubled consonant."""

    value: str
    vowel: bool
    long: bool = False
    double: bool = False


def _plain(word: str) -> tuple[str, frozenset[int]]:
    """The word in lowercase ASCII letters and the positions of vowels marked long."""
    letters: list[str] = []
    long: set[int] = set()
    for char in unicodedata.normalize("NFKD", word.casefold()):
        if unicodedata.combining(char):
            if char in LONG_MARKS and letters and letters[-1] in VOWELS:
                long.add(len(letters) - 1)
            continue
        if char == ":" and letters and letters[-1] in VOWELS:
            long.add(len(letters) - 1)
            continue
        if char in "'`’ʼʔ:":
            continue
        letters.extend(LETTERS.get(char, char))
    return "".join(letters), frozenset(long)


def _vowel(letter: str) -> bool:
    return bool(letter) and letter in VOWELS


def _consonant(text: str, index: int) -> tuple[str | None, int]:
    """The consonant spelled at ``index`` and how many letters spell it (None: not a letter)."""
    after = text[index + 1 : index + 2]
    nxt = text[index + 2 : index + 3]
    if text.startswith("qu", index) and _vowel(nxt):
        return ("k" if nxt in "ei" else "kw"), 2
    if text.startswith("gu", index) and _vowel(nxt):
        return ("g" if nxt in "ei" else "gw"), 2
    if text.startswith("hu", index) and _vowel(nxt) and nxt != "u":
        return "hw", 2
    for spelling, value in DIGRAPHS:
        if text.startswith(spelling, index):
            return value, len(spelling)
    if text[index] == "c":
        return ("s" if after and after in "eiy" else "k"), 1
    return SINGLE.get(text[index]), 1


def sounds(word: str) -> list[Sound]:
    """The sounds of one word (no spaces or hyphens) as the transcription reads them."""
    text, marked = _plain(word)
    found: list[Sound] = []
    index = 0
    while index < len(text):
        char = text[index]
        glide = char in "yw" and _vowel(text[index + 1 : index + 2])
        if char in VOWELS or (char in "yw" and not glide):
            value = {"y": "i", "w": "u"}.get(char, char)
            if found and found[-1].vowel and found[-1].value == value:
                found[-1] = Sound(value, vowel=True, long=True)
            else:
                found.append(Sound(value, vowel=True, long=index in marked))
            index += 1
            continue
        value, length = (char, 1) if glide else _consonant(text, index)
        if value is not None and found and not found[-1].vowel and found[-1].value == value:
            found[-1] = Sound(value, vowel=False, double=True)
        elif value is not None:
            found.append(Sound(value, vowel=False))
        index += length
    return found


def _words(name: str) -> list[str]:
    return [part for part in name.replace("-", " ").split() if part]


# --- Cyrillic -----------------------------------------------------------------------------------

CYRILLIC: Final[dict[str, str]] = {
    "p": "п",
    "b": "б",
    "t": "т",
    "d": "д",
    "k": "к",
    "g": "г",
    "m": "м",
    "n": "н",
    "ng": "нг",
    "f": "ф",
    "v": "в",
    "s": "с",
    "z": "з",
    "sh": "ш",
    "zh": "ж",
    "ch": "ч",
    "j": "дж",
    "ts": "ц",
    "dz": "дз",
    "tl": "тл",
    "h": "х",
    "l": "л",
    "r": "р",
    "w": "в",
    "hw": "у",
    "y": "й",
    "kw": "кв",
    "gw": "гв",
    "ny": "нь",
}
PLAIN_VOWELS: Final[dict[str, str]] = {"a": "а", "e": "е", "i": "и", "o": "о", "u": "у"}
# Vowels after a *y*, and after a soft *ny* (which then loses its soft sign).
IOTATED_VOWELS: Final[dict[str, str]] = {"a": "я", "e": "е", "i": "и", "o": "йо", "u": "ю"}
SOFT_VOWELS: Final[dict[str, str]] = {"a": "я", "e": "е", "i": "и", "o": "ьо", "u": "ю"}


def _cyrillic_word(word: str) -> str:
    out: list[str] = []
    found = sounds(word)
    for index, sound in enumerate(found):
        before = found[index - 1] if index else None
        after = found[index + 1] if index + 1 < len(found) else None
        if not sound.vowel:
            if sound.value == "y" and after is not None and after.vowel:
                continue
            letters = "тль" if sound.value == "tl" and after is None else CYRILLIC[sound.value]
            out.append(letters * 2 if sound.double and len(letters) == 1 else letters)
            continue
        if before is not None and not before.vowel and before.value == "y":
            out.append(IOTATED_VOWELS[sound.value])
        elif before is not None and not before.vowel and before.value == "ny":
            out[-1] = out[-1].removesuffix("ь")
            out.append(SOFT_VOWELS[sound.value])
        elif (
            sound.value == "i"
            and before is not None
            and before.vowel
            and (after is None or not after.vowel)
        ):
            out.append("й")
        elif sound.value == "e" and (before is None or before.vowel):
            out.append("э")
        else:
            out.append(PLAIN_VOWELS[sound.value])
    return "".join(out)


def _keep_case(source: str, written: str) -> str:
    """The written word with a capital where the source word has one."""
    return written[:1].upper() + written[1:] if source[:1].isupper() else written


def cyrillic(name: str) -> str:
    """A name in Cyrillic letters, as the game's Russian writes American names.

    Spaces and hyphens stay where they are; each part keeps the case of its first letter, so
    *Sacha-p-qulla* reads as the game writes it, *Сача-п-кулья*.
    """
    parts = re.split(r"([ -]+)", name)
    written = [
        part if index % 2 else _keep_case(part, _cyrillic_word(part))
        for index, part in enumerate(parts)
    ]
    text = "".join(written).strip(" -")
    return text[:1].upper() + text[1:]


# --- Syllables for katakana, hangul and characters ----------------------------------------------


@dataclass(frozen=True, slots=True)
class Syllable:
    """An onset (``""`` for none) with a vowel, or a consonant left without one (``vowel=""``)."""

    onset: str
    vowel: str
    long: bool = False
    double: bool = False
    final: bool = False


def syllables(word: str) -> list[Syllable]:
    """The word as syllables: each consonant before a vowel opens one, others stand alone.

    The Nahuatl *hu* before a vowel is a *w* here; only Cyrillic writes it as a vowel.
    """
    found = [Sound("w", vowel=False) if sound.value == "hw" else sound for sound in sounds(word)]
    out: list[Syllable] = []
    index = 0
    while index < len(found):
        sound = found[index]
        if sound.vowel:
            out.append(Syllable("", sound.value, long=sound.long))
            index += 1
            continue
        after = found[index + 1] if index + 1 < len(found) else None
        if after is not None and after.vowel:
            out.append(Syllable(sound.value, after.value, long=after.long, double=sound.double))
            index += 2
            continue
        out.append(Syllable(sound.value, "", double=sound.double, final=after is None))
        index += 1
    return out


# --- Katakana -----------------------------------------------------------------------------------

# Rows of the syllabary in its own order of vowels: a, i, u, e, o.
KANA_ROWS: Final[dict[str, str]] = {
    "": "アイウエオ",
    "k": "カキクケコ",
    "g": "ガギグゲゴ",
    "s": "サシスセソ",
    "z": "ザジズゼゾ",
    "n": "ナニヌネノ",
    "h": "ハヒフヘホ",
    "b": "バビブベボ",
    "p": "パピプペポ",
    "m": "マミムメモ",
    "r": "ラリルレロ",
    "l": "ラリルレロ",
}
KANA_PAIRS: Final[dict[str, tuple[str, str, str, str, str]]] = {
    "t": ("タ", "ティ", "トゥ", "テ", "ト"),
    "d": ("ダ", "ディ", "ドゥ", "デ", "ド"),
    "y": ("ヤ", "イ", "ユ", "イェ", "ヨ"),
    "w": ("ワ", "ウィ", "ウ", "ウェ", "ウォ"),
    "f": ("ファ", "フィ", "フ", "フェ", "フォ"),
    "v": ("ヴァ", "ヴィ", "ヴ", "ヴェ", "ヴォ"),
    "sh": ("シャ", "シ", "シュ", "シェ", "ショ"),
    "zh": ("ジャ", "ジ", "ジュ", "ジェ", "ジョ"),
    "j": ("ジャ", "ジ", "ジュ", "ジェ", "ジョ"),
    "ch": ("チャ", "チ", "チュ", "チェ", "チョ"),
    "ts": ("ツァ", "ツィ", "ツ", "ツェ", "ツォ"),
    "dz": ("ザ", "ジ", "ズ", "ゼ", "ゾ"),
    "ny": ("ニャ", "ニ", "ニュ", "ニェ", "ニョ"),
    "kw": ("クワ", "クィ", "ク", "クェ", "クォ"),
    "gw": ("グア", "グイ", "グ", "グエ", "グオ"),
    "tl": ("トラ", "トリ", "トル", "トレ", "トロ"),
    "ng": ("ンガ", "ンギ", "ング", "ンゲ", "ンゴ"),
}
KANA_CODA: Final[dict[str, str]] = {
    "n": "ン",
    "m": "ム",
    "ng": "ング",
    "k": "ク",
    "t": "ト",
    "p": "プ",
    "s": "ス",
    "l": "ル",
    "r": "ル",
    "sh": "シュ",
    "ch": "チ",
    "ts": "ツ",
    "tl": "トル",
    "h": "フ",
    "f": "フ",
    "b": "ブ",
    "d": "ド",
    "g": "グ",
    "z": "ズ",
    "j": "ジ",
    "zh": "ジ",
    "dz": "ズ",
    "w": "ウ",
    "y": "イ",
    "kw": "ク",
    "gw": "グ",
    "ny": "ニ",
    "v": "ヴ",
}
STOPS: Final[frozenset[str]] = frozenset({"k", "t", "p", "ch", "ts", "s", "sh", "tl", "kw"})


def _kana(onset: str, vowel: str) -> str:
    column = "aiueo".index(vowel)
    if onset in KANA_ROWS:
        return KANA_ROWS[onset][column]
    return KANA_PAIRS[onset][column]


def _katakana_word(word: str) -> str:
    out: list[str] = []
    found = syllables(word)
    for index, syllable in enumerate(found):
        before = found[index - 1] if index else None
        if syllable.vowel:
            if syllable.double and syllable.onset in STOPS:
                out.append("ッ")
            if syllable.onset == "ng" and (before is None or not before.vowel):
                out.append(_kana("g", syllable.vowel))
            else:
                out.append(_kana(syllable.onset, syllable.vowel))
            if syllable.long:
                out.append("ー")
            continue
        nxt = found[index + 1] if index + 1 < len(found) else None
        if syllable.onset == "m" and nxt is not None and nxt.onset in {"b", "p"}:
            out.append("ン")
            continue
        short = before is not None and before.vowel and not before.long
        if syllable.final and short and syllable.onset in {"k", "t", "p"}:
            out.append("ッ")
        out.append(KANA_CODA[syllable.onset])
    return "".join(out)


def katakana(name: str) -> str:
    """A name in katakana, words joined by a middle dot, as the game's Japanese writes them."""
    return "・".join(_katakana_word(word) for word in _words(name))


# --- Hangul -------------------------------------------------------------------------------------

HANGUL_BASE: Final[int] = 0xAC00
# Initial consonants of a syllable block, by their index among the nineteen.
INITIAL: Final[dict[str, int]] = {
    "g": 0,
    "n": 2,
    "d": 3,
    "l": 5,
    "r": 5,
    "m": 6,
    "b": 7,
    "v": 7,
    "s": 9,
    "sh": 9,
    "": 11,
    "y": 11,
    "w": 11,
    "z": 12,
    "j": 12,
    "zh": 12,
    "dz": 12,
    "ch": 14,
    "ts": 14,
    "k": 15,
    "kw": 15,
    "t": 16,
    "p": 17,
    "f": 17,
    "h": 18,
    "gw": 0,
    "ny": 2,
    "tl": 5,
    "ng": 0,
}
PLAIN_HANGUL_VOWEL: Final[dict[str, int]] = {"a": 0, "e": 5, "i": 20, "o": 8, "u": 13}
Y_HANGUL_VOWEL: Final[dict[str, int]] = {"a": 2, "e": 7, "i": 20, "o": 12, "u": 17}
W_HANGUL_VOWEL: Final[dict[str, int]] = {"a": 9, "e": 15, "i": 16, "o": 14, "u": 13}
EU: Final[int] = 18
FINAL: Final[dict[str, int]] = {"k": 1, "n": 4, "l": 8, "r": 8, "m": 16, "p": 17, "t": 19, "ng": 21}
# Consonants without a vowel that make a syllable of their own with the vowel ``eu``.
ALONE: Final[dict[str, tuple[int, int]]] = {
    "s": (9, EU),
    "sh": (9, 20),
    "ch": (14, 20),
    "ts": (14, EU),
    "j": (12, 20),
    "zh": (12, 20),
    "dz": (12, EU),
    "f": (17, EU),
    "v": (7, EU),
    "b": (7, EU),
    "d": (3, EU),
    "g": (0, EU),
    "z": (12, EU),
    "h": (18, EU),
    "k": (15, EU),
    "t": (16, EU),
    "p": (17, EU),
    "kw": (15, EU),
    "gw": (0, EU),
    "w": (11, 13),
    "y": (11, 20),
    "ny": (2, 20),
}


def _block(initial: int, vowel: int, final: int = 0) -> str:
    return chr(HANGUL_BASE + (initial * 21 + vowel) * 28 + final)


def _hangul_vowel(onset: str, vowel: str) -> int:
    if onset in {"y", "sh", "ny"} and vowel != "i":
        return Y_HANGUL_VOWEL[vowel]
    if onset in {"w", "kw", "gw"}:
        return W_HANGUL_VOWEL[vowel]
    return PLAIN_HANGUL_VOWEL[vowel]


def _hangul_word(word: str) -> str:
    blocks: list[list[int]] = []  # [initial, vowel, final]
    found = syllables(word)
    for index, syllable in enumerate(found):
        last = blocks[-1] if blocks else None
        if syllable.vowel:
            if syllable.onset == "tl":
                blocks.append([16, EU, 8])  # 틀
                blocks.append([5, _hangul_vowel("", syllable.vowel), 0])
                continue
            if syllable.onset in {"l", "ng"} and last is not None and last[2] == 0:
                last[2] = 8 if syllable.onset != "ng" else 21
            blocks.append([
                INITIAL[syllable.onset], _hangul_vowel(syllable.onset, syllable.vowel), 0,
            ])  # fmt: skip
            continue
        before = found[index - 1] if index else None
        can_close = last is not None and last[2] == 0 and before is not None and before.vowel
        closes = syllable.onset in {"n", "m", "ng", "l", "r"} or (
            syllable.onset in {"k", "p", "t"}
            and syllable.final
            and before is not None
            and not before.long
        )
        if syllable.onset == "tl":
            blocks.append([16, EU, 8])
        elif can_close and closes and last is not None:
            last[2] = FINAL[syllable.onset]
        elif syllable.onset in {"n", "m", "ng", "l", "r"}:
            first = {"n": 2, "m": 6, "ng": 11, "l": 5, "r": 5}[syllable.onset]
            blocks.append([first, EU, 21 if syllable.onset == "ng" else 0])
        else:
            initial, vowel = ALONE[syllable.onset]
            blocks.append([initial, vowel, 0])
    return "".join(_block(*block) for block in blocks)


def hangul(name: str) -> str:
    """A name in hangul, words apart, as the game's Korean writes them."""
    return " ".join(_hangul_word(word) for word in _words(name))


# --- Chinese characters -------------------------------------------------------------------------

# The characters of the transliteration tables for an onset and each vowel a, e, i, o, u; then for
# the same with a following n (an, en, in, on, un).
HANZI: Final[dict[str, tuple[str, str]]] = {
    "": ("阿埃伊奥乌", "安恩因翁温"),
    "b": ("巴贝比博布", "班本宾邦本"),
    "p": ("帕佩皮波普", "潘彭平庞蓬"),
    "m": ("马梅米莫穆", "曼门明蒙蒙"),
    "f": ("法费菲福富", "范芬芬丰丰"),
    "v": ("瓦韦维沃武", "万文温翁温"),
    "d": ("达德迪多杜", "丹登丁东敦"),
    "t": ("塔特蒂托图", "坦滕廷通通"),
    "n": ("纳内尼诺努", "南嫩宁农农"),
    "l": ("拉莱利洛卢", "兰伦林隆伦"),
    "r": ("拉雷里罗鲁", "兰伦林隆伦"),
    "g": ("加格吉戈古", "甘根金贡贡"),
    "k": ("卡凯基科库", "坎肯金孔昆"),
    "h": ("哈赫希霍胡", "汉亨欣洪洪"),
    "j": ("贾杰吉乔朱", "詹真金琼准"),
    "zh": ("贾杰吉乔朱", "詹真金琼准"),
    "ch": ("查切奇乔丘", "钱琴钦琼春"),
    "sh": ("沙谢希肖舒", "尚申辛雄顺"),
    "s": ("萨塞西索苏", "桑森辛松孙"),
    "z": ("扎泽齐佐祖", "赞曾津宗尊"),
    "dz": ("扎泽齐佐祖", "赞曾津宗尊"),
    "ts": ("察采齐措楚", "灿岑钦聪村"),
    "w": ("瓦韦维沃武", "万文温翁温"),
    "y": ("亚耶伊约尤", "扬延因永云"),
    "kw": ("夸奎奎阔库", "宽昆昆孔昆"),
    "gw": ("瓜圭圭果古", "关衮衮贡衮"),
}
# Onsets written as two characters, the first standing alone.
HANZI_LEAD: Final[dict[str, tuple[str, str]]] = {"tl": ("特", "l"), "ny": ("尼", "y")}
# Syllables with a following i or u, one character each.
HANZI_AI: Final[dict[str, str]] = {
    "": "艾",
    "b": "拜",
    "p": "派",
    "m": "迈",
    "d": "代",
    "t": "泰",
    "n": "奈",
    "l": "莱",
    "r": "赖",
    "g": "盖",
    "k": "凯",
    "h": "海",
    "ch": "柴",
    "s": "赛",
    "z": "宰",
    "ts": "采",
    "w": "怀",
    "sh": "夏",
    "j": "杰",
    "f": "法",
    "y": "亚",
}
HANZI_AU: Final[dict[str, str]] = {
    "": "奥",
    "b": "包",
    "p": "保",
    "m": "毛",
    "d": "道",
    "t": "陶",
    "n": "瑙",
    "l": "劳",
    "r": "劳",
    "g": "高",
    "k": "考",
    "h": "豪",
    "ch": "乔",
    "s": "绍",
    "z": "藻",
    "ts": "曹",
    "w": "沃",
    "sh": "绍",
    "j": "焦",
    "f": "福",
    "y": "尧",
}
HANZI_CODA: Final[dict[str, str]] = {
    "k": "克",
    "t": "特",
    "p": "普",
    "s": "斯",
    "l": "尔",
    "r": "尔",
    "sh": "什",
    "ch": "奇",
    "ts": "茨",
    "j": "吉",
    "zh": "日",
    "dz": "兹",
    "f": "夫",
    "v": "夫",
    "b": "布",
    "d": "德",
    "g": "格",
    "z": "兹",
    "h": "赫",
    "tl": "特尔",
    "m": "姆",
    "n": "恩",
    "ng": "恩",
    "w": "乌",
    "y": "伊",
    "kw": "克",
    "gw": "格",
    "ny": "尼",
}


def _hanzi_word(word: str) -> str:
    out: list[str] = []
    found = syllables(word)
    index = 0
    while index < len(found):
        syllable = found[index]
        nxt = found[index + 1] if index + 1 < len(found) else None
        if not syllable.vowel:
            out.append(HANZI_CODA[syllable.onset])
            index += 1
            continue
        onset = syllable.onset
        if onset in HANZI_LEAD:
            lead, onset = HANZI_LEAD[onset]
            out.append(lead)
            if onset == "y" and syllable.vowel == "i":
                index += 1
                continue
        if (
            onset in {"k", "g"}
            and syllable.vowel == "u"
            and nxt is not None
            and nxt.onset == ""
            and nxt.vowel in {"a", "e", "i", "o"}
        ):
            onset, syllable = onset + "w", nxt
            index += 1
            nxt = found[index + 1] if index + 1 < len(found) else None
        if onset == "ng":
            onset = "g"
        column = VOWELS.index(syllable.vowel)
        if nxt is not None and nxt.onset == "n" and not nxt.vowel:
            out.append(HANZI[onset][1][column])
            index += 2
            continue
        if (
            syllable.vowel == "a"
            and nxt is not None
            and nxt.onset == ""
            and nxt.vowel in {"i", "u", "o"}
            and not syllable.long
        ):
            table = HANZI_AI if nxt.vowel == "i" else HANZI_AU
            if onset in table:
                out.append(table[onset])
                index += 2
                continue
        out.append(HANZI[onset][0][column])
        index += 1
    return "".join(out)


def hanzi(name: str) -> str:
    """A name in transliteration characters, words run together, as the game's Chinese does."""
    return "".join(_hanzi_word(word) for word in _words(name))
