"""The Workshop description in every official language, current against its English source.

Steam takes one description per language, in its own markup (BBCode). The English is
``docs/workshop/english.bbcode``; each translation in ``docs/workshop/<language>.bbcode`` starts
with a line naming the fingerprint of the English it was made from, as the catalogs do
(``rnw.translations``).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from rnw.languages import SOURCE
from rnw.translations import catalog_languages, fingerprint

TEXTS = Path(__file__).parent.parent / "docs" / "workshop"
HEADER = re.compile(r"source: ([0-9a-f]+)\n\n")
TAGS = (
    r"/?(?:h[1-3]|b|i|u|strike|spoiler|noparse|hr|list|olist|\*|quote|code|url|img|table|tr|th|td)"
)
TAG = re.compile(rf"\[{TAGS}(?:=[^\]]*)?\]")
# Our notes for whoever uploads, in brackets like a tag; they stay English and are removed.
NOTE = re.compile(rf"\[(?!{TAGS}[\]=])[^\]]+\]")
# Steam's limit for a Workshop description: 8000 bytes of UTF-8 with the closing NUL, so
# Cyrillic, Greek or CJK text holds far fewer characters than English.
LIMIT = 8000
LANGUAGES = tuple(language for language in catalog_languages() if language != SOURCE)


def _english() -> str:
    return (TEXTS / f"{SOURCE}.bbcode").read_text(encoding="utf-8")


def _translation(language: str) -> tuple[str, str]:
    text = (TEXTS / f"{language}.bbcode").read_text(encoding="utf-8")
    header = HEADER.match(text)
    assert header, f"{language}.bbcode does not start with its source fingerprint"
    return header.group(1), text[header.end() :]


def _published(text: str) -> str:
    return NOTE.sub("", text)


def test_every_official_language_has_a_text() -> None:
    found = {path.stem for path in TEXTS.glob("*.bbcode")}
    assert found == {SOURCE, *LANGUAGES}


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_translation_is_current(language: str) -> None:
    source, _ = _translation(language)
    assert source == fingerprint(_english()), (
        f"docs/workshop/{language}.bbcode was made from another English text: update it, then "
        "its fingerprint"
    )


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_translation_keeps_the_markup_and_links(language: str) -> None:
    _, text = _translation(language)
    assert TAG.findall(text) == TAG.findall(_english())


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_translation_keeps_the_notes(language: str) -> None:
    _, text = _translation(language)
    assert NOTE.findall(text) == NOTE.findall(_english())


@pytest.mark.parametrize("language", [SOURCE, *LANGUAGES])
def test_a_text_fits_the_workshop(language: str) -> None:
    text = _english() if language == SOURCE else _translation(language)[1]
    assert len(_published(text).encode()) < LIMIT
    assert text.startswith("[h1]")
