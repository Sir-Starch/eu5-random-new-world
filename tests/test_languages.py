"""The game's official languages are read from the installation, never listed (synthetic)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.eu5_newworld import Plan, PlannedCell
from rnw.eu5_nw_export import _localization  # pyright: ignore[reportPrivateUsage]
from rnw.languages import LanguageError, official_languages
from rnw.model import CellClass

if TYPE_CHECKING:
    from pathlib import Path


def _write(root: Path, relative: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text("l_x:\n", encoding="utf-8")


def test_the_languages_are_the_folders_that_hold_their_own_files(tmp_path: Path) -> None:
    """A folder counts when it holds a file named for it, however deep; others do not."""
    base = "game/main_menu/localization"
    _write(tmp_path, f"{base}/english/a_l_english.yml")
    _write(tmp_path, f"{base}/turkish/events/DHE/b_l_turkish.yml")
    _write(tmp_path, f"{base}/german/a_l_english.yml")  # a stray file of another language
    (tmp_path / base / "empty").mkdir()
    assert official_languages(tmp_path) == ("english", "turkish")


def test_an_installation_without_english_is_refused(tmp_path: Path) -> None:
    """Authored text is English, so an installation without it cannot be exported."""
    _write(tmp_path, "game/main_menu/localization/german/a_l_german.yml")
    with pytest.raises(LanguageError, match="no english localization"):
        _ = official_languages(tmp_path)
    with pytest.raises(LanguageError, match="No localization folder"):
        _ = official_languages(tmp_path / "missing")


def test_a_world_writes_its_names_in_every_language_it_is_given() -> None:
    """Both files of the names exist for every language, Turkish among them."""
    cell = PlannedCell("a", "Alpha", 1, CellClass.LAND, "p", "ar", "r", "s", "c")
    files = _localization(Plan(cells=[cell]), {}, {}, ("english", "turkish"))
    assert sorted(files) == [
        "main_menu/localization/english/replace/rnw_new_world_replace_l_english.yml",
        "main_menu/localization/english/rnw_new_world_l_english.yml",
        "main_menu/localization/turkish/replace/rnw_new_world_replace_l_turkish.yml",
        "main_menu/localization/turkish/rnw_new_world_l_turkish.yml",
    ]
    turkish = files["main_menu/localization/turkish/rnw_new_world_l_turkish.yml"].decode(
        "utf-8-sig"
    )
    assert turkish.startswith("l_turkish:\n")
    assert ' a: "Alpha"' in turkish
