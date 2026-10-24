"""Installing and removing generated mods touches only rnw_exp_* folders."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from rnw.app import install
from rnw.app.install import InstallError


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
    assert not (profile / "mod" / install.WORK).exists()
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


@pytest.mark.skipif(sys.platform == "win32", reason="a read-only folder holds no file on Windows")
def test_a_world_whose_files_the_game_holds_is_retired_and_deleted_later(tmp_path: Path) -> None:
    """The folder moves aside in one rename, the new world goes in, the held rest stays hidden.

    A read-only folder stands in for a file the game holds: its entries cannot be deleted,
    while the world around it can still be renamed, as under Wine (experiment 021).
    """
    profile = tmp_path / "profile"
    profile.mkdir()
    target = install.install(_mod(tmp_path / "a", "rnw_exp_new_world", "one"), profile)
    held = target / "in_game"
    held.mkdir()
    _ = (held / "heightmap.bin").write_bytes(b"old")
    held.chmod(0o500)
    try:
        _ = install.install(_mod(tmp_path / "b", "rnw_exp_new_world", "two"), profile, replace=True)
        assert (target / "in_game.txt").read_text(encoding="utf-8") == "two"
        assert install.installed_mods(profile) == [target]
        [retired] = (profile / "mod" / install.WORK / install.RETIRED).iterdir()
        assert (retired / "in_game" / "heightmap.bin").is_file()
        assert not (retired / install.METADATA).exists()
        assert install.sweep(profile) == [retired]
    finally:
        (profile / "mod" / install.WORK / install.RETIRED).chmod(0o700)
        for path in (profile / "mod" / install.WORK / install.RETIRED).rglob("*"):
            if path.is_dir():
                path.chmod(0o700)
    assert install.sweep(profile) == []
    assert not (profile / "mod" / install.WORK).exists()


def test_a_world_that_cannot_be_moved_is_left_as_it_was(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the system refuses to move the installed world, nothing changes and it says why."""
    profile = tmp_path / "profile"
    profile.mkdir()
    target = install.install(_mod(tmp_path / "a", "rnw_exp_new_world", "one"), profile)
    original = Path.rename

    def refuse(self: Path, destination: Path) -> Path:
        if self == target:
            message = "[WinError 32] Sharing violation"
            raise PermissionError(message)
        return original(self, destination)

    monkeypatch.setattr(Path, "rename", refuse)
    incoming = install.stage(
        _mod(tmp_path / "b", "rnw_exp_new_world", "two"), profile, replace=True
    )
    with pytest.raises(install.WorldInUseError, match="Untick it"):
        _ = install.put_in_place(incoming)
    assert (target / "in_game.txt").read_text(encoding="utf-8") == "one"
    assert incoming.is_dir()
    with pytest.raises(install.WorldInUseError):
        _ = install.install(
            _mod(tmp_path / "c", "rnw_exp_new_world", "three"), profile, replace=True
        )
    assert not incoming.exists()
    assert install.installed_mods(profile) == [target]
