"""The window's language: chosen, the game's, the system's; its texts and its errors (L1)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.app.gamenames import game_names
from rnw.gui import text as window
from rnw.messages import MESSAGES, say
from rnw.settings import SettingsError
from rnw.translations import WINDOW, problems
from rnw.worldfile import WorldFileError

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

OFFICIAL = tuple(window.LANGUAGE_NAMES)


@pytest.fixture(autouse=True)
def _english() -> Iterator[None]:
    yield
    window.set_language("english")


def test_every_window_text_is_translated_and_current_in_every_language() -> None:
    """The release check of the window: strings, stages and messages."""
    assert problems(WINDOW, window.sources(), OFFICIAL) == []


def test_the_choice_comes_before_the_game_and_the_game_before_the_system() -> None:
    assert window.choose_language("german", "russian", "french") == "german"
    assert window.choose_language("", "russian", "french") == "russian"
    assert window.choose_language("", None, "french") == "french"
    assert window.choose_language("", "klingon", None) == "english"


def test_the_window_speaks_the_language_it_is_given() -> None:
    window.set_language("russian")
    assert window.language() == "russian"
    assert window.text("cancel") != window.STRINGS["cancel"]
    assert window.stage_text("natives") != "Founding native societies"
    window.set_language("klingon")
    assert window.language() == "english"
    assert window.text("cancel") == "Cancel"


def test_errors_are_explained_in_the_windows_language() -> None:
    error = ValueError(say("code.short"))
    assert str(error) == MESSAGES["code.short"]
    assert window.explain(error) == MESSAGES["code.short"]
    window.set_language("german")
    assert window.explain(error) not in {MESSAGES["code.short"], ""}
    damaged = window.explain(WorldFileError("META lists no files"))
    assert "META lists no files" in damaged
    assert "Setting x must be an integer" in window.explain(
        SettingsError("Setting x must be an integer")
    )
    assert window.explain(OSError("disk full")) == "disk full"


def test_the_games_names_are_read_and_stems_completed(tmp_path: Path) -> None:
    folder = tmp_path / "game" / "main_menu" / "localization" / "russian"
    folder.mkdir(parents=True)
    lines = (
        "l_russian:",
        ' abipones_culture: "Абипонск"',
        ' goods_gold: "Золото"',
        ' scripted: "[ROOT.GetName]"',
    )
    _ = (folder / "cultures_l_russian.yml").write_text("\n".join(lines), encoding="utf-8-sig")
    keys = frozenset({"abipones_culture", "goods_gold", "scripted", "absent"})
    assert game_names(tmp_path, "russian", keys) == {
        "abipones_culture": "Абипонская",
        "goods_gold": "Золото",
    }
