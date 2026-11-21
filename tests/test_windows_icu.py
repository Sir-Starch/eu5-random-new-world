"""The hub's ICU forwarder is put on the DLL search path only where the system lacks icuuc.dll."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rnw.gui import windows_icu

if TYPE_CHECKING:
    from pathlib import Path


def _hub(tmp_path: Path, *, forwarder: bool) -> Path:
    folder = windows_icu.forwarder_folder(tmp_path)
    folder.mkdir(parents=True)
    if forwarder:
        _ = (folder / windows_icu.LIBRARY).write_bytes(b"MZ")
    return tmp_path


def _missing(name: str) -> None:
    raise FileNotFoundError(name)


def test_the_forwarder_is_added_where_the_system_has_no_icuuc(tmp_path: Path) -> None:
    """Valve's Proton: the load fails, so the hub's folder joins the search path."""
    added: list[Path] = []
    note = windows_icu.prepare(
        program_folder=_hub(tmp_path, forwarder=True),
        platform="win32",
        load=_missing,
        add=added.append,
    )
    assert added == [tmp_path / "generator" / "compat"]
    assert "icuuc.dll" in note
    assert "forwarder" in note


def test_a_system_with_icuuc_keeps_its_own(tmp_path: Path) -> None:
    """Windows 10 and later, and the community Proton builds, are left alone."""
    asked: list[str] = []
    added: list[Path] = []
    note = windows_icu.prepare(
        program_folder=_hub(tmp_path, forwarder=True),
        platform="win32",
        load=asked.append,
        add=added.append,
    )
    assert asked == ["icuuc.dll"]
    assert (added, note) == ([], "")


def test_a_package_without_the_forwarder_says_so(tmp_path: Path) -> None:
    """The window's own import error follows; the log names its cause."""
    added: list[Path] = []
    note = windows_icu.prepare(
        program_folder=_hub(tmp_path, forwarder=False),
        platform="win32",
        load=_missing,
        add=added.append,
    )
    assert added == []
    assert "no forwarder" in note


def test_other_systems_are_not_touched(tmp_path: Path) -> None:
    """The load is never attempted off Windows."""

    def fail(_name: str) -> None:
        raise AssertionError

    assert windows_icu.prepare(program_folder=tmp_path, platform="linux", load=fail) == ""


def test_the_forwarder_lies_beside_the_interpreters_generator_folder(tmp_path: Path) -> None:
    """``program_directory`` of the hub is the mod folder; the forwarder is in generator/compat."""
    assert windows_icu.forwarder_folder(tmp_path) == tmp_path / "generator" / "compat"
