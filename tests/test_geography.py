"""Synthetic hierarchy tests; no game assets enter the repository."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.geography import GeographyError, read_locations, summary

if TYPE_CHECKING:
    from pathlib import Path


def test_reads_hierarchy_and_ignores_scalar_when_province_has_attribute(tmp_path: Path) -> None:
    """Given a synthetic province, when parsed, then only its two cells are counted."""
    source = tmp_path / "definitions.txt"
    _ = source.write_text(
        """america = { north = { r_region = { a_area = { p_province = {
not_eligible_for_dynamic_country_name = yes cell_one cell_two } } } } }""",
        encoding="utf-8",
    )
    locations = read_locations(source)
    assert [item.key for item in locations] == ["cell_one", "cell_two"]
    assert summary(locations)["american_location"] == 2


def test_duplicate_location_is_rejected(tmp_path: Path) -> None:
    """Given two parents for a key, when parsed, then validation fails."""
    source = tmp_path / "definitions.txt"
    _ = source.write_text(
        """america = { north = { r_region = { a_area = {
p_province = { cell_one } q_province = { cell_one } } } } }""",
        encoding="utf-8",
    )
    with pytest.raises(GeographyError, match="multiple parents"):
        _ = read_locations(source)
