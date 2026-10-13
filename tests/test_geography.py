"""Synthetic hierarchy tests; no game assets enter the repository."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.geography import GeographyError, color_summary, read_locations, summary

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


def test_color_audit_accepts_inline_comments_uppercase_keys_and_bom(tmp_path: Path) -> None:
    """Color counts must include declarations carrying notes and mixed-case keys."""
    definitions = tmp_path / "definitions.txt"
    colors = tmp_path / "colors.txt"
    _ = definitions.write_text(
        "america={ north={ region={ area={ province={ cell_one Cell_TWO } } } } }",
        encoding="utf-8-sig",
    )
    _ = colors.write_text(
        "cell_one = a # note\nCell_TWO = 00FF01\nunused = 000002 # note\n",
        encoding="utf-8-sig",
    )
    result = color_summary(read_locations(definitions), colors)
    assert result["named_locations"] == 3
    assert result["hierarchy_keys_without_color"] == 0
    assert result["color_keys_outside_hierarchy"] == 1
    assert result["duplicate_colors"] == 0


def test_malformed_color_entry_is_rejected(tmp_path: Path) -> None:
    """Unexpected non-comment lines cannot be silently left out of an audit."""
    colors = tmp_path / "colors.txt"
    _ = colors.write_text("cell_one = gg0000\n", encoding="utf-8")
    with pytest.raises(GeographyError, match="line 1"):
        _ = color_summary((), colors)


def test_malformed_assignment_is_rejected(tmp_path: Path) -> None:
    """A truncated scalar assignment cannot become a false location key."""
    definitions = tmp_path / "definitions.txt"
    _ = definitions.write_text(
        "america={ north={ region={ area={ province={ cell_one bad= } } } } }",
        encoding="utf-8",
    )
    with pytest.raises(GeographyError, match="Malformed assignment"):
        _ = read_locations(definitions)
