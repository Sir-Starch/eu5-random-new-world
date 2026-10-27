"""The local hub updater preserves the existing hub on success and failure."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
import update_local_hub as updater

if TYPE_CHECKING:
    from pathlib import Path


def _profile_and_candidate(root: Path) -> tuple[Path, Path]:
    profile = root / "profile"
    old = profile / "mod/rnw_exp_hub"
    (old / ".metadata").mkdir(parents=True)
    _ = (old / ".metadata/metadata.json").write_text(
        json.dumps({"id": "rnw_exp_hub", "version": "0.13.9"}), encoding="utf-8"
    )
    _ = (old / "marker").write_text("old", encoding="utf-8")
    candidate = root / "candidate"
    candidate.mkdir()
    _ = (candidate / "marker").write_text("new", encoding="utf-8")
    return profile, candidate


def test_install_preserves_previous_hub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subprocess, "run", Mock(return_value=subprocess.CompletedProcess([], 1)))
    profile, candidate = _profile_and_candidate(tmp_path)
    backup = updater.install(candidate, profile, "0.13.10")
    assert (backup / "marker").read_text(encoding="utf-8") == "old"
    assert (profile / "mod/rnw_exp_hub/marker").read_text(encoding="utf-8") == "new"


def test_failed_installed_verification_restores_previous_hub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(subprocess, "run", Mock(return_value=subprocess.CompletedProcess([], 1)))
    profile, candidate = _profile_and_candidate(tmp_path)
    actual_verify = updater.verify_copy

    def fail_after_swap(folder: Path, wanted: dict[str, str]) -> None:
        if folder.name == "rnw_exp_hub":
            raise ValueError("verification failed")  # noqa: EM101, TRY003 - injected failure
        actual_verify(folder, wanted)

    monkeypatch.setattr(updater, "verify_copy", fail_after_swap)
    with pytest.raises(ValueError, match="verification failed"):
        _ = updater.install(candidate, profile, "0.13.10")
    assert (profile / "mod/rnw_exp_hub/marker").read_text(encoding="utf-8") == "old"
