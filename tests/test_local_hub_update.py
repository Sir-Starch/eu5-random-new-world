"""The local hub updater preserves the existing hub on success and failure."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, cast
from unittest.mock import Mock

import hub
import pytest
import update_local_hub as updater

if TYPE_CHECKING:
    from pathlib import Path


def _profile_and_candidate(root: Path, installed_id: str = hub.LEGACY_MOD_ID) -> tuple[Path, Path]:
    profile = root / "profile"
    old = profile / "mod/rnw_exp_hub"
    (old / ".metadata").mkdir(parents=True)
    _ = (old / ".metadata/metadata.json").write_text(
        json.dumps({"id": installed_id, "version": "0.13.9"}), encoding="utf-8"
    )
    _ = (old / "marker").write_text("old", encoding="utf-8")
    candidate = root / "candidate"
    candidate.mkdir()
    _ = (candidate / "marker").write_text("new", encoding="utf-8")
    (candidate / ".metadata").mkdir()
    _ = (candidate / ".metadata/metadata.json").write_bytes(hub.metadata("0.13.10"))
    return profile, candidate


@pytest.mark.parametrize("installed_id", [hub.LEGACY_MOD_ID, hub.MOD_ID])
def test_install_preserves_previous_hub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, installed_id: str
) -> None:
    monkeypatch.setattr(updater, "check_eu5_not_running", Mock())
    profile, candidate = _profile_and_candidate(tmp_path, installed_id)
    backup = updater.install(candidate, profile, "0.13.10")
    assert (backup / "marker").read_text(encoding="utf-8") == "old"
    assert (profile / "mod/rnw_exp_hub/marker").read_text(encoding="utf-8") == "new"
    metadata = cast(
        "dict[str, object]",
        json.loads(
            (profile / "mod/rnw_exp_hub/.metadata/metadata.json").read_text(encoding="utf-8-sig")
        ),
    )
    assert metadata["id"] == hub.MOD_ID
    previous = cast(
        "dict[str, object]", json.loads((backup / ".metadata/metadata.json").read_text())
    )
    assert previous["id"] == installed_id


def test_foreign_id_is_not_replaced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(updater, "check_eu5_not_running", Mock())
    profile, candidate = _profile_and_candidate(tmp_path, "another.mod")
    with pytest.raises(ValueError, match="not the development hub"):
        _ = updater.install(candidate, profile, "0.13.10")
    assert (profile / "mod/rnw_exp_hub/marker").read_text(encoding="utf-8") == "old"
    assert not (profile / ".rnw-hub-backups").exists()


def test_failed_installed_verification_restores_previous_hub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(updater, "check_eu5_not_running", Mock())
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


def _which_pgrep(cmd: str) -> str | None:
    return "/usr/bin/pgrep" if cmd == "pgrep" else None


def _which_tasklist(cmd: str) -> str | None:
    return r"C:\Windows\System32\tasklist.exe" if cmd == "tasklist" else None


def _which_none(_cmd: str) -> str | None:
    return None


def test_check_eu5_not_running_passes_on_posix_when_not_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(shutil, "which", _which_pgrep)
    monkeypatch.setattr(subprocess, "run", Mock(return_value=subprocess.CompletedProcess([], 1)))
    updater.check_eu5_not_running()


def test_check_eu5_not_running_fails_on_posix_when_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(shutil, "which", _which_pgrep)
    monkeypatch.setattr(subprocess, "run", Mock(return_value=subprocess.CompletedProcess([], 0)))
    with pytest.raises(ValueError, match="EU5 is running"):
        updater.check_eu5_not_running()


def test_check_eu5_not_running_fails_on_posix_when_pgrep_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(shutil, "which", _which_none)
    with pytest.raises(ValueError, match="Cannot check whether EU5 is running"):
        updater.check_eu5_not_running()


def test_check_eu5_not_running_passes_on_windows_when_not_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(shutil, "which", _which_tasklist)
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(
            return_value=subprocess.CompletedProcess(
                [], 0, stdout="INFO: No tasks are running which match the specified criteria."
            )
        ),
    )
    updater.check_eu5_not_running()


def test_check_eu5_not_running_fails_on_windows_when_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(shutil, "which", _which_tasklist)
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(
            return_value=subprocess.CompletedProcess(
                [], 0, stdout='"eu5.exe","1234","Console","1","50,000 K"'
            )
        ),
    )
    with pytest.raises(ValueError, match="EU5 is running"):
        updater.check_eu5_not_running()


def test_check_eu5_not_running_fails_on_windows_when_tasklist_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(shutil, "which", _which_none)
    with pytest.raises(ValueError, match="Cannot check whether EU5 is running"):
        updater.check_eu5_not_running()
