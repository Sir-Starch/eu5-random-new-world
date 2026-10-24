"""The Workshop description in every official language, current against its English draft.

Steam takes one description per language. ``docs/workshop-description.md`` holds the English
below its ``---`` line; each translation in ``docs/workshop/<language>.md`` starts with the
fingerprint of the English it was made from, as the catalogs do (``rnw.translations``).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from rnw.languages import SOURCE
from rnw.translations import catalog_languages, fingerprint

ROOT = Path(__file__).parent.parent
DRAFT = ROOT / "docs" / "workshop-description.md"
TRANSLATIONS = ROOT / "docs" / "workshop"
HEADER = re.compile(r"<!-- source: ([0-9a-f]+) -->\n\n")
# What a translation carries over unchanged: our bracketed notes, links and paths in code.
KEPT = re.compile(r"\[[^\]]+\](?!\()|https://[\w./-]*[\w/]|`[^`]+`", re.ASCII)
LANGUAGES = tuple(language for language in catalog_languages() if language != SOURCE)


def _english() -> str:
    _, separator, english = DRAFT.read_text(encoding="utf-8").partition("\n---\n")
    assert separator, f"{DRAFT} has no --- line"
    return english.strip() + "\n"


def _translation(language: str) -> tuple[str, str]:
    text = (TRANSLATIONS / f"{language}.md").read_text(encoding="utf-8")
    header = HEADER.match(text)
    assert header, f"{language}.md does not start with its source fingerprint"
    return header.group(1), text[header.end() :]


def test_every_official_language_has_a_translation() -> None:
    found = {path.stem for path in TRANSLATIONS.glob("*.md")}
    assert found == set(LANGUAGES)


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_translation_is_current(language: str) -> None:
    source, _ = _translation(language)
    assert source == fingerprint(_english()), (
        f"docs/workshop/{language}.md was made from another English text: update it, then "
        "its fingerprint"
    )


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_translation_keeps_notes_links_and_paths(language: str) -> None:
    _, text = _translation(language)
    assert sorted(KEPT.findall(text)) == sorted(KEPT.findall(_english()))


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_translation_keeps_the_sections(language: str) -> None:
    _, text = _translation(language)
    headings = [line for line in text.splitlines() if line.startswith("## ")]
    english = [line for line in _english().splitlines() if line.startswith("## ")]
    assert len(headings) == len(english)
    assert headings[0] == english[0] == "## Random New World"
