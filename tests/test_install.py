"""Installing and removing generated mods touches only rnw_exp_* folders."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.app import install
from rnw.app.install import InstallError

if TYPE_CHECKING:
    from pathlib import Path


def _mod(root: Path, name: str, marker: str = "one") -> Path:
    mod = root / name
    (mod / ".metadata").mkdir(parents=True)
    _ = (mod / ".metadata/metadata.json").write_text('{"id": "x"}', encoding="utf-8")
    _ = (mod / "in_game.txt").write_text(marker, encoding="utf-8")
    return mod


def test_install_replace_and_uninstall_leave_other_mods_alone(tmp_path: Path) -> None:
    """A generated mod is copied in, replaced in place, listed and removed; a stranger stays."""
    profile = tmp_path / "profile"
    profile.mkdir()
    stranger = _mod(profile / "mod", "workshop_12345")
    first = _mod(tmp_path / "out", "rnw_exp_new_world", "one")
    target = install.install(first, profile)
    assert target == profile / "mod" / "rnw_exp_new_world"
    assert (target / "in_game.txt").read_text(encoding="utf-8") == "one"
    with pytest.raises(InstallError, match="exists"):
        _ = install.install(first, profile)
    second = _mod(tmp_path / "out2", "rnw_exp_new_world", "two")
    _ = install.install(second, profile, replace=True)
    assert (target / "in_game.txt").read_text(encoding="utf-8") == "two"
    assert not list((profile / "mod").glob(".*partial"))
    assert install.installed_mods(profile) == [target]
    with pytest.raises(InstallError, match="Not installed"):
        _ = install.uninstall(["workshop_12345"], profile)
    assert stranger.exists()
    assert install.uninstall(["rnw_exp_new_world"], profile) == [target]
    assert not target.exists()
    assert stranger.exists()


def test_a_foreign_folder_of_the_same_name_is_never_replaced(tmp_path: Path) -> None:
    """A folder named like ours but without our metadata is refused, even with replace."""
    profile = tmp_path / "profile"
    (profile / "mod" / "rnw_exp_new_world").mkdir(parents=True)
    prepared = _mod(tmp_path / "out", "rnw_exp_new_world")
    with pytest.raises(InstallError):
        _ = install.install(prepared, profile, replace=True)
    with pytest.raises(InstallError, match="valid rnw_exp_"):
        _ = install.install(tmp_path / "out", profile)
    with pytest.raises(InstallError, match="profile folder"):
        _ = install.install(prepared, tmp_path / "nowhere")
    assert install.installed_mods(tmp_path / "nowhere") == []
