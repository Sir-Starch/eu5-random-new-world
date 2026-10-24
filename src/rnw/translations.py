"""Translations of the mod's and the generator's texts into the game's languages (roadmap L1).

English is written in the code, where the text is used; the other languages are catalogs under
``rnw/locale/<language>/<domain>.toml``, one table per key::

    ["rnw_river.1.title"]
    source = "9f86d081884c7d65"
    text = '''Река меняет русло'''

``source`` is the fingerprint of the English text the translation was made from, so a change of
the English makes its translations stale until they are redone. ``translate`` refuses a missing
or stale entry; ``problems`` is the release check that finds every one of them, and a scripted
token (``[...]``, ``$...$``, ``{...}``) that a translation lost or invented. The domains are
``game`` (the world's mod) and ``window`` (the generator). See ``docs/localization.md``.
"""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from collections import Counter
from functools import cache
from importlib import resources
from typing import TYPE_CHECKING, Final

from rnw.languages import SOURCE

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

GAME: Final[str] = "game"
WINDOW: Final[str] = "window"
DOMAINS: Final[tuple[str, ...]] = (GAME, WINDOW)
FINGERPRINT_DIGITS: Final[int] = 16
# Scripted parts of a text that a translation must carry unchanged.
TOKENS: Final[re.Pattern[str]] = re.compile(r"\[[^\]]+\]|\$[^$\s]+\$|\{[a-z_]*(?::[^}]*)?\}")


class TranslationError(ValueError):
    """A text that has no current translation in a language that has a catalog."""


def fingerprint(english: str) -> str:
    """The fingerprint of an English text that a translation records as its source."""
    return hashlib.sha256(english.encode("utf-8")).hexdigest()[:FINGERPRINT_DIGITS]


def tokens(text: str) -> Counter[str]:
    """The scripted parts of a text, counted; a translation may change a part's case format
    (``[X|l]`` for ``[X]``), which the game applies to whatever the part shows."""
    found: list[str] = TOKENS.findall(text)
    return Counter(re.sub(r"\|[A-Za-z]+\]$", "]", token) for token in found)


def catalog_languages() -> tuple[str, ...]:
    """The languages that have catalogs, English (the source) first."""
    root = resources.files("rnw") / "locale"
    found = sorted(entry.name for entry in root.iterdir() if entry.is_dir())
    return (SOURCE, *(name for name in found if name != SOURCE))


@cache
def catalog(domain: str, language: str) -> dict[str, tuple[str, str]]:
    """Each key's source fingerprint and translation; empty when the language has no catalog."""
    path = resources.files("rnw") / "locale" / language / f"{domain}.toml"
    if not path.is_file():
        return {}
    table: dict[str, object] = tomllib.loads(path.read_text(encoding="utf-8"))
    found: dict[str, tuple[str, str]] = {}
    for key, entry in table.items():
        if not isinstance(entry, dict):
            message = f"{language}/{domain}.toml: {key} is not a table"
            raise TranslationError(message)
        source, text = entry.get("source"), entry.get("text")  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if not isinstance(source, str) or not isinstance(text, str):
            message = f"{language}/{domain}.toml: {key} needs a source and a text"
            raise TranslationError(message)
        found[key] = (source, text)
    return found


def has_catalog(domain: str, language: str) -> bool:
    """Whether the generator carries translations of ``domain`` into ``language``."""
    return language == SOURCE or bool(catalog(domain, language))


def translate(domain: str, language: str, sources: Mapping[str, str]) -> dict[str, str]:
    """The texts of ``sources`` (key: English) in ``language``.

    English is the sources themselves. A language without a catalog is the caller's to decide
    (``has_catalog``); in a language with one, a missing or stale entry raises.
    """
    if language == SOURCE:
        return dict(sources)
    entries = catalog(domain, language)
    found: dict[str, str] = {}
    for key, english in sources.items():
        entry = entries.get(key)
        if entry is None or entry[0] != fingerprint(english) or (english and not entry[1]):
            state = "missing" if entry is None else "stale" if entry[1] else "empty"
            message = f"The {language} translation of {key} ({domain}) is {state}"
            raise TranslationError(message)
        found[key] = entry[1]
    return found


def problems(domain: str, sources: Mapping[str, str], languages: Iterable[str]) -> list[str]:
    """Everything that keeps ``domain`` from being released in ``languages``: the release check.

    A key without a current, non-empty translation; a translation whose scripted tokens differ
    from the English; a straight double quote (the game's files end a text at it); a translation
    of a key that no longer exists.
    """
    found: list[str] = []
    for language in languages:
        if language == SOURCE:
            continue
        entries = catalog(domain, language)
        if not entries:
            found.append(f"{language}: no {domain} catalog")
            continue
        for key, english in sources.items():
            entry = entries.get(key)
            if entry is None:
                found.append(f"{language}: {key} is missing")
                continue
            source, text = entry
            if english and not text:
                found.append(f"{language}: {key} is empty")
            elif source != fingerprint(english):
                found.append(f"{language}: {key} is stale")
            elif tokens(text) != tokens(english):
                found.append(f"{language}: {key} changes the scripted parts {tokens(english)}")
            elif '"' in text:
                found.append(f'{language}: {key} holds a straight double quote (")')
        found.extend(f"{language}: {key} has no English source" for key in entries.keys() - sources)
    return found


def _basic(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def _quoted(text: str) -> str:
    """A literal string where the text allows (backslashes stay as written), else a basic one."""
    if "'''" in text or text.endswith("'") or any(char in text for char in "\n\r\t"):
        return _basic(text)
    return f"'''{text}'''"


def dump(entries: Mapping[str, tuple[str, str]]) -> str:
    """A catalog's text: one table per key, in the order given."""
    blocks = [
        f"[{_basic(key)}]\nsource = {_basic(source)}\ntext = {_quoted(text)}\n"
        for key, (source, text) in entries.items()
    ]
    return "\n".join(blocks)


def scaffold(
    current: Mapping[str, tuple[str, str]], sources: Mapping[str, str]
) -> dict[str, tuple[str, str]]:
    """A catalog in the order of ``sources``: current entries kept, stale ones kept with their
    old text and the old fingerprint (the check still reports them), missing ones empty."""
    return {key: current.get(key, (fingerprint(english), "")) for key, english in sources.items()}
