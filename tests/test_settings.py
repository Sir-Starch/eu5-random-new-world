"""Settings documents are versioned, strict and canonically serialized."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from rnw.settings import (
    GENERATOR_VERSION,
    PRESETS,
    SettingsError,
    build_settings,
    canonical_json,
    load_settings,
    run_spec,
    spec_digest,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_presets_differ_in_shape_controls() -> None:
    """At least two presets with different geography and coast parameters exist."""
    assert {"continents", "archipelago"} <= set(PRESETS)
    assert PRESETS["continents"].geography != PRESETS["archipelago"].geography
    assert PRESETS["continents"].coast != PRESETS["archipelago"].coast


def test_settings_document_round_trips_through_its_canonical_json(tmp_path: Path) -> None:
    """A written settings document reloads to identical settings and digest."""
    settings = build_settings("archipelago", {"coast": {"passes": 3, "window": [1, 2, 30, 40]}})
    path = tmp_path / "settings.json"
    _ = path.write_text(canonical_json(settings.to_json_data()), encoding="utf-8")
    loaded = load_settings("continents", path)
    assert loaded == settings
    assert spec_digest(run_spec(5, loaded)) == spec_digest(run_spec(5, settings))
    assert spec_digest(run_spec(5, loaded)) != spec_digest(run_spec(6, loaded))
    assert run_spec(5, loaded)["generator_version"] == GENERATOR_VERSION


def test_canonical_json_is_sorted_compact_ascii() -> None:
    """Key order and spacing never depend on insertion order or platform."""
    assert canonical_json({"b": 1, "a": "é"}) == '{"a":"\\u00e9","b":1}\n'


@pytest.mark.parametrize(
    "overrides",
    [
        {"geography": {"unknown": 1}},
        {"coast": {"passes": 65}},
        {"coast": {"passes": True}},
        {"coast": {"window": [5, 5, 4, 9]}},
        {"surprise": {}},
        {"schema": 2},
        {"preset": "fantasy"},
        {"synthetic": {"width": 64, "old_world_columns": 40}},
    ],
)
def test_invalid_overrides_are_rejected(overrides: dict[str, object]) -> None:
    """Unknown, mistyped or out-of-range values never silently pass."""
    with pytest.raises(SettingsError):
        _ = build_settings("continents", overrides)


def test_settings_file_must_be_an_object(tmp_path: Path) -> None:
    """A JSON list is not a settings document."""
    path = tmp_path / "settings.json"
    _ = path.write_text(json.dumps([1, 2]), encoding="utf-8")
    with pytest.raises(SettingsError):
        _ = load_settings("continents", path)
