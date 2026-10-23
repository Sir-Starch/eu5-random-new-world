"""The hook probe of N2: anchors, files and script syntax (synthetic)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw import eu5_probe
from rnw.pdx import parse

if TYPE_CHECKING:
    from pathlib import Path

DEFINITIONS = """europe = {
\twestern_europe = { r = { central_switzerland_area = { p = { bern interlaken } } } }
}
"""
COUNTRIES = """countries = { countries = {
\tBRN = { own_control_core = { bern interlaken } country_rank = rank_county capital = bern }
} }
"""
README = "# " + " ".join(eu5_probe.FORMABLE_KEYS) + "\n"
COAT_OF_ARMS = 'x = { pattern = "pattern_solid.dds" texture = "ce_checky_15_points.dds" }\n'
FILES = {
    "in_game/map_data/definitions.txt": DEFINITIONS,
    "main_menu/setup/1337/10_countries.txt": COUNTRIES,
    "in_game/common/formable_countries/readme.txt": README,
    "main_menu/common/coat_of_arms/coat_of_arms/pre_scripted_countries.txt": COAT_OF_ARMS,
    "in_game/common/on_action/_hardcoded.txt": "on_game_start = { effect = { } }\n",
    "in_game/common/on_action/country_yearly.txt": "yearly_country_pulse = { on_actions = { x } }\n",
    "in_game/common/decisions/canal_construction.txt": (
        "x = { decision_category = infrastructure_decisions ai_will_do = { value = 1 } }\n"
    ),
    "in_game/common/scripted_effects/e.txt": (
        "e = { create_country_from_location = { set_capital = x make_subject_of = { } } }\n"
    ),
    "in_game/common/subject_types/vassal.txt": "vassal = { }\n",
    "main_menu/localization/english/a_l_english.yml": 'l_english:\n a: "A"\n',
    "main_menu/localization/turkish/a_l_turkish.yml": 'l_turkish:\n a: "A"\n',
}


def _install(root: Path, overrides: dict[str, str] | None = None) -> Path:
    for relative, text in {**FILES, **(overrides or {})}.items():
        path = root / "game" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(text, encoding="utf-8")
    return root


def test_the_probe_is_built_from_anchors_that_hold(tmp_path: Path) -> None:
    """A conforming installation gives every file, each script reads, texts in every language."""
    files = eu5_probe.build(_install(tmp_path))
    eu5_probe.check(files)
    assert ".metadata/metadata.json" in files
    assert "main_menu/localization/turkish/rnw_probe_l_turkish.yml" in files
    formable = files["in_game/common/formable_countries/rnw_probe.txt"].decode("utf-8-sig")
    assert "tag = ZQP" in formable
    assert "area = area:central_switzerland_area" in files[
        "in_game/common/scripted_country_names/rnw_probe.txt"
    ].decode("utf-8-sig")
    for path, data in files.items():
        if path.endswith(".txt"):
            assert parse(data.decode("utf-8-sig")).entries, path


@pytest.mark.parametrize(
    ("override", "problem"),
    [
        ({"in_game/events/x.txt": "x = { tag = ZQP }\n"}, "already used by the game"),
        ({"in_game/common/formable_countries/readme.txt": "# level\n"}, "no longer documents"),
        (
            {"main_menu/setup/1337/10_countries.txt": COUNTRIES.replace("interlaken", "elsewhere")},
            "no longer starts with",
        ),
        (
            {
                "main_menu/setup/1337/10_countries.txt": COUNTRIES.replace(
                    "rank_county", "rank_duchy"
                )
            },
            "no longer a county",
        ),
        ({"in_game/common/subject_types/vassal.txt": "x = { }\n"}, "vassal.txt no longer holds"),
        (
            {"in_game/common/scripted_effects/e.txt": "e = { }\n"},
            "no scripted effect uses create_country_from_location",
        ),
    ],
)
def test_an_anchor_that_has_moved_stops_the_build(
    tmp_path: Path, override: dict[str, str], problem: str
) -> None:
    """The probe is never built on a guess: a changed installation is refused with the reason."""
    root = _install(tmp_path, override)
    assert any(problem in found for found in eu5_probe.anchor_problems(root))
    with pytest.raises(eu5_probe.ProbeError, match="cannot be built"):
        _ = eu5_probe.build(root)
