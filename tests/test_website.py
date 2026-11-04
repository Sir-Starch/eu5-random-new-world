"""The player's guide at rnw.sirstarch.com: translations, generated pages and font coverage.

The site is committed as built (website/public). These checks fail when a translation is missing,
stale or loses a control, a link or a code span; when a committed page no longer matches its
sources; and when a page shows a character its font subset lacks.
"""

from __future__ import annotations

import re
import tomllib

import pytest
import sitegen


def test_every_language_is_current() -> None:
    assert sitegen.content_problems() == []


def test_every_official_language_has_a_page() -> None:
    games = {language.game for language in sitegen.LANGUAGES}
    assert games == {path.stem for path in sitegen.CONTENT.glob("*.toml")}
    assert len({language.slug for language in sitegen.LANGUAGES}) == len(sitegen.LANGUAGES)
    assert set(sitegen.GAME_TERMS) == games


def test_a_changed_control_is_caught() -> None:
    english, _ = sitegen.read_content("english")
    text = english["start.3_text"]
    changed = text.replace("{ui:install}", "{ui:generate}")
    assert sitegen.markup_signature(text) != sitegen.markup_signature(changed)
    lost_link = english["start.ready_text"].replace("(https://", "(http://")
    assert sitegen.markup_signature(english["start.ready_text"]) != sitegen.markup_signature(
        lost_link
    )


def test_terms_are_the_windows_words_of_the_release() -> None:
    english = sitegen.window_english()
    russian = sitegen.window_terms("russian", english)
    assert sitegen.clean_term(english["library_remove"]) == "Remove"
    assert sitegen.clean_term(english["compare"]) == "Compare"
    assert sitegen.clean_term(russian["generate"]) == "Создать"


def test_committed_pages_match_their_sources() -> None:
    manifest = sitegen.read_manifest()
    for path, text in sitegen.render(manifest).items():
        committed = sitegen.PUBLIC / path
        assert committed.is_file(), f"{path} is not built"
        assert committed.read_text(encoding="utf-8") == text, f"{path} is out of date"


def test_fonts_cover_every_character_they_show() -> None:
    manifest = sitegen.read_manifest()
    for page, document in sitegen.pages():
        for face in sitegen.faces(page.language):
            chars = sitegen.needed(face, page, document)
            name = sitegen.font_name(face, page.language.slug, chars)
            assert name in manifest, f"{page.language.slug}: {name} is not built"
            assert set(chars) <= set(manifest[name]["chars"])
            assert (sitegen.PUBLIC / "fonts" / name).is_file()


@pytest.mark.parametrize("language", [language.game for language in sitegen.LANGUAGES])
def test_texts_carry_no_straight_quotes_or_stray_markup(language: str) -> None:
    texts = sitegen.flatten(
        tomllib.loads((sitegen.CONTENT / f"{language}.toml").read_text(encoding="utf-8"))
    )
    for key, text in texts.items():
        if key == "source":
            continue
        assert '"' not in text, f"{language}/{key}"
        assert text.count("**") % 2 == 0, f"{language}/{key}"
        assert text.count("`") % 2 == 0, f"{language}/{key}"
        assert not re.search(r"\{(?!ui:|game:|v:)", text), f"{language}/{key}"
