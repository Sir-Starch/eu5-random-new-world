"""The hub builder's decisions, on synthetic folders (the build itself needs MinGW and uv)."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import TYPE_CHECKING, cast

import hub
import pytest

from rnw.app import install

if TYPE_CHECKING:
    from pathlib import Path


def test_qt_keeps_what_the_window_imports_and_nothing_else() -> None:
    """Core, Gui, Widgets, their bindings, the runtime and two platform plugins stay."""
    kept = (
        "__init__.py",
        "Qt6Core.dll",
        "Qt6Widgets.dll",
        "QtGui.pyd",
        "msvcp140_1.dll",
        "vcruntime140.dll",
        "support/signature/loader.py",
        "plugins/platforms/qwindows.dll",
        "plugins/platforms/qoffscreen.dll",
        "plugins/styles/qmodernwindowsstyle.dll",
    )
    dropped = (
        "Qt6Quick.dll",
        "Qt6Network.dll",
        "opengl32sw.dll",
        "designer.exe",
        "QtCore.pyi",
        "plugins/platforms/qdirect2d.dll",
        "plugins/imageformats/qjpeg.dll",
        "qml/QtQuick/Controls/impl.dll",
        "translations/qtbase_de.qm",
    )
    assert all(hub.keeps_qt(name) for name in kept)
    assert not any(hub.keeps_qt(name) for name in dropped)


def test_pruning_removes_the_rest_and_refuses_a_qt_without_the_window(tmp_path: Path) -> None:
    """Unwanted files and emptied folders go; a missing needed library is an error."""
    folder = tmp_path / "site" / "PySide6"
    needed = [name for name in hub.QT_KEPT if "*" not in name]
    for name in [*needed, "Qt6Quick.dll", "qml/QtQuick/a.dll", "msvcp140.dll"]:
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_bytes(b"x" * 10)
    removed = hub.prune_qt(tmp_path / "site")
    assert removed == 20
    assert not (folder / "qml").exists()
    assert (folder / "msvcp140.dll").is_file()
    (folder / "Qt6Widgets.dll").unlink()
    with pytest.raises(hub.BuildError, match="Qt6Widgets"):
        _ = hub.prune_qt(tmp_path / "site")


def test_versions_become_four_resource_numbers() -> None:
    """MAJOR.MINOR.PATCH gets a zero; anything else stops the build."""
    assert hub.version_fields("0.9.13") == (0, 9, 13, 0)
    for bad in ("0.9", "1.0.0-rc1", "1.0.0.1", "a.b.c"):
        with pytest.raises(hub.BuildError):
            _ = hub.version_fields(bad)


def test_public_hub_identity_keeps_the_replaceable_install_folder(tmp_path: Path) -> None:
    """The public ID is independent of the local folder the installer recognises."""
    text = hub.metadata("0.9.13").decode("utf-8-sig")
    payload = cast("dict[str, object]", json.loads(text))
    assert (payload["id"], payload["version"]) == (hub.MOD_ID, "0.9.13")
    assert payload["name"] == "Random New World (RNW)"
    assert payload["id"] == "sirstarch.randomnewworld"
    assert payload["tags"] == ["Map", "Gameplay", "Utilities", "Alternative History"]
    assert "test" not in cast("str", payload["name"]).lower()
    assert "not game validated" not in cast("str", payload["name"]).lower()
    assert "test" not in cast("str", payload["short_description"]).lower()
    assert "not game validated" not in cast("str", payload["short_description"]).lower()
    mod = tmp_path / hub.MOD_FOLDER
    (mod / ".metadata").mkdir(parents=True)
    _ = (mod / ".metadata" / "metadata.json").write_bytes(hub.metadata("0.9.13"))
    assert install.is_rnw_mod(mod)


def test_python_imports_only_from_the_site_folder() -> None:
    """The ._pth names the standard library, the interpreter folder and ../site."""
    assert hub.PATH_LINES == ("python312.zip", ".", "../site", "import site")


def test_the_hub_holds_exactly_three_programs(tmp_path: Path) -> None:
    """Entry-point scripts are removed; any other program is an error."""
    for name in [*hub.PROGRAMS, "generator/site/bin/f2py", "generator/site/Scripts/x.exe"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_bytes(b"MZ")
    with pytest.raises(hub.BuildError, match="Programs"):
        hub.check_programs(tmp_path)
    hub.remove_scripts(tmp_path / "generator" / "site")
    hub.check_programs(tmp_path)
    _ = (tmp_path / "generator" / "run.bat").write_text("@echo off\n", encoding="utf-8")
    with pytest.raises(hub.BuildError, match=r"run\.bat"):
        hub.check_programs(tmp_path)


OBJDUMP_LISTING = """
The Import Tables (interpreted .idata section contents)
 vma:            Hint    Time      Forward  DLL       First
                 Table   Stamp     Chain    Name      Thunk
 009ade3c\t009ae5e8 00000000 00000000 009b052a 003e8658

\tDLL Name: icuuc.dll
\tvma:     Ordinal  Hint  Member-Name  Bound-To
\t003e8cd0  <none>  0107  ucnv_open
\t003e8cd8  <none>  00e1  UCNV_FROM_U_CALLBACK_SUBSTITUTE

 009ade50\t009ae5f0 00000000 00000000 009b0600 003e8660

\tDLL Name: KERNEL32.dll
\t003e8d00  <none>  0003  CreateFileW
\t003e8d08  0005    <none>  <none>
"""


def test_the_imports_of_a_library_are_read_from_objdump() -> None:
    """Names are kept per DLL, DLL names in lower case, an import by ordinal as ``#ordinal``."""
    assert hub.pe_imports(OBJDUMP_LISTING) == {
        "icuuc.dll": {"ucnv_open", "UCNV_FROM_U_CALLBACK_SUBSTITUTE"},
        "kernel32.dll": {"CreateFileW", "#0005"},
    }


def test_the_icu_forwarder_forwards_every_name_to_icu_dll(tmp_path: Path) -> None:
    """Windows' own icuuc.dll forwards to icu.dll; so must ours, name for name."""
    names = hub.forwarded_names(hub.ICU_SOURCES / "icuuc.def")
    assert {"ucnv_open", "ucnv_close", "UCNV_FROM_U_CALLBACK_SUBSTITUTE"} <= names
    wrong = tmp_path / "wrong.def"
    _ = wrong.write_text("EXPORTS\n    ucnv_open = icuuc68.ucnv_open_68\n", encoding="utf-8")
    with pytest.raises(hub.BuildError, match=r"icu\.ucnv_open"):
        _ = hub.forwarded_names(wrong)


def _qt_site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, imports: dict[str, set[str]]) -> Path:
    """A site folder whose Qt DLL imports ``imports`` (the reader is replaced)."""
    site = tmp_path / "site"
    (site / "PySide6").mkdir(parents=True, exist_ok=True)
    _ = (site / "PySide6" / "Qt6Core.dll").write_bytes(b"MZ")

    def read(_library: Path) -> dict[str, set[str]]:
        return imports

    monkeypatch.setattr(hub, "read_imports", read)
    return site


def test_a_qt_that_needs_more_icu_than_the_forwarder_forwards_fails_the_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A PySide6 update must break the build, not the window of a player under Proton."""
    definition = hub.ICU_SOURCES / "icuuc.def"
    own = hub.forwarded_names(definition)
    hub.check_icu_forwarder(_qt_site(tmp_path, monkeypatch, {"icuuc.dll": own}), definition)
    site = _qt_site(tmp_path, monkeypatch, {"icuuc.dll": {*own, "u_strlen"}})
    with pytest.raises(hub.BuildError, match="u_strlen"):
        hub.check_icu_forwarder(site, definition)
    site = _qt_site(tmp_path, monkeypatch, {"icuin.dll": {"ucol_open"}})
    with pytest.raises(hub.BuildError, match=r"icuin\.dll"):
        hub.check_icu_forwarder(site, definition)
    # icu.dll itself is the forwarder's target, which every Windows 10 and Proton has.
    hub.check_icu_forwarder(_qt_site(tmp_path, monkeypatch, {"icu.dll": {"u_strlen"}}), definition)


@pytest.mark.skipif(
    shutil.which(f"{hub.MINGW}-gcc") is None or shutil.which(f"{hub.MINGW}-windres") is None,
    reason="the forwarder is built with MinGW",
)
def test_the_icu_forwarder_is_built_the_same_every_time(tmp_path: Path) -> None:
    """One file for every build, so that a scan of its hash stays valid; it exports exactly the
    names of the definition, forwarded to icu.dll, and imports nothing."""
    first = hub.build_icu_forwarder(tmp_path / "a", tmp_path / "work-a")
    second = hub.build_icu_forwarder(tmp_path / "b", tmp_path / "work-b")
    assert first.read_bytes() == second.read_bytes()
    listing = subprocess.run(  # noqa: S603 - a fixed tool on a file the test built
        [f"{hub.MINGW}-objdump", "-p", str(first)], check=True, capture_output=True, text=True
    ).stdout
    forwards = {
        line.split("icu.", 1)[1].strip() for line in listing.splitlines() if "Forwarder RVA" in line
    }
    assert forwards == hub.forwarded_names(hub.ICU_SOURCES / "icuuc.def")
    assert "DLL Name" not in listing
