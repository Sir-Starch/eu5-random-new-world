"""Synthetic map-contract tests; never package installed game files."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest
from typer.testing import CliRunner

from rnw.cli import app
from rnw.contract import CONTRACT_FILES, MissingContractFileError, fingerprint

if TYPE_CHECKING:
    from pathlib import Path


def _make_synthetic_install(root: Path) -> None:
    for relative in CONTRACT_FILES:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_bytes(relative.encode())


def test_fingerprint_is_stable_and_detects_file_change(tmp_path: Path) -> None:
    """The same bytes hash identically; one changed source changes one digest."""
    _make_synthetic_install(tmp_path)
    first = fingerprint(tmp_path)
    assert first == fingerprint(tmp_path)
    changed = tmp_path / CONTRACT_FILES[0]
    _ = changed.write_bytes(b"changed")
    second = fingerprint(tmp_path)
    assert first[0].sha256 != second[0].sha256
    assert first[1:] == second[1:]


def test_missing_contract_file_fails_with_relative_path(tmp_path: Path) -> None:
    """A missing input cannot yield a misleading partial fingerprint."""
    with pytest.raises(MissingContractFileError, match=r"default\.map"):
        _ = fingerprint(tmp_path)


def test_cli_rejects_output_inside_game_installation(tmp_path: Path) -> None:
    """Inspection commands never write into their source installation."""
    _make_synthetic_install(tmp_path)
    destination = tmp_path / "contract.json"
    result = CliRunner().invoke(app, ["fingerprint", str(tmp_path), str(destination)])
    assert result.exit_code != 0
    assert "outside the game installation" in result.output
    assert not destination.exists()


def test_cli_fingerprint_writes_only_hashes_to_separate_path(tmp_path: Path) -> None:
    """A fingerprint file contains paths, sizes and digests, never source bytes."""
    game = tmp_path / "game_install"
    _make_synthetic_install(game)
    destination = tmp_path / "local_data/contract.json"
    result = CliRunner().invoke(app, ["fingerprint", str(game), str(destination)])
    assert result.exit_code == 0, result.output
    data = cast("dict[str, object]", json.loads(destination.read_text()))
    assert data["schema"] == 1
    records = cast("list[dict[str, object]]", data["files"])
    assert len(records) == len(CONTRACT_FILES)
    assert records[0]["path"] == CONTRACT_FILES[0]
