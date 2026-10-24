"""Names a world composes, written in each of the game's languages (roadmap L1).

A generated name is a proper word (``Kaira``) or a *phrase*: a term with a proper word, and for a
part of a sea the compass points that tell it from the other parts (``Northern Kaira Sea``). The
generator keeps phrases as data (``Phrase``) until a world's files are written, and each language
writes them by its own grammar, as the game's translators write its geography and its countries
(``docs/localization.md`` §2.4, §2.5, §3.3): the term before or after the word, glued or apart, an
adjective agreeing with the term's gender, the word in the language's script (``translit``).

A bare ``str`` is a proper word in the generator's Latin spelling. ``REFERENCE`` phrases are the
game's own keys (``$key$``), written unchanged so the game shows its own text in every language.
Pure functions; a language the module does not know is written as English.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from rnw import translit

if TYPE_CHECKING:
    from collections.abc import Callable

ENGLISH: Final[str] = "english"
REFERENCE: Final[str] = "reference"
ADJECTIVE: Final[str] = "adjective"
HIGHLANDS: Final[str] = "highlands"
LAKE: Final[str] = "lake"
# The kinds of water (``seanames.Kind`` values).
WATERS: Final[tuple[str, ...]] = (
    "sea",
    "ocean",
    "gulf",
    "bay",
    "strait",
    "channel",
    "sound",
    "coast",
    "cape",
    "island",
    "islands",
    "archipelago",
)
# Compass points in the order of ``seanames.SECTORS`` (east, then counter-clockwise), the middle
# of a body, and the word repeated before a point that two parts of one body share.
SECTORS: Final[tuple[str, ...]] = (
    "east",
    "north_east",
    "north",
    "north_west",
    "west",
    "south_west",
    "south",
    "south_east",
)
CENTRAL: Final[str] = "central"
FAR: Final[str] = "far"
FORMATION: Final[str] = "formation."
COLONY: Final[str] = "colony."
FORMATIONS: Final[tuple[str, ...]] = (
    "union",
    "confederation",
    "league",
    "commonwealth",
    "realm",
    "federation",
)
TRADITIONS: Final[tuple[str, ...]] = ("spanish", "portuguese", "english", "french", "dutch")


@dataclass(frozen=True, slots=True, order=True)
class Phrase:
    """A term with a proper word, and the compass points of a part of a body of water."""

    term: str
    word: str
    sectors: tuple[str, ...] = field(default=())


type Name = str | Phrase


class WordingError(ValueError):
    """A phrase whose term no language knows."""


def reference(key: str) -> Phrase:
    """A name that is the game's own text under ``key``, in whichever language the game is in."""
    return Phrase(REFERENCE, key)


def adjective(word: str) -> Phrase:
    """The adjective of a country named ``word``."""
    return Phrase(ADJECTIVE, word)


# --- What each language needs -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Term:
    """How one language writes a term: its pattern (``{n}`` for the word), its gender (``m``,
    ``f``, ``n``, ``p`` for a plural) and, where a language needs it, its genitive."""

    pattern: str
    gender: str = "m"
    genitive: str = ""


type Sectors = Callable[[Term, str, str, tuple[str, ...]], str]


def _fill(pattern: str, word: str) -> str:
    return pattern.replace("{n}", word)


@dataclass(frozen=True, slots=True)
class Grammar:
    """One language's way with generated names."""

    proper: Callable[[str], str]
    terms: dict[str, Term]
    sectors: Sectors
    adjective: Callable[[str], str]
    formation: Callable[[str, str], str]
    colony: Callable[[str, str], str]
    fill: Callable[[str, str], str] = field(default=_fill)


def _same(word: str) -> str:
    return word


# English ---------------------------------------------------------------------------------------

EN_TERMS: Final[dict[str, Term]] = {
    "sea": Term("{n} Sea"),
    "ocean": Term("{n} Ocean"),
    "gulf": Term("Gulf of {n}"),
    "bay": Term("{n} Bay"),
    "strait": Term("{n} Strait"),
    "channel": Term("{n} Channel"),
    "sound": Term("{n} Sound"),
    "coast": Term("{n} Coast"),
    "cape": Term("Cape {n}"),
    "island": Term("{n} Island"),
    "islands": Term("{n} Islands"),
    "archipelago": Term("{n} Archipelago"),
    HIGHLANDS: Term("{n} Highlands"),
    LAKE: Term("Lake {n}"),
}
EN_SECTORS: Final[dict[str, str]] = {
    "east": "Eastern",
    "north_east": "North Eastern",
    "north": "Northern",
    "north_west": "North Western",
    "west": "Western",
    "south_west": "South Western",
    "south": "Southern",
    "south_east": "South Eastern",
    CENTRAL: "Central",
    FAR: "Far",
}
EN_FORMATIONS: Final[dict[str, str]] = {
    "union": "{n} Union",
    "confederation": "{n} Confederation",
    "league": "{n} League",
    "commonwealth": "{n} Commonwealth",
    "realm": "{n} Realm",
    "federation": "{n} Federation",
}
# English keeps the founder's own word for *new* (content plan, N4c).
EN_COLONIES: Final[dict[str, str]] = {
    "spanish": "Nueva {n}",
    "portuguese": "Nova {n}",
    "english": "New {n}",
    "french": "Nouvelle-{n}",
    "dutch": "Nieuw-{n}",
}


def _en_sectors(_term: Term, base: str, _word: str, sectors: tuple[str, ...]) -> str:
    return " ".join([*(EN_SECTORS[sector] for sector in sectors), base])


# Russian ---------------------------------------------------------------------------------------

RU_TERMS: Final[dict[str, Term]] = {
    "sea": Term("Море {n}", "m", "моря"),
    "ocean": Term("Океан {n}", "m", "океана"),
    "gulf": Term("Залив {n}", "m", "залива"),
    "bay": Term("Бухта {n}", "m", "бухты"),
    "strait": Term("Пролив {n}", "m", "пролива"),
    "channel": Term("Канал {n}", "m", "канала"),
    "sound": Term("Губа {n}", "m", "губы"),
    "coast": Term("Побережье {n}", "m", "побережья"),
    "cape": Term("Мыс {n}", "m", "мыса"),
    "island": Term("Остров {n}", "m", "острова"),
    "islands": Term("Острова {n}", "m", "островов"),
    "archipelago": Term("Архипелаг {n}", "m", "архипелага"),
    HIGHLANDS: Term("Нагорье {n}", "m", "нагорья"),
    LAKE: Term("Озеро {n}", "m", "озера"),
}
# A part of a body: ``Северная часть моря Кайра``, as the game writes the parts of a strait.
RU_SECTORS: Final[dict[str, str]] = {
    "east": "восточная",
    "north_east": "северо-восточная",
    "north": "северная",
    "north_west": "северо-западная",
    "west": "западная",
    "south_west": "юго-западная",
    "south": "южная",
    "south_east": "юго-восточная",
    CENTRAL: "центральная",
    FAR: "дальняя",
}
RU_FORMATIONS: Final[dict[str, str]] = {
    "union": "ий союз",
    "confederation": "ая конфедерация",
    "league": "ая лига",
    "commonwealth": "ое содружество",
    "realm": "ое царство",
    "federation": "ая федерация",
}


def _ru_sectors(term: Term, _base: str, word: str, sectors: tuple[str, ...]) -> str:
    text = " ".join([*(RU_SECTORS[sector] for sector in sectors), "часть", term.genitive, word])
    return text[:1].upper() + text[1:]


def _ru_adjective(word: str) -> str:
    """The stem the game's Russian texts complete with an ending: *Кайрск* (-ий, -ая, -ие)."""
    stem = translit.cyrillic(word)
    last, before = stem[-1:], stem[-2:-1]
    if last in "иы":
        return stem[:-1] + "ийск"
    if last == "я":
        return stem[:-1] + "йск"
    if last == "а" and before.lower() in "аеёиоуыэюя":
        return stem + "нск"
    if last in "ао":
        return stem[:-1] + "ск"
    return stem + "ск"


def _ru_colony(_tradition: str, word: str) -> str:
    name = translit.cyrillic(word)
    return ("Новая " if name[-1:] in "аяь" else "Новый ") + name


# German ----------------------------------------------------------------------------------------

DE_TERMS: Final[dict[str, Term]] = {
    "sea": Term("{n}-Meer", "n"),
    "ocean": Term("{n}-Ozean", "m"),
    "gulf": Term("Golf von {n}", "m"),
    "bay": Term("{n}-Bucht", "f"),
    "strait": Term("Straße von {n}", "f"),
    "channel": Term("{n}-Kanal", "m"),
    "sound": Term("{n}-Sund", "m"),
    "coast": Term("{n}-Küste", "f"),
    "cape": Term("Kap {n}", "n"),
    "island": Term("Insel {n}", "f"),
    "islands": Term("{n}-Inseln", "p"),
    "archipelago": Term("{n}-Archipel", "m"),
    HIGHLANDS: Term("Hochland von {n}", "n"),
    LAKE: Term("{n}-See", "m"),
}
DE_SECTORS: Final[dict[str, str]] = {
    "east": "östlich",
    "north_east": "nordöstlich",
    "north": "nördlich",
    "north_west": "nordwestlich",
    "west": "westlich",
    "south_west": "südwestlich",
    "south": "südlich",
    "south_east": "südöstlich",
    CENTRAL: "mittler",
    FAR: "äußer",
}
# Strong endings of an adjective without an article, by the gender of its noun.
DE_ENDINGS: Final[dict[str, str]] = {"m": "er", "f": "e", "n": "es", "p": "e"}
DE_FORMATIONS: Final[dict[str, tuple[str, str]]] = {
    "union": ("Union", "f"),
    "confederation": ("Eidgenossenschaft", "f"),
    "league": ("Bund", "m"),
    "commonwealth": ("Gemeinwesen", "n"),
    "realm": ("Reich", "n"),
    "federation": ("Föderation", "f"),
}


def _de_compound(pattern: str, word: str) -> str:
    """A compound joins the parts of a word by hyphens: *Ggaaleł-Taaneo-Meer*."""
    return _fill(pattern, word.replace(" ", "-") if pattern.startswith("{n}-") else word)


def _de_sectors(term: Term, base: str, _word: str, sectors: tuple[str, ...]) -> str:
    ending = DE_ENDINGS[term.gender]
    words = [(DE_SECTORS[sector] + ending).capitalize() for sector in sectors]
    return " ".join([*words, base])


def _de_adjective(word: str) -> str:
    """The adjective the game's German declines: *Kairanisch*, *Chénisch*, *Warsangalisch*."""
    lower = word.lower()
    if lower.endswith("a"):
        return word + "nisch"
    if lower.endswith("i"):
        return word + "sch"
    if lower.endswith("e") and not lower.endswith(("ee", "ie")):
        return word[:-1] + "isch"
    return word + "isch"


def _de_formation(family: str, word: str) -> str:
    noun, gender = DE_FORMATIONS[family]
    return f"{_de_adjective(word)}{DE_ENDINGS[gender]} {noun}"


# French ----------------------------------------------------------------------------------------

FR_TERMS: Final[dict[str, Term]] = {
    "sea": Term("Mer de {n}", "f"),
    "ocean": Term("Océan {n}", "m"),
    "gulf": Term("Golfe de {n}", "m"),
    "bay": Term("Baie de {n}", "f"),
    "strait": Term("Détroit de {n}", "m"),
    "channel": Term("Canal de {n}", "m"),
    "sound": Term("Passe de {n}", "f"),
    "coast": Term("Côte de {n}", "f"),
    "cape": Term("Cap {n}", "m"),
    "island": Term("Île {n}", "f"),
    "islands": Term("Îles {n}", "f"),
    "archipelago": Term("Archipel de {n}", "m"),
    HIGHLANDS: Term("Hautes Terres de {n}", "f"),
    LAKE: Term("Lac {n}", "m"),
}
FR_SECTORS: Final[dict[str, str]] = {
    "east": "Est",
    "north_east": "Nord-Est",
    "north": "Nord",
    "north_west": "Nord-Ouest",
    "west": "Ouest",
    "south_west": "Sud-Ouest",
    "south": "Sud",
    "south_east": "Sud-Est",
    CENTRAL: "Centre",
}
FR_FORMATIONS: Final[dict[str, str]] = {
    "union": "Union de {n}",
    "confederation": "Confédération de {n}",
    "league": "Ligue de {n}",
    "commonwealth": "Communauté de {n}",
    "realm": "Royaume de {n}",
    "federation": "Fédération de {n}",
}
# Not before an *h*: the names are foreign, and French does not elide before a foreign h.
FR_ELISION: Final[re.Pattern[str]] = re.compile(r"\bde ([AEIOUYÀÂÉÈÊËÎÏÔÛÜaeiouyàâéèêëîïôûü])")


def _fr_fill(pattern: str, word: str) -> str:
    """French writes *d'* for *de* before a vowel: *Mer d'Akaira*."""
    return FR_ELISION.sub(r"d'\1", _fill(pattern, word))


def _fr_sectors(_term: Term, base: str, _word: str, sectors: tuple[str, ...]) -> str:
    point = FR_SECTORS[sectors[-1]]
    if sectors[:-1]:
        point = "Extrême-" * len(sectors[:-1]) + point
    article = "de l'" if point[0] in "AEIOU" else "du "
    return f"{base} {article}{point}"


def _fr_colony(_tradition: str, word: str) -> str:
    joined = word.replace(" ", "-")
    return ("Nouvelle-" if word.lower().endswith(("a", "e")) else "Nouveau-") + joined


# Spanish and Portuguese ------------------------------------------------------------------------

ES_TERMS: Final[dict[str, Term]] = {
    "sea": Term("Mar de {n}"),
    "ocean": Term("Océano {n}"),
    "gulf": Term("Golfo de {n}"),
    "bay": Term("Bahía de {n}", "f"),
    "strait": Term("Estrecho de {n}"),
    "channel": Term("Canal de {n}"),
    "sound": Term("Paso de {n}"),
    "coast": Term("Costa de {n}", "f"),
    "cape": Term("Cabo {n}"),
    "island": Term("Isla {n}", "f"),
    "islands": Term("Islas {n}", "p"),
    "archipelago": Term("Archipiélago de {n}"),
    HIGHLANDS: Term("Tierras Altas de {n}", "p"),
    LAKE: Term("Lago {n}"),
}
ES_SECTORS: Final[dict[str, str]] = {
    "east": "Oriental",
    "north_east": "Nororiental",
    "north": "Septentrional",
    "north_west": "Noroccidental",
    "west": "Occidental",
    "south_west": "Suroccidental",
    "south": "Meridional",
    "south_east": "Suroriental",
    CENTRAL: "Central",
    FAR: "Exterior",
}
ES_FORMATIONS: Final[dict[str, str]] = {
    "union": "Unión de {n}",
    "confederation": "Confederación de {n}",
    "league": "Liga de {n}",
    "commonwealth": "Mancomunidad de {n}",
    "realm": "Reino de {n}",
    "federation": "Federación de {n}",
}
PT_TERMS: Final[dict[str, Term]] = {
    "sea": Term("Mar de {n}"),
    "ocean": Term("Oceano {n}"),
    "gulf": Term("Golfo de {n}"),
    "bay": Term("Baía de {n}", "f"),
    "strait": Term("Estreito de {n}"),
    "channel": Term("Canal de {n}"),
    "sound": Term("Passagem de {n}", "f"),
    "coast": Term("Costa de {n}", "f"),
    "cape": Term("Cabo {n}"),
    "island": Term("Ilha {n}", "f"),
    "islands": Term("Ilhas {n}", "p"),
    "archipelago": Term("Arquipélago de {n}"),
    HIGHLANDS: Term("Planalto de {n}"),
    LAKE: Term("Lago {n}"),
}
PT_SECTORS: Final[dict[str, str]] = {
    "east": "Leste",
    "north_east": "Nordeste",
    "north": "Norte",
    "north_west": "Noroeste",
    "west": "Oeste",
    "south_west": "Sudoeste",
    "south": "Sul",
    "south_east": "Sudeste",
    CENTRAL: "Central",
    FAR: "Exterior",
}
PT_FORMATIONS: Final[dict[str, str]] = {
    "union": "União de {n}",
    "confederation": "Confederação de {n}",
    "league": "Liga de {n}",
    "commonwealth": "Comunidade de {n}",
    "realm": "Reino de {n}",
    "federation": "Federação de {n}",
}


def _iberian_sectors(words: dict[str, str], *, agree: bool) -> Sectors:
    """Compass words after the name. Spanish adjectives agree with a plural term (*Islas Kaira
    Occidentales*); Portuguese points of the compass do not (*Ilhas Kaira Oeste*)."""

    def write(term: Term, base: str, _word: str, sectors: tuple[str, ...]) -> str:
        ordered = [sectors[-1], *sectors[:-1]]
        parts = [words[sector] for sector in ordered]
        if term.gender == "p":
            parts = [
                part + "es" if agree or sector == FAR else part
                for part, sector in zip(parts, ordered, strict=True)
            ]
        return " ".join([base, *parts])

    return write


def _iberian_colony(feminine: str, masculine: str) -> Callable[[str, str], str]:
    def write(_tradition: str, word: str) -> str:
        return (masculine if word.lower().endswith("o") else feminine) + " " + word

    return write


# Polish ----------------------------------------------------------------------------------------

PL_TERMS: Final[dict[str, Term]] = {
    "sea": Term("Morze {n}", "n"),
    "ocean": Term("Ocean {n}", "m"),
    "gulf": Term("Zatoka {n}", "f"),
    "bay": Term("Zatoka {n}", "f"),
    "strait": Term("Cieśnina {n}", "f"),
    "channel": Term("Kanał {n}", "m"),
    "sound": Term("Przesmyk {n}", "m"),
    "coast": Term("Wybrzeże {n}", "n"),
    "cape": Term("Przylądek {n}", "m"),
    "island": Term("Wyspa {n}", "f"),
    "islands": Term("Wyspy {n}", "p"),
    "archipelago": Term("Archipelag {n}", "m"),
    HIGHLANDS: Term("Wyżyna {n}", "f"),
    LAKE: Term("Jezioro {n}", "n"),
}
# Stems and whether they are soft (``Wschodni``) or hard (``Północny``).
PL_SECTORS: Final[dict[str, tuple[str, bool]]] = {
    "east": ("Wschodn", True),
    "north_east": ("Północno-Wschodn", True),
    "north": ("Północn", False),
    "north_west": ("Północno-Zachodn", True),
    "west": ("Zachodn", True),
    "south_west": ("Południowo-Zachodn", True),
    "south": ("Południow", False),
    "south_east": ("Południowo-Wschodn", True),
    CENTRAL: ("Środkow", False),
    FAR: ("Dalek", True),
}
PL_ENDINGS: Final[dict[bool, dict[str, str]]] = {
    False: {"m": "y", "f": "a", "n": "e", "p": "e"},
    True: {"m": "i", "f": "ia", "n": "ie", "p": "ie"},
}
PL_FORMATIONS: Final[dict[str, tuple[str, str]]] = {
    "union": ("Unia", "ka"),
    "confederation": ("Konfederacja", "ka"),
    "league": ("Liga", "ka"),
    "commonwealth": ("Wspólnota", "ka"),
    "realm": ("Królestwo", "kie"),
    "federation": ("Federacja", "ka"),
}


def _pl_sectors(term: Term, base: str, _word: str, sectors: tuple[str, ...]) -> str:
    words: list[str] = []
    for sector in sectors:
        stem, soft = PL_SECTORS[sector]
        ending = PL_ENDINGS[soft][term.gender]
        if stem == "Dalek":
            ending = {"m": "i", "f": "a", "n": "ie", "p": "ie"}[term.gender]
        words.append(stem + ending)
    return " ".join([*words, base])


def _pl_adjective(word: str) -> str:
    """The stem the game's Polish completes with -ki/-ka/-kie: *Kairańs*, *Shilluc*, *Cocoms*."""
    lower = word.lower()
    if lower.endswith("n"):
        return word[:-1] + "ńs"
    if lower[-1:] in "aeiouy":
        return word + "ńs"
    if lower.endswith("k"):
        return word[:-1] + "c"
    return word + "s"


def _pl_formation(family: str, word: str) -> str:
    noun, ending = PL_FORMATIONS[family]
    return f"{noun} {_pl_adjective(word)}{ending}"


def _pl_colony(_tradition: str, word: str) -> str:
    return ("Nowa " if word.lower().endswith("a") else "Nowy ") + word


# Turkish ---------------------------------------------------------------------------------------

TR_TERMS: Final[dict[str, Term]] = {
    "sea": Term("{n} Denizi"),
    "ocean": Term("{n} Okyanusu"),
    "gulf": Term("{n} Körfezi"),
    "bay": Term("{n} Koyu"),
    "strait": Term("{n} Boğazı"),
    "channel": Term("{n} Kanalı"),
    "sound": Term("{n} Geçidi"),
    "coast": Term("{n} Kıyısı"),
    "cape": Term("{n} Burnu"),
    "island": Term("{n} Adası"),
    "islands": Term("{n} Adaları"),
    "archipelago": Term("{n} Takımadaları"),
    HIGHLANDS: Term("{n} Yaylası"),
    LAKE: Term("{n} Gölü"),
}
TR_SECTORS: Final[dict[str, str]] = {
    "east": "Doğu",
    "north_east": "Kuzeydoğu",
    "north": "Kuzey",
    "north_west": "Kuzeybatı",
    "west": "Batı",
    "south_west": "Güneybatı",
    "south": "Güney",
    "south_east": "Güneydoğu",
    CENTRAL: "Orta",
    FAR: "Uzak",
}
TR_FORMATIONS: Final[dict[str, str]] = {
    "union": "{n} Birliği",
    "confederation": "{n} Konfederasyonu",
    "league": "{n} Ligi",
    "commonwealth": "{n} Topluluğu",
    "realm": "{n} Devleti",
    "federation": "{n} Federasyonu",
}


def _prefix_sectors(words: dict[str, str]) -> Sectors:
    def write(_term: Term, base: str, _word: str, sectors: tuple[str, ...]) -> str:
        return " ".join([*(words[sector] for sector in sectors), base])

    return write


# Japanese, Korean and Chinese ------------------------------------------------------------------

JA_TERMS: Final[dict[str, Term]] = {
    "sea": Term("{n}海"),
    "ocean": Term("{n}洋"),
    "gulf": Term("{n}湾"),
    "bay": Term("{n}湾"),
    "strait": Term("{n}海峡"),
    "channel": Term("{n}水道"),
    "sound": Term("{n}入江"),
    "coast": Term("{n}海岸"),
    "cape": Term("{n}岬"),
    "island": Term("{n}島"),
    "islands": Term("{n}諸島"),
    "archipelago": Term("{n}群島"),
    HIGHLANDS: Term("{n}高地"),
    LAKE: Term("{n}湖"),
}
JA_SECTORS: Final[dict[str, str]] = {
    "east": "東部",
    "north_east": "北東部",
    "north": "北部",
    "north_west": "北西部",
    "west": "西部",
    "south_west": "南西部",
    "south": "南部",
    "south_east": "南東部",
    CENTRAL: "中部",
    FAR: "最",
}
JA_FORMATIONS: Final[dict[str, str]] = {
    "union": "{n}連合",
    "confederation": "{n}盟約者団",
    "league": "{n}同盟",
    "commonwealth": "{n}共同体",
    "realm": "{n}王国",
    "federation": "{n}連邦",
}
# Japanese and Korean keep the founder's word for *new*, in their script (``ヌエバ・エスパーニャ``).
JA_COLONIES: Final[dict[str, str]] = {
    "spanish": "ヌエバ・{n}",
    "portuguese": "ノヴァ・{n}",
    "english": "ニュー・{n}",
    "french": "ヌーヴェル・{n}",
    "dutch": "ニーウ・{n}",
}
KO_TERMS: Final[dict[str, Term]] = {
    "sea": Term("{n}해"),
    "ocean": Term("{n}양"),
    "gulf": Term("{n}만"),
    "bay": Term("{n}만"),
    "strait": Term("{n} 해협"),
    "channel": Term("{n} 수로"),
    "sound": Term("{n} 해협"),
    "coast": Term("{n} 해안"),
    "cape": Term("{n}곶"),
    "island": Term("{n}섬"),
    "islands": Term("{n} 제도"),
    "archipelago": Term("{n} 군도"),
    HIGHLANDS: Term("{n} 고원"),
    LAKE: Term("{n}호"),
}
KO_SECTORS: Final[dict[str, str]] = {
    "east": "동부",
    "north_east": "북동부",
    "north": "북부",
    "north_west": "북서부",
    "west": "서부",
    "south_west": "남서부",
    "south": "남부",
    "south_east": "남동부",
    CENTRAL: "중부",
    FAR: "외곽",
}
KO_FORMATIONS: Final[dict[str, str]] = {
    "union": "{n} 연합",
    "confederation": "{n} 연맹",
    "league": "{n} 동맹",
    "commonwealth": "{n} 공동체",
    "realm": "{n} 왕국",
    "federation": "{n} 연방",
}
KO_COLONIES: Final[dict[str, str]] = {
    "spanish": "누에바 {n}",
    "portuguese": "노바 {n}",
    "english": "뉴 {n}",
    "french": "누벨 {n}",
    "dutch": "니우 {n}",
}
ZH_TERMS: Final[dict[str, Term]] = {
    "sea": Term("{n}海"),
    "ocean": Term("{n}洋"),
    "gulf": Term("{n}湾"),
    "bay": Term("{n}湾"),
    "strait": Term("{n}海峡"),
    "channel": Term("{n}水道"),
    "sound": Term("{n}海湾"),
    "coast": Term("{n}海岸"),
    "cape": Term("{n}角"),
    "island": Term("{n}岛"),
    "islands": Term("{n}诸岛"),
    "archipelago": Term("{n}群岛"),
    HIGHLANDS: Term("{n}高地"),
    LAKE: Term("{n}湖"),
}
ZH_SECTORS: Final[dict[str, str]] = {
    "east": "东部",
    "north_east": "东北部",
    "north": "北部",
    "north_west": "西北部",
    "west": "西部",
    "south_west": "西南部",
    "south": "南部",
    "south_east": "东南部",
    CENTRAL: "中部",
    FAR: "极",
}
ZH_FORMATIONS: Final[dict[str, str]] = {
    "union": "{n}联合",
    "confederation": "{n}邦联",
    "league": "{n}同盟",
    "commonwealth": "{n}共同体",
    "realm": "{n}王国",
    "federation": "{n}联邦",
}


def _suffix_sectors(words: dict[str, str]) -> Sectors:
    """The part as a suffix (``カイラ海北部``), a far part with its prefix (``最北部``)."""

    def write(_term: Term, base: str, _word: str, sectors: tuple[str, ...]) -> str:
        return base + words[FAR] * len(sectors[:-1]) + words[sectors[-1]]

    return write


def _table(patterns: dict[str, str], proper: Callable[[str], str]) -> Callable[[str, str], str]:
    def write(key: str, word: str) -> str:
        return _fill(patterns[key], proper(word))

    return write


# --- The languages ------------------------------------------------------------------------------

LANGUAGES: Final[dict[str, Grammar]] = {
    ENGLISH: Grammar(
        _same,
        EN_TERMS,
        _en_sectors,
        _same,
        _table(EN_FORMATIONS, _same),
        _table(EN_COLONIES, _same),
    ),
    "russian": Grammar(
        translit.cyrillic,
        RU_TERMS,
        _ru_sectors,
        _ru_adjective,
        lambda family, word: _ru_adjective(word) + RU_FORMATIONS[family],
        _ru_colony,
    ),
    "german": Grammar(
        _same,
        DE_TERMS,
        _de_sectors,
        _de_adjective,
        _de_formation,
        lambda _tradition, word: "Neu-" + word.replace(" ", "-"),
        _de_compound,
    ),
    "french": Grammar(
        _same,
        FR_TERMS,
        _fr_sectors,
        _same,
        lambda family, word: _fr_fill(FR_FORMATIONS[family], word),
        _fr_colony,
        _fr_fill,
    ),
    "spanish": Grammar(
        _same,
        ES_TERMS,
        _iberian_sectors(ES_SECTORS, agree=True),
        _same,
        _table(ES_FORMATIONS, _same),
        _iberian_colony("Nueva", "Nuevo"),
    ),
    "braz_por": Grammar(
        _same,
        PT_TERMS,
        _iberian_sectors(PT_SECTORS, agree=False),
        _same,
        _table(PT_FORMATIONS, _same),
        _iberian_colony("Nova", "Novo"),
    ),
    "polish": Grammar(_same, PL_TERMS, _pl_sectors, _pl_adjective, _pl_formation, _pl_colony),
    "turkish": Grammar(
        _same,
        TR_TERMS,
        _prefix_sectors(TR_SECTORS),
        _same,
        _table(TR_FORMATIONS, _same),
        lambda _tradition, word: "Yeni " + word,
    ),
    "japanese": Grammar(
        translit.katakana,
        JA_TERMS,
        _suffix_sectors(JA_SECTORS),
        translit.katakana,
        _table(JA_FORMATIONS, translit.katakana),
        _table(JA_COLONIES, translit.katakana),
    ),
    "korean": Grammar(
        translit.hangul,
        KO_TERMS,
        _prefix_sectors(KO_SECTORS),
        translit.hangul,
        _table(KO_FORMATIONS, translit.hangul),
        _table(KO_COLONIES, translit.hangul),
    ),
    "simp_chinese": Grammar(
        translit.hanzi,
        ZH_TERMS,
        _suffix_sectors(ZH_SECTORS),
        translit.hanzi,
        _table(ZH_FORMATIONS, translit.hanzi),
        lambda _tradition, word: "新" + translit.hanzi(word),
    ),
}


def grammar(language: str) -> Grammar:
    """The grammar of ``language``; English for a language the module does not know."""
    return LANGUAGES.get(language, LANGUAGES[ENGLISH])


def render(name: Name, language: str) -> str:
    """A name as ``language`` writes it."""
    rules = grammar(language)
    if isinstance(name, str):
        return rules.proper(name)
    if name.term == REFERENCE:
        return f"${name.word}$"
    if name.term == ADJECTIVE:
        return rules.adjective(name.word)
    if name.term.startswith(FORMATION):
        return rules.formation(name.term.removeprefix(FORMATION), name.word)
    if name.term.startswith(COLONY):
        return rules.colony(name.term.removeprefix(COLONY), name.word)
    term = rules.terms.get(name.term)
    if term is None:
        message = f"No language writes the term {name.term!r}"
        raise WordingError(message)
    word = rules.proper(name.word)
    base = rules.fill(term.pattern, word)
    return rules.sectors(term, base, word, name.sectors) if name.sectors else base


def english(name: Name) -> str:
    """A name in English, the language the generator's own reports and window default to."""
    return render(name, ENGLISH)
